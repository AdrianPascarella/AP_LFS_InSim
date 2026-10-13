"""OutSim, OutGauge and run() (W3.7), tested with local datagrams. Never port 30000: in use here."""

import asyncio
import logging
import socket
import threading
import time
from collections.abc import Callable

import pytest
from fake_lfs import FakeLFS

from lfs_insim import InSim, OutGauge, OutSim, run
from lfs_insim.packets import (
    IS_ISI,
    IS_TINY,
    OSO,
    TINY,
    OutGaugePack,
    OutSimMain,
    OutSimPack,
    OutSimPack2,
)


def send(port: int, *datagrams: bytes) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for data in datagrams:
            sock.sendto(data, ("127.0.0.1", port))


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


def test_outgauge_handlers_receive_its_packets() -> None:
    async def main() -> None:
        gauge = OutGauge(port=0)
        received: list[OutGaugePack] = []
        waited: list[float] = []

        @gauge.on(OutGaugePack)
        def dashboard(packet: OutGaugePack) -> None:
            received.append(packet)

        @gauge.on(OutGaugePack)
        async def later(packet: OutGaugePack) -> None:
            await asyncio.sleep(0)
            waited.append(packet.RPM)

        async with gauge:
            assert gauge.port != 0  # port=0 picks a free one, and port tells which
            send(gauge.port, OutGaugePack(Car="XFG", RPM=3000.0).pack(), OutGaugePack(ID=7).pack())
            await _until(lambda: len(received) == 2 and len(waited) == 2)
        assert received[0].Car == "XFG"
        assert received[0].ID is None
        assert received[1].ID == 7  # LFS adds it when "OutGauge ID" is set in cfg.txt
        assert waited == [3000.0, 0.0]

    asyncio.run(main())


def test_unreadable_datagrams_are_skipped_and_reported_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def main() -> None:
        gauge = OutGauge(port=0)
        received: list[OutGaugePack] = []
        gauge.on(OutGaugePack)(received.append)
        good = OutGaugePack(RPM=1.0).pack()

        async with gauge:
            # Too short, a broken ID, too long (LFS set up for something else), then a good one.
            send(gauge.port, b"x" * 50, good[:-1] + b"\0\0", good + bytes(8), good)
            await _until(lambda: received)
            assert caplog.text.count("cannot be read") == 1  # not once per datagram
            send(gauge.port, b"x" * 10, good)
            await _until(lambda: len(received) == 2)
        assert caplog.text.count("cannot be read") == 2  # again, after a good one in between
        assert [packet.RPM for packet in received] == [1.0, 1.0]

    with caplog.at_level(logging.WARNING, logger="lfs_insim"):
        asyncio.run(main())


def test_outsim_without_options_receives_outsimpack() -> None:
    async def main() -> None:
        outsim = OutSim(port=0)
        received: list[OutSimPack] = []
        outsim.on(OutSimPack)(received.append)
        async with outsim:
            send(outsim.port, OutSimPack(Time=5, Heading=1.5).pack(), OutSimPack(ID=3).pack())
            await _until(lambda: len(received) == 2)
        assert (received[0].Time, received[0].Heading, received[1].ID) == (5, 1.5, 3)

    asyncio.run(main())


def test_outsim_with_options_receives_outsimpack2() -> None:
    options = OSO.HEADER | OSO.TIME | OSO.MAIN
    packet = OutSimPack2(OSOpts=options, Time=9, OSMain=OutSimMain(Heading=2.0))

    async def main() -> None:
        outsim = OutSim(port=0, options=options)
        received: list[OutSimPack2] = []
        outsim.on(OutSimPack2)(received.append)
        async with outsim:
            send(outsim.port, packet.pack())
            await _until(lambda: received)
        assert received == [packet]

    asyncio.run(main())


def test_handlers_for_a_packet_that_never_comes_are_refused() -> None:
    with pytest.raises(TypeError, match="OutSimPack2"):
        OutSim(port=0, options=OSO.TIME).on(OutSimPack)
    with pytest.raises(TypeError, match="OutSimPack"):
        OutSim(port=0).on(OutSimPack2)
    with pytest.raises(TypeError, match="OutGaugePack"):
        OutGauge(port=0).on(OutSimPack)  # type: ignore[arg-type]


def test_a_failing_handler_does_not_stop_the_others(caplog: pytest.LogCaptureFixture) -> None:
    async def main() -> None:
        gauge = OutGauge(port=0)
        calls: list[str] = []

        @gauge.on(OutGaugePack)
        def broken(packet: OutGaugePack) -> None:
            raise RuntimeError("boom")

        @gauge.on(OutGaugePack)
        def fine(packet: OutGaugePack) -> None:
            calls.append("fine")

        async with gauge:
            send(gauge.port, OutGaugePack().pack(), OutGaugePack().pack())
            await _until(lambda: len(calls) == 2)

    asyncio.run(main())
    assert "handler test_a_failing_handler_does_not_stop_the_others" in caplog.text


