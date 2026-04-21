"""um_class.py"""

from dataclasses import dataclass, field
from typing import Any
from lfs_insim.insim_enums import *
from lfs_insim.utils import (
    lfs_pos_to_meters, lfs_angvel_to_degrees_per_second,
    lfs_speed_to_kmh, lfs_angle_to_degrees
)

# ---------------------------------------------------------
# 1. ENTIDADES (Modelos de datos)
# ---------------------------------------------------------

@dataclass
class Coordinates:
    """Coordenadas, tiene getters y setters"""
    x: int
    y: int
    z: int

    @property
    def x_m(self) -> float:
        return lfs_pos_to_meters(self.x)
    
    @x_m.setter
    def x_m(self, value: float):
        self.x = lfs_pos_to_meters(value, rev=True)

    @property
    def y_m(self) -> float:
        return lfs_pos_to_meters(self.y)
    
    @y_m.setter
    def y_m(self, value: float):
        self.y = lfs_pos_to_meters(value, rev=True)

    @property
    def z_m(self) -> float:
        return lfs_pos_to_meters(self.z)
    
    @z_m.setter
    def z_m(self, value: float):
        self.z = lfs_pos_to_meters(value, rev=True)

@dataclass
class Speed:
    """Velocidad, con conversión automática a km/h"""
    speed_lfs: int  # Corregido para que coincida en el getter/setter
    
    @property
    def speed_kmh(self) -> float:
        return lfs_speed_to_kmh(self.speed_lfs)
    
    @speed_kmh.setter
    def speed_kmh(self, value: float):
        self.speed_lfs = lfs_speed_to_kmh(value, rev=True)

@dataclass
class Angle:
    """Ángulos de LFS (Heading/Direction) a grados (-180 a 180)"""
    angle_lfs: int
    
    @property
    def degrees(self) -> float:
        return lfs_angle_to_degrees(self.angle_lfs)
        
    @degrees.setter
    def degrees(self, value: float):
        self.angle_lfs = lfs_angle_to_degrees(value, rev=True)

@dataclass
class AngularVelocity:
    """Velocidad de rotación del chasis (AngVel)"""
    angvel_lfs: int
    
    @property
    def degrees_per_second(self) -> float:
        # 16384 unidades en LFS = 360 grados por segundo
        return lfs_angvel_to_degrees_per_second(self.angvel_lfs)
        
    @degrees_per_second.setter
    def degrees_per_second(self, value: float):
        self.angvel_lfs = lfs_angvel_to_degrees_per_second(value, rev=True)

@dataclass
class CCIFlags:
    """Decodifica el byte 'Info' del paquete CompCar (IS_MCI)"""
    raw_info: int
    
    @property
    def is_blue_flag(self) -> bool:
        return bool(self.raw_info & CCI.BLUE)
        
    @property
    def is_yellow_flag(self) -> bool:
        return bool(self.raw_info & CCI.YELLOW)
        
    @property
    def is_lagging(self) -> bool:
        return bool(self.raw_info & CCI.LAG)
        
    @property
    def is_first(self) -> bool:
        return bool(self.raw_info & CCI.FIRST)

    @property
    def is_last(self) -> bool:
        return bool(self.raw_info & CCI.LAST)

# --- CLASES DEL DOMINIO DEL SERVIDOR ---

@dataclass
class Telemetry:
    """Datos raw directos del MCI para máxima precisión y escalabilidad."""
    node: int
    lap: int
    position_race: int
    info: CCIFlags
    coordinates: Coordinates
    speed: Speed
    direction: Angle
    heading: Angle
    angvel: AngularVelocity
    extra: dict[str, Any] = field(default_factory=dict)

@dataclass
class User:
    """
    Representa una cuenta de LFS (Uname)
    Estando en un servidor adquiere un UserIdentificator (UCID)
    
    Si el UCID es 0, dicho usuario es el host
    Puede tener AI's activas
    El campo plid tiene un valor si dicho usuario está en pista
    """
    user_name: str
    ucid: int
    player_name: str
    admin: AD_NOAD
    connection_type: NCN_FLAGS
    plids_ais_actives: set[int] = field(default_factory=set)
    plid: int|None = None
    extra: dict[str, Any] = field(default_factory=dict)

@dataclass
class Player:
    """
    Representa un vehículo en pista (PLID) que siemple
    estará asociado a su usuario (UCID)
    """
    plid: int
    player_type: PTYPE
    plate: str
    flags: PIF
    car_name: str
    skin_name: str
    tyres: tuple[TYRE,TYRE,TYRE,TYRE]
    handicap_mass: int
    handicap_throttle: int
    driver_model: int
    passengers: PASS
    rwadj: int
    fwadj: int
    set_up_flags: SETF
    configuration: int
    starting_fuel: int
    ucid: int
    telemetry: Telemetry|None = None
    extra: dict[str, Any] = field(default_factory=dict)

@dataclass
class AI:
    """Representa un vehículo AI en pista (PLID, pertenece a un usuario UCID)"""
    player: Player
    ai_name: str
    extra: dict[str, Any] = field(default_factory=dict)