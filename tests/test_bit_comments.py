"""Bits named only in a field's comment become an IntFlag (W6.6, W6.8): IS_NPL.PType -> PTYPE."""

import pytest
from generate_enums import bit_members
from spec_parser import SpecError

from lfs_insim.packets import HCPF, IS_NPL, NCNF, PTYPE, SCHF, unpack_insim


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
    members = bit_members("HCPF", comment, 1)
    assert [(m.name, m.value) for m in members] == [
        ("HCPF_SET_MASS", 1),
        ("HCPF_SET_TRES", 2),
        ("HCPF_SILENT", 128),
    ]
    assert members[1].comment == "bit 1: set TRes (e.g. Flags=3 to set both)"


def test_the_other_fields_with_bits_in_their_comment() -> None:
    assert int(NCNF.REMOTE) == 4
    assert SCHF.SHIFT | SCHF.CTRL == 3
    assert HCPF.SET_MASS | HCPF.SET_TRES == 3 and int(HCPF.SILENT) == 0x80


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
