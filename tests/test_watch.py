"""W8.4: insim.watch(before=, after=), the public door Roster uses, against the fake LFS."""

import asyncio
import re
from pathlib import Path

import pytest
from fake_lfs import FakeLFS

from lfs_insim import InSim
from lfs_insim.packets import IS_TINY, InSimPacket

FAST = (0.01, 0.02, 0.05)


def test_before_runs_before_the_handlers_and_after_after_them() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            insim._retry_delays = FAST
            seen: list[str] = []

            def before(packet: InSimPacket) -> None:
                if isinstance(packet, IS_TINY) and packet.ReqI == 7:
                    seen.append("before")

            def after(packet: InSimPacket) -> None:
                if isinstance(packet, IS_TINY) and packet.ReqI == 7:
                    seen.append("after")

            insim.watch(before=before, after=after)

            @insim.on.IS_TINY
            def handler(packet: IS_TINY) -> None:
                if packet.ReqI == 7:
                    seen.append("handler")

            @insim.on.IS_TINY
            async def first_step(packet: IS_TINY) -> None:
                if packet.ReqI == 7:
                    seen.append("async first step")
                    await asyncio.sleep(0.05)
                    seen.append("async later")

            async with insim:
                await lfs.wait_connected()
                await lfs.send(IS_TINY(ReqI=7))
                async with asyncio.timeout(2):
                    while len(seen) < 5:
                        await asyncio.sleep(0.01)
            assert seen == ["before", "handler", "async first step", "after", "async later"]

    asyncio.run(main())


def test_only_before_or_only_after() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            befores: list[InSimPacket] = []
            afters: list[InSimPacket] = []
            insim.watch(before=befores.append)
            insim.watch(after=afters.append)
            async with insim:
                await lfs.wait_connected()
                await lfs.send(IS_TINY(ReqI=7))
                async with asyncio.timeout(2):
                    while not any(getattr(p, "ReqI", 0) == 7 for p in afters):
                        await asyncio.sleep(0.01)
            assert any(isinstance(p, IS_TINY) and p.ReqI == 7 for p in befores)

    asyncio.run(main())


def test_watch_needs_a_function_and_only_def() -> None:
    insim = InSim()

    async def coroutine(packet: InSimPacket) -> None:
        pass

    with pytest.raises(TypeError, match="watch\\(\\) needs before=, after= or both"):
        insim.watch()
    with pytest.raises(TypeError, match="must be a plain def"):
        insim.watch(before=coroutine)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be a plain def"):
        insim.watch(after=coroutine)  # type: ignore[arg-type]


def test_a_failing_watcher_follows_errors_raise() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port, errors="raise")
            insim._retry_delays = FAST

            def broken(packet: InSimPacket) -> None:
                if isinstance(packet, IS_TINY) and packet.ReqI == 7:
                    raise RuntimeError("bug in the watcher")

            insim.watch(before=broken)
            with pytest.raises(RuntimeError, match="bug in the watcher"):
                async with insim:
                    await lfs.wait_connected()
                    await lfs.send(IS_TINY(ReqI=7))
                    async with asyncio.timeout(2):
                        await insim.wait_closed()

    asyncio.run(main())


def test_roster_uses_only_the_public_api() -> None:
    source = (Path(__file__).parents[1] / "src" / "lfs_insim" / "state.py").read_text("utf-8")
    assert re.findall(r"\b_?insim\._\w+", source) == []
