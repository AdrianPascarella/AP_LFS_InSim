"""Orquestador del comportamiento de tráfico: se llama una vez por IA y por
paquete MCI, y coordina radar, ACC, cesión de paso (por RoadLink, Fase 8) y
FSM de adelantamiento.

Auto-regula el radar con una compuerta (`_radar_interval`, ~7-10 Hz por IA con
jitter para desincronizar las IAs). Red de tests: el marco (asignación final,
compuerta, reglas especiales) y la conducta de cesión en test_orchestrator.py;
el gatillo del adelantamiento en test_traffic.py (S34)."""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

from insims.ai_control.base import _MixinBase
from insims.ai_control.behavior import AIBehavior
from insims.ai_control.nav_modes.freeroam.enums import (
    AIManeuverState,
    TrafficRule,
    YieldType,
)
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from insims.ai_control.traffic.cruise_control import PARADA_ABSOLUTA_M
from insims.ai_control.traffic.yielding import (
    DEFAULT_YIELD_STOP_HOLD_S,
    STOPPED_SPEED_MS,
    has_crossed_line,
)

if TYPE_CHECKING:
    from insims.users_management.main import AI

# Suelo de la distancia de seguridad (m): el hueco que dejan los coches entre sí cuando
# el time-gap (velocidad × segundos) se queda corto — marcha lenta y, sobre todo, parados
# en cola. Subido de 5 a 8 m en S35 a petición del usuario ("un poco más grande"). Es el
# dial del hueco mínimo junto con `PARADA_ABSOLUTA_M` (7 m) de cruise_control.py, que es
# el suelo duro por debajo del cual se para en seco. Ajustable.
MIN_GAP_FLOOR_M = 8.0


