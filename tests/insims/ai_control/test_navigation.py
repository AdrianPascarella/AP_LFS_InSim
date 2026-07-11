"""
Tests de CARACTERIZACIÓN de _NavigationMixin (insims/ai_control/navigation.py).

Congelan el comportamiento ACTUAL de la lógica DETERMINISTA de navegación antes
de tocar nada (red de seguridad, MODUS_OPERANDI §3):

  - Geometría pura: `_get_closest_node_index`, `_get_indicator_to_use`,
    `_is_link_reachable_ahead`.
  - Planificación de enlaces: `_get_raw_candidates`, `_calculate_next_link`,
    `_plan_next_link` (sobre un grafo sintético poblado en el MapRecorder real).

NO se cubren aquí los grandes métodos de integración con estado y tiempo
(`_update_route_navigation`, `_update_freeroam_navigation`, `_get_radar_speed_limit`):
usan `time.time()` y mutan mucho estado; se abordan más adelante.

Nota sobre densidad de nodos: `_is_link_reachable_ahead` (que `_calculate_next_link`
usa con max_dist=8) hace un culling rápido de radio ~38 m medido desde el nodo de
INICIO de cada segmento. Por eso las vías de estos tests se trazan con nodos densos
(cada 10 m, como una vía grabada de verdad); con nodos muy separados un enlace
alcanzable podría quedar fuera del culling. Ese comportamiento queda fijado por los
tests directos de `_is_link_reachable_ahead`.

Convenciones LFS relevantes (mismas que test_physics):
  - Ejes de mundo: +Y = Norte, +X = Oeste.
  - `_get_indicator_to_use` decide por el signo de un producto cruzado 2D; estos
    tests fijan ese signo TAL CUAL lo produce hoy el código.
"""

from types import SimpleNamespace

import pytest

from insims.ai_control import navigation
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from lfs_insim.insim_enums import CSVAL

OFF = CSVAL.INDICATORS.OFF
LEFT = CSVAL.INDICATORS.LEFT
RIGHT = CSVAL.INDICATORS.RIGHT


def _straight_y(x, y_start, y_end, step=10):
    """Puntos (x, y) de una vía recta en Y, de y_start a y_end (incl.) cada `step` m."""
    n = int(round((y_end - y_start) / step))
    return [(x, y_start + i * step) for i in range(n + 1)]


# ─── _get_closest_node_index: nodo más cercano (índice, distancia) ────────────


class TestGetClosestNodeIndex:
    def test_devuelve_indice_y_distancia_del_mas_cercano(self, ai_control, make_coords):
        nodes = [
            make_coords(0, 0),
            make_coords(0, 10),
            make_coords(0, 20),
            make_coords(0, 30),
        ]
        idx, dist = ai_control._get_closest_node_index(0.0, 21.0, nodes)
        assert idx == 2
        assert dist == pytest.approx(1.0)

    def test_punto_sobre_un_nodo_da_distancia_cero(self, ai_control, make_coords):
        nodes = [make_coords(0, 0), make_coords(0, 10), make_coords(0, 20)]
        idx, dist = ai_control._get_closest_node_index(0.0, 10.0, nodes)
        assert idx == 1
        assert dist == pytest.approx(0.0)

    def test_empate_gana_el_indice_menor(self, ai_control, make_coords):
        # Equidistante de (0,0) y (0,10): el `<` estricto conserva el PRIMERO.
        nodes = [make_coords(0, 0), make_coords(0, 10)]
        idx, dist = ai_control._get_closest_node_index(0.0, 5.0, nodes)
        assert idx == 0
        assert dist == pytest.approx(5.0)

    def test_busqueda_es_2d_ignora_la_z(self, ai_control, make_coords):
        # Solo cuenta hypot(x, y): la Z no influye en la distancia.
        nodes = [make_coords(0, 0, 0), make_coords(0, 0, 100)]
        idx, dist = ai_control._get_closest_node_index(0.0, 0.0, nodes)
        assert idx == 0
        assert dist == pytest.approx(0.0)

    def test_lista_vacia_devuelve_cero_e_infinito(self, ai_control):
        idx, dist = ai_control._get_closest_node_index(0.0, 0.0, [])
        assert idx == 0
        assert dist == float("inf")


# ─── _get_indicator_to_use: producto cruzado → intermitente ───────────────────


class TestGetIndicatorToUse:
    def test_menos_de_dos_nodos_propios_da_off(self, ai_control, make_coords):
        my = [make_coords(0, 0)]
        other = [make_coords(5, 0)]
        assert ai_control._get_indicator_to_use(my, other, 0) == OFF

    def test_carril_destino_sin_nodos_da_off(self, ai_control, make_coords):
        my = [make_coords(0, 0), make_coords(0, 10)]
        assert ai_control._get_indicator_to_use(my, [], 0) == OFF

    def test_destino_a_x_positiva_da_right(self, ai_control, make_coords):
        # Avanzando hacia +Y con el otro carril a +X → cross < 0 → RIGHT (comportamiento actual).
        my = [make_coords(0, 0), make_coords(0, 10)]
        other = [make_coords(5, 0)]
        assert ai_control._get_indicator_to_use(my, other, 0) == RIGHT

    def test_destino_a_x_negativa_da_left(self, ai_control, make_coords):
        my = [make_coords(0, 0), make_coords(0, 10)]
        other = [make_coords(-5, 0)]
        assert ai_control._get_indicator_to_use(my, other, 0) == LEFT

    def test_destino_colineal_da_off(self, ai_control, make_coords):
        my = [make_coords(0, 0), make_coords(0, 10)]
        other = [make_coords(0, 20)]
        assert ai_control._get_indicator_to_use(my, other, 0) == OFF

    def test_sentido_contrario_invierte_el_lado(self, ai_control, make_coords):
        # Mismo carril destino a +X, pero is_opposing invierte el vector fwd → LEFT.
        my = [make_coords(0, 0), make_coords(0, 10)]
        other = [make_coords(5, 0)]
        assert ai_control._get_indicator_to_use(my, other, 0, is_opposing=True) == LEFT


# ─── _is_link_reachable_ahead: alcance espacial del enlace ────────────────────


class TestIsLinkReachableAhead:
    @staticmethod
    def _road(make_coords):
        return [
            make_coords(0, 0),
            make_coords(0, 20),
            make_coords(0, 40),
            make_coords(0, 60),
        ]

    def test_enlace_sobre_la_via_por_delante_es_alcanzable(
        self, ai_control, make_coords
    ):
        link = [make_coords(0, 40)]
        assert (
            ai_control._is_link_reachable_ahead(self._road(make_coords), 0, link)
            is True
        )

    def test_enlace_lejos_no_es_alcanzable(self, ai_control, make_coords):
        link = [make_coords(50, 40)]
        assert (
            ai_control._is_link_reachable_ahead(self._road(make_coords), 0, link)
            is False
        )

    def test_solo_cuenta_el_tramo_por_delante_del_indice(self, ai_control, make_coords):
        # El enlace está sobre (0,0), pero current_index=2 → remaining = nodos[2:] → no lo ve.
        link = [make_coords(0, 0)]
        assert (
            ai_control._is_link_reachable_ahead(self._road(make_coords), 2, link)
            is False
        )

    def test_respeta_max_dist_lateral(self, ai_control, make_coords):
        # Perpendicular al tramo x=0: 3 m entra (<=3.5 por defecto), 4 m no.
        road = self._road(make_coords)
        assert (
            ai_control._is_link_reachable_ahead(road, 0, [make_coords(3, 30)]) is True
        )
        assert (
            ai_control._is_link_reachable_ahead(road, 0, [make_coords(4, 30)]) is False
        )

    def test_listas_vacias_no_alcanzable(self, ai_control, make_coords):
        assert ai_control._is_link_reachable_ahead([], 0, [make_coords(0, 0)]) is False
        assert (
            ai_control._is_link_reachable_ahead(self._road(make_coords), 0, []) is False
        )