def test_closing_stops_listening_and_cancels_waiting_handlers() -> None:
    async def main() -> None:
        gauge = OutGauge(port=0)
        started = asyncio.Event()
        cancelled: list[bool] = []

        @gauge.on(OutGaugePack)
        async def forever(packet: OutGaugePack) -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.append(True)
                raise

        async with gauge:
            send(gauge.port, OutGaugePack().pack())
            await asyncio.wait_for(started.wait(), 2)
            waiting = asyncio.create_task(gauge.wait_closed())
            await asyncio.sleep(0.01)
            assert not waiting.done()
            await gauge.close()
            await asyncio.wait_for(waiting, 2)
        assert cancelled == [True]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", gauge.port))  # free again

    asyncio.run(main())


def test_a_port_in_use_fails_when_starting() -> None:
    async def main() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as taken:
            taken.bind(("127.0.0.1", 0))
            with pytest.raises(OSError):
                async with OutGauge(port=taken.getsockname()[1]):
                    pass

    asyncio.run(main())


def test_run_needs_something_to_run() -> None:
    with pytest.raises(TypeError):
        run()


def test_run_starts_every_source_and_closing_one_stops_them_all() -> None:
    # Example 3 of API_DESIGN.md, without every(): InSim and OutGauge in one event loop.
    ready = threading.Event()
    lfs_port: list[int] = []
    closed: list[IS_TINY] = []

    async def fake() -> None:
        async with FakeLFS() as lfs:
            lfs_port.append(lfs.port)
            ready.set()
            await lfs.wait_for(IS_ISI, timeout=5)
            closed.append(await lfs.wait_for(IS_TINY, timeout=5))

    thread = threading.Thread(target=asyncio.run, args=(fake(),))
    thread.start()
    assert ready.wait(5)
    insim = InSim(port=lfs_port[0])
    gauge = OutGauge(port=0)
    received: list[OutGaugePack] = []

    @insim.on_connect
    def connected() -> None:
        send(gauge.port, OutGaugePack(RPM=4000.0).pack())  # gauge is listening by now

    @gauge.on(OutGaugePack)
    async def dashboard(packet: OutGaugePack) -> None:
        received.append(packet)
        await gauge.close()  # run() returns, and closes insim too

    runner = threading.Thread(target=run, args=(insim, gauge), daemon=True)
    runner.start()
    runner.join(10)
    assert not runner.is_alive(), "run() did not return after close()"
    thread.join(5)
    assert not thread.is_alive()
    assert [packet.RPM for packet in received] == [4000.0]
    assert closed[0].SubT == TINY.CLOSE  # insim said goodbye to LFS


def test_a_source_runs_alone_until_closed() -> None:
    outsim = OutSim(port=0)

    @outsim.on(OutSimPack)
    async def stop(packet: OutSimPack) -> None:
        await outsim.close()

    def sender() -> None:
        while outsim.port == 0:  # set once it listens
            time.sleep(0.01)
        send(outsim.port, OutSimPack().pack())

    threading.Thread(target=sender, daemon=True).start()
    runner = threading.Thread(target=outsim.run, daemon=True)
    runner.start()
    runner.join(10)
    assert not runner.is_alive(), "run() did not return after close()"


def test_the_packet_attribute_of_on_is_the_same_as_calling_it() -> None:
    # W7.5: @gauge.on.OutGaugePack and @outsim.on.OutSimPack / .OutSimPack2.
    options = OSO.HEADER | OSO.TIME

    async def main() -> None:
        gauge = OutGauge(port=0)
        outsim = OutSim(port=0)
        outsim2 = OutSim(port=0, options=options)
        got: list[str] = []

        @gauge.on.OutGaugePack
        def dashboard(packet: OutGaugePack) -> None:
            got.append(f"gauge {packet.Car}")

        @outsim.on.OutSimPack
        def motion(packet: OutSimPack) -> None:
            got.append(f"outsim {packet.Time}")

        @outsim2.on.OutSimPack2
        def motion2(packet: OutSimPack2) -> None:
            got.append(f"outsim2 {packet.Time}")

        async with gauge, outsim, outsim2:
            send(gauge.port, OutGaugePack(Car="XRT").pack())
            send(outsim.port, OutSimPack(Time=1).pack())
            send(outsim2.port, OutSimPack2(OSOpts=options, Time=2).pack())
            await _until(lambda: len(got) == 3)
        assert sorted(got) == ["gauge XRT", "outsim 1", "outsim2 2"]

    asyncio.run(main())
    with pytest.raises(TypeError, match="LFS sends OutSimPack, not OutSimPack2"):
        _ = OutSim(port=0).on.OutSimPack2
