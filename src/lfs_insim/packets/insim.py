from dataclasses import dataclass, field
from .base import PacketFunctions, repeat
from .structures import (
    Vec, Vector, NodeLap, CompCar, CarContact, CarContOBJ, 
    ObjectInfo, CarHCP, PlayerHCap, AIInputVal
)
from .outsim import OSMain
from lfs_insim.insim_enums import *

@dataclass
class ISP_NONE(PacketFunctions):
    Size: int = field(default=4, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.NONE, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    NumC: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_ISI(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.ISI, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    UDPPort: int = field(default=0, metadata={'fmt': 'H'})
    Flags: ISF = field(default=0, metadata={'fmt': 'H'})
    InSimVer: int = field(default=10, metadata={'fmt': 'B'})
    Prefix: int = field(default=ord("!"), metadata={'fmt': 'B'})
    Interval: int = field(default=100, metadata={'fmt': 'H'})
    Admin: str = field(default='', metadata={'fmt': '16s'})
    IName: str = field(default='TestInsim', metadata={'fmt': '16s'})

@dataclass
class ISP_VER(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.VER, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    Version: str = field(default='', metadata={'fmt': '8s'})
    Product: str = field(default='', metadata={'fmt': '6s'})
    InSimVer: int = field(default=0, metadata={'fmt': 'B'})
    Spare: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_TINY(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.TINY, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    SubT: TINY = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_SMALL(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: int = field(default=ISP.SMALL, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    SubT: SMALL = field(default=0, metadata={'fmt': 'B'})
    UVal: int = field(default=0, metadata={'fmt': 'I'})

@dataclass
class ISP_STA(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.STA, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    ReplaySpeed: float = field(default=0.0, metadata={'fmt': 'f'})
    Flags: ISS = field(default=0, metadata={'fmt': 'H'})
    InGameCam: VIEW = field(default=0, metadata={'fmt': 'B'})
    ViewPLID: int = field(default=0, metadata={'fmt': 'B'})
    NumP: int = field(default=0, metadata={'fmt': 'B'})
    NumConns: int = field(default=0, metadata={'fmt': 'B'})
    NumFinished: int = field(default=0, metadata={'fmt': 'B'})
    RaceInProg: RAINPR = field(default=0, metadata={'fmt': 'B'})
    QualMins: int = field(default=0, metadata={'fmt': 'B'})
    RaceLaps: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    ServerStatus: SERVER = field(default=0, metadata={'fmt': 'B'})
    Track: str = field(default='', metadata={'fmt': '6s'})
    Weather: int = field(default=0, metadata={'fmt': 'B'})
    Wind: WIND = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_SCH(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.SCH, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    CharB: CHARS = field(default=0, metadata={'fmt': 'B'})
    Flags: SCH_FLAGS = field(default=0, metadata={'fmt': 'B'})
    Spare2: int = field(default=0, metadata={'fmt': 'B'})
    Spare3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_SFP(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.SFP, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    Flag: ISS_SFP = field(default=0, metadata={'fmt': 'H'})
    OffOn: OFFON = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_SCC(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.SCC, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    ViewPLID: int = field(default=0, metadata={'fmt': 'B'})
    InGameCam: VIEW = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_CPP(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.CPP, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    Pos: Vec = field(default_factory=Vec, metadata={'fmt': Vec})
    H: int = field(default=0, metadata={'fmt': 'H'})
    P: int = field(default=0, metadata={'fmt': 'H'})
    R: int = field(default=0, metadata={'fmt': 'H'})
    ViewPLID: int = field(default=0, metadata={'fmt': 'B'})
    InGameCam: VIEW = field(default=0, metadata={'fmt': 'B'})
    FOV: float = field(default=0.0, metadata={'fmt': 'f'})
    Time: int = field(default=0, metadata={'fmt': 'H'})
    Flags: ISS_CPP = field(default=0, metadata={'fmt': 'H'})

@dataclass
class ISP_ISM(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.ISM, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    Host: HG = field(default=0, metadata={'fmt': 'B'})
    Sp1: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    Hname: str = field(default='', metadata={'fmt': '32s'})

@dataclass
class ISP_MSO(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.MSO, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    UserType: MSO = field(default=0, metadata={'fmt': 'B'})
    TextStart: int = field(default=0, metadata={'fmt': 'B'})
    Msg: str = field(default="", metadata={'fmt': ('s', 128)})

@dataclass
class ISP_III(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.III, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    Msg: str = field(default="", metadata={'fmt': ('s', 64)})

@dataclass
class ISP_MST(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.MST, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    Msg: str = field(default='', metadata={'fmt': '64s'})

@dataclass
class ISP_MTC(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.MTC, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Sound: SND = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    Text: str = field(default="", metadata={'fmt': ('s', 128)})

@dataclass
class ISP_MOD(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.MOD, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    Bits16: MOD_BIT = field(default=0, metadata={'fmt': 'i'})
    RR: int = field(default=0, metadata={'fmt': 'i'})
    Width: int = field(default=0, metadata={'fmt': 'i'})
    Height: int = field(default=0, metadata={'fmt': 'i'})

@dataclass
class ISP_VTN(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.VTN, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    Action: VOTE = field(default=0, metadata={'fmt': 'B'})
    Spare2: int = field(default=0, metadata={'fmt': 'B'})
    Spare3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_RST(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.RST, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    RaceLaps: int = field(default=0, metadata={'fmt': 'B'})
    QualMins: int = field(default=0, metadata={'fmt': 'B'})
    NumP: int = field(default=0, metadata={'fmt': 'B'})
    Timing: RST_TIMING = field(default=0, metadata={'fmt': 'B'})
    Track: str = field(default='', metadata={'fmt': '6s'})
    Weather: int = field(default=0, metadata={'fmt': 'B'})
    Wind: WIND = field(default=0, metadata={'fmt': 'B'})
    Flags: HOSTF = field(default=0, metadata={'fmt': 'H'})
    NumNodes: int = field(default=0, metadata={'fmt': 'H'})
    Finish: int = field(default=0, metadata={'fmt': 'H'})
    Split1: int = field(default=0, metadata={'fmt': 'H'})
    Split2: int = field(default=0, metadata={'fmt': 'H'})
    Split3: int = field(default=0, metadata={'fmt': 'H'})

@dataclass
class ISP_NCN(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.NCN, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    UName: str = field(default='', metadata={'fmt': '24s'})
    PName: str = field(default='', metadata={'fmt': '24s'})
    Admin: AD_NOAD = field(default=0, metadata={'fmt': 'B'})
    Total: int = field(default=0, metadata={'fmt': 'B'})
    Flags: NCN_FLAGS = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_CNL(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.CNL, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    Reason: LEAVR = field(default=0, metadata={'fmt': 'B'})
    Total: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_CPR(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.CPR, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    PName: str = field(default='', metadata={'fmt': '24s'})
    Plate: str = field(default='', metadata={'fmt': '8s'})

@dataclass
class ISP_NPL(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.NPL, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    PType: PTYPE = field(default=0, metadata={'fmt': 'B'})
    Flags: PIF = field(default=0, metadata={'fmt': 'H'})
    PName: str = field(default='', metadata={'fmt': '24s'})
    Plate: str = field(default='', metadata={'fmt': '8s'})
    CName: str = field(default='', metadata={'fmt': '4s'})
    SName: str = field(default='', metadata={'fmt': '16s'})
    Tyres: tuple[TYRE,TYRE,TYRE,TYRE] = field(default=(0,0,0,0), metadata={'fmt': repeat('B', 4)})
    H_Mass: int = field(default=0, metadata={'fmt': 'B'})
    H_TRes: int = field(default=0, metadata={'fmt': 'B'})
    Model: int = field(default=0, metadata={'fmt': 'B'})
    Pass: PASS = field(default=0, metadata={'fmt': 'B'})
    RWAdj: int = field(default=0, metadata={'fmt': 'B'})
    FWAdj: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    SetF: SETF = field(default=0, metadata={'fmt': 'B'})
    NumP: int = field(default=0, metadata={'fmt': 'B'})
    Config: CAR_CONFIG = field(default=0, metadata={'fmt': 'B'})
    Fuel: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_PLP(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.PLP, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_PLL(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.PLL, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_LAP(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: int = field(default=ISP.LAP, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLIP: int = field(default=0, metadata={'fmt': 'B'})
    LTime: int = field(default=0, metadata={'fmt': 'I'})
    ETime: int = field(default=0, metadata={'fmt': 'I'})
    LapsDone: int = field(default=0, metadata={'fmt': 'H'})
    Flags: PIF = field(default=0, metadata={'fmt': 'H'})
    Sp0: int = field(default=0, metadata={'fmt': 'B'})
    Penalty: PENALTY = field(default=0, metadata={'fmt': 'B'})
    NumStops: int = field(default=0, metadata={'fmt': 'B'})
    Fuel200: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_SPX(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.SPX, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLIP: int = field(default=0, metadata={'fmt': 'B'})
    STime: int = field(default=0, metadata={'fmt': 'I'})
    ETime: int = field(default=0, metadata={'fmt': 'I'})
    Split: int = field(default=0, metadata={'fmt': 'B'})
    Penalty: PENALTY = field(default=0, metadata={'fmt': 'B'})
    NumStops: int = field(default=0, metadata={'fmt': 'B'})
    Fuel200: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_PIT(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.PIT, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    LapsDone: int = field(default=0, metadata={'fmt': 'H'})
    Flags: PIF = field(default=0, metadata={'fmt': 'H'})
    FuelAdd: int = field(default=0, metadata={'fmt': 'B'})
    Penalty: PENALTY = field(default=0, metadata={'fmt': 'B'})
    NumStops: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    Tyres: tuple[TYRE, TYRE, TYRE, TYRE] = field(default=(0,0,0,0), metadata={'fmt': repeat('B', 4)})
    Work: PSE = field(default=0, metadata={'fmt': 'I'})
    Spare: int = field(default=0, metadata={'fmt': 'I'})

@dataclass
class ISP_PSF(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.PSF, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    STime: int = field(default=0, metadata={'fmt': 'I'})
    Spare: int = field(default=0, metadata={'fmt': 'I'})

@dataclass
class ISP_PLA(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.PLA, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Fact: PITLANE = field(default=0, metadata={'fmt': 'B'})
    Sp1: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_CCH(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.CCH, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Camera: VIEW = field(default=0, metadata={'fmt': 'B'})
    Sp1: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_PEN(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.PEN, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    OldPen: PENALTY = field(default=0, metadata={'fmt': 'B'})
    NewPen: PENALTY = field(default=0, metadata={'fmt': 'B'})
    Reason: PENR = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_TOC(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.TOC, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    OldUCID: int = field(default=0, metadata={'fmt': 'B'})
    NewUCID: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_FLG(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: int = field(default=32, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    OffOn: OFFON = field(default=0, metadata={'fmt': 'B'})
    Flag: int = field(default=0, metadata={'fmt': 'B'})
    CarBehind: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_PFL(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.PFL, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Flags: PIF = field(default=0, metadata={'fmt': 'H'})
    Spare: int = field(default=0, metadata={'fmt': 'H'})

@dataclass
class ISP_FIN(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.FIN, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    TTime: int = field(default=0, metadata={'fmt': 'I'})
    BTime: int = field(default=0, metadata={'fmt': 'I'})
    SpA: int = field(default=0, metadata={'fmt': 'B'})
    NumStops: int = field(default=0, metadata={'fmt': 'B'})
    Confirm: CONF = field(default=0, metadata={'fmt': 'B'})
    SpB: int = field(default=0, metadata={'fmt': 'B'})
    LapsDone: int = field(default=0, metadata={'fmt': 'H'})
    Flags: PIF = field(default=0, metadata={'fmt': 'H'})

@dataclass
class ISP_RES(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.RES, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Uname: str = field(default='', metadata={'fmt': '24s'})
    Pname: str = field(default='', metadata={'fmt': '24s'})
    Plate: str = field(default='', metadata={'fmt': '8s'})
    Cname: str = field(default='', metadata={'fmt': '4s'})
    TTime: int = field(default=0, metadata={'fmt': 'I'})
    BTime: int = field(default=0, metadata={'fmt': 'I'})
    SpA: int = field(default=0, metadata={'fmt': 'B'})
    NumStops: int = field(default=0, metadata={'fmt': 'B'})
    Confirm: CONF = field(default=0, metadata={'fmt': 'B'})
    SpB: int = field(default=0, metadata={'fmt': 'B'})
    LapsDone: int = field(default=0, metadata={'fmt': 'H'})
    Flags: PIF = field(default=0, metadata={'fmt': 'H'})
    ResultNum: int = field(default=0, metadata={'fmt': 'B'})
    NumRes: int = field(default=0, metadata={'fmt': 'B'})
    PSeconds: int = field(default=0, metadata={'fmt': 'H'})

@dataclass
class ISP_REO(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: int = field(default=36, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    NumP: int = field(default=0, metadata={'fmt': 'B'})
    PLID: tuple[int, ...] = field(default_factory=lambda: tuple(0 for _ in range(48)), metadata={'fmt': repeat('B', 48)})

@dataclass
class ISP_NLP(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.NLP, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    NumP: int = field(default=0, metadata={'fmt': 'B'})
    Info: list[NodeLap] = field(default_factory=lambda: [], metadata={'fmt': (NodeLap, None)})

@dataclass
class ISP_MCI(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.MCI, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    NumC: int = field(default=0, metadata={'fmt': 'B'})
    Info: list[CompCar] = field(default_factory=lambda: [], metadata={'fmt': (CompCar, None)})

@dataclass
class ISP_MSX(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.MSX, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    Msg: str = field(default='', metadata={'fmt': '96s'})

@dataclass
class ISP_MSL(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.MSL, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Sound: SND = field(default=0, metadata={'fmt': 'B'})
    Msg: str = field(default='', metadata={'fmt': '128s'})

@dataclass
class ISP_CRS(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.CRS, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_BFN(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.BFN, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    SubT: BFN = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    ClickID: int = field(default=0, metadata={'fmt': 'B'})
    ClickMax: int = field(default=0, metadata={'fmt': 'B'})
    Inst: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_AXI(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.AXI, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    AXStart: int = field(default=0, metadata={'fmt': 'B'})
    NumCP: int = field(default=0, metadata={'fmt': 'B'})
    NumO: int = field(default=0, metadata={'fmt': 'H'})
    LName: str = field(default='', metadata={'fmt': '32s'})

@dataclass
class ISP_AXO(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.AXO, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_BTN(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.BTN, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    ClickID: int = field(default=0, metadata={'fmt': 'B'})
    Inst: INST = field(default=0, metadata={'fmt': 'B'})
    BStyle: ISB_STYLE = field(default=0, metadata={'fmt': 'B'})
    TypeIn: TYPEIN_FLAGS = field(default=0, metadata={'fmt': 'B'})
    L: int = field(default=0, metadata={'fmt': 'B'})
    T: int = field(default=0, metadata={'fmt': 'B'})
    W: int = field(default=0, metadata={'fmt': 'B'})
    H: int = field(default=0, metadata={'fmt': 'B'})
    Text: str = field(default="", metadata={'fmt': ('s', 240)})

@dataclass
class ISP_BTC(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.BTC, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    ClickID: int = field(default=0, metadata={'fmt': 'B'})
    Inst: INST = field(default=0, metadata={'fmt': 'B'})
    CFlags: ISB_CLICK = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_BTT(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.BTT, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    ClickID: int = field(default=0, metadata={'fmt': 'B'})
    Inst: INST = field(default=0, metadata={'fmt': 'B'})
    TypeIn: TYPEIN_FLAGS = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    Text: str = field(default='', metadata={'fmt': '96s'})

@dataclass
class ISP_RIP(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.RIP, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Error: RIP = field(default=0, metadata={'fmt': 'B'})
    MPR: SMPR = field(default=0, metadata={'fmt': 'B'})
    Paused: int = field(default=0, metadata={'fmt': 'B'})
    Options: RIPOPT = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    CTime: int = field(default=0, metadata={'fmt': 'I'})
    TTime: int = field(default=0, metadata={'fmt': 'I'})
    RName: str = field(default='', metadata={'fmt': '64s'})

@dataclass
class ISP_SSH(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.SSH, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Error: SSH = field(default=0, metadata={'fmt': 'B'})
    Sp0: int = field(default=0, metadata={'fmt': 'B'})
    Sp1: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    Name: str = field(default='', metadata={'fmt': '32s'})

@dataclass
class ISP_CON(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.CON, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    SpClose: int = field(default=0, metadata={'fmt': 'H'})
    SpW: int = field(default=0, metadata={'fmt': 'H'})
    Time: int = field(default=0, metadata={'fmt': 'I'})
    A: CarContact = field(default_factory=CarContact, metadata={'fmt': CarContact})
    B: CarContact = field(default_factory=CarContact, metadata={'fmt': CarContact})

@dataclass
class ISP_OBH(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.OBH, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    SpClose: int = field(default=0, metadata={'fmt': 'H'})
    SpW: int = field(default=0, metadata={'fmt': 'H'})
    Time: int = field(default=0, metadata={'fmt': 'I'})
    C: CarContOBJ = field(default_factory=CarContOBJ, metadata={'fmt': CarContOBJ})
    X: int = field(default=0, metadata={'fmt': 'h'})
    Y: int = field(default=0, metadata={'fmt': 'h'})
    Zbyte: int = field(default=0, metadata={'fmt': 'B'})
    Sp1: int = field(default=0, metadata={'fmt': 'B'})
    Index: AXO_INDEX = field(default=0, metadata={'fmt': 'B'})
    OBHFlags: OBH = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_HLV(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.HLV, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    HLVC: GWSO = field(default=0, metadata={'fmt': 'B'})
    Sp1: int = field(default=0, metadata={'fmt': 'B'})
    SpW: int = field(default=0, metadata={'fmt': 'H'})
    Time: int = field(default=0, metadata={'fmt': 'I'})
    C: CarContOBJ = field(default_factory=CarContOBJ, metadata={'fmt': CarContOBJ})

@dataclass
class ISP_PLC(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.PLC, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    Sp1: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    Cars: CARS = field(default=0, metadata={'fmt': 'I'})

@dataclass
class ISP_AXM(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.AXM, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    NumO: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    PMOAction: PMO = field(default=0, metadata={'fmt': 'B'})
    PMOFlags: PMOF = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    Info: list[ObjectInfo] = field(default_factory=lambda: [], metadata={'fmt': (ObjectInfo, None)})

@dataclass
class ISP_ACR(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.ACR, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    Admin: AD_NOAD = field(default=0, metadata={'fmt': 'B'})
    Result: RESULT = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    Text: str = field(default='', metadata={'fmt': ('s', 64)})

@dataclass
class ISP_HCP(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.HCP, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    Info: list[CarHCP] = field(default_factory=lambda: list(CarHCP() for _ in range(32)), metadata={'fmt': repeat(CarHCP, 32)})

@dataclass
class ISP_NCI(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.NCI, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    Language: LFS = field(default=0, metadata={'fmt': 'B'})
    License: LICENSE = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    UserID: int = field(default=0, metadata={'fmt': 'I'})
    IPAddress: int = field(default=0, metadata={'fmt': 'I'})

@dataclass
class ISP_JRR(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.JRR, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    JRRAction: JRR = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    StartPos: ObjectInfo = field(default_factory=ObjectInfo, metadata={'fmt': ObjectInfo})

@dataclass
class ISP_UCO(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.UCO, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Sp0: int = field(default=0, metadata={'fmt': 'B'})
    UCOAction: UCO = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    Time: int = field(default=0, metadata={'fmt': 'I'})
    C: CarContOBJ = field(default_factory=CarContOBJ, metadata={'fmt': CarContOBJ})
    Info: ObjectInfo = field(default_factory=ObjectInfo, metadata={'fmt': ObjectInfo})

@dataclass
class ISP_OCO(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.OCO, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    Zero: int = field(default=0, metadata={'fmt': 'B'})
    OCOAction: OCO = field(default=0, metadata={'fmt': 'B'})
    Index: AXO_INDEX = field(default=0, metadata={'fmt': 'B'})
    Identifier: int = field(default=0, metadata={'fmt': 'B'})
    Data: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_TTC(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.TTC, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    SubT: TTC = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    B1: int = field(default=0, metadata={'fmt': 'B'})
    B2: int = field(default=0, metadata={'fmt': 'B'})
    B3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_SLC(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.SLC, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    CName: str = field(default="", metadata={'fmt': '4s'})

@dataclass
class ISP_CSC(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.CSC, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    Sp0: int = field(default=0, metadata={'fmt': 'B'})
    CSCAction: CSC = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    Time: int = field(default=0, metadata={'fmt': 'I'})
    C: CarContOBJ = field(default_factory=CarContOBJ, metadata={'fmt': CarContOBJ})

@dataclass
class ISP_CIM(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.CIM, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    Mode: CIM = field(default=0, metadata={'fmt': 'B'})
    SubMode: NRM | GRG | FVM = field(default=0, metadata={'fmt': 'B'})
    SelType: MARSH = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})

@dataclass
class ISP_MAL(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.MAL, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    NumM: int = field(default=0, metadata={'fmt': 'B'})
    UCID: int = field(default=0, metadata={'fmt': 'B'})
    Flags: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    SkinID: list[int] = field(default_factory=lambda: [], metadata={'fmt': ('I', None)})

@dataclass
class ISP_PLH(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.PLH, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    NumP: int = field(default=0, metadata={'fmt': 'B'})
    HCaps: list[PlayerHCap] = field(default_factory=lambda: [], metadata={'fmt': (PlayerHCap, None)})

@dataclass
class ISP_IPB(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.IPB, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    NumB: int = field(default=0, metadata={'fmt': 'B'})
    Sp0: int = field(default=0, metadata={'fmt': 'B'})
    Sp1: int = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    BanIPs: list[tuple[int, int, int, int]] = field(default_factory=lambda: [], metadata={'fmt': ('4B', None)})

@dataclass
class ISP_AIC(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.AIC, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    Inputs: list[AIInputVal] = field(default_factory=lambda: [], metadata={'fmt': (AIInputVal, 20)})

@dataclass
class ISP_AII(PacketFunctions):
    Size: int = field(default=0, metadata={'fmt': 'B'})
    Type: ISP = field(default=ISP.AII, metadata={'fmt': 'B'})
    ReqI: int = field(default=0, metadata={'fmt': 'B'})
    PLID: int = field(default=0, metadata={'fmt': 'B'})
    OSData: OSMain = field(default_factory=OSMain, metadata={'fmt': OSMain})
    Flags: AI_FLAGS = field(default=0, metadata={'fmt': 'B'})
    Gear: GEAR = field(default=0, metadata={'fmt': 'B'})
    Sp2: int = field(default=0, metadata={'fmt': 'B'})
    Sp3: int = field(default=0, metadata={'fmt': 'B'})
    RPM: float = field(default=0.0, metadata={'fmt': 'f'})
    SpF0: float = field(default=0.0, metadata={'fmt': 'f'})
    SpF1: float = field(default=0.0, metadata={'fmt': 'f'})
    ShowLights: DL = field(default=0, metadata={'fmt': 'I'})
    SPU1: int = field(default=0, metadata={'fmt': 'I'})
    SPU2: int = field(default=0, metadata={'fmt': 'I'})
    SPU3: int = field(default=0, metadata={'fmt': 'I'})
