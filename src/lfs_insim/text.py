"""Helpers for LFS text.

Text fields arrive as str with LFS's ^ codes kept, exactly as LFS sends them: colours (^0 to ^9,
^:) and escaped characters (^^ for ^, ^v for |, ...). Code page switches (^L, ^J, ...) are not
there: the library has already turned the bytes into the right characters.
"""

from __future__ import annotations

import re

__all__ = ["strip_colours"]

_CODE = re.compile(r"\^(.)", re.DOTALL)


def strip_colours(text: str) -> str:
    """Remove the colour codes from LFS text: '^1Red ^7car' -> 'Red car'.

    Other ^ codes stay, so '^^1' (a caret followed by 1) is left alone.
    """
    return _CODE.sub(lambda match: "" if match[1] in "0123456789:" else match[0], text)
