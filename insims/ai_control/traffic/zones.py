"""Vigilancia de la cesión de paso (Fase 8): distancia a la línea de detención
y detección de amenazas de un RoadLink con cesión — tráfico del `to_road`
acercándose al punto de unión y, si el link referencia una zona, tráfico a
menos de T segundos de su punto de conflicto.

Compone los predicados puros de `yielding.py`; el orquestador decide con esto
si frenar ante la línea. El modelo viejo (zona-área + `priority_rules`) se
retiró de la conducta en el 8.3; sus restos de datos/UI caen en el 8.6."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from insims.ai_control.base import _MixinBase
from insims.ai_control.nav_modes.freeroam.geometry import (
    calc_dist_point_to_segment_2d,
)
from insims.ai_control.traffic.yielding import (
    DEFAULT_YIELD_TIME_S,
    forward_arc_dist_m,
    is_heading_towards,
    time_to_point_s,
)

if TYPE_CHECKING:
    from insims.ai_control.nav_modes.freeroam.graph import RoadLink
    from insims.users_management.main import AI, Player


class _ZonesMixin(_MixinBase):
    def _dist_to_yield_line_m(self, px: float, py: float, line: list) -> float:
        """Distancia 2D mínima desde (px, py) a la polilínea de la línea de
        detención. Sin línea utilizable (menos de 2 puntos) ⇒ inf (nunca se
        está "cerca" de una línea que no existe)."""
        if len(line) < 2:
            return math.inf
        return min(
            calc_dist_point_to_segment_2d(px, py, a.x_m, a.y_m, b.x_m, b.y_m)
            for a, b in zip(line, line[1:])
        )

    def _yield_threat_detected(self, ai: AI, link: RoadLink) -> bool:
        """¿Hay tráfico por el que el link con cesión debe frenar? (diseño S38)

        Vigilados:
          1. Los del `to_road` acercándose al punto de unión (último nodo del
             link): t = distancia hacia delante a lo largo de la vía / su
             velocidad. Parado ⇒ ∞ ⇒ se ignora; el que ya pasó el punto o va
             a contramano (no apunta hacia él) se excluye.
          2. Si el link referencia una zona: cualquiera a menos de T segundos
             del punto de conflicto apuntando hacia él — salvo los que van
             DETRÁS de la IA (si contaran, tus propios seguidores te dejarían
             clavado en la línea para siempre).

        Los umbrales T salen del link / la zona; `None` ⇒ default global de
        config (`yield_time_s`, inicial `DEFAULT_YIELD_TIME_S`).
        """
        junction = link.nodes[-1]
        default_t = self.config.get("yield_time_s", DEFAULT_YIELD_TIME_S)
        t_link = link.yield_time_s if link.yield_time_s is not None else default_t

        to_road = self.map_recorder.roads.get(link.to_road_id)
        junction_idx = None
        if to_road is not None and to_road.nodes:
            junction_idx, _ = self._get_closest_node_index(
                junction.x_m, junction.y_m, to_road.nodes
            )

        zone_point = None
        t_zone = default_t
        if link.yield_zone_id:
            zone = self.map_recorder.zones.get(link.yield_zone_id)
            if zone is not None and zone.nodes:
                zone_point = zone.nodes[0]
                if zone.yield_time_s is not None:
                    t_zone = zone.yield_time_s

        my = ai.player.telemetry
        my_x, my_y = my.coordinates.x_m, my.coordinates.y_m
        my_heading = my.heading.angle_lfs

        def es_amenaza(player: Player, road_id, node_idx) -> bool:
            coords = player.telemetry.coordinates
            speed_ms = player.telemetry.speed.speed_kmh / 3.6
            heading = player.telemetry.heading.angle_lfs

            # 1) Tráfico del to_road hacia el punto de unión.
            if junction_idx is not None and road_id == link.to_road_id:
                arc_m = forward_arc_dist_m(
                    to_road.nodes, node_idx, junction_idx, to_road.is_circular
                )
                if (
                    arc_m is not None
                    and is_heading_towards(
                        coords.x_m, coords.y_m, heading, junction.x_m, junction.y_m
                    )
                    and time_to_point_s(arc_m, speed_ms) <= t_link
                ):
                    return True

            # 2) Zona referenciada: punto de conflicto + T.
            if (
                zone_point is not None
                # Delante de la IA (los de detrás, excluidos):
                and is_heading_towards(my_x, my_y, my_heading, coords.x_m, coords.y_m)
                and is_heading_towards(
                    coords.x_m, coords.y_m, heading, zone_point.x_m, zone_point.y_m
                )
            ):
                dist_m = math.hypot(
                    zone_point.x_m - coords.x_m, zone_point.y_m - coords.y_m
                )
                if time_to_point_s(dist_m, speed_ms) <= t_zone:
                    return True

            return False

        # Humanos: no publican topología — se localizan por posición (nodo más
        # cercano de la vía más cercana, como el modelo viejo: find_links=False).
        for p in self.user_manager.players.values():
            if p.plid == ai.player.plid or not p.telemetry:
                continue
            ctx = self.map_recorder.get_location_context(
                p.telemetry.coordinates.x_m,
                p.telemetry.coordinates.y_m,
                p.telemetry.coordinates.z_m,
                find_links=False,
                find_zones=False,
            )
            if es_amenaza(p, ctx.road_id, ctx.road_node_idx):
                return True

        # IAs: su topología es fiable (current_id); su nodo se recalcula por
        # posición — node_index es el nodo OBJETIVO (va uno por delante, S35) y
        # cerca del punto de unión ese sesgo diría "ya pasó" justo al llegar.
        for a in self.user_manager.ais.values():
            player = a.player
            if player.plid == ai.player.plid or not player.telemetry:
                continue
            other_behavior = a.extra.get("aic")
            other_mode = other_behavior.active_mode if other_behavior else None
            road_id = other_mode.current_id if other_mode else None
            node_idx = 0
            if road_id == link.to_road_id and to_road is not None and to_road.nodes:
                node_idx, _ = self._get_closest_node_index(
                    player.telemetry.coordinates.x_m,
                    player.telemetry.coordinates.y_m,
                    to_road.nodes,
                )
            if es_amenaza(player, road_id, node_idx):
                return True

        return False
