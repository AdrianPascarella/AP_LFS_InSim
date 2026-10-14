"""InSim(udp_port=...): IS_ISI.UDPPort, where LFS sends OutSim / OutGauge after SMALL_SSP / SSG."""

import asyncio

import pytest

from lfs_insim import InSim
from lfs_insim.packets import IS_ISI, ISF
from lfs_insim.testing import FakeLFS


def test_udp_port_goes_in_is_isi() -> None:
    async def scenario() -> IS_ISI:
        async with FakeLFS() as lfs, InSim(port=lfs.port, udp_port=30011):
            return await lfs.wait_for(IS_ISI)

    assert asyncio.run(scenario()).UDPPort == 30011


def test_no_udp_port_by_default() -> None:
    assert InSim()._isi.UDPPort == 0


@pytest.mark.parametrize("flag", [ISF.MCI, ISF.NLP])
def test_udp_port_with_mci_or_nlp_is_refused(flag: ISF) -> None:
    # InSim.txt: with UDPPort set, LFS sends IS_MCI / IS_NLP by UDP, which InSim does not read.
    with pytest.raises(ValueError, match="udp_port"):
        InSim(udp_port=30011, flags=ISF.LOCAL | flag)


def test_need_refuses_mci_with_udp_port_and_changes_nothing() -> None:
    insim = InSim(udp_port=30011, flags=ISF.LOCAL)
    with pytest.raises(ValueError, match="udp_port"):
        insim.need(flags=ISF.MCI)
    assert insim._isi.Flags == ISF.LOCAL


def test_mci_without_udp_port_is_fine() -> None:
    insim = InSim(flags=ISF.MCI)
    insim.need(flags=ISF.NLP)
    assert insim._isi.Flags == ISF.MCI | ISF.NLP
