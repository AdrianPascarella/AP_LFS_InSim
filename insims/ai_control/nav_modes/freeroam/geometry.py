from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Tuple

from lfs_insim.utils import calc_dist_3d

if TYPE_CHECKING:
    from insims.users_management.main import Coordinates


def get_dist_to_polygon_edge_2d(
    px: float, py: float, nodes: List["Coordinates"]
) -> float:
    """Encuentra la distancia más corta desde un punto hasta el borde de un poligono."""
    min_dist = float("inf")
    n = len(nodes)

    for i in range(n):
        j = (i + 1) % n
        xi, yi = nodes[i].x_m, nodes[i].y_m
        xj, yj = nodes[j].x_m, nodes[j].y_m

        dist = calc_dist_point_to_segment_2d(px, py, xi, yi, xj, yj)

        if dist < min_dist:
            min_dist = dist

    return min_dist


def calc_dist_point_to_segment_2d(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    """Calcula la distancia minima desde un punto a un segmento de recta en 2D."""
    l2 = (x2 - x1) ** 2 + (y2 - y1) ** 2
    if l2 == 0:
        return math.hypot(px - x1, py - y1)

    t = max(0.0, min(1.0, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2))

    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)

    return math.hypot(px - proj_x, py - proj_y)


def segment_intersection_2d(
    ax: float,
    ay: float,
    bx: float,
    by: float,
    cx: float,
    cy: float,
    dx: float,
    dy: float,
) -> Optional[Tuple[float, float, float, float]]:
    """¿Dónde se cortan los segmentos AB y CD en XY?

    Devuelve ``(px, py, t_ab, t_cd)`` — el punto de cruce y su posición
    normalizada (0..1) sobre CADA segmento, que el llamante necesita para
    interpolar la Z en el cruce. Paralelos, degenerados o que solo se cortarían
    al prolongarlos ⇒ ``None``.
    """
    r_x, r_y = bx - ax, by - ay
    s_x, s_y = dx - cx, dy - cy

    denom = r_x * s_y - r_y * s_x
    if -1e-9 < denom < 1e-9:
        return None  # paralelos, colineales o algún segmento degenerado

    t_ab = ((cx - ax) * s_y - (cy - ay) * s_x) / denom
    t_cd = ((cx - ax) * r_y - (cy - ay) * r_x) / denom
    if not (0.0 <= t_ab <= 1.0 and 0.0 <= t_cd <= 1.0):
        return None  # el cruce cae fuera de alguno de los dos segmentos

    return ax + t_ab * r_x, ay + t_ab * r_y, t_ab, t_cd


def is_point_in_polygon_2d(px: float, py: float, nodes: List["Coordinates"]) -> bool:
    """Algoritmo de Ray-Casting para saber si un punto 2D esta dentro de un poligono."""
    inside = False
    n = len(nodes)
    j = n - 1

    for i in range(n):
        xi, yi = nodes[i].x_m, nodes[i].y_m
        xj, yj = nodes[j].x_m, nodes[j].y_m

        intersect = ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi) + xi
        )

        if intersect:
            inside = not inside
        j = i

    return inside


# ==========================================================================
# Geometría / navegación de la IA (migrado de lfs_insim.utils en W1, Fase 6).
# Es matemática específica de ai_control (rumbos LFS, captura de waypoints,
# radar longitudinal/lateral), no primitivas genéricas del framework.
# ==========================================================================


def calc_target_heading(
    current_x: int, current_y: int, target_x: int, target_y: int, rev: bool = False
) -> int:
    """
    Calcula el rumbo (Heading) necesario para mirar hacia un objetivo.
    Devuelve el ángulo en unidades LFS (0 - 65535).
    Si rev=True, devuelve el rumbo opuesto (ideal para dirigir el coche en marcha atrás).
    """
    # En LFS: +Y es Norte, +X es Oeste.
    dx = current_x - target_x
    dy = target_y - current_y
    rad = math.atan2(dx, dy)

    if rad < 0:
        rad += 2 * math.pi

    heading = int((rad / (2 * math.pi)) * 65536) % 65536

    if rev:
        # Sumamos media vuelta entera (180 grados = 32768 unidades LFS)
        return (heading + 32768) % 65536

    return heading


