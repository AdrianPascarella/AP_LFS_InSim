from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    from insims.users_management.main import UsersManagement
    from insims.ai_control.nav_modes.route.manager import RouteManager
    from insims.ai_control.nav_modes.freeroam.map_recorder import MapRecorder
    from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
    from insims.ai_control.nav_modes.freeroam.graph import RoadLink, LateralLink
    from insims.ai_control.behavior import AIBehavior
    from insims.users_management.main import AI, Coordinates
    from lfs_insim.utils import PIDController


class _MixinBase:
    """
    Clase base compartida de todos los mixins de AIControl.

    PROPÓSITO
    ---------
    Actúa como contrato explícito: documenta qué atributos y métodos tiene
    disponibles `self` dentro de cualquier mixin. Sin esta clase, un desarrollador
    que abra commands.py vería `self.user_manager` o `self.send_ISP_MSL` sin saber
    de dónde vienen.

    ARQUITECTURA (ver app.py para la composición final)
    ---------------------------------------------------
        AIControl(_CommandsMixin, _PhysicsMixin, _NavigationMixin, _TrafficMixin, InSimApp)
        Cada mixin hereda de _MixinBase.

    CÓMO AÑADIR UN NUEVO MIXIN
    --------------------------
    1. Crea el archivo (ej. my_feature.py):

           from insims.ai_control.base import _MixinBase

           class _MyFeatureMixin(_MixinBase):
               def mi_metodo(self):
                   self.user_manager.ais  # IDE lo autocompletará
                   self.send_ISP_MSL(Msg="Hola")

    2. Si el mixin necesita atributos de instancia propios, añádelos aquí
       con sus anotaciones para que los otros mixins también los vean.

    3. Agrega la clase a la herencia de AIControl en app.py.

    VALORES REALES
    --------------
    Los atributos anotados aquí NO tienen valor en tiempo de ejecución dentro
    de esta clase — son solo hints. Los valores reales los asignan:
    - AIControl.__init__()  →  cmd_prefix, cmd_base, interval_mci_s, map_recorder
    - AIControl.on_connect() →  user_manager, route_manager
    - InSimApp.__init__()   →  logger, config
    - PacketSenderMixin     →  send(), send_ISP_*()
    """

    # ─── Configuración ─────────────────────────────────────────────────────────
    cmd_prefix: str          # Prefijo de comandos (ej. '.')
    cmd_base: str            # Nombre base del grupo de comandos (ej. 'aic')
    interval_mci_s: float    # Intervalo del paquete MCI en segundos (para dt del PID)
    logger: logging.Logger   # Logger del módulo (provisto por InSimApp)

    if TYPE_CHECKING:
        # ─── Módulos externos ──────────────────────────────────────────────────
        user_manager: Optional['UsersManagement']   # Gestión de jugadores/IAs
        route_manager: Optional['RouteManager']     # Gestión de rutas grabadas
        map_recorder: 'MapRecorder'                 # Grafo de navegación Freeroam

        # ─── Grupos de comandos (inicializados en _init_commands) ─────────────
        cmds_aic: Any     # CMDManager del grupo 'aic'
        cmds_route: Any   # CMDManager del grupo 'route'

        # ─── Envío de paquetes (heredado de InSimApp → PacketSenderMixin) ──────
        def send(self, packet: Any) -> None: ...
        def send_ISP_MSL(self, **kwargs: Any) -> None: ...
        def send_ISP_MST(self, **kwargs: Any) -> None: ...
        def send_ISP_AIC(self, **kwargs: Any) -> None: ...
        def get_insim(self, name: str) -> Any: ...

        # ─── Métodos cross-mixin ───────────────────────────────────────────────
        # Cada método está implementado en su mixin correspondiente,
        # pero todos los mixins los pueden llamar a través de self.

        # app.py
        def _get_behavior(self, user_ucid: int, plid: int) -> Optional['AIBehavior']: ...
        def _generate_random_pid(self, pid_type: str) -> 'PIDController': ...
        def _get_coords_for_map(self, ucid: int) -> Optional['Coordinates']: ...

        # commands.py
        def _cmd_add(self) -> None: ...
        def _cmd_spec(self, plid: int) -> None: ...
        def _cmd_map_freeroam(self, packet: Any, plid_ai: int) -> None: ...
        def _cmd_route_follow(self, packet: Any, route_name: str, plid: int) -> None: ...

        # navigation.py
        def _update_route_navigation(self, ai: 'AI') -> None: ...
        def _update_freeroam_navigation(self, ai: 'AI') -> None: ...
        def _get_radar_speed_limit(self, ai: 'AI', base_speed: float, gap_filling_mode: bool = True) -> float: ...
        def _get_closest_node_index(self, px: float, py: float, nodes: list) -> tuple[int, float]: ...
        def _get_indicator_to_use(self, my_road_nodes: list, other_road_nodes: list, node_index: int) -> Any: ...
        def _is_link_reachable_ahead(self, current_road_nodes: list, current_index: int, link_nodes: list, max_dist: float) -> bool: ...
        def _get_raw_candidates(self, current_road_id: str) -> list: ...
        def _calculate_next_link(self, current_road_id: str, previous_road_id: Optional[str], current_index: int) -> tuple: ...
        def _plan_next_link(self, mode: 'FreeroamMode', on_link: Optional[tuple] = None) -> None: ...

        # physics.py
        def _handle_steering(self, ai: 'AI') -> list: ...
        def _handle_pedals_and_gears(self, ai: 'AI') -> list: ...

        # traffic.py
        def _update_traffic_behavior(self, ai: 'AI') -> None: ...
        def _scan_lane_ahead(self, ai: 'AI', mode: 'FreeroamMode', max_dist_m: float) -> list: ...
        def _apply_adaptive_cruise_control(self, base_speed_kmh: float, closest_speed_kmh: float, closest_dist_m: float, min_dist_m: float, max_dist_m: float) -> float: ...
        def _find_valid_overtake_lane(self, current_road_id: str, current_road_traffic_rule: Any, current_road_nodes: list, node_index: int) -> Optional[tuple]: ...
        def _get_zone_centroid(self, zone: Any) -> tuple[float, float]: ...
        def _is_point_in_zone(self, px: float, py: float, zone: Any) -> bool: ...
        def _get_dist_to_zone_edge(self, px: float, py: float, zone: Any) -> float: ...
        def _is_priority_vehicle_active_at_zone(self, vehicle_coords: Any, vehicle_speed_kmh: float, vehicle_heading_lfs: int, zone: Any, approach_time_s: float) -> bool: ...
        def _get_available_overtake_distance(self, mode: 'FreeroamMode', my_coords: 'Coordinates', overtake_lat_link: 'LateralLink') -> float: ...
        def _calc_path_length(self, nodes: list, start_idx: int = 0) -> float: ...
        def _scan_target_lane(self, ai: 'AI', mode: 'FreeroamMode', target_road_id: str, max_dist_m: float) -> list: ...
        def _is_lane_safe_to_overtake(self, ai: 'AI', mode: 'FreeroamMode', target_road_id: str, overtake_lat_link: 'LateralLink', is_opposing: bool, req_dist_m: float, time_to_overtake_s: float) -> bool: ...
