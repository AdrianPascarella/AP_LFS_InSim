"""Conversion between LFS text bytes and str (internal).

LFS text is a sequence of bytes in a Windows code page that can change inside the string: ^L, ^E,
^T, ^B, ^J, ^C, ^G, ^H, ^S and ^K switch to the code page listed at the end of InSim.txt. Those
switches are an encoding detail, so they are removed when reading and added back when writing.
Every other ^ code stays in the str exactly as LFS sends it: colours (^0 to ^9, ^:) and escaped
characters (^^, ^v, ^d...). Keeping them makes the str unambiguous: "^^1" is a caret and a 1,
"^1" is red.

Two codes also change the code page, and stay in the str (Scawen, lfs.net forum thread "Any
urgent InSim requests?", post 460437, 2007): ^8 returns to the original colour and code page, ^:
to the original colour and Latin-1. The original code page is Latin-1, except in IS_MSO, where
MSOData says which one it is (0.8C27).

In the double-byte code pages (J, H, S, K), the second byte of a character can be 0x5E, the same
byte as ^, so the bytes are walked character by character and never searched for ^.
"""

from __future__ import annotations

from lfs_insim.packets._enums import LID

# LFS code page letter -> (LID, Python codec), as listed in InSim.txt.
CODE_PAGES: dict[str, tuple[LID, str]] = {
    "L": (LID.LATIN, "cp1252"),
    "E": (LID.EUROPEAN, "cp1250"),
    "T": (LID.TURKISH, "cp1254"),
    "B": (LID.BALTIC, "cp1257"),
    "J": (LID.JAPANESE, "cp932"),
    "C": (LID.CYRILLIC, "cp1251"),
    "G": (LID.GREEK, "cp1253"),
    "H": (LID.TRADITIONAL_CHINESE, "cp950"),
    "S": (LID.SIMPLIFIED_CHINESE, "cp936"),
    "K": (LID.KOREAN, "cp949"),
}
_LETTERS = {lid: letter for letter, (lid, _) in CODE_PAGES.items()}
_CODECS = {lid: codec for lid, codec in CODE_PAGES.values()}
_SWITCHES = {ord(letter): lid for letter, (lid, _) in CODE_PAGES.items()}
CARET = 0x5E


def _is_lead_byte(byte: int, codec: str) -> bool:
    """True if `byte` starts a two-byte character: it does not decode alone, but with a second."""
    try:
        bytes([byte]).decode(codec)
    except UnicodeDecodeError:
        pass
    else:
        return False
    for second in range(0x40, 0x100):
        try:
            bytes([byte, second]).decode(codec)
        except UnicodeDecodeError:
            continue
        return True
    return False


# Bytes that start a two-byte character, per code page (empty for the single-byte ones).
_LEAD_BYTES: dict[LID, frozenset[int]] = {
    lid: frozenset(b for b in range(0x80, 0x100) if _is_lead_byte(b, codec))
    for lid, codec in _CODECS.items()
}
# Where encode() looks for a character the current code page lacks: the single-byte code pages
# first, so Cyrillic and Greek get ^C and ^G even though the Japanese one has them too.
_SEARCH_ORDER = sorted(_CODECS, key=lambda lid: (bool(_LEAD_BYTES[lid]), lid))


def code_page(value: int) -> LID:
    """The LID in the low 4 bits of a byte like MSOData; Latin-1 if it is not a known one."""
    try:
        return LID(value & 0x0F)
    except ValueError:
        return LID.LATIN


def decode(data: bytes, start: LID = LID.LATIN) -> str:
    """LFS bytes (without the zero terminator) -> str. `start` is the original code page."""
    parts: list[str] = []
    run = bytearray()  # bytes in the current code page, decoded together
    current = start
    i = 0
    while i < len(data):
        byte = data[i]
        if byte in _LEAD_BYTES[current] and i + 1 < len(data):
            run += data[i : i + 2]
            i += 2
            continue
        if byte == CARET and i + 1 < len(data):
            code = data[i + 1]
            if code in _SWITCHES or code in b"8:":
                parts.append(run.decode(_CODECS[current], errors="replace"))
                run.clear()
                if code in _SWITCHES:
                    current = _SWITCHES[code]
                else:
                    current = start if code == ord("8") else LID.LATIN
                    parts.append("^" + chr(code))
            else:
                run += data[i : i + 2]  # colour or escaped character: ^^L is not a switch
            i += 2
            continue
        run.append(byte)
        i += 1
    parts.append(run.decode(_CODECS[current], errors="replace"))
    return "".join(parts)


def encode(text: str, start: LID = LID.LATIN) -> bytes:
    """str -> LFS bytes. A switch is added before each character the current code page lacks;
    characters that no code page has become '?'."""
    out = bytearray()
    current = start
    i = 0
    while i < len(text):
        char = text[i]
        if char == "^" and i + 1 < len(text) and text[i + 1].isascii():
            code = text[i + 1]
            out += ("^" + code).encode("ascii")
            if code in CODE_PAGES:  # a switch written by hand: follow it
                current = CODE_PAGES[code][0]
            elif code == "8":
                current = start
            elif code == ":":
                current = LID.LATIN
            i += 2
            continue
        try:
            out += char.encode(_CODECS[current])
        except UnicodeEncodeError:
            for lid in _SEARCH_ORDER:
                try:
                    raw = char.encode(_CODECS[lid])
                except UnicodeEncodeError:
                    continue
                out += b"^" + _LETTERS[lid].encode("ascii") + raw
                current = lid
                break
            else:
                out += b"?"
        i += 1
    return bytes(out)
