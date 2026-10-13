"""@insim.every(seconds) (W3.8), tested against the fake LFS with short intervals."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from itertools import pairwise

import pytest

from lfs_insim import InSim
from lfs_insim.packets import IS_MST, IS_TINY, IS_VER, TINY
from lfs_insim.testing import FakeLFS


def run(test: Callable[[FakeLFS], Awaitable[None]]) -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            await test(lfs)

    asyncio.run(main())


async def _until(condition: Callable[[], object], timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.01)


def test_a_def_runs_at_a_fixed_rate() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        calls: list[float] = []

        @insim.every(0.02)
        def tick() -> None:
            calls.append(time.perf_counter())

        async with insim:
            await _until(lambda: len(calls) >= 5)
        assert all(later > earlier for earlier, later in pairwise(calls))

    run(test)


def test_an_async_def_may_await_and_send() -> None:
    # Example 3 of API_DESIGN.md: send packets at a fixed rate.
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)

        @insim.every(0.02)
        async def drive() -> None:
            await asyncio.sleep(0)
            insim.send(IS_MST(Msg="tick"))

        async with insim:
            assert (await lfs.wait_for(IS_MST)).Msg == "tick"
            assert (await lfs.wait_for(IS_MST)).Msg == "tick"

    run(test)


def test_an_error_is_logged_and_does_not_stop_it(caplog: pytest.LogCaptureFixture) -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        calls: list[int] = []

        @insim.every(0.02)
        def broken() -> None:
            calls.append(1)
            raise RuntimeError("boom")

        @insim.every(0.02)
        async def broken_async() -> None:
            calls.append(2)
            raise RuntimeError("boom")

        async with insim:
            await _until(lambda: calls.count(1) >= 3 and calls.count(2) >= 3)

    run(test)
    assert (
        "handler test_an_error_is_logged_and_does_not_stop_it.<locals>.test.<locals>.broken "
        in (caplog.text)
    )
    assert "broken_async failed" in caplog.text


def test_it_only_runs_while_connected() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        insim._retry_delays = (0.3,)  # a long gap without a connection
        calls: list[bool] = []

        @insim.every(0.01)
        def tick() -> None:
            calls.append(insim.connected)

        async with insim:
            await _until(lambda: len(calls) >= 3)
            await lfs.drop()
            await _until(lambda: not insim.connected)
            during_the_gap = len(calls)
            await asyncio.sleep(0.15)
            assert len(calls) == during_the_gap
            await _until(lambda: len(calls) > during_the_gap + 2)  # back after reconnecting
        assert all(calls)

    run(test)


def test_it_does_not_start_before_lfs_answers() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        order: list[str] = []

        @insim.on(IS_VER)
        def version(packet: IS_VER) -> None:
            order.append("ver")

        @insim.every(0.01)
        def tick() -> None:
            order.append("tick")

        async with insim:
            await _until(lambda: "tick" in order)
        assert order[0] == "ver"

    run(test)


def test_asking_for_the_version_does_not_start_it_twice() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        calls: list[float] = []
        versions: list[IS_VER] = []
        insim.on(IS_VER)(versions.append)

        @insim.every(0.05)
        def tick() -> None:
            calls.append(time.perf_counter())

        async with insim:
            await _until(lambda: versions)
            insim.send(IS_TINY(ReqI=2, SubT=TINY.VER))  # LFS answers with another IS_VER
            await _until(lambda: len(versions) == 2)
            await _until(lambda: len(calls) >= 5)
        gaps = [later - earlier for earlier, later in pairwise(calls)]
        assert min(gaps) > 0.025  # a second loop would call it again a moment later

    run(test)


def test_a_call_in_progress_is_cancelled_when_the_connection_ends() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        insim._retry_delays = (5.0,)  # stay disconnected
        started = asyncio.Event()
        cancelled: list[bool] = []

        @insim.every(0.01)
        async def waiting() -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.append(True)
                raise

        async with insim:
            await asyncio.wait_for(started.wait(), 2)
            await lfs.drop()
            await _until(lambda: cancelled)

    run(test)


def test_a_slow_call_does_not_cause_a_burst() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        # perf_counter: on Windows before 3.13, time.monotonic ticks every ~15 ms
        starts: list[float] = []
        ends: list[float] = []

        @insim.every(0.02)
        def tick() -> None:
            starts.append(time.perf_counter())
            if len(starts) == 1:
                time.sleep(0.15)  # misses about seven ticks
            ends.append(time.perf_counter())

        async with insim:
            await _until(lambda: len(starts) >= 3)
        assert starts[1] - ends[0] > 0.002  # not called again at once to catch up
        assert starts[2] - starts[1] > 0.002

    run(test)


def test_an_async_call_does_not_overlap_itself() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        running: list[int] = []
        most: list[int] = [0]

        @insim.every(0.01)
        async def slow() -> None:
            running.append(1)
            most[0] = max(most[0], len(running))
            await asyncio.sleep(0.05)
            running.pop()

        async with insim:
            await asyncio.sleep(0.3)
        assert most[0] == 1

    run(test)


def test_closing_from_inside_stops_it() -> None:
    async def test(lfs: FakeLFS) -> None:
        insim = InSim(port=lfs.port)
        calls: list[int] = []

        @insim.every(0.01)
        async def once() -> None:
            calls.append(1)
            await insim.close()

        async with insim:
            await insim.wait_closed()
            await asyncio.sleep(0.1)
        assert calls == [1]

    run(test)


def test_the_interval_must_be_positive() -> None:
    insim = InSim()
    with pytest.raises(ValueError):
        insim.every(0)
    with pytest.raises(ValueError):
        insim.every(-1)
