"""The InSim connection (W3.4), tested against the fake LFS."""

import asyncio
import logging
import threading
from collections.abc import Awaitable, Callable

import pytest
from fake_lfs import FakeLFS

from lfs_insim import InSim
from lfs_insim.packets import IS_ISI, IS_MSO, IS_MST, IS_TINY, IS_VER, ISF, TINY


def run(test: Callable[[FakeLFS], Awaitable[None]], **options: str) -> None:
    async def main() -> None:
        async with FakeLFS(**options) as lfs:  # type: ignore[arg-type]
            await test(lfs)

    asyncio.run(main())


def test_connecting_sends_isi_and_lfs_answers_with_ver() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(
            name="hello",
            admin_password="secret",
            port=lfs.port,
            flags=ISF.MCI | ISF.LOCAL,
            interval_ms=100,
            prefix="!",
        )
        received: list[IS_VER] = []

        @insim.on(IS_VER)
        def connected(packet: IS_VER) -> None:
            received.append(packet)

        async with insim:
            isi = await lfs.wait_for(IS_ISI)
            await _until(lambda: received)
        assert isi == IS_ISI(
            ReqI=1,
            Flags=ISF.MCI | ISF.LOCAL,
            InSimVer=10,
            Prefix=ord("!"),
            Interval=100,
            Admin="secret",
            IName="hello",
        )
        assert received[0].Version == "0.8C31"

    run(test, admin="secret")


def test_handlers_receive_their_packets_and_send_replies() -> None:
    # Example 1 of API_DESIGN.md: answer a chat command.
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(name="hello", port=lfs.port)

        @insim.on(IS_MSO)
        def chat(packet: IS_MSO) -> None:
            if packet.Msg == "!hello":
                insim.send(IS_MST(Msg="/msg Hello from Python"))

        async with insim:
            await lfs.wait_connected()
            await lfs.send(IS_MSO(Msg="something else"), IS_MSO(Msg="!hello"))
            assert await lfs.wait_for(IS_MST) == IS_MST(Msg="/msg Hello from Python")

    run(test)


def test_several_handlers_for_one_packet_run_in_order() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        calls: list[str] = []

        @insim.on(IS_TINY)
        def first(packet: IS_TINY) -> None:
            calls.append("first")

        @insim.on(IS_TINY)
        def second(packet: IS_TINY) -> None:
            calls.append("second")

        async with insim:
            await lfs.wait_connected()
            await lfs.send(IS_TINY(SubT=TINY.NONE))
            await _until(lambda: len(calls) == 2)
        assert calls == ["first", "second"]

    run(test)


def test_a_failing_handler_does_not_stop_the_others(caplog: pytest.LogCaptureFixture) -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        calls: list[int] = []

        @insim.on(IS_TINY)
        def broken(packet: IS_TINY) -> None:
            raise RuntimeError("bug in the handler")

        @insim.on(IS_TINY)
        def working(packet: IS_TINY) -> None:
            calls.append(packet.ReqI)

        async with insim:
            await lfs.wait_connected()
            await lfs.send(IS_TINY(ReqI=1), IS_TINY(ReqI=2))
            await _until(lambda: len(calls) == 2)
        assert calls == [1, 2]  # the next packets still arrive, too

    with caplog.at_level(logging.ERROR, logger="lfs_insim"):
        run(test)
    assert "bug in the handler" in caplog.text
    assert "broken" in caplog.text


def test_async_handlers_can_wait_without_blocking_the_others() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        calls: list[str] = []
        release = asyncio.Event()

        @insim.on(IS_TINY)
        async def slow(packet: IS_TINY) -> None:
            await release.wait()
            calls.append("slow")

        @insim.on(IS_TINY)
        def fast(packet: IS_TINY) -> None:
            calls.append("fast")

        async with insim:
            await lfs.wait_connected()
            await lfs.send(IS_TINY())
            await _until(lambda: calls == ["fast"])
            release.set()
            await _until(lambda: calls == ["fast", "slow"])

    run(test)


def test_a_failing_async_handler_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)

        @insim.on(IS_TINY)
        async def broken(packet: IS_TINY) -> None:
            raise RuntimeError("bug in the async handler")

        async with insim:
            await lfs.wait_connected()
            await lfs.send(IS_TINY())
            await _until(lambda: _logged_by_us(caplog))

    with caplog.at_level(logging.ERROR, logger="lfs_insim"):
        run(test)
    # asyncio would also log it ("Task exception was never retrieved"), but not by name.
    record = _logged_by_us(caplog)
    assert record is not None
    assert "broken" in record.getMessage()
    assert record.exc_info is not None
    assert "bug in the async handler" in str(record.exc_info[1])


def _logged_by_us(caplog: pytest.LogCaptureFixture) -> logging.LogRecord | None:
    records = [r for r in caplog.records if r.name == "lfs_insim" and r.levelno >= logging.ERROR]
    return records[0] if records else None


def test_closing_cancels_async_handlers_that_are_still_waiting() -> None:
    # A handler that never finishes must not keep close() (or Ctrl+C) waiting forever.
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        started = asyncio.Event()
        cancelled: list[bool] = []

        @insim.on(IS_TINY)
        async def endless(packet: IS_TINY) -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.append(True)
                raise

        async with asyncio.timeout(2):
            async with insim:
                await lfs.wait_connected()
                await lfs.send(IS_TINY())
                await started.wait()
        assert cancelled == [True]

    run(test)


def test_send_without_a_connection_fails() -> None:
    with pytest.raises(ConnectionError):
        InSim().send(IS_TINY(SubT=TINY.PING))


def test_a_broken_stream_closes_the_connection(caplog: pytest.LogCaptureFixture) -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        async with insim:
            await lfs.wait_connected()
            await lfs.send_raw(bytes([0, 3, 0, 0]))  # Size 0
            await lfs.wait_disconnected()
            await _until(lambda: not insim.connected)

    with caplog.at_level(logging.ERROR, logger="lfs_insim"):
        run(test)
    assert "Size 0" in caplog.text


def test_leaving_async_with_closes_the_connection() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        async with insim:
            await lfs.wait_connected()
            assert insim.connected
        assert not insim.connected
        await lfs.wait_disconnected()

    run(test)


def test_names_and_prefix_are_checked() -> None:
    with pytest.raises(ValueError, match="prefix"):
        InSim(prefix="!!")


def test_run_blocks_until_lfs_closes_the_connection() -> None:
    # run() starts its own event loop, so the fake LFS lives in another thread here.
    ready = threading.Event()
    port: list[int] = []

    async def fake() -> None:
        async with FakeLFS() as lfs:
            port.append(lfs.port)
            ready.set()
            await lfs.wait_for(IS_ISI, timeout=5)
            await lfs.drop()

    thread = threading.Thread(target=asyncio.run, args=(fake(),))
    thread.start()
    assert ready.wait(5)
    InSim(port=port[0]).run()  # returns once the fake LFS drops the connection
    thread.join(5)


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)
