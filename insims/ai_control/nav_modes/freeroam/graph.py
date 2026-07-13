from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional

from insims.ai_control.nav_modes.freeroam.enums import TrafficRule
from insims.users_management.main import Coordinates
from lfs_insim.insim_enums import CSVAL

# ==========================================
# 1. EL GRAFO DE NAVEGACIÓN (Enlaces)
# ==========================================


@dataclass
class RoadLink:
    """Conexión topológica entre dos vías."""

    from_road_id: str
    to_road_id: str
    nodes: List[Coordinates] = field(default_factory=list)

    from_suffix: str = ""
    to_suffix: str = ""

    by_road_id: Optional[str] = None

    indicators: CSVAL.INDICATORS = CSVAL.INDICATORS.OFF
    time: float = 5.0

    speed_limit_kmh: float = 30.0

    # Cesión de paso (Fase 8, S38). `yield_line` vacía ⇒ este giro NO cede
    # (los mapas viejos cargan así). Si tiene puntos: al tomar el enlace hay
    # que parar ANTES de la línea si hay tráfico vigilado a menos de
    # `yield_time_s` segundos del punto de conflicto; cruzada la línea, la
    # maniobra está comprometida y no se frena dentro del cruce.
    yield_line: List[Coordinates] = field(default_factory=list)
    yield_time_s: Optional[float] = None  # None ⇒ default global de config
    yield_zone_id: Optional[str] = None  # zona (punto de conflicto) extra a vigilar

    @property
    def has_yield(self) -> bool:
        return bool(self.yield_line)

    @property
    def min_speed_kmh(self) -> float:
        return self.speed_limit_kmh / 2.0

    @property
    def link_id(self) -> str:
        return (
            f"{self.from_road_id}{self.from_suffix}->{self.to_road_id}{self.to_suffix}"
        )


@dataclass
class LateralLink:
    """Conexión topológica entre dos carriles."""

    road_a: str
    road_b: str
    nodes: List[Coordinates] = field(default_factory=list)

    suffix_a: str = ""
    suffix_b: str = ""

    allow_a_to_b: bool = True
    allow_b_to_a: bool = True

    opposing: bool = False
    is_circular: bool = False
    made_to_overtake: bool = False

    @property
    def link_id(self) -> str:
        return f"{self.road_a}{self.suffix_a}<<>>{self.road_b}{self.suffix_b}"


# ==========================================
# 2. EL RADAR DE TRÁFICO (Intersecciones)
# ==========================================


@dataclass
class IntersectionZone:
    """
    Punto de conflicto de un cruce múltiple (Fase 8, S38): los RoadLink con
    cesión que lo referencian (`yield_zone_id`) vigilan además el tráfico a
    menos de `yield_time_s` segundos de este punto. La zona NO decide quién
    cede (eso lo hace la `yield_line` de cada link); solo amplía qué se vigila.
    """

    zone_id: str
    nodes: List[Coordinates] = field(default_factory=list)

    yield_time_s: Optional[float] = None  # None ⇒ default global de config

    # ─── Modelo VIEJO (área + pares de prioridad) ───────────────────────────
    # En retirada (Fase 8): la conducta que los consume se sustituye en el
    # bloque 8.3 y el JSON se migra en el 8.6.
    radius_m: float = 10.0

    # [[viaPrioritaria_id, viaNoPrioritaria_id], ...]
    priority_rules: List[List[str, str]] = field(default_factory=list)


# ==========================================
# 3. LA VÍA BASE (Tramos de Carril)
# ==========================================


@dataclass
class RoadSegment:
    road_id: str
    nodes: List[Coordinates] = field(default_factory=list)
    is_circular: bool = False
    is_closed: bool = False

    speed_limit_kmh: float = 30.0

    @property
    def min_speed_kmh(self) -> float:
        return self.speed_limit_kmh / 2.0

    traffic_rule: Optional[TrafficRule] = None


# ==========================================
# 4. REGLAS ESPECIALES (Tramos con comportamiento restringido)
# ==========================================


@dataclass
class SpecialRule:
    """
    Tramo con una o varias reglas especiales activas entre dos nodos.
    nodes[0] = nodo de inicio (activa la regla al pasar cerca)
    nodes[1] = nodo de fin   (desactiva la regla al pasar cerca)

    Reglas soportadas en el dict `rules`:
      "speed_limit"    : float  → override del límite de velocidad (km/h)
      "no_lane_change" : bool   → bloquea cambios de carril y adelantamientos
    """

    rule_id: str
    nodes: List[Coordinates] = field(default_factory=list)
    radius_m: float = 8.0
    rules: dict = field(default_factory=dict)


@dataclass
class LocationContext:
    """Almacena el contexto espacial de unas coordenadas dadas."""

    # Datos de la Vía
    road_id: Optional[str] = None
    road_node_idx: int = -1
    road_dist: float = float("inf")

    # Datos de Enlaces
    link_id: Optional[str] = None
    link_type: Optional[Literal["LatLink", "RoadLink"]] = None
    link_dist: float = float("inf")

    # Datos de Zona
    zone_id: Optional[str] = None
    zone_dist: float = float("inf")
    zone_radius: float = 0.0
