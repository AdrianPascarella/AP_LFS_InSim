"""LFS text <-> str: code pages switched with ^L, ^J... and the ^ codes that stay in the str."""

from dataclasses import fields

import pytest

from lfs_insim.packets import IS_BTN, IS_MSO, IS_MST, ISP, LID, MSO
from lfs_insim.packets._text import decode, encode
from lfs_insim.text import plain, strip_colours


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


@pytest.mark.parametrize(
    ("text", "readable"),
    [
        ("^4^h773 ^7A.Pascarella", "#773 A.Pascarella"),  # a real name, seen in W4.7 (S12)
        ("^v^a^c^d^s^q^t^l^r^h^^", '|*:\\/?"<>#^'),  # every escape (as in InSim.NET's table)
        ("^^1", "^1"),  # a caret and a 1, not a colour
        ("^^^1x", "^x"),  # a caret, then red
        ("^8name^9 ^:x", "name x"),
        ("^zunknown ^", "^zunknown ^"),  # unknown codes and a lone caret stay
        ("Ελλάδα", "Ελλάδα"),
    ],
)
def test_plain_is_text_as_lfs_shows_it(text: str, readable: str) -> None:
    assert plain(text) == readable


def test_mso_text_start_is_an_index_into_the_str() -> None:
    # The name has a two-byte character and LFS adds code page switches (Scawen, post 460437):
    # TextStart counts bytes, up to "hi" after the last ^L.
    msg = b"^J\x82\xa0^L : ^Lhi"
    data = bytes([0, ISP.MSO, 0, 0, 0, 0, 1, msg.index(b"hi")]) + msg + b"\0"
    data = bytes([len(data + bytes(-len(data) % 4)) // 4]) + data[1:] + bytes(-len(data) % 4)
    packet = IS_MSO.unpack(data)
    assert packet.Msg == "あ : hi"
    assert packet.Msg[packet.TextStart :] == "hi"
    assert IS_MSO.unpack(packet.pack()) == packet


def test_mso_text_start_points_after_an_added_switch() -> None:
    packet = IS_MSO(TextStart=6, Msg="Bob : あ")
    data = packet.pack()
    assert data[8:] == b"Bob : ^J\x82\xa0\0\0"
    assert data[7] == 8  # after ^J, where the typed text starts
    assert IS_MSO.unpack(data) == packet


def _mso(user_type: int, text_start: int, msg: bytes) -> IS_MSO:
    data = bytes([0, ISP.MSO, 0, 0, 0, 0, user_type, text_start]) + msg + b"\0"
    data += bytes(-len(data) % 4)
    return IS_MSO.unpack(bytes([len(data) // 4]) + data[1:])


def test_mso_text_is_what_the_user_typed() -> None:
    # Shaped like the messages seen in the live test (S12): LFS puts ^L before the typed text.
    packet = _mso(MSO.USER, 11, b"^1Driver : ^Lhello ^G\xd9\xeb")
    assert packet.Msg == "^1Driver : hello Ωλ"
    assert packet.text == "hello Ωλ"


def test_mso_text_of_a_prefix_message_keeps_the_prefix() -> None:
    packet = _mso(MSO.PREFIX, 9, b"Driver : ^L!hello world")
    assert packet.text == "!hello world"


def test_mso_text_of_a_system_message_is_all_of_it() -> None:
    packet = _mso(MSO.SYSTEM, 0, b"Circuito no disponible")
    assert packet.text == packet.Msg == "Circuito no disponible"


def test_mso_text_is_not_a_field() -> None:
    assert "text" not in {f.name for f in fields(IS_MSO)}
    assert IS_MSO(TextStart=6, Msg="Bob : hi").text == "hi"


def test_mso_text_start_out_of_the_text_is_rejected() -> None:
    with pytest.raises(ValueError, match="not a position in Msg"):
        IS_MSO(TextStart=3, Msg="ab").pack()


def test_button_caption() -> None:
    # InSim.txt: 0-65-66-67-0-68-69-70-71-0-0-0 displays "DEFG" with caption "ABC".
    packet = IS_BTN(ReqI=1, TypeIn=10, Text="DEFG", Caption="ABC")
    data = packet.pack()
    assert data[12:] == bytes([0, 65, 66, 67, 0, 68, 69, 70, 71, 0, 0, 0])
    assert IS_BTN.unpack(data) == packet


def test_button_without_caption() -> None:
    data = IS_BTN(ReqI=1, Text="ABC").pack()
    assert data[12:] == bytes([65, 66, 67, 0])  # "65-66-67-0 would display button text ABC"
    assert IS_BTN.unpack(data) == IS_BTN(ReqI=1, Text="ABC")
    assert IS_BTN.unpack(IS_BTN(Caption="only").pack()) == IS_BTN(Caption="only")
