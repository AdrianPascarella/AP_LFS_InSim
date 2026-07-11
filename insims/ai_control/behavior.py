from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

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
    """Almacena el estado lógico y controladores de una IA específica.

    OBJETIVOS: PETICIÓN vs VALOR RESUELTO
    -------------------------------------
    Cada objetivo (velocidad y dirección) vive en DOS campos:

    - `*_request`  — lo que se PIDE. Puede ser heterogéneo: una velocidad fija o
      una `AdaptiveSpeedConfig`; un punto, una tupla en metros o un PLID a seguir.
      Lo escriben los comandos y la navegación (route / freeroam / tráfico).
    - `*_resolved` — el valor CONCRETO que se está usando en este tick, ya listo
      para el PID. Lo calcula `physics.py` a partir de la petición, y se
      recalcula en cada MCI (no se conserva entre ticks).
    """

    # Controladores
    pid_speed: PIDController | None = None
    pid_direction: PIDController | None = None

    # Objetivo de velocidad (pedales). Un float en km/h; negativo = marcha atrás.
    speed_request: AdaptiveSpeedConfig | float | None = None
    speed_resolved_kmh: float | None = None

    # Objetivo de dirección (volante). La petición admite Coordinates, una tupla
    # (x_m, y_m) en metros o un PLID (int) al que seguir.
    point_request: Coordinates | tuple[float, float] | int | None = None
    point_resolved: Coordinates | None = None

    # Flags de Sincronización
    logic_reversed: bool = False
    speed_reverse: bool = False

    # Tracking de Estados de Marcha
    active_ready: bool = False
    gear_mode: GearMode = GearMode.NEUTRAL
    stuck_start_time: float = (
        0.0  # Guarda el momento exacto (time.time()) en el que se atascó
    )

    # Estado de Navegación Activa (State Pattern).
    # Puede ser None (parado), RouteMode, o FreeroamMode.
    active_mode: Optional[AINavModeState] = None

    # =========================================================
    # Personalidad Humana (Imperfecciones y Estilo)
    # =========================================================
    ignore_human: bool = False  # Si es True, se ignoran las imperfecciones humanas y se sigue la lógica perfecta.
    human_speed_factor: float = 1.0  # Multiplicador de la velocidad asignada
    human_safe_gap: float = 2.0  # Radar: Segundos de frenada de emergencia
    human_warn_gap: float = 3.5  # Radar: Segundos de precaución

    def reset_mode(self):
        """Apaga la navegación borrando el modo activo."""
        self.active_mode = None

    def reset_direction(self):
        """Limpia los objetivos de dirección (volante) actuales."""
        self.point_request = None
        self.point_resolved = None
        self.logic_reversed = False
        # Eliminamos self.reset_mode() para que la IA no pierda su modo si pierde el target

    def reset_speed(self):
        """Limpia los objetivos de velocidad (pedales) actuales."""
        self.speed_request = None
        self.speed_resolved_kmh = None
        self.speed_reverse = False
        # Eliminamos self.reset_mode() para que la IA no se apague al detenerse a 0 km/h
