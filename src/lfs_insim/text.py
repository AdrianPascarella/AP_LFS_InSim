"""Helpers for LFS text.

Text fields arrive as str with LFS's ^ codes kept, exactly as LFS sends them: colours (^0 to ^9,
^:) and escaped characters (^^ for ^, ^v for |, ...). Code page switches (^L, ^J, ...) are not
there: the library has already turned the bytes into the right characters.
"""

from __future__ import annotations

import re

__all__ = ["plain", "strip_colours"]

_CODE = re.compile(r"\^(.)", re.DOTALL)
_COLOURS = "0123456789:"
# The characters LFS writes as ^ and a letter (the same table as InSim.NET's LfsUnicodeEncoding).
_ESCAPES = {
    "v": "|",
    "a": "*",
    "c": ":",
    "d": "\\",
    "s": "/",
    "q": "?",
    "t": '"',
    "l": "<",
    "r": ">",
    "h": "#",
    "^": "^",
}


def strip_colours(text: str) -> str:
    """Remove the colour codes from LFS text: '^1Red ^7car' -> 'Red car'.

    Other ^ codes stay, so '^^1' (a caret followed by 1) is left alone.
    """
    return _CODE.sub(lambda match: "" if match[1] in _COLOURS else match[0], text)


def plain(text: str) -> str:
    """LFS text as LFS shows it, without colours: '^4^h773 ^7Bob' -> '#773 Bob'.

    For printing or saving. The escaped characters become what they stand for (^h is #, ^v is
    |, ^^ is ^...), so the result cannot be sent back to LFS as it is.
    """

    def readable(match: re.Match[str]) -> str:
        code = match[1]
        return "" if code in _COLOURS else _ESCAPES.get(code, match[0])

    return _CODE.sub(readable, text)