class _OrchestratorMixin(_MixinBase):
    def _should_keep_yielding(
        self, detected: bool, hold_until: float, now: float
    ) -> bool:
        """Histéresis del ceda-el-paso (anti-parpadeo). True si la IA debe seguir
        cediendo: hay un prioritario detectado este tick, o aún no ha expirado el
        `hold_until` de la última detección. Evita soltar el yield —y pegar un
        acelerón contra el freno de mano— por un único tick sin detección."""
        return detected or now < hold_until

    def _stop_pending(self, mode, link, my_speed_ms: float, now: float) -> bool:
        """¿Este link es un STOP que todavía no ha cumplido su parada? (S44)

        Un `STOP` para siempre, venga alguien o no: frena hasta detenerse de
        verdad (v≈0 ⇒ `STOPPED_SPEED_MS`), aguanta `yield_stop_hold_s` clavado
        y solo entonces se da por cumplido — a partir de ahí evalúa como un
        `YIELD` normal. La marca es por link: cambiar de enlace exige parar otra
        vez.

        Devuelve True mientras la parada esté pendiente (⇒ hay que frenar).
        """
        if link.yield_type is not YieldType.STOP:
            return False

        if mode.yield_stop_done_link_id == link.link_id:
            return False  # ya paró en ESTE link: ahora es un YIELD

        if mode.yield_stop_link_id != link.link_id:
            # Primer tick ante este STOP: empieza la maniobra de parada.
            mode.yield_stop_link_id = link.link_id
            mode._yield_stopped_since = 0.0
            return True

        if my_speed_ms >= STOPPED_SPEED_MS:
            mode._yield_stopped_since = 0.0  # aún rueda: la cuenta no empieza
            return True

        if mode._yield_stopped_since == 0.0:
            mode._yield_stopped_since = now  # acaba de detenerse: arranca el reloj
            return True

        hold_s = self.config.get("yield_stop_hold_s", DEFAULT_YIELD_STOP_HOLD_S)
        if now - mode._yield_stopped_since < hold_s:
            return True  # aguantando la parada

        mode.yield_stop_done_link_id = link.link_id
        return False

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
            # Distancia de seguridad por time-gap, con un SUELO para la marcha lenta y el
            # parado (a 0 km/h el time-gap se iría a 0). Ese suelo es el hueco que dejan
            # los coches en una cola: subido de 5 a 8 m en S35 a petición del usuario.
            min_dist_m = max(MIN_GAP_FLOOR_M, my_speed_ms * safe_gap_s)
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
                    # Nunca se ABRE una maniobra dentro de un cruce: ahí el radar ve la
                    # cadena del enlace (Fase 7 · fix (3)) y el coche que bloquea puede
                    # ir por otra vía, pero `_find_valid_overtake_lane` buscaría carril
                    # en la vía que ya dejamos, con el `node_index` del enlace. En un
                    # RoadLink se frena por él (ACC) y punto. Un adelantamiento YA en
                    # curso no se toca: lo cierran sus propios estados del FSM.
                    if (
                        mode.current_type == "Road"
                        and not lane_change_blocked
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
            # CONTROL DE INTERSECCIONES (cesión por RoadLink, Fase 8)
            # =========================================================
            # La cesión cuelga del giro: un RoadLink con `yield_type` YIELD/STOP
            # y su `yield_point` marcado obliga a frenar ANTES de la línea —que
            # se DERIVA del punto (S44)— si `_yield_threat_detected` ve tráfico
            # a menos de T segundos de algún punto de conflicto. Cruzada la
            # línea, la maniobra está comprometida y NO se frena en mitad del
            # cruce. `STOP` además para siempre, venga alguien o no.
            YIELD_LOOK_AHEAD_S = (
                5.0  # Anticipación: a cuántos segundos por delante se mira la línea
            )
            YIELD_HOLD_S = 1.0  # Histéresis: se sigue cediendo este tiempo tras la última detección

            if mode.current_type == "RoadLink":
                candidato = self.map_recorder.road_links.get(mode.current_id)
            elif mode.current_type == "Road" and mode.next_link_type == "RoadLink":
                candidato = self.map_recorder.road_links.get(mode.next_link_id)
            else:
                candidato = None

            cediendo = False
            if candidato is not None and candidato.has_yield and candidato.nodes:
                linea = self._yield_line_of(candidato)
                punto_union = candidato.nodes[-1]
                comprometida = has_crossed_line(
                    my_coords.x_m,
                    my_coords.y_m,
                    linea,
                    punto_union.x_m,
                    punto_union.y_m,
                )
                dist_linea_m = self._dist_to_yield_line_m(
                    my_coords.x_m, my_coords.y_m, linea
                )
                yield_range_m = max(15.0, my_speed_ms * YIELD_LOOK_AHEAD_S)

                if not comprometida and dist_linea_m <= yield_range_m:
                    now = time.time()
                    # El STOP manda mientras no haya cumplido su parada: para
                    # aunque no venga nadie. Cumplida, evalúa como un YIELD.
                    parando = self._stop_pending(mode, candidato, my_speed_ms, now)
                    detectado = parando or self._yield_threat_detected(ai, candidato)
                    # Histéresis anti-parpadeo (fix (5), S33): detectar renueva
                    # el hold; sin detección se cede hasta que expira.
                    if detectado:
                        mode._yield_hold_until = now + YIELD_HOLD_S
                        mode.yield_link_id = candidato.link_id
                    hold_until = (
                        mode._yield_hold_until
                        if mode.yield_link_id == candidato.link_id
                        else 0.0
                    )
                    if self._should_keep_yielding(detectado, hold_until, now):
                        cediendo = True
                        mode.yield_active = True
                        mode.yield_link_id = candidato.link_id
                        # Freno: ACC contra un "coche parado" fantasma colocado
                        # PARADA_ABSOLUTA_M más allá de la línea → el morro se
                        # detiene EN la línea, no un radio arbitrario antes.
                        velocidad_cesion = self._apply_adaptive_cruise_control(
                            base_speed_kmh=velocidad_base,
                            closest_speed_kmh=0.0,
                            closest_dist_m=dist_linea_m + PARADA_ABSOLUTA_M,
                            min_dist_m=min_dist_m,
                            max_dist_m=yield_range_m,
                        )
                        velocidad_segura = min(velocidad_segura, velocidad_cesion)

            if not cediendo and mode.yield_active:
                mode.yield_active = False
                mode.yield_link_id = None

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
