import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
from enum import IntEnum

# Importaciones de negocio (Fuera de TYPE_CHECKING para que existan en tiempo de ejecución)
from insims.users_management.main import Coordinates
from lfs_insim.utils import PIDController

if TYPE_CHECKING:
    from insims.ai_control.nav_modes import AINavModeState

@dataclass
class AdaptiveSpeedConfig:
    """Configuración para la velocidad dinámica."""
    min_speed: float
    max_speed: float
    min_dist: float
    max_dist: float

class GearMode(IntEnum):
    NEUTRAL = 0
    REVERSE = 1
    NORMAL = 2

@dataclass
class AIBehavior:
    """Almacena el estado lógico y controladores de una IA específica."""
    
    # Controladores
    pid_speed: PIDController | None = None
    pid_direction: PIDController | None = None
    
    # Intenciones Finales de Acción (Velocidad y Dirección)
    target_speed_kmh_use: float | None = None
    target_speed_kmh: AdaptiveSpeedConfig | float | None = None
    
    target_point_use: Coordinates | None = None
    target_point_m: Coordinates | int | None = None
    
    # Flags de Sincronización
    logic_reversed: bool = False
    speed_reverse: bool = False
    
    # Tracking de Estados de Marcha
    active_ready: bool = False
    gear_mode: GearMode = GearMode.NEUTRAL
    # En tu dataclass o clase AIBehavior:
    stuck_start_time: float = 0.0  # Guarda el momento exacto (time.time()) en el que se atascó
    
    # =========================================================
    # [!] NUEVO: Estado de Navegación Activa (State Pattern)
    # Puede ser None (parado), RouteMode, o FreeroamMode.
    # =========================================================
    active_mode: Optional[AINavModeState] = None
    
    # =========================================================
    # Personalidad Humana (Imperfecciones y Estilo)
    # =========================================================
    ignore_human: bool = False          # Si es True, se ignoran las imperfecciones humanas y se sigue la lógica perfecta.
    human_speed_factor: float = 1.0       # Multiplicador de la velocidad asignada
    human_safe_gap: float = 2.0           # Radar: Segundos de frenada de emergencia
    human_warn_gap: float = 3.5           # Radar: Segundos de precaución
    human_wander_amp: float = 0.0         # Volante: Grados máximos de despiste lateral
    human_wander_freq: float = 1.0        # Volante: Velocidad del despiste
    human_wander_offset: float = 0.0      # Volante: Desfase para desincronizar IAs
    human_curve_factor: float = 1.0

    def reset_mode(self):
        """Apaga la navegación borrando el modo activo."""
        self.active_mode = None

    def reset_direction(self):
        """Limpia los objetivos de dirección (volante) actuales."""
        self.target_point_m = None
        self.target_point_use = None
        self.logic_reversed = False
        # Eliminamos self.reset_mode() para que la IA no pierda su modo si pierde el target
        
    def reset_speed(self):
        """Limpia los objetivos de velocidad (pedales) actuales."""
        self.target_speed_kmh = None
        self.target_speed_kmh_use = None
        self.speed_reverse = False
        # Eliminamos self.reset_mode() para que la IA no se apague al detenerse a 0 km/h