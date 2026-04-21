from enum import IntEnum


class TrafficRule(IntEnum):
    RHT = 0  # Right-Hand Traffic (Conducción por la derecha: España, USA, etc.)
    LHT = 1  # Left-Hand Traffic (Conducción por la izquierda: UK, Japón, etc.)

class AIManeuverState(IntEnum):
    NORMAL = 0
    FOLLOWING = 1     # Siguiendo a un coche lento
    OVERTAKING = 2    # En pleno adelantamiento (carril contrario/izquierdo)
    RETURNING = 3     # Volviendo al carril original
