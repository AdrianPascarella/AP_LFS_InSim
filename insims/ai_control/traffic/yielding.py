"""Predicados PUROS de la cesión de paso (Fase 8, S38; ampliado en el 8.6/S44).

Sin estado y sin LFS: la conducta los compone desde el orquestador de tráfico.
Un solo concepto — tiempo-al-punto — que sirve a los DOS mecanismos ortogonales
del diseño S44, sin que ninguno se refiera al otro:

- el **link** (el que hace la maniobra) vigila los puntos de conflicto que su
  trazado se encuentra: `link_conflict_points`;
- la **zona** (el que cruza de recto) vigila el borde de su polígono, con las
  roads que lo pisan: `roads_touching_polygon`.

Aquí vive además la geometría propia de la cesión: los puntos de conflicto, la
línea de detención derivada del `yield_point` y el auto-poblado de la tabla de
la zona. La matemática genérica (cruce de segmentos, punto-en-polígono) está en
`nav_modes/freeroam/geometry.py`.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, NamedTuple, Optional

from insims.ai_control.nav_modes.freeroam.geometry import (
    calc_dist_point_to_segment_2d,
    is_point_in_polygon_2d,
    segment_intersection_2d,
)
from insims.users_management.um_class import Coordinates

# Ventana por defecto de la cesión (s): se cede si el vigilado llega en menos
# de este tiempo. Heredada del modelo viejo (_is_priority_vehicle_active_at_zone
# usaba 4.0 s). Se sobreescribe por link/zona con su campo `yield_time_s`.
DEFAULT_YIELD_TIME_S = 4.0

# Por debajo de esta velocidad el vehículo se considera PARADO y deja de ser
# amenaza (tiempo-al-punto = inf). Cambio deliberado respecto al modelo viejo,
# que usaba este mismo valor como SUELO de velocidad (y contaba a los parados).
STOPPED_SPEED_MS = 0.5

# ─── Diales del rediseño S44 (config: `yield_*`) ────────────────────────────

# Ancho (m) de la línea de detención que se DERIVA del `yield_point`. Cubre el
# carril de lado a lado: es la cuerda contra la que se mide el compromiso.
DEFAULT_YIELD_LINE_WIDTH_M = 6.0

# Cuánto aguanta parado un `STOP` antes de volver a evaluar como `YIELD` (s).
DEFAULT_YIELD_STOP_HOLD_S = 1.0

# Tolerancia en altura (m) al detectar cruces: por encima de esto no es un
# cruce sino un puente / paso inferior, y no se cede a quien pasa por debajo.
DEFAULT_YIELD_Z_TOLERANCE_M = 3.0


class ConflictPoint(NamedTuple):
    """Un sitio donde el trazado de un link se cruza con una road.

    `node_idx` es el nodo de ESA road más cercano al cruce: con él se mide el
    arco que le falta a un coche de esa road para llegar al conflicto.
    """

    road_id: str
    x_m: float
    y_m: float
    node_idx: int


def time_to_point_s(dist_m: float, speed_ms: float) -> float:
    """Tiempo (s) en llegar a un punto a `dist_m` metros yendo a `speed_ms`.

    Distancia ya consumida ⇒ 0.0 (amenaza inmediata: está en el punto).
    Parado o casi (< STOPPED_SPEED_MS) ⇒ inf (un coche detenido no viene).
    """
    if dist_m <= 0.0:
        return 0.0
    if speed_ms < STOPPED_SPEED_MS:
        return math.inf
    return dist_m / speed_ms


def forward_arc_dist_m(
    nodes: List["Coordinates"],
    from_idx: int,
    to_idx: int,
    is_circular: bool = False,
) -> Optional[float]:
    """Distancia (m) hacia DELANTE por la polilínea desde `from_idx` a `to_idx`.

    El orden de los nodos ES el sentido de circulación de la vía.
    Lineal: None si `from_idx` > `to_idx` — el coche ya pasó el punto y no es
    amenaza. Circular: envuelve por el cierre implícito último→primero (en una
    vía circular nunca se "pasa" el punto: siempre se vuelve a él).
    """
    n = len(nodes)
    if not (0 <= from_idx < n and 0 <= to_idx < n):
        return None
    if from_idx == to_idx:
        return 0.0
    if from_idx > to_idx and not is_circular:
        return None

    total = 0.0
    i = from_idx
    while i != to_idx:
        j = (i + 1) % n
        a, b = nodes[i], nodes[j]
        total += math.hypot(b.x_m - a.x_m, b.y_m - a.y_m)
        i = j
    return total


def _cross_2d(ax: float, ay: float, bx: float, by: float, px: float, py: float):
    """Producto cruzado 2D del vector a→b con a→p (signo = lado de la línea)."""
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


def has_crossed_line(
    px: float,
    py: float,
    line: List["Coordinates"],
    ref_x: float,
    ref_y: float,
) -> bool:
    """¿(px, py) ya cruzó la línea de detención? (punto de compromiso, S38).

    True si el punto está ESTRICTAMENTE del mismo lado de la cuerda
    (primer→último punto de la línea) que la referencia (ref_x, ref_y) — el
    punto de unión, que por construcción queda pasada la línea. Sobre la
    línea aún NO se ha cruzado (detenerse EN la línea no compromete).
    Sin línea utilizable (menos de 2 puntos) ⇒ False.
    """
    if len(line) < 2:
        return False
    ax, ay = line[0].x_m, line[0].y_m
    bx, by = line[-1].x_m, line[-1].y_m

    side_pos = _cross_2d(ax, ay, bx, by, px, py)
    side_ref = _cross_2d(ax, ay, bx, by, ref_x, ref_y)
    if side_pos == 0.0 or side_ref == 0.0:
        return False
    return (side_pos > 0.0) == (side_ref > 0.0)


def closest_node_idx_2d(x_m: float, y_m: float, nodes: List["Coordinates"]) -> int:
    """Índice del nodo (2D) más cercano a (x_m, y_m). Lista vacía ⇒ 0."""
    best_idx, best_dist = 0, math.inf
    for i, node in enumerate(nodes):
        dist = math.hypot(node.x_m - x_m, node.y_m - y_m)
        if dist < best_dist:
            best_idx, best_dist = i, dist
    return best_idx


def link_conflict_points(
    link_nodes: List["Coordinates"],
    roads: Dict[str, object],
    z_tolerance_m: float = DEFAULT_YIELD_Z_TOLERANCE_M,
    exclude_ids: Iterable[str] = (),
) -> List[ConflictPoint]:
    """Los puntos de conflicto que el trazado de un link se encuentra (S44).

    Ya NO se vigila solo la `to_road`: se cruza el trazado del link contra la
    geometría de TODAS las roads y cada cruce aporta un punto (el de unión
    sobre la `to_road` sale de aquí como uno más). Un cruce con más de
    `z_tolerance_m` de desnivel es un puente, no un cruce, y no cuenta.

    `exclude_ids` deja fuera roads concretas — en producción, la `from_road`:
    de la vía que dejas atrás no se cede, y el "primer cruce real" del diseño
    es con otra vía.

    Una road pisada varias veces aporta solo su cruce MÁS TEMPRANO (el primero
    que te encuentras siguiendo el trazado): es el que manda al conducir.
    """
    if len(link_nodes) < 2:
        return []

    excluded = set(exclude_ids)
    # {road_id: (orden_del_cruce_a_lo_largo_del_link, ConflictPoint)}
    best: Dict[str, tuple] = {}

    for seg_i in range(len(link_nodes) - 1):
        a, b = link_nodes[seg_i], link_nodes[seg_i + 1]
        for road_id, road in roads.items():
            if road_id in excluded:
                continue
            nodes = getattr(road, "nodes", [])
            for j in range(len(nodes) - 1):
                c, d = nodes[j], nodes[j + 1]
                hit = segment_intersection_2d(
                    a.x_m, a.y_m, b.x_m, b.y_m, c.x_m, c.y_m, d.x_m, d.y_m
                )
                if hit is None:
                    continue
                px, py, t_ab, t_cd = hit

                # Z interpolada en el cruce, a cada lado: ¿misma altura?
                z_link = a.z_m + t_ab * (b.z_m - a.z_m)
                z_road = c.z_m + t_cd * (d.z_m - c.z_m)
                if abs(z_link - z_road) > z_tolerance_m:
                    continue

                orden = seg_i + t_ab
                if road_id not in best or orden < best[road_id][0]:
                    best[road_id] = (
                        orden,
                        ConflictPoint(
                            road_id=road_id,
                            x_m=px,
                            y_m=py,
                            node_idx=closest_node_idx_2d(px, py, nodes),
                        ),
                    )

    return [punto for _, punto in sorted(best.values(), key=lambda item: item[0])]


def derive_yield_line(
    link_nodes: List["Coordinates"],
    yield_point: Optional["Coordinates"],
    width_m: float = DEFAULT_YIELD_LINE_WIDTH_M,
) -> List["Coordinates"]:
    """La línea de detención de un link, DERIVADA de su punto (S44).

    Ya no se graba punto a punto: el punto implica la línea. Devuelve los dos
    extremos de un segmento de `width_m` centrado en `yield_point` y
    perpendicular a la tangente del link ahí (la del tramo más cercano al
    punto, no la del link entero: en un link en L cada tramo tiene la suya).

    Sin punto o sin trazado utilizable ⇒ `[]` (no hay línea que derivar).
    """
    if yield_point is None or len(link_nodes) < 2:
        return []

    px, py = yield_point.x_m, yield_point.y_m

    # Tramo del link al que pertenece el punto = el que pasa más cerca de él.
    best_i, best_dist = 0, math.inf
    for i in range(len(link_nodes) - 1):
        a, b = link_nodes[i], link_nodes[i + 1]
        dist = calc_dist_point_to_segment_2d(px, py, a.x_m, a.y_m, b.x_m, b.y_m)
        if dist < best_dist:
            best_i, best_dist = i, dist

    a, b = link_nodes[best_i], link_nodes[best_i + 1]
    tan_x, tan_y = b.x_m - a.x_m, b.y_m - a.y_m
    mag = math.hypot(tan_x, tan_y)
    if mag == 0.0:
        return []
    # Perpendicular unitaria a la tangente, media anchura a cada lado.
    half = width_m / 2.0
    off_x, off_y = -tan_y / mag * half, tan_x / mag * half

    extremos = []
    for sign in (-1.0, 1.0):
        extremo = Coordinates(x=0, y=0, z=0)
        extremo.x_m = px + sign * off_x
        extremo.y_m = py + sign * off_y
        extremo.z_m = yield_point.z_m
        extremos.append(extremo)
    return extremos


def roads_touching_polygon(
    polygon_nodes: List["Coordinates"],
    roads: Dict[str, object],
    z_tolerance_m: float = DEFAULT_YIELD_Z_TOLERANCE_M,
) -> List[str]:
    """Las roads que pisan el polígono de una zona (S44): auto-poblado de su tabla.

    Pisa el que mete algún nodo DENTRO del polígono o cuyo trazado CRUZA el
    contorno. El filtro en Z (contra la altura media del polígono) deja fuera
    los falsos cruces por altura: un puente que sobrevuela el cruce no entra en
    la tabla.

    Polígono inválido (menos de 3 puntos) ⇒ `[]`: no hay contorno que pisar.
    Devuelve ids ordenados y sin repetir (la tabla de la UI es estable).
    """
    if len(polygon_nodes) < 3:
        return []

    z_ref = sum(node.z_m for node in polygon_nodes) / len(polygon_nodes)
    tocadas = set()

    for road_id, road in roads.items():
        nodes = getattr(road, "nodes", [])
        if not nodes:
            continue

        for i, node in enumerate(nodes):
            if abs(node.z_m - z_ref) > z_tolerance_m:
                continue
            if is_point_in_polygon_2d(node.x_m, node.y_m, polygon_nodes):
                tocadas.add(road_id)
                break

            if road_id in tocadas or i >= len(nodes) - 1:
                continue
            # ¿El tramo cruza alguna arista del polígono?
            nxt = nodes[i + 1]
            for j in range(len(polygon_nodes)):
                p, q = polygon_nodes[j], polygon_nodes[(j + 1) % len(polygon_nodes)]
                if segment_intersection_2d(
                    node.x_m,
                    node.y_m,
                    nxt.x_m,
                    nxt.y_m,
                    p.x_m,
                    p.y_m,
                    q.x_m,
                    q.y_m,
                ):
                    tocadas.add(road_id)
                    break
            if road_id in tocadas:
                break

    return sorted(tocadas)


def is_heading_towards(
    px: float, py: float, heading_lfs: int, tx: float, ty: float
) -> bool:
    """¿El morro apunta hacia (tx, ty)? (heading LFS: 0 = +Y, crece antihorario).

    Mismo criterio que el modelo viejo: producto escalar del vector frontal
    con el vector al objetivo > 0 (medio plano frontal).
    """
    heading_rad = heading_lfs * 2.0 * math.pi / 65536.0
    fwd_x = -math.sin(heading_rad)
    fwd_y = math.cos(heading_rad)
    return (fwd_x * (tx - px) + fwd_y * (ty - py)) > 0.0