def get_heading_diff(target_h: int, current_h: int) -> int:
    """
    Calcula el error direccional más corto.
    Recibe y devuelve valores en unidades LFS (-32768 a 32768).
    """
    return (target_h - current_h + 32768) % 65536 - 32768


def calc_deviation_angle(x1: int, y1: int, x2: int, y2: int, x3: int, y3: int) -> int:
    """
    Calcula el ángulo de desviación entre la línea de los 2 puntos
    previos y el nuevo punto.

    Segmento 1: De (x1, y1) a (x2, y2)
    Segmento 2: De (x2, y2) a (x3, y3)

    Retorna:
        int: Ángulo de desviación en unidades LFS (-32768 a 32768).
             0 significa que la trayectoria sigue en línea recta perfecta.
             Valores positivos/negativos indican giro a la izquierda o derecha.
    """
    # 1. Calculamos el ángulo (rumbo) de ambos segmentos en radianes
    theta1 = math.atan2(y2 - y1, x2 - x1)
    theta2 = math.atan2(y3 - y2, x3 - x2)

    # 2. Encontramos la diferencia
    diff_rad = theta2 - theta1

    # 3. Normalizamos el ángulo para que esté en el rango de -pi a pi radianes
    diff_rad = (diff_rad + math.pi) % (2 * math.pi) - math.pi

    # 4. Convertimos de radianes a unidades LFS (pi radianes = 32768 unidades)
    return int((diff_rad / math.pi) * 32768)


def calc_dist_point_to_segment_3d(px, py, pz, ax, ay, az, bx, by, bz):
    """Calcula la distancia mínima entre un punto (P) y un segmento de línea (A-B)."""
    # Vector AB (El segmento de la calle)
    abx, aby, abz = bx - ax, by - ay, bz - az

    # Vector AP (Del inicio del segmento hasta el jugador)
    apx, apy, apz = px - ax, py - ay, pz - az

    # Producto punto para proyectar AP sobre AB
    ap_ab = apx * abx + apy * aby + apz * abz
    ab_ab = abx * abx + aby * aby + abz * abz

    if ab_ab == 0:
        # Los puntos A y B son idénticos (el segmento es un punto)
        return math.sqrt(apx**2 + apy**2 + apz**2)

    # 't' es la posición normalizada (0 a 1) en el segmento AB
    t = ap_ab / ab_ab

    if t <= 0.0:
        # El jugador está "por detrás" del inicio del segmento (Punto A es el más cercano)
        return math.sqrt(apx**2 + apy**2 + apz**2)
    elif t >= 1.0:
        # El jugador está "por delante" del final del segmento (Punto B es el más cercano)
        bpx, bpy, bpz = px - bx, py - by, pz - bz
        return math.sqrt(bpx**2 + bpy**2 + bpz**2)
    else:
        # El jugador está paralelo al segmento (Calculamos la distancia perpendicular)
        # CORRECCIÓN: Faltaba calcular cx y cy
        cx = ax + t * abx
        cy = ay + t * aby
        cz = az + t * abz

        cpx, cpy, cpz = px - cx, py - cy, pz - cz
        return math.sqrt(cpx**2 + cpy**2 + cpz**2)


def get_closest_node_index(
    my_coords: Any, list_of_nodes: list[Any], is_waypoint: bool = False
) -> int:
    """
    Encuentra el índice del nodo o waypoint más cercano a unas coordenadas.
    Args:
        my_coords: Objeto con x_m, y_m, z_m
        list_of_nodes: Lista de Nodos (Route.waypoints o RoadSegment.nodes)
        is_waypoint: Si es True, asume que list_of_nodes contiene objetos Waypoint y
                     accede a .coordinates. De lo contrario, asume que los nodos en sí tienen x_m...
    """
    min_dist = float("inf")
    best_idx = 0
    total_nodes = len(list_of_nodes)

    for i in range(total_nodes):
        node = list_of_nodes[i]
        coords = node.coordinates if is_waypoint else node

        dist = calc_dist_3d(
            my_coords.x_m,
            my_coords.y_m,
            my_coords.z_m,
            coords.x_m,
            coords.y_m,
            coords.z_m,
        )
        if dist < min_dist:
            min_dist = dist
            best_idx = i

    return best_idx


