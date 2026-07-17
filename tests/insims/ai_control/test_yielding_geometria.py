"""Red del bloque 8.6 (Fase 8): geometría pura del rediseño de la cesión (S44).

Lo que el diseño S44 mete de nuevo, todo sin estado y sin LFS:

- **Puntos de conflicto de un link**: ya NO se vigila solo la `to_road`, sino
  TODAS las roads que el trazado del link pisa (cruce en XY, con **tolerancia
  en Z** para que un puente no cuente como cruce). El punto de unión sobre la
  `to_road` es simplemente uno más. La `from_road` (de la que sales) NO cuenta:
  el "primer cruce real" del diseño es con otra vía, no con la que dejas atrás.
- **Línea de detención derivada**: ya no se graba punto a punto. Del
  `yield_point` sale una línea perpendicular a la tangente del link en ese
  punto, con el ancho de config.
- **Tabla de roads de una zona**: se auto-puebla con las roads que pisan el
  polígono (misma tolerancia en Z).
"""

from __future__ import annotations

from insims.ai_control.nav_modes.freeroam.geometry import segment_intersection_2d
from insims.ai_control.traffic.yielding import (
    derive_yield_line,
    link_conflict_points,
    roads_touching_polygon,
)


def _road(make_road, road_id, points):
    return make_road(road_id, points)


class TestSegmentIntersection2D:
    """Primitiva genérica: ¿dónde se cortan dos segmentos en XY?"""

    def test_cruce_en_x_devuelve_el_punto_y_los_parametros(self):
        # AB horizontal por y=0; CD vertical por x=5. Se cortan en (5, 0).
        hit = segment_intersection_2d(0.0, 0.0, 10.0, 0.0, 5.0, -5.0, 5.0, 5.0)
        assert hit is not None
        px, py, t_ab, t_cd = hit
        assert (round(px, 6), round(py, 6)) == (5.0, 0.0)
        assert round(t_ab, 6) == 0.5  # a mitad de AB
        assert round(t_cd, 6) == 0.5  # a mitad de CD

    def test_paralelos_no_se_cortan(self):
        assert segment_intersection_2d(0.0, 0.0, 10.0, 0.0, 0.0, 2.0, 10.0, 2.0) is None

    def test_se_cortarian_al_prolongarlos_pero_no_se_tocan(self):
        # CD queda corto: el cruce cae fuera del segmento.
        assert segment_intersection_2d(0.0, 0.0, 10.0, 0.0, 5.0, 2.0, 5.0, 8.0) is None

    def test_segmento_degenerado_no_revienta(self):
        assert segment_intersection_2d(0.0, 0.0, 0.0, 0.0, 5.0, -5.0, 5.0, 5.0) is None


