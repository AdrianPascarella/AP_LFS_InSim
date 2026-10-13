"""What plugins need in IS_ISI (W10.5): `insim.need(flags=..., interval_ms=...)`, joined before
connecting. Flags are added up; of the intervals, the shortest is kept (0 means none)."""

import asyncio
import logging

import pytest
from fake_lfs import FakeLFS

from lfs_insim import InSim
from lfs_insim.packets import IS_ISI, ISF

FAST = (0.01, 0.02, 0.05)


async def _isi(lfs: FakeLFS, insim: InSim) -> IS_ISI:
    insim.port = lfs.port
    async with insim:
        return await lfs.wait_for(IS_ISI)


def test_the_flags_of_every_plugin_are_added_up() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(flags=ISF.LOCAL)
            insim.need(flags=ISF.MCI)
            insim.need(flags=ISF.CON | ISF.MCI)
            isi = await _isi(lfs, insim)
            assert isi.Flags == ISF.LOCAL | ISF.MCI | ISF.CON

    asyncio.run(main())


def test_the_shortest_interval_is_kept() -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim()
            insim.need(interval_ms=500)
            insim.need(interval_ms=100)
            insim.need(interval_ms=0)  # "none": asks for nothing
            insim.need(interval_ms=300)
            isi = await _isi(lfs, insim)
            assert isi.Interval == 100

    asyncio.run(main())


def test_an_interval_given_to_insim_counts_too() -> None:
    insim = InSim(interval_ms=50)
    insim.need(interval_ms=200)
    assert insim._isi.Interval == 50


def test_a_negative_interval_is_an_error() -> None:
    with pytest.raises(ValueError, match="interval_ms"):
        InSim().need(interval_ms=-1)


def test_asking_while_connected_warns_and_counts_from_the_next_connection(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def main() -> None:
        async with FakeLFS() as lfs:
            insim = InSim(port=lfs.port)
            insim._retry_delays = FAST
            async with insim:
                first = await lfs.wait_for(IS_ISI)
                with caplog.at_level(logging.WARNING, logger="lfs_insim"):
                    insim.need(flags=ISF.MCI)
                assert "next connection" in caplog.text
                assert not first.Flags & ISF.MCI
                await lfs.drop()
                second = await lfs.wait_for(IS_ISI)
                assert second.Flags & ISF.MCI

    asyncio.run(main())
