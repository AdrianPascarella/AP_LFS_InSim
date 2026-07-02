"""
Golden-bytes de SERIALIZACIÓN (Fase 1 — red de seguridad del core).

Cada test fija los bytes EXACTOS que produce hoy la ruta real de encode de
`send_packet()` (insim_packet_sender.py):

    packet.prepare() -> packet.get_struct_string() -> _extract_values() -> struct.pack

Si un refactor de la ruta de serialización (P19) o de la arquitectura (Fase 2)
cambia UN solo byte, estos tests fallan. Los valores esperados se generaron con
el código actual y se contrastaron contra la spec LFS 0.8C5 (`docs/InSim.txt`):
tamaños totales, byte Size (= bytes/4), byte Type y offsets de campos clave.

NOTA: desde P13 `encode` ES la función real (`encode_packet`), extraída de
`send_packet()`: estos tests ejercitan la ruta de producción sin socket.
"""
import pytest

from lfs_insim.insim_packet_sender import encode_packet as encode
from lfs_insim.packets import (
    ALLOWED_PACKETS,
    ISP_AIC, ISP_AXM, ISP_BFN, ISP_BTN, ISP_CPP, ISP_HCP, ISP_IPB, ISP_ISI,
    ISP_JRR, ISP_MAL, ISP_MOD, ISP_MSL, ISP_MST, ISP_MSX, ISP_MTC, ISP_OCO,
    ISP_PLC, ISP_PLH, ISP_REO, ISP_RIP, ISP_SCC, ISP_SCH, ISP_SFP, ISP_SMALL,
    ISP_SSH, ISP_TINY, ISP_TTC,
    AIInputVal, CarHCP, ObjectInfo, PlayerHCap, Vec,
)
from lfs_insim.insim_enums import (
    BFN, CS, ISF, JRR, SMALL, SND, TINY, TTC, VIEW,
)


class TestInvarianteEstructural:
    """Todo paquete enviable con defaults: bytes múltiplo de 4, Size y Type coherentes."""

    @pytest.mark.parametrize(
        "cls",
        list(ALLOWED_PACKETS),
        ids=lambda c: c.__name__,
    )
    def test_defaults_encajan_con_cabecera(self, cls):
        pkt = cls()
        data = encode(pkt)
        assert len(data) % 4 == 0
        assert data[0] == len(data) // 4      # Size = bytes/4
        assert data[1] == int(pkt.Type)       # byte Type = valor ISP


class TestGoldenConexion:

    def test_isi_tipico(self):
        pkt = ISP_ISI(ReqI=1, UDPPort=30000, Flags=ISF.LOCAL | ISF.MCI,
                      InSimVer=10, Prefix=ord('!'), Interval=100,
                      Admin='secreto', IName='Golden')
        assert encode(pkt) == (
            b'\x0b\x01\x01\x000u$\x00\n!d\x00'
            + b'secreto' + b'\x00' * 9
            + b'Golden' + b'\x00' * 10
        )

    def test_isi_defaults(self):
        assert encode(ISP_ISI()) == (
            b'\x0b\x01\x00\x00\x00\x00\x00\x00\n!d\x00'
            + b'\x00' * 16
            + b'TestInsim' + b'\x00' * 7
        )


