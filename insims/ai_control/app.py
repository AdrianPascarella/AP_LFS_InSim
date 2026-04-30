from __future__ import annotations
import random
import logging
from typing import TYPE_CHECKING, Optional, Literal

from lfs_insim import InSimApp, mute_send_logs
from lfs_insim.insim_packet_class import ISP_MCI, ISP_RST, ISP_CRS, ISP_MSO, AIInputVal as AIV, CS, SND
from lfs_insim.utils import PIDController, separate_command_args, TextColors

mute_send_logs('ISP_AIC')

from insims.ai_control.behavior import AIBehavior, GearMode
from insims.ai_control.nav_modes.route.mode import RouteMode
from insims.ai_control.nav_modes.route.manager import RouteManager
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from insims.ai_control.nav_modes.freeroam.map_recorder import MapRecorder

from insims.ai_control.commands import _CommandsMixin
from insims.ai_control.physics import _PhysicsMixin
from insims.ai_control.navigation import _NavigationMixin
from insims.ai_control.traffic import _TrafficMixin
from insims.ai_control.map_ui import _MapUIMixin

if TYPE_CHECKING:
    from insims.users_management.main import UsersManagement, AI, Telemetry, Coordinates


class AIControl(_MapUIMixin, _CommandsMixin, _PhysicsMixin, _NavigationMixin, _TrafficMixin, InSimApp):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cmd_base = 'aic'
        self.cmd_prefix = '.'
        self.user_manager: Optional['UsersManagement'] = None
        self.route_manager: Optional['RouteManager'] = None
        self.map_recorder = MapRecorder(self._get_coords_for_map, self.cmd_prefix)
        self._init_ui_state()

        self.interval_mci_s: float = self.config.get('interval', 100) / 1000

        # Cachés de localización para jugadores humanos en los radares de tráfico.
        # Claves: PLID. Valores: (timestamp, road_id, [node_index]).
        # Se limpian automáticamente por TTL en cada ciclo de radar.
        self._radar_human_cache: dict = {}
        self._target_lane_human_cache: dict = {}

        self.logger.info(f"Módulo {self.name} inicializado con arquitectura de objetos.")

    def on_connect(self):
        self.user_manager = self.get_insim("users_management")
        self.route_manager = RouteManager()
        self._init_commands()

    def on_ISP_MSO(self, packet: ISP_MSO):
        """Filtra y redirige comandos de chat a los managers correspondientes."""
        cmd, args = separate_command_args(self.cmd_prefix, packet)
        if not cmd: return

        if self.user_manager.user_autorized_cmd(self.user_manager.cmds_white_list, self.cmd_base, cmd, packet.UCID):
            self.cmds_aic.handle_commands(packet, args)
        elif self.user_manager.user_autorized_cmd(self.user_manager.cmds_white_list, 'route', cmd, packet.UCID):
            self.cmds_route.handle_commands(packet, args)
        elif self.user_manager.user_autorized_cmd(self.user_manager.cmds_white_list, 'map', cmd, packet.UCID):
            self.map_recorder._current_cmd_ucid = packet.UCID
            self.map_recorder.cmd_manager.handle_commands(packet, args)

    def _generate_random_pid(self, pid_type: Literal['speed', 'direction']) -> PIDController:
        """Genera PIDs escalados a las unidades de LFS."""
        if pid_type == 'speed':
            kp = round(random.uniform(0.04, 0.08), 3)
            ki = round(random.uniform(0.001, 0.005), 4)
            kd = round(random.uniform(0.01, 0.03), 3)
            return PIDController(kp=kp, ki=ki, kd=kd, out_min=-1.0, out_max=1.0)
        elif pid_type == 'direction':
            kp = 0.00018
            ki = 0.0000015
            kd = 0.00004
            return PIDController(kp=kp, ki=ki, kd=kd, out_min=-1.0, out_max=1.0)

    def _get_behavior(self, user_ucid, plid: int) -> Optional[AIBehavior]:
        """Extrae el AIBehavior. Si no existe, lo crea con PIDs y personalidades únicos."""
        ai = self.user_manager.ais.get(plid)
        if not ai:
            self.send_ISP_MSL(Msg=f'El PLID "{plid}" no está asociado a ninguna AI', Sound=SND.SYSMESSAGE)
            return None
        if ai.player.ucid != user_ucid:
            self.send_ISP_MSL(Msg=f'La AI "{ai.ai_name}" no es una de tus AI\'s', Sound=SND.SYSMESSAGE)
            return None

        if 'aic' not in ai.extra:
            behavior = AIBehavior(
                pid_speed=self._generate_random_pid('speed'),
                pid_direction=self._generate_random_pid('direction')
            )
            behavior.human_speed_factor = random.uniform(0.92, 1.05)
            behavior.human_safe_gap = random.uniform(1.2, 2.5)
            behavior.human_warn_gap = behavior.human_safe_gap + 1.5
            behavior.human_wander_amp = random.uniform(0.3, 1.2)
            behavior.human_wander_freq = random.uniform(0.5, 2.0)
            behavior.human_wander_offset = random.uniform(0, 100)
            behavior.human_curve_factor = random.uniform(0.6, 1.4)
            ai.extra['aic'] = behavior
            self.logger.info(f"Asignados PIDs y Personalidad única a la IA {plid}")

        return ai.extra['aic']

    def _get_coords_for_map(self, ucid: int):
        if not self.user_manager: return None
        user = self.user_manager.users.get(ucid)
        if user and user.plid:
            player = self.user_manager.players.get(user.plid)
            if player and player.telemetry:
                return player.telemetry.coordinates
        return None

    def on_ISP_RST(self, packet: ISP_RST):
        """Se ejecuta cuando se reinicia la carrera."""
        self.logger.info("Carrera reiniciada. Reseteando el contacto de todas las IAs...")
        for ai in self.user_manager.ais.values():
            if 'aic' in ai.extra:
                behavior: AIBehavior = ai.extra['aic']
                behavior.active_ready = False
                behavior.gear_mode = GearMode.NEUTRAL
                if isinstance(behavior.active_mode, RouteMode):
                    behavior.active_mode.route_wp_index = 0
                    behavior.active_mode.route_started = False

    def on_ISP_CRS(self, packet: ISP_CRS):
        """Se ejecuta cuando un coche individual se reinicia."""
        plid = packet.PLID
        ai = self.user_manager.ais.get(plid)
        if ai and 'aic' in ai.extra:
            self.logger.info(f"La IA {ai.ai_name} se ha reiniciado. Reseteando su contacto...")
            behavior: AIBehavior = ai.extra['aic']
            behavior.active_ready = False
            behavior.gear_mode = GearMode.NEUTRAL
            if isinstance(behavior.active_mode, RouteMode):
                behavior.active_mode.route_wp_index = 0
                behavior.active_mode.route_started = False

    def on_ISP_MCI(self, packet: ISP_MCI):
        """Bucle principal de telemetría."""
        if not self.route_manager or not self.user_manager:
            return

        for car_info in packet.Info:
            plid = car_info.PLID

            player = self.user_manager.players.get(plid)
            ai = self.user_manager.ais.get(plid)

            telemetry = None
            if player:
                telemetry = player.telemetry
            elif ai:
                telemetry = ai.player.telemetry

            if not telemetry:
                continue

            rec_ucid = self.map_recorder.recording_ucid
            if player and (rec_ucid is None or player.ucid == rec_ucid):
                self.map_recorder.update_recording(
                    telemetry.coordinates,
                    telemetry.speed.speed_kmh
                )

            if plid in self.route_manager.recorders:
                self.route_manager.process(plid, telemetry.coordinates, telemetry.speed)

            if ai and 'aic' in ai.extra:
                behavior: AIBehavior = ai.extra['aic']

                if isinstance(behavior.active_mode, RouteMode):
                    self._update_route_navigation(ai)
                elif isinstance(behavior.active_mode, FreeroamMode):
                    self._update_freeroam_navigation(ai)

                inputs_to_send: list[AIV] = []
                inputs_to_send.extend(self._handle_steering(ai))
                inputs_pedals = self._handle_pedals_and_gears(ai)
                if inputs_pedals:
                    inputs_to_send.extend(inputs_pedals)
                if behavior.active_mode and behavior.active_mode.extra_inputs_to_send:
                    inputs_to_send.extend(behavior.active_mode.extra_inputs_to_send)

                if inputs_to_send:
                    self.send_ISP_AIC(PLID=ai.player.plid, Inputs=inputs_to_send)
