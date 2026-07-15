"""Red del bloque 8.5 (Fase 8): render del mapa freeroam.

`map_renderer.generate_map_image` era una función monolítica sin tests. Se
extrajo un seam puro `_draw_elements(ax, data, road_lw, link_lw)` (dibuja todos
los elementos sobre un axes y devuelve los bounds, sin tocar figura/leyenda/
disco) para poder afirmar sobre los artistas de matplotlib sin generar PNGs.

Dos partes:

- **Caracterización** del dibujo actual (roads, zonas círculo/polígono, lateral
  links discontinuos, road links cian). Verde ANTES de tocar el render nuevo.
- **Cesión (8.5)**: las `yield_line` de los RoadLink se pintan como líneas de
  detención en su color reservado, con su T; las zonas muestran su T. Estos
  tests nacen en ROJO (el dibujo de cesión aún no existe).
"""

from __future__ import annotations

import os

# Backend headless antes de importar el renderer (importa pyplot).
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")
import math

import matplotlib.pyplot as plt
import pytest

from insims.ai_control.nav_modes.freeroam import map_renderer as mr

_LFS = 65536  # unidades LFS por metro (el render divide por esto)


def _n(x_m: float, y_m: float, z_m: float = 0.0) -> dict:
    """Nodo JSON {x,y,z} en unidades LFS desde metros (formato del mapa real)."""
    return {"x": int(x_m * _LFS), "y": int(y_m * _LFS), "z": int(z_m * _LFS)}


def _road(nodes, **extra) -> dict:
    d = {"nodes": nodes}
    d.update(extra)
    return d


def _link(nodes, **extra) -> dict:
    d = {"nodes": nodes}
    d.update(extra)
    return d


def _zone(nodes, **extra) -> dict:
    d = {"nodes": nodes}
    d.update(extra)
    return d


@pytest.fixture
def ax():
    """Un axes headless nuevo por test; se cierra la figura al terminar."""
    fig, axes = plt.subplots()
    yield axes
    plt.close(fig)


def _lines_by_color(axes, color):
    """Líneas (Line2D) del axes cuyo color coincide con `color`."""
    return [ln for ln in axes.lines if ln.get_color() == color]


def _texts_containing(axes, needle):
    return [t for t in axes.texts if needle in t.get_text()]


# ══════════════════════════════════════════════════════════════════════════
# Caracterización del dibujo actual (verde antes de tocar nada)
# ══════════════════════════════════════════════════════════════════════════


class TestRoads:
    def test_cada_road_es_una_linea_con_su_id(self, ax):
        data = {
            "roads": {
                "R1": _road([_n(0, 0), _n(10, 0)]),
                "R2": _road([_n(0, 5), _n(10, 5)]),
            }
        }
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        labels = {ln.get_label() for ln in ax.lines}
        assert {"R1", "R2"} <= labels
        # Colores de la paleta cualitativa (no reservados).
        for ln in ax.lines:
            assert ln.get_color() not in (
                mr.ZONE_COLOR,
                mr.LATERAL_COLOR,
                mr.ROADLINK_COLOR,
            )

    def test_road_circular_cierra_el_trazo(self, ax):
        data = {
            "roads": {"R": _road([_n(0, 0), _n(10, 0), _n(10, 10)], is_circular=True)}
        }
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        ln = ax.lines[0]
        xs = ln.get_xdata()
        ys = ln.get_ydata()
        assert (xs[0], ys[0]) == (xs[-1], ys[-1])


class TestZonas:
    def test_zona_de_un_nodo_es_un_circulo_rojo(self, ax):
        import matplotlib.patches as mpatches

        data = {"zones": {"Z": _zone([_n(5, 5)], radius_m=8.0)}}
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        circles = [p for p in ax.patches if isinstance(p, mpatches.Circle)]
        assert len(circles) == 1
        assert circles[0].get_edgecolor() is not None
        assert _texts_containing(ax, "Z")  # el id de la zona se rotula

    def test_zona_poligono_de_3_o_mas_nodos(self, ax):
        import matplotlib.patches as mpatches

        data = {"zones": {"Z": _zone([_n(0, 0), _n(4, 0), _n(4, 4)], radius_m=10.0)}}
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        polys = [p for p in ax.patches if isinstance(p, mpatches.Polygon)]
        assert len(polys) == 1

    def test_zona_de_dos_nodos_no_se_dibuja(self, ax):
        # Modelo VIEJO (test1 tiene 2 nodos): ni círculo ni polígono. Se
        # caracteriza el hueco actual; el modelo nuevo es de 1 nodo (punto).
        data = {"zones": {"test1": _zone([_n(0, 0), _n(4, 0)], radius_m=10.0)}}
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        assert not ax.patches


