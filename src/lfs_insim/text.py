"""Helpers for LFS text.

Text fields arrive as str with LFS's ^ codes kept, exactly as LFS sends them: colours (^0 to ^9,
^:) and escaped characters (^^ for ^, ^v for |, ...). Code page switches (^L, ^J, ...) are not
there: the library has already turned the bytes into the right characters.

To send colours, put a Colour in the text: `insim.say(f"{Colour.RED}Stop{Colour.DEFAULT} now")`,
or `coloured("Stop", Colour.RED)`.
"""

from __future__ import annotations

import re
from enum import StrEnum

__all__ = ["Colour", "coloured", "plain", "strip_colours"]

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


class Colour(StrEnum):
    """The colour codes of LFS text, to put in what you send: f"{Colour.RED}Stop"."""

    BLACK = "^0"
    RED = "^1"
    GREEN = "^2"
    YELLOW = "^3"
    BLUE = "^4"
    MAGENTA = "^5"
    CYAN = "^6"
    WHITE = "^7"
    DEFAULT = "^8"
    """Back to the default colour."""


def coloured(text: str, colour: Colour) -> str:
    """The text in this colour, and the default colour after it: '^1Stop^8'."""
    if not isinstance(colour, Colour):
        raise TypeError(f"the colour must be a Colour (Colour.RED), not {colour!r}")
    return f"{colour}{text}{Colour.DEFAULT}"
