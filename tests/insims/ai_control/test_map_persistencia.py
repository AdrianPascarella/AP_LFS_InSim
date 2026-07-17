"""Red del bloque 8.1, rehecha en el 8.6 (Fase 8): persistencia del mapa freeroam.

Tres partes:

- **Caracterización de la carga actual**: `south_city.json` (el mapa real:
  223 roads / 374 road_links / 43 lateral_links / 1 zona) tiene que cargar
  INTACTO. Es el requisito duro de compatibilidad de la Fase 8 (PLAN § Fase 8,
  decisión 6): los campos nuevos son opcionales con default. (Los conteos se
  re-basan cuando el usuario amplía el mapa; el último ajuste fue en S44.)

- **Round-trip del modelo de cesión (S44, bloque 8.6)**: los campos del
  `RoadLink` (`yield_type` + `yield_point` + T) y los de `IntersectionZone`
  (polígono + T + tabla `roads`) sobreviven a serializar+cargar por el MISMO
  camino que el guardado real (`_serialize_map_data` + `_json_map_default` +
  JSON + `_load_map_from_data`).

- **Retirada del modelo viejo**: los campos muertos (`yield_line`,
  `yield_zone_id`, `radius_m`, `priority_rules`) ya no existen en el modelo, y
  un JSON que aún los traiga carga igual (el loader filtra claves desconocidas).
"""

from __future__ import annotations

import json

from insims.ai_control.nav_modes.freeroam.enums import YieldType
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
    """Caracterización: el mapa real carga entero."""

    def test_south_city_carga_intacto(self, ai_control):
        # Conteos de CARACTERIZACIÓN: se re-basan cuando el usuario amplía el
        # mapa en el juego (S42, S44, S46). Que fallen tras un remapeo es lo
        # normal; lo que vigilan es que el mapa real siga cargando entero.
        mr = ai_control.map_recorder
        assert mr._load_map_from_disk("south_city") is True
        assert len(mr.roads) == 226
        assert len(mr.road_links) == 387
        assert len(mr.lateral_links) == 50
        assert "test1" in mr.zones

    def test_zona_vieja_carga_con_lo_que_sobrevive(self, ai_control):
        """`test1` (modelo viejo) carga: conserva nodos, pierde lo retirado.

        Sus 2 nodos no son un polígono válido (≥3), así que la zona queda
        INERTE hasta que el usuario la regrabe en el juego (bloque 8.7). Sus
        `priority_rules` no se convierten solas: la tabla `roads` nace vacía.
        """
        mr = ai_control.map_recorder
        assert mr._load_map_from_disk("south_city") is True
        zona = mr.zones["test1"]
        assert len(zona.nodes) == 2
        assert zona.roads == {}
        assert zona.yield_time_s is None
        assert zona.has_polygon is False

    def test_links_de_mapa_viejo_cargan_sin_cesion(self, ai_control):
        """Un JSON sin campos `yield_*` produce links con los defaults S44."""
        mr = ai_control.map_recorder
        assert mr._load_map_from_disk("south_city") is True
        link = mr.road_links["SOUTH_CITY_STATION_s2->HAVEN_LANE_S22_b"]
        assert link.yield_type is YieldType.NONE
        assert link.yield_point is None
        assert link.yield_time_s is None
        assert link.has_yield is False


class TestRoundTripCesionLink:
    """La cesión del link (S44) sobrevive a guardar+cargar."""

    def test_link_con_cesion_sobrevive(
        self, ai_control, populate_graph, make_road, make_road_link, make_coords
    ):
        mr = ai_control.map_recorder
        punto = make_coords(10.0, 0.0)
        populate_graph(
            mr,
            roads=[make_road("R1", [(0.0, 0.0), (20.0, 0.0)])],
            road_links=[
                make_road_link(
                    "R1",
                    "R2",
                    [(20.0, 0.0), (30.0, 0.0)],
                    yield_type=YieldType.YIELD,
                    yield_point=punto,
                    yield_time_s=3.0,
                )
            ],
        )

        _roundtrip(mr)

        link = mr.road_links["R1->R2"]
        assert link.yield_type is YieldType.YIELD  # enum, no el str crudo
        assert link.yield_point == punto
        assert isinstance(link.yield_point, Coordinates)  # no un dict crudo
        assert link.yield_time_s == 3.0
        assert link.has_yield is True

    def test_link_stop_sobrevive(
        self, ai_control, populate_graph, make_road_link, make_coords
    ):
        mr = ai_control.map_recorder
        populate_graph(
            mr,
            road_links=[
                make_road_link(
                    "R1",
                    "R2",
                    [(20.0, 0.0), (30.0, 0.0)],
                    yield_type=YieldType.STOP,
                    yield_point=make_coords(10.0, 0.0),
                )
            ],
        )

        _roundtrip(mr)

        assert mr.road_links["R1->R2"].yield_type is YieldType.STOP

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
        assert link.yield_type is YieldType.NONE
        assert link.yield_point is None
        assert link.yield_time_s is None
        assert link.has_yield is False

    def test_tipo_sin_punto_no_es_cesion(
        self, ai_control, populate_graph, make_road_link
    ):
        """Un toggle en YIELD sin punto marcado está a medias: no hay línea que
        derivar, así que no cede (la UI deja marcar el punto después)."""
        mr = ai_control.map_recorder
        populate_graph(
            mr,
            road_links=[
                make_road_link(
                    "R1", "R2", [(20.0, 0.0), (30.0, 0.0)], yield_type=YieldType.YIELD
                )
            ],
        )

        link = mr.road_links["R1->R2"]
        assert link.yield_point is None
        assert link.has_yield is False