class TestGoldenControl:

    def test_tiny_keepalive(self):
        assert encode(ISP_TINY()) == b'\x01\x03\x00\x00'

    def test_tiny_ncn(self):
        assert encode(ISP_TINY(ReqI=3, SubT=TINY.NCN)) == b'\x01\x03\x03\r'

    def test_small_ssp(self):
        assert encode(ISP_SMALL(ReqI=2, SubT=SMALL.SSP, UVal=100)) == \
            b'\x02\x04\x02\x01d\x00\x00\x00'

    def test_small_uval_grande(self):
        # UVal de 32 bits en little-endian
        assert encode(ISP_SMALL(SubT=SMALL.SSG, UVal=0xDEADBEEF)) == \
            b'\x02\x04\x00\x02\xef\xbe\xad\xde'

    def test_sfp(self):
        assert encode(ISP_SFP(Flag=64, OffOn=1)) == b'\x02\x07\x00\x00@\x00\x01\x00'

    def test_mod(self):
        assert encode(ISP_MOD(Bits16=0, RR=60, Width=1920, Height=1080)) == \
            b'\x05\x0f\x00\x00\x00\x00\x00\x00<\x00\x00\x00\x80\x07\x00\x008\x04\x00\x00'

    def test_scc(self):
        assert encode(ISP_SCC(ViewPLID=3, InGameCam=VIEW.CUSTOM)) == \
            b'\x02\x08\x00\x00\x03\x04\x00\x00'

    def test_cpp(self):
        # Sub-struct Vec (3 x int32) + float FOV (90.0 es exacto en float32)
        pkt = ISP_CPP(Pos=Vec(X=65536, Y=-131072, Z=1024), H=16384, P=0, R=0,
                      ViewPLID=255, InGameCam=VIEW.CUSTOM, FOV=90.0,
                      Time=1000, Flags=8)
        assert encode(pkt) == (
            b'\x08\t\x00\x00\x00\x00\x01\x00\x00\x00\xfe\xff\x00\x04\x00\x00'
            b'\x00@\x00\x00\x00\x00\xff\x04\x00\x00\xb4B\xe8\x03\x08\x00'
        )

    def test_sch(self):
        assert encode(ISP_SCH(CharB=ord('A'), Flags=1)) == b'\x02\x06\x00\x00A\x01\x00\x00'

    def test_ttc_sel(self):
        assert encode(ISP_TTC(ReqI=1, SubT=TTC.SEL, UCID=4)) == \
            b'\x02=\x01\x01\x04\x00\x00\x00'

    def test_oco(self):
        assert encode(ISP_OCO(OCOAction=5, Index=240, Identifier=10, Data=3)) == \
            b'\x02<\x00\x00\x05\xf0\n\x03'

    def test_bfn_clear(self):
        assert encode(ISP_BFN(SubT=BFN.CLEAR, UCID=255)) == b'\x02*\x00\x01\xff\x00\x00\x00'


class TestGoldenMensajes:

    def test_mst_hola(self):
        # Msg con formato FIJO '64s': se rellena con nulls hasta 64
        assert encode(ISP_MST(Msg='hola')) == \
            b'\x11\r\x00\x00' + b'hola' + b'\x00' * 60

    def test_mst_larga_se_trunca(self):
        # 70 chars en '64s': _extract_values recorta a 64 forzando null final
        assert encode(ISP_MST(Msg='x' * 70)) == \
            b'\x11\r\x00\x00' + b'x' * 63 + b'\x00'

    def test_mtc_texto_vacio_queda_en_0_bytes(self):
        # Comportamiento actual (ver P8): un string VARIABLE vacío no emite ni el
        # null terminator — el paquete queda en solo 8 bytes de cabecera.
        # La spec indica TEXT_SIZE de 4 a 128; se caracteriza tal cual.
        assert encode(ISP_MTC(UCID=255)) == b'\x02\x0e\x00\x00\xff\x00\x00\x00'

    def test_mtc_hola(self):
        # String variable ('s', 128): null terminator + padding a bloque de 4
        assert encode(ISP_MTC(UCID=1, Text='hola')) == \
            b'\x04\x0e\x00\x00\x01\x00\x00\x00hola\x00\x00\x00\x00'

    def test_mtc_larga_se_trunca_a_128(self):
        # 130 chars con límite 128: se trunca a 127 + null = 128 (total 136)
        assert encode(ISP_MTC(UCID=1, Text='y' * 130)) == \
            b'"\x0e\x00\x00\x01\x00\x00\x00' + b'y' * 127 + b'\x00'

    def test_msx(self):
        assert encode(ISP_MSX(Msg='mensaje extendido')) == \
            b"\x19'\x00\x00" + b'mensaje extendido' + b'\x00' * 79

    def test_msl(self):
        assert encode(ISP_MSL(Sound=SND.SYSMESSAGE, Msg='local')) == \
            b'!(\x00\x02' + b'local' + b'\x00' * 123


