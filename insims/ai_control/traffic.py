from __future__ import annotations
import math
import time
import random
from typing import TYPE_CHECKING, Optional, List, Tuple

from lfs_insim.insim_packet_class import CSVAL
from lfs_insim.utils import calc_dist_3d
from insims.ai_control.behavior import AIBehavior
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from insims.ai_control.nav_modes.freeroam.graph import IntersectionZone, LateralLink, RoadLink, SpecialRule
from insims.ai_control.nav_modes.freeroam.geometry import (
    calc_dist_point_to_segment_2d, get_dist_to_polygon_edge_2d, is_point_in_polygon_2d
)
from insims.ai_control.nav_modes.freeroam.enums import TrafficRule, AIManeuverState
from insims.users_management.main import Coordinates
from insims.ai_control.base import _MixinBase

if TYPE_CHECKING:
    from insims.users_management.main import AI


class _TrafficMixin(_MixinBase):
    def _scan_lane_ahead(self, ai: AI, mode: FreeroamMode, max_dist_m: float) -> list[tuple[float, float, int]]:
        vehicles_ahead = []
        
        if not ai.player.telemetry:
            return vehicles_ahead
            
        my_coords = ai.player.telemetry.coordinates
        is_opposing = getattr(mode, 'is_driving_opposing', False)
        
        # =========================================================
        # [!] OPTIMIZACIÓN 1: Obtener la geometría FUERA del bucle.
        # Si no hay geometría actual válida, ni siquiera iteramos.
        # =========================================================
        if mode.current_type == 'Road':
            geom = self.map_recorder.roads.get(mode.current_id)
        elif mode.current_type == 'RoadLink': 
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
            if curr_idx == next_idx_dir: next_idx_dir = min(len(geom.nodes) - 1, curr_idx + 1)
            next_idx_dist = max(0, curr_idx - 1)
        else:
            next_idx_dir = min(curr_idx + 1, len(geom.nodes) - 1)
            if curr_idx == next_idx_dir: next_idx_dir = max(0, curr_idx - 1)
            next_idx_dist = min(curr_idx + 1, len(geom.nodes) - 1)

        # A. Vector direccional pre-calculado
        node_a = geom.nodes[curr_idx]
        node_b = geom.nodes[next_idx_dir]
        dir_x = node_b.x_m - node_a.x_m
        dir_y = node_b.y_m - node_a.y_m

        # B. Mi distancia al nodo pre-calculada
        target_node = geom.nodes[next_idx_dist]
        mi_dist_al_nodo = math.hypot(target_node.x_m - my_coords.x_m, target_node.y_m - my_coords.y_m)

        # =========================================================
        # 1. GENERADOR UNIFICADO
        # =========================================================
        def iter_all_vehicles():
            for p in self.user_manager.players.values(): yield p, False, None
            for a in self.user_manager.ais.values(): yield a.player, True, a

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
            if is_ai and other_ai and 'aic' in other_ai.extra:
                other_mode = other_ai.extra['aic'].active_mode
                if other_mode and other_mode.current_id:
                    other_road_id = other_mode.current_id
                    other_node_index = other_mode.node_index
            else:
                current_time = time.time()
                if len(self._radar_human_cache) > 64:
                    self._radar_human_cache = {
                        plid: d for plid, d in self._radar_human_cache.items()
                        if current_time - d[0] < 10.0
                    }
                cached_data = self._radar_human_cache.get(other_player.plid)

                if not cached_data or (current_time - cached_data[0]) > 0.1:
                    ctx = self.map_recorder.get_location_context(other_coords.x_m, other_coords.y_m, other_coords.z_m)
                    calc_road_id = ctx.link_id if (ctx.link_id and ctx.link_dist < ctx.road_dist) else ctx.road_id
                    calc_node_index = -1

                    # [!] OPTIMIZACIÓN 4: Solo calculamos el índice exacto del jugador si comparte nuestra calle
                    if calc_road_id == mode.current_id:
                        calc_node_index, _ = self._get_closest_node_index(other_coords.x_m, other_coords.y_m, geom.nodes)

                    self._radar_human_cache[other_player.plid] = (current_time, calc_road_id, calc_node_index)
                    other_road_id = calc_road_id
                    other_node_index = calc_node_index
                else:
                    _, other_road_id, other_node_index = cached_data

            # ---------------------------------------------------------
            # FILTROS ESTRICTOS DE CARRIL
            # ---------------------------------------------------------
            if not other_road_id or other_road_id != mode.current_id:
                continue
                
            idx_diff = mode.node_index - other_node_index if is_opposing else other_node_index - mode.node_index

            if idx_diff < -3:
                continue
                
            # Tu lógica de EMPATE DE NODOS, ahora súper rápida
            if idx_diff == 0:
                su_dist_al_nodo = math.hypot(target_node.x_m - other_coords.x_m, target_node.y_m - other_coords.y_m)
                if su_dist_al_nodo > mi_dist_al_nodo:
                    continue

            # Tu lógica de PRODUCTO PUNTO, ahora solo es suma y multiplicación
            elif idx_diff <= 3:
                vec_x = other_coords.x_m - my_coords.x_m
                vec_y = other_coords.y_m - my_coords.y_m
                
                if (dir_x * vec_x) + (dir_y * vec_y) <= 0:
                    continue

            # ---------------------------------------------------------
            # CÁLCULO DE DISTANCIA FINAL
            # ---------------------------------------------------------
            dist_m = calc_dist_3d(
                my_coords.x_m, my_coords.y_m, my_coords.z_m,
                other_coords.x_m, other_coords.y_m, other_coords.z_m
            )

            if dist_m <= max_dist_m:
                vehicles_ahead.append((dist_m, other_player.telemetry.speed.speed_kmh, other_player.plid))

        # =========================================================
        # 3. ORDENACIÓN
        # =========================================================
        vehicles_ahead.sort(key=lambda x: x[0])
        return vehicles_ahead
    
    def _update_traffic_behavior(self, ai: AI) -> None:
        """
        Orquestador táctico (Navegación Micro).
        Sigue el patrón Sense-Think-Act gestionando su propia frecuencia de escaneo
        y operando la Máquina de Estados de Adelantamiento (FSM).
        """
        behavior: AIBehavior = ai.extra.get('aic')
        if not behavior or not ai.player.telemetry: 
            return
            
        mode: FreeroamMode = behavior.active_mode
        if not mode: 
            return

        # =========================================================
        # 1. RECUPERAR CONTEXTO ESPACIAL Y ESTADOS
        # =========================================================
        nodes_list = []
        if mode.current_type == 'Road':
            geom = self.map_recorder.roads.get(mode.current_id)
        elif mode.current_type == 'RoadLink': 
            geom = self.map_recorder.road_links.get(mode.current_id)
        else:
            geom = None
            
        if not geom or mode.node_index >= len(geom.nodes): 
            return

        nodes_list = geom.nodes
        min_vel = getattr(geom, 'min_speed_kmh', 15.0)
        limite_vel = getattr(geom, 'speed_limit_kmh', 30.0)

        # Override de velocidad por SpecialRule activa
        for rule_id in mode.active_special_rules:
            rule = self.map_recorder.special_rules.get(rule_id)
            if rule and 'speed_limit' in rule.rules:
                override = rule.rules['speed_limit']
                limite_vel = min(limite_vel, override)
                min_vel = min(min_vel, override / 2.0)

        velocidad_base = min_vel + (limite_vel - min_vel) * getattr(mode, 'speed_limit_bias', 0.5)
        
        target_node = nodes_list[mode.node_index]
        target_x, target_y = target_node.x_m, target_node.y_m
        my_coords = ai.player.telemetry.coordinates

        # =========================================================
        # 2. CONTROL DE FRECUENCIA Y PATRÓN SENSE-THINK-ACT
        # =========================================================
        current_time = time.time()
        
        if current_time - mode._last_radar_time >= mode._radar_interval:
            
            my_speed_ms = max(ai.player.telemetry.speed.speed_kmh / 3.6, 0.1)
            safe_gap_s = 2.0 
            warn_gap_s = 4.0 
            min_dist_m = max(4.0, my_speed_ms * safe_gap_s)
            max_dist_m = max(15.0, my_speed_ms * warn_gap_s)

            # Por defecto, asumimos que podemos ir a la velocidad base
            velocidad_segura = velocidad_base

            # =========================================================
            # MÁQUINA DE ESTADOS FINITOS (FSM) DEL ADELANTAMIENTO
            # =========================================================
            
            # ---------------------------------------------------------
            # ESTADO: IDLE (Conducción Normal)
            # ---------------------------------------------------------
            if mode.overtake_state == 'IDLE':
                # Recuperación: si el AI terminó en IDLE en el carril rápido, forzar retorno
                if mode.overtake_fast_lane_id and mode.overtake_fast_lane_id == mode.current_road_id \
                   and mode.overtake_return_lane_id and mode.overtake_return_lane_id != mode.current_road_id:
                    mode.overtake_state = 'RETURNING'
                    mode.maneuver_state = AIManeuverState.RETURNING
                    mode._returning_start_time = current_time
                else:
                    pass  # continúa con lógica IDLE normal abajo

            if mode.overtake_state == 'IDLE':
                mode.last_link = mode.next_link_id, mode.next_link_type
                vehicles_ahead = self._scan_lane_ahead(ai, mode, max_dist_m + 50.0)
                
                if vehicles_ahead:
                    closest_dist, closest_speed_kmh, closest_plid = vehicles_ahead[0]
                    
                    # 1. Aplicamos Control de Crucero Adaptativo (ACC) siempre
                    velocidad_segura = self._apply_adaptive_cruise_control(
                        velocidad_base, closest_speed_kmh, closest_dist, min_dist_m, max_dist_m
                    )
                    mode.blocking_plid = closest_plid
                    
                    # 2. Gatillo del Adelantamiento: Si nos frenan mucho y no hay cooldown
                    lane_change_blocked = any(
                        self.map_recorder.special_rules.get(rid) and
                        self.map_recorder.special_rules[rid].rules.get('no_lane_change', False)
                        for rid in mode.active_special_rules
                    )
                    speed_delta = velocidad_base - closest_speed_kmh
                    if not lane_change_blocked and speed_delta > 7.0 and current_time > mode.overtake_cooldown and closest_dist < max_dist_m:
                        mode.overtake_state = 'EVALUATING'
                        mode.maneuver_state = AIManeuverState.FOLLOWING
                        mode.overtake_target_plid = closest_plid
                        mode.overtake_return_lane_id = mode.current_road_id # Guardamos cómo volver

            # ---------------------------------------------------------
            # ESTADO: EVALUATING (Matemática Pesada)
            # ---------------------------------------------------------
            elif mode.overtake_state == 'EVALUATING':
                velocidad_segura = mode._cached_target_speed 
                # Obtenemos la regla de tráfico del segmento actual
                current_rule = getattr(geom, 'traffic_rule', TrafficRule.LHT) 
                
                # 1. ¿HAY PISTA VÁLIDA? (Buscamos la línea discontinua a nuestro favor)
                target_road_id, target_lat_id = self._find_valid_overtake_lane(mode.current_road_id, current_rule, nodes_list, mode.node_index)
                
                if target_road_id:
                    target_road_geom = self.map_recorder.roads[target_road_id]
                    
                    if target_road_geom:

                        lat_link = self.map_recorder.lateral_links[target_lat_id]
                        # 2. ¿ES SENTIDO CONTRARIO? (¡Leído directamente de tu mapa!)
                        is_opposing = lat_link.opposing
                        
                        # 3. ¿CUÁNTO ESPACIO NECESITO? (Física)
                        vehicles_ahead = self._scan_lane_ahead(ai, mode, max_dist_m + 100.0) 
                        distances_ahead_m = [v[0] for v in vehicles_ahead]
                        
                        rel_dist_m = self._get_relative_dist_to_cover(distances_ahead_m, extra_dist=7.0)
                        
                        # Evaluamos la velocidad del objetivo
                        overtake_speed = velocidad_base
                        target_speed = vehicles_ahead[0][1] if vehicles_ahead else (velocidad_base * 0.5)
                        
                        req_dist_m, time_to_overtake_s = self._estimate_overtake_distance(overtake_speed, target_speed, rel_dist_m)
                        
                        # 4. ¿ES SEGURO? (Radar Dinámico de Carril Objetivo)
                        if req_dist_m != float('inf'):
                            es_seguro = self._is_lane_safe_to_overtake(ai, mode, target_road_id, lat_link, is_opposing, req_dist_m, time_to_overtake_s)
                            
                            if es_seguro:
                                # ¡LUZ VERDE!
                                mode.next_link_id = target_lat_id
                                mode.next_link_type = 'LatLink'
                                mode.overtake_fast_lane_id = target_road_id
                                mode.is_driving_opposing = is_opposing
                                mode.overtake_state = 'PASSING'
                                mode.maneuver_state = AIManeuverState.OVERTAKING
                                mode._passing_start_time = current_time
                                mode._entered_fast_lane = False
                            else:
                                # Abortamos: Tráfico en contra o falta de asfalto
                                mode.overtake_state = 'IDLE'
                                mode.maneuver_state = AIManeuverState.NORMAL
                                mode.overtake_cooldown = current_time + 4.0
                        else:
                            # Velocidad delta demasiado pequeña (no compensa)
                            mode.overtake_state = 'IDLE'
                            mode.maneuver_state = AIManeuverState.NORMAL
                            mode.overtake_cooldown = current_time + 5.0
                    else:
                        mode.overtake_state = 'IDLE'
                        mode.maneuver_state = AIManeuverState.NORMAL
                        mode.overtake_cooldown = current_time + 2.0
                else:
                    # No hay conexión lateral válida (ej. línea continua)
                    mode.overtake_state = 'IDLE'
                    mode.maneuver_state = AIManeuverState.NORMAL
                    mode.overtake_cooldown = current_time + 3.0

            # ---------------------------------------------------------
            # ESTADO: PASSING (Acelerando en el carril rápido)
            # ---------------------------------------------------------
            elif mode.overtake_state == 'PASSING':
                # Marcar cuando el AI llega al carril rápido por primera vez
                if not mode._entered_fast_lane and mode.current_road_id == mode.overtake_fast_lane_id:
                    mode._entered_fast_lane = True
                    mode._fast_lane_entry_time = current_time

                # La navegación ya nos devolvió al carril original DESPUÉS de haber estado en el rápido
                if mode._entered_fast_lane and mode.current_road_id == mode.overtake_return_lane_id:
                    mode.overtake_state = 'IDLE'
                    mode.maneuver_state = AIManeuverState.NORMAL
                    mode.overtake_target_plid = None
                    mode.is_driving_opposing = False
                    mode._entered_fast_lane = False
                    velocidad_segura = velocidad_base
                else:
                    # Si no hay link en el carril rápido, apuntamos al LatLink de retorno para
                    # que la navegación lo active al pasar físicamente por su posición
                    if not mode.next_link_id and mode.current_road_id == getattr(mode, 'overtake_fast_lane_id', None):
                        for _lid, _lat in self.map_recorder.lateral_links.items():
                            if (_lat.road_a == mode.current_road_id and _lat.road_b == mode.overtake_return_lane_id) or \
                               (_lat.road_b == mode.current_road_id and _lat.road_a == mode.overtake_return_lane_id):
                                mode.next_link_id = _lid
                                mode.next_link_type = 'LatLink'
                                break

                    # Ya no multiplicamos la velocidad, usamos la base
                    velocidad_segura = velocidad_base

                    # Radar en el carril rápido por si hay tráfico de frente o lento allí
                    vehicles_fast_lane = self._scan_lane_ahead(ai, mode, max_dist_m)
                    if vehicles_fast_lane:
                        f_dist, f_speed, _ = vehicles_fast_lane[0]
                        velocidad_segura = min(velocidad_segura, self._apply_adaptive_cruise_control(
                            velocidad_base, f_speed, f_dist, min_dist_m, max_dist_m
                        ))

                    # =========================================================
                    # EMERGENCIA FRONTAL (solo en sentido contrario)
                    # =========================================================
                    ONCOMING_EMERGENCY_S = 2.0
                    ONCOMING_DANGER_S    = 5.0

                    if mode.is_driving_opposing and mode._entered_fast_lane and vehicles_fast_lane:
                        f_dist, f_speed, _ = vehicles_fast_lane[0]
                        closing_speed_ms = my_speed_ms + max(f_speed / 3.6, 0.1)
                        time_to_frontal = f_dist / closing_speed_ms

                        if time_to_frontal < ONCOMING_EMERGENCY_S:
                            mode.overtake_state = 'RETURNING'
                            mode.maneuver_state = AIManeuverState.RETURNING
                            mode._returning_start_time = current_time
                            velocidad_segura = 0
                        elif time_to_frontal < ONCOMING_DANGER_S:
                            velocidad_segura = 0

                    # =========================================================
                    # Buscar el vehículo MÁS CERCANO relevante para decidir retorno
                    # =========================================================
                    closest_player = None
                    min_dist = float('inf')

                    dir_x = target_x - my_coords.x_m
                    dir_y = target_y - my_coords.y_m
                    if getattr(mode, 'is_driving_opposing', False):
                        dir_x = -dir_x
                        dir_y = -dir_y
                    dir_mag = math.hypot(dir_x, dir_y)
                    if dir_mag > 0:
                        dir_x /= dir_mag
                        dir_y /= dir_mag
                    else:
                        dir_x, dir_y = 1.0, 0.0

                    def es_obstaculo_relevante(t_coords):
                        vec_x = t_coords.x_m - my_coords.x_m
                        vec_y = t_coords.y_m - my_coords.y_m
                        dot_product = (dir_x * vec_x) + (dir_y * vec_y)
                        distancia_lateral = abs(dir_x * vec_y - dir_y * vec_x)
                        if dot_product < 0 and distancia_lateral < 2.0:
                            return False
                        return True

                    for p in self.user_manager.players.values():
                        if p.plid == ai.player.plid or not p.telemetry: continue
                        t_coords = p.telemetry.coordinates
                        if not es_obstaculo_relevante(t_coords): continue
                        dist = calc_dist_3d(my_coords.x_m, my_coords.y_m, my_coords.z_m, t_coords.x_m, t_coords.y_m, t_coords.z_m)
                        if dist < min_dist:
                            min_dist = dist
                            closest_player = p

                    for a in self.user_manager.ais.values():
                        if a.player.plid == ai.player.plid or not a.player.telemetry: continue
                        t_coords = a.player.telemetry.coordinates
                        if not es_obstaculo_relevante(t_coords): continue
                        dist = calc_dist_3d(my_coords.x_m, my_coords.y_m, my_coords.z_m, t_coords.x_m, t_coords.y_m, t_coords.z_m)
                        if dist < min_dist:
                            min_dist = dist
                            closest_player = a.player

                    # Mínimo 3s desde que empieza PASSING — la IA se compromete a adelantar
                    _can_return = current_time - mode._passing_start_time >= 3.0

                    if not closest_player:
                        if _can_return:
                            mode.overtake_state = 'RETURNING'
                            mode.maneuver_state = AIManeuverState.RETURNING
                            mode._returning_start_time = current_time
                    else:
                        t_coords = closest_player.telemetry.coordinates
                        vec_x = t_coords.x_m - my_coords.x_m
                        vec_y = t_coords.y_m - my_coords.y_m
                        dot_product = (dir_x * vec_x) + (dir_y * vec_y)
                        if _can_return and (min_dist > min_dist_m + 5.0 or (dot_product < 0 and min_dist > min_dist_m)):
                            mode.overtake_state = 'RETURNING'
                            mode.maneuver_state = AIManeuverState.RETURNING
                            mode._returning_start_time = current_time

            # ---------------------------------------------------------
            # ESTADO: RETURNING (Volviendo a casa)
            # ---------------------------------------------------------
            elif mode.overtake_state == 'RETURNING':
                velocidad_segura = velocidad_base
                
                # 1. Comprobamos si el next_link actual es el que nos lleva a casa
                necesita_enlace = True
                if getattr(mode, 'next_link_type', None) == 'LatLink' and mode.next_link_id:
                    current_link = self.map_recorder.lateral_links.get(mode.next_link_id)
                    # Si el enlace actual conecta con nuestra vía original, ya estamos en camino
                    if current_link and (current_link.road_a == mode.overtake_return_lane_id or current_link.road_b == mode.overtake_return_lane_id):
                        necesita_enlace = False
                
                # 2. Si no tenemos el enlace correcto (ya sea porque está vacío o porque la macro-navegación 
                # puso un RoadLink para seguir recto), lo SOBREESCRIBIMOS.
                if necesita_enlace:
                    _fast_road = self.map_recorder.roads.get(mode.current_road_id)
                    for link_id, lat_link in self.map_recorder.lateral_links.items():
                        if (lat_link.road_a == mode.current_road_id and lat_link.road_b == mode.overtake_return_lane_id) or \
                           (lat_link.road_b == mode.current_road_id and lat_link.road_a == mode.overtake_return_lane_id):
                            if _fast_road and not _fast_road.is_circular and not self._is_link_reachable_ahead(
                                _fast_road.nodes, mode.node_index, lat_link.nodes, max_dist=8.0
                            ):
                                continue
                            mode.next_link_id = link_id
                            mode.next_link_type = 'LatLink'
                            break
                
                # 3. Si la macro navegación ya nos ha devuelto a la vía y se ha estabilizado
                if mode.current_road_id == mode.overtake_return_lane_id:
                    mode.overtake_state = 'IDLE'
                    mode.maneuver_state = AIManeuverState.NORMAL
                    mode.overtake_target_plid = None
                    mode.is_driving_opposing = False
                elif current_time - mode._returning_start_time > 10.0:
                    # Timeout de seguridad: algo salió mal, forzamos IDLE
                    mode.overtake_state = 'IDLE'
                    mode.maneuver_state = AIManeuverState.NORMAL
                    mode.overtake_target_plid = None
                    mode.is_driving_opposing = False
                    mode.overtake_fast_lane_id = None  # Evita bucle en la recuperación IDLE

            # Guardamos el resultado en caché
            mode._cached_target_speed = velocidad_segura
            mode._last_radar_time = current_time

            # =========================================================
            # CONTROL DE INTERSECCIONES (Ceda el Paso)
            # =========================================================
            YIELD_LOOK_AHEAD_s = 5.0   # Anticipación: cuántos segundos adelante miramos el cruce
            PRIORITY_APPROACH_s = 4.0  # Ventana para detectar coche prioritario aproximándose

            if hasattr(self.map_recorder, 'zones') and self.map_recorder.zones:

                yielding_to_zone = False

                for zone_id, zone in self.map_recorder.zones.items():

                    # 1. ¿Somos la vía no-prioritaria en este cruce?
                    vias_prioritarias_a_vigilar = []
                    for prio_id, no_prio_id in zone.priority_rules:
                        if mode.current_road_id == no_prio_id:
                            vias_prioritarias_a_vigilar.append(prio_id)

                    if not vias_prioritarias_a_vigilar:
                        continue

                    # 2. ¿Nos estamos acercando a la zona? (tiempo-based, más amplio que el ACC)
                    dist_al_borde = self._get_dist_to_zone_edge(my_coords.x_m, my_coords.y_m, zone)
                    yield_range_m = max(15.0, my_speed_ms * YIELD_LOOK_AHEAD_s)

                    if dist_al_borde > yield_range_m:
                        continue

                    # Si no estamos ya dentro de la zona, verificamos que vamos hacia ella
                    if dist_al_borde > 0.1:
                        zone_cx, zone_cy = self._get_zone_centroid(zone)
                        my_heading_rad = ai.player.telemetry.heading.angle_lfs * 2.0 * math.pi / 65536.0
                        my_fwd_x = -math.sin(my_heading_rad)
                        my_fwd_y = math.cos(my_heading_rad)
                        vec_x = zone_cx - my_coords.x_m
                        vec_y = zone_cy - my_coords.y_m
                        if my_fwd_x * vec_x + my_fwd_y * vec_y <= 0.0:
                            continue  # Nos alejamos: ignorar

                    # 3. Pre-filtro esférico usando el centroide real de la zona
                    zone_cx, zone_cy = self._get_zone_centroid(zone)
                    radio_filtro = zone.radius_m + max(20.0, my_speed_ms * PRIORITY_APPROACH_s * 1.5)

                    # 4. Escanear vehículos prioritarios (dentro O aproximándose con dirección correcta)
                    coche_prioritario_detectado = False

                    # 4.A IAs
                    for a in self.user_manager.ais.values():
                        if a.player.plid == ai.player.plid or not a.player.telemetry:
                            continue

                        other_coords = a.player.telemetry.coordinates
                        if math.hypot(zone_cx - other_coords.x_m, zone_cy - other_coords.y_m) > radio_filtro:
                            continue

                        other_road_id = None
                        if a.extra.get('aic') and a.extra['aic'].active_mode:
                            other_road_id = a.extra['aic'].active_mode.current_road_id

                        if other_road_id in vias_prioritarias_a_vigilar:
                            other_heading_lfs = a.player.telemetry.heading.angle_lfs
                            other_speed_kmh = a.player.telemetry.speed.speed_kmh
                            if self._is_priority_vehicle_active_at_zone(other_coords, other_speed_kmh, other_heading_lfs, zone, PRIORITY_APPROACH_s):
                                coche_prioritario_detectado = True
                                break

                    # 4.B Jugadores reales
                    if not coche_prioritario_detectado:
                        for p in self.user_manager.players.values():
                            if p.plid == ai.player.plid or not p.telemetry:
                                continue

                            other_coords = p.telemetry.coordinates
                            if math.hypot(zone_cx - other_coords.x_m, zone_cy - other_coords.y_m) > radio_filtro:
                                continue

                            ctx = self.map_recorder.get_location_context(
                                other_coords.x_m, other_coords.y_m, other_coords.z_m,
                                find_links=False, find_zones=False
                            )

                            if ctx.road_id in vias_prioritarias_a_vigilar:
                                other_heading_lfs = p.telemetry.heading.angle_lfs
                                other_speed_kmh = p.telemetry.speed.speed_kmh
                                if self._is_priority_vehicle_active_at_zone(other_coords, other_speed_kmh, other_heading_lfs, zone, PRIORITY_APPROACH_s):
                                    coche_prioritario_detectado = True
                                    break

                    # 5. Aplicar freno o limpiar estado de ceda el paso
                    if coche_prioritario_detectado:
                        mode.yield_zone_id = zone_id
                        mode.yield_active = True
                        yielding_to_zone = True

                        dist_acc = max(0.1, dist_al_borde)
                        velocidad_interseccion = self._apply_adaptive_cruise_control(
                            base_speed_kmh=velocidad_base,
                            closest_speed_kmh=0.0,
                            closest_dist_m=dist_acc,
                            min_dist_m=min_dist_m,
                            max_dist_m=yield_range_m,
                        )
                        velocidad_segura = min(velocidad_segura, velocidad_interseccion)
                    elif mode.yield_zone_id == zone_id:
                        mode.yield_zone_id = None
                        mode.yield_active = False

                if not yielding_to_zone and mode.yield_active:
                    mode.yield_active = False
                    mode.yield_zone_id = None

            # =========================================================
            # CONTROL DE REGLAS ESPECIALES (Activación/Desactivación)
            # =========================================================
            if hasattr(self.map_recorder, 'special_rules') and self.map_recorder.special_rules:
                for rule_id, rule in self.map_recorder.special_rules.items():
                    if len(rule.nodes) < 2:
                        continue
                    start_node = rule.nodes[0]
                    end_node   = rule.nodes[1]
                    dist_start = math.hypot(my_coords.x_m - start_node.x_m, my_coords.y_m - start_node.y_m)
                    dist_end   = math.hypot(my_coords.x_m - end_node.x_m,   my_coords.y_m - end_node.y_m)

                    if rule_id not in mode.active_special_rules:
                        if dist_start <= rule.radius_m:
                            mode.active_special_rules.append(rule_id)
                    else:
                        if dist_end <= rule.radius_m:
                            mode.active_special_rules.remove(rule_id)

        else:
            # --- LECTURA DE CACHÉ (Ahorro de CPU) ---
            velocidad_segura = mode._cached_target_speed

        
        velocidad_final = min(velocidad_segura, velocidad_base)

        # =========================================================
        # 3. ASIGNACIÓN FINAL AL COCHE
        # =========================================================
        my_speed_ms = ai.player.telemetry.speed.speed_kmh / 3.6
        lookahead_m = max(5.0, my_speed_ms * 0.4)
        la_x, la_y = self._get_lookahead_point(
            my_coords.x_m, my_coords.y_m,
            mode.node_index, nodes_list,
            lookahead_m,
            reverse=getattr(mode, 'is_driving_opposing', False),
        )
        behavior.target_point_m = (la_x, la_y)
        behavior.target_speed_kmh = velocidad_final

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
            dist = calc_dist_point_to_segment_2d(px, py, nodes[0].x_m, nodes[0].y_m, nodes[1].x_m, nodes[1].y_m)
            return dist <= zone.radius_m
        else:
            # Es un polígono
            return is_point_in_polygon_2d(px, py, nodes)

    def _get_dist_to_zone_edge(self, px: float, py: float, zone) -> float:
        """Calcula la distancia exacta desde el coche hasta el borde geométrico de la zona."""
        nodes = zone.nodes
        n_nodes = len(nodes)
        
        if n_nodes == 0:
            return float('inf')
        elif n_nodes == 1:
            dist = math.hypot(px - nodes[0].x_m, py - nodes[0].y_m) - zone.radius_m
        elif n_nodes == 2:
            dist = calc_dist_point_to_segment_2d(px, py, nodes[0].x_m, nodes[0].y_m, nodes[1].x_m, nodes[1].y_m) - zone.radius_m
        else:
            if is_point_in_polygon_2d(px, py, nodes):
                return 0.0 # Ya estamos dentro del polígono
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

    def _is_priority_vehicle_active_at_zone(self, vehicle_coords, vehicle_speed_kmh: float, vehicle_heading_lfs: int, zone, approach_time_s: float = 4.0) -> bool:
        """True si el vehículo está dentro de la zona O se aproxima a ella con dirección hacia ella."""
        if self._is_point_in_zone(vehicle_coords.x_m, vehicle_coords.y_m, zone):
            return True

        dist_to_edge = self._get_dist_to_zone_edge(vehicle_coords.x_m, vehicle_coords.y_m, zone)
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

    def _apply_adaptive_cruise_control(self, base_speed_kmh: float, closest_speed_kmh: float, closest_dist_m: float, min_dist_m: float, max_dist_m: float) -> float:
        """
        Regula la velocidad de la IA con 3 zonas: Adaptación suave, Frenado agresivo y Parada crítica.
        """
        # ==========================================
        # CONFIGURACIÓN DE LÍMITES FÍSICOS ABSOLUTOS
        # ==========================================
        PARADA_ABSOLUTA_M = 3.0 
        
        # La distancia crítica nunca será menor a nuestro límite absoluto (3 metros).
        critical_dist_m = max(PARADA_ABSOLUTA_M, min_dist_m * 0.5)
        
        # [!] PARCHE DE SEGURIDAD MATEMÁTICO: 
        # Al forzar los 3 metros arriba, si el `min_dist_m` dinámico es muy pequeño (ej. 2m), 
        # las fórmulas de abajo fallarían por división por cero o darían ratios negativos.
        # Por tanto, empujamos las zonas dinámicas hacia arriba si es necesario.
        min_dist_m = max(critical_dist_m + 2.0, min_dist_m)
        max_dist_m = max(min_dist_m + 5.0, max_dist_m)

        # ==========================================
        # ZONA ROJA: Peligro inminente de colisión
        # ==========================================
        if closest_dist_m <= critical_dist_m:
            return 0.0

        # ==========================================
        # ZONA NARANJA: Warning Area (Frenado directo)
        # ==========================================
        if closest_dist_m <= min_dist_m:
            # Aquí frenamos agresivamente de forma proporcional.
            ratio_frenado = (closest_dist_m - critical_dist_m) / (min_dist_m - critical_dist_m)
            
            # Pedimos ir MÁS LENTO que el coche de delante para recuperar la distancia de seguridad
            target_speed = closest_speed_kmh * ratio_frenado
            
            # ANTI-CREEP: Evita el frenado asintótico. Si la velocidad objetivo es ridículamente 
            # baja (ej. arrastrarse a 1.5 km/h frente a un ceda el paso), frenamos en seco.
            if target_speed < 2.0:
                return 0.0
                
            return target_speed

        # ==========================================
        # ZONA AMARILLA: Safety Area (Adaptación)
        # ==========================================
        if closest_dist_m < max_dist_m:
            # Interpolación (Lerp) para igualar la velocidad del líder de forma suave
            ratio_adaptacion = (closest_dist_m - min_dist_m) / (max_dist_m - min_dist_m)
            
            # Buscamos igualar la velocidad del coche de delante
            match_speed = min(closest_speed_kmh, base_speed_kmh)
            
            # A medida que nos acercamos al min_dist_m, la velocidad cae a match_speed
            target_speed = match_speed + (base_speed_kmh - match_speed) * ratio_adaptacion
            return min(target_speed, base_speed_kmh)

        # Si está fuera de los radares (más lejos que max_dist_m), vamos a la velocidad base
        return base_speed_kmh

    def _get_lookahead_point(
        self,
        my_x: float, my_y: float,
        node_index: int,
        nodes_list: list,
        lookahead_m: float,
        reverse: bool = False,
    ) -> tuple[float, float]:
        if not nodes_list:
            return my_x, my_y

        indices = range(node_index, -1, -1) if reverse else range(node_index, len(nodes_list))

        prev_x, prev_y = my_x, my_y
        accumulated = 0.0
        for idx in indices:
            node = nodes_list[idx]
            seg_len = math.hypot(node.x_m - prev_x, node.y_m - prev_y)
            if accumulated + seg_len >= lookahead_m:
                t = (lookahead_m - accumulated) / seg_len if seg_len > 0 else 0.0
                return prev_x + t * (node.x_m - prev_x), prev_y + t * (node.y_m - prev_y)
            accumulated += seg_len
            prev_x, prev_y = node.x_m, node.y_m

        last = nodes_list[0 if reverse else -1]
        return last.x_m, last.y_m

    def _find_valid_overtake_lane(self, current_road_id: str, current_road_traffic_rule: TrafficRule, current_road_nodes: List[Coordinates], node_index: int) -> Optional[Tuple[str,str]]:
        """
        Evalúa una lista de carriles laterales y devuelve el primero que sea válido
        para adelantar basándose en la regla de tráfico (RHT/LHT) del carril actual.
        """
        # 1. Obtener el segmento actual para conocer su TrafficRule


        connected_lateral_ids: List[Tuple[str, str]] = []
        
        # 2. Definimos el lado objetivo
        for lat_link in self.map_recorder.lateral_links.values():
            if lat_link.road_a == current_road_id: connected_lateral_ids.append((lat_link.road_b, lat_link.link_id))
            elif lat_link.road_b == current_road_id: connected_lateral_ids.append((lat_link.road_a, lat_link.link_id))
        
        target_side = CSVAL.INDICATORS.LEFT if current_road_traffic_rule == TrafficRule.RHT else CSVAL.INDICATORS.RIGHT

        # 3. Evaluamos los carriles vecinos
        for info_id in connected_lateral_ids:
            road_id = info_id[0]
            link_id = info_id[1]
            road_geom = self.map_recorder.roads[road_id]        
                
            # Reutilizamos tu lógica matemática exacta para saber el lado real del carril
            side = self._get_indicator_to_use(current_road_nodes, road_geom.nodes, node_index)
            
            # Si el carril está físicamente en el lado legal de adelantamiento, es nuestro candidato
            if side == target_side:
                return road_id, link_id
                
        return None, None
    
    def _get_relative_dist_to_cover(self, distances_ahead_m: list[float], extra_dist: float = 5) -> float:
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
            
            if gap <= first_car_dist+extra_dist:
                last_car_dist = current_dist
            else:
                break
                
        # Retorna la distancia relativa total a cubrir matemáticamente simplificada
        return last_car_dist + first_car_dist + extra_dist
    
    def _estimate_overtake_distance(self, overtake_lane_speed_kmh: float, target_speed_kmh: float, relative_dist_to_cover_m: float) -> float:
        """
        Calcula los metros de asfalto requeridos para completar un adelantamiento.
        """
        my_overtake_speed_ms = overtake_lane_speed_kmh / 3.6
        target_speed_ms = max(target_speed_kmh / 3.6, 0.1)
        
        speed_delta_ms = my_overtake_speed_ms - target_speed_ms
        
        if speed_delta_ms <= 0.1:
            return float('inf'), float('inf')
            
        time_to_overtake_s = relative_dist_to_cover_m / speed_delta_ms
        total_road_distance_m = my_overtake_speed_ms * time_to_overtake_s
        
        # Retornamos la tupla (distancia, tiempo)
        return total_road_distance_m, time_to_overtake_s
    
    def _get_available_overtake_distance(self, mode: FreeroamMode, my_coords: Coordinates, overtake_lat_link: LateralLink) -> float:
        """
        Devuelve cuántos metros físicos seguros le quedan a la IA para adelantar,
        teniendo en cuenta su ruta (next_link) y la longitud de la línea discontinua.
        """
        if overtake_lat_link.is_circular:
            return float('inf')

        # 1. Metros restantes de la ventana de adelantamiento (línea discontinua)
        # Asumimos una función que calcula la longitud restante de una lista de nodos
        closest_lat_idx, _ = self._get_closest_node_index(my_coords.x_m, my_coords.y_m, overtake_lat_link.nodes)
        lat_dist_available = self._calc_path_length(overtake_lat_link.nodes, start_idx=closest_lat_idx)
        
        # 2. Metros restantes hasta que la IA tenga que girar/salir
        route_dist_available = float('inf')
        if mode.next_link_id:
            current_road_nodes = self.map_recorder.roads[mode.current_road_id].nodes
            route_dist_available = self._calc_path_length(current_road_nodes, start_idx=mode.node_index)

        # La distancia real que tenemos para maniobrar es el peor de los casos (el más corto)
        return min(lat_dist_available, route_dist_available)
    
    def _calc_path_length(self, nodes: List[Coordinates], start_idx: int = 0) -> float:
        """
        Calcula la distancia real de un trazado sumando la distancia entre sus nodos
        a partir de un índice específico.
        """
        if not nodes or start_idx >= len(nodes) - 1:
            return 0.0
            
        total_dist = 0.0
        # Nos aseguramos de que el índice inicial no sea negativo
        start_idx = max(0, start_idx)
        
        for i in range(start_idx, len(nodes) - 1):
            p1 = nodes[i]
            p2 = nodes[i + 1]
            # Usamos math.hypot (2D) por rendimiento, ya que para longitudes de asfalto 
            # suele ser más que suficiente salvo que haya pendientes extremas.
            total_dist += math.hypot(p2.x_m - p1.x_m, p2.y_m - p1.y_m)
            
        return total_dist

    def _scan_target_lane(self, ai: AI, mode: FreeroamMode, target_road_id: str, max_dist_m: float) -> list[tuple[float, float, int]]:
        """
        Escanea un carril específico usando una caché independiente 
        para evitar sobreescribir los datos del radar principal.
        """
        vehicles_ahead = []
        if not ai.player.telemetry: 
            return vehicles_ahead
            
        my_coords = ai.player.telemetry.coordinates

        def iter_all_vehicles():
            for p in self.user_manager.players.values(): yield p, False, None
            for a in self.user_manager.ais.values(): yield a.player, True, a

        # =========================================================
        # VECTOR DIRECCIONAL BASE (Para saber qué es "hacia adelante")
        # =========================================================
        curr_geom = self.map_recorder.roads.get(mode.current_id) or self.map_recorder.road_links.get(mode.current_id) or self.map_recorder.lateral_links.get(mode.current_id)
        if not curr_geom or not curr_geom.nodes: return []
        
        curr_idx = min(mode.node_index, len(curr_geom.nodes) - 1)
        next_idx = min(curr_idx + 1, len(curr_geom.nodes) - 1)
        if curr_idx == next_idx: curr_idx = max(0, curr_idx - 1)
        
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
            fast_dist = math.hypot(my_coords.x_m - other_coords.x_m, my_coords.y_m - other_coords.y_m)
            if fast_dist > max_dist_m + 15.0: 
                continue

            # Extracción Topológica
            other_road_id = None
            if is_ai and other_ai and 'aic' in other_ai.extra:
                other_mode: FreeroamMode = other_ai.extra['aic'].active_mode
                if other_mode: other_road_id = other_mode.current_id
            else:
                # [!] Usamos una caché propia para este escaner: _target_lane_human_cache
                current_time = time.time()
                if len(self._target_lane_human_cache) > 64:
                    self._target_lane_human_cache = {
                        plid: d for plid, d in self._target_lane_human_cache.items()
                        if current_time - d[0] < 10.0
                    }
                cached_data = self._target_lane_human_cache.get(other_player.plid)
                
                if not cached_data or (current_time - cached_data[0]) > 0.1:
                    ctx = self.map_recorder.get_location_context(other_coords.x_m, other_coords.y_m, other_coords.z_m)
                    calc_road_id = ctx.link_id if (ctx.link_id and ctx.link_dist < ctx.road_dist) else ctx.road_id
                    
                    self._target_lane_human_cache[other_player.plid] = (current_time, calc_road_id)
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
                continue # Está detrás

            dist_m = calc_dist_3d(my_coords.x_m, my_coords.y_m, my_coords.z_m, other_coords.x_m, other_coords.y_m, other_coords.z_m)

            if dist_m <= max_dist_m:
                vehicles_ahead.append((dist_m, other_player.telemetry.speed.speed_kmh, other_player.plid))

        vehicles_ahead.sort(key=lambda x: x[0])
        return vehicles_ahead

    def _is_lane_safe_to_overtake(self, ai: AI, mode: FreeroamMode, target_road_id: str, overtake_lat_link: LateralLink
    , is_opposing: bool, req_dist_m: float, time_to_overtake_s: float) -> bool:
        """
        Calcula dinámicamente si el carril objetivo es seguro:
        1. Comprueba si tenemos suficiente asfalto físico en la vía y en nuestra ruta.
        2. Escanea el tráfico para evitar colisiones.
        """
        my_coords = ai.player.telemetry.coordinates
        
        # =========================================================
        # 1. COMPROBACIÓN FÍSICA Y DE RUTA (Límites de asfalto)
        # =========================================================
        # Calculamos cuánta pista útil nos queda realmente
        available_dist_m = self._get_available_overtake_distance(mode, my_coords, overtake_lat_link)
        
        # Si la distancia que necesitamos + un margen de seguridad de 15m es mayor a la pista que tenemos, abortamos
        if req_dist_m + 15.0 > available_dist_m:
            return False

        # =========================================================
        # 2. ESCANEO DINÁMICO DE TRÁFICO
        # =========================================================
        # Escaneamos con margen de sobra (el doble de lo requerido, tope 300m)
        scan_dist = min(req_dist_m * 2.0, 300.0)
        target_vehicles = self._scan_target_lane(ai, mode, target_road_id, max_dist_m=scan_dist)

        my_speed_kmh = ai.player.telemetry.speed.speed_kmh
        my_speed_ms = my_speed_kmh / 3.6

        for dist_m, other_speed_kmh, _ in target_vehicles:
            other_speed_ms = other_speed_kmh / 3.6

            if not is_opposing:
                # =========================================================
                # CASO A: CARRIL MISMO SENTIDO (Autovía)
                # =========================================================
                if other_speed_kmh >= my_speed_kmh:
                    # [!] PARCHE DE SEGURIDAD: Si va más rápido pero está literalmente a nuestro lado (punto ciego), abortar.
                    if dist_m < 10.0: 
                        return False
                    continue 

                # Va más lento. ¿Lo alcanzaremos antes de terminar de adelantar al otro?
                # 1. Calculamos cuánto avanzará él durante nuestro tiempo de maniobra
                dist_they_travel_m = other_speed_ms * time_to_overtake_s
                
                # 2. Su posición futura respecto a donde estamos nosotros HOY
                their_future_pos_m = dist_m + dist_they_travel_m
                
                # 3. Si nuestra posición final requerida está demasiado cerca de él... abortar.
                if their_future_pos_m - req_dist_m < 10.0: # 15m de espacio vital al terminar
                    return False

            else:
                # =========================================================
                # CASO B: CARRIL SENTIDO CONTRARIO (Carretera convencional)
                # =========================================================
                # En sentido contrario, CUALQUIER coche es peligroso, no importa su velocidad.
                
                # Velocidad de cierre (nos acercamos mutuamente)
                closing_speed_ms = my_speed_ms + other_speed_ms
                
                # Distancia física que "desaparecerá" entre ambos durante la maniobra
                dist_consumed_m = closing_speed_ms * time_to_overtake_s
                
                # Si la distancia inicial es menor que la que nos comeremos + margen de seguridad frontal...
                if dist_m < dist_consumed_m + 30.0: # 30m de margen para evitar choques frontales
                    return False

        # Si pasamos el filtro físico y el filtro de tráfico, ¡vía libre!
        return True