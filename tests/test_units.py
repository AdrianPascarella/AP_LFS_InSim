"""W8.3: lfs_insim.units and the unit properties of the packets, from the scales of InSim.txt."""

import math

import pytest

from lfs_insim import units
from lfs_insim.packets import (
    IS_CON,
    IS_OBH,
    CarContact,
    CarContOBJ,
    CompCar,
    OutGaugePack,
    Vec,
)

# The scales, as InSim.txt states them (CompCar, Vec, CarContact, CarContOBJ, IS_CON).


def test_positions_65536_is_one_metre() -> None:
    assert units.to_metres(65536) == 1.0
    assert units.to_metres(-32768) == -0.5
    assert units.from_metres(1.5) == 98304
    assert units.from_metres(units.to_metres(123456)) == 123456


def test_speed_32768_is_100_metres_per_second() -> None:
    assert units.speed_to_mps(32768) == 100.0
    assert units.mps_to_speed(50.0) == 16384


def test_angles_32768_is_180_degrees() -> None:
    assert units.angle_to_degrees(32768) == 180.0
    assert units.angle_to_degrees(16384) == 90.0
    assert units.degrees_to_angle(90.0) == 16384
    assert units.degrees_to_angle(-90.0) == 49152  # wraps: 0 to 65535
    assert units.degrees_to_angle(360.0) == 0


def test_angular_velocity_16384_is_360_degrees_per_second() -> None:
    assert units.angvel_to_degrees(16384) == 360.0
    assert units.angvel_to_degrees(8192) == 180.0  # NOTE 3 of CompCar says the same
    assert units.angvel_to_degrees(-8192) == -180.0
    assert units.degrees_to_angvel(-180.0) == -8192


def test_speed_units() -> None:
    assert units.mps_to_kmh(10.0) == pytest.approx(36.0)
    assert units.kmh_to_mps(36.0) == pytest.approx(10.0)
    assert units.mps_to_mph(0.44704) == pytest.approx(1.0)
    assert units.mph_to_mps(1.0) == pytest.approx(0.44704)


# Properties on the packets


def test_compcar_in_metres_kmh_and_degrees() -> None:
    car = CompCar(
        X=65536 * 10,
        Y=-65536 * 2,
        Z=32768,
        Speed=32768,
        Direction=16384,
        Heading=32768,
        AngVel=-4096,
    )
    assert (car.x_m, car.y_m, car.z_m) == (10.0, -2.0, 0.5)
    assert car.speed_mps == 100.0
    assert car.speed_kmh == pytest.approx(360.0)
    assert (car.direction_deg, car.heading_deg) == (90.0, 180.0)
    assert car.angvel_dps == -90.0


def test_vec_in_metres_both_ways() -> None:
    vec = Vec(X=65536, Y=-131072, Z=0)
    assert (vec.x_m, vec.y_m, vec.z_m) == (1.0, -2.0, 0.0)
    assert Vec.from_metres(1.0, -2.0, 0.25) == Vec(X=65536, Y=-131072, Z=16384)


def test_contacts_16_is_one_metre_and_128_is_180_degrees() -> None:
    for cls in (CarContact, CarContOBJ):
        contact = cls(X=160, Y=-8, Speed=10, Direction=64, Heading=128)
        assert (contact.x_m, contact.y_m) == (10.0, -0.5)
        assert contact.speed_kmh == pytest.approx(36.0)  # Speed is already m/s
        assert (contact.direction_deg, contact.heading_deg) == (90.0, 180.0)


def test_closing_speed_is_the_low_12_bits_with_10_per_metre_per_second() -> None:
    for cls in (IS_CON, IS_OBH):
        packet = cls(SpClose=0xF000 | 125)  # the high 4 bits are reserved
        assert packet.closing_speed_mps == 12.5


def test_outgauge_speed_in_kmh_and_mph() -> None:
    gauge = OutGaugePack(Speed=10.0)
    assert gauge.speed_kmh == pytest.approx(36.0)
    assert gauge.speed_mph == pytest.approx(10.0 / 0.44704)


def test_the_properties_do_not_change_the_fields_or_the_bytes() -> None:
    car = CompCar(X=1, Speed=2)
    assert CompCar.unpack(car.pack()) == car
    assert not math.isnan(car.x_m)
    with pytest.raises(AttributeError):
        car.x_m = 5.0  # type: ignore[misc]  # read only: set X
