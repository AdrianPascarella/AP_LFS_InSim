import json
import logging
import math
import os

import matplotlib

# [!] FORZAR MOTOR NO INTERACTIVO (Debe ir antes de importar pyplot)
matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

logger = logging.getLogger(__name__)

# ==========================================================================
# CONVENCIÓN DE COLORES SEMÁNTICOS (reservados — los roads NO deben usarlos):
#   rojo     → zonas de intersección
#   gris     → lateral links
#   cian     → road links
#   magenta  → líneas de cesión (yield_line): dónde para la IA para ceder
# Los roads se pintan con esta paleta cualitativa, que EXCLUYE a propósito
# esos colores para que un road nunca se confunda con una zona, un lateral
# link, un road link o una línea de cesión.
# ==========================================================================
ZONE_COLOR = "red"
LATERAL_COLOR = "gray"
ROADLINK_COLOR = "c"
YIELDLINE_COLOR = "m"  # magenta: línea de detención de una cesión (Fase 8, 8.5)


def _fmt_yield_t(t) -> str:
    """Etiqueta del tiempo de cesión T: `None` ⇒ 'def' (default global de
    config); un valor ⇒ '<t>s' (sin ceros de más, p. ej. '4s', '3.5s')."""
    if t is None:
        return "def"
    return f"{t:g}s"


ROAD_PALETTE = [
    "#1f77b4",  # azul
    "#ff7f0e",  # naranja
    "#2ca02c",  # verde
    "#9467bd",  # púrpura
    "#8c564b",  # marrón
    "#e377c2",  # rosa
    "#bcbd22",  # oliva
    "#1a5276",  # azul oscuro
    "#6c3483",  # púrpura oscuro
    "#196f3d",  # verde oscuro
    "#b9770e",  # ámbar
    "#8e44ad",  # violeta
]


def _scaled_line_widths(span_m: float):
    """
    Grosores de línea proporcionales a la extensión del mapa (en metros), de
    forma que en un mapa grande las líneas se afinan (los roads paralelos dejan
    de solaparse) y en uno pequeño se engrosan. Devuelve (road_lw, link_lw).
    Los links salen SIEMPRE más finos que los roads (deben verse menos).
    """
    span_m = max(span_m, 1.0)
    road_lw = min(3.0, max(0.6, 1300.0 / span_m))
    link_lw = max(0.5, road_lw * 0.55)
    return road_lw, link_lw


def _road_bounds(data: dict):
    """
    Bounding box (xmin, ymin, xmax, ymax) en metros sobre los nodos de los
    roads. Se usa para escalar los grosores ANTES de dibujar. Devuelve
    infinitos si no hay roads.
    """
    xmin = ymin = math.inf
    xmax = ymax = -math.inf
    for road in data.get("roads", {}).values():
        for n in road["nodes"]:
            x = n["x"] / 65536.0
            y = n["y"] / 65536.0
            xmin = min(xmin, x)
            xmax = max(xmax, x)
            ymin = min(ymin, y)
            ymax = max(ymax, y)
    return xmin, ymin, xmax, ymax


