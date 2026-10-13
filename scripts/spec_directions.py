"""Which way each InSim packet travels (part of scripts/generate_packets.py).

The ISP enum of InSim.txt marks every packet type in its comment:

    ISP_ISI,		//  1 - instruction		: insim initialise
    ISP_VER,		//  2 - info			: version info
    ISP_TINY,		//  3 - both ways		: multi purpose

"info" packets are sent by LFS, "instruction" packets by the program, and "both ways" go in
either direction. Anything else in a comment stops generation, as the parser does.
"""

from __future__ import annotations

import re

from generate_enums import docstring
from spec_parser import Enum, Spec, SpecError

DIRECTIONS = ("info", "instruction", "both ways")
MARK = re.compile(r"^\d+\s*-\s*(info|instruction|both ways)\s*:")
UNUSED = {"ISP_NONE"}  # "0 : not used": the value no packet has


def packet_types(spec: Spec) -> Enum:
    """The enum of the packet types: the one whose members are ISP_ values."""
    for enum in spec.enums:
        if enum.members and enum.members[0].name.startswith("ISP_"):
            return enum
    raise SpecError("no ISP_ enum (the packet types) in the specification")


def packet_directions(spec: Spec) -> dict[str, str]:
    """Packet class name -> its direction: {"IS_ISI": "instruction", "IS_VER": "info", ...}."""
    enum = packet_types(spec)
    directions: dict[str, str] = {}
    for member in enum.members:
        if member.name in UNUSED:
            continue
        match = MARK.match(member.comment)
        if match is None:
            raise SpecError(
                f"line {enum.line}: {member.name} has no direction (info / instruction / "
                f"both ways) in its comment: {member.comment!r}"
            )
        directions["IS_" + member.name.removeprefix("ISP_")] = match.group(1)
    return directions


# The public modules that list the packets by direction (src/lfs_insim/received.py and sent.py).
DIRECTION_MODULES = {
    "received": (
        ("info", "both ways"),
        "The InSim packets that LFS sends, for `insim.on`: `@insim.on(received.IS_NPL)`.\n\n"
        "The same classes as in lfs_insim.packets (`received.IS_NPL is packets.IS_NPL`), listed\n"
        "by direction so that the editor shows only these. A packet that goes both ways is also\n"
        "in lfs_insim.sent. OutGaugePack, OutSimPack and OutSimPack2 are here too: they come by\n"
        "UDP, for `gauge.on` and `outsim.on`.",
    ),
    "sent": (
        ("instruction", "both ways"),
        "The InSim packets that your program sends, for `insim.send`: `insim.send(sent.IS_MST())`."
        "\n\n"
        "The same classes as in lfs_insim.packets (`sent.IS_MST is packets.IS_MST`), listed by\n"
        "direction so that the editor shows only these. A packet that goes both ways is also in\n"
        "lfs_insim.received.",
    ),
}


SHORTCUT_CLASSES = {
    # class: (base, attribute type, module of its packets, docstring)
    "On": (
        "Receive",
        "Receiver",
        "received",
        "Register handlers: `@insim.on.IS_NPL` lists only the packets that LFS sends.\n\n"
        "    `@insim.on(IS_NPL)` does the same.",
    ),
    "Send": (
        "Transmit",
        "Sender",
        "sent",
        "Send packets: `insim.send.IS_MST(Msg=...)` lists only the packets a program sends.\n\n"
        "    `insim.send(IS_MST(Msg=...))` does the same, and sends several at once.",
    ),
}


def emit_shortcuts(directions: dict[str, str], docs: dict[str, str], header: str) -> str:
    """lfs_insim/_shortcuts.py: insim.on.IS_XXX and insim.send.IS_XXX, one attribute per packet."""
    out = [
        header,
        '"""The attributes of insim.on and insim.send: one per packet (see lfs_insim._events)."""',
        "\n\nfrom __future__ import annotations\n\n",
        "from lfs_insim._events import Receive, Receiver, Sender, Transmit\n",
        f"from lfs_insim.packets import {', '.join(sorted(directions))}\n",
    ]
    for name, (base, attribute, module, doc) in SHORTCUT_CLASSES.items():
        wanted = DIRECTION_MODULES[module][0]
        out.append(f'\n\nclass {name}({base}):\n    """{doc}\n    """\n')
        for packet in sorted(p for p, direction in directions.items() if direction in wanted):
            out.append(f"\n    {packet} = {attribute}({packet})\n")
            out.append(docstring(docs[packet], "    "))
    return "".join(out)


# OutSim and OutGauge are only received; they come by UDP, not through insim.on. Their classes
# are in lfs_insim.packets whether or not OutSimPack.txt is here, so received.py never needs it.
UDP_PACKETS = ("OutGaugePack", "OutSimPack", "OutSimPack2")


def emit_direction_module(module: str, directions: dict[str, str], header: str) -> str:
    """lfs_insim.received or lfs_insim.sent: re-exports, written out so the editor sees them."""
    wanted, doc = DIRECTION_MODULES[module]
    names = sorted(name for name, direction in directions.items() if direction in wanted)
    if module == "received":
        names += UDP_PACKETS
    return (
        f'{header}"""{doc}\n"""\n\n'
        f"from lfs_insim.packets import {', '.join(names)}\n\n"
        f"__all__ = {names!r}\n"
    )
