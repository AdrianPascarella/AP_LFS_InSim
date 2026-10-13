"""Vector types that the specification uses but only describes in comments."""

from __future__ import annotations

from dataclasses import dataclass

from lfs_insim.packets._codec import Scalar
from lfs_insim.packets._structure import Structure


@dataclass(kw_only=True)
class Vec(Structure):
    """Position: 3 ints (X, Y, Z). 65536 means 1 metre."""

    X: int = 0
    Y: int = 0
    Z: int = 0

    _LAYOUT = (("X", Scalar("i")), ("Y", Scalar("i")), ("Z", Scalar("i")))


@dataclass(kw_only=True)
class Vector(Structure):
    """3 floats (X, Y, Z)."""

    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0

    _LAYOUT = (("X", Scalar("f")), ("Y", Scalar("f")), ("Z", Scalar("f")))
