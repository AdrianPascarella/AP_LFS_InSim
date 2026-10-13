"""Every way to say the same thing is the same thing, for every packet (W7.6, condition 1)."""

import pytest

from lfs_insim import InSim, packets, received, sent
from lfs_insim.packets import BothWaysPacket, InfoPacket, InstructionPacket

NAMES = sorted(name for name in packets.__all__ if name.startswith("IS_"))
UDP = ["OutGaugePack", "OutSimPack", "OutSimPack2"]


def test_there_are_the_packets_of_the_specification() -> None:
    assert len(NAMES) == 70


@pytest.mark.parametrize("name", NAMES)
def test_a_packet_is_where_its_direction_says(name: str) -> None:
    cls = getattr(packets, name)
    in_on = issubclass(cls, InfoPacket)
    in_send = issubclass(cls, InstructionPacket)
    assert in_on or in_send
    assert issubclass(cls, BothWaysPacket) == (in_on and in_send)
    # the same class everywhere, never a copy
    assert (getattr(received, name, None) is cls) == in_on
    assert (getattr(sent, name, None) is cls) == in_send
    insim = InSim()
    assert hasattr(insim.on, name) == in_on
    assert hasattr(insim.send, name) == in_send


@pytest.mark.parametrize("name", [n for n in NAMES if issubclass(getattr(packets, n), InfoPacket)])
def test_on_attribute_and_call_register_the_same_handler(name: str) -> None:
    cls = getattr(packets, name)
    insim = InSim()

    def handler(packet: object) -> None: ...

    getattr(insim.on, name)(handler)
    insim.on(cls)(handler)
    insim.on(getattr(received, name))(handler)
    assert insim._handlers._by_type == {cls: [handler, handler, handler]}


@pytest.mark.parametrize("name", UDP)
def test_udp_packets_are_received_and_never_sent(name: str) -> None:
    assert getattr(received, name) is getattr(packets, name)
    assert not hasattr(sent, name)