class TestLinkConflictPoints:
    """Qué vigila un link: todas las roads que su trazado pisa."""

    def test_detecta_la_road_que_el_trazado_cruza(self, make_road, make_coords):
        # El link va de oeste a este por y=0; CRUZA la road "CRUZADA" (vertical).
        link_nodes = [make_coords(0.0, 0.0), make_coords(20.0, 0.0)]
        roads = {
            "CRUZADA": _road(make_road, "CRUZADA", [(10.0, -10.0), (10.0, 10.0)]),
        }

        puntos = link_conflict_points(link_nodes, roads)

        assert [p.road_id for p in puntos] == ["CRUZADA"]
        assert (round(puntos[0].x_m, 3), round(puntos[0].y_m, 3)) == (10.0, 0.0)

    def test_road_que_no_toca_el_trazado_no_cuenta(self, make_road, make_coords):
        link_nodes = [make_coords(0.0, 0.0), make_coords(20.0, 0.0)]
        roads = {"LEJOS": _road(make_road, "LEJOS", [(10.0, 50.0), (10.0, 60.0)])}

        assert link_conflict_points(link_nodes, roads) == []

    def test_varias_roads_pisadas_dan_varios_puntos(self, make_road, make_coords):
        link_nodes = [make_coords(0.0, 0.0), make_coords(30.0, 0.0)]
        roads = {
            "A": _road(make_road, "A", [(10.0, -5.0), (10.0, 5.0)]),
            "B": _road(make_road, "B", [(20.0, -5.0), (20.0, 5.0)]),
        }

        puntos = link_conflict_points(link_nodes, roads)

        assert sorted(p.road_id for p in puntos) == ["A", "B"]

    def test_puente_no_es_cruce_por_la_tolerancia_en_z(self, make_road, make_coords):
        """Misma XY, pero 10 m más abajo: es un paso inferior, no un cruce."""
        link_nodes = [make_coords(0.0, 0.0, 0.0), make_coords(20.0, 0.0, 0.0)]
        roads = {
            "DEBAJO": _road(
                make_road, "DEBAJO", [(10.0, -10.0, -10.0), (10.0, 10.0, -10.0)]
            )
        }

        assert link_conflict_points(link_nodes, roads, z_tolerance_m=3.0) == []

    def test_cruce_a_la_misma_altura_si_cuenta(self, make_road, make_coords):
        link_nodes = [make_coords(0.0, 0.0, 5.0), make_coords(20.0, 0.0, 5.0)]
        roads = {
            "MISMA": _road(make_road, "MISMA", [(10.0, -10.0, 4.0), (10.0, 10.0, 4.0)])
        }

        puntos = link_conflict_points(link_nodes, roads, z_tolerance_m=3.0)

        assert [p.road_id for p in puntos] == ["MISMA"]

    def test_la_from_road_no_es_un_punto_de_conflicto(self, make_road, make_coords):
        """De la vía que dejas no se cede: el cruce 'real' es con otra."""
        link_nodes = [make_coords(0.0, 0.0), make_coords(20.0, 0.0)]
        roads = {
            "ORIGEN": _road(make_road, "ORIGEN", [(0.0, -10.0), (0.0, 10.0)]),
            "CRUZADA": _road(make_road, "CRUZADA", [(10.0, -10.0), (10.0, 10.0)]),
        }

        puntos = link_conflict_points(link_nodes, roads, exclude_ids=("ORIGEN",))

        assert [p.road_id for p in puntos] == ["CRUZADA"]

    def test_el_punto_trae_el_nodo_mas_cercano_de_su_road(self, make_road, make_coords):
        """El índice sirve para medir el arco del coche al punto de conflicto."""
        link_nodes = [make_coords(0.0, 0.0), make_coords(20.0, 0.0)]
        roads = {
            "CRUZADA": _road(
                make_road,
                "CRUZADA",
                [(10.0, -10.0), (10.0, -1.0), (10.0, 10.0)],
            )
        }

        puntos = link_conflict_points(link_nodes, roads)

        # El cruce cae en (10, 0): el nodo más cercano es el del medio (10, -1).
        assert puntos[0].node_idx == 1

    def test_sin_trazado_no_hay_puntos(self, make_road, make_coords):
        roads = {"A": _road(make_road, "A", [(10.0, -5.0), (10.0, 5.0)])}
        assert link_conflict_points([], roads) == []
        assert link_conflict_points([make_coords(0.0, 0.0)], roads) == []


class TestDeriveYieldLine:
    """La línea de detención se deriva del punto; ya no se graba."""

    def test_linea_perpendicular_al_trazado_centrada_en_el_punto(
        self, make_road, make_coords
    ):
        # Link horizontal (+X); en (10, 0) la perpendicular es vertical (±Y).
        link_nodes = [make_coords(0.0, 0.0), make_coords(20.0, 0.0)]
        punto = make_coords(10.0, 0.0)

        linea = derive_yield_line(link_nodes, punto, width_m=6.0)

        assert len(linea) == 2
        xs = [round(c.x_m, 3) for c in linea]
        ys = sorted(round(c.y_m, 3) for c in linea)
        assert xs == [10.0, 10.0]  # no se mueve en X
        assert ys == [-3.0, 3.0]  # ancho/2 a cada lado

    def test_el_ancho_manda(self, make_coords):
        link_nodes = [make_coords(0.0, 0.0), make_coords(20.0, 0.0)]
        linea = derive_yield_line(link_nodes, make_coords(10.0, 0.0), width_m=10.0)
        ys = sorted(round(c.y_m, 3) for c in linea)
        assert ys == [-5.0, 5.0]

    def test_trazado_en_diagonal_da_perpendicular_en_diagonal(self, make_coords):
        # Link a 45º: la perpendicular también, y la línea sigue centrada.
        link_nodes = [make_coords(0.0, 0.0), make_coords(10.0, 10.0)]
        punto = make_coords(5.0, 5.0)

        linea = derive_yield_line(link_nodes, punto, width_m=2.0)

        a, b = linea
        # El punto medio de la línea es el yield_point.
        assert round((a.x_m + b.x_m) / 2.0, 3) == 5.0
        assert round((a.y_m + b.y_m) / 2.0, 3) == 5.0
        # Perpendicular: el producto escalar con la tangente (1,1) es ~0.
        assert round((b.x_m - a.x_m) + (b.y_m - a.y_m), 3) == 0.0

    def test_usa_la_tangente_del_tramo_del_punto_no_la_del_link_entero(
        self, make_coords
    ):
        """Link en L: en el tramo vertical la línea tiene que ser horizontal."""
        link_nodes = [
            make_coords(0.0, 0.0),
            make_coords(10.0, 0.0),
            make_coords(10.0, 20.0),
        ]
        punto = make_coords(10.0, 15.0)  # en el tramo vertical

        linea = derive_yield_line(link_nodes, punto, width_m=4.0)

        ys = [round(c.y_m, 3) for c in linea]
        xs = sorted(round(c.x_m, 3) for c in linea)
        assert ys == [15.0, 15.0]  # no se mueve en Y
        assert xs == [8.0, 12.0]

    def test_sin_punto_o_sin_trazado_no_hay_linea(self, make_coords):
        assert derive_yield_line([], make_coords(1.0, 1.0), width_m=4.0) == []
        assert derive_yield_line([make_coords(0.0, 0.0)], None, width_m=4.0) == []


