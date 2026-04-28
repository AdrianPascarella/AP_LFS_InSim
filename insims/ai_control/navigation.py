from __future__ import annotations
import math
import time
import random
from typing import TYPE_CHECKING, Optional, List, Tuple, Literal

from lfs_insim.insim_packet_class import CSVAL, AIInputVal as AIV, CS
from lfs_insim.utils import (
    calc_dist_3d, get_closest_node_index, determine_smart_spawn_index,
    apply_antilag_window, evaluate_dynamic_capture
)
from insims.ai_control.behavior import AIBehavior, GearMode
from insims.ai_control.nav_modes.route.mode import RouteMode
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from insims.ai_control.nav_modes.freeroam.graph import RoadLink, LocationContext
from insims.ai_control.nav_modes.freeroam.geometry import calc_dist_point_to_segment_2d
from insims.ai_control.base import _MixinBase

if TYPE_CHECKING:
    from insims.users_management.main import AI, Coordinates


class _NavigationMixin(_MixinBase):
    def _update_route_navigation(self, ai: AI):
        """Calcula el progreso de la IA sobre su ruta activa con sistema Anti-Lag y evaluación de tráfico."""
        behavior: AIBehavior = ai.extra['aic']
        mode = behavior.active_mode
        
        if not isinstance(mode, RouteMode) or not mode.active_route_name: return
        
        route = self.route_manager.loaded_routes.get(mode.active_route_name)
        if not route or not route.waypoints: return
        
        my_coords = ai.player.telemetry.coordinates
        
        # =========================================================
        # FASE 1: INICIALIZACIÓN (Smart Spawn Global)
        # =========================================================
        if getattr(mode, 'route_started', False) is False:
            closest_idx = get_closest_node_index(my_coords, route.waypoints, is_waypoint=True)
            mode.route_wp_index = determine_smart_spawn_index(my_coords, closest_idx, route.waypoints, is_waypoint=True)
            mode.route_started = True
            
        # =========================================================
        # FASE 2: SISTEMA ANTI-LAG (Búsqueda hacia adelante)
        # =========================================================
        mode.route_wp_index = apply_antilag_window(
            my_coords, mode.route_wp_index, route.waypoints, window_size=15, is_waypoint=True
        )
        
        # =========================================================
        # FASE 3: RADIO DE CAPTURA DINÁMICO (Lookahead Distance)
        # =========================================================
        mode.route_wp_index = evaluate_dynamic_capture(
            my_coords, mode.route_wp_index, route.waypoints, 
            speed_kmh=ai.player.telemetry.speed.speed_kmh, 
            is_waypoint=True
        )
                
        # Obtenemos el waypoint objetivo
        wp = route.waypoints[mode.route_wp_index]
        
        # 1. Dirección (A dónde mirar) -> Lo usará _handle_steering
        behavior.target_point_m = (wp.coordinates.x_m, wp.coordinates.y_m)
        
        # 2. Intención Original (Velocidad del Waypoint)
        behavior.target_speed_kmh = wp.speed.speed_kmh

        # =========================================================
        # FASE 4: TÁCTICAS Y RADAR DE TRÁFICO (El Cerebro)
        # =========================================================
        # A. Aplicamos el factor de "personalidad" del conductor a la velocidad del waypoint
        base_speed = behavior.target_speed_kmh * getattr(behavior, 'human_speed_factor', 1.0)
        
        # B. El radar exclusivo de rutas analiza el entorno (Autodistribución y Muelle Anticolisión)
        final_speed = self._get_radar_speed_limit(ai, base_speed)
        
        # C. Asignamos la velocidad final real para que los pedales la ejecuten a ciegas
        behavior.target_speed_kmh = final_speed
        behavior.speed_reverse = (final_speed < 0)

        # =========================================================
        # FASE 5: WATCHDOG ESPECÍFICO DE RUTA
        # =========================================================
        if behavior.stuck_start_time > 0:
            segundos_atascado = time.time() - behavior.stuck_start_time
            
            # En una ruta estricta, si se atasca 3 segundos, lo quitamos de en medio
            if segundos_atascado > 3.0:
                self.logger.info(f"IA {ai.ai_name} atascada en ruta durante {segundos_atascado:.1f}s. A espectadores.")
                self._cmd_spec(ai.player.plid)
                
                # Reseteamos por seguridad, aunque la IA ya vaya a spec
                behavior.stuck_start_time = 0.0
    
    def _get_radar_speed_limit(self, ai: AI, base_speed: float, gap_filling_mode: bool = True) -> float:
        """
        Escanea la ruta y devuelve la velocidad objetivo final (Adaptive Cruise Control).
        Modo de 2 capas: 
        1. Sincronización Global (Auto-distribución en el circuito completo).
        2. Muelle Local (Anticolisiones de corto alcance).
        """
        behavior: AIBehavior = ai.extra.get('aic')
        mode = behavior.active_mode if behavior else None
        
        if not isinstance(mode, RouteMode) or not mode.active_route_name: 
            return base_speed
        if not getattr(mode, 'route_started', True): 
            return base_speed
        
        safe_gap_s = getattr(behavior, 'human_safe_gap', 2.0)
        warn_gap_s = getattr(behavior, 'human_warn_gap', 3.5)
            
        route = self.route_manager.loaded_routes.get(mode.active_route_name)
        if not route or not route.waypoints: 
            return base_speed
            
        total_wps = len(route.waypoints)
        my_idx = mode.route_wp_index
        my_coords = ai.player.telemetry.coordinates
        
        my_speed_kmh = ai.player.telemetry.speed.speed_kmh
        my_speed_ms = my_speed_kmh / 3.6
        
        # =========================================================
        # CONFIGURACIÓN DEL RADAR CORTO (Muelle)
        # =========================================================
        min_dist_m = max(5.0, my_speed_ms * safe_gap_s)
        max_dist_m = max(15.0, my_speed_ms * warn_gap_s * 1.5) 
        
        radar_range_m = max_dist_m + max(30.0, my_speed_ms * 4.0)
        
        next_idx = (my_idx + 1) % total_wps
        wp_c = route.waypoints[my_idx].coordinates
        wp_n = route.waypoints[next_idx].coordinates
        local_wp_density_m = max(1.0, calc_dist_3d(wp_c.x_m, wp_c.y_m, wp_c.z_m, wp_n.x_m, wp_n.y_m, wp_n.z_m))
        
        SCAN_WPS_AHEAD = int(radar_range_m / local_wp_density_m)
        SCAN_WPS_AHEAD = max(15, min(SCAN_WPS_AHEAD, total_wps // 3))

        closest_dist_ahead_m = float('inf')
        global_wps_ahead = float('inf')
        global_wps_behind = float('inf')
        ais_on_route = 0
        
        # =========================================================
        # ESCANEO ÚNICO DE COCHES (Global y Corto Alcance)
        # =========================================================
        for other_ai in self.user_manager.ais.values():
            if other_ai == ai: continue
                
            other_behavior: AIBehavior = other_ai.extra.get('aic')
            other_mode = other_behavior.active_mode if other_behavior else None
            
            if not isinstance(other_mode, RouteMode) or other_mode.active_route_name != mode.active_route_name:
                continue 
                
            ais_on_route += 1
            idx_diff_ahead = (other_mode.route_wp_index - my_idx) % total_wps
            idx_diff_behind = (my_idx - other_mode.route_wp_index) % total_wps
            
            # 1. Registro Global (Todo el circuito)
            if 0 < idx_diff_ahead < global_wps_ahead:
                global_wps_ahead = idx_diff_ahead
            if 0 < idx_diff_behind < global_wps_behind:
                global_wps_behind = idx_diff_behind
            
            # 2. Registro de Corto Alcance (Anticolisión frontal)
            other_coords = other_ai.player.telemetry.coordinates
            dist_m = calc_dist_3d(
                my_coords.x_m, my_coords.y_m, my_coords.z_m,
                other_coords.x_m, other_coords.y_m, other_coords.z_m
            )
            
            if idx_diff_ahead == 0:
                wp_coords = route.waypoints[my_idx].coordinates
                my_dist_to_wp = calc_dist_3d(my_coords.x_m, my_coords.y_m, my_coords.z_m, wp_coords.x_m, wp_coords.y_m, wp_coords.z_m)
                other_dist_to_wp = calc_dist_3d(other_coords.x_m, other_coords.y_m, other_coords.z_m, wp_coords.x_m, wp_coords.y_m, wp_coords.z_m)
                is_ahead = other_dist_to_wp < my_dist_to_wp
            else:
                is_ahead = idx_diff_ahead < idx_diff_behind
            
            if is_ahead and idx_diff_ahead <= SCAN_WPS_AHEAD:
                if dist_m < closest_dist_ahead_m:
                    closest_dist_ahead_m = dist_m

        # =========================================================
        # CAPA 1: SINCRONIZACIÓN GLOBAL (Intención de Velocidad Base)
        # =========================================================
        target_speed = base_speed

        if gap_filling_mode and ais_on_route > 0 and global_wps_ahead != float('inf') and global_wps_behind != float('inf'):
            total_gap = global_wps_ahead + global_wps_behind
            
            if total_gap > 0:
                balance = global_wps_ahead / total_gap 
                
                # Tolerancia del 10% (0.45 a 0.55) en el centro para evitar luces parpadeantes
                if balance < 0.45:
                    target_speed = base_speed * 0.75  # Está muy pegado al de delante -> Frena para retrasarse
                elif balance > 0.55:
                    target_speed = base_speed * 1.20  # Está muy separado del de delante -> Acelera para cazarlo
                    
        # Nota: Aquí no usamos ignore_human. Queremos que el multiplicador de agresividad 
        # del conductor se aplique después a estas decisiones "estratégicas" de la Capa 1.

        # =========================================================
        # CAPA 2: MUELLE ANTICOLISIÓN (Física Local y Seguridad)
        # =========================================================
        # El radar de proximidad SIEMPRE tiene la última palabra por seguridad.
        if closest_dist_ahead_m <= min_dist_m:
            target_speed = 0.0
            behavior.ignore_human = True  # [!] Freno de emergencia, la física manda.

        elif closest_dist_ahead_m < max_dist_m:
            # Si el de delante está cerca, aplicamos el acordeón
            ratio = (closest_dist_ahead_m - min_dist_m) / (max_dist_m - min_dist_m)
            ratio = ratio ** 2.0 
            
            # Reducimos nuestra 'intención global' usando el multiplicador del muelle
            target_speed = target_speed * ratio
            behavior.ignore_human = True  # [!] Mantener la distancia requiere matemáticas robóticas.

        return target_speed










    def _update_freeroam_navigation(self, ai: AI):
        """
        Cerebro de navegación libre (Freeroam).
        Mueve a la IA por el grafo topológico usando Macro y Micronavegación.
        Soporta conducción en sentido contrario (Shadow Tracking).
        """
        behavior: AIBehavior = ai.extra.get('aic')
        if not behavior: return

       # =========================================================
        # [!] CONTROL DE ATASCOS (Anti-Stuck)
        # =========================================================
        # 1. Comprobamos si la parada es intencionada (tráfico, cruces, fin de vía)
        es_parada_intencionada = behavior.target_speed_kmh < 5.0 if behavior.target_speed_kmh else True

        if es_parada_intencionada:
            # La IA quiere ir lento o detenerse. Reseteamos el temporizador para no castigarla.
            behavior.stuck_start_time = 0.0
            
        elif behavior.stuck_start_time > 0.0 and (time.time() - behavior.stuck_start_time) >= 3.0:
            # La IA quiere ir a más de 5 km/h, pero lleva 3 segundos clavada. ¡Está atascada de verdad!
            self.logger.info(f"IA {ai.ai_name} (PLID {ai.player.plid}) atascada por 3s. Enviando a espectadores...")
            self._cmd_spec(ai.player.plid)
            return  # Cortamos la ejecución de este tick

        mode: FreeroamMode = behavior.active_mode
        if not mode: return
        
        my_coords = ai.player.telemetry.coordinates
        current_speed = ai.player.telemetry.speed.speed_kmh
        
        # =========================================================
        # 1. LOCALIZACIÓN INICIAL (El Despertar)
        # =========================================================
        if not mode.freeroam_road_started:
            ctx: LocationContext = self.map_recorder.get_location_context(my_coords.x_m, my_coords.y_m, my_coords.z_m, find_zones=False)
            
            if not ctx.road_id:
                behavior.target_speed_kmh = 0.0
                return
                
            if ctx.link_dist < ctx.road_dist and ctx.link_type == 'RoadLink':
                mode.current_id = ctx.link_id
                mode.current_type = ctx.link_type
                link_obj = self.map_recorder.road_links[ctx.link_id]
                mode.current_road_id = link_obj.from_road_id
                mode.node_index = closest_idx = get_closest_node_index(my_coords, link_obj.nodes, is_waypoint=False)
                self._plan_next_link(mode, on_link=(link_obj, my_coords))
            else:
                mode.current_id = ctx.road_id
                mode.current_type = 'Road'

                # Smart Spawn al despertar
                geom = self.map_recorder.roads.get(ctx.road_id)
                if not geom or not geom.nodes:
                    behavior.target_speed_kmh = 0.0
                    return
                closest_idx = get_closest_node_index(my_coords, geom.nodes, is_waypoint=False)
                mode.node_index = determine_smart_spawn_index(my_coords, closest_idx, geom.nodes, is_waypoint=False)
                
                mode.current_road_id = ctx.road_id
                self._plan_next_link(mode)
                
            mode.freeroam_road_started = True
            return

        TRIGGER_DIST_M = 3.5

        # =========================================================
        # 2. EVALUACIÓN DE TRANSICIONES (Los "Triggers")
        # =========================================================
        _in_overtake = mode.overtake_state in ('OVERTAKING', 'RETURNING')

        # Resolver qué LatLink procesar: adelantamiento (FSM) o navegación normal
        if _in_overtake and mode.overtake_change_lane and mode.overtake_lat_link_id:
            _active_lat_id   = mode.overtake_lat_link_id
            _is_overtake_lat = True
        elif mode.next_link_id and mode.next_link_type == 'LatLink' and not _in_overtake:
            _active_lat_id   = mode.next_link_id
            _is_overtake_lat = False
        else:
            _active_lat_id   = None
            _is_overtake_lat = False

        # --- CASO LATLINK (adelantamiento o normal) ---
        if _active_lat_id:
            lat_link_obj = self.map_recorder.lateral_links[_active_lat_id]
            closest_idx  = get_closest_node_index(my_coords, lat_link_obj.nodes, is_waypoint=False)
            target_node  = lat_link_obj.nodes[closest_idx]

            # Intención predictiva (blinker)
            speed_ms    = max(current_speed / 3.6, 0.5)
            time_to_link = calc_dist_3d(my_coords.x_m, my_coords.y_m, my_coords.z_m,
                                        target_node.x_m, target_node.y_m, target_node.z_m) / speed_ms
            if not mode.future_indicator:
                _dest_road_id    = lat_link_obj.road_b if lat_link_obj.road_a == mode.current_road_id else lat_link_obj.road_a
                _is_in_fast_lane = _is_overtake_lat and mode.current_road_id == mode.overtake_fast_lane_id

                if _is_overtake_lat and not _is_in_fast_lane:
                    _raw = self._get_indicator_to_use(
                        self.map_recorder.roads[mode.current_road_id].nodes,
                        self.map_recorder.roads[_dest_road_id].nodes,
                        mode.node_index, is_opposing=False
                    )
                    if _raw == CSVAL.INDICATORS.LEFT:
                        mode.future_indicator = CSVAL.INDICATORS.RIGHT
                    elif _raw == CSVAL.INDICATORS.RIGHT:
                        mode.future_indicator = CSVAL.INDICATORS.LEFT
                    else:
                        mode.future_indicator = _raw
                else:
                    mode.future_indicator = self._get_indicator_to_use(
                        self.map_recorder.roads[mode.current_road_id].nodes,
                        self.map_recorder.roads[_dest_road_id].nodes,
                        mode.node_index, is_opposing=mode.is_driving_opposing if _is_in_fast_lane else False
                    )
            if time_to_link <= behavior.human_safe_gap and mode.blinkers_active != mode.future_indicator:
                mode.blinkers_active = mode.future_indicator
                mode._blinker_on_time = time.time()

            # Trigger: dot product — el link está a nuestro lado o ya lo hemos pasado
            _curr_geom = (self.map_recorder.roads.get(mode.current_id)     if mode.current_type == 'Road'
                     else self.map_recorder.road_links.get(mode.current_id) if mode.current_type == 'RoadLink'
                     else None)
            _at_side = False
            if _curr_geom and len(_curr_geom.nodes) >= 2:
                if mode.is_driving_opposing:
                    _ni   = max(1, min(mode.node_index, len(_curr_geom.nodes) - 1))
                    _fwd_x = _curr_geom.nodes[_ni - 1].x_m - _curr_geom.nodes[_ni].x_m
                    _fwd_y = _curr_geom.nodes[_ni - 1].y_m - _curr_geom.nodes[_ni].y_m
                else:
                    _ni   = min(mode.node_index, len(_curr_geom.nodes) - 2)
                    _fwd_x = _curr_geom.nodes[_ni + 1].x_m - _curr_geom.nodes[_ni].x_m
                    _fwd_y = _curr_geom.nodes[_ni + 1].y_m - _curr_geom.nodes[_ni].y_m
                _dot = _fwd_x * (target_node.x_m - my_coords.x_m) + _fwd_y * (target_node.y_m - my_coords.y_m)
                _at_side = _dot <= 0
                if _is_overtake_lat:
                    self.logger.debug(
                        f"[NAV:{ai.ai_name}] LatLink dot={_dot:.2f} at_side={_at_side} "
                        f"state={mode.overtake_state} cur={mode.current_road_id} "
                        f"node={mode.node_index} opposing={mode.is_driving_opposing}"
                    )

            if _at_side:
                target_road_id  = lat_link_obj.road_b if lat_link_obj.road_a == mode.current_road_id else lat_link_obj.road_a
                target_road_obj = self.map_recorder.roads[target_road_id]

                mode.previous_road_id = mode.current_road_id
                mode.current_road_id  = target_road_id
                mode.current_id       = target_road_id
                mode.current_type     = 'Road'
                mode.node_index       = get_closest_node_index(my_coords, target_road_obj.nodes, is_waypoint=False)

                if _is_overtake_lat:
                    mode.overtake_change_lane = False
                else:
                    n_id, n_type = self._calculate_next_link(mode.current_road_id, mode.previous_road_id, mode.node_index)
                    mode.next_link_id, mode.next_link_type = n_id, n_type

        # --- CASO ROADLINK ---
        elif mode.next_link_id and mode.next_link_type == 'RoadLink' and not _in_overtake:
            next_link_obj = self.map_recorder.road_links[mode.next_link_id]
            closest_idx   = get_closest_node_index(my_coords, next_link_obj.nodes, is_waypoint=False)
            target_node   = next_link_obj.nodes[closest_idx]

            dist_to_link = calc_dist_3d(my_coords.x_m, my_coords.y_m, my_coords.z_m,
                                        target_node.x_m, target_node.y_m, target_node.z_m)
            speed_ms     = max(current_speed / 3.6, 0.5)
            time_to_link = dist_to_link / speed_ms
            if time_to_link <= next_link_obj.time and mode.blinkers_active != next_link_obj.indicators:
                mode.blinkers_active = next_link_obj.indicators
                mode._blinker_on_time = time.time()

            if dist_to_link < TRIGGER_DIST_M:
                mode.current_id  = mode.next_link_id
                mode.current_type = 'RoadLink'
                mode.node_index  = determine_smart_spawn_index(my_coords, closest_idx, next_link_obj.nodes, is_waypoint=False)
                self._plan_next_link(mode, on_link=(next_link_obj, ai.player.telemetry.coordinates))

        # =========================================================
        # 3. EXTRACCIÓN Y PROGRESIÓN (Acelerar y Avanzar)
        # =========================================================
        nodes_list = []
        
        if mode.current_type == 'Road':
            geom = self.map_recorder.roads.get(mode.current_id)
            if geom and geom.nodes:
                nodes_list = geom.nodes

                # Apagamos intermitentes SOLO cuando hayamos terminado la maniobra y se cumple el mínimo
                if mode.blinkers_active != CSVAL.INDICATORS.OFF:
                    elapsed = time.time() - (mode._blinker_on_time or 0)
                    if elapsed >= mode._blinker_min_duration:
                        mode.blinkers_active = CSVAL.INDICATORS.OFF
                
        elif mode.current_type == 'RoadLink':
            geom = self.map_recorder.road_links.get(mode.current_id)
            if geom and geom.nodes:
                nodes_list = geom.nodes

        # Si por algún motivo nodes_list está vacío, abortamos este ciclo de progresión
        if not nodes_list:
            return

        is_opposing = getattr(mode, 'is_driving_opposing', False)

        # --- 1. ANTI-LAG (Recuperar la trazada si nos saltamos un nodo) ---
        mode.node_index = apply_antilag_window(
            my_coords=my_coords, 
            current_idx=mode.node_index, 
            list_of_nodes=nodes_list, 
            window_size=5, 
            is_waypoint=False,
            is_driving_opposing=is_opposing
        )

        # --- 2. CAPTURA DINÁMICA (Verificar si alcanzamos el nodo actual) ---
        next_index = evaluate_dynamic_capture(
            my_coords=my_coords,
            current_target_idx=mode.node_index,
            list_of_nodes=nodes_list,
            speed_kmh=current_speed,
            min_radius=2.5, 
            max_radius=12.0, 
            lookahead_time=0.3,
            is_waypoint=False,
            is_driving_opposing=is_opposing
        )
        
        # PROGRESIÓN: Avanzamos si la captura tuvo éxito en nuestro sentido
        avanzamos = (next_index < mode.node_index) if is_opposing else (next_index > mode.node_index)

        if avanzamos:
            mode.node_index = next_index
            
            # ¿Nos quedamos sin nodos en la geometría actual?
            fin_de_geometria = (mode.node_index < 0) if is_opposing else (mode.node_index >= len(nodes_list))
            
            if fin_de_geometria:
                
                # --- CASO EXCEPCIONAL: FIN DE VÍA OPUESTA ---
                if is_opposing:
                    self.logger.warning(f"IA {ai.ai_name} se quedó sin asfalto en sentido contrario. Forzando retorno de emergencia.")
                    mode.is_driving_opposing = False
                    mode.overtake_state = 'RETURNING'
                    mode.node_index = 0  # Prevenimos crash por OutOfIndex mientras la FSM reincorpora
                    return
                
                # --- CASO NORMAL ---
                if mode.current_type == 'RoadLink':
                    geom = self.map_recorder.road_links[mode.current_id]
                    mode.previous_road_id = mode.current_road_id
                    mode.current_road_id = geom.to_road_id
                    mode.current_id = geom.to_road_id
                    mode.current_type = 'Road'
                    
                    target_road_obj = self.map_recorder.roads[geom.to_road_id]
                    # Smart Spawn final para incorporarse a la vía principal
                    closest_idx = get_closest_node_index(my_coords, target_road_obj.nodes, is_waypoint=False)
                    mode.node_index = determine_smart_spawn_index(my_coords, closest_idx, target_road_obj.nodes, is_waypoint=False)
                    return 

                elif mode.current_type == 'Road':
                    geom = self.map_recorder.roads[mode.current_id]
                    if geom.is_circular:
                        mode.node_index = 0
                        return
                    elif not mode.next_link_id:
                        behavior.target_speed_kmh = 0.0
                        if ai.player.telemetry.speed.speed_kmh < 1: self._cmd_spec(ai.player.plid)
                        return
                    else:
                        # Llegamos al final con un next_link_id que nunca se activó — recalcular
                        mode.node_index = max(0, len(nodes_list) - 2)
                        self._plan_next_link(mode)
                        return

        # =========================================================
        # ASIGNACIÓN FINAL AL COCHE Y TOMA DE DECISIONES
        # =========================================================
        self._update_traffic_behavior(ai)

        # -----------------------------------------------------------------
        # [!] GESTOR DE ESTADOS HARDWARE (ACCIÓN FINAL)
        # -----------------------------------------------------------------
        mode.extra_inputs_to_send.clear() 

        if getattr(mode, 'blinkers_active_now', None) != mode.blinkers_active:
            mode.extra_inputs_to_send.append(AIV(Input=CS.INDICATORS, Value=mode.blinkers_active))
            mode.blinkers_active_now = mode.blinkers_active
    
    def _get_indicator_to_use(self, my_road_nodes: List[Coordinates], other_road_nodes: List[Coordinates], node_index, is_opposing: bool = False) -> CSVAL.INDICATORS:
        # Seguridad: necesitamos al menos 2 nodos para trazar nuestra dirección
        if len(my_road_nodes) < 2 or not other_road_nodes:
            return CSVAL.INDICATORS.OFF

        # 1. Obtenemos el vector de dirección de nuestro carril actual (Adelante)
        # Usamos mode.node_index asegurándonos de no salirnos de los límites
        idx = min(node_index, len(my_road_nodes) - 2)
        p1 = my_road_nodes[idx]
        p2 = my_road_nodes[idx + 1]

        v_fwd_x = p2.x_m - p1.x_m
        v_fwd_y = p2.y_m - p1.y_m

        # Si vamos en sentido contrario al orden de nodos, invertimos el vector
        if is_opposing:
            v_fwd_x = -v_fwd_x
            v_fwd_y = -v_fwd_y
        
        # 2. Buscamos el nodo más cercano en el carril de destino REUTILIZANDO tu método
        best_idx, _ = self._get_closest_node_index(p1.x_m, p1.y_m, other_road_nodes)
        closest_other = other_road_nodes[best_idx]
        
        # 3. Obtenemos el vector lateral (Desde nosotros hacia el nodo más cercano del otro carril)
        v_side_x = closest_other.x_m - p1.x_m
        v_side_y = closest_other.y_m - p1.y_m
        
        # 4. Producto Cruzado 2D (Determinante matemático)
        cross_product = (v_fwd_x * v_side_y) - (v_fwd_y * v_side_x)
        
        # 5. Evaluación del resultado
        if cross_product > 0:
            return CSVAL.INDICATORS.LEFT
        elif cross_product < 0:
            return CSVAL.INDICATORS.RIGHT
        else:
            return CSVAL.INDICATORS.OFF

    def _is_link_reachable_ahead(self, current_road_nodes: List[Coordinates], current_index: int, link_nodes: List[Coordinates], max_dist: float = 3.5) -> bool:
        """
        Verifica si el enlace es alcanzable en el tramo de vía que le queda por recorrer a la IA.
        Utiliza culling espacial para optimizar el rendimiento.
        """
        if not current_road_nodes or not link_nodes:
            return False
            
        remaining_road = current_road_nodes[current_index:]
        FAST_CULLING_RADIUS = max_dist + 30.0 

        for l_node in link_nodes:
            for i in range(len(remaining_road) - 1):
                node_a = remaining_road[i]
                
                # 1. Filtro rápido
                fast_dist = math.hypot(l_node.x_m - node_a.x_m, l_node.y_m - node_a.y_m)
                if fast_dist > FAST_CULLING_RADIUS:
                    continue
                    
                # 2. Cálculo preciso
                node_b = remaining_road[i + 1]
                dist = calc_dist_point_to_segment_2d(
                    l_node.x_m, l_node.y_m, 
                    node_a.x_m, node_a.y_m, 
                    node_b.x_m, node_b.y_m
                )
                
                if dist <= max_dist:
                    return True
                    
        return False

    def _get_raw_candidates(self, current_road_id: str) -> List[Tuple[str, str, str, List[Coordinates]]]:
        """
        Sub-función de apoyo. Recopila todos los enlaces salientes posibles 
        sin importar su viabilidad en este momento.
        Devuelve una lista de tuplas: (link_id, link_type, target_road_id, link_nodes)
        """
        candidatos = []

        # 1. Recopilar RoadLinks
        for l_id, link in self.map_recorder.road_links.items():
            if link.from_road_id == current_road_id:
                candidatos.append((l_id, 'RoadLink', link.to_road_id, link.nodes))

        # 2. Recopilar LateralLinks (ignorando los exclusivos de adelantamiento)
        for l_id, link in self.map_recorder.lateral_links.items():
            if link.made_to_overtake:
                continue
                
            if link.road_a == current_road_id and link.allow_a_to_b:
                candidatos.append((l_id, 'LatLink', link.road_b, link.nodes))
            elif link.road_b == current_road_id and link.allow_b_to_a:
                candidatos.append((l_id, 'LatLink', link.road_a, link.nodes))

        return candidatos

    def _calculate_next_link(self, current_road_id: str, previous_road_id: Optional[str], current_index: int) -> Tuple[Optional[str], Optional[Literal['RoadLink', 'LatLink']]]:
        """
        Busca todos los enlaces salientes de la vía actual, los pasa por un filtro de validación
        y elige aleatoriamente uno que sea válido.
        """
        current_road = self.map_recorder.roads.get(current_road_id)
        if not current_road:
            return None, None

        opciones_validas = []
        opciones_retorno = []

        # 0. Si la vía es circular, seguir en ella se considera una opción válida de retorno
        if current_road.is_circular:
            opciones_retorno.append((None, None))

        # 1. Obtener todos los candidatos "en bruto"
        candidatos = self._get_raw_candidates(current_road_id)

        # 2. Filtrar y clasificar usando una única lógica centralizada
        for l_id, l_type, target_road_id, link_nodes in candidatos:
            target_road = self.map_recorder.roads.get(target_road_id)
            
            # Filtro A: La vía de destino debe existir y estar abierta
            if not target_road or target_road.is_closed:
                continue
                
            # Filtro B: Alcance espacial (Se ignora si estamos en una vía circular)
            if not current_road.is_circular:
                if not self._is_link_reachable_ahead(current_road.nodes, current_index, link_nodes, max_dist=8.0):
                    continue
            
            # Clasificación final
            if target_road_id == previous_road_id:
                opciones_retorno.append((l_id, l_type))
            else:
                opciones_validas.append((l_id, l_type))

        # 3. Decisión final
        if opciones_validas:
            return random.choice(opciones_validas)
        elif opciones_retorno:
            return random.choice(opciones_retorno)
            
        return None, None

    def _plan_next_link(self, mode: FreeroamMode, on_link: Optional[Tuple[RoadLink, Coordinates]] = None):
        """Calcula y asigna directamente al estado de la IA su próximo enlace objetivo."""
        if on_link:
            link_obj = on_link[0]
            coordinates = on_link[1]
            nodes = self.map_recorder.roads[link_obj.to_road_id].nodes
            node_index, _ = self._get_closest_node_index(coordinates.x_m, coordinates.y_m, nodes)
            n_id, n_type = self._calculate_next_link(link_obj.to_road_id, link_obj.from_road_id, node_index)
        else:
            if not mode.current_road_id: return  # Seguridad
            n_id, n_type = self._calculate_next_link(mode.current_road_id, mode.previous_road_id, mode.node_index)
        mode.next_link_id = n_id
        mode.next_link_type = n_type

    def _get_closest_node_index(self, px: float, py: float, nodes: List[Coordinates]) -> tuple[int, float]:
        """Devuelve el (índice, distancia) del nodo más cercano a px, py."""
        min_dist = float('inf')
        best_idx = 0
        for i, node in enumerate(nodes):
            # Asumo que tienes math.hypot o similar importado
            dist = math.hypot(px - node.x_m, py - node.y_m) 
            if dist < min_dist:
                min_dist = dist
                best_idx = i
        return best_idx, min_dist
