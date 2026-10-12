from pathlib import Path

import pytest
import spec_parser
from spec_parser import SpecError

CACHE = Path(__file__).resolve().parent.parent / "spec" / "cache"

FRAGMENT = """#ifndef _ISPACKETS_H_
#define _ISPACKETS_H_

const int INSIM_VERSION = 10;
const int MAX_THINGS = 3; // NOTE: grows

// Flags field

#define XF_ONE		1		// bit 0
#define XF_TWO		0x02	// bit 1

#define XF_BOTH		(XF_ONE | XF_TWO)

// the packet types

enum // the second byte of any packet is one of these
{
	XP_NONE,		// 0 : not used
	XP_THING,		// 1 : a thing
	XP_NUM
};

struct Thing // one thing
{
	word	A;		// first
	byte	B;
	byte	Sp;
};

struct IS_X // eXample - variable size
{
	byte	Size;		// 8 + TEXT_SIZE
	byte	Type;		// XP_THING
	byte	ReqI;		// 0
	byte	Zero;

	Thing	Things	[MAX_THINGS];
	char	Name[4];	// name
	Vec		Pos;

//	char	Text[TEXT_SIZE]; // 0 to 240 characters of text
};
#endif
"""


def test_reads_constants_defines_enums_and_structs() -> None:
    spec = spec_parser.parse(FRAGMENT, "fragment")
    assert spec.constants["INSIM_VERSION"].value == 10
    assert spec.constants["MAX_THINGS"].comment == "NOTE: grows"

    (group,) = spec.define_groups
    assert group.heading == "Flags field"
    assert [(d.name, d.value) for d in group.defines] == [
        ("XF_ONE", 1),
        ("XF_TWO", 2),
        ("XF_BOTH", 3),
    ]

    (enum,) = spec.enums
    assert enum.comment == "the second byte of any packet is one of these"
    assert enum.heading == "the packet types"
    assert [(m.name, m.value) for m in enum.members] == [
        ("XP_NONE", 0),
        ("XP_THING", 1),
        ("XP_NUM", 2),
    ]
    assert enum.members[1].comment == "1 : a thing"

    packet = spec.structs["IS_X"]
    assert packet.comment == "eXample - variable size"
    names = [f.name for f in packet.fields]
    assert names == ["Size", "Type", "ReqI", "Zero", "Things", "Name", "Pos", "Text"]
    things, name, pos, text = packet.fields[4:]
    assert (things.ctype, things.count, things.count_name) == ("Thing", 3, "MAX_THINGS")
    assert (name.ctype, name.count, name.comment) == ("char", 4, "name")
    assert (pos.ctype, pos.count) == ("Vec", None)
    assert text.commented_out
    assert (text.count, text.count_name) == (None, "TEXT_SIZE")
    assert packet.fields[0].comment == "8 + TEXT_SIZE"


def test_reads_outsim_conditions() -> None:
    # the mixed indentation is copied from OutSimPack.txt
    text = (
        "struct Pack\n{\n\t// if (OSOpts & OSO_HEADER)\n\n\tchar L;\n\tchar F;\n\n"
        "  \t// if (OSOpts & OSO_TIME)\n\n\tunsigned\tTime;\t\t// ms\n};\n"
    )
    (struct,) = spec_parser.parse(text, "outsim").structs.values()
    assert [(f.name, f.condition) for f in struct.fields] == [
        ("L", "OSO_HEADER"),
        ("F", "OSO_HEADER"),
        ("Time", "OSO_TIME"),
    ]


def test_collects_values_listed_only_in_comments() -> None:
    text = (
        "// Values for Input\n\n// CS_MSX\t\t\t 0 - steer: 1 hard left\n"
        "// CS_THROTTLE\t\t 1 - 0 to 65535\n// HOSTF_FCV\t\t\t0x100\n"
        "// AXO_START_LIGHTS1\t149 // layout\n// TINY_NONE is not followed by a number\n"
    )
    values = spec_parser.parse(text, "x").comment_values
    assert [(v.name, v.value, v.comment, v.line) for v in values] == [
        ("CS_MSX", 0, "steer: 1 hard left", 3),
        ("CS_THROTTLE", 1, "0 to 65535", 4),
        ("HOSTF_FCV", 256, "", 5),
        ("AXO_START_LIGHTS1", 149, "layout", 6),
    ]


def test_a_heading_two_blank_lines_away_is_not_attached() -> None:
    text = "// unrelated\n\n\nenum\n{\n\tA_ONE,\n};\n"
    (enum,) = spec_parser.parse(text, "x").enums
    assert enum.heading == ""


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("typedef int thing;\n", "x:1: unexpected statement"),
        ("struct S\n{\n\tbyte A, B;\n};\n", "x:3: unexpected line in struct S"),
        ("struct S\n{\n\tbyte A[UNKNOWN];\n};\n", "x:3: unknown array length 'UNKNOWN'"),
        ("struct S\n{\n\tMystery A;\n};\n", "unknown type 'Mystery'"),
        ("struct S\n{\n\t// just a remark\n};\n", "x:3: unexpected line in struct S"),
        ("struct S\n{\n\tbyte A;\n", "x:1: block never closed"),
        ("#define X_A\t(X_B | X_C)\n", "unknown symbol 'X_B'"),
        ("#define X_A\t1 << 2\n", "unsupported value '1 << 2'"),
        ("#define NOTHING\n", "#define NOTHING has no value"),
        ("enum\n{\n};\n", "x:1: empty enum"),
        ("struct S\n{\n\tbyte A;\n};\nstruct S\n{\n\tbyte A;\n};\n", "defined twice"),
    ],
)
def test_anything_unknown_stops_with_the_line_number(text: str, message: str) -> None:
    with pytest.raises(SpecError, match=message.replace("(", r"\(").replace(")", r"\)")):
        spec_parser.parse(text, "x")


@pytest.mark.skipif(not (CACHE / "InSim.txt").exists(), reason="run scripts/fetch_spec.py first")
def test_reads_the_whole_insim_specification() -> None:
    spec = spec_parser.parse((CACHE / "InSim.txt").read_text(encoding="utf-8"), "InSim.txt")
    assert spec.constants["INSIM_VERSION"].value == 10
    assert len(spec.structs) == 81
    assert len(spec.enums) == 30
    packet_types = spec.enums[0]
    assert packet_types.members[0].name == "ISP_NONE"
    # every IS_ packet with a Type field has an ISP_ value of the same name
    isp = {m.name for m in packet_types.members}
    for struct in spec.structs.values():
        if struct.fields and struct.fields[0].name == "Size" and struct.name.startswith("IS_"):
            assert "ISP_" + struct.name[3:] in isp, struct.name


@pytest.mark.skipif(not (CACHE / "OutSimPack.txt").exists(), reason="needs LFS's OutSimPack.txt")
def test_reads_the_whole_outsim_specification() -> None:
    text = (CACHE / "OutSimPack.txt").read_text(encoding="utf-8")
    spec = spec_parser.parse(text, "OutSimPack.txt")
    pack = spec.structs["OutSimPack2"]
    assert pack.fields[0].condition == "OSO_HEADER"
    assert pack.fields[-1].condition == "OSO_EXTRA_1"
