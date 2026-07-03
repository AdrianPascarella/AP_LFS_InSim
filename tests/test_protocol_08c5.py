"""Tests de los cambios de protocolo LFS 0.8A → 0.8C5 (InSim v10).

Cubre: ISP_SET (nuevo paquete 70), ISF.SET, NPL.RIFlags (antes Sp2) + RIF/SAI,
CCI.RETIRED, NLP_MAX_CARS=48 y los nuevos HOSTF.
"""

import struct

from lfs_insim.insim_enums import (
    CCI,
    HOSTF,
    ISF,
    ISP,
    LFS_LIMITS,
    RIF,
    RIF_SAI_SHIFTS,
    SAI,
)
from lfs_insim.insim_packet_decoders import decode_packet
from lfs_insim.packets import INSIM_PACKETS, ISP_NPL, ISP_SET


class TestEnums08C5:
    def test_isp_set_es_70(self):
        assert ISP.SET == 70

    def test_isf_set_es_bit_12(self):
        assert ISF.SET == 0x1000

    def test_cci_retired_es_8(self):
        assert CCI.RETIRED == 8

    def test_nlp_max_cars_es_48(self):
        assert LFS_LIMITS.NLP_MAX_CARS == 48

    def test_hostf_nuevos_valores(self):
        assert HOSTF.SHOW_FUEL == 0x400
        assert HOSTF.CAN_REFUEL == 0x800
        assert HOSTF.ALLOW_MODS == 0x1000
        assert HOSTF.UNAPPROVED == 0x2000
        assert HOSTF.TEAMARROWS == 0x4000
        assert HOSTF.NO_FLOOD == 0x8000

    def test_rif_valores(self):
        assert RIF.LATE_START == 1
        assert RIF.SAI_NON_SOLID == 8
        assert RIF.SAI_MASK == 0x30

    def test_sai_type_derivado_de_riflags(self):
        # SAIType = (RIFlags & RIF.SAI_MASK) >> RIF_SAI_SHIFTS
        riflags = RIF.SAI_0 | RIF.SAI_1  # 0x30
        assert SAI((riflags & RIF.SAI_MASK) >> RIF_SAI_SHIFTS) == SAI.ANGLE
        riflags = RIF.SAI_1  # 0x20
        assert SAI((riflags & RIF.SAI_MASK) >> RIF_SAI_SHIFTS) == SAI.GROUND
        assert SAI((0 & RIF.SAI_MASK) >> RIF_SAI_SHIFTS) == SAI.MOVE


class TestISPSet:
    def test_registrado_en_insim_packets(self):
        assert INSIM_PACKETS[70] is ISP_SET

    def test_tamano_es_136_bytes(self):
        # Spec: Size = 136 (4 cabecera + 4 CName + 4 Spare + 4 fuel/spares + 120 setup)
        assert ISP_SET().get_size() == 136

    def test_decode_desde_bytes(self):
        setup = bytes(range(120))
        data = (
            bytes([136 // 4, 70, 0, 5])  # Size, Type=ISP_SET, ReqI, PLID=5
            + b"XRT\x00"  # CName (skin prefix)
            + struct.pack("<I", 0)  # Spare
            + bytes([55, 0, 0, 0])  # FuelLoad=55, Sp1-3
            + setup  # Setup[120]
        )
        assert len(data) == 136

        pkt = decode_packet(data)
        assert isinstance(pkt, ISP_SET)
        assert pkt.PLID == 5
        assert pkt.CName == "XRT"
        assert pkt.FuelLoad == 55
        assert pkt.Setup == list(range(120))


class TestNPLRIFlags:
    def test_npl_tiene_riflags_en_lugar_de_sp2(self):
        campos = list(ISP_NPL.metadata_to_dict().keys())
        assert "RIFlags" in campos
        assert "Sp2" not in campos
        # Posición según la spec: ... RWAdj, FWAdj, RIFlags, Sp3, SetF ...
        i = campos.index("RIFlags")
        assert campos[i - 1] == "FWAdj"
        assert campos[i + 1] == "Sp3"

    def test_npl_conserva_su_tamano(self):
        # El rename Sp2→RIFlags no cambia el layout binario (76 bytes)
        assert ISP_NPL().get_size() == 76
