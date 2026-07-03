"""
Golden-bytes de DECODIFICACIÓN (Fase 1 — red de seguridad del core).

Cada test construye a mano los bytes de un paquete info según la spec LFS 0.8C5
(`docs/InSim.txt`) y fija el dataclass que produce `decode_packet()` hoy.
Cubre los paquetes info más usados (VER, STA, NCN, NPL, MSO, MCI, NLP...) y
los contactos (CON, OBH, HLV), más el enrutado de `decode_packet`.

Comportamientos actuales que se CARACTERIZAN tal cual (no son necesariamente
los deseados):
  - los strings se cortan en el primer null y conservan los espacios
    anteriores a él (el `.strip()` se eliminó en S11 — P19);
  - los campos de lista fija (p. ej. NPL.Tyres) se decodifican como `list`,
    aunque el dataclass los declare `tuple`;
  - los enums llegan como int crudo (no se convierten a IntEnum/IntFlag).
"""

import struct

from lfs_insim.insim_enums import ISP
from lfs_insim.insim_packet_decoders import decode_packet
from lfs_insim.packets import (
    ISP_BTC,
    ISP_BTT,
    ISP_CNL,
    ISP_CON,
    ISP_HLV,
    ISP_MCI,
    ISP_MSO,
    ISP_NCN,
    ISP_NLP,
    ISP_NPL,
    ISP_OBH,
    ISP_SMALL,
    ISP_STA,
    ISP_TINY,
    ISP_VER,
)


def _pad(texto: bytes, size: int) -> bytes:
    return texto.ljust(size, b"\x00")


class TestGoldenDecodeConexion:
    def test_ver(self):
        data = (
            bytes([5, ISP.VER, 1, 0])
            + _pad(b"0.8C5", 8)  # Version[8]
            + _pad(b"S3", 6)  # Product[6]
            + bytes([10, 0])  # InSimVer, Spare
        )
        assert len(data) == 20
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_VER)
        assert pkt.ReqI == 1
        assert pkt.Version == "0.8C5"
        assert pkt.Product == "S3"
        assert pkt.InSimVer == 10

    def test_tiny_keepalive(self):
        pkt = decode_packet(bytes([1, ISP.TINY, 0, 0]))
        assert isinstance(pkt, ISP_TINY)
        assert pkt.ReqI == 0
        assert pkt.SubT == 0

    def test_small(self):
        data = bytes([2, ISP.SMALL, 1, 4]) + struct.pack("<I", 12345678)
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_SMALL)
        assert pkt.SubT == 4
        assert pkt.UVal == 12345678

    def test_sta(self):
        data = (
            bytes([7, ISP.STA, 1, 0])
            + struct.pack("<f", 1.0)  # ReplaySpeed
            + struct.pack("<H", 0x0009)  # Flags (ISS)
            + bytes(
                [
                    3,
                    1,  # InGameCam, ViewPLID
                    2,
                    3,
                    0,  # NumP, NumConns, NumFinished
                    1,
                    0,
                    5,  # RaceInProg, QualMins, RaceLaps
                    0,
                    1,
                ]
            )  # Sp2, ServerStatus
            + _pad(b"BL1", 6)  # Track[6]
            + bytes([1, 2])  # Weather, Wind
        )
        assert len(data) == 28
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_STA)
        assert pkt.ReplaySpeed == 1.0
        assert pkt.Flags == 0x0009
        assert pkt.InGameCam == 3
        assert pkt.ViewPLID == 1
        assert pkt.NumP == 2
        assert pkt.NumConns == 3
        assert pkt.RaceInProg == 1
        assert pkt.RaceLaps == 5
        assert pkt.ServerStatus == 1
        assert pkt.Track == "BL1"
        assert pkt.Weather == 1
        assert pkt.Wind == 2

    def test_ncn(self):
        data = (
            bytes([14, ISP.NCN, 1, 4])
            + _pad(b"adrian_pace", 24)  # UName[24]
            + _pad(b"^1Adrian", 24)  # PName[24] (códigos de color intactos)
            + bytes([1, 5, 4, 0])  # Admin, Total, Flags, Sp3
        )
        assert len(data) == 56
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_NCN)
        assert pkt.UCID == 4
        assert pkt.UName == "adrian_pace"
        assert pkt.PName == "^1Adrian"
        assert pkt.Admin == 1
        assert pkt.Total == 5
        assert pkt.Flags == 4

    def test_cnl(self):
        data = bytes([2, ISP.CNL, 0, 4, 2, 4, 0, 0])
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_CNL)
        assert pkt.UCID == 4
        assert pkt.Reason == 2
        assert pkt.Total == 4


