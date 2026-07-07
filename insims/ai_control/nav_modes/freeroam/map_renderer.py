import json
import logging
import math
import os

import matplotlib

# [!] FORZAR MOTOR NO INTERACTIVO (Debe ir antes de importar pyplot)
matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# ==========================================================================
# CONVENCIÓN DE COLORES SEMÁNTICOS (reservados — los roads NO deben usarlos):
#   rojo  → zonas de intersección
#   gris  → lateral links
#   cian  → road links
# Los roads se pintan con esta paleta cualitativa, que EXCLUYE a propósito
# rojo/gris/cian para que un road nunca se confunda con una zona, un lateral
# link o un road link.
# ==========================================================================
ZONE_COLOR = "red"
LATERAL_COLOR = "gray"
ROADLINK_COLOR = "c"

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

    # Primera pasada de bounds sobre los roads para conocer la extensión y así
    # escalar los grosores ANTES de dibujar.
    for road in data.get("roads", {}).values():
        _track(
            [n["x"] / 65536.0 for n in road["nodes"]],
            [n["y"] / 65536.0 for n in road["nodes"]],
        )
    span_m = max(xmax - xmin, ymax - ymin) if xmax > -math.inf else 1.0
    road_lw, link_lw = _scaled_line_widths(span_m)

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

            # Only add the legend label to the first zone to avoid duplicates
            label_zone = "Zonas (radio de influencia)" if z_idx == 0 else ""

            if len(nodes) == 1:
                # It's a point -> Draw a circle
                cx = nodes[0]["x"] / 65536.0
                cy = nodes[0]["y"] / 65536.0
                circle = patches.Circle(
                    (cx, cy), radius, color=ZONE_COLOR, alpha=0.2, label=label_zone
                )
                ax.add_patch(circle)
                ax.text(cx, cy, zone_id, fontsize=8, ha="center", color="darkred")
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
                ax.text(cx, cy, zone_id, fontsize=8, ha="center", color="darkred")
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

    # Leyenda a la derecha pero MULTI-COLUMNA, para que su alto ≈ el del mapa y
    # no lo aplaste (el problema con mapas de decenas de roads). Fuente reducida.
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        max_rows = 30
        ncol = max(1, math.ceil(len(labels) / max_rows))
        ax.legend(
            handles,
            labels,
            bbox_to_anchor=(1.02, 1),
            loc="upper left",
            borderaxespad=0.0,
            ncol=ncol,
            fontsize=7,
            handlelength=1.5,
            columnspacing=1.0,
        )
    fig.tight_layout()

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