class TestRoadsTouchingPolygon:
    """La tabla de roads de la zona se auto-puebla con lo que pisa el polígono."""

    def test_road_que_cruza_el_poligono(self, make_road, make_coords):
        poligono = [
            make_coords(0.0, 0.0),
            make_coords(10.0, 0.0),
            make_coords(10.0, 10.0),
            make_coords(0.0, 10.0),
        ]
        roads = {"CRUZA": _road(make_road, "CRUZA", [(-5.0, 5.0), (15.0, 5.0)])}

        assert roads_touching_polygon(poligono, roads) == ["CRUZA"]

    def test_road_con_un_nodo_dentro_cuenta(self, make_road, make_coords):
        poligono = [
            make_coords(0.0, 0.0),
            make_coords(10.0, 0.0),
            make_coords(10.0, 10.0),
            make_coords(0.0, 10.0),
        ]
        roads = {"ACABA_DENTRO": _road(make_road, "ACABA_DENTRO", [(5.0, 5.0)])}

        assert roads_touching_polygon(poligono, roads) == ["ACABA_DENTRO"]

    def test_road_fuera_no_cuenta(self, make_road, make_coords):
        poligono = [
            make_coords(0.0, 0.0),
            make_coords(10.0, 0.0),
            make_coords(10.0, 10.0),
            make_coords(0.0, 10.0),
        ]
        roads = {"FUERA": _road(make_road, "FUERA", [(50.0, 50.0), (60.0, 60.0)])}

        assert roads_touching_polygon(poligono, roads) == []

    def test_puente_sobre_la_zona_no_cuenta(self, make_road, make_coords):
        """Falso cruce por altura: el filtro en Z lo deja fuera de la tabla."""
        poligono = [
            make_coords(0.0, 0.0, 0.0),
            make_coords(10.0, 0.0, 0.0),
            make_coords(10.0, 10.0, 0.0),
            make_coords(0.0, 10.0, 0.0),
        ]
        roads = {
            "PUENTE": _road(make_road, "PUENTE", [(-5.0, 5.0, 12.0), (15.0, 5.0, 12.0)])
        }

        assert roads_touching_polygon(poligono, roads, z_tolerance_m=3.0) == []

    def test_poligono_invalido_no_da_nada(self, make_road, make_coords):
        roads = {"CRUZA": _road(make_road, "CRUZA", [(-5.0, 5.0), (15.0, 5.0)])}
        assert roads_touching_polygon([], roads) == []
        assert roads_touching_polygon([make_coords(0.0, 0.0)], roads) == []
        assert (
            roads_touching_polygon(
                [make_coords(0.0, 0.0), make_coords(1.0, 0.0)], roads
            )
            == []
        )

    def test_devuelve_ordenado_y_sin_repetir(self, make_road, make_coords):
        poligono = [
            make_coords(0.0, 0.0),
            make_coords(10.0, 0.0),
            make_coords(10.0, 10.0),
            make_coords(0.0, 10.0),
        ]
        roads = {
            "B": _road(make_road, "B", [(-5.0, 5.0), (15.0, 5.0)]),
            "A": _road(make_road, "A", [(5.0, -5.0), (5.0, 15.0)]),  # entra y sale
        }

        assert roads_touching_polygon(poligono, roads) == ["A", "B"]
