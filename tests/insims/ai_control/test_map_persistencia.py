"""Red del bloque 8.1 (Fase 8): persistencia del mapa freeroam.

Dos partes:

- **Caracterización de la carga actual**: `south_city.json` (el mapa real:
  222 roads / 328 road_links / 28 lateral_links / 1 zona) tiene que cargar
  INTACTO. Es el requisito duro de compatibilidad de la Fase 8 (PLAN § Fase 8,
  decisión 6): los campos nuevos son opcionales con default.

- **Round-trip del modelo de cesión (S38)**: los campos `yield_*` del
  `RoadLink` (línea de detención + T + zona vigilada) y el `yield_time_s` de
  `IntersectionZone` sobreviven a serializar+cargar por el MISMO camino que el
  guardado real (`_serialize_map_data` + `_json_map_default` + JSON +
  `_load_map_from_data`); los mapas viejos (sin esos campos) cargan con los
  defaults (sin cesión).
"""

from __future__ import annotations

import json

from insims.ai_control.nav_modes.freeroam.graph import IntersectionZone
from insims.users_management.um_class import Coordinates


def _roundtrip(mr):
    """Serializa el mapa en memoria y lo recarga sobre el mismo recorder.

    Pasa por json.dumps con el MISMO `default` que usa el guardado real, para
    que el test cubra también la serialización de Enums y Coordinates.
    """
    from insims.ai_control.nav_modes.freeroam.map_recorder import _json_map_default

    data = json.loads(json.dumps(mr._serialize_map_data(), default=_json_map_default))
    mr._load_map_from_data(data)


class TestCargaSouthCity:
    """Caracterización: el mapa real carga entero (verde ANTES del cambio)."""

    def test_south_city_carga_intacto(self, ai_control):
        mr = ai_control.map_recorder
        assert mr._load_map_from_disk("south_city") is True
        assert len(mr.roads) == 222
        assert len(mr.road_links) == 328
        assert len(mr.lateral_links) == 28
        # La zona vieja (área + priority_rules) sigue cargando tal cual hasta
        # que 8.3/8.6 retiren el modelo antiguo.
        zona = mr.zones["test1"]
        assert zona.radius_m == 10.0
        assert len(zona.priority_rules) == 2

    def test_links_de_mapa_viejo_cargan_sin_cesion(self, ai_control):
        """Un JSON sin campos `yield_*` produce links con los defaults S38."""
        mr = ai_control.map_recorder
        assert mr._load_map_from_disk("south_city") is True
        link = mr.road_links["SOUTH_CITY_STATION_s2->HAVEN_LANE_S22_b"]
        assert link.yield_line == []
        assert link.yield_time_s is None
        assert link.yield_zone_id is None
        assert link.has_yield is False


class TestRoundTripCesion:
    """El modelo nuevo (S38) sobrevive a guardar+cargar."""

    def test_link_con_cesion_sobrevive(
        self, ai_control, populate_graph, make_road, make_road_link, make_coords
    ):
        mr = ai_control.map_recorder
        linea = [make_coords(10.0, 0.0), make_coords(10.0, 4.0)]
        populate_graph(
            mr,
            roads=[make_road("R1", [(0.0, 0.0), (20.0, 0.0)])],
            road_links=[
                make_road_link(
                    "R1",
                    "R2",
                    [(20.0, 0.0), (30.0, 0.0)],
                    yield_line=linea,
                    yield_time_s=3.0,
                    yield_zone_id="Z1",
                )
            ],
        )

        _roundtrip(mr)

        link = mr.road_links["R1->R2"]
        assert link.yield_line == linea
        assert isinstance(link.yield_line[0], Coordinates)  # no dicts crudos
        assert link.yield_time_s == 3.0
        assert link.yield_zone_id == "Z1"
        assert link.has_yield is True

    def test_link_sin_cesion_mantiene_defaults_tras_roundtrip(
        self, ai_control, populate_graph, make_road, make_road_link
    ):
        mr = ai_control.map_recorder
        populate_graph(
            mr,
            roads=[make_road("R1", [(0.0, 0.0), (20.0, 0.0)])],
            road_links=[make_road_link("R1", "R2", [(20.0, 0.0), (30.0, 0.0)])],
        )

        _roundtrip(mr)

        link = mr.road_links["R1->R2"]
        assert link.yield_line == []
        assert link.yield_time_s is None
        assert link.yield_zone_id is None
        assert link.has_yield is False

    def test_zona_nueva_punto_mas_tiempo_sobrevive(self, ai_control, make_coords):
        mr = ai_control.map_recorder
        punto = make_coords(25.0, 5.0)
        mr.zones["Z1"] = IntersectionZone(zone_id="Z1", nodes=[punto], yield_time_s=6.0)

        _roundtrip(mr)

        zona = mr.zones["Z1"]
        assert zona.nodes == [punto]
        assert isinstance(zona.nodes[0], Coordinates)
        assert zona.yield_time_s == 6.0
