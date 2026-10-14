"""Bits named only in a field's comment become an IntFlag (W6.6): IS_NPL.PType -> PTYPE."""

import pytest
from generate_enums import bit_members
from spec_parser import SpecError

from lfs_insim.packets import IS_NPL, PTYPE, unpack_insim


def test_the_bits_are_read_from_the_comment() -> None:
    members = bit_members("PTYPE", "bit 0: female / bit 1: AI / bit 2: remote", 1)
    assert [(m.name, m.value) for m in members] == [
        ("PTYPE_FEMALE", 1),
        ("PTYPE_AI", 2),
        ("PTYPE_REMOTE", 4),
    ]
    assert bit_members("X", "bit 0: set Mass", 1)[0].name == "X_SET_MASS"


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
