"""Orquestador del comportamiento de tráfico: se llama una vez por IA y por
paquete MCI, y coordina radar, ACC, zonas de intersección y FSM de
adelantamiento.

Auto-regula el radar con una compuerta (`_radar_interval`, ~7-10 Hz por IA con
jitter para desincronizar las IAs). NO tiene red de tests de caracterización:
usa `time.time()` y muta mucho estado del `mode` (ver AUDITORIA_HOTLOOP.md)."""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

from insims.ai_control.base import _MixinBase
from insims.ai_control.behavior import AIBehavior
from insims.ai_control.nav_modes.freeroam.enums import AIManeuverState, TrafficRule
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode

if TYPE_CHECKING:
    from insims.users_management.main import AI


class _OrchestratorMixin(_MixinBase):
    def _should_keep_yielding(
        self, detected: bool, hold_until: float, now: float
    ) -> bool:
        """Histéresis del ceda-el-paso (anti-parpadeo). True si la IA debe seguir
        cediendo: hay un prioritario detectado este tick, o aún no ha expirado el
        `hold_until` de la última detección. Evita soltar el yield —y pegar un
        acelerón contra el freno de mano— por un único tick sin detección."""
        return detected or now < hold_until

    def _update_traffic_behavior(self, ai: AI) -> None:
        """
        Orquestador táctico (Navegación Micro).
        Sigue el patrón Sense-Think-Act gestionando su propia frecuencia de escaneo
        y operando la Máquina de Estados de Adelantamiento (FSM).
        """
        behavior: AIBehavior = ai.extra.get("aic")
        if not behavior or not ai.player.telemetry:
            return

        mode: FreeroamMode = behavior.active_mode
        if not mode:
            return

        # =========================================================
        # 1. RECUPERAR CONTEXTO ESPACIAL Y ESTADOS
        # =========================================================
        nodes_list = []
        if mode.current_type == "Road":
            geom = self.map_recorder.roads.get(mode.current_id)
        elif mode.current_type == "RoadLink":
            geom = self.map_recorder.road_links.get(mode.current_id)
        else:
            geom = None

        if not geom or mode.node_index >= len(geom.nodes):
            return

        nodes_list = geom.nodes
        min_vel = getattr(geom, "min_speed_kmh", 15.0)
        limite_vel = getattr(geom, "speed_limit_kmh", 30.0)

        # Override de velocidad por SpecialRule activa
        for rule_id in mode.active_special_rules:
            rule = self.map_recorder.special_rules.get(rule_id)
            if rule and "speed_limit" in rule.rules:
                override = rule.rules["speed_limit"]
                limite_vel = min(limite_vel, override)
                min_vel = min(min_vel, override / 2.0)

        velocidad_base = min_vel + (limite_vel - min_vel) * getattr(
            mode, "speed_limit_bias", 0.5
        )
        mode._debug_speed_base = velocidad_base
        my_coords = ai.player.telemetry.coordinates

        # =========================================================
        # 2. CONTROL DE FRECUENCIA Y PATRÓN SENSE-THINK-ACT
        # =========================================================
        current_time = time.time()

        if current_time - mode._last_radar_time >= mode._radar_interval:
            my_speed_ms = max(ai.player.telemetry.speed.speed_kmh / 3.6, 0.1)
            safe_gap_s = behavior.human_safe_gap
            warn_gap_s = behavior.human_warn_gap
            min_dist_m = max(5.0, my_speed_ms * safe_gap_s)
            max_dist_m = max(15.0, my_speed_ms * warn_gap_s)

            # Por defecto, asumimos que podemos ir a la velocidad base
            velocidad_segura = velocidad_base

            # =========================================================
            # MÁQUINA DE ESTADOS FINITOS (FSM) DEL ADELANTAMIENTO
            # =========================================================
            lookahead_dist_m = max(15.0, my_speed_ms * 10.0)
            vehicles_ahead = self._scan_lane_ahead(ai, mode, lookahead_dist_m)

            # ---------------------------------------------------------
            # ESTADO: IDLE (Conducción Normal)
            # ---------------------------------------------------------
            if mode.overtake_state == "IDLE":
                if vehicles_ahead:
                    closest_dist, closest_speed_kmh, closest_plid = vehicles_ahead[0]

                    # ACC siempre activo
                    velocidad_segura = self._apply_adaptive_cruise_control(
                        velocidad_base,
                        closest_speed_kmh,
                        closest_dist,
                        min_dist_m,
                        max_dist_m,
                    )
                    mode.blocking_plid = closest_plid
                    mode.blocking_dist = closest_dist

                    # Gatillo: coche delante ≥5% más lento, sin cooldown, sin regla bloqueante
                    lane_change_blocked = any(
                        self.map_recorder.special_rules.get(rid)
                        and self.map_recorder.special_rules[rid].rules.get(
                            "no_lane_change", False
                        )
                        for rid in mode.active_special_rules
                    )
                    if (
                        not lane_change_blocked
                        and closest_speed_kmh < velocidad_base * 0.95
                        and current_time > mode.overtake_cooldown
                        and closest_dist < max_dist_m
                    ):
                        mode.overtake_state = "EVALUATING"
                        mode.overtake_target_plid = closest_plid
                        mode.overtake_return_lane_id = mode.current_road_id
                    elif lane_change_blocked:
                        pass  # no_lane_change activo — sin log (demasiado frecuente)
                else:
                    mode.blocking_plid = None
                    mode.blocking_dist = 0.0

            # ---------------------------------------------------------
            # ESTADO: EVALUATING (Análisis de viabilidad)
            # ---------------------------------------------------------
            elif mode.overtake_state == "EVALUATING":
                velocidad_segura = mode._cached_target_speed
                mode.maneuver_state = AIManeuverState.FOLLOWING

                current_rule = getattr(geom, "traffic_rule", TrafficRule.LHT)
                target_road_id, target_lat_id = self._find_valid_overtake_lane(
                    mode.current_road_id, current_rule, nodes_list, mode.node_index
                )

                if target_road_id:
                    target_road_geom = self.map_recorder.roads.get(target_road_id)
                    lat_link = self.map_recorder.lateral_links.get(target_lat_id)

                    if target_road_geom and lat_link:
                        is_opposing = lat_link.opposing

                        distances_ahead_m = [v[0] for v in vehicles_ahead]
                        rel_dist_m = self._get_relative_dist_to_cover(
                            distances_ahead_m, extra_dist=5.0
                        )

                        overtake_speed = (
                            target_road_geom.speed_limit_kmh * mode.speed_limit_bias
                        )
                        target_speed = (
                            vehicles_ahead[0][1]
                            if vehicles_ahead
                            else velocidad_base * 0.8
                        )
                        req_dist_m, time_to_overtake_s = (
                            self._estimate_overtake_distance(
                                overtake_speed, target_speed, rel_dist_m
                            )
                        )

                        if req_dist_m != float("inf"):
                            es_seguro = self._is_lane_safe_to_overtake(
                                ai,
                                mode,
                                target_road_id,
                                lat_link,
                                is_opposing,
                                req_dist_m,
                                time_to_overtake_s,
                            )
                            if es_seguro:
                                mode.overtake_lat_link_id = target_lat_id
                                mode.overtake_change_lane = True
                                mode.overtake_fast_lane_id = target_road_id
                                mode.is_driving_opposing = is_opposing
                                mode.overtake_state = "OVERTAKING"
                                mode.maneuver_state = AIManeuverState.OVERTAKING
                                mode.future_indicator = None
                                # Tiempo hasta estar en paralelo con el target: dist / speed_delta
                                _our_speed_ms = (
                                    target_road_geom.speed_limit_kmh
                                    * mode.speed_limit_bias
                                    * 1.05
                                ) / 3.6
                                _target_speed_ms = target_speed / 3.6
                                _closest_dist_m = (
                                    vehicles_ahead[0][0] if vehicles_ahead else 0.0
                                )
                                _speed_delta = max(
                                    _our_speed_ms - _target_speed_ms, 0.1
                                )
                                _time_to_parallel = _closest_dist_m / _speed_delta

                                mode._passing_start_time = current_time
                                mode._overtake_no_return_until = (
                                    current_time + _time_to_parallel
                                )
                            else:
                                mode.overtake_state = "IDLE"
                                mode.maneuver_state = AIManeuverState.NORMAL
                                mode.overtake_cooldown = current_time + 4.0
                        else:
                            mode.overtake_state = "IDLE"
                            mode.maneuver_state = AIManeuverState.NORMAL
                            mode.overtake_cooldown = current_time + 5.0
                    else:
                        mode.overtake_state = "IDLE"
                        mode.maneuver_state = AIManeuverState.NORMAL
                        mode.overtake_cooldown = current_time + 2.0
                else:
                    mode.overtake_state = "IDLE"
                    mode.maneuver_state = AIManeuverState.NORMAL
                    mode.overtake_cooldown = current_time + 3.0

            # ---------------------------------------------------------
            # ESTADO: OVERTAKING (Maniobra en el carril rápido)
            # ---------------------------------------------------------
            elif mode.overtake_state == "OVERTAKING":
                in_fast_lane = mode.current_road_id == mode.overtake_fast_lane_id

                # Nav cruzó el LatLink de entrada (una sola vez): estamos en el carril rápido.
                if (
                    in_fast_lane
                    and not mode.overtake_change_lane
                    and not mode._fast_lane_logged
                ):
                    mode._fast_lane_logged = True
                    mode.future_indicator = None

                # Velocidad: base +5% como máximo
                velocidad_segura = velocidad_base * 1.05

                # ACC en el carril rápido
                if vehicles_ahead:
                    f_dist, f_speed, _ = vehicles_ahead[0]
                    velocidad_segura = min(
                        velocidad_segura,
                        self._apply_adaptive_cruise_control(
                            velocidad_base, f_speed, f_dist, min_dist_m, max_dist_m
                        ),
                    )

                # Emergencia frontal (solo en carril contrario y ya dentro)
                if mode.is_driving_opposing and in_fast_lane and vehicles_ahead:
                    ONCOMING_EMERGENCY_S = 3.0
                    ONCOMING_DANGER_S = 5.0
                    f_dist, f_speed, _ = vehicles_ahead[0]
                    closing_speed_ms = my_speed_ms + max(f_speed / 3.6, 0.1)
                    time_to_frontal = f_dist / closing_speed_ms
                    if time_to_frontal < ONCOMING_EMERGENCY_S:
                        self._trigger_return(mode, current_time)
                        velocidad_segura = 0
                    elif time_to_frontal < ONCOMING_DANGER_S:
                        velocidad_segura = 0

                # Retorno normal: timer expirado + hueco libre en el carril original
                if (
                    in_fast_lane
                    and mode.overtake_state == "OVERTAKING"
                    and current_time >= mode._overtake_no_return_until
                ):
                    ahead_gap, behind_gap = self._scan_return_lane_gap(
                        ai, mode, max_dist_m
                    )
                    if ahead_gap >= min_dist_m and behind_gap >= min_dist_m:
                        self._trigger_return(mode, current_time)

            # ---------------------------------------------------------
            # ESTADO: RETURNING (Volviendo al carril original)
            # ---------------------------------------------------------
            elif mode.overtake_state == "RETURNING":
                velocidad_segura = velocidad_base

                if mode.current_road_id == mode.overtake_return_lane_id:
                    self._finish_overtake(mode, current_time)
                elif current_time - mode._returning_start_time > 5.0:
                    self._finish_overtake(mode, current_time)

            # Guardamos el resultado en caché
            mode._cached_target_speed = velocidad_segura
            mode._last_radar_time = current_time

            # =========================================================
            # CONTROL DE INTERSECCIONES (Ceda el Paso)
            # =========================================================
            YIELD_LOOK_AHEAD_s = (
                5.0  # Anticipación: cuántos segundos adelante miramos el cruce
            )
            PRIORITY_APPROACH_s = (
                4.0  # Ventana para detectar coche prioritario aproximándose
            )
            YIELD_HOLD_S = 1.0  # Histéresis: se sigue cediendo este tiempo tras la última detección

            if hasattr(self.map_recorder, "zones") and self.map_recorder.zones:
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
                    dist_al_borde = self._get_dist_to_zone_edge(
                        my_coords.x_m, my_coords.y_m, zone
                    )
                    yield_range_m = max(15.0, my_speed_ms * YIELD_LOOK_AHEAD_s)

                    if dist_al_borde > yield_range_m:
                        continue

                    # Si no estamos ya dentro de la zona, verificamos que vamos hacia ella
                    if dist_al_borde > 0.1:
                        zone_cx, zone_cy = self._get_zone_centroid(zone)
                        my_heading_rad = (
                            ai.player.telemetry.heading.angle_lfs
                            * 2.0
                            * math.pi
                            / 65536.0
                        )
                        my_fwd_x = -math.sin(my_heading_rad)
                        my_fwd_y = math.cos(my_heading_rad)
                        vec_x = zone_cx - my_coords.x_m
                        vec_y = zone_cy - my_coords.y_m
                        if my_fwd_x * vec_x + my_fwd_y * vec_y <= 0.0:
                            continue  # Nos alejamos: ignorar

                    # 3. Pre-filtro esférico usando el centroide real de la zona
                    zone_cx, zone_cy = self._get_zone_centroid(zone)
                    radio_filtro = zone.radius_m + max(
                        20.0, my_speed_ms * PRIORITY_APPROACH_s * 1.5
                    )

                    # 4. Escanear vehículos prioritarios (dentro O aproximándose con dirección correcta)
                    coche_prioritario_detectado = False

                    # 4.A IAs
                    for a in self.user_manager.ais.values():
                        if a.player.plid == ai.player.plid or not a.player.telemetry:
                            continue

                        other_coords = a.player.telemetry.coordinates
                        if (
                            math.hypot(
                                zone_cx - other_coords.x_m, zone_cy - other_coords.y_m
                            )
                            > radio_filtro
                        ):
                            continue

                        other_road_id = None
                        if a.extra.get("aic") and a.extra["aic"].active_mode:
                            other_road_id = a.extra["aic"].active_mode.current_road_id

                        if other_road_id in vias_prioritarias_a_vigilar:
                            other_heading_lfs = a.player.telemetry.heading.angle_lfs
                            other_speed_kmh = a.player.telemetry.speed.speed_kmh
                            if self._is_priority_vehicle_active_at_zone(
                                other_coords,
                                other_speed_kmh,
                                other_heading_lfs,
                                zone,
                                PRIORITY_APPROACH_s,
                            ):
                                coche_prioritario_detectado = True
                                break

                    # 4.B Jugadores reales
                    if not coche_prioritario_detectado:
                        for p in self.user_manager.players.values():
                            if p.plid == ai.player.plid or not p.telemetry:
                                continue

                            other_coords = p.telemetry.coordinates
                            if (
                                math.hypot(
                                    zone_cx - other_coords.x_m,
                                    zone_cy - other_coords.y_m,
                                )
                                > radio_filtro
                            ):
                                continue

                            ctx = self.map_recorder.get_location_context(
                                other_coords.x_m,
                                other_coords.y_m,
                                other_coords.z_m,
                                find_links=False,
                                find_zones=False,
                            )

                            if ctx.road_id in vias_prioritarias_a_vigilar:
                                other_heading_lfs = p.telemetry.heading.angle_lfs
                                other_speed_kmh = p.telemetry.speed.speed_kmh
                                if self._is_priority_vehicle_active_at_zone(
                                    other_coords,
                                    other_speed_kmh,
                                    other_heading_lfs,
                                    zone,
                                    PRIORITY_APPROACH_s,
                                ):
                                    coche_prioritario_detectado = True
                                    break

                    # 5. Aplicar freno o limpiar estado (con histéresis anti-parpadeo:
                    #    detectar renueva el hold; sin detección se cede hasta que expira).
                    now = time.time()
                    if coche_prioritario_detectado:
                        mode._yield_hold_until = now + YIELD_HOLD_S
                        mode.yield_zone_id = zone_id
                    hold_until = (
                        mode._yield_hold_until if mode.yield_zone_id == zone_id else 0.0
                    )
                    if self._should_keep_yielding(
                        coche_prioritario_detectado, hold_until, now
                    ):
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
            if (
                hasattr(self.map_recorder, "special_rules")
                and self.map_recorder.special_rules
            ):
                for rule_id, rule in self.map_recorder.special_rules.items():
                    if len(rule.nodes) < 2:
                        continue
                    start_node = rule.nodes[0]
                    end_node = rule.nodes[1]
                    dist_start = math.hypot(
                        my_coords.x_m - start_node.x_m, my_coords.y_m - start_node.y_m
                    )
                    dist_end = math.hypot(
                        my_coords.x_m - end_node.x_m, my_coords.y_m - end_node.y_m
                    )

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
        _reverse_lookahead = getattr(
            mode, "is_driving_opposing", False
        ) and mode.current_road_id == getattr(mode, "overtake_fast_lane_id", None)
        la_x, la_y = self._get_lookahead_point(
            my_coords.x_m,
            my_coords.y_m,
            mode.node_index,
            nodes_list,
            lookahead_m,
            reverse=_reverse_lookahead,
        )
        behavior.point_request = (la_x, la_y)
        behavior.speed_request = velocidad_final
