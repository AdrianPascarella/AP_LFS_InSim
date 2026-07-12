"""Adelantamiento: elección del carril válido, matemática de la maniobra
(distancias y tiempos), guardián de seguridad y helpers del FSM."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple

from insims.ai_control.base import _MixinBase
from insims.ai_control.nav_modes.freeroam.enums import AIManeuverState, TrafficRule
from insims.ai_control.nav_modes.freeroam.graph import LateralLink
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from insims.users_management.main import Coordinates
from lfs_insim.insim_enums import CSVAL
from lfs_insim.utils import calc_dist_3d

if TYPE_CHECKING:
    from insims.users_management.main import AI


class _OvertakeMixin(_MixinBase):
    def _find_valid_overtake_lane(
        self,
        current_road_id: str,
        current_road_traffic_rule: TrafficRule,
        current_road_nodes: List[Coordinates],
        node_index: int,
    ) -> Optional[Tuple[str, str]]:
        """
        Evalúa una lista de carriles laterales y devuelve el primero que sea válido
        para adelantar basándose en la regla de tráfico (RHT/LHT) del carril actual.
        """
        # 1. Obtener el segmento actual para conocer su TrafficRule

        connected_lateral_ids: List[Tuple[str, str]] = []

        # 2. Definimos el lado objetivo
        for lat_link in self.map_recorder.lateral_links.values():
            if lat_link.road_a == current_road_id:
                connected_lateral_ids.append((lat_link.road_b, lat_link.link_id))
            elif lat_link.road_b == current_road_id:
                connected_lateral_ids.append((lat_link.road_a, lat_link.link_id))

        target_side = (
            CSVAL.INDICATORS.LEFT
            if current_road_traffic_rule == TrafficRule.RHT
            else CSVAL.INDICATORS.RIGHT
        )

        # 3. Evaluamos los carriles vecinos
        for info_id in connected_lateral_ids:
            road_id = info_id[0]
            link_id = info_id[1]
            road_geom = self.map_recorder.roads.get(road_id)
            lat_link = self.map_recorder.lateral_links.get(link_id)
            if not road_geom or not lat_link:
                continue

            # Fase 7 · fix (4): no adelantar metiéndose en una vía cerrada.
            if not self.map_recorder.is_road_usable(road_id):
                continue

            side = self._get_indicator_to_use(
                current_road_nodes, road_geom.nodes, node_index
            )

            if side == target_side:
                return road_id, link_id

        return None, None

    def _get_relative_dist_to_cover(
        self, distances_ahead_m: list[float], extra_dist: float = 5
    ) -> float:
        """
        Calcula la distancia relativa a ganar para un adelantamiento.
        Usa la distancia al primer coche como el 'safe gap' delantero y trasero.
        Fórmula simplificada: last_car_dist + first_car_dist + 5.0m (tamaño del coche)
        """
        if not distances_ahead_m:
            return 0.0

        distances_ahead_m.sort()
        first_car_dist = distances_ahead_m[0]
        last_car_dist = first_car_dist

        # Evaluamos el hueco entre cada coche para ver dónde termina el convoy
        for i in range(1, len(distances_ahead_m)):
            current_dist = distances_ahead_m[i]
            gap = current_dist - last_car_dist

            if gap <= first_car_dist + extra_dist:
                last_car_dist = current_dist
            else:
                break

        # Retorna la distancia relativa total a cubrir matemáticamente simplificada
        return last_car_dist + first_car_dist + extra_dist

    def _estimate_overtake_distance(
        self,
        overtake_lane_speed_kmh: float,
        target_vehicle_speed_kmh: float,
        relative_dist_to_cover_m: float,
    ) -> float:
        """
        Calcula los metros de asfalto requeridos para completar un adelantamiento.

        `target_vehicle_speed_kmh` es la velocidad del vehículo AL QUE se adelanta
        (aquí "target" es el coche objetivo, no la velocidad pedida a la IA).
        """
        my_overtake_speed_ms = overtake_lane_speed_kmh / 3.6
        target_speed_ms = max(target_vehicle_speed_kmh / 3.6, 0.1)

        speed_delta_ms = my_overtake_speed_ms - target_speed_ms

        if speed_delta_ms <= 0.1:
            return float("inf"), float("inf")

        time_to_overtake_s = relative_dist_to_cover_m / speed_delta_ms
        total_road_distance_m = my_overtake_speed_ms * time_to_overtake_s

        # Retornamos la tupla (distancia, tiempo)
        return total_road_distance_m, time_to_overtake_s

    def _get_available_overtake_distance(
        self, mode: FreeroamMode, my_coords: Coordinates, overtake_lat_link: LateralLink
    ) -> float:
        """
        Devuelve cuántos metros físicos seguros le quedan a la IA para adelantar,
        teniendo en cuenta su ruta (next_link) y la longitud de la línea discontinua.
        """
        if overtake_lat_link.is_circular:
            return float("inf")

        # 1. Metros restantes de la ventana de adelantamiento (línea discontinua)
        # Asumimos una función que calcula la longitud restante de una lista de nodos
        closest_lat_idx, _ = self._get_closest_node_index(
            my_coords.x_m, my_coords.y_m, overtake_lat_link.nodes
        )
        lat_dist_available = self._calc_path_length(
            overtake_lat_link.nodes, start_idx=closest_lat_idx
        )

        # 2. Metros restantes hasta que la IA tenga que girar/salir
        route_dist_available = float("inf")
        if mode.next_link_id:
            current_road_nodes = self.map_recorder.roads[mode.current_road_id].nodes
            route_dist_available = self._calc_path_length(
                current_road_nodes, start_idx=mode.node_index
            )

        # La distancia real que tenemos para maniobrar es el peor de los casos (el más corto)
        return min(lat_dist_available, route_dist_available)

    def _is_lane_safe_to_overtake(
        self,
        ai: AI,
        mode: FreeroamMode,
        target_road_id: str,
        overtake_lat_link: LateralLink,
        is_opposing: bool,
        req_dist_m: float,
        time_to_overtake_s: float,
        safe_gap_s: float = 2.0,
    ) -> bool:
        """
        Calcula dinámicamente si el carril objetivo es seguro:
        1. Comprueba si tenemos suficiente asfalto físico en la vía y en nuestra ruta.
        2. Escanea el tráfico para evitar colisiones.
        """
        my_coords = ai.player.telemetry.coordinates
        my_speed_kmh = ai.player.telemetry.speed.speed_kmh
        my_speed_ms = my_speed_kmh / 3.6

        # =========================================================
        # 1. COMPROBACIÓN DE SALIDA (¿Cabe la maniobra antes de nuestro próximo giro?)
        # =========================================================
        if mode.next_link_id and mode.next_link_type == "RoadLink":
            road_link = self.map_recorder.road_links.get(mode.next_link_id)
            if road_link and road_link.nodes:
                exit_idx, _ = self._get_closest_node_index(
                    my_coords.x_m, my_coords.y_m, road_link.nodes
                )
                exit_node = road_link.nodes[exit_idx]
                dist_to_exit = calc_dist_3d(
                    my_coords.x_m,
                    my_coords.y_m,
                    my_coords.z_m,
                    exit_node.x_m,
                    exit_node.y_m,
                    exit_node.z_m,
                )
                if req_dist_m > dist_to_exit:
                    return False

        # =========================================================
        # 2. COMPROBACIÓN FÍSICA Y DE RUTA (Límites de asfalto)
        # =========================================================
        available_dist_m = self._get_available_overtake_distance(
            mode, my_coords, overtake_lat_link
        )
        safe_gap_m = my_speed_ms * safe_gap_s
        if req_dist_m + safe_gap_m > available_dist_m:
            return False

        # =========================================================
        # 2. ESCANEO DINÁMICO DE TRÁFICO
        # =========================================================
        scan_dist = min(req_dist_m * 2.0, my_speed_ms * 10.0)
        target_vehicles = self._scan_target_lane(
            ai, mode, target_road_id, max_dist_m=scan_dist
        )

        for dist_m, other_speed_kmh, _ in target_vehicles:
            other_speed_ms = other_speed_kmh / 3.6

            if not is_opposing:
                # =========================================================
                # CASO A: CARRIL MISMO SENTIDO (Autovía)
                # =========================================================
                if other_speed_kmh >= my_speed_kmh:
                    if dist_m < safe_gap_m:
                        return False
                    continue

                dist_they_travel_m = other_speed_ms * time_to_overtake_s
                their_future_pos_m = dist_m + dist_they_travel_m
                if their_future_pos_m - req_dist_m < safe_gap_m:
                    return False

            else:
                # =========================================================
                # CASO B: CARRIL SENTIDO CONTRARIO (Carretera convencional)
                # =========================================================
                closing_speed_ms = my_speed_ms + other_speed_ms
                dist_consumed_m = closing_speed_ms * time_to_overtake_s

                if dist_m < dist_consumed_m + safe_gap_m * 2.0:
                    return False

        # Si pasamos el filtro físico y el filtro de tráfico, ¡vía libre!
        return True

    # =========================================================
    # HELPERS DEL FSM DE ADELANTAMIENTO
    # =========================================================

    def _trigger_return(self, mode: FreeroamMode, current_time: float) -> None:
        """Activa RETURNING: indica a nav que ejecute el cambio de carril de retorno."""
        mode.overtake_change_lane = True
        mode.overtake_state = "RETURNING"
        mode.maneuver_state = AIManeuverState.RETURNING
        mode._returning_start_time = current_time

    def _finish_overtake(self, mode: FreeroamMode, current_time: float) -> None:
        """Cierra el adelantamiento. next_link_id nunca fue tocado — no hay nada que restaurar."""
        mode.overtake_state = "IDLE"
        mode.maneuver_state = AIManeuverState.NORMAL
        mode.overtake_target_plid = None
        mode.is_driving_opposing = False
        mode.overtake_fast_lane_id = None
        mode.overtake_lat_link_id = None
        mode.overtake_change_lane = False
        mode._fast_lane_logged = False
        mode.overtake_cooldown = current_time + 8.0
