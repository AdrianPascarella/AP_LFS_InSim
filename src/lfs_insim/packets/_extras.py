"""Hand-written additions to generated packets.

scripts/generate_packets.py adds each class here as a base of the packet that EXTRAS in
scripts/spec_overrides.py names. They hold properties only, never fields: the fields and the
binary layout come from the specification.
"""

from __future__ import annotations

from lfs_insim import units


class MSOText:
    """For IS_MSO: the text that the user typed."""

    Msg: str
    TextStart: int

    @property
    def text(self) -> str:
        """What the user typed, without the "Name : " that LFS puts before it.

        For a system message (UserType 0) it is the whole message. LFS's ^ codes (colours...)
        are kept, as in Msg: `lfs_insim.text.strip_colours()` removes the colours.
        """
        return self.Msg[self.TextStart :]


class CompCarUnits:
    """For CompCar (in IS_MCI): position, speed and angles in metres, m/s, km/h and degrees."""

    X: int
    Y: int
    Z: int
    Speed: int
    Direction: int
    Heading: int
    AngVel: int

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

    @property
    def speed_mps(self) -> float:
        """Speed in m/s."""
        return units.speed_to_mps(self.Speed)

    @property
    def speed_kmh(self) -> float:
        """Speed in km/h."""
        return units.mps_to_kmh(self.speed_mps)

    @property
    def direction_deg(self) -> float:
        """Direction of motion in degrees (0 to 360, anticlockwise from the world's Y axis)."""
        return units.angle_to_degrees(self.Direction)

    @property
    def heading_deg(self) -> float:
        """Direction the car points to, in degrees (0 to 360, anticlockwise from Y)."""
        return units.angle_to_degrees(self.Heading)

    @property
    def angvel_dps(self) -> float:
        """Rate of turn in degrees per second (anticlockwise positive)."""
        return units.angvel_to_degrees(self.AngVel)


class ContactUnits:
    """For CarContact and CarContOBJ (IS_CON, IS_OBH, IS_HLV): their own, smaller scales."""

    X: int
    Y: int
    Speed: int
    Direction: int
    Heading: int

    @property
    def x_m(self) -> float:
        """X in metres (16 = 1 metre here)."""
        return self.X / 16

    @property
    def y_m(self) -> float:
        """Y in metres (16 = 1 metre here)."""
        return self.Y / 16

    @property
    def speed_kmh(self) -> float:
        """Speed in km/h (Speed is in m/s)."""
        return units.mps_to_kmh(self.Speed)

    @property
    def direction_deg(self) -> float:
        """Direction of motion in degrees (128 = 180 degrees here)."""
        return self.Direction * 360 / 256

    @property
    def heading_deg(self) -> float:
        """Direction the car points to, in degrees (128 = 180 degrees here)."""
        return self.Heading * 360 / 256


class ClosingSpeed:
    """For IS_CON and IS_OBH: the closing speed of the contact."""

    SpClose: int

    @property
    def closing_speed_mps(self) -> float:
        """Closing speed in m/s (the low 12 bits of SpClose; 10 = 1 m/s)."""
        return (self.SpClose & 0x0FFF) / 10


class GaugeUnits:
    """For OutGaugePack: the speed in km/h and mph."""

    Speed: float

    @property
    def speed_kmh(self) -> float:
        """Speed in km/h (Speed is in m/s)."""
        return units.mps_to_kmh(self.Speed)

    @property
    def speed_mph(self) -> float:
        """Speed in miles per hour."""
        return units.mps_to_mph(self.Speed)
