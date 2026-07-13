"""Red del bloque 8.2 (Fase 8): predicados puros de la cesión de paso.

Kit de `traffic/yielding.py` (sin estado, sin LFS): tiempo-al-punto,
distancia hacia delante a lo largo de una vía, "¿cruzó la línea de
detención?" (punto de compromiso) y "¿apunta hacia?".

Semántica S38 a proteger:
- Un coche PARADO no es amenaza: tiempo-al-punto ⇒ ∞ (cambio deliberado
  respecto al modelo viejo, que le ponía un suelo de 0.5 m/s y lo contaba).
- Un coche que YA PASÓ el punto de unión (vía lineal) se ignora.
- Sobre la línea de detención todavía NO se ha cruzado: el compromiso
  exige estar estrictamente del lado del punto de unión.
"""

from __future__ import annotations

import math

from insims.ai_control.traffic.yielding import (
    DEFAULT_YIELD_TIME_S,
    forward_arc_dist_m,
    has_crossed_line,
    is_heading_towards,
    time_to_point_s,
)


def _heading_lfs(deg: float) -> int:
    """Grados LFS (0 = +Y, crece antihorario) → unidades enteras LFS."""
    return int(deg * 65536.0 / 360.0) % 65536


class TestTimeToPoint:
    def test_caso_normal_dist_entre_velocidad(self):
        assert time_to_point_s(20.0, 10.0) == 2.0

    def test_parado_es_infinito(self):
        assert time_to_point_s(5.0, 0.0) == math.inf

    def test_casi_parado_es_infinito(self):
        # Por debajo del umbral de parado (0.5 m/s) tampoco es amenaza
        assert time_to_point_s(5.0, 0.4) == math.inf

    def test_distancia_cero_o_negativa_es_tiempo_cero(self):
        # Ya está en el punto (o lo penetró): amenaza inmediata
        assert time_to_point_s(0.0, 10.0) == 0.0
        assert time_to_point_s(-3.0, 10.0) == 0.0


class TestForwardArcDist:
    """Distancia hacia DELANTE por la vía (índices de nodos, orden = sentido)."""

    def _recta(self, make_coords):
        # Nodos cada 10 m en Y (0..50)
        return [make_coords(0.0, i * 10.0) for i in range(6)]

    def test_lineal_hacia_delante(self, make_coords):
        nodes = self._recta(make_coords)
        assert forward_arc_dist_m(nodes, 0, 5) == 50.0
        assert forward_arc_dist_m(nodes, 2, 4) == 20.0

    def test_lineal_mismo_nodo_es_cero(self, make_coords):
        nodes = self._recta(make_coords)
        assert forward_arc_dist_m(nodes, 3, 3) == 0.0

    def test_lineal_ya_paso_devuelve_none(self, make_coords):
        # El coche está MÁS ALLÁ del punto de unión → no es amenaza
        nodes = self._recta(make_coords)
        assert forward_arc_dist_m(nodes, 4, 2) is None

    def test_circular_envuelve_por_el_cierre(self, make_coords):
        # Cuadrado de 10 m de lado; el cierre 3→0 es implícito (is_circular)
        nodes = [
            make_coords(0.0, 0.0),
            make_coords(10.0, 0.0),
            make_coords(10.0, 10.0),
            make_coords(0.0, 10.0),
        ]
        assert forward_arc_dist_m(nodes, 3, 1, is_circular=True) == 20.0
        # Hacia delante sin envolver funciona igual que en lineal
        assert forward_arc_dist_m(nodes, 0, 2, is_circular=True) == 20.0


class TestHasCrossedLine:
    """Línea vertical x=10; el punto de unión (ref) está en x=20 (más allá)."""

    def _linea(self, make_coords):
        return [make_coords(10.0, -5.0), make_coords(10.0, 5.0)]

    def test_antes_de_la_linea_no_ha_cruzado(self, make_coords):
        linea = self._linea(make_coords)
        assert has_crossed_line(5.0, 0.0, linea, 20.0, 0.0) is False

    def test_pasada_la_linea_ha_cruzado(self, make_coords):
        linea = self._linea(make_coords)
        assert has_crossed_line(15.0, 0.0, linea, 20.0, 0.0) is True

    def test_sobre_la_linea_aun_no_ha_cruzado(self, make_coords):
        # En la línea = detenido en la línea: el compromiso exige cruzarla
        linea = self._linea(make_coords)
        assert has_crossed_line(10.0, 0.0, linea, 20.0, 0.0) is False

    def test_linea_de_mas_de_dos_puntos_usa_la_cuerda(self, make_coords):
        # Polilínea con punto intermedio desviado: cuenta la cuerda 1º→último
        linea = [
            make_coords(10.0, -5.0),
            make_coords(11.0, 0.0),
            make_coords(10.0, 5.0),
        ]
        assert has_crossed_line(5.0, 0.0, linea, 20.0, 0.0) is False
        assert has_crossed_line(15.0, 0.0, linea, 20.0, 0.0) is True

    def test_sin_linea_no_se_cruza_nunca(self):
        assert has_crossed_line(15.0, 0.0, [], 20.0, 0.0) is False


class TestIsHeadingTowards:
    """Convención LFS: heading 0 = +Y; 90° = -X (crece antihorario)."""

    def test_apunta_al_objetivo(self):
        assert is_heading_towards(0.0, 0.0, _heading_lfs(0.0), 0.0, 10.0) is True

    def test_objetivo_a_la_espalda(self):
        assert is_heading_towards(0.0, 0.0, _heading_lfs(0.0), 0.0, -10.0) is False

    def test_convencion_lfs_90_grados_mira_a_menos_x(self):
        assert is_heading_towards(0.0, 0.0, _heading_lfs(90.0), -10.0, 0.0) is True
        assert is_heading_towards(0.0, 0.0, _heading_lfs(90.0), 10.0, 0.0) is False


class TestDefaults:
    def test_ventana_por_defecto_es_la_heredada_del_modelo_viejo(self):
        # 4 s: la misma que usaba _is_priority_vehicle_active_at_zone
        assert DEFAULT_YIELD_TIME_S == 4.0
