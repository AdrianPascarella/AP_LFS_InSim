"""W8.1: on_disconnect and insim.reconnected, errors="raise", and colours to send."""

import asyncio
import socket
import threading
from collections.abc import Callable

import pytest

from lfs_insim import InSim, OutGauge, text
from lfs_insim.packets import IS_ISI, IS_TINY, OutGaugePack
from lfs_insim.state import Roster
from lfs_insim.testing import FakeLFS
from lfs_insim.text import Colour

FAST = (0.01, 0.02, 0.05)


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


# on_disconnect and reconnected


def test_on_disconnect_follows_every_connection_and_reconnected_tells_them_apart() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            insim._retry_delays = FAST
            events: list[str] = []
            assert not insim.reconnected

            @insim.on_connect
            def connected() -> None:
                events.append(f"connect reconnected={insim.reconnected}")

            @insim.on_disconnect
            def disconnected() -> None:
                events.append(f"disconnect connected={insim.connected}")

            async with insim:
                await lfs.wait_connected()
                await _until(lambda: len(events) == 1)
                await lfs.drop()
                await lfs.wait_connected(connections=2)
                await _until(lambda: len(events) == 3)
            assert events == [
                "connect reconnected=False",
                "disconnect connected=False",  # after the connection is gone: it cannot send
                "connect reconnected=True",
                "disconnect connected=False",  # leaving `async with` ends a connection too
            ]

    asyncio.run(main())


def test_an_async_on_disconnect_runs_to_the_end_when_closing() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            done: list[str] = []

            @insim.on_disconnect
            async def disconnected() -> None:
                await asyncio.sleep(0.05)
                done.append("saved")

            async with insim:
                await lfs.wait_connected()
                await _until(lambda: insim.connected)
            assert done == ["saved"]  # close() waited for it; it was not cancelled

    asyncio.run(main())


def test_closing_from_on_connect_still_calls_on_disconnect() -> None:
    # Seen with the real LFS (S17): wait_closed() returned while that close() was still running,
    # and the close() of `async with` cancelled it half way, before on_disconnect.
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            events: list[str] = []

            @insim.on_connect
            async def connected() -> None:
                events.append("connect")
                await asyncio.sleep(0.05)
                await insim.close()
                events.append("after close")  # the caller is not cancelled by its own close()

            @insim.on_disconnect
            def disconnected() -> None:
                events.append("disconnect")

            async with insim:
                await insim.wait_closed()
                assert events == ["connect", "disconnect", "after close"]  # all done by now
            assert events == ["connect", "disconnect", "after close"]

    asyncio.run(main())


def test_closing_from_on_disconnect_does_not_hang() -> None:
    async def main(lfs_leaves: bool) -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            insim._retry_delays = FAST
            events: list[str] = []

            @insim.on_disconnect
            async def disconnected() -> None:
                events.append("disconnect")
                await insim.close()  # stop for good when the connection ends
                events.append("closed")

            async with asyncio.timeout(2), insim:
                await lfs.wait_connected()
                await _until(lambda: insim.connected)
                if lfs_leaves:
                    await lfs.drop()
                    await insim.wait_closed()
            await asyncio.sleep(0.1)
            assert events == ["disconnect", "closed"]
            assert lfs.connections == 1  # no reconnection after it

    asyncio.run(main(lfs_leaves=True))
    asyncio.run(main(lfs_leaves=False))


def test_a_connection_that_never_opened_has_no_on_disconnect() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            await lfs.stop()
            insim = InSim(port=lfs.port)
            insim._retry_delays = FAST
            calls: list[int] = []
            insim.on_disconnect(lambda: calls.append(1))
            async with insim:
                await asyncio.sleep(0.1)
            assert calls == []

    asyncio.run(main())


# errors="raise"


def test_errors_must_be_log_or_raise() -> None:
    with pytest.raises(ValueError, match="errors must be 'log' or 'raise'"):
        InSim(errors="ignore")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="errors must be 'log' or 'raise'"):
        OutGauge(0, errors="ignore")  # type: ignore[arg-type]


def test_with_errors_raise_a_failing_handler_closes_and_wait_closed_raises() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port, errors="raise")
            insim._retry_delays = FAST
            later: list[int] = []

            @insim.on.IS_TINY
            def broken(packet: IS_TINY) -> None:
                raise RuntimeError("bug in the handler")

            @insim.on.IS_TINY
            def after(packet: IS_TINY) -> None:
                later.append(1)

            with pytest.raises(RuntimeError, match="bug in the handler"):
                async with insim:
                    await lfs.wait_connected()
                    await lfs.send(IS_TINY(ReqI=1))
                    await insim.wait_closed()
            assert not insim.connected
            await lfs.wait_disconnected()
            await asyncio.sleep(0.1)
            assert lfs.connections == 1  # closed for good: no reconnection
            assert later == []  # it stops at the first error

    asyncio.run(main())