def _draw_elements(ax, data: dict, road_lw: float, link_lw: float):
    """
    Dibuja TODOS los elementos del mapa sobre `ax` (roads, zonas, lateral links,
    road links y líneas de cesión). Dibujo puro: no toca figura, límites,
    leyenda ni disco — eso es responsabilidad de `generate_map_image`. Devuelve
    el bounding box (xmin, ymin, xmax, ymax) sobre todo lo dibujado, para que el
    llamante encuadre el mapa.
    """
    # Bounds de TODOS los elementos, para encuadrar el mapa al final.
    xmin = ymin = math.inf
    xmax = ymax = -math.inf

    def _track(xs, ys):
        nonlocal xmin, ymin, xmax, ymax
        if xs:
            xmin = min(xmin, min(xs))
            xmax = max(xmax, max(xs))
        if ys:
            ymin = min(ymin, min(ys))
            ymax = max(ymax, max(ys))

    # 2. Draw Roads (en orden ALFABÉTICO para que la leyenda quede ordenada y
    #    los carriles paralelos "X_a"/"X_b" queden contiguos y con color distinto)
    if "roads" in data:
        sorted_roads = sorted(data["roads"].items(), key=lambda kv: kv[0].lower())
        for color_idx, (road_id, road) in enumerate(sorted_roads):
            # Convert LFS units to meters
            xs = [node["x"] / 65536.0 for node in road["nodes"]]
            ys = [node["y"] / 65536.0 for node in road["nodes"]]

            # If the road is circular, connect the last point to the first to close the drawing
            if road.get("is_circular", False) and len(xs) > 0:
                xs.append(xs[0])
                ys.append(ys[0])

            current_color = ROAD_PALETTE[color_idx % len(ROAD_PALETTE)]
            _track(xs, ys)

            # Línea sólida fina (sin marcadores por nodo: ensuciaban y engrosaban)
            ax.plot(
                xs,
                ys,
                linestyle="-",
                linewidth=road_lw,
                color=current_color,
                label=road_id,
            )

    # 3. Draw Intersection Zones
    if "zones" in data:
        for z_idx, (zone_id, zone) in enumerate(data["zones"].items()):
            nodes = zone["nodes"]
            radius = zone.get("radius_m", 10.0)
            # Etiqueta del punto: id + T (nuevo modelo punto+T, Fase 8).
            zone_label = f"{zone_id}\nT={_fmt_yield_t(zone.get('yield_time_s'))}"

            # Only add the legend label to the first zone to avoid duplicates
            label_zone = "Zonas de cesión (punto + T)" if z_idx == 0 else ""

            if len(nodes) == 1:
                # It's a point -> Draw a circle
                cx = nodes[0]["x"] / 65536.0
                cy = nodes[0]["y"] / 65536.0
                circle = patches.Circle(
                    (cx, cy), radius, color=ZONE_COLOR, alpha=0.2, label=label_zone
                )
                ax.add_patch(circle)
                ax.text(cx, cy, zone_label, fontsize=8, ha="center", color="darkred")
                _track([cx - radius, cx + radius], [cy - radius, cy + radius])

            elif len(nodes) >= 3:
                # It's a polygon -> Draw the shape
                xs = [n["x"] / 65536.0 for n in nodes]
                ys = [n["y"] / 65536.0 for n in nodes]
                poly = patches.Polygon(
                    xy=list(zip(xs, ys)),
                    closed=True,
                    color=ZONE_COLOR,
                    alpha=0.2,
                    label=label_zone,
                )
                ax.add_patch(poly)
                cx, cy = (
                    sum(xs) / len(xs),
                    sum(ys) / len(ys),
                )  # Approximate centroid for the text
                ax.text(cx, cy, zone_label, fontsize=8, ha="center", color="darkred")
                _track(xs, ys)

    # 4. Draw Lateral Links (línea gris fina DISCONTINUA)
    if "lateral_links" in data:
        for l_idx, (link_id, link) in enumerate(data["lateral_links"].items()):
            xs = [node["x"] / 65536.0 for node in link["nodes"]]
            ys = [node["y"] / 65536.0 for node in link["nodes"]]
            label_lat = "Lateral Link" if l_idx == 0 else ""

            ax.plot(
                xs,
                ys,
                marker="",
                linestyle="--",
                linewidth=link_lw,
                color=LATERAL_COLOR,
                alpha=0.7,
                label=label_lat,
            )
            _track(xs, ys)

    # 5. Draw Longitudinal Links (Road Links): línea cian fina CONTINUA, como los
    #    laterales pero sólida — deben verse menos que los roads.
    if "road_links" in data:
        for r_idx, (link_id, link) in enumerate(data["road_links"].items()):
            nodes = link["nodes"]
            if not nodes:
                continue
            xs = [n["x"] / 65536.0 for n in nodes]
            ys = [n["y"] / 65536.0 for n in nodes]
            label_road = "Road Link" if r_idx == 0 else ""

            ax.plot(
                xs,
                ys,
                marker="",
                linestyle="-",
                linewidth=link_lw,
                color=ROADLINK_COLOR,
                alpha=0.9,
                label=label_road,
            )
            _track(xs, ys)

    # 5b. Yield lines (Fase 8, 8.5): línea de detención de un RoadLink con
    #     cesión — DÓNDE para la IA para ceder el paso. Magenta sólido y grueso
    #     con marcadores en los extremos (se ven aunque sean cortas), rotulada
    #     con su T. Los links sin cesión (`yield_line` vacía) no pintan nada.
    yield_lw = max(road_lw * 1.6, 1.2)
    first_yield = True
    if "road_links" in data:
        for link in data["road_links"].values():
            yl = link.get("yield_line") or []
            if len(yl) < 2:
                continue
            xs = [n["x"] / 65536.0 for n in yl]
            ys = [n["y"] / 65536.0 for n in yl]
            label_yield = "Línea de cesión (stop)" if first_yield else ""
            first_yield = False

            ax.plot(
                xs,
                ys,
                marker="o",
                markersize=max(2.0, yield_lw),
                linestyle="-",
                linewidth=yield_lw,
                color=YIELDLINE_COLOR,
                alpha=0.95,
                zorder=5,  # por encima de roads/links
                label=label_yield,
            )
            # T en el centro de la línea de detención.
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            ax.text(
                cx,
                cy,
                f"T={_fmt_yield_t(link.get('yield_time_s'))}",
                fontsize=7,
                ha="center",
                va="bottom",
                color="darkmagenta",
                zorder=6,
            )
            _track(xs, ys)

    return xmin, ymin, xmax, ymax