class TestLinks:
    def test_lateral_link_gris_discontinuo(self, ax):
        data = {"lateral_links": {"L": _link([_n(0, 0), _n(0, 4)])}}
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        grises = _lines_by_color(ax, mr.LATERAL_COLOR)
        assert len(grises) == 1
        assert grises[0].get_linestyle() in ("--", "dashed")

    def test_road_link_cian_continuo(self, ax):
        data = {"road_links": {"RL": _link([_n(0, 0), _n(2, 2)])}}
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        cianes = _lines_by_color(ax, mr.ROADLINK_COLOR)
        assert len(cianes) == 1
        assert cianes[0].get_linestyle() in ("-", "solid")

    def test_road_link_sin_nodos_se_ignora(self, ax):
        data = {"road_links": {"RL": _link([])}}
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        assert not ax.lines


class TestBounds:
    def test_devuelve_bounds_finitos_sobre_lo_dibujado(self, ax):
        data = {"roads": {"R": _road([_n(-3, -3), _n(7, 5)])}}
        xmin, ymin, xmax, ymax = mr._draw_elements(ax, data, 1.0, 0.5)
        assert math.isclose(xmin, -3, abs_tol=0.01)
        assert math.isclose(ymin, -3, abs_tol=0.01)
        assert math.isclose(xmax, 7, abs_tol=0.01)
        assert math.isclose(ymax, 5, abs_tol=0.01)

    def test_road_bounds_infinito_sin_roads(self):
        xmin, ymin, xmax, ymax = mr._road_bounds({})
        assert xmin == math.inf and xmax == -math.inf


# ══════════════════════════════════════════════════════════════════════════
# Cesión (8.5) — nacen en ROJO
# ══════════════════════════════════════════════════════════════════════════


class TestYieldLine:
    def test_yield_line_se_pinta_en_su_color_reservado(self, ax):
        # Un road_link con línea de detención (>=2 puntos) => una línea en el
        # color reservado de cesión, distinta del road link en sí.
        data = {
            "road_links": {
                "RL": _link(
                    [_n(0, 0), _n(4, 0)],
                    yield_line=[_n(2, -1), _n(2, 1)],
                    yield_time_s=None,
                )
            }
        }
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        cesion = _lines_by_color(ax, mr.YIELDLINE_COLOR)
        assert len(cesion) == 1
        pts = list(zip(cesion[0].get_xdata(), cesion[0].get_ydata()))
        assert (2.0, -1.0) in [(round(x, 3), round(y, 3)) for x, y in pts]
        assert (2.0, 1.0) in [(round(x, 3), round(y, 3)) for x, y in pts]

    def test_yield_line_reservada_no_la_usan_los_roads(self, ax):
        # El color de cesión es reservado: ningún road de la paleta lo usa.
        data = {
            "roads": {
                f"R{i}": _road([_n(i, 0), _n(i, 10)])
                for i in range(len(mr.ROAD_PALETTE) + 2)
            }
        }
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        assert not _lines_by_color(ax, mr.YIELDLINE_COLOR)

    def test_yield_line_vacia_no_dibuja_nada(self, ax):
        data = {"road_links": {"RL": _link([_n(0, 0), _n(4, 0)], yield_line=[])}}
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        assert not _lines_by_color(ax, mr.YIELDLINE_COLOR)

    def test_yield_line_rotula_su_T(self, ax):
        data = {
            "road_links": {
                "RL": _link(
                    [_n(0, 0), _n(4, 0)],
                    yield_line=[_n(2, -1), _n(2, 1)],
                    yield_time_s=3.0,
                )
            }
        }
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        assert _texts_containing(ax, "T=3")

    def test_yield_line_sin_T_rotula_default(self, ax):
        data = {
            "road_links": {
                "RL": _link(
                    [_n(0, 0), _n(4, 0)],
                    yield_line=[_n(2, -1), _n(2, 1)],
                    yield_time_s=None,
                )
            }
        }
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        # T no fijado => se rotula el default global, no un número.
        assert _texts_containing(ax, "def")


class TestZonaConT:
    def test_zona_rotula_su_T(self, ax):
        data = {"zones": {"Z": _zone([_n(5, 5)], yield_time_s=5.0, radius_m=8.0)}}
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        assert _texts_containing(ax, "T=5")

    def test_zona_sin_T_rotula_default(self, ax):
        data = {"zones": {"Z": _zone([_n(5, 5)], yield_time_s=None, radius_m=8.0)}}
        mr._draw_elements(ax, data, road_lw=1.0, link_lw=0.5)
        assert _texts_containing(ax, "def")