def determine_smart_spawn_index(
    my_coords: Any,
    closest_idx: int,
    list_of_nodes: list[Any],
    is_waypoint: bool = False,
) -> int:
    """
    Decide lógicamente si el coche debe apuntar al nodo más cercano o al siguiente en la serie (Smart Spawn).
    Evita que el coche intente girar 180º para ir a un nodo que acaba de pasar.
    """
    total_nodes = len(list_of_nodes)
    if total_nodes < 2:
        return closest_idx

    # En rutas (circuito cerrado) damos la vuelta. En freeroam (segmento abierto) tenemos límites.
    prev_idx = (
        (closest_idx - 1) % total_nodes if is_waypoint else max(0, closest_idx - 1)
    )
    next_idx = (
        (closest_idx + 1) % total_nodes
        if is_waypoint
        else min(total_nodes - 1, closest_idx + 1)
    )

    node_prev = (
        list_of_nodes[prev_idx].coordinates if is_waypoint else list_of_nodes[prev_idx]
    )
    node_next = (
        list_of_nodes[next_idx].coordinates if is_waypoint else list_of_nodes[next_idx]
    )

    dist_to_prev = calc_dist_3d(
        my_coords.x_m,
        my_coords.y_m,
        my_coords.z_m,
        node_prev.x_m,
        node_prev.y_m,
        node_prev.z_m,
    )
    dist_to_next = calc_dist_3d(
        my_coords.x_m,
        my_coords.y_m,
        my_coords.z_m,
        node_next.x_m,
        node_next.y_m,
        node_next.z_m,
    )

    if dist_to_next < dist_to_prev:
        return next_idx
    return closest_idx


def apply_antilag_window(
    my_coords: Any,
    current_idx: int,
    list_of_nodes: list[Any],
    window_size: int = 15,
    is_waypoint: bool = False,
    is_driving_opposing: bool = False,
) -> int:
    """
    Escanea hacia el futuro para recuperar el hilo si un nodo ha quedado por detrás debido
    a ping, lagazos de física o un spawn agresivo. Soporta sentido contrario.
    """
    total_nodes = len(list_of_nodes)
    if total_nodes == 0:
        return current_idx
    if not is_driving_opposing and current_idx >= total_nodes:
        return current_idx
    if is_driving_opposing and current_idx < 0:
        return current_idx

    best_index = current_idx
    min_dist = float("inf")

    # Calcular hasta dónde podemos mirar sin salirnos de la lista
    if is_waypoint:
        search_window = min(window_size, total_nodes)
    else:
        if is_driving_opposing:
            search_window = min(
                window_size, current_idx + 1
            )  # Solo podemos retroceder hasta el índice 0
        else:
            search_window = min(window_size, total_nodes - current_idx)

    for i in range(search_window):
        if is_waypoint:
            # Ventana circular
            check_idx = (
                (current_idx - i) % total_nodes
                if is_driving_opposing
                else (current_idx + i) % total_nodes
            )
        else:
            # Ventana lineal
            check_idx = current_idx - i if is_driving_opposing else current_idx + i

        node_check = (
            list_of_nodes[check_idx].coordinates
            if is_waypoint
            else list_of_nodes[check_idx]
        )

        dist = calc_dist_3d(
            my_coords.x_m,
            my_coords.y_m,
            my_coords.z_m,
            node_check.x_m,
            node_check.y_m,
            node_check.z_m,
        )

        if dist < min_dist:
            min_dist = dist
            best_index = check_idx

    return best_index


