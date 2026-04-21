from .base import *
from .structures import *
from .insim import *
from .outsim import *
from .maps import INSIM_PACKETS

OUTSIM_PACKETS = {
    OutGaugePack().get_size(): OutGaugePack,
    OutSimPack().get_size(): OutSimPack,
    OutSimPack2().get_size(): OutSimPack2,
}

class RECEIVE:
    """Catálogo de recepción"""
    ISP_VER = ISP_VER
    ISP_TINY = ISP_TINY
    ISP_SMALL = ISP_SMALL
    ISP_STA = ISP_STA
    ISP_CPP = ISP_CPP
    ISP_ISM = ISP_ISM
    ISP_NCN = ISP_NCN
    ISP_CNL = ISP_CNL
    ISP_CPR = ISP_CPR
    ISP_NCI = ISP_NCI
    ISP_CIM = ISP_CIM
    ISP_SLC = ISP_SLC
    ISP_MSO = ISP_MSO
    ISP_III = ISP_III
    ISP_ACR = ISP_ACR
    ISP_VTN = ISP_VTN
    ISP_RST = ISP_RST
    ISP_NPL = ISP_NPL
    ISP_PLP = ISP_PLP
    ISP_PLL = ISP_PLL
    ISP_LAP = ISP_LAP
    ISP_SPX = ISP_SPX
    ISP_PIT = ISP_PIT
    ISP_PSF = ISP_PSF
    ISP_PLA = ISP_PLA
    ISP_CCH = ISP_CCH
    ISP_PEN = ISP_PEN
    ISP_TOC = ISP_TOC
    ISP_FLG = ISP_FLG
    ISP_PFL = ISP_PFL
    ISP_FIN = ISP_FIN
    ISP_RES = ISP_RES
    ISP_REO = ISP_REO
    ISP_CRS = ISP_CRS
    ISP_NLP = ISP_NLP
    ISP_MCI = ISP_MCI
    ISP_CON = ISP_CON
    ISP_OBH = ISP_OBH
    ISP_HLV = ISP_HLV
    ISP_CSC = ISP_CSC
    ISP_AII = ISP_AII
    ISP_UCO = ISP_UCO
    ISP_AXI = ISP_AXI
    ISP_AXO = ISP_AXO
    ISP_AXM = ISP_AXM
    ISP_BFN = ISP_BFN
    ISP_BTC = ISP_BTC
    ISP_BTT = ISP_BTT
    ISP_RIP = ISP_RIP
    ISP_SSH = ISP_SSH
    ISP_MAL = ISP_MAL
    ISP_PLH = ISP_PLH
    ISP_IPB = ISP_IPB
    OutGaugePack = OutGaugePack
    OutSimPack = OutSimPack
    OutSimPack2 = OutSimPack2

class SEND:
    """Catálogo de envío"""
    ISP_ISI = ISP_ISI
    ISP_TINY = ISP_TINY
    ISP_SMALL = ISP_SMALL
    ISP_SFP = ISP_SFP
    ISP_MOD = ISP_MOD
    ISP_SCC = ISP_SCC
    ISP_CPP = ISP_CPP
    ISP_SCH = ISP_SCH
    ISP_MST = ISP_MST
    ISP_MTC = ISP_MTC
    ISP_MSX = ISP_MSX
    ISP_MSL = ISP_MSL
    ISP_REO = ISP_REO
    ISP_PLC = ISP_PLC
    ISP_HCP = ISP_HCP
    ISP_JRR = ISP_JRR
    ISP_TTC = ISP_TTC
    ISP_AIC = ISP_AIC
    ISP_MAL = ISP_MAL
    ISP_PLH = ISP_PLH
    ISP_IPB = ISP_IPB
    ISP_AXM = ISP_AXM
    ISP_OCO = ISP_OCO
    ISP_BFN = ISP_BFN
    ISP_BTN = ISP_BTN
    ISP_RIP = ISP_RIP
    ISP_SSH = ISP_SSH

ALLOWED_PACKETS = tuple(
    valor for nombre, valor in vars(SEND).items() 
    if nombre.startswith("ISP_")
)