class TestGoldenCarrera:

    def test_plc(self):
        assert encode(ISP_PLC(UCID=5, Cars=0x00000003)) == \
            b'\x035\x00\x00\x05\x00\x00\x00\x03\x00\x00\x00'

    def test_jrr_con_objectinfo(self):
        # Sub-struct ObjectInfo con X/Y negativos (int16 little-endian)
        pkt = ISP_JRR(PLID=1, UCID=2, JRRAction=JRR.RESET,
                      StartPos=ObjectInfo(X=100, Y=-200, Zbyte=10,
                                          Flags=0x80, Index=0, Heading=128))
        assert encode(pkt) == b'\x04:\x00\x01\x02\x04\x00\x00d\x008\xff\n\x80\x00\x80'

    def test_mal_vacio(self):
        # MAL sin skins = instrucción "borrar lista" (4 + 4 bytes)
        assert encode(ISP_MAL(UCID=0)) == b'\x02A\x00\x00\x00\x00\x00\x00'

    def test_mal_dos_skins(self):
        # SkinID: lista variable de uint32 little-endian
        assert encode(ISP_MAL(NumM=2, SkinID=[0x00112233, 0xFFEEDDCC])) == \
            b'\x04A\x00\x02\x00\x00\x00\x003"\x11\x00\xcc\xdd\xee\xff'

    def test_plh_dos_hcaps(self):
        pkt = ISP_PLH(NumP=2, HCaps=[
            PlayerHCap(PLID=1, Flags=1, H_Mass=50, H_TRes=0),
            PlayerHCap(PLID=2, Flags=3, H_Mass=0, H_TRes=20),
        ])
        assert encode(pkt) == b'\x03B\x00\x02\x01\x012\x00\x02\x03\x00\x14'

    def test_axm_dos_objetos(self):
        pkt = ISP_AXM(NumO=2, UCID=0, PMOAction=1, PMOFlags=0, Info=[
            ObjectInfo(X=1000, Y=-1000, Zbyte=5, Flags=0, Index=20, Heading=64),
            ObjectInfo(X=-32768, Y=32767, Zbyte=255, Flags=0x80, Index=192, Heading=255),
        ])
        assert encode(pkt) == (
            b'\x066\x00\x02\x00\x01\x00\x00'
            b'\xe8\x03\x18\xfc\x05\x00\x14@'
            b'\x00\x80\xff\x7f\xff\x80\xc0\xff'
        )

    def test_aic_un_input(self):
        pkt = ISP_AIC(PLID=7, Inputs=[AIInputVal(Input=CS.THROTTLE, Time=50, Value=32768)])
        assert encode(pkt) == b'\x02D\x00\x07\x012\x00\x80'

    def test_aic_tres_inputs(self):
        pkt = ISP_AIC(PLID=7, Inputs=[
            AIInputVal(Input=CS.THROTTLE, Time=0, Value=65535),
            AIInputVal(Input=2, Time=10, Value=0),
            AIInputVal(Input=3, Time=20, Value=1),
        ])
        assert encode(pkt) == \
            b'\x04D\x00\x07\x01\x00\xff\xff\x02\n\x00\x00\x03\x14\x01\x00'

    def test_aic_25_inputs_se_truncan_a_20(self):
        # El límite ('AIInputVal', 20) descarta los inputs 21-25: 4 + 20*4 = 84 bytes
        pkt = ISP_AIC(PLID=1, Inputs=[AIInputVal(Input=i % 12, Time=i, Value=i)
                                      for i in range(25)])
        assert encode(pkt) == (
            b'\x15D\x00\x01\x00\x00\x00\x00\x01\x01\x01\x00\x02\x02\x02\x00'
            b'\x03\x03\x03\x00\x04\x04\x04\x00\x05\x05\x05\x00\x06\x06\x06\x00'
            b'\x07\x07\x07\x00\x08\x08\x08\x00\t\t\t\x00\n\n\n\x00'
            b'\x0b\x0b\x0b\x00\x00\x0c\x0c\x00\x01\r\r\x00\x02\x0e\x0e\x00'
            b'\x03\x0f\x0f\x00\x04\x10\x10\x00\x05\x11\x11\x00\x06\x12\x12\x00'
            b'\x07\x13\x13\x00'
        )


