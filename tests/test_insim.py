"""The InSim connection (W3.4), tested against the fake LFS."""

import asyncio
import logging
import threading
from collections.abc import Awaitable, Callable

import pytest

from lfs_insim import InSim
from lfs_insim.packets import IS_ISI, IS_MSO, IS_MST, IS_TINY, IS_VER, ISF, TINY
from lfs_insim.testing import FakeLFS


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


def test_keepalive_packets_are_answered() -> None:
    # LFS sends a blank IS_TINY every 30 s and closes the connection after 70 s of silence.
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        seen: list[IS_TINY] = []

        @insim.on(IS_TINY)
        def tiny(packet: IS_TINY) -> None:
            seen.append(packet)  # handlers still see the keepalive packets

        async with insim:
            await lfs.wait_connected()
            assert await lfs.wait_for(IS_TINY) == IS_TINY(ReqI=0, SubT=TINY.NONE)
            assert await lfs.wait_for(IS_TINY) == IS_TINY(ReqI=0, SubT=TINY.NONE)
            await asyncio.sleep(0.4)  # longer than the fake LFS's timeout
            assert insim.connected and lfs.connected
        assert seen and all(packet.SubT == TINY.NONE for packet in seen)

    run(test, keepalive=0.05, timeout=0.2)  # type: ignore[arg-type]


def test_a_silent_lfs_is_taken_for_dead(caplog: pytest.LogCaptureFixture) -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        insim._silence_timeout = 0.1
        async with insim:
            await lfs.wait_connected()
            await _until(lambda: not insim.connected)
            await lfs.wait_disconnected()

    with caplog.at_level(logging.WARNING, logger="lfs_insim"):
        run(test)
    assert "no data from LFS" in caplog.text


def test_data_keeps_the_connection_alive() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        insim._silence_timeout = 0.2
        async with insim:
            await lfs.wait_connected()
            for _ in range(6):
                await asyncio.sleep(0.1)
                await lfs.send(IS_MSO(Msg="still here"))
            assert insim.connected

    run(test)


def test_leaving_sends_tiny_close() -> None:
    async def test(lfs: FakeLFS) -> None:
        async with InSim(port=lfs.port):
            await lfs.wait_connected()
        assert await lfs.wait_for(IS_TINY) == IS_TINY(ReqI=0, SubT=TINY.CLOSE)
        await lfs.wait_disconnected()

    run(test)


def test_closing_after_lfs_has_gone_does_not_fail() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        async with insim:
            await lfs.wait_connected()
            await lfs.drop()
            await _until(lambda: not insim.connected)
        assert not any(isinstance(packet, IS_TINY) for packet in lfs.received)

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
        insim._retry_delays = FAST
        async with insim:
            await lfs.wait_connected()
            assert insim.connected
        assert not insim.connected
        await lfs.wait_disconnected()
        await asyncio.sleep(0.2)  # several retry delays: closed means no more reconnecting
        assert lfs.connections == 1 and not lfs.connected

    run(test)


def test_names_and_prefix_are_checked() -> None:
    with pytest.raises(ValueError, match="prefix"):
        InSim(prefix="!!")


def test_run_reconnects_and_returns_when_closed() -> None:
    # run() starts its own event loop, so the fake LFS lives in another thread here.
    ready = threading.Event()
    port: list[int] = []

    async def fake() -> None:
        async with FakeLFS() as lfs:
            port.append(lfs.port)
            ready.set()
            await lfs.wait_for(IS_ISI, timeout=5)
            await lfs.drop()  # run() does not stop here: it connects again
            await lfs.wait_for(IS_ISI, timeout=5)
            await lfs.wait_disconnected(timeout=5)

    thread = threading.Thread(target=asyncio.run, args=(fake(),))
    thread.start()
    assert ready.wait(5)
    insim = InSim(port=port[0])
    insim._retry_delays = FAST
    connections: list[int] = []

    @insim.on_connect
    async def connected() -> None:
        connections.append(1)
        if len(connections) == 2:
            await insim.close()  # the way out of run() besides Ctrl+C

    # In its own thread, so that a run() that never returns fails the test instead of hanging it.
    runner = threading.Thread(target=insim.run, daemon=True)
    runner.start()
    runner.join(10)
    assert not runner.is_alive(), "run() did not return after close()"
    thread.join(5)
    assert not thread.is_alive()
    assert len(connections) == 2


FAST = (0.01, 0.02, 0.05)


def test_retry_delays_grow_and_stop_growing() -> None:
    delays = InSim()._retry_delays
    assert delays[0] == 1
    assert list(delays) == sorted(delays)
    assert delays[-1] == 10  # the last one repeats for as long as LFS is away


