from dataclasses import dataclass, field, make_dataclass
from .base import PacketFunctions, repeat
from .structures import Vec, Vector
from lfs_insim.insim_enums import OSO


@dataclass
class OSMain(PacketFunctions):
    AngVel: Vector = field(default_factory=Vector, metadata={'fmt': Vector})
    Heading: float = field(default=0.0, metadata={'fmt': 'f'})
    Pitch: float = field(default=0.0, metadata={'fmt': 'f'})
    Roll: float = field(default=0.0, metadata={'fmt': 'f'})
    Accel: Vector = field(default_factory=Vector, metadata={'fmt': Vector})
    Vel: Vector = field(default_factory=Vector, metadata={'fmt': Vector})
    Pos: Vec = field(default_factory=Vec, metadata={'fmt': Vec})


@dataclass
class OutSimPack(PacketFunctions):
    """OutSim legacy (formato fijo, activado via SMALL.SSP)."""
    Time: int = field(default=0, metadata={'fmt': 'I'})
    AngVel: Vector = field(default_factory=Vector, metadata={'fmt': Vector})
    Heading: float = field(default=0.0, metadata={'fmt': 'f'})
    Pitch: float = field(default=0.0, metadata={'fmt': 'f'})
    Roll: float = field(default=0.0, metadata={'fmt': 'f'})
    Accel: Vector = field(default_factory=Vector, metadata={'fmt': Vector})
    Vel: Vector = field(default_factory=Vector, metadata={'fmt': Vector})
    Pos: Vec = field(default_factory=Vec, metadata={'fmt': Vec})
    ID: int = field(default=0, metadata={'fmt': 'i'})


@dataclass
class OutGaugePack(PacketFunctions):
    """OutGauge (formato fijo, activado via SMALL.SSG)."""
    Time: int = field(default=0, metadata={'fmt': 'I'})
    Car: str = field(default="", metadata={'fmt': '4s'})
    Flags: int = field(default=0, metadata={'fmt': 'H'})
    Gear: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Speed: float = field(default=0.0, metadata={'fmt': 'f'})
    RPM: float = field(default=0.0, metadata={'fmt': 'f'})
    Turbo: float = field(default=0.0, metadata={'fmt': 'f'})
    EngTemp: float = field(default=0.0, metadata={'fmt': 'f'})
    Fuel: float = field(default=0.0, metadata={'fmt': 'f'})
    OilPressure: float = field(default=0.0, metadata={'fmt': 'f'})
    OilTemp: float = field(default=0.0, metadata={'fmt': 'f'})
    DashLights: int = field(default=0, metadata={'fmt': 'I'})
    ShowLights: int = field(default=0, metadata={'fmt': 'I'})
    Throttle: float = field(default=0.0, metadata={'fmt': 'f'})
    Brake: float = field(default=0.0, metadata={'fmt': 'f'})
    Clutch: float = field(default=0.0, metadata={'fmt': 'f'})
    Display1: str = field(default="", metadata={'fmt': '16s'})
    Display2: str = field(default="", metadata={'fmt': '16s'})


@dataclass
class OutSimMain(PacketFunctions):
    AngVel: Vector = field(default_factory=Vector, metadata={'fmt': Vector})
    Heading: float = field(default=0.0, metadata={'fmt': 'f'})
    Pitch: float = field(default=0.0, metadata={'fmt': 'f'})
    Roll: float = field(default=0.0, metadata={'fmt': 'f'})
    Accel: Vector = field(default_factory=Vector, metadata={'fmt': Vector})
    Vel: Vector = field(default_factory=Vector, metadata={'fmt': Vector})
    Pos: Vec = field(default_factory=Vec, metadata={'fmt': Vec})


@dataclass
class OutSimInputs(PacketFunctions):
    Throttle: float = field(default=0.0, metadata={'fmt': 'f'})
    Brake: float = field(default=0.0, metadata={'fmt': 'f'})
    InputSteer: float = field(default=0.0, metadata={'fmt': 'f'})
    Clutch: float = field(default=0.0, metadata={'fmt': 'f'})
    Handbrake: float = field(default=0.0, metadata={'fmt': 'f'})


