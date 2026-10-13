"""on_close (W10.7): once, when the InSim is closed, for a plugin to save what it keeps; and a
failing plugin is named in the log by its function."""

import asyncio
import logging

import pytest

from lfs_insim import InSim
from lfs_insim.packets import IS_VER
from lfs_insim.testing import FakeLFS


def test_on_close_runs_once_after_the_last_disconnection() -> None:
    order: list[str] = []

    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            insim.on_disconnect(lambda: order.append("disconnect"))

            @insim.on_close
            async def save() -> None:
                await asyncio.sleep(0.01)
                order.append("close")

            async with insim:
                await lfs.wait_connected()
                await asyncio.sleep(0.05)
            assert order == ["disconnect", "close"]  # awaited before leaving
            await insim.close()  # already closed: not again
            assert order == ["disconnect", "close"]

    asyncio.run(main())


def test_on_close_runs_without_ever_connecting() -> None:
    closed: list[bool] = []

    async def main() -> None:
        async with FakeLFS() as lfs:
            port = lfs.port
        insim = InSim(port=port)  # nothing listens there now
        insim.on_close(lambda: closed.append(True))
        async with insim:
            await asyncio.sleep(0.05)
        assert closed == [True]

    asyncio.run(main())


def test_a_failing_plugin_is_named_in_the_log(caplog: pytest.LogCaptureFixture) -> None:
    def camera(insim: InSim) -> None:
        @insim.on(IS_VER)
        def broken(packet: IS_VER) -> None:
            raise RuntimeError("no camera")

    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            insim.use(camera)
            with caplog.at_level(logging.ERROR, logger="lfs_insim"):
                async with insim:
                    await lfs.wait_connected()
                    await asyncio.sleep(0.1)
        assert "camera.<locals>.broken" in caplog.text

    asyncio.run(main())


def test_on_close_runs_when_the_program_is_cancelled() -> None:
    # Ctrl+C in run() cancels the task that runs the InSim.
    closed: list[bool] = []

    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            insim.on_close(lambda: closed.append(True))

            async def program() -> None:
                async with insim:
                    await insim.wait_closed()

            task = asyncio.create_task(program())
            await lfs.wait_connected()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        assert closed == [True]

    asyncio.run(main())