class TestGoldenDecodeMensajes:
    def test_mso_de_usuario(self):
        data = (
            bytes([6, ISP.MSO, 0, 0])
            + bytes([2, 0, 1, 9])  # UCID, PLID, UserType, TextStart
            + _pad(b"Adrian : hola", 16)  # Msg (13 + null + pad a bloque de 4)
        )
        assert len(data) == 24
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_MSO)
        assert pkt.UCID == 2
        assert pkt.UserType == 1
        assert pkt.TextStart == 9
        assert pkt.Msg == "Adrian : hola"

    def test_mso_espacios_finales_se_conservan(self):
        # P19 (S11, cambio deliberado): el decoder ya no hace .strip() — corta
        # en el primer null y conserva los espacios significativos previos.
        data = bytes([4, ISP.MSO, 0, 0]) + bytes([2, 0, 1, 0]) + b"hola   \x00"
        assert len(data) == 16
        pkt = decode_packet(data)
        assert pkt.Msg == "hola   "  # los 3 espacios se conservan

    def test_btc(self):
        data = bytes([2, ISP.BTC, 1, 4, 12, 0, 1, 0])
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_BTC)
        assert pkt.UCID == 4
        assert pkt.ClickID == 12
        assert pkt.CFlags == 1

    def test_btt(self):
        data = (
            bytes([26, ISP.BTT, 1, 4])
            + bytes([12, 0, 95, 0])  # ClickID, Inst, TypeIn, Sp3
            + _pad(b"hola mundo", 96)  # Text[96]
        )
        assert len(data) == 104
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_BTT)
        assert pkt.ClickID == 12
        assert pkt.TypeIn == 95
        assert pkt.Text == "hola mundo"


class TestGoldenDecodeJugadores:
    def test_npl(self):
        data = (
            bytes([19, ISP.NPL, 1, 3])
            + bytes([1, 2])  # UCID, PType
            + struct.pack("<H", 3)  # Flags (PIF)
            + _pad(b"IA uno", 24)  # PName[24]
            + _pad(b"AP 01", 8)  # Plate[8]
            + _pad(b"XFG", 4)  # CName[4]
            + _pad(b"default", 16)  # SName[16]
            + bytes([1, 2, 3, 4])  # Tyres[4]
            + bytes([20, 10, 0, 0, 0, 0])  # H_Mass, H_TRes, Model, Pass, RWAdj, FWAdj
            + bytes([0x21, 0])  # RIFlags (LATE_START|SAI_1), Sp3
            + bytes([7, 6, 1, 100])  # SetF, NumP, Config, Fuel
        )
        assert len(data) == 76
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_NPL)
        assert pkt.PLID == 3
        assert pkt.UCID == 1
        assert pkt.PType == 2
        assert pkt.Flags == 3
        assert pkt.PName == "IA uno"
        assert pkt.Plate == "AP 01"
        assert pkt.CName == "XFG"
        assert pkt.SName == "default"
        # Lista fija: se decodifica como list, no como tuple (comportamiento actual)
        assert pkt.Tyres == [1, 2, 3, 4]
        assert pkt.H_Mass == 20
        assert pkt.H_TRes == 10
        assert pkt.RIFlags == 0x21
        assert pkt.SetF == 7
        assert pkt.NumP == 6
        assert pkt.Config == 1
        assert pkt.Fuel == 100

    def test_mci_dos_coches(self):
        # CompCar: HHBBBB iii HHH h = 28 bytes
        car1 = struct.pack(
            "<HHBBBBiiiHHHh",
            250,
            3,
            1,
            1,
            64,
            0,
            655360,
            1310720,
            65536,  # X=10m, Y=20m, Z=1m (65536 = 1 m)
            3000,
            16384,
            16000,
            50,
        )
        car2 = struct.pack(
            "<HHBBBBiiiHHHh",
            251,
            3,
            2,
            2,
            32,
            0,
            -655360,
            -1310720,
            131072,
            2500,
            49152,
            48000,
            -50,
        )
        data = bytes([15, ISP.MCI, 0, 2]) + car1 + car2
        assert len(data) == 60
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_MCI)
        assert pkt.NumC == 2
        assert len(pkt.Info) == 2
        c1, c2 = pkt.Info
        assert (c1.Node, c1.Lap, c1.PLID, c1.Position) == (250, 3, 1, 1)
        assert c1.Info == 64
        assert (c1.X, c1.Y, c1.Z) == (655360, 1310720, 65536)
        assert (c1.Speed, c1.Direction, c1.Heading, c1.AngVel) == (
            3000,
            16384,
            16000,
            50,
        )
        assert (c2.X, c2.Y) == (-655360, -1310720)
        assert c2.AngVel == -50

    def test_nlp_tres_coches_con_padding(self):
        # NodeLap = 6 bytes; 4 + 3*6 = 22 → LFS rellena a 24 (Size=6).
        # El decoder debe leer los 3 NodeLap e ignorar los 2 bytes de padding.
        nl = (
            struct.pack("<HHBB", 100, 1, 1, 1)
            + struct.pack("<HHBB", 101, 1, 2, 2)
            + struct.pack("<HHBB", 102, 2, 3, 3)
        )
        data = bytes([6, ISP.NLP, 1, 3]) + nl + b"\x00\x00"
        assert len(data) == 24
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_NLP)
        assert pkt.NumP == 3
        assert len(pkt.Info) == 3
        assert (pkt.Info[0].Node, pkt.Info[0].Lap) == (100, 1)
        assert (pkt.Info[2].PLID, pkt.Info[2].Position) == (3, 3)