# ─── _get_raw_candidates: enlaces salientes en bruto ──────────────────────────


class TestGetRawCandidates:
    def test_recopila_roadlink_y_lateral(
        self, ai_control, make_road, make_road_link, make_lateral_link, populate_graph
    ):
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", [(0, 0), (0, 100)]),
                make_road("R2", [(0, 100), (0, 200)]),
                make_road("R3", [(5, 0), (5, 100)]),
            ],
            road_links=[make_road_link("R1", "R2", [(0, 100), (0, 120)])],
            lateral_links=[make_lateral_link("R1", "R3", [(2, 0), (2, 100)])],
        )
        got = {
            (cid, ctype, target)
            for cid, ctype, target, _ in ai_control._get_raw_candidates("R1")
        }
        assert got == {("R1->R2", "RoadLink", "R2"), ("R1<<>>R3", "LatLink", "R3")}

    def test_excluye_laterales_de_adelantamiento(
        self, ai_control, make_road, make_lateral_link, populate_graph
    ):
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", [(0, 0), (0, 100)]),
                make_road("R3", [(5, 0), (5, 100)]),
            ],
            lateral_links=[
                make_lateral_link("R1", "R3", [(2, 0), (2, 100)], made_to_overtake=True)
            ],
        )
        assert ai_control._get_raw_candidates("R1") == []

    def test_respeta_allow_a_to_b(
        self, ai_control, make_road, make_lateral_link, populate_graph
    ):
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", [(0, 0), (0, 100)]),
                make_road("R3", [(5, 0), (5, 100)]),
            ],
            lateral_links=[
                make_lateral_link("R1", "R3", [(2, 0), (2, 100)], allow_a_to_b=False)
            ],
        )
        assert ai_control._get_raw_candidates("R1") == []

    def test_direccion_b_a_a_cuando_current_es_road_b(
        self, ai_control, make_road, make_lateral_link, populate_graph
    ):
        # current = R3 = road_b; con allow_b_to_a el destino es road_a (R1).
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", [(0, 0), (0, 100)]),
                make_road("R3", [(5, 0), (5, 100)]),
            ],
            lateral_links=[make_lateral_link("R1", "R3", [(2, 0), (2, 100)])],
        )
        got = {
            (cid, ctype, target)
            for cid, ctype, target, _ in ai_control._get_raw_candidates("R3")
        }
        assert got == {("R1<<>>R3", "LatLink", "R1")}


# ─── _calculate_next_link: filtrado + elección del próximo enlace ─────────────


