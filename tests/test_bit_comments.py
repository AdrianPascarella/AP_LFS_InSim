"""Bits and values named only in a field's comment become an IntFlag or IntEnum (W6.6, W6.8,
W6.9): IS_NPL.PType -> PTYPE, IS_STA.Wind -> WIND."""

import enum

import pytest
import spec_overrides
import spec_parser
from generate_enums import bit_members, collect_enums, value_members
from spec_parser import SpecError

from lfs_insim.packets import (
    ACR,
    FLG,
    HLVC,
    IS_NPL,
    NCNF,
    OFFON,
    PLHF,
    PTYPE,
    SCHF,
    WIND,
    unpack_insim,
)


def test_the_bits_are_read_from_the_comment() -> None:
    members = bit_members("PTYPE", "bit 0: female / bit 1: AI / bit 2: remote", 1)
    assert [(m.name, m.value) for m in members] == [
        ("PTYPE_FEMALE", 1),
        ("PTYPE_AI", 2),
        ("PTYPE_REMOTE", 4),
    ]
    assert bit_members("X", "bit 0: set Mass", 1)[0].name == "X_SET_MASS"


def test_an_aside_in_brackets_is_not_part_of_the_name() -> None:
    comment = "bit 0: set Mass / bit 1: set TRes (e.g. Flags=3 to set both) / bit 7: silent"
    members = bit_members("PLHF", comment, 1)
    assert [(m.name, m.value) for m in members] == [
        ("PLHF_SET_MASS", 1),
        ("PLHF_SET_TRES", 2),
        ("PLHF_SILENT", 128),
    ]
    assert members[1].comment == "bit 1: set TRes (e.g. Flags=3 to set both)"


def test_the_other_fields_with_bits_in_their_comment() -> None:
    assert int(NCNF.REMOTE) == 4
    assert SCHF.SHIFT | SCHF.CTRL == 3
    assert PLHF.SET_MASS | PLHF.SET_TRES == 3 and int(PLHF.SILENT) == 0x80


@pytest.mark.parametrize("comment", ["female / AI", "bit 0: female / remote", "bit x: AI", ""])
def test_a_comment_that_changed_stops_the_generation(comment: str) -> None:
    with pytest.raises(SpecError, match="BIT_COMMENTS"):
        bit_members("PTYPE", comment, 1)


def test_ptype_of_a_remote_ai_player() -> None:
    packet = unpack_insim(IS_NPL(PLID=3, PType=PTYPE.AI | PTYPE.REMOTE).pack())
    assert isinstance(packet, IS_NPL)
    assert packet.PType & PTYPE.AI and packet.PType & PTYPE.REMOTE
    assert not packet.PType & PTYPE.FEMALE
    assert PTYPE(packet.PType) == PTYPE.AI | PTYPE.REMOTE


def test_the_values_are_read_from_the_comment() -> None:
    def read(comment: str) -> list[tuple[str, int]]:
        return [(m.name, m.value) for m in value_members("X", comment, 1)]

    assert read("0 = off / 1 = weak / 2 = strong") == [("X_OFF", 0), ("X_WEAK", 1), ("X_STRONG", 2)]
    assert read("1 - processed / 3 - unknown command") == [
        ("X_PROCESSED", 1),
        ("X_UNKNOWN_COMMAND", 3),
    ]
    assert read("0: ground / 5: out of bounds") == [("X_GROUND", 0), ("X_OUT_OF_BOUNDS", 5)]


@pytest.mark.parametrize("comment", ["0:demo / 1:S1 ...", "0 = unknown / > 1 = fail", "off / on"])
def test_a_comment_that_does_not_list_every_value_stops_the_generation(comment: str) -> None:
    with pytest.raises(SpecError, match="VALUE_COMMENTS"):
        value_members("X", comment, 1)


def test_the_value_classes() -> None:
    assert [m.name for m in WIND] == ["OFF", "WEAK", "STRONG"]
    # Values, not bits, although 3 = 1 | 2: an IntEnum, never an IntFlag
    assert not issubclass(ACR, enum.IntFlag) and int(ACR.UNKNOWN_COMMAND) == 3
    assert [m.name for m in FLG] == ["BLUE", "YELLOW"]  # "1 = given blue", renamed
    assert int(HLVC.OUT_OF_BOUNDS) == 5 and int(OFFON.ON) == 1


SHARED = """
struct IS_AAA // a
{
	byte	Size;		// 4
	byte	OffOn;		// 0 = off / 1 = on
};

struct IS_BBB // b
{
	byte	Size;		// 4
	byte	OffOn;		// %s
};
"""


def test_two_fields_share_a_class_only_with_the_same_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(spec_overrides, "BIT_COMMENTS", {})
    monkeypatch.setattr(
        spec_overrides, "VALUE_COMMENTS", {("IS_AAA", "OffOn"): "OO", ("IS_BBB", "OffOn"): "OO"}
    )
    shared = collect_enums(spec_parser.parse(SHARED % "0 = off / 1 = on", "x"))
    assert [c.fields for c in shared] == [["IS_AAA.OffOn", "IS_BBB.OffOn"]]
    with pytest.raises(SpecError, match="not the same values"):
        collect_enums(spec_parser.parse(SHARED % "0 = off / 2 = on", "x"))