def test_reconnects_when_lfs_drops_the_connection() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(name="again", port=lfs.port)
        insim._retry_delays = FAST
        async with insim:
            await lfs.wait_connected()
            assert (await lfs.wait_for(IS_ISI)).IName == "again"
            await lfs.drop()
            await lfs.wait_connected(connections=2)
            assert (await lfs.wait_for(IS_ISI)).IName == "again"  # greeted again
            await _until(lambda: insim.connected)

    run(test)


def test_a_long_wait_for_lfs_is_reported_once(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Refused connections fail at once here (on Windows a real one takes ~2 s).
    real_open = asyncio.open_connection
    attempts: list[int] = []

    async def open_connection(host: str, port: int) -> object:
        attempts.append(port)
        if len(attempts) <= 3:
            raise ConnectionRefusedError("LFS is not running")
        return await real_open(host, port)

    async def test(lfs: FakeLFS) -> None:
        monkeypatch.setattr(asyncio, "open_connection", open_connection)
        insim = InSim(port=lfs.port)
        insim._retry_delays = FAST
        async with insim:
            await lfs.wait_connected()

    with caplog.at_level(logging.INFO, logger="lfs_insim"):
        run(test)
    assert len(attempts) == 4
    failures = [r for r in caplog.records if "not answering" in r.getMessage()]
    assert len(failures) == 1


def test_waits_for_lfs_to_start(caplog: pytest.LogCaptureFixture) -> None:
    async def test(lfs: FakeLFS) -> None:
        await lfs.stop()
        insim = InSim(port=lfs.port)
        insim._retry_delays = FAST
        async with insim:
            assert not insim.connected
            # A refused connection takes ~2 s to fail on Windows, so wait for it, not a fixed time.
            await _until(lambda: "not answering" in caplog.text, timeout=10)
            await asyncio.sleep(0.1)  # more attempts may fail meanwhile, and are not reported
            await lfs.start()
            await lfs.wait_connected()
            await _until(lambda: insim.connected)

    with caplog.at_level(logging.INFO, logger="lfs_insim"):
        run(test)
    failures = [r for r in caplog.records if "not answering" in r.getMessage()]
    assert len(failures) == 1  # said once, not once per attempt
    assert "connected to LFS" in caplog.text


def test_on_connect_runs_after_every_connection() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        insim._retry_delays = FAST
        calls: list[str] = []

        @insim.on_connect
        def first() -> None:
            calls.append("def")
            insim.send(IS_TINY(ReqI=42, SubT=TINY.PING))  # already connected here

        @insim.on_connect
        async def second() -> None:
            calls.append("async")

        @insim.on_connect
        def broken() -> None:
            raise RuntimeError("bug in on_connect")

        async with insim:
            assert (await lfs.wait_for(IS_TINY)).ReqI == 42
            await lfs.drop()
            assert (await lfs.wait_for(IS_TINY)).ReqI == 42
            await _until(lambda: len(calls) == 4)
        assert calls == ["def", "async", "def", "async"]

    run(test)


def test_lfs_closing_at_once_is_reported_and_slows_down(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # A wrong admin password: LFS closes the connection without IS_VER (see FakeLFS). The wait
    # must keep growing: resetting it made the previous project reconnect ~250 times in 25 s
    # until LFS said "TCP excess" (LEGADO.md P24).
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port, admin_password="wrong")
        insim._retry_delays = (0.01, 0.3)
        async with insim:
            await lfs.wait_connected(connections=2)
            await asyncio.sleep(0.2)
            assert lfs.connections == 2  # waiting 0.3 s now, not reconnecting at once

    with caplog.at_level(logging.WARNING, logger="lfs_insim"):
        run(test, admin="secret")
    assert "before answering" in caplog.text
    # Also what happens with 8 InSim programs already connected (the real LFS, S20): not a password.
    assert "8 InSim programs" in caplog.text


def test_close_while_waiting_for_lfs_returns_at_once() -> None:
    async def test(lfs: FakeLFS) -> None:
        await lfs.stop()
        insim = InSim(port=lfs.port)  # default delays: up to 10 s between attempts
        async with asyncio.timeout(1):
            async with insim:
                await asyncio.sleep(0.1)

    run(test)


def test_connect_is_a_single_attempt() -> None:
    async def test(lfs: FakeLFS) -> None:
        await lfs.stop()
        with pytest.raises(OSError):
            await InSim(port=lfs.port).connect()

    run(test)


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)