class TestCalculateNextLink:
    @staticmethod
    def _basic_graph(ai_control, make_road, make_road_link, populate_graph, **road2):
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", _straight_y(0, 0, 100)),
                make_road("R2", _straight_y(0, 100, 200), **road2),
            ],
            road_links=[make_road_link("R1", "R2", [(0, 100), (0, 120)])],
        )

    def test_unica_opcion_valida_se_elige(
        self, ai_control, make_road, make_road_link, populate_graph
    ):
        self._basic_graph(ai_control, make_road, make_road_link, populate_graph)
        assert ai_control._calculate_next_link("R1", None, 0) == ("R1->R2", "RoadLink")

    def test_via_actual_inexistente_devuelve_none(self, ai_control):
        assert ai_control._calculate_next_link("NOPE", None, 0) == (None, None)

    def test_sin_candidatos_devuelve_none(self, ai_control, make_road, populate_graph):
        populate_graph(
            ai_control.map_recorder, roads=[make_road("R1", _straight_y(0, 0, 100))]
        )
        assert ai_control._calculate_next_link("R1", None, 0) == (None, None)

    def test_destino_cerrado_se_descarta(
        self, ai_control, make_road, make_road_link, populate_graph
    ):
        self._basic_graph(
            ai_control, make_road, make_road_link, populate_graph, is_closed=True
        )
        assert ai_control._calculate_next_link("R1", None, 0) == (None, None)

    def test_enlace_inalcanzable_se_descarta(
        self, ai_control, make_road, make_road_link, populate_graph
    ):
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", _straight_y(0, 0, 100)),
                make_road("R2", _straight_y(0, 100, 200)),
            ],
            road_links=[
                make_road_link("R1", "R2", [(100, 100), (100, 120)])
            ],  # lejos de la vía
        )
        assert ai_control._calculate_next_link("R1", None, 0) == (None, None)

    def test_solo_opcion_de_retorno_se_usa(
        self, ai_control, make_road, make_road_link, populate_graph
    ):
        # El único enlace lleva a la vía de la que venimos (previous=R2) → es "retorno", pero se usa.
        self._basic_graph(ai_control, make_road, make_road_link, populate_graph)
        assert ai_control._calculate_next_link("R1", "R2", 0) == ("R1->R2", "RoadLink")

    def test_prefiere_no_retorno(
        self, ai_control, make_road, make_road_link, populate_graph
    ):
        # Dos salidas: a R2 (nueva) y a R3 (de donde venimos) → elige la de R2.
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", _straight_y(0, 0, 100)),
                make_road("R2", _straight_y(0, 100, 200)),
                make_road("R3", [(0, 100), (-100, 100)]),
            ],
            road_links=[
                make_road_link("R1", "R2", [(0, 100), (0, 120)]),
                make_road_link("R1", "R3", [(0, 100), (-20, 100)]),
            ],
        )
        assert ai_control._calculate_next_link("R1", "R3", 0) == ("R1->R2", "RoadLink")

    def test_varias_validas_congela_el_conjunto(
        self, ai_control, make_road, make_road_link, populate_graph, monkeypatch
    ):
        # Con dos opciones válidas la elección es aleatoria; parcheamos random.choice para
        # congelar el CONJUNTO de candidatos (la parte determinista) sin depender del RNG.
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", _straight_y(0, 0, 100)),
                make_road("R2", _straight_y(0, 100, 200)),
                make_road("R3", [(0, 100), (-100, 100)]),
            ],
            road_links=[
                make_road_link("R1", "R2", [(0, 100), (0, 120)]),
                make_road_link("R1", "R3", [(0, 100), (-20, 100)]),
            ],
        )
        captured = {}

        def fake_choice(seq):
            captured["seq"] = list(seq)
            return seq[0]

        monkeypatch.setattr(navigation, "random", SimpleNamespace(choice=fake_choice))
        result = ai_control._calculate_next_link("R1", None, 0)
        assert {(cid, ctype) for cid, ctype in captured["seq"]} == {
            ("R1->R2", "RoadLink"),
            ("R1->R3", "RoadLink"),
        }
        assert result == captured["seq"][0]


# ─── _plan_next_link: asignación del próximo enlace al estado del modo ─────────


