from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from insims.ai_control.behavior import AIBehavior
    from insims.ai_control.nav_modes.freeroam.graph import LateralLink
    from insims.ai_control.nav_modes.freeroam.map_recorder import MapRecorder
    from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
    from insims.ai_control.nav_modes.route.manager import RouteManager
    from insims.users_management.main import AI, UsersManagement


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
        AIControl(_MapUIMixin, _CommandsMixin, _PhysicsMixin, _NavigationMixin,
                  _TrafficMixin, InSimApp)
        Cada mixin hereda de _MixinBase.

        `_TrafficMixin` es a su vez una fachada: compone los submixins del paquete
        `traffic/` (radar, cruise_control, zones, overtake, paths, orchestrator).

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
    cmd_prefix: str  # Prefijo de comandos (ej. '.')
    cmd_base: str  # Nombre base del grupo de comandos (ej. 'aic')
    interval_mci_s: float  # Intervalo del paquete MCI en segundos (para dt del PID)
    logger: logging.Logger  # Logger del módulo (provisto por InSimApp)

    if TYPE_CHECKING:
        # ─── Módulos externos ──────────────────────────────────────────────────
        user_manager: Optional["UsersManagement"]  # Gestión de jugadores/IAs
        route_manager: Optional["RouteManager"]  # Gestión de rutas grabadas
        map_recorder: "MapRecorder"  # Grafo de navegación Freeroam

        # ─── Grupos de comandos (inicializados en _init_commands) ─────────────
        cmds_aic: Any  # CMDManager del grupo 'aic'
        cmds_route: Any  # CMDManager del grupo 'route'

        # ─── Envío de paquetes (heredado de InSimApp → PacketSenderMixin) ──────
        def send(self, packet: Any) -> None: ...
        def send_ISP_MSL(self, **kwargs: Any) -> None: ...
        def send_ISP_MST(self, **kwargs: Any) -> None: ...
        def send_ISP_AIC(self, **kwargs: Any) -> None: ...
        def send_ISP_BTN(self, **kwargs: Any) -> None: ...
        def send_ISP_BFN(self, **kwargs: Any) -> None: ...
        def get_insim(self, name: str) -> Any: ...

        # ─── Métodos cross-mixin ───────────────────────────────────────────────
        # Solo se declaran aquí los métodos que un mixin llama sobre `self` pero
        # que están implementados en OTRO mixin (el acoplamiento real entre
        # módulos). Los métodos que solo se usan dentro de su propio mixin NO van
        # aquí: su clase ya los ve directamente. Entre paréntesis, quién los llama.

        # app.py  (← commands.py)
        def _get_behavior(
            self, user_ucid: int, plid: int
        ) -> Optional["AIBehavior"]: ...

        # commands.py  (← navigation.py, map_ui.py, app.py)
        def _cmd_spec(self, plid: int) -> None: ...
        def _stop_traffic_loops(self) -> None: ...

        # navigation.py  (← app.py, overtake.py, radar.py)
        def _update_route_navigation(self, ai: "AI") -> None: ...
        def _update_freeroam_navigation(self, ai: "AI") -> None: ...
        def _get_closest_node_index(
            self, px: float, py: float, nodes: list
        ) -> tuple[int, float]: ...
        def _get_indicator_to_use(
            self, my_road_nodes: list, other_road_nodes: list, node_index: int
        ) -> Any: ...

        # physics.py  (← app.py)
        def _handle_steering(self, ai: "AI") -> list: ...
        def _handle_pedals_and_gears(self, ai: "AI") -> list: ...

        # traffic/orchestrator.py  (← navigation.py)
        def _update_traffic_behavior(self, ai: "AI") -> None: ...

        # traffic/radar.py  (← orchestrator.py, overtake.py, app.py)
        def _build_vehicle_grid(self) -> None: ...
        def _scan_lane_ahead(
            self, ai: "AI", mode: "FreeroamMode", max_dist_m: float
        ) -> list: ...
        def _scan_target_lane(
            self, ai: "AI", mode: "FreeroamMode", target_road_id: str, max_dist_m: float
        ) -> list: ...

        # traffic/cruise_control.py  (← orchestrator.py)
        def _apply_adaptive_cruise_control(
            self,
            base_speed_kmh: float,
            closest_speed_kmh: float,
            closest_dist_m: float,
            min_dist_m: float,
            max_dist_m: float,
        ) -> float: ...

        # traffic/overtake.py  (← orchestrator.py)
        def _find_valid_overtake_lane(
            self,
            current_road_id: str,
            current_road_traffic_rule: Any,
            current_road_nodes: list,
            node_index: int,
        ) -> Optional[tuple]: ...
        def _is_lane_safe_to_overtake(
            self,
            ai: "AI",
            mode: "FreeroamMode",
            target_road_id: str,
            overtake_lat_link: "LateralLink",
            is_opposing: bool,
            req_dist_m: float,
            time_to_overtake_s: float,
        ) -> bool: ...

        # traffic/zones.py  (← orchestrator.py)
        def _dist_to_yield_line_m(self, px: float, py: float, line: list) -> float: ...
        def _yield_threat_detected(self, ai: "AI", link: Any) -> bool: ...

        # traffic/paths.py  (← overtake.py)
        def _calc_path_length(self, nodes: list, start_idx: int = 0) -> float: ...