class TestGoldenDecodeContactos:
    # CarContact: BBBb BBBB BBbb hh = 16 bytes
    _CONTACTO_A = struct.pack(
        "<BBBbBBBBBBbbhh",
        1,
        1,
        0,
        -10,
        0xF0,
        0x0F,
        0x30,
        40,
        100,
        110,
        -5,
        3,
        1600,
        -1600,
    )
    _CONTACTO_B = struct.pack(
        "<BBBbBBBBBBbbhh",
        2,
        0,
        0,
        5,
        0x0F,
        0xF0,
        0x20,
        38,
        105,
        108,
        4,
        -2,
        1650,
        -1580,
    )

    def test_con(self):
        data = (
            bytes([11, ISP.CON, 0, 0])
            + struct.pack("<HH", 25, 0)  # SpClose, SpW
            + struct.pack("<I", 123456)  # Time
            + self._CONTACTO_A
            + self._CONTACTO_B
        )
        assert len(data) == 44
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_CON)
        assert pkt.SpClose == 25
        assert pkt.Time == 123456
        assert pkt.A.PLID == 1
        assert pkt.A.Steer == -10  # char con signo
        assert pkt.A.ThrBrk == 0xF0
        assert pkt.A.AccelF == -5
        assert (pkt.A.X, pkt.A.Y) == (1600, -1600)
        assert pkt.B.PLID == 2
        assert pkt.B.GearSp == 0x20

    def test_obh(self):
        data = (
            bytes([7, ISP.OBH, 0, 3])
            + struct.pack("<HH", 50, 0)  # SpClose, SpW
            + struct.pack("<I", 99999)  # Time
            + struct.pack("<BBBBhh", 10, 20, 15, 4, 800, -800)  # CarContOBJ C
            + struct.pack("<hh", 100, -100)  # X, Y
            + bytes([4, 0, 20, 3])  # Zbyte, Sp1, Index, OBHFlags
        )
        assert len(data) == 28
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_OBH)
        assert pkt.PLID == 3
        assert pkt.SpClose == 50
        assert pkt.Time == 99999
        assert (pkt.C.Direction, pkt.C.Heading, pkt.C.Speed) == (10, 20, 15)
        assert (pkt.C.X, pkt.C.Y) == (800, -800)
        assert (pkt.X, pkt.Y) == (100, -100)
        assert pkt.Index == 20
        assert pkt.OBHFlags == 3

    def test_hlv(self):
        data = (
            bytes([5, ISP.HLV, 0, 3])
            + bytes([1, 0])  # HLVC=wall, Sp1
            + struct.pack("<H", 0)  # SpW
            + struct.pack("<I", 55555)  # Time
            + struct.pack("<BBBBhh", 10, 20, 15, 4, 800, -800)  # CarContOBJ C
        )
        assert len(data) == 20
        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_HLV)
        assert pkt.PLID == 3
        assert pkt.HLVC == 1
        assert pkt.Time == 55555
        assert pkt.C.Zbyte == 4


class TestEnrutadoDecodePacket:
    def test_datos_vacios_devuelve_none(self):
        assert decode_packet(b"") is None

    def test_tipo_desconocido_devuelve_none(self):
        # Type=238 no existe en INSIM_PACKETS y len=4 no casa con OutSim/OutGauge
        assert decode_packet(bytes([1, 238, 0, 0])) is None

    def test_size_incoherente_devuelve_none(self):
        # El byte Size dice 8 bytes (2*4) pero el buffer tiene 4: firma inválida
        assert decode_packet(bytes([2, ISP.TINY, 0, 0])) is None

    def test_roundtrip_encode_decode_tiny(self):
        # Coherencia entre las dos rutas: lo que produce el encoder lo
        # reconstruye el decoder (para un paquete simple sin strings).
        from lfs_insim.insim_packet_sender import _extract_values

        pkt = ISP_TINY(ReqI=7, SubT=13)
        pkt.prepare()
        data = struct.pack(pkt.get_struct_string(), *_extract_values(pkt))
        decoded = decode_packet(data)
        assert isinstance(decoded, ISP_TINY)
        assert decoded.ReqI == 7
        assert decoded.SubT == 13
