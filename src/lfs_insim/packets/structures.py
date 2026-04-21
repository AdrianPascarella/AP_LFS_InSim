from dataclasses import dataclass, field
from .base import PacketFunctions, repeat
from lfs_insim.insim_enums import (
    CCI, PHC, CS, CSVAL, OSO
)

# Structs básicos
@dataclass
class Vec(PacketFunctions):
    X: int = field(default=0, metadata={'fmt': 'i'})
    Y: int = field(default=0, metadata={'fmt': 'i'})
    Z: int = field(default=0, metadata={'fmt': 'i'})

@dataclass
class Vector(PacketFunctions):
    X: float = field(default=0.0, metadata={'fmt': 'f'})
    Y: float = field(default=0.0, metadata={'fmt': 'f'})
    Z: float = field(default=0.0, metadata={'fmt': 'f'})

# Structs complejos de InSim
@dataclass
class NodeLap(PacketFunctions):
    Node: int = field(default=0, metadata={'fmt': 'H'})
    Lap: int = field(default=0, metadata={'fmt': 'H'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Position: int = field(default=0, metadata={'fmt': 'B'})

@dataclass 
class CompCar(PacketFunctions):
    Node: int = field(default=0, metadata={'fmt': 'H'})
    Lap: int = field(default=0, metadata={'fmt': 'H'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Position: int = field(default=0, metadata={'fmt': 'B'})
    Info: CCI = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    X: int = field(default=0, metadata={'fmt': 'i'})
    Y: int = field(default=0, metadata={'fmt': 'i'})
    Z: int = field(default=0, metadata={'fmt': 'i'})
    Speed: int = field(default=0, metadata={'fmt': 'H'})
    Direction: int = field(default=0, metadata={'fmt': 'H'})
    Heading: int = field(default=0, metadata={'fmt': 'H'})
    AngVel: int = field(default=0, metadata={'fmt': 'h'})

@dataclass
class CarContact(PacketFunctions):
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Info: CCI = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Steer: int = field(default=0, metadata={'fmt': 'b'})
    ThrBrk: int = field(default=0, metadata={'fmt': 'B'})
    CluHan: int = field(default=0, metadata={'fmt': 'B'})
    GearSp: int = field(default=0, metadata={'fmt': 'B'})
    Speed: int = field(default=0, metadata={'fmt': 'B'})
    Direction: int = field(default=0, metadata={'fmt': 'B'})
    Heading: int = field(default=0, metadata={'fmt': 'B'})
    AccelF: int = field(default=0, metadata={'fmt': 'b'})
    AccelR: int = field(default=0, metadata={'fmt': 'b'})
    X: int = field(default=0, metadata={'fmt': 'h'})
    Y: int = field(default=0, metadata={'fmt': 'h'})

@dataclass
class CarContOBJ(PacketFunctions):
    Direction: int = field(default=0, metadata={'fmt': 'B'})
    Heading: int = field(default=0, metadata={'fmt': 'B'})
    Speed: int = field(default=0, metadata={'fmt': 'B'})
    Zbyte: int = field(default=0, metadata={'fmt': 'B'})
    X: int = field(default=0, metadata={'fmt': 'h'})
    Y: int = field(default=0, metadata={'fmt': 'h'})

@dataclass
class ObjectInfo(PacketFunctions):
    X: int = field(default=0, metadata={'fmt': 'h'})
    Y: int = field(default=0, metadata={'fmt': 'h'})
    Zbyte: int = field(default=0, metadata={'fmt': 'B'})
    Flags: int = field(default=0, metadata={'fmt': 'B'})
    Index: int = field(default=0, metadata={'fmt': 'B'})
    Heading: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class CarHCP(PacketFunctions):
    H_Mass: int = field(default=0, metadata={'fmt': 'B'})
    H_TRes: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class PlayerHCap(PacketFunctions):
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Flags: PHC = field(default=0, metadata={'fmt': 'B'})
    H_Mass: int = field(default=0, metadata={'fmt': 'B'})
    H_TRes: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class AIInputVal(PacketFunctions):
    Input: CS = field(default=0, metadata={'fmt': 'B'})
    Time: int = field(default=0, metadata={'fmt': 'B'})
    Value: CSVAL = field(default=0, metadata={'fmt': 'H'})
