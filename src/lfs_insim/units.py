"""LFS's units and everyday ones: metres, m/s, km/h, mph, degrees.

LFS sends positions, speeds and angles as whole numbers with a scale of their own; these functions
turn them into metres, m/s and degrees and back, with the scales InSim.txt gives for CompCar (in
IS_MCI) and Vec:

    position   65536 = 1 metre        to_metres(),        from_metres()
    speed      32768 = 100 m/s        speed_to_mps(),     mps_to_speed()
    angle      32768 = 180 degrees    angle_to_degrees(), degrees_to_angle()
    turn rate  16384 = 360 deg/s      angvel_to_degrees(), degrees_to_angvel()

Angles are anticlockwise from above, 0 along the world's Y axis. The packets have properties that
use them (`car.x_m`, `car.speed_kmh`, `car.heading_deg`...), so you seldom need these directly.
"""

from __future__ import annotations

__all__ = [
    "angle_to_degrees",
    "angvel_to_degrees",
    "degrees_to_angle",
    "degrees_to_angvel",
    "from_metres",
    "kmh_to_mps",
    "mph_to_mps",
    "mps_to_kmh",
    "mps_to_mph",
    "mps_to_speed",
    "speed_to_mps",
    "to_metres",
]

METRE = 65536
"""A position of 1 metre (CompCar X, Y, Z and Vec)."""
SPEED_100_MPS = 32768
"""A speed of 100 m/s (CompCar Speed)."""
HALF_TURN = 32768
"""An angle of 180 degrees (CompCar Direction and Heading)."""
TURN_PER_SECOND = 16384
"""A turn rate of 360 degrees per second (CompCar AngVel)."""
MPH = 0.44704
"""1 mile per hour, in m/s (exact)."""


def to_metres(value: int) -> float:
    """A position of LFS in metres: 65536 -> 1.0."""
    return value / METRE


def from_metres(metres: float) -> int:
    """Metres as an LFS position: 1.0 -> 65536."""
    return round(metres * METRE)


def speed_to_mps(value: int) -> float:
    """A CompCar speed in m/s: 32768 -> 100.0."""
    return value * 100 / SPEED_100_MPS


def mps_to_speed(mps: float) -> int:
    """m/s as a CompCar speed: 100.0 -> 32768."""
    return round(mps * SPEED_100_MPS / 100)


def angle_to_degrees(value: int) -> float:
    """An LFS angle (0 to 65535) in degrees (0 to 360): 32768 -> 180.0."""
    return value * 180 / HALF_TURN


def degrees_to_angle(degrees: float) -> int:
    """Degrees as an LFS angle, wrapped to 0-65535: 90.0 -> 16384, -90.0 -> 49152."""
    return round(degrees * HALF_TURN / 180) % (2 * HALF_TURN)


def angvel_to_degrees(value: int) -> float:
    """A CompCar AngVel in degrees per second: 16384 -> 360.0 (anticlockwise positive)."""
    return value * 360 / TURN_PER_SECOND


def degrees_to_angvel(degrees_per_second: float) -> int:
    """Degrees per second as a CompCar AngVel: 360.0 -> 16384."""
    return round(degrees_per_second * TURN_PER_SECOND / 360)


def mps_to_kmh(mps: float) -> float:
    """m/s in km/h."""
    return mps * 3.6


def kmh_to_mps(kmh: float) -> float:
    """km/h in m/s."""
    return kmh / 3.6


def mps_to_mph(mps: float) -> float:
    """m/s in miles per hour."""
    return mps / MPH


def mph_to_mps(mph: float) -> float:
    """Miles per hour in m/s."""
    return mph * MPH