class TestRoundTripZona:
    """La zona nueva (polígono + T + tabla de roads) sobrevive a guardar+cargar."""

    def test_zona_poligono_sobrevive(self, ai_control, make_coords):
        mr = ai_control.map_recorder
        poligono = [
            make_coords(0.0, 0.0),
            make_coords(10.0, 0.0),
            make_coords(5.0, 8.0),
        ]
        mr.zones["Z1"] = IntersectionZone(
            zone_id="Z1",
            nodes=poligono,
            yield_time_s=6.0,
            roads={"R1": YieldType.NONE, "R2": YieldType.YIELD, "R3": YieldType.STOP},
        )

        _roundtrip(mr)

        zona = mr.zones["Z1"]
        assert zona.nodes == poligono
        assert isinstance(zona.nodes[0], Coordinates)
        assert zona.yield_time_s == 6.0
        assert zona.roads == {
            "R1": YieldType.NONE,
            "R2": YieldType.YIELD,
            "R3": YieldType.STOP,
        }
        # Los valores de la tabla vuelven como enum, no como str crudo.
        assert all(isinstance(v, YieldType) for v in zona.roads.values())
        assert zona.has_polygon is True

    def test_zona_con_menos_de_tres_nodos_no_es_poligono(self, ai_control, make_coords):
        mr = ai_control.map_recorder
        mr.zones["Z1"] = IntersectionZone(
            zone_id="Z1", nodes=[make_coords(0.0, 0.0), make_coords(10.0, 0.0)]
        )

        _roundtrip(mr)

        assert mr.zones["Z1"].has_polygon is False

    def test_zona_nueva_nace_vacia(self):
        zona = IntersectionZone(zone_id="Z1")
        assert zona.nodes == []
        assert zona.roads == {}
        assert zona.yield_time_s is None
        assert zona.has_polygon is False


class TestModeloViejoRetirado:
    """Los campos del modelo viejo ya no existen; su JSON carga igual (S44)."""

    def test_campos_muertos_fuera_del_modelo(self, ai_control, make_road_link):
        link = make_road_link("R1", "R2", [(0.0, 0.0)])
        assert not hasattr(link, "yield_line")
        assert not hasattr(link, "yield_zone_id")

        zona = IntersectionZone(zone_id="Z1")
        assert not hasattr(zona, "radius_m")
        assert not hasattr(zona, "priority_rules")

    def test_json_con_campos_retirados_carga_ignorandolos(self, ai_control):
        """El loader filtra las claves desconocidas: un mapa guardado con el
        modelo viejo carga sin reventar (y al re-guardar quedan fuera)."""
        mr = ai_control.map_recorder
        data = {
            "zones": {
                "Z1": {
                    "zone_id": "Z1",
                    "nodes": [{"x": 0, "y": 0, "z": 0}],
                    "yield_time_s": None,
                    "radius_m": 10.0,
                    "priority_rules": [["A", "B"]],
                }
            },
            "road_links": {
                "R1->R2": {
                    "from_road_id": "R1",
                    "to_road_id": "R2",
                    "nodes": [{"x": 0, "y": 0, "z": 0}],
                    "yield_line": [{"x": 0, "y": 0, "z": 0}],
                    "yield_zone_id": "Z1",
                    "yield_time_s": 3.0,
                }
            },
        }

        mr._load_map_from_data(data)

        zona = mr.zones["Z1"]
        assert zona.roads == {}
        link = mr.road_links["R1->R2"]
        assert link.yield_type is YieldType.NONE  # el modelo viejo no declaraba tipo
        assert link.yield_point is None
        assert link.yield_time_s == 3.0  # este sí sobrevive: no cambió de forma
        assert link.has_yield is False

    def test_lo_guardado_no_arrastra_campos_muertos(
        self, ai_control, populate_graph, make_road_link
    ):
        mr = ai_control.map_recorder
        populate_graph(mr, road_links=[make_road_link("R1", "R2", [(0.0, 0.0)])])
        mr.zones["Z1"] = IntersectionZone(zone_id="Z1")

        data = mr._serialize_map_data()

        assert "yield_line" not in data["road_links"]["R1->R2"]
        assert "yield_zone_id" not in data["road_links"]["R1->R2"]
        assert "radius_m" not in data["zones"]["Z1"]
        assert "priority_rules" not in data["zones"]["Z1"]
