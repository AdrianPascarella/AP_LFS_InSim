"""Predicados PUROS de la cesión de paso (Fase 8, S38).

Sin estado y sin LFS: la conducta (bloque 8.3) los compone desde el
orquestador de tráfico. Un solo concepto — tiempo-al-punto — con dos formas
de "qué vigilo": el punto de unión del RoadLink (tráfico del `to_road`) y el
punto de conflicto de una `IntersectionZone` referenciada (tráfico cruzado).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from insims.users_management.um_class import Coordinates

# Ventana por defecto de la cesión (s): se cede si el vigilado llega en menos
# de este tiempo. Heredada del modelo viejo (_is_priority_vehicle_active_at_zone
# usaba 4.0 s). Se sobreescribe por link/zona con su campo `yield_time_s`.
DEFAULT_YIELD_TIME_S = 4.0

# Por debajo de esta velocidad el vehículo se considera PARADO y deja de ser
# amenaza (tiempo-al-punto = inf). Cambio deliberado respecto al modelo viejo,
# que usaba este mismo valor como SUELO de velocidad (y contaba a los parados).
STOPPED_SPEED_MS = 0.5


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