class TestGoldenPantalla:

    def test_btn(self):
        pkt = ISP_BTN(ReqI=1, UCID=0, ClickID=12, Inst=0, BStyle=32 | 7,
                      TypeIn=0, L=25, T=40, W=50, H=10, Text='Click')
        assert encode(pkt) == b"\x05-\x01\x00\x0c\x00'\x00\x19(2\nClick\x00\x00\x00"

    def test_btn_texto_vacio(self):
        # Igual que MTC: texto variable vacío = 0 bytes (solo cabecera de 12)
        assert encode(ISP_BTN(ReqI=1, ClickID=1, L=1, T=1, W=1, H=1)) == \
            b'\x03-\x01\x00\x01\x00\x00\x00\x01\x01\x01\x01'

    def test_rip(self):
        pkt = ISP_RIP(ReqI=1, MPR=0, Paused=1, Options=0,
                      CTime=60000, TTime=120000, RName='replay')
        assert encode(pkt) == (
            b'\x140\x01\x00\x00\x01\x00\x00`\xea\x00\x00\xc0\xd4\x01\x00'
            + b'replay' + b'\x00' * 58
        )

    def test_ssh(self):
        assert encode(ISP_SSH(ReqI=1, Name='captura')) == \
            b'\n1\x01\x00\x00\x00\x00\x00' + b'captura' + b'\x00' * 25


class TestGoldenSecuenciasFijas:
    """
    Golden-bytes de REO, HCP e IPB-con-bans (P21 ARREGLADO en S06): las listas
    de formato fijo (`repeat(...)`) se aplanan y rellenan con defaults hasta su
    longitud fija, y los items multi-valor ('4B') se expanden.
    """

    def test_reo_con_dos_plids(self):
        # 4 cabecera + PLID[48] = 52 bytes (Size 13); Type REO = 36
        assert encode(ISP_REO(ReqI=1, NumP=2, PLID=(9, 5))) == \
            bytes([13, 36, 1, 2, 9, 5]) + bytes(46)

    def test_reo_defaults(self):
        assert encode(ISP_REO()) == bytes([13, 36, 0, 0]) + bytes(48)

    def test_hcp_un_coche(self):
        # 4 cabecera + 32×CarHCP(2B) = 68 bytes (Size 17); Type HCP = 56.
        # El resto de coches se rellena con CarHCP() por defecto (0, 0).
        assert encode(ISP_HCP(Info=[CarHCP(30, 30)])) == \
            bytes([17, 56, 0, 0, 30, 30]) + bytes(62)

    def test_ipb_sin_bans_funciona(self):
        assert encode(ISP_IPB()) == b'\x02C\x00\x00\x00\x00\x00\x00'

    def test_ipb_con_un_ban(self):
        # 8 cabecera + 1 IP ('4B') = 12 bytes (Size 3); Type IPB = 67
        assert encode(ISP_IPB(NumB=1, BanIPs=[(192, 168, 1, 1)])) == \
            bytes([3, 67, 0, 1, 0, 0, 0, 0, 192, 168, 1, 1])
