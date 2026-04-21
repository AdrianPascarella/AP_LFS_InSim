"""Tests for utility functions: unit conversions, geometry, colors, PID."""
import math
import pytest
from lfs_insim.utils import (
    strip_lfs_colors,
    lfs_pos_to_meters,
    lfs_speed_to_kmh,
    lfs_angle_to_degrees,
    lfs_angvel_to_degrees_per_second,
    calc_dist_3d,
    get_heading_diff,
    calc_deviation_angle,
    calc_dist_point_to_segment_3d,
    PIDController,
)


class TestStripLfsColors:
    def test_removes_numeric_codes(self):
        assert strip_lfs_colors("^7Hello") == "Hello"

    def test_removes_multiple_codes(self):
        assert strip_lfs_colors("^2Hello ^7World") == "Hello World"

    def test_removes_letter_codes(self):
        assert strip_lfs_colors("^hHello^L") == "Hello"

    def test_no_codes_unchanged(self):
        assert strip_lfs_colors("Hello World") == "Hello World"

    def test_empty_string(self):
        assert strip_lfs_colors("") == ""

    def test_only_codes_becomes_empty(self):
        assert strip_lfs_colors("^0^1^2") == ""

    def test_double_caret_removed(self):
        assert strip_lfs_colors("^^") == ""

    def test_strips_surrounding_whitespace(self):
        assert strip_lfs_colors("  ^7Hello  ") == "Hello"

    def test_all_color_codes(self):
        text = "^0^1^2^3^4^5^6^7^8^9"
        assert strip_lfs_colors(text) == ""


class TestLfsPosToMeters:
    def test_one_meter(self):
        assert lfs_pos_to_meters(65536) == pytest.approx(1.0)

    def test_zero(self):
        assert lfs_pos_to_meters(0) == pytest.approx(0.0)

    def test_half_meter(self):
        assert lfs_pos_to_meters(32768) == pytest.approx(0.5)

    def test_reverse_one_meter(self):
        assert lfs_pos_to_meters(1.0, rev=True) == 65536

    def test_reverse_zero(self):
        assert lfs_pos_to_meters(0.0, rev=True) == 0

    def test_roundtrip(self):
        original = 131072
        assert lfs_pos_to_meters(lfs_pos_to_meters(original, rev=False), rev=True) == original


class TestLfsSpeedToKmh:
    def test_known_value(self):
        # 32768 units → 360 km/h
        assert lfs_speed_to_kmh(32768) == pytest.approx(360.0)

    def test_zero(self):
        assert lfs_speed_to_kmh(0) == pytest.approx(0.0)

    def test_reverse(self):
        assert lfs_speed_to_kmh(360, rev=True) == 32768

    def test_reverse_zero(self):
        assert lfs_speed_to_kmh(0, rev=True) == 0

    def test_roundtrip(self):
        units = 16384
        assert lfs_speed_to_kmh(lfs_speed_to_kmh(units), rev=True) == units


class TestLfsAngleToDegrees:
    def test_zero_angle(self):
        assert lfs_angle_to_degrees(0) == pytest.approx(0.0)

    def test_quarter_turn(self):
        # 16384 units → 90 degrees
        assert lfs_angle_to_degrees(16384) == pytest.approx(90.0, abs=0.01)

    def test_half_turn_negative(self):
        # 32768 units → -180 degrees (wraps to negative)
        assert lfs_angle_to_degrees(32768) == pytest.approx(-180.0, abs=0.01)

    def test_three_quarter_negative(self):
        # 49152 units → -90 degrees
        assert lfs_angle_to_degrees(49152) == pytest.approx(-90.0, abs=0.01)

    def test_reverse_zero(self):
        assert lfs_angle_to_degrees(0.0, rev=True) == 0

    def test_reverse_quarter(self):
        result = lfs_angle_to_degrees(90.0, rev=True)
        assert result == pytest.approx(16384, abs=2)

    def test_wraparound_65536(self):
        assert lfs_angle_to_degrees(65536) == pytest.approx(0.0, abs=0.01)


class TestLfsAngvelToDegPerSec:
    def test_known_value(self):
        # 16384 units → 360 deg/s
        assert lfs_angvel_to_degrees_per_second(16384) == pytest.approx(360.0)

    def test_zero(self):
        assert lfs_angvel_to_degrees_per_second(0) == pytest.approx(0.0)

    def test_reverse(self):
        assert lfs_angvel_to_degrees_per_second(360.0, rev=True) == 16384

    def test_roundtrip(self):
        units = 8192
        result = lfs_angvel_to_degrees_per_second(
            lfs_angvel_to_degrees_per_second(units), rev=True
        )
        assert result == units


class TestCalcDist3d:
    def test_3_4_5_triangle(self):
        assert calc_dist_3d(0, 0, 0, 3, 4, 0) == pytest.approx(5.0)

    def test_same_point(self):
        assert calc_dist_3d(1, 2, 3, 1, 2, 3) == pytest.approx(0.0)

    def test_along_z_axis(self):
        assert calc_dist_3d(0, 0, 0, 0, 0, 10) == pytest.approx(10.0)

    def test_symmetric(self):
        d1 = calc_dist_3d(1, 2, 3, 4, 5, 6)
        d2 = calc_dist_3d(4, 5, 6, 1, 2, 3)
        assert d1 == pytest.approx(d2)

    def test_unit_cube_diagonal(self):
        assert calc_dist_3d(0, 0, 0, 1, 1, 1) == pytest.approx(math.sqrt(3))


class TestGetHeadingDiff:
    def test_positive_diff(self):
        assert get_heading_diff(1000, 500) == 500

    def test_negative_diff(self):
        assert get_heading_diff(500, 1000) == -500

    def test_no_diff(self):
        assert get_heading_diff(1000, 1000) == 0

    def test_wraparound_short_path(self):
        # From 65000 to 100: shortest is +636, not -64900
        assert get_heading_diff(100, 65000) == 636

    def test_max_positive(self):
        # Exactly half circle forward
        assert get_heading_diff(32768, 0) == -32768

    def test_result_in_range(self):
        diff = get_heading_diff(10000, 60000)
        assert -32768 <= diff <= 32768


class TestCalcDeviationAngle:
    def test_straight_line(self):
        # Three collinear points: deviation = 0
        angle = calc_deviation_angle(0, 0, 100, 0, 200, 0)
        assert angle == 0

    def test_90_degree_left(self):
        # Turn left: (0,0) → (1,0) → (1,1)
        angle = calc_deviation_angle(0, 0, 1, 0, 1, 1)
        assert angle > 0

    def test_90_degree_right(self):
        # Turn right: (0,0) → (1,0) → (1,-1)
        angle = calc_deviation_angle(0, 0, 1, 0, 1, -1)
        assert angle < 0

    def test_180_u_turn(self):
        angle = calc_deviation_angle(0, 0, 1, 0, 0, 0)
        assert abs(angle) == 32768


class TestCalcDistPointToSegment3d:
    def test_point_on_segment(self):
        # Midpoint of segment from (0,0,0) to (10,0,0) is at (5,0,0)
        dist = calc_dist_point_to_segment_3d(5, 0, 0, 0, 0, 0, 10, 0, 0)
        assert dist == pytest.approx(0.0)

    def test_point_perpendicular(self):
        # Point at (5,3,0), segment from (0,0,0) to (10,0,0)
        dist = calc_dist_point_to_segment_3d(5, 3, 0, 0, 0, 0, 10, 0, 0)
        assert dist == pytest.approx(3.0)

    def test_point_before_segment(self):
        # Point at (-3,4,0), segment from (0,0,0) to (10,0,0) → closest is A=(0,0,0)
        dist = calc_dist_point_to_segment_3d(-3, 4, 0, 0, 0, 0, 10, 0, 0)
        assert dist == pytest.approx(5.0)

    def test_point_after_segment(self):
        # Point at (13,4,0), segment from (0,0,0) to (10,0,0) → closest is B=(10,0,0)
        dist = calc_dist_point_to_segment_3d(13, 4, 0, 0, 0, 0, 10, 0, 0)
        assert dist == pytest.approx(5.0)

    def test_degenerate_segment(self):
        # A == B (point segment): distance = distance from P to that point
        dist = calc_dist_point_to_segment_3d(3, 4, 0, 0, 0, 0, 0, 0, 0)
        assert dist == pytest.approx(5.0)


class TestPIDController:
    def test_zero_dt_returns_zero(self):
        pid = PIDController(kp=1.0, ki=0.0, kd=0.0)
        assert pid.update(10, 0, dt=0.0) == 0.0

    def test_proportional_only(self):
        pid = PIDController(kp=0.1, ki=0.0, kd=0.0)
        # error = 10 - 0 = 10, p = 0.1 * 10 = 1.0 → clamped to 1.0
        result = pid.update(target=10, current=0, dt=0.1)
        assert result == pytest.approx(1.0)

    def test_output_clamped_max(self):
        pid = PIDController(kp=100.0, ki=0.0, kd=0.0)
        result = pid.update(target=100, current=0, dt=0.1)
        assert result == pytest.approx(1.0)

    def test_output_clamped_min(self):
        pid = PIDController(kp=100.0, ki=0.0, kd=0.0)
        result = pid.update(target=-100, current=0, dt=0.1)
        assert result == pytest.approx(-1.0)

    def test_custom_output_limits(self):
        pid = PIDController(kp=1.0, ki=0.0, kd=0.0, out_min=-0.5, out_max=0.5)
        result = pid.update(target=10, current=0, dt=0.1)
        assert result == pytest.approx(0.5)

    def test_no_derivative_kick_on_first_run(self):
        # On first run, prev_current is set to current, so d_term = 0
        pid = PIDController(kp=0.0, ki=0.0, kd=10.0)
        result = pid.update(target=0, current=5, dt=0.1)
        assert result == pytest.approx(0.0)

    def test_derivative_on_second_run(self):
        pid = PIDController(kp=0.0, ki=0.0, kd=1.0)
        pid.update(target=0, current=0, dt=0.1)    # first run: sets prev_current=0
        result = pid.update(target=0, current=1, dt=0.1)  # current increased by 1
        # d_term = -kd * (current - prev) / dt = -1.0 * (1 - 0) / 0.1 = -10 → clamped -1.0
        assert result == pytest.approx(-1.0)

    def test_reset_clears_state(self):
        pid = PIDController(kp=0.0, ki=1.0, kd=0.0)
        pid.update(target=10, current=0, dt=1.0)  # builds up integral
        pid.reset()
        assert pid.integral == 0.0
        assert pid.first_run is True

    def test_anti_windup_clamps_integral(self):
        pid = PIDController(kp=0.0, ki=1.0, kd=0.0)
        # Run many iterations with large error — integral should not grow beyond limits
        for _ in range(100):
            result = pid.update(target=100, current=0, dt=0.1)
        assert result == pytest.approx(1.0)
        # Integral clamped: ki * integral <= out_max → integral <= 1.0
        assert pid.integral <= 1.0