@dataclass
class OutSimWheel(PacketFunctions):
    SuspDeflect: float = field(default=0.0, metadata={'fmt': 'f'})
    Steer: float = field(default=0.0, metadata={'fmt': 'f'})
    XForce: float = field(default=0.0, metadata={'fmt': 'f'})
    YForce: float = field(default=0.0, metadata={'fmt': 'f'})
    VerticalLoad: float = field(default=0.0, metadata={'fmt': 'f'})
    AngVel: float = field(default=0.0, metadata={'fmt': 'f'})
    LeanRelToRoad: float = field(default=0.0, metadata={'fmt': 'f'})
    AirTemp: int = field(default=0, metadata={'fmt': 'B'})
    SlipFraction: int = field(default=0, metadata={'fmt': 'B'})
    Touching: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    SlipRatio: float = field(default=0.0, metadata={'fmt': 'f'})
    TanSlipAngle: float = field(default=0.0, metadata={'fmt': 'f'})


def build_outsim_pack2(oso_opts: OSO) -> type:
    """
    Construye dinámicamente OutSimPack2 incluyendo solo los campos
    correspondientes a los flags OSO activos.

    La clase resultante hereda de PacketFunctions y es compatible con
    el decoder (OUTSIM_PACKETS se indexa por su tamaño).

    El tamaño del paquete resultante debe coincidir con OutSim Opts en cfg.txt.
    """
    fields = []

    if oso_opts & OSO.HEADER:
        fields += [
            ('L', str, field(default='L', metadata={'fmt': 's'})),
            ('F', str, field(default='F', metadata={'fmt': 's'})),
            ('S', str, field(default='S', metadata={'fmt': 's'})),
            ('T', str, field(default='T', metadata={'fmt': 's'})),
        ]
    if oso_opts & OSO.ID:
        fields.append(('ID', int, field(default=0, metadata={'fmt': 'i'})))
    if oso_opts & OSO.TIME:
        fields.append(('Time', int, field(default=0, metadata={'fmt': 'I'})))
    if oso_opts & OSO.MAIN:
        fields.append((
            'OSMain', OutSimMain,
            field(default_factory=OutSimMain, metadata={'fmt': OutSimMain})
        ))
    if oso_opts & OSO.INPUTS:
        fields.append((
            'OSInputs', OutSimInputs,
            field(default_factory=OutSimInputs, metadata={'fmt': OutSimInputs})
        ))
    if oso_opts & OSO.DRIVE:
        fields += [
            ('Gear',           int,   field(default=0,   metadata={'fmt': 'B'})),
            ('Sp1',            int,   field(default=0,   metadata={'fmt': 'B'})),
            ('Sp2',            int,   field(default=0,   metadata={'fmt': 'B'})),
            ('Sp3',            int,   field(default=0,   metadata={'fmt': 'B'})),
            ('EngineAngVel',   float, field(default=0.0, metadata={'fmt': 'f'})),
            ('MaxTorqueAtVel', float, field(default=0.0, metadata={'fmt': 'f'})),
        ]
    if oso_opts & OSO.DISTANCE:
        fields += [
            ('CurrentLapDist',  float, field(default=0.0, metadata={'fmt': 'f'})),
            ('IndexedDistance', float, field(default=0.0, metadata={'fmt': 'f'})),
        ]
    if oso_opts & OSO.WHEELS:
        fields.append((
            'OSWheels', tuple,
            field(
                default_factory=lambda: (
                    OutSimWheel(), OutSimWheel(), OutSimWheel(), OutSimWheel()
                ),
                metadata={'fmt': repeat(OutSimWheel, 4)}
            )
        ))
    if oso_opts & OSO.EXTRA_1:
        fields += [
            ('SteerTorque', float, field(default=0.0, metadata={'fmt': 'f'})),
            ('Spare',       float, field(default=0.0, metadata={'fmt': 'f'})),
        ]

    return make_dataclass('OutSimPack2', fields, bases=(PacketFunctions,))


# OutSimPack2 con todos los campos — para type annotations e IDE autocomplete.
# El decoder registra la versión dinámica construida según los opts declarados.
OutSimPack2 = build_outsim_pack2(OSO.ALL)
