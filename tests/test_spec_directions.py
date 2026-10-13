"""Which way each packet travels, read from the ISP enum of InSim.txt (W7.1)."""

from pathlib import Path

import pytest
import spec_parser
from spec_directions import packet_directions
from spec_parser import SpecError

CACHE = Path(__file__).resolve().parent.parent / "spec" / "cache"

PACKET_TYPES = """
enum // the second byte of any packet is one of these
{
    ISP_NONE,       //  0                   : not used
    ISP_ISI,        //  1 - instruction     : insim initialise
    ISP_VER,        //  2 - info            : version info
    ISP_TINY,       //  3 - both ways       : multi purpose
    ISP_REO,        // 36 - both ways       : reorder (info or instruction)
};
"""


def directions(text: str) -> dict[str, str]:
    return packet_directions(spec_parser.parse(text, "x"))


def test_reads_the_direction_of_each_packet_type() -> None:
    assert directions(PACKET_TYPES) == {
        "IS_ISI": "instruction",
        "IS_VER": "info",
        "IS_TINY": "both ways",
        "IS_REO": "both ways",  # the words after the colon do not count
    }


@pytest.mark.parametrize(
    "comment",
    ["4 : no direction", "4 - sometimes : unknown word", "4 - info"],
)
def test_a_packet_type_without_a_known_direction_stops(comment: str) -> None:
    text = PACKET_TYPES.replace("};", f"    ISP_NEW, // {comment}\n}};")
    with pytest.raises(SpecError, match="ISP_NEW has no direction"):
        directions(text)


def test_a_specification_without_packet_types_stops() -> None:
    with pytest.raises(SpecError, match="no ISP_ enum"):
        directions("enum // other\n{\n    XP_ONE, // 1 : one\n};\n")


@pytest.mark.skipif(not (CACHE / "InSim.txt").exists(), reason="run scripts/fetch_spec.py first")
def test_every_packet_of_the_specification_has_a_direction() -> None:
    spec = spec_parser.parse((CACHE / "InSim.txt").read_text(encoding="utf-8"), "InSim.txt")
    found = packet_directions(spec)
    assert found.keys() == {name for name in spec.structs if name.startswith("IS_")}
    assert found["IS_ISI"] == "instruction"
    assert found["IS_VER"] == "info"
    assert found["IS_REO"] == "both ways"  # "reorder (info or instruction)"
    assert found["IS_BTN"] == "instruction"
    assert found["IS_BTC"] == "info"
