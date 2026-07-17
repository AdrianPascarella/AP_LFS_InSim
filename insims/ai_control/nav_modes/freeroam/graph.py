from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

from insims.ai_control.nav_modes.freeroam.enums import TrafficRule, YieldType
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

    # Cesión de paso del que HACE LA MANIOBRA (Fase 8, rediseño S44).
    #
    # `yield_type` NONE ⇒ este giro no cede (los mapas viejos cargan así).
    # YIELD/STOP ⇒ al tomar el enlace hay que parar ANTES de `yield_point` si
    # hay tráfico a menos de `yield_time_s` segundos de alguno de los puntos de
    # conflicto — que se detectan por geometría: TODAS las roads que el trazado
    # del link pisa, no solo la `to_road`. La línea de detención NO se graba:
    # se deriva perpendicular a la tangente del link en `yield_point`, con el
    # ancho de config. Pasado el punto la maniobra está comprometida y no se
    # frena dentro del cruce.
    #
    # Este mecanismo es AUTOCONTENIDO: no referencia zonas jamás (la zona
    # gobierna a los que cruzan de recto, y son cosas distintas).
    yield_type: YieldType = YieldType.NONE
    yield_point: Optional[Coordinates] = None
    yield_time_s: Optional[float] = None  # None ⇒ default global de config

    @property
    def has_yield(self) -> bool:
        """¿Este giro cede? Exige tipo Y punto: un toggle sin punto marcado está
        a medias (no hay línea que derivar), así que no cede."""
        return self.yield_type is not YieldType.NONE and self.yield_point is not None

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
    Cruce donde varias vías se cortan SIN que medie ningún enlace (Fase 8,
    rediseño S44): el caso que el link no puede resolver — cada coche va de
    RECTO por su road y, si nadie cede, chocan en mitad del cruce.

    Es el mecanismo ortogonal al del `RoadLink`: no se refieren el uno al otro.
    El link gobierna al que maniobra; la zona, al que cruza de recto.

    - `nodes` es un **polígono** (mínimo 3 puntos, sin máximo): su contorno ES
      el borde donde se para. No hay radio: el único umbral es el TIEMPO.
    - `roads` se auto-puebla con las roads que pisan el polígono (con tolerancia
      en Z, para que un puente no cuente) y es borrable a mano.
    """

    zone_id: str
    nodes: List[Coordinates] = field(default_factory=list)

    yield_time_s: Optional[float] = None  # None ⇒ default global de config

    # {road_id: cómo se comporta esa road en ESTA zona}. Las NONE no ceden nunca.
    roads: Dict[str, YieldType] = field(default_factory=dict)

    @property
    def has_polygon(self) -> bool:
        """¿La zona tiene un polígono utilizable? Con menos de 3 puntos no hay
        contorno que cerrar: la zona está a medias y no gobierna nada."""
        return len(self.nodes) >= 3


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
    zone_dist: float = float("inf")  # 0.0 si se está dentro del polígono
    # ¿Dentro del polígono de la zona? (S44: no hay radio — el contorno ES el
    # borde). Solo puede ser True con un polígono de verdad: una zona a medias
    # (<3 nodos) no encierra nada.
    zone_inside: bool = False
