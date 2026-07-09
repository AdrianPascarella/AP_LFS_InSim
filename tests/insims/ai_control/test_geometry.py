"""Caracterización de la geometría/navegación específica de ai_control.

Estas funciones vivían en `lfs_insim.utils` (API pública del framework) y se mueven
a `insims/ai_control/nav_modes/freeroam/geometry.py` en W1 (Fase 6) porque son
específicas de la IA, no primitivas genéricas del framework.

Esta suite es la RED DE SEGURIDAD de esa extracción (MODUS_OPERANDI §3): congela el
comportamiento ACTUAL antes de mover el código. Durante la Fase 1 importa desde la
ubicación de origen (`lfs_insim.utils`); tras el move (Fase 2) el import apunta al
destino y estos mismos asserts deben seguir verdes (extracción sin cambio de lógica).
"""

from types import SimpleNamespace

import pytest

from insims.ai_control.nav_modes.freeroam.geometry import (
    apply_antilag_window,
    calc_deviation_angle,
    calc_dist_point_to_segment_3d,
    calc_target_heading,
    determine_smart_spawn_index,
    evaluate_dynamic_capture,
    get_closest_node_index,
    get_heading_diff,
    is_target_ahead_and_in_lane,
)


def _node(x_m: float, y_m: float, z_m: float = 0.0) -> SimpleNamespace:
    """Nodo mínimo con la interfaz que consumen las funciones (.x_m/.y_m/.z_m)."""
    return SimpleNamespace(x_m=x_m, y_m=y_m, z_m=z_m)


def _wp(x_m: float, y_m: float, z_m: float = 0.0) -> SimpleNamespace:
    """Waypoint: envuelve un nodo en `.coordinates` (rama is_waypoint=True)."""
    return SimpleNamespace(coordinates=_node(x_m, y_m, z_m))


# ─── get_heading_diff (movida de test_utils.py) ──────────────────────────────


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


# ─── calc_deviation_angle (movida de test_utils.py) ──────────────────────────


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


# ─── calc_dist_point_to_segment_3d (movida de test_utils.py) ─────────────────


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


# ─── calc_target_heading (nueva cobertura) ───────────────────────────────────
# LFS: +Y es Norte (heading 0), +X es Oeste. atan2(dx, dy) con dx=cur-tgt, dy=tgt-cur.


class TestCalcTargetHeading:
    def test_target_north_is_zero(self):
        # Objetivo al Norte (+Y): heading 0
        assert calc_target_heading(0, 0, 0, 10) == 0

    def test_target_south_is_half_turn(self):
        # Objetivo al Sur (-Y): media vuelta = 32768
        assert calc_target_heading(0, 0, 0, -10) == 32768

    def test_target_west_plus_x(self):
        # Objetivo a +X (Oeste): 3/4 de vuelta = 49152
        assert calc_target_heading(0, 0, 10, 0) == pytest.approx(49152, abs=1)

    def test_target_east_minus_x(self):
        # Objetivo a -X (Este): 1/4 de vuelta = 16384
        assert calc_target_heading(0, 0, -10, 0) == pytest.approx(16384, abs=1)

    def test_rev_adds_half_turn(self):
        # rev=True suma 32768 (para marcha atrás): Norte → Sur
        assert calc_target_heading(0, 0, 0, 10, rev=True) == 32768

    def test_returns_int(self):
        assert isinstance(calc_target_heading(0, 0, 5, 7), int)


# ─── get_closest_node_index (nueva cobertura) ────────────────────────────────


class TestGetClosestNodeIndex:
    def test_picks_nearest(self):
        nodes = [_node(0, 0), _node(0, 10), _node(0, 20)]
        assert get_closest_node_index(_node(0, 9), nodes) == 1

    def test_picks_first_on_tie(self):
        # Desempate estricto `<`: gana el primero en la lista
        nodes = [_node(0, 0), _node(0, 20)]
        assert get_closest_node_index(_node(0, 10), nodes) == 0

    def test_empty_list_returns_zero(self):
        assert get_closest_node_index(_node(0, 0), []) == 0

    def test_uses_3d_distance(self):
        nodes = [_node(0, 0, 100), _node(0, 0, 5)]
        assert get_closest_node_index(_node(0, 0, 0), nodes) == 1

    def test_waypoint_mode_reads_coordinates(self):
        wps = [_wp(0, 0), _wp(0, 10), _wp(0, 20)]
        assert get_closest_node_index(_node(0, 11), wps, is_waypoint=True) == 1


# ─── determine_smart_spawn_index (nueva cobertura) ───────────────────────────


class TestDetermineSmartSpawnIndex:
    def _nodes(self):
        return [_node(0, 0), _node(0, 10), _node(0, 20), _node(0, 30)]

    def test_advances_when_next_is_closer(self):
        # Más cerca del nodo 2 (y=20) que del 0 (y=0) → apunta al siguiente
        assert determine_smart_spawn_index(_node(0, 12), 1, self._nodes()) == 2

    def test_stays_when_prev_is_closer(self):
        # Más cerca del nodo 0 (y=0) que del 2 (y=20) → mantiene el closest
        assert determine_smart_spawn_index(_node(0, 8), 1, self._nodes()) == 1

    def test_single_node_returns_closest(self):
        assert determine_smart_spawn_index(_node(0, 0), 0, [_node(0, 0)]) == 0

    def test_non_waypoint_clamps_at_edges(self):
        # closest en el último índice: next se clampa a sí mismo (no da la vuelta)
        nodes = self._nodes()
        assert determine_smart_spawn_index(_node(0, 100), 3, nodes) == 3