def test_with_errors_raise_async_handlers_and_every_raise_too() -> None:
    async def main(kind: str) -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port, errors="raise")

            if kind == "async":

                @insim.on.IS_TINY
                async def broken(packet: IS_TINY) -> None:
                    await asyncio.sleep(0)
                    raise RuntimeError(kind)
            else:

                @insim.every(0.01)
                def tick() -> None:
                    raise RuntimeError(kind)

            with pytest.raises(RuntimeError, match=kind):
                async with insim:
                    await lfs.wait_connected()
                    await lfs.send(IS_TINY(ReqI=1))
                    async with asyncio.timeout(2):
                        await insim.wait_closed()

    asyncio.run(main("async"))
    asyncio.run(main("every"))


def test_with_errors_raise_run_raises() -> None:
    ready = threading.Event()
    port: list[int] = []

    async def fake() -> None:
        async with FakeLFS() as lfs:
            port.append(lfs.port)
            ready.set()
            await lfs.wait_for(IS_ISI, timeout=5)
            await lfs.send(IS_TINY(ReqI=1))
            await lfs.wait_disconnected(timeout=5)

    thread = threading.Thread(target=asyncio.run, args=(fake(),))
    thread.start()
    assert ready.wait(5)
    insim = InSim(port=port[0], errors="raise")

    @insim.on.IS_TINY
    def broken(packet: IS_TINY) -> None:
        raise RuntimeError("from run")

    raised: list[BaseException] = []

    def runner() -> None:
        try:
            insim.run()
        except RuntimeError as error:
            raised.append(error)

    worker = threading.Thread(target=runner, daemon=True)
    worker.start()
    worker.join(10)
    thread.join(5)
    assert not worker.is_alive(), "run() did not return"
    assert [str(e) for e in raised] == ["from run"]


def test_with_errors_raise_outgauge_raises_and_run_passes_it_on() -> None:
    # The body of run(gauge): run() itself starts an event loop, so its coroutine is used here.
    from lfs_insim._run import _run

    gauge = OutGauge(0, errors="raise")

    @gauge.on.OutGaugePack
    def broken(packet: OutGaugePack) -> None:
        raise RuntimeError("gauge bug")

    async def send_when_listening() -> None:
        await _until(lambda: gauge._transport is not None)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(OutGaugePack(Car="XRT").pack(), ("127.0.0.1", gauge.port))

    async def main() -> None:
        sender = asyncio.create_task(send_when_listening())
        async with asyncio.timeout(5):
            await _run((gauge,))
        await sender

    with pytest.raises(RuntimeError, match="gauge bug"):
        asyncio.run(main())


def test_by_default_errors_are_logged_and_the_connection_stays() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)

            @insim.on.IS_TINY
            def broken(packet: IS_TINY) -> None:
                raise RuntimeError("only logged")

            async with insim:
                await lfs.wait_connected()
                await lfs.send(IS_TINY(ReqI=1))
                await asyncio.sleep(0.1)
                assert insim.connected

    asyncio.run(main())


# colours


def test_colours_are_the_lfs_codes() -> None:
    assert [c.value for c in Colour] == [f"^{n}" for n in range(9)]
    assert [c.name for c in Colour] == [
        "BLACK",
        "RED",
        "GREEN",
        "YELLOW",
        "BLUE",
        "MAGENTA",
        "CYAN",
        "WHITE",
        "DEFAULT",
    ]
    assert f"{Colour.RED}Stop{Colour.DEFAULT} now" == "^1Stop^8 now"


def test_coloured_wraps_text_and_goes_back_to_the_default() -> None:
    assert text.coloured("Stop", Colour.RED) == "^1Stop^8"
    assert text.plain(text.coloured("Stop", Colour.RED)) == "Stop"
    with pytest.raises(TypeError, match="Colour"):
        text.coloured("Stop", "^1")  # type: ignore[arg-type]


def test_connect_alone_calls_on_connect_and_close_calls_on_disconnect() -> None:
    """W6.10: a plugin that asks LFS on connecting (Roster) must work with connect() too."""

    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            roster = insim.use(Roster)
            events: list[str] = []
            insim.on_connect(lambda: events.append("connect"))
            insim.on_disconnect(lambda: events.append("disconnect"))
            await insim.connect()
            await _until(lambda: events == ["connect"])
            async with asyncio.timeout(3):
                await roster.ready()
            await insim.close()
            assert events == ["connect", "disconnect"]
            assert not insim.reconnected

    asyncio.run(main())
