"""Caracterización de `MapRecorder.get_location_context` (freeroam).

Congela el comportamiento ACTUAL de la localización geométrica ANTES de tocar
su interior (auditoría del hot-loop, Fase 5). El foco es la **selección del
enlace más cercano**, que hoy recorre `road_links` ∪ `lateral_links`: ese es
justo el punto que se va a optimizar (evitar la reconstrucción del dict
fusionado), así que estos tests fijan el resultado —incluido el desempate por
orden de iteración— para garantizar que la optimización no cambia nada.

Escenario base (todo en metros): dos vías verticales R1 (x=0) y R2 (x=100),
cada una con nodos cada 10 m en Y (0..90). Los enlaces se añaden por test.
"""

from __future__ import annotations


def _straight_y(x=0.0, y0=0.0, y1=90.0, step=10.0):
    n = int(round((y1 - y0) / step))
    return [(x, y0 + i * step) for i in range(n + 1)]


def _base_roads(populate_graph, make_road, mr):
    populate_graph(
        mr,
        roads=[
            make_road("R1", _straight_y(x=0.0)),
            make_road("R2", _straight_y(x=100.0)),
        ],
    )


class TestGetLocationContextRoads:
    def test_encuentra_el_road_mas_cercano(self, ai_control, populate_graph, make_road):
        mr = ai_control.map_recorder
        _base_roads(populate_graph, make_road, mr)

        ctx = mr.get_location_context(
            5.0, 45.0, 0.0, find_links=False, find_zones=False
        )

        assert ctx.road_id == "R1"
        assert ctx.road_dist == 5.0  # perpendicular exacta a la recta x=0
        assert ctx.link_id is None  # find_links=False

    def test_road_node_idx_es_el_nodo_mas_cercano(
        self, ai_control, populate_graph, make_road
    ):
        mr = ai_control.map_recorder
        _base_roads(populate_graph, make_road, mr)

        # (0,50) coincide con el nodo de índice 5 de R1 (nodos cada 10 m)
        ctx = mr.get_location_context(
            0.0, 50.0, 0.0, find_links=False, find_zones=False
        )

        assert ctx.road_id == "R1"
        assert ctx.road_node_idx == 5

    def test_mapa_vacio_devuelve_contexto_vacio(self, ai_control):
        mr = ai_control.map_recorder
        ctx = mr.get_location_context(10.0, 10.0, 0.0)
        assert ctx.road_id is None
        assert ctx.link_id is None

    def test_ignore_closed_roads_salta_la_cerrada(
        self, ai_control, populate_graph, make_road
    ):
        mr = ai_control.map_recorder
        populate_graph(
            mr,
            roads=[
                make_road("R1", _straight_y(x=0.0), is_closed=True),
                make_road("R2", _straight_y(x=100.0)),
            ],
        )
        # Punto pegado a R1 (cerrada): con el flag, se ignora y gana R2.
        ctx = mr.get_location_context(
            5.0, 45.0, 0.0, find_links=False, find_zones=False, ignore_closed_roads=True
        )
        assert ctx.road_id == "R2"


class TestGetLocationContextLinks:
    """La parte que se va a optimizar: enlace más cercano sobre road+lateral."""

    def test_considera_lateral_links_no_solo_road_links(
        self, ai_control, populate_graph, make_road, make_road_link, make_lateral_link
    ):
        mr = ai_control.map_recorder
        _base_roads(populate_graph, make_road, mr)
        populate_graph(
            mr,
            # road_link horizontal lejos (y=100); lateral vertical cerca (x=50)
            road_links=[make_road_link("R1", "R2", [(0.0, 100.0), (100.0, 100.0)])],
            lateral_links=[make_lateral_link("R1", "R2", [(50.0, 0.0), (50.0, 90.0)])],
        )
        # (48,45): el lateral (x=50) está a ~2 m; el road_link (y=100) mucho más lejos.
        ctx = mr.get_location_context(48.0, 45.0, 0.0, find_zones=False)

        assert ctx.link_id == "R1<<>>R2"
        assert ctx.link_type == "LatLink"
        assert ctx.link_dist == 2.0

    def test_road_link_gana_cuando_es_el_mas_cercano(
        self, ai_control, populate_graph, make_road, make_road_link, make_lateral_link
    ):
        mr = ai_control.map_recorder
        _base_roads(populate_graph, make_road, mr)
        populate_graph(
            mr,
            road_links=[make_road_link("R1", "R2", [(0.0, 100.0), (100.0, 100.0)])],
            lateral_links=[make_lateral_link("R1", "R2", [(50.0, 0.0), (50.0, 90.0)])],
        )
        # (50,98): el road_link (y=100) está a 2 m; el lateral (tope en y=90) a 8 m.
        ctx = mr.get_location_context(50.0, 98.0, 0.0, find_zones=False)

        assert ctx.link_id == "R1->R2"
        assert ctx.link_type == "RoadLink"

    def test_empate_gana_el_road_link_por_orden_de_iteracion(
        self, ai_control, populate_graph, make_road, make_road_link, make_lateral_link
    ):
        """Con distancia IDÉNTICA, road_links se recorre antes que lateral_links y
        `get_closest_geometry` usa `<` estricto → gana el primero (el road_link).
        Invariante que la optimización del dict fusionado debe conservar."""
        mr = ai_control.map_recorder
        _base_roads(populate_graph, make_road, mr)
        same_nodes = [(0.0, 100.0), (100.0, 100.0)]
        populate_graph(
            mr,
            road_links=[make_road_link("R1", "R2", same_nodes)],
            lateral_links=[make_lateral_link("R1", "R2", same_nodes)],
        )
        # Equidistante de ambos (mismos nodos) → gana road_links por orden.
        ctx = mr.get_location_context(50.0, 105.0, 0.0, find_zones=False)

        assert ctx.link_id == "R1->R2"
        assert ctx.link_type == "RoadLink"

    def test_solo_lateral_links_tambien_se_encuentra(
        self, ai_control, populate_graph, make_road, make_lateral_link
    ):
        mr = ai_control.map_recorder
        _base_roads(populate_graph, make_road, mr)
        populate_graph(
            mr,
            lateral_links=[make_lateral_link("R1", "R2", [(50.0, 0.0), (50.0, 90.0)])],
        )
        ctx = mr.get_location_context(48.0, 45.0, 0.0, find_zones=False)
        assert ctx.link_id == "R1<<>>R2"
        assert ctx.link_type == "LatLink"
