"""Which way an InSim packet travels, as the ISP enum of InSim.txt marks it.

Every generated InSim packet has one of these as its base, so the type checker (and the editor)
knows what `insim.on` and `insim.send` accept: `on` takes info packets, `send` takes instruction
packets, and the "both ways" ones are both.
"""

from __future__ import annotations

from lfs_insim.packets._codec import InSimPacket


class InfoPacket(InSimPacket):
    """An InSim packet that LFS sends ("info" in InSim.txt): receive it with `insim.on`."""


class InstructionPacket(InSimPacket):
    """An InSim packet that your program sends ("instruction" in InSim.txt): `insim.send` it."""


class BothWaysPacket(InfoPacket, InstructionPacket):
    """An InSim packet that goes both ways: LFS sends it, and your program may send it too."""


def direction_error(packet_type: object, wanted: type[InSimPacket]) -> str:
    """Why `packet_type` cannot be used where `wanted` is (for a clear TypeError)."""
    if not isinstance(packet_type, type):
        return f"{packet_type!r} is not a packet class (IS_NPL, not IS_NPL())"
    name = packet_type.__name__
    if name.startswith(("OutSim", "OutGauge")):
        source, variable = (
            ("OutGauge", "gauge") if name.startswith("OutGauge") else ("OutSim", "outsim")
        )
        return f"{name} comes by UDP, not InSim: use {source} (`@{variable}.on.{name}`)"
    if wanted is InfoPacket:
        if issubclass(packet_type, InstructionPacket):
            return f"{name} is an instruction: LFS never sends it, your program sends it (send)"
        return f"{name} is not an InSim packet that LFS sends"
    if issubclass(packet_type, InfoPacket):
        return f"{name} is info: LFS sends it and your program receives it (on), not the reverse"
    return f"{name} is not an InSim packet that your program can send"