def generate_map_image(json_path: str):
    """
    Reads a map JSON file and generates a PNG image with the exact topology,
    saving it in the same folder where this script resides.
    Safe for background threading.
    """
    # 1. Load the JSON file
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error leyendo el JSON del mapa: {e}")
        return

    # Create a large canvas with good resolution
    fig, ax = plt.subplots(figsize=(14, 10))

    # Primera pasada de bounds sobre los roads para conocer la extensión y así
    # escalar los grosores ANTES de dibujar.
    rxmin, rymin, rxmax, rymax = _road_bounds(data)
    span_m = max(rxmax - rxmin, rymax - rymin) if rxmax > -math.inf else 1.0
    road_lw, link_lw = _scaled_line_widths(span_m)

    # Dibujo de todos los elementos; devuelve los bounds para encuadrar.
    xmin, ymin, xmax, ymax = _draw_elements(ax, data, road_lw, link_lw)

    # 6. Visual chart configuration (Orientado a objetos para Thread-Safety)
    #    adjustable="box": el eje se ajusta a la proporción de los datos (el mapa
    #    llena el recuadro) en vez de expandir el rango de datos.
    ax.set_aspect("equal", adjustable="box")
    if xmax > -math.inf and xmin < math.inf:
        margin = max((xmax - xmin), (ymax - ymin)) * 0.03 + 1.0
        ax.set_xlim(xmin - margin, xmax + margin)
        ax.set_ylim(ymin - margin, ymax + margin)
    ax.set_title("Map Visualization", fontsize=16, fontweight="bold")
    ax.set_xlabel("X (Meters)", fontsize=12)
    ax.set_ylabel("Y (Meters)", fontsize=12)
    ax.grid(True, linestyle=":", alpha=0.6)

    # Leyenda a la derecha: los nombres bajan SIEMPRE hasta el fondo del mapa (su
    # extensión vertical == la del recuadro del mapa) y solo entonces se abre la
    # siguiente columna. Dos casos, según quepan o no en una sola columna a
    # espaciado natural:
    #   • Caben de sobra (pocos roads) → 1 columna, pero se REPARTEN (se agranda el
    #     `labelspacing`) hasta que ocupan justo el alto del mapa, sin dejar hueco.
    #   • No caben (muchos roads) → multi-columna a espaciado natural, llenando
    #     columna-a-columna hasta el fondo antes de saltar a la siguiente (la última
    #     se rellena con entradas invisibles para que matplotlib no equilibre
    #     columnas más cortas).
    # El nº de filas por columna y el reparto se MIDEN sobre un render de sondeo
    # (alto del recuadro del mapa / alto de la leyenda), no se estiman; los ratios
    # son independientes del dpi.
    fig.tight_layout()
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        legend_fontsize = 7
        legend_kwargs = dict(
            loc="upper left",
            bbox_to_anchor=(1.02, 1),
            borderaxespad=0.0,
            fontsize=legend_fontsize,
        )
        # Medición: alto del recuadro del mapa y alto de la leyenda a 1 columna
        # (sondeo con TODAS las entradas, a espaciado natural).
        fig.canvas.draw()
        pad_px = 0.4 * legend_fontsize * fig.dpi / 72.0  # borderpad (arriba+abajo)
        axes_h = ax.get_window_extent().height
        probe = ax.legend(handles, labels, ncol=1, **legend_kwargs)
        fig.canvas.draw()
        probe_h = probe.get_window_extent().height
        per_entry = max(1.0, (probe_h - 2 * pad_px) / len(labels))

        rows_per_col = max(1, int((axes_h - 2 * pad_px) // per_entry))
        ncol = max(1, math.ceil(len(labels) / rows_per_col))

        # Reparto vertical: si todo cabe en 1 columna que queda MÁS CORTA que el
        # mapa, agrandar `labelspacing` (en unidades de tamaño de fuente) para que
        # los nombres bajen justo hasta el fondo. El sondeo ya midió el alto natural
        # (probe_h) a `labelspacing` por defecto (0.5); cada unidad extra añade
        # `fs_px` de separación en cada uno de los (n-1) huecos.
        labelspacing = 0.5
        if ncol == 1 and len(labels) >= 2 and probe_h < axes_h:
            fs_px = legend_fontsize * fig.dpi / 72.0
            labelspacing = 0.5 + (axes_h - probe_h) / ((len(labels) - 1) * fs_px)

        # Con ≥2 columnas, rellenar hasta ncol*rows_per_col con entradas invisibles
        # para que cada columna se llene hasta el fondo del mapa antes de saltar a
        # la siguiente (si no, matplotlib equilibraría columnas más cortas).
        h_full, l_full = list(handles), list(labels)
        if ncol > 1:
            while len(h_full) < ncol * rows_per_col:
                h_full.append(Line2D([], [], color="none"))
                l_full.append(" ")

        ax.legend(
            h_full,
            l_full,
            ncol=ncol,
            handlelength=1.5,
            columnspacing=1.0,
            labelspacing=labelspacing,
            **legend_kwargs,
        )

    # 7. Save to disk
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_name = os.path.basename(json_path).replace(".json", "")
    output_path = os.path.join(script_dir, f"{base_name}_rendered.png")

    # Usar fig.savefig en lugar de plt.savefig
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    logger.info(f"Imagen del mapa guardada en '{output_path}'")

    # [!] MUY IMPORTANTE: Liberar explícitamente la memoria de ESTA figura
    fig.clf()
    plt.close(fig)


# --- HOW TO USE IT ---
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "maps", "test.json")
    json_path = os.path.abspath(json_path)
    generate_map_image(json_path)
