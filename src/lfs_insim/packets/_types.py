"""Vector types that the specification uses but only describes in comments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from lfs_insim import units
from lfs_insim.packets._codec import Scalar
from lfs_insim.packets._structure import Structure


@dataclass(kw_only=True)
class Vec(Structure):
    """Position: 3 ints (X, Y, Z). 65536 means 1 metre."""

    X: int = 0
    Y: int = 0
    Z: int = 0

    _LAYOUT = (("X", Scalar("i")), ("Y", Scalar("i")), ("Z", Scalar("i")))

    @classmethod
    def from_metres(cls, x: float, y: float, z: float) -> Self:
        """A position from metres: `Vec.from_metres(10.0, -2.5, 0.0)`."""
        return cls(X=units.from_metres(x), Y=units.from_metres(y), Z=units.from_metres(z))

    @property
    def x_m(self) -> float:
        """X in metres."""
        return units.to_metres(self.X)

    @property
    def y_m(self) -> float:
        """Y in metres."""
        return units.to_metres(self.Y)

    @property
    def z_m(self) -> float:
        """Z (altitude) in metres."""
        return units.to_metres(self.Z)


@dataclass(kw_only=True)
class Vector(Structure):
    """3 floats (X, Y, Z)."""

    X: float = 0.0
    Y: float = 0.0
    Z: float = 0.0

    _LAYOUT = (("X", Scalar("f")), ("Y", Scalar("f")), ("Z", Scalar("f")))
