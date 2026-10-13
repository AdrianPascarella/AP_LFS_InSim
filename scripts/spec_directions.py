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


# Packets whose SubT comes from an enum: `insim.on.IS_TINY(TINY.MPE)` (lfs_insim/_events.py).
SUBTYPE_ENUMS = {"IS_SMALL": "SMALL", "IS_TINY": "TINY"}

# Their enums mark every subtype too, with more words than the ISP enum:
#     TINY_VER,		//  1 - info request	: get version
#     TINY_MPE,		//  9 - info			: multi player end
# Each word says who sends it: LFS ("info"), the program ("instruction"), or both.
SUBTYPE_MARKS = {
    "info": "info",
    "report": "info",  # SMALL_VTA: LFS reports a vote action
    "ping reply": "info",  # TINY_REPLY: LFS answers a TINY_PING
    "both ways": "both ways",
    "keep alive": "both ways",  # TINY_NONE: LFS sends it and the program sends it back
    "instruction": "instruction",
    "info request": "instruction",
    "ping request": "instruction",
}
SUBTYPE_MARK = re.compile(r"^\d+\s*-\s*([a-z ]+?)\s*:")
UNUSED_SUBTYPES = {"SMALL_NONE"}  # "0 : not used"


def subtype_directions(spec: Spec) -> dict[str, dict[str, str]]:
    """Packet -> its subtypes and their direction: {"IS_TINY": {"VER": "instruction", ...}}."""
    result: dict[str, dict[str, str]] = {}
    for packet, prefix in SUBTYPE_ENUMS.items():
        found = [e for e in spec.enums if e.members and e.members[0].name.startswith(prefix + "_")]
        if len(found) != 1:
            raise SpecError(f"{len(found)} {prefix}_ enums (the subtypes of {packet}), not 1")
        enum = found[0]
        result[packet] = {}
        for member in enum.members:
            if member.name in UNUSED_SUBTYPES:
                continue
            match = SUBTYPE_MARK.match(member.comment)
            if match is None or match.group(1) not in SUBTYPE_MARKS:
                raise SpecError(
                    f"line {enum.line}: {member.name} has no known direction "
                    f"({' / '.join(SUBTYPE_MARKS)}) in its comment: {member.comment!r}"
                )
            result[packet][member.name.removeprefix(prefix + "_")] = SUBTYPE_MARKS[match.group(1)]
    return result


def emit_subtypes(subtypes: dict[str, dict[str, str]], header: str) -> str:
    """lfs_insim/_subtypes.py: the subtypes that LFS sends, for the type checker and when run."""
    out = [
        header,
        '"""The subtypes (SubT) that LFS sends: `@insim.on.IS_TINY(TINY.MPE)` (lfs_insim._events).',
        "\n\nThose marked info, report, ping reply, keep alive or both ways in InSim.txt. The",
        "\nothers are requests and instructions that your program sends: a handler of them would",
        "\nnever run.",
        '\n"""\n\nfrom __future__ import annotations\n\n',
        "from enum import IntEnum\nfrom typing import Literal, TypeAlias\n\n",
        f"from lfs_insim.packets import InfoPacket, {', '.join(sorted(SUBTYPE_ENUMS))}, ",
        f"{', '.join(sorted(SUBTYPE_ENUMS.values()))}\n",
    ]
    received = {
        packet: [f"{SUBTYPE_ENUMS[packet]}.{n}" for n, d in subs.items() if d != "instruction"]
        for packet, subs in sorted(subtypes.items())
    }
    for packet, names in received.items():
        out.append(f"\nReceived{SUBTYPE_ENUMS[packet]}: TypeAlias = Literal[{', '.join(names)}]\n")
    out.append(
        "\n# Each packet with subtypes: its enum, and the subtypes that LFS sends.\n"
        "SUBTYPES: dict[type[InfoPacket], tuple[type[IntEnum], frozenset[IntEnum]]] = {\n"
    )
    for packet, names in received.items():
        out.append(f"    {packet}: ({SUBTYPE_ENUMS[packet]}, frozenset({{{', '.join(names)}}})),\n")
    out.append("}\n")
    return "".join(out)


