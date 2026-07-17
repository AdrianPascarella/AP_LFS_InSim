from enum import Enum, IntEnum


class TrafficRule(IntEnum):
    RHT = 0  # Right-Hand Traffic (Conducción por la derecha: España, USA, etc.)
    LHT = 1  # Left-Hand Traffic (Conducción por la izquierda: UK, Japón, etc.)


class YieldType(str, Enum):
    """Cómo se comporta ante un cruce el que lleva esta marca (Fase 8, S44).

    Vocabulario ÚNICO de la cesión: lo usan los dos mecanismos ortogonales —el
    `RoadLink` (el que hace la maniobra) y cada road de una `IntersectionZone`
    (el que cruza de recto)— sin que ninguno se refiera al otro.

    Hereda de `str` para que el JSON del mapa se lea a ojo ("YIELD" y no un 2).
    """

    NONE = "NONE"  # No cede nunca: tiene la prioridad.
    YIELD = "YIELD"  # Cede: para antes del punto SOLO si hay amenaza a menos de T.
    STOP = "STOP"  # Para siempre (v≈0), aguanta ~1 s y luego evalúa como YIELD.


class AIManeuverState(IntEnum):
    NORMAL = 0
    FOLLOWING = 1  # Siguiendo a un coche lento
    OVERTAKING = 2  # En pleno adelantamiento (carril contrario/izquierdo)
    RETURNING = 3  # Volviendo al carril original
