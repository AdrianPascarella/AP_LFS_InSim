"""Radar de tráfico: barrido de vehículos en el carril propio, en el carril
objetivo de un adelantamiento y en el hueco de regreso.

Es el punto caliente del módulo (O(N) por IA → O(N²) global): aquí aterrizará
el índice espacial de vehículos (PLAN § Fase 6 · W3)."""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

from insims.ai_control.base import _MixinBase
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from lfs_insim.utils import calc_dist_3d

if TYPE_CHECKING:
    from insims.users_management.main import AI


class _RadarMixin(_MixinBase):
    def _scan_lane_ahead(
        self, ai: AI, mode: FreeroamMode, max_dist_m: float
    ) -> list[tuple[float, float, int]]:
        vehicles_ahead = []

        if not ai.player.telemetry:
            return vehicles_ahead

        my_coords = ai.player.telemetry.coordinates
        is_opposing = getattr(mode, "is_driving_opposing", False)

        # =========================================================
        # [!] OPTIMIZACIÓN 1: Obtener la geometría FUERA del bucle.
        # Si no hay geometría actual válida, ni siquiera iteramos.
        # =========================================================
        if mode.current_type == "Road":
            geom = self.map_recorder.roads.get(mode.current_id)
        elif mode.current_type == "RoadLink":
            geom = self.map_recorder.road_links.get(mode.current_id)
        else:
            geom = None

        if not geom or not geom.nodes:
            return vehicles_ahead

        # =========================================================
        # [!] OPTIMIZACIÓN 2: Pre-calcular constantes direccionales
        # Calculamos nuestro vector direccional y nuestra distancia
        # al siguiente nodo UNA sola vez antes de mirar a otros coches.
        # =========================================================
        curr_idx = max(0, min(mode.node_index, len(geom.nodes) - 1))

        # Índices para el vector de dirección (Dot Product) y para la distancia (Empates)
        if is_opposing:
            next_idx_dir = max(0, curr_idx - 1)
            if curr_idx == next_idx_dir:
                next_idx_dir = min(len(geom.nodes) - 1, curr_idx + 1)
            next_idx_dist = max(0, curr_idx - 1)
        else:
            next_idx_dir = min(curr_idx + 1, len(geom.nodes) - 1)
            if curr_idx == next_idx_dir:
                next_idx_dir = max(0, curr_idx - 1)
            next_idx_dist = min(curr_idx + 1, len(geom.nodes) - 1)

        # A. Vector direccional pre-calculado
        node_a = geom.nodes[curr_idx]
        node_b = geom.nodes[next_idx_dir]
        dir_x = node_b.x_m - node_a.x_m
        dir_y = node_b.y_m - node_a.y_m

        # B. Mi distancia al nodo pre-calculada
        target_node = geom.nodes[next_idx_dist]
        mi_dist_al_nodo = math.hypot(
            target_node.x_m - my_coords.x_m, target_node.y_m - my_coords.y_m
        )

        # =========================================================
        # 1. GENERADOR UNIFICADO
        # =========================================================
        def iter_all_vehicles():
            for p in self.user_manager.players.values():
                yield p, False, None
            for a in self.user_manager.ais.values():
                yield a.player, True, a

        # =========================================================
        # 2. ESCANEO Y DETECCIÓN (Bucle Caliente)
        # =========================================================
        for other_player, is_ai, other_ai in iter_all_vehicles():
            if other_player.plid == ai.player.plid or not other_player.telemetry:
                continue

            other_coords = other_player.telemetry.coordinates

            # [!] OPTIMIZACIÓN 3: Bounding Box Check rápido antes del hypot
            dx = my_coords.x_m - other_coords.x_m
            dy = my_coords.y_m - other_coords.y_m

            if abs(dx) > max_dist_m + 15.0 or abs(dy) > max_dist_m + 15.0:
                continue

            fast_dist = math.hypot(dx, dy)
            if fast_dist > max_dist_m + 15.0:
                continue

            other_road_id = None
            other_node_index = -1

            # ---------------------------------------------------------
            # EXTRACCIÓN TOPOLÓGICA
            # ---------------------------------------------------------
            if is_ai and other_ai and "aic" in other_ai.extra:
                other_mode = other_ai.extra["aic"].active_mode
                if other_mode and other_mode.current_id:
                    other_road_id = other_mode.current_id
                    other_node_index = other_mode.node_index
            else:
                current_time = time.time()
                if len(self._radar_human_cache) > 64:
                    self._radar_human_cache = {
                        plid: d
                        for plid, d in self._radar_human_cache.items()
                        if current_time - d[0] < 10.0
                    }
                cached_data = self._radar_human_cache.get(other_player.plid)

                if not cached_data or (current_time - cached_data[0]) > 0.1:
                    ctx = self.map_recorder.get_location_context(
                        other_coords.x_m, other_coords.y_m, other_coords.z_m
                    )
                    calc_road_id = (
                        ctx.link_id
                        if (ctx.link_id and ctx.link_dist < ctx.road_dist)
                        else ctx.road_id
                    )
                    calc_node_index = -1

                    # [!] OPTIMIZACIÓN 4: Solo calculamos el índice exacto del jugador si comparte nuestra calle
                    if calc_road_id == mode.current_id:
                        calc_node_index, _ = self._get_closest_node_index(
                            other_coords.x_m, other_coords.y_m, geom.nodes
                        )

                    self._radar_human_cache[other_player.plid] = (
                        current_time,
                        calc_road_id,
                        calc_node_index,
                    )
                    other_road_id = calc_road_id
                    other_node_index = calc_node_index
                else:
                    _, other_road_id, other_node_index = cached_data

            # ---------------------------------------------------------
            # FILTROS ESTRICTOS DE CARRIL
            # ---------------------------------------------------------
            if not other_road_id:
                continue

            same_segment = other_road_id == mode.current_id

            # Si estamos en un Road y el otro ya está en nuestro próximo RoadLink,
            # lo tratamos como obstáculo adelante (evita pileup en la entrada del link)
            in_our_next_link = (
                not same_segment
                and mode.current_type == "Road"
                and mode.next_link_id
                and mode.next_link_type == "RoadLink"
                and other_road_id == mode.next_link_id
            )

            if not same_segment and not in_our_next_link:
                continue

            if same_segment:
                idx_diff = (
                    mode.node_index - other_node_index
                    if is_opposing
                    else other_node_index - mode.node_index
                )

                # Vehículo en nodo inferior = detrás de nosotros → nunca es bloqueante
                if idx_diff < 0:
                    continue

                if idx_diff == 0:
                    su_dist_al_nodo = math.hypot(
                        target_node.x_m - other_coords.x_m,
                        target_node.y_m - other_coords.y_m,
                    )
                    if su_dist_al_nodo > mi_dist_al_nodo:
                        continue
                    if (
                        abs(su_dist_al_nodo - mi_dist_al_nodo) < 0.3
                        and ai.player.plid < other_player.plid
                    ):
                        continue

                elif idx_diff <= 3:
                    vec_x = other_coords.x_m - my_coords.x_m
                    vec_y = other_coords.y_m - my_coords.y_m
                    if (dir_x * vec_x) + (dir_y * vec_y) <= 0:
                        continue
            # in_our_next_link: el otro ya está en el RoadLink que vamos a entrar.
            # Solo necesitamos verificar que está delante (dot product positivo).
            else:
                vec_x = other_coords.x_m - my_coords.x_m
                vec_y = other_coords.y_m - my_coords.y_m
                if (dir_x * vec_x) + (dir_y * vec_y) <= 0:
                    continue

            # ---------------------------------------------------------
            # CÁLCULO DE DISTANCIA FINAL
            # ---------------------------------------------------------
            dist_m = calc_dist_3d(
                my_coords.x_m,
                my_coords.y_m,
                my_coords.z_m,
                other_coords.x_m,
                other_coords.y_m,
                other_coords.z_m,
            )

            if dist_m <= max_dist_m:
                vehicles_ahead.append(
                    (dist_m, other_player.telemetry.speed.speed_kmh, other_player.plid)
                )

        # =========================================================
        # 3. ORDENACIÓN
        # =========================================================
        vehicles_ahead.sort(key=lambda x: x[0])
        return vehicles_ahead

    def _scan_target_lane(
        self, ai: AI, mode: FreeroamMode, target_road_id: str, max_dist_m: float
    ) -> list[tuple[float, float, int]]:
        """
        Escanea un carril específico usando una caché independiente
        para evitar sobreescribir los datos del radar principal.
        """
        vehicles_ahead = []
        if not ai.player.telemetry:
            return vehicles_ahead

        my_coords = ai.player.telemetry.coordinates

        def iter_all_vehicles():
            for p in self.user_manager.players.values():
                yield p, False, None
            for a in self.user_manager.ais.values():
                yield a.player, True, a

        # =========================================================
        # VECTOR DIRECCIONAL BASE (Para saber qué es "hacia adelante")
        # =========================================================
        curr_geom = (
            self.map_recorder.roads.get(mode.current_id)
            or self.map_recorder.road_links.get(mode.current_id)
            or self.map_recorder.lateral_links.get(mode.current_id)
        )
        if not curr_geom or not curr_geom.nodes:
            return []

        curr_idx = min(mode.node_index, len(curr_geom.nodes) - 1)
        next_idx = min(curr_idx + 1, len(curr_geom.nodes) - 1)
        if curr_idx == next_idx:
            curr_idx = max(0, curr_idx - 1)

        my_dir_x = curr_geom.nodes[next_idx].x_m - curr_geom.nodes[curr_idx].x_m
        my_dir_y = curr_geom.nodes[next_idx].y_m - curr_geom.nodes[curr_idx].y_m

        # =========================================================
        # ESCANEO Y DETECCIÓN (Con caché aislada)
        # =========================================================
        for other_player, is_ai, other_ai in iter_all_vehicles():
            if other_player.plid == ai.player.plid or not other_player.telemetry:
                continue

            other_coords = other_player.telemetry.coordinates

            # Culling espacial rápido 2D
            fast_dist = math.hypot(
                my_coords.x_m - other_coords.x_m, my_coords.y_m - other_coords.y_m
            )
            if fast_dist > max_dist_m + 15.0:
                continue

            # Extracción Topológica
            other_road_id = None
            if is_ai and other_ai and "aic" in other_ai.extra:
                other_mode: FreeroamMode = other_ai.extra["aic"].active_mode
                if other_mode:
                    other_road_id = other_mode.current_id
            else:
                # [!] Usamos una caché propia para este escaner: _target_lane_human_cache
                current_time = time.time()
                if len(self._target_lane_human_cache) > 64:
                    self._target_lane_human_cache = {
                        plid: d
                        for plid, d in self._target_lane_human_cache.items()
                        if current_time - d[0] < 10.0
                    }
                cached_data = self._target_lane_human_cache.get(other_player.plid)

                if not cached_data or (current_time - cached_data[0]) > 0.1:
                    ctx = self.map_recorder.get_location_context(
                        other_coords.x_m, other_coords.y_m, other_coords.z_m
                    )
                    calc_road_id = (
                        ctx.link_id
                        if (ctx.link_id and ctx.link_dist < ctx.road_dist)
                        else ctx.road_id
                    )

                    self._target_lane_human_cache[other_player.plid] = (
                        current_time,
                        calc_road_id,
                    )
                    other_road_id = calc_road_id
                else:
                    # Acceso seguro por índice. El 1 es siempre nuestro calc_road_id
                    other_road_id = cached_data[1]

            # [!] FILTRO ESTRICTO: Solo nos interesa si está en el carril objetivo
            if other_road_id != target_road_id:
                continue

            # [!] FILTRO DIRECCIONAL: ¿Está físicamente delante de nosotros?
            vec_x = other_coords.x_m - my_coords.x_m
            vec_y = other_coords.y_m - my_coords.y_m

            if (my_dir_x * vec_x) + (my_dir_y * vec_y) <= 0:
                continue  # Está detrás

            dist_m = calc_dist_3d(
                my_coords.x_m,
                my_coords.y_m,
                my_coords.z_m,
                other_coords.x_m,
                other_coords.y_m,
                other_coords.z_m,
            )

            if dist_m <= max_dist_m:
                vehicles_ahead.append(
                    (dist_m, other_player.telemetry.speed.speed_kmh, other_player.plid)
                )

        vehicles_ahead.sort(key=lambda x: x[0])
        return vehicles_ahead

    def _scan_return_lane_gap(
        self, ai: "AI", mode: FreeroamMode, max_dist_m: float
    ) -> tuple[float, float]:
        """
        Escanea el carril de retorno desde la posición actual (en el carril rápido).
        Devuelve (dist_más_cercano_delante, dist_más_cercano_detrás) en ese carril.
        """
        if not ai.player.telemetry:
            return 0.0, 0.0

        my_coords = ai.player.telemetry.coordinates
        ret_geom = self.map_recorder.roads.get(mode.overtake_return_lane_id)
        if not ret_geom or not ret_geom.nodes:
            return float("inf"), float("inf")

        closest_idx, _ = self._get_closest_node_index(
            my_coords.x_m, my_coords.y_m, ret_geom.nodes
        )
        next_idx = min(closest_idx + 1, len(ret_geom.nodes) - 1)
        if closest_idx == next_idx:
            next_idx = max(0, closest_idx - 1)
        dir_x = ret_geom.nodes[next_idx].x_m - ret_geom.nodes[closest_idx].x_m
        dir_y = ret_geom.nodes[next_idx].y_m - ret_geom.nodes[closest_idx].y_m

        min_ahead = float("inf")
        min_behind = float("inf")

        for other_player, is_ai, other_ai in [
            (p, False, None) for p in self.user_manager.players.values()
        ] + [(a.player, True, a) for a in self.user_manager.ais.values()]:
            if other_player.plid == ai.player.plid or not other_player.telemetry:
                continue

            # Filtro topológico: solo coches en el carril de retorno
            if is_ai and other_ai and "aic" in other_ai.extra:
                other_mode = other_ai.extra["aic"].active_mode
                other_road = other_mode.current_road_id if other_mode else None
            else:
                ctx = self.map_recorder.get_location_context(
                    other_player.telemetry.coordinates.x_m,
                    other_player.telemetry.coordinates.y_m,
                    other_player.telemetry.coordinates.z_m,
                )
                other_road = ctx.road_id

            if other_road != mode.overtake_return_lane_id:
                continue

            oc = other_player.telemetry.coordinates
            dist = calc_dist_3d(
                my_coords.x_m, my_coords.y_m, my_coords.z_m, oc.x_m, oc.y_m, oc.z_m
            )
            if dist > max_dist_m * 2.0:
                continue

            dot = dir_x * (oc.x_m - my_coords.x_m) + dir_y * (oc.y_m - my_coords.y_m)

            if dot >= 0:
                min_ahead = min(min_ahead, dist)
            else:
                min_behind = min(min_behind, dist)

        return min_ahead, min_behind
