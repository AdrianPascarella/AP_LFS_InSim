"""LFS text <-> str: code pages switched with ^L, ^J... and the ^ codes that stay in the str."""

import pytest

from lfs_insim.packets import IS_MSO, IS_MST, ISP, LID
from lfs_insim.packets._text import decode, encode
from lfs_insim.text import strip_colours


@pytest.mark.parametrize(
    ("text", "raw"),
    [
        ("hello", b"hello"),
        ("Ñandú", b"\xd1and\xfa"),  # Latin-1 is where every text starts
        ("Привет", b"^C\xcf\xf0\xe8\xe2\xe5\xf2"),
        ("Ελλάδα", b"^G\xc5\xeb\xeb\xdc\xe4\xe1"),
        ("çğ", b"\xe7^T\xf0"),  # switches only when the current code page lacks the character
        ("こんにちは", b"^J\x82\xb1\x82\xf1\x82\xc9\x82\xbf\x82\xcd"),
        ("한국", b"^K\xc7\xd1\xb1\xb9"),
        ("^1red ^7white", b"^1red ^7white"),
        ("^^1 ^v ^h", b"^^1 ^v ^h"),  # escaped characters stay escaped
    ],
)
def test_round_trip(text: str, raw: bytes) -> None:
    assert encode(text) == raw
    assert decode(raw) == text


def test_switches_are_removed_when_reading() -> None:
    assert decode(b"^L^Eab^Lc") == "abc"
    assert decode(b"^JD^Lsd") == "Dsd"


def test_caret_caret_is_not_a_switch() -> None:
    assert decode(b"^^L") == "^^L"
    assert encode("^^L") == b"^^L"


def test_second_byte_equal_to_caret_is_part_of_the_character() -> None:
    # In cp932, U+FF0F is 0x81 0x5E: its second byte is ^, so "^L" here is not a switch.
    assert "\uff0f".encode("cp932") == b"\x81^"
    assert decode(b"^J\x81^L") == "\uff0fL"
    assert encode("\uff0fL") == b"^J\x81^L"


def test_8_returns_to_the_original_code_page_and_colon_to_latin() -> None:
    # Scawen, lfs.net forum, post 460437: ^8 = original colour and code page, ^: = Latin-1.
    assert decode(b"^C\xcf^8\xcf", start=LID.CYRILLIC) == "П^8П"
    assert decode(b"^C\xcf^8\xcf") == "П^8Ï"
    assert decode(b"^C\xcf^:\xcf", start=LID.CYRILLIC) == "П^:Ï"
    assert encode("П^8П") == b"^C\xcf^8^C\xcf"
    assert encode("П^8П", start=LID.CYRILLIC) == b"\xcf^8\xcf"


def test_switch_typed_by_hand_is_followed() -> None:
    assert encode("^Cxп") == b"^Cx\xef"


def test_characters_without_a_code_page_become_question_marks() -> None:
    assert encode("a\U0001f600b") == b"a?b"


def test_mso_text_starts_in_the_code_page_of_msodata() -> None:
    # LFS 0.8C27: MSOData & 0x0f is the code page of the message (LID_x).
    data = bytes([3, ISP.MSO, 0, LID.CYRILLIC, 0, 0, 0, 0]) + b"\xcf\0\0\0"
    packet = IS_MSO.unpack(data)
    assert packet.Msg == "П"
    assert packet.pack() == data
    assert IS_MSO(Msg="П").pack()[8:] == b"^C\xcf\0"


def test_text_limit_counts_bytes_after_encoding() -> None:
    IS_MST(Msg="ж" * 61).pack()  # ^C + 61 bytes = 63, the limit
    with pytest.raises(ValueError, match="limit is 63"):
        IS_MST(Msg="ж" * 62).pack()


@pytest.mark.parametrize(
    ("text", "plain"),
    [
        ("^1Red ^7car", "Red car"),
        ("^8name^9 ^:x", "name x"),
        ("^^1", "^^1"),  # a caret and a 1, not a colour
        ("^vpipe", "^vpipe"),
        ("trailing ^", "trailing ^"),
    ],
)
def test_strip_colours(text: str, plain: str) -> None:
    assert strip_colours(text) == plain