class TestPlanNextLink:
    def test_sin_on_link_planifica_desde_current_road(
        self, ai_control, make_road, make_road_link, populate_graph
    ):
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", _straight_y(0, 0, 100)),
                make_road("R2", _straight_y(0, 100, 200)),
            ],
            road_links=[make_road_link("R1", "R2", [(0, 100), (0, 120)])],
        )
        mode = FreeroamMode(current_road_id="R1", previous_road_id=None, node_index=0)
        ai_control._plan_next_link(mode)
        assert (mode.next_link_id, mode.next_link_type) == ("R1->R2", "RoadLink")

    def test_current_road_none_es_no_op(self, ai_control):
        mode = FreeroamMode()  # current_road_id None por defecto → guarda de seguridad
        ai_control._plan_next_link(mode)
        assert mode.next_link_id is None
        assert mode.next_link_type is None

    def test_on_link_planifica_desde_la_via_destino(
        self, ai_control, make_road, make_road_link, make_coords, populate_graph
    ):
        # Venimos por R1->R2; al llegar a R2 se planifica el siguiente enlace (R2->R3).
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", _straight_y(0, 0, 100)),
                make_road("R2", _straight_y(0, 100, 200)),
                make_road("R3", _straight_y(0, 200, 300)),
            ],
            road_links=[
                make_road_link("R1", "R2", [(0, 100), (0, 120)]),
                make_road_link("R2", "R3", [(0, 200), (0, 220)]),
            ],
        )
        link_r1_r2 = ai_control.map_recorder.road_links["R1->R2"]
        mode = FreeroamMode(current_road_id="R2", previous_road_id="R1", node_index=0)
        ai_control._plan_next_link(mode, on_link=(link_r1_r2, make_coords(0, 100)))
        assert (mode.next_link_id, mode.next_link_type) == ("R2->R3", "RoadLink")


# ─── _is_dead_end_stop: watchdog de fin de vía sin salida (Fix S29) ───────────


class TestIsDeadEndStop:
    """Predicado del watchdog que decide si una IA está clavada en un fin de vía
    sin salida (mapa incompleto) y debe irse a espectadores."""

    def _mode_on_road(self, ai_control, make_road, populate_graph, **overrides):
        populate_graph(
            ai_control.map_recorder, roads=[make_road("R1", [(0, 0), (0, 50)])]
        )
        return FreeroamMode(current_road_id="R1", **overrides)

    def test_parada_sin_next_link_en_via_normal_es_fin_de_via(
        self, ai_control, make_road, populate_graph
    ):
        mode = self._mode_on_road(ai_control, make_road, populate_graph)
        mode.next_link_id = None
        assert ai_control._is_dead_end_stop(mode, speed_kmh=0.0) is True

    def test_con_next_link_es_parada_legitima_de_trafico(
        self, ai_control, make_road, populate_graph
    ):
        # Parada a 0 km/h PERO con salida planificada → espera de tráfico, no fin de vía.
        mode = self._mode_on_road(ai_control, make_road, populate_graph)
        mode.next_link_id = "R1->R2"
        assert ai_control._is_dead_end_stop(mode, speed_kmh=0.0) is False

    def test_en_movimiento_no_es_fin_de_via(
        self, ai_control, make_road, populate_graph
    ):
        mode = self._mode_on_road(ai_control, make_road, populate_graph)
        mode.next_link_id = None
        # Por encima del umbral (2 km/h) todavía se mueve.
        assert ai_control._is_dead_end_stop(mode, speed_kmh=5.0) is False

    def test_adelantando_nunca_es_fin_de_via(
        self, ai_control, make_road, populate_graph
    ):
        mode = self._mode_on_road(ai_control, make_road, populate_graph)
        mode.next_link_id = None
        for estado in ("OVERTAKING", "RETURNING"):
            mode.overtake_state = estado
            assert ai_control._is_dead_end_stop(mode, speed_kmh=0.0) is False

    def test_via_circular_sin_next_link_no_es_fin_de_via(
        self, ai_control, make_road, populate_graph
    ):
        # Una vía circular sin next_link da vueltas: no es un callejón sin salida.
        mode = self._mode_on_road(ai_control, make_road, populate_graph)
        ai_control.map_recorder.roads["R1"].is_circular = True
        mode.next_link_id = None
        assert ai_control._is_dead_end_stop(mode, speed_kmh=0.0) is False

    def test_sin_via_localizada_puede_sacarse(self, ai_control):
        # current_road_id None (nunca localizó, p. ej. spawn fuera del mapa): a 0
        # km/h y sin salida se considera sacable.
        mode = FreeroamMode()
        assert ai_control._is_dead_end_stop(mode, speed_kmh=0.0) is True
