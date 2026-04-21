from __future__ import annotations
import time
from typing import TYPE_CHECKING

from lfs_insim.insim_packet_class import CSVAL, AIInputVal as AIV, CS
from lfs_insim.utils import calc_dist_3d, calc_target_heading, get_heading_diff, lfs_pos_to_meters
from insims.ai_control.behavior import AIBehavior, AdaptiveSpeedConfig, GearMode
from insims.users_management.main import Coordinates
from insims.ai_control.base import _MixinBase

if TYPE_CHECKING:
    from insims.users_management.main import AI, Telemetry


class _PhysicsMixin(_MixinBase):
    def _handle_steering(self, ai: AI) -> list[AIV]:
        behavior: AIBehavior = ai.extra['aic']
        
        if not behavior.target_point_m:
            return [AIV(Input=CS.STEER, Value=CSVAL.STEER.CENTRE)]
        
        if isinstance(behavior.target_point_m, int):
            # Es un PLID: buscamos sus coordenadas actuales en players o ais
            target_plid = behavior.target_point_m
            if target_plid in self.user_manager.players:
                behavior.target_point_use = self.user_manager.players[target_plid].telemetry.coordinates
            elif target_plid in self.user_manager.ais:
                behavior.target_point_use = self.user_manager.ais[target_plid].player.telemetry.coordinates
            else:
                # [!] ESCUDO DE SEGURIDAD: El objetivo ha desaparecido
                self.logger.warning(f"La IA {ai.ai_name} ha perdido a su objetivo (PLID {target_plid}).")
                behavior.reset_direction()
                return [AIV(Input=CS.STEER, Value=CSVAL.STEER.CENTRE)]
        
        elif isinstance(behavior.target_point_m, tuple):
            # Es una tupla (X, Y) estática dada por comando. 
            # Usamos la Z actual de la IA para mantener el cálculo 3D intacto sin alterar la altura.
            behavior.target_point_use = Coordinates(
                lfs_pos_to_meters(behavior.target_point_m[0], rev=True),
                lfs_pos_to_meters(behavior.target_point_m[1], rev=True), 
                ai.player.telemetry.coordinates.z
            )
        
        # Volante
        lfs_steer = self._calculate_steering(behavior=behavior, telemetry=ai.player.telemetry)

        return [AIV(Input=CS.STEER, Value=lfs_steer)]
    
    def _calculate_steering(self, behavior: AIBehavior, telemetry: Telemetry) -> int:
        """
        Calcula el giro del volante necesario.
        Retorna un int en escala InSim (0 a 65535).
        """
        if behavior.target_point_use is None:
            return CSVAL.STEER.CENTRE

        logic_rev = behavior.logic_reversed
        if behavior.speed_reverse:
            logic_rev = not logic_rev

        # 1. ¿Hacia dónde deberíamos mirar? (Geometría pura)
        target_h = calc_target_heading(
            telemetry.coordinates.x, telemetry.coordinates.y, 
            behavior.target_point_use.x, behavior.target_point_use.y, 
            rev=logic_rev
        )

        # 2. ¿Cuánto nos desviamos? (Error real geométrico)
        error = get_heading_diff(target_h, telemetry.heading.angle_lfs)

        # 3. PID (Busca reducir el error a 0)
        steer_val = behavior.pid_direction.update(target=0.0, current=error, dt=self.interval_mci_s)
        
        if behavior.gear_mode == GearMode.REVERSE:
            steer_val = -steer_val

        # 4. Convertimos al sistema InSim de 16 bits (0 a MAX)
        lfs_steer = int(CSVAL.STEER.CENTRE + (steer_val * CSVAL.STEER.CENTRE))
        lfs_steer = max(1, min(65535, lfs_steer))
        
        return lfs_steer
    
    def _handle_pedals_and_gears(self, ai: AI) -> list[AIV]:
        behavior: AIBehavior = ai.extra['aic']
        actions: list[AIV] = []
        
        # --- APAGADO COMPLETO ---
        # (Se mantiene exactamente igual...)
        if not behavior.target_speed_kmh:
            if ai.player.telemetry.speed.speed_kmh < 1:
                if behavior.active_ready:
                    behavior.gear_mode = GearMode.NEUTRAL
                    behavior.active_ready = False
                    behavior.reset_speed()
                    return [
                        AIV(Input=CS.THROTTLE, Value=CSVAL.MIN_MID_MAX.MIN),
                        AIV(Input=CS.HANDBRAKE, Value=CSVAL.MIN_MID_MAX.MAX),
                        AIV(Input=CS.BRAKE, Value=CSVAL.MIN_MID_MAX.MIN),
                        AIV(Input=CS.IGNITION, Value=CSVAL.TOGGLE.OFF),
                        AIV(Input=CS.GEAR, Value=CSVAL.GEAR.NEUTRAL)
                    ]
                else: return
            else: behavior.target_speed_kmh_use = 0.0
        
        # --- ENCENDIDO ---
        if not behavior.active_ready:
            actions.extend([
                AIV(Input=CS.IGNITION, Value=CSVAL.TOGGLE.ON),
                AIV(Input=CS.HANDBRAKE, Value=CSVAL.MIN_MID_MAX.MIN)
            ])
            behavior.active_ready = True
        
        # --- 1. RESOLVER VELOCIDAD CRUDA (Modos NO complejos) ---
        # Si la IA tiene RouteMode, este bloque no altera nada porque 
        # la ruta ya calculó y asignó behavior.target_speed_kmh_use.
        if isinstance(behavior.target_speed_kmh, float):
            behavior.target_speed_kmh_use = behavior.target_speed_kmh
            behavior.speed_reverse = (behavior.target_speed_kmh < 0)
            
        elif isinstance(behavior.target_speed_kmh, AdaptiveSpeedConfig):
            behavior.speed_reverse = False
            config = behavior.target_speed_kmh
            
            if behavior.target_point_use is not None:
                my_coords = ai.player.telemetry.coordinates
                target_coords = behavior.target_point_use
                dist_m = calc_dist_3d(
                    my_coords.x_m, my_coords.y_m, my_coords.z_m,
                    target_coords.x_m, target_coords.y_m, target_coords.z_m
                )
                
                speed_at_min = config.max_speed if behavior.logic_reversed else config.min_speed
                speed_at_max = config.min_speed if behavior.logic_reversed else config.max_speed
                
                if dist_m <= config.min_dist:
                    behavior.target_speed_kmh_use = speed_at_min
                elif dist_m >= config.max_dist:
                    behavior.target_speed_kmh_use = speed_at_max
                else:
                    ratio = (dist_m - config.min_dist) / (config.max_dist - config.min_dist)
                    behavior.target_speed_kmh_use = speed_at_min + ratio * (speed_at_max - speed_at_min)
            else:
                behavior.target_speed_kmh_use = 0.0

        # --- 2. [!] LEY UNIVERSAL DE CAOS (El filtro final) ---
        # Afecta SIEMPRE, a menos que un sistema superior pida ignorarlo.
        if behavior.target_speed_kmh_use is not None and not behavior.ignore_human:
            behavior.target_speed_kmh_use *= getattr(behavior, 'human_speed_factor', 1.0)
            
        # Reseteamos el flag de ignore para el siguiente tick, por si el modo quiere volver al caos
        behavior.ignore_human = False

        # =========================================================
        # [!] REGISTRO DEL ESTADO ATASCADO (Watchdog Pasivo)
        # =========================================================
        if behavior.target_speed_kmh_use != 0 and ai.player.telemetry.speed.speed_kmh < 1:
            if behavior.stuck_start_time == 0.0:
                behavior.stuck_start_time = time.time() 
        else:
            behavior.stuck_start_time = 0.0
        
        # --- GESTOR DE MARCHAS AUTOMÁTICAS ---
        if behavior.target_speed_kmh_use < 0 and behavior.gear_mode != GearMode.REVERSE:
            if ai.player.telemetry.speed.speed_kmh > 1:
                behavior.target_speed_kmh_use = 0.0 # Frenar antes de cambiar
            else:
                actions.append(AIV(Input=CS.GEAR, Value=CSVAL.GEAR.REVERSE))
                behavior.gear_mode = GearMode.REVERSE
        
        elif behavior.target_speed_kmh_use > 0 and behavior.gear_mode != GearMode.NORMAL:
            if ai.player.telemetry.speed.speed_kmh > 1:
                behavior.target_speed_kmh_use = 0.0 # Frenar antes de cambiar
            else:
                actions.extend([
                    AIV(Input=CS.GEAR, Time=10, Value=CSVAL.GEAR.FIRST),
                    AIV(Input=CS.SET_HELP_FLAGS, Value=CSVAL.AI_HELP.AUTOGEARS)
                ])
                behavior.gear_mode = GearMode.NORMAL
        
        # --- CÁLCULO DE PEDALES ---
        lfs_throttle, lfs_brake = self._calculate_pedals(behavior, ai.player.telemetry.speed.speed_kmh)
        
        actions.extend([
            AIV(Input=CS.THROTTLE, Value=lfs_throttle),
            AIV(Input=CS.BRAKE, Value=lfs_brake)
        ])
        
        return actions

    def _calculate_pedals(self, behavior: AIBehavior, current_speed_kmh: float) -> tuple[int, int]:
        """
        Calcula la presión de los pedales.
        Retorna una tupla (throttle, brake), ambos en escala InSim (0 a 65535).
        """
        if behavior.target_speed_kmh_use == 0.0:
            return CSVAL.MIN_MID_MAX.MIN, CSVAL.MIN_MID_MAX.MAX  # Freno a fondo si el objetivo es parar

        # 1. PID de Velocidad (El nuevo PID ya sabe que no debe exceder -1.0 a 1.0)
        target_mag = abs(behavior.target_speed_kmh_use)
        pid_out = behavior.pid_speed.update(target=target_mag, current=current_speed_kmh, dt=self.interval_mci_s)

        # 2. Repartir la salida del PID a los pedales físicos
        throttle = 0.0
        brake = 0.0

        if pid_out > 0:
            throttle = pid_out
        elif pid_out < 0:
            brake = -pid_out  # Invertimos el signo para el freno (ej: -0.8 -> 0.8)
        
        # 3. Convertimos al sistema InSim de 16 bits (0 a MAX)
        lfs_throttle = int(throttle * CSVAL.MIN_MID_MAX.MAX)
        lfs_brake = int(brake * CSVAL.MIN_MID_MAX.MAX)

        return lfs_throttle, lfs_brake
    