# ─── apply_antilag_window (nueva cobertura) ──────────────────────────────────


class TestApplyAntilagWindow:
    def _nodes(self):
        return [_node(0, 0), _node(0, 10), _node(0, 20), _node(0, 30), _node(0, 40)]

    def test_recovers_forward_index(self):
        # current_idx=1 pero el coche está en y=32 → recupera el nodo 3 (y=30)
        assert apply_antilag_window(_node(0, 32), 1, self._nodes()) == 3

    def test_empty_list_returns_current(self):
        assert apply_antilag_window(_node(0, 0), 2, []) == 2

    def test_current_idx_past_end_returns_current(self):
        # current_idx >= total (no opposing) → devuelve current sin escanear
        assert apply_antilag_window(_node(0, 0), 5, self._nodes()) == 5

    def test_opposing_scans_backwards(self):
        # Sentido contrario: escanea hacia atrás desde current_idx
        assert (
            apply_antilag_window(
                _node(0, 8), 4, self._nodes(), is_driving_opposing=True
            )
            == 1
        )


# ─── evaluate_dynamic_capture (nueva cobertura) ──────────────────────────────


class TestEvaluateDynamicCapture:
    def _nodes(self):
        return [_node(0, 0), _node(0, 10), _node(0, 20)]

    def test_advances_when_inside_radius(self):
        # A parado (speed 0) el radio es min_radius=1.0; dist 0.5 < 1.0 → avanza
        assert evaluate_dynamic_capture(_node(0, 0.5), 0, self._nodes(), 0.0) == 1

    def test_stays_when_outside_radius(self):
        # dist 5 > radio 1.0 → mantiene el índice actual
        assert evaluate_dynamic_capture(_node(0, 5), 0, self._nodes(), 0.0) == 0

    def test_radius_grows_with_speed(self):
        # A 72 km/h (20 m/s): radio = min(10, 1 + 20*0.5)=10; dist 5 < 10 → avanza
        assert evaluate_dynamic_capture(_node(0, 5), 0, self._nodes(), 72.0) == 1

    def test_target_idx_past_end_returns_same(self):
        assert evaluate_dynamic_capture(_node(0, 0), 3, self._nodes(), 0.0) == 3

    def test_waypoint_wraps_to_zero(self):
        # is_waypoint: capturar el último nodo da la vuelta al índice 0
        wps = [_wp(0, 0), _wp(0, 10), _wp(0, 20)]
        assert (
            evaluate_dynamic_capture(_node(0, 20), 2, wps, 0.0, is_waypoint=True) == 0
        )


# ─── is_target_ahead_and_in_lane (nueva cobertura) ───────────────────────────
# OJO: función actualmente SIN uso en el código (candidata a revisión).


class TestIsTargetAheadAndInLane:
    def test_car_directly_ahead_is_dangerous(self):
        me = _node(0, 0)
        target = _node(0, 10)  # apunto al Norte
        other = _node(0, 5)  # coche justo delante, en carril
        dangerous, longitudinal, lateral = is_target_ahead_and_in_lane(
            me, target, other
        )
        assert dangerous is True
        assert longitudinal == pytest.approx(5.0)
        assert lateral == pytest.approx(0.0)

    def test_car_behind_is_not_dangerous(self):
        me = _node(0, 0)
        target = _node(0, 10)
        other = _node(0, -5)  # detrás
        dangerous, longitudinal, _ = is_target_ahead_and_in_lane(me, target, other)
        assert dangerous is False
        assert longitudinal == pytest.approx(5.0)

    def test_car_ahead_but_off_lane(self):
        # QUIRK caracterizado: si está delante pero fuera de carril (lateral ≥ 2.5),
        # la función NO reporta la distancia lateral real: devuelve lateral=0.0.
        # Solo se devuelve el lateral real cuando la detección es peligrosa (True).
        me = _node(0, 0)
        target = _node(0, 10)
        other = _node(5, 5)  # delante pero desviado lateralmente 5 m
        dangerous, _, lateral = is_target_ahead_and_in_lane(me, target, other)
        assert dangerous is False
        assert lateral == pytest.approx(0.0)

    def test_car_beyond_max_range(self):
        me = _node(0, 0)
        target = _node(0, 10)
        other = _node(0, 200)  # > max_ahead_dist (120)
        dangerous, longitudinal, lateral = is_target_ahead_and_in_lane(
            me, target, other
        )
        assert dangerous is False
        assert longitudinal == pytest.approx(200.0)
        assert lateral == pytest.approx(0.0)

    def test_degenerate_forward_vector(self):
        # target == posición propia → vector de avance nulo → no peligroso
        me = _node(0, 0)
        target = _node(0, 0)
        other = _node(0, 5)
        dangerous, _, _ = is_target_ahead_and_in_lane(me, target, other)
        assert dangerous is False
