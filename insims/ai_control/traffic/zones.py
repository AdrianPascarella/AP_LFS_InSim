"""Geometría de las zonas de intersección (círculo / cápsula / polígono) y
detección de vehículos con prioridad de paso."""

from __future__ import annotations

import math

from insims.ai_control.base import _MixinBase
from insims.ai_control.nav_modes.freeroam.geometry import (
    calc_dist_point_to_segment_2d,
    get_dist_to_polygon_edge_2d,
    is_point_in_polygon_2d,
)
from insims.ai_control.nav_modes.freeroam.graph import IntersectionZone


class _ZonesMixin(_MixinBase):
    def _is_point_in_zone(self, px: float, py: float, zone: IntersectionZone) -> bool:
        """Verifica si un punto está dentro de la zona usando tus funciones geométricas."""
        nodes = zone.nodes
        n_nodes = len(nodes)

        if n_nodes == 0:
            return False
        elif n_nodes == 1:
            # Es un círculo
            return math.hypot(px - nodes[0].x_m, py - nodes[0].y_m) <= zone.radius_m
        elif n_nodes == 2:
            # Es una línea con grosor (cápsula)
            dist = calc_dist_point_to_segment_2d(
                px, py, nodes[0].x_m, nodes[0].y_m, nodes[1].x_m, nodes[1].y_m
            )
            return dist <= zone.radius_m
        else:
            # Es un polígono
            return is_point_in_polygon_2d(px, py, nodes)

    def _get_dist_to_zone_edge(self, px: float, py: float, zone) -> float:
        """Calcula la distancia exacta desde el coche hasta el borde geométrico de la zona."""
        nodes = zone.nodes
        n_nodes = len(nodes)

        if n_nodes == 0:
            return float("inf")
        elif n_nodes == 1:
            dist = math.hypot(px - nodes[0].x_m, py - nodes[0].y_m) - zone.radius_m
        elif n_nodes == 2:
            dist = (
                calc_dist_point_to_segment_2d(
                    px, py, nodes[0].x_m, nodes[0].y_m, nodes[1].x_m, nodes[1].y_m
                )
                - zone.radius_m
            )
        else:
            if is_point_in_polygon_2d(px, py, nodes):
                return 0.0  # Ya estamos dentro del polígono
            dist = get_dist_to_polygon_edge_2d(px, py, nodes)

        # Devolvemos max(0.0, dist) para evitar distancias negativas si penetramos un poco la zona
        return max(0.0, dist)

    def _get_zone_centroid(self, zone) -> tuple:
        nodes = zone.nodes
        if not nodes:
            return 0.0, 0.0
        cx = sum(n.x_m for n in nodes) / len(nodes)
        cy = sum(n.y_m for n in nodes) / len(nodes)
        return cx, cy

    def _is_priority_vehicle_active_at_zone(
        self,
        vehicle_coords,
        vehicle_speed_kmh: float,
        vehicle_heading_lfs: int,
        zone,
        approach_time_s: float = 4.0,
    ) -> bool:
        """True si el vehículo está dentro de la zona O se aproxima a ella con dirección hacia ella."""
        if self._is_point_in_zone(vehicle_coords.x_m, vehicle_coords.y_m, zone):
            return True

        dist_to_edge = self._get_dist_to_zone_edge(
            vehicle_coords.x_m, vehicle_coords.y_m, zone
        )
        speed_ms = max(vehicle_speed_kmh / 3.6, 0.5)

        if dist_to_edge / speed_ms > approach_time_s:
            return False

        # Comprobación de dirección: ¿apunta hacia el centroide de la zona?
        heading_rad = vehicle_heading_lfs * 2.0 * math.pi / 65536.0
        fwd_x = -math.sin(heading_rad)
        fwd_y = math.cos(heading_rad)
        zone_cx, zone_cy = self._get_zone_centroid(zone)
        vec_x = zone_cx - vehicle_coords.x_m
        vec_y = zone_cy - vehicle_coords.y_m
        return (fwd_x * vec_x + fwd_y * vec_y) > 0.0