def evaluate_dynamic_capture(
    my_coords: Any,
    current_target_idx: int,
    list_of_nodes: list[Any],
    speed_kmh: float,
    min_radius: float = 1.0,
    max_radius: float = 10.0,
    lookahead_time: float = 0.5,
    is_waypoint: bool = False,
    is_driving_opposing: bool = False,
) -> int:
    """
    Calcula el Radio de Captura Dinámico.
    Si está en modo opposing, decrementa el índice al capturar el nodo en lugar de incrementarlo.
    """
    total_nodes = len(list_of_nodes)
    if not is_driving_opposing and current_target_idx >= total_nodes:
        return current_target_idx
    if is_driving_opposing and current_target_idx < 0:
        return current_target_idx

    speed_ms = speed_kmh / 3.6
    dynamic_capture_radius = max(
        min_radius, min(max_radius, min_radius + (speed_ms * lookahead_time))
    )

    target_node = (
        list_of_nodes[current_target_idx].coordinates
        if is_waypoint
        else list_of_nodes[current_target_idx]
    )

    dist_to_target = calc_dist_3d(
        my_coords.x_m,
        my_coords.y_m,
        my_coords.z_m,
        target_node.x_m,
        target_node.y_m,
        target_node.z_m,
    )

    if dist_to_target < dynamic_capture_radius:
        # Aquí invertimos la matemática de progresión
        next_idx = (
            current_target_idx - 1 if is_driving_opposing else current_target_idx + 1
        )

        if is_waypoint:
            if not is_driving_opposing and next_idx >= total_nodes:
                return 0
            if is_driving_opposing and next_idx < 0:
                return total_nodes - 1

        return next_idx

    return current_target_idx


def find_road_pointed_at(
    px: float,
    py: float,
    fwd_x: float,
    fwd_y: float,
    roads: Iterable[Tuple[str, Any]],
    exclude_id: Optional[str],
    max_dist_m: float,
) -> Tuple[Optional[str], float]:
    """Ray-cast 2D: ¿a qué road apunta el morro del coche y a qué distancia?

    Lanza un rayo desde (px, py) en la dirección (fwd_x, fwd_y) y devuelve el
    ``(road_id, distancia)`` del road cuyo segmento cruza el rayo MÁS CERCA del
    origen, dentro de ``max_dist_m``. Ignora ``exclude_id`` (el road sobre el que
    ya estás) y los roads que el rayo no toca. Si no toca ninguno: ``(None, inf)``.

    Pensado para mapear: apuntas el morro a una vía y te dice cuál es y cuánto
    falta. ``roads`` es un iterable de ``(road_id, road)`` con ``road.nodes`` (nodos
    con ``.x_m``/``.y_m``). ``(fwd_x, fwd_y)`` no necesita estar normalizado; la
    distancia es euclídea 2D a lo largo del rayo hasta el punto de impacto.
    """
    mag = math.hypot(fwd_x, fwd_y)
    if mag == 0.0:
        return None, float("inf")
    dx, dy = fwd_x / mag, fwd_y / mag
    # Perpendicular a la dirección del rayo, para el test rayo-segmento 2D.
    perp_x, perp_y = -dy, dx

    best_id: Optional[str] = None
    best_t = max_dist_m
    for road_id, road in roads:
        if road_id == exclude_id:
            continue
        nodes = road.nodes
        for i in range(len(nodes) - 1):
            ax, ay = nodes[i].x_m, nodes[i].y_m
            ex = nodes[i + 1].x_m - ax
            ey = nodes[i + 1].y_m - ay
            denom = ex * perp_x + ey * perp_y
            if -1e-9 < denom < 1e-9:
                continue  # segmento paralelo al rayo
            v1x, v1y = px - ax, py - ay
            # u = posición del cruce sobre el segmento (debe caer en [0, 1])
            u = (v1x * perp_x + v1y * perp_y) / denom
            if u < 0.0 or u > 1.0:
                continue
            # t = distancia del cruce a lo largo del rayo (>= 0 y la más corta)
            t = (ex * v1y - ey * v1x) / denom
            if 0.0 <= t < best_t:
                best_t = t
                best_id = road_id
    if best_id is None:
        return None, float("inf")
    return best_id, best_t