def emit_shortcuts(directions: dict[str, str], docs: dict[str, str], header: str) -> str:
    """lfs_insim/_shortcuts.py: insim.on.IS_XXX and insim.send.IS_XXX, one attribute per packet."""
    aliases = sorted(f"Received{enum}" for enum in SUBTYPE_ENUMS.values())
    out = [
        header,
        '"""The attributes of insim.on and insim.send: one per packet (see lfs_insim._events)."""',
        "\n\nfrom __future__ import annotations\n\n",
        "from lfs_insim._events import Receive, Receiver, Sender, SubReceiver, Transmit\n",
        f"from lfs_insim._subtypes import {', '.join(aliases)}\n",
        f"from lfs_insim.packets import {', '.join(sorted(directions))}\n",
    ]
    for name, (base, attribute, module, doc) in SHORTCUT_CLASSES.items():
        wanted = DIRECTION_MODULES[module][0]
        out.append(f'\n\nclass {name}({base}):\n    """{doc}\n    """\n')
        for packet in sorted(p for p, direction in directions.items() if direction in wanted):
            if attribute == "Receiver" and packet in SUBTYPE_ENUMS:
                alias = f"Received{SUBTYPE_ENUMS[packet]}"
                out.append(
                    f"\n    {packet}: SubReceiver[{packet}, {alias}] = SubReceiver({packet})\n"
                )
            else:
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


TABLE_WORDS = {
    "info": "LFS sends it",
    "instruction": "your program sends it",
    "both ways": "both",
}


def emit_table(
    directions: dict[str, str], docs: dict[str, str], subtypes: dict[str, dict[str, str]]
) -> str:
    """docs/packets.md: every InSim packet with its direction and the way to use it."""
    out = [
        "<!-- Generated by scripts/generate_packets.py from InSim.txt. Do not edit. -->\n\n",
        "# Packets by direction\n\n",
        "Which way each InSim packet travels, as the specification marks it. Receive with\n",
        "`@insim.on.IS_XXX` what LFS sends; send with `insim.send.IS_XXX(...)` what your program\n",
        "sends. The editor lists only the packets that fit each one. `insim.on(IS_XXX)` and\n",
        "`insim.send(IS_XXX(...))` do the same, and `received.IS_XXX` and `sent.IS_XXX` are the\n",
        "same classes as `lfs_insim.packets.IS_XXX`.\n\n",
        "| Packet | Direction | Receive | Send | What it is |\n",
        "| --- | --- | --- | --- | --- |\n",
    ]
    for name in sorted(directions):
        direction = directions[name]
        receive = f"`on.{name}`" if direction in DIRECTION_MODULES["received"][0] else ""
        send = f"`send.{name}`" if direction in DIRECTION_MODULES["sent"][0] else ""
        what = docs[name].replace("|", r"\|")
        out.append(f"| `{name}` | {TABLE_WORDS[direction]} | {receive} | {send} | {what} |\n")
    out.append(
        "\nOutSim and OutGauge come by UDP only: `@outsim.on.OutSimPack2`, "
        "`@gauge.on.OutGaugePack`.\n"
    )
    out.append(
        "\n## Subtypes\n\n"
        "`IS_TINY` and `IS_SMALL` carry a subtype (`SubT`). `@insim.on.IS_TINY(TINY.MPE)` accepts\n"
        "only the subtypes that LFS sends; the others are requests and instructions for\n"
        "`insim.send.IS_TINY(SubT=...)`.\n\n"
        "| Packet | LFS sends | Your program sends |\n"
        "| --- | --- | --- |\n"
    )
    for packet, subs in sorted(subtypes.items()):
        enum = SUBTYPE_ENUMS[packet]
        cells = [
            ", ".join(f"`{enum}.{name}`" for name, d in subs.items() if (d == "instruction") == own)
            for own in (False, True)
        ]
        out.append(f"| `{packet}` | {cells[0]} | {cells[1]} |\n")
    out.append(
        "\nThe ones marked both ways (`TINY.VTC`, `SMALL.ALC`, `SMALL.LCL`) and the keep alive\n"
        "(`TINY.NONE`) are in the first column, and your program may send them too.\n"
    )
    return "".join(out)
