"""Vigilancia de la cesión de paso del LINK (Fase 8; rediseñado en el 8.6/S44).

El link gobierna al que HACE LA MANIOBRA: distancia a su línea de detención
—que ya no se graba, se deriva del `yield_point`— y detección de amenazas en
los puntos de conflicto que su trazado se encuentra (todas las roads que pisa,
no solo la `to_road`).

Compone los predicados puros de `yielding.py`; el orquestador decide con esto
si frenar ante la línea. La zona (el que cruza de recto) es un mecanismo
ORTOGONAL y no se toca desde aquí: ni este módulo la mira, ni ella mira links.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, List

from insims.ai_control.base import _MixinBase
from insims.ai_control.nav_modes.freeroam.geometry import (
    calc_dist_point_to_segment_2d,
)
from insims.ai_control.traffic.yielding import (
    DEFAULT_YIELD_LINE_WIDTH_M,
    DEFAULT_YIELD_TIME_S,
    DEFAULT_YIELD_Z_TOLERANCE_M,
    derive_yield_line,
    forward_arc_dist_m,
    is_heading_towards,
    time_to_point_s,
)

if TYPE_CHECKING:
    from insims.ai_control.nav_modes.freeroam.graph import RoadLink
    from insims.users_management.main import AI, Player


class _ZonesMixin(_MixinBase):
    def _yield_line_of(self, link: RoadLink) -> List:
        """La línea de detención de un link, derivada de su `yield_point` (S44).

        Sin punto marcado ⇒ `[]`: no hay línea, y sin línea no se cede."""
        return derive_yield_line(
            link.nodes,
            link.yield_point,
            width_m=self.config.get("yield_line_width_m", DEFAULT_YIELD_LINE_WIDTH_M),
        )

    def _dist_to_yield_line_m(self, px: float, py: float, line: list) -> float:
        """Distancia 2D mínima desde (px, py) a la línea de detención. Sin línea
        utilizable (menos de 2 puntos) ⇒ inf (nunca se está "cerca" de una línea
        que no existe)."""
        if len(line) < 2:
            return math.inf
        return min(
            calc_dist_point_to_segment_2d(px, py, a.x_m, a.y_m, b.x_m, b.y_m)
            for a, b in zip(line, line[1:])
        )

    def _yield_threat_detected(self, ai: AI, link: RoadLink) -> bool:
        """¿Hay tráfico por el que este link debe frenar? (rediseño S44)

        Se vigila CADA punto de conflicto del link —los sitios donde su trazado
        pisa otra road, más el punto de unión con la `to_road`— y para cada uno
        solo el tráfico DE ESA road: t = distancia hacia delante a lo largo de
        la vía / su velocidad. Parado ⇒ ∞ ⇒ se ignora; el que ya pasó el punto
        (arco `None`) o va a contramano (no apunta hacia él) se excluye.

        Esto es lo que hace innecesaria la zona: el link se gana por geometría
        lo que antes le daba el `yield_zone_id`, que ya no existe.

        El umbral T sale del link; `None` ⇒ default global de config
        (`yield_time_s`, inicial `DEFAULT_YIELD_TIME_S`).
        """
        puntos = self.map_recorder.get_link_conflict_points(
            link,
            self.config.get("yield_z_tolerance_m", DEFAULT_YIELD_Z_TOLERANCE_M),
        )
        if not puntos:
            return False

        default_t = self.config.get("yield_time_s", DEFAULT_YIELD_TIME_S)
        t_link = link.yield_time_s if link.yield_time_s is not None else default_t

        # Los puntos se agrupan por road: solo el tráfico de la road cruzada
        # llega a su punto de conflicto (por la propia road, no en línea recta).
        por_road = {punto.road_id: punto for punto in puntos}

        def es_amenaza(player: Player, road_id, node_idx) -> bool:
            punto = por_road.get(road_id)
            if punto is None:
                return False
            road = self.map_recorder.roads.get(road_id)
            if road is None or not road.nodes:
                return False

            arc_m = forward_arc_dist_m(
                road.nodes, node_idx, punto.node_idx, road.is_circular
            )
            if arc_m is None:  # ya pasó el punto: no es amenaza
                return False

            coords = player.telemetry.coordinates
            if not is_heading_towards(
                coords.x_m,
                coords.y_m,
                player.telemetry.heading.angle_lfs,
                punto.x_m,
                punto.y_m,
            ):
                return False

            speed_ms = player.telemetry.speed.speed_kmh / 3.6
            return time_to_point_s(arc_m, speed_ms) <= t_link

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
        # cerca del punto de conflicto ese sesgo diría "ya pasó" justo al llegar.
        for a in self.user_manager.ais.values():
            player = a.player
            if player.plid == ai.player.plid or not player.telemetry:
                continue
            other_behavior = a.extra.get("aic")
            other_mode = other_behavior.active_mode if other_behavior else None
            road_id = other_mode.current_id if other_mode else None
            road = self.map_recorder.roads.get(road_id) if road_id else None
            node_idx = 0
            if road is not None and road.nodes:
                node_idx, _ = self._get_closest_node_index(
                    player.telemetry.coordinates.x_m,
                    player.telemetry.coordinates.y_m,
                    road.nodes,
                )
            if es_amenaza(player, road_id, node_idx):
                return True

        return False
