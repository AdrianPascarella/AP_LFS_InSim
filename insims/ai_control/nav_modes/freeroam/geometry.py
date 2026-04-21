from __future__ import annotations
import math
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from insims.users_management.main import Coordinates


def get_dist_to_polygon_edge_2d(px: float, py: float, nodes: List['Coordinates']) -> float:
    """Encuentra la distancia más corta desde un punto hasta el borde de un poligono."""
    min_dist = float('inf')
    n = len(nodes)

    for i in range(n):
        j = (i + 1) % n
        xi, yi = nodes[i].x_m, nodes[i].y_m
        xj, yj = nodes[j].x_m, nodes[j].y_m

        dist = calc_dist_point_to_segment_2d(px, py, xi, yi, xj, yj)

        if dist < min_dist:
            min_dist = dist

    return min_dist

def calc_dist_point_to_segment_2d(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Calcula la distancia minima desde un punto a un segmento de recta en 2D."""
    l2 = (x2 - x1)**2 + (y2 - y1)**2
    if l2 == 0:
        return math.hypot(px - x1, py - y1)

    t = max(0.0, min(1.0, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2))

    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)

    return math.hypot(px - proj_x, py - proj_y)

def is_point_in_polygon_2d(px: float, py: float, nodes: List['Coordinates']) -> bool:
    """Algoritmo de Ray-Casting para saber si un punto 2D esta dentro de un poligono."""
    inside = False
    n = len(nodes)
    j = n - 1

    for i in range(n):
        xi, yi = nodes[i].x_m, nodes[i].y_m
        xj, yj = nodes[j].x_m, nodes[j].y_m

        intersect = ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi)

        if intersect:
            inside = not inside
        j = i

    return inside
