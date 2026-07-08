"""Equivalencia del índice espacial de roads con el barrido lineal (Fase 5).

`get_location_context` localiza el road más cercano. La optimización sustituye el
barrido O(nodos totales) por una consulta al `SpatialHashGrid`, pero DEBE devolver
EXACTAMENTE lo mismo que antes (misma distancia, mismo road, mismo desempate por
orden de dict). El oráculo es el propio `get_closest_geometry` sobre TODOS los
roads en orden de dict = el comportamiento antiguo literal.

El test central es un fuzz: muchos grafos y puntos aleatorios (dentro y fuera de
vía, con y sin roads cerradas) donde grid y oráculo deben coincidir al bit.
"""

from __future__ import annotations

import math
import random

import pytest


def _oracle(mr, px, py, pz, ignore_closed):
    """Barrido lineal antiguo: get_closest_geometry sobre TODOS los roads en
    orden de dict (filtrando cerradas si procede)."""
    items = (
        (rid, r) for rid, r in mr.roads.items() if not ignore_closed or not r.is_closed
    )
    return mr.get_closest_geometry(px, py, pz, items, lambda r: r.nodes)


def _random_polyline(rng, x0, y0, n, step_lo=5.0, step_hi=30.0):
    """Polilínea de n nodos que parte de (x0,y0) y camina en pasos aleatorios."""
    pts = [(x0, y0)]
    x, y = x0, y0
    for _ in range(n - 1):
        ang = rng.uniform(0, 6.283)
        d = rng.uniform(step_lo, step_hi)
        x += d * math.cos(ang)
        y += d * math.sin(ang)
        pts.append((x, y))
    return pts


def _build_random_map(mr, rng, make_road, populate_graph, n_roads=30):
    roads = []
    for i in range(n_roads):
        x0 = rng.uniform(0, 500)
        y0 = rng.uniform(0, 500)
        n_nodes = rng.randint(2, 15)
        closed = rng.random() < 0.25  # ~1/4 cerradas
        roads.append(
            make_road(
                f"R{i}",
                _random_polyline(rng, x0, y0, n_nodes),
                is_closed=closed,
            )
        )
    populate_graph(mr, roads=roads)


class TestEquivalenciaConBarridoLineal:
    @pytest.mark.parametrize("seed", range(8))
    def test_fuzz_grid_igual_que_oraculo(
        self, seed, ai_control, populate_graph, make_road
    ):
        rng = random.Random(seed)
        mr = ai_control.map_recorder
        _build_random_map(mr, rng, make_road, populate_graph, n_roads=30)

        for _ in range(200):
            # Puntos dentro del área de vías Y fuera (para ejercitar la expansión
            # de anillos y la terminación por cobertura de bloque).
            px = rng.uniform(-150, 650)
            py = rng.uniform(-150, 650)
            pz = rng.uniform(-2, 2)
            for ignore_closed in (False, True):
                grid = mr._get_closest_road(px, py, pz, ignore_closed)
                oracle = _oracle(mr, px, py, pz, ignore_closed)
                assert grid["id"] == oracle["id"], (
                    f"seed={seed} p=({px:.2f},{py:.2f}) ignore={ignore_closed}: "
                    f"grid={grid['id']} oracle={oracle['id']}"
                )
                # Misma distancia exacta (mismo segmento, misma cuenta).
                assert grid["dist"] == oracle["dist"]

    def test_get_location_context_completo_coincide(
        self, ai_control, populate_graph, make_road
    ):
        """El road_id / road_dist / road_node_idx del contexto completo también
        coinciden con el oráculo (no solo el helper interno)."""
        rng = random.Random(1234)
        mr = ai_control.map_recorder
        _build_random_map(mr, rng, make_road, populate_graph, n_roads=20)

        for _ in range(100):
            px = rng.uniform(-100, 600)
            py = rng.uniform(-100, 600)
            ctx = mr.get_location_context(
                px, py, 0.0, find_links=False, find_zones=False
            )
            oracle = _oracle(mr, px, py, 0.0, ignore_closed=False)
            assert ctx.road_id == oracle["id"]
            assert ctx.road_dist == oracle["dist"]


class TestCasosBorde:
    def test_road_de_un_solo_nodo(self, ai_control, populate_graph, make_road):
        """Un road con 1 nodo se trata como punto (igual que get_closest_geometry)."""
        mr = ai_control.map_recorder
        populate_graph(
            mr,
            roads=[
                make_road("PUNTO", [(100.0, 100.0)]),  # 1 nodo
                make_road("LINEA", [(0.0, 0.0), (0.0, 90.0)]),
            ],
        )
        # Pegado al punto → gana PUNTO.
        best = mr._get_closest_road(101.0, 100.0, 0.0, ignore_closed_roads=False)
        assert best["id"] == "PUNTO"
        assert best["dist"] == pytest.approx(1.0)

    def test_road_sin_nodos_se_ignora(self, ai_control, populate_graph, make_road):
        mr = ai_control.map_recorder
        populate_graph(
            mr,
            roads=[
                make_road("VACIA", []),  # sin nodos
                make_road("LINEA", [(0.0, 0.0), (0.0, 90.0)]),
            ],
        )
        best = mr._get_closest_road(5.0, 45.0, 0.0, ignore_closed_roads=False)
        assert best["id"] == "LINEA"

    def test_punto_muy_lejano_devuelve_el_unico_road(
        self, ai_control, populate_graph, make_road
    ):
        """Punto a kilómetros: la expansión termina por cobertura de bloque y da
        el mismo road que el barrido completo."""
        mr = ai_control.map_recorder
        populate_graph(mr, roads=[make_road("R", [(0.0, 0.0), (10.0, 0.0)])])
        best = mr._get_closest_road(5000.0, 5000.0, 0.0, ignore_closed_roads=False)
        oracle = _oracle(mr, 5000.0, 5000.0, 0.0, ignore_closed=False)
        assert best["id"] == "R" == oracle["id"]
        assert best["dist"] == oracle["dist"]

    def test_invalidacion_reconstruye_tras_anadir_road(
        self, ai_control, populate_graph, make_road
    ):
        """Tras mutar self.roads e invalidar, la siguiente consulta ve el cambio."""
        mr = ai_control.map_recorder
        populate_graph(mr, roads=[make_road("A", [(0.0, 0.0), (0.0, 90.0)])])
        # Primera consulta construye el índice.
        assert mr._get_closest_road(50.0, 45.0, 0.0, False)["id"] == "A"
        # Añadimos un road MÁS cercano y NO invalidamos: el índice viejo no lo ve.
        mr.roads["B"] = make_road("B", [(49.0, 0.0), (49.0, 90.0)])
        assert mr._get_closest_road(50.0, 45.0, 0.0, False)["id"] == "A"  # stale
        # Invalidamos como haría un sitio de mutación → ahora sí gana B.
        mr._invalidate_road_index()
        assert mr._get_closest_road(50.0, 45.0, 0.0, False)["id"] == "B"
