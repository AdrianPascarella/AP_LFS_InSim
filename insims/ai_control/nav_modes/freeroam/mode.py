from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional, List, Literal

from lfs_insim.insim_packet_class import CSVAL
from insims.ai_control.nav_modes import AINavModeState
from insims.ai_control.nav_modes.freeroam.enums import AIManeuverState


@dataclass
class FreeroamMode(AINavModeState):
    """Estado exclusivo del modo Freeroam / Explorador."""

    # Variables de control interno
    freeroam_road_started: bool = False
    speed_limit_bias: float = 0.5

    # 1. Localización Topológica (¿Dónde estoy?)
    current_id: Optional[str] = None
    current_type: Optional[Literal['Road', 'RoadLink', 'LatLink']] = None
    node_index: int = 0

    # 2. Planificación de enlaces y Micronavegación
    next_link_id: Optional[str] = None
    next_link_type: Optional[Literal['RoadLink', 'LatLink']] = None
    current_road_id: Optional[str] = None
    previous_road_id: Optional[str] = None

    # 3. Macronavegación (El GPS / Pathfinding)
    destination_road_id: Optional[str] = None
    path_queue: List[str] = field(default_factory=list)

    # 4. Estado Táctico (Decisiones del entorno)
    is_changing_lane: bool = False
    is_driving_opposing: bool = False
    future_indicator: Optional[CSVAL.INDICATORS] = None
    blinkers_active: CSVAL.INDICATORS = CSVAL.INDICATORS.OFF
    blinkers_active_now: CSVAL.INDICATORS = CSVAL.INDICATORS.OFF

    # 5. Estados de Maniobra y Adelantamiento
    maneuver_state: AIManeuverState = AIManeuverState.NORMAL

    overtake_target_plids: set[int] = field(default_factory=set)

    # Extra
    extra_inputs_to_send: List = field(default_factory=list)

    # 6. Estado de Ceda el Paso
    yield_zone_id: Optional[str] = None
    yield_active: bool = False

    # 7. Reglas Especiales activas
    active_special_rules: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Radar de tráfico — por instancia para que cada AI tenga su propio intervalo
        self._last_radar_time: float = 0.0
        self._cached_target_speed: float = 0.0
        self._radar_interval: float = 0.1 + random.uniform(0.0, 0.05)

        # Intermitentes
        self._blinker_on_time: Optional[float] = None
        self._blinker_min_duration: float = 3.0

        # FSM de adelantamiento — inicialización garantizada en construcción
        self.overtake_state: str = 'IDLE'
        self.overtake_cooldown: float = 0.0
        self.overtake_target_plid: Optional[int] = None
        self.overtake_fast_lane_id: Optional[str] = None
        self.overtake_return_lane_id: Optional[str] = None
        self.last_link: Optional[tuple] = None
        self._passing_start_time: float = 0.0
        self._fast_lane_entry_time: float = 0.0
        self._returning_start_time: float = 0.0
        self._entered_fast_lane: bool = False
        self.blocking_plid: Optional[int] = None
