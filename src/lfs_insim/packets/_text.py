"""Conversion between LFS text bytes and str (internal).

Placeholder until W2.9: LFS switches code page inside a string with escape codes (^L, ^E, ...),
and this module will implement that. For now text is read and written as cp1252, which is what
LFS uses for Latin text (^L), so plain ASCII and Western European messages already work.
"""

from __future__ import annotations

ENCODING = "cp1252"


def encode(text: str) -> bytes:
    """str -> LFS bytes. Characters that cannot be represented become '?'."""
    return text.encode(ENCODING, errors="replace")


def decode(data: bytes) -> str:
    """LFS bytes (without the zero terminator) -> str."""
    return data.decode(ENCODING, errors="replace")
