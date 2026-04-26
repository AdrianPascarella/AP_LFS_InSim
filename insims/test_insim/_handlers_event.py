"""
_handlers_event.py - Handlers para paquetes que solo llegan por eventos.
Guarda el ultimo paquete recibido de cada tipo y lo muestra con un comando.
Cubre: CPR, LAP, SPX, PIT, PSF, PLA, CCH, PEN, TOC, FLG, PFL, FIN, RES,
       CRS, AXO, CON, OBH, HLV, UCO, SLC, CSC, CIM, VTN, III, ACR, AXM, PLP.
"""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from lfs_insim.packets import *
from lfs_insim.utils import CMDManager, TextColors as c
from lfs_insim.insim_enums import (
    PITLANE, VIEW, PENALTY, PENR, BYF, OFFON, VOTE,
    CIM, CSC, UCO, PMO, RESULT, HLVC, AXO_INDEX, OBH,
)

if TYPE_CHECKING:
    from lfs_insim import InSimApp as _Base
else:
    _Base = object


def _en(enum_cls, val):
    """Devuelve el nombre del enum o el valor numérico si no existe."""
    try:
        return enum_cls(val).name
    except ValueError:
        return str(int(val))


def _ms(ms: int) -> str:
    m, s = divmod(ms // 1000, 60)
    return f"{m:02d}:{s:02d}.{ms % 1000:03d}"


def _no_event(name: str) -> str:
    return f"{c.YELLOW}[{name}] Sin eventos recibidos aun."


class _EventMixin(_Base):

    def _init_event_state(self) -> None:
        self._last_cpr: Optional[ISP_CPR] = None
        self._last_lap: Optional[ISP_LAP] = None
        self._last_spx: Optional[ISP_SPX] = None
        self._last_pit: Optional[ISP_PIT] = None
        self._last_psf: Optional[ISP_PSF] = None
        self._last_pla: Optional[ISP_PLA] = None
        self._last_cch: Optional[ISP_CCH] = None
        self._last_pen: Optional[ISP_PEN] = None
        self._last_toc: Optional[ISP_TOC] = None
        self._last_flg: Optional[ISP_FLG] = None
        self._last_pfl: Optional[ISP_PFL] = None
        self._last_fin: Optional[ISP_FIN] = None
        self._last_res: Optional[ISP_RES] = None
        self._last_crs: Optional[ISP_CRS] = None
        self._last_axo: Optional[ISP_AXO] = None
        self._last_con: Optional[ISP_CON] = None
        self._last_obh: Optional[ISP_OBH] = None
        self._last_hlv: Optional[ISP_HLV] = None
        self._last_uco: Optional[ISP_UCO] = None
        self._last_slc: Optional[ISP_SLC] = None
        self._last_csc: Optional[ISP_CSC] = None
        self._last_cim: Optional[ISP_CIM] = None
        self._last_vtn: Optional[ISP_VTN] = None
        self._last_iii: Optional[ISP_III] = None
        self._last_acr: Optional[ISP_ACR] = None
        self._last_axm: Optional[ISP_AXM] = None
        self._last_plp: Optional[ISP_PLP] = None

    def _reg_event_cmds(self, cmds: CMDManager) -> None:
        (cmds
         .add_cmd("cpr",  "Ultimo ISP_CPR (renombrar jugador)",      None, self._cmd_cpr,  is_mso_required=False)
         .add_cmd("lap",  "Ultimo ISP_LAP (tiempo de vuelta)",       None, self._cmd_lap,  is_mso_required=False)
         .add_cmd("spx",  "Ultimo ISP_SPX (tiempo de sector)",       None, self._cmd_spx,  is_mso_required=False)
         .add_cmd("pit",  "Ultimo ISP_PIT (inicio parada en boxes)", None, self._cmd_pit,  is_mso_required=False)
         .add_cmd("psf",  "Ultimo ISP_PSF (fin parada en boxes)",    None, self._cmd_psf,  is_mso_required=False)
         .add_cmd("pla",  "Ultimo ISP_PLA (pit lane entrada/salida)", None, self._cmd_pla,  is_mso_required=False)
         .add_cmd("cch",  "Ultimo ISP_CCH (camara cambiada)",        None, self._cmd_cch,  is_mso_required=False)
         .add_cmd("pen",  "Ultimo ISP_PEN (penalizacion)",           None, self._cmd_pen,  is_mso_required=False)
         .add_cmd("toc",  "Ultimo ISP_TOC (cambio de piloto)",       None, self._cmd_toc,  is_mso_required=False)
         .add_cmd("flg",  "Ultimo ISP_FLG (bandera)",                None, self._cmd_flg,  is_mso_required=False)
         .add_cmd("pfl",  "Ultimo ISP_PFL (flags del jugador)",      None, self._cmd_pfl,  is_mso_required=False)
         .add_cmd("fin",  "Ultimo ISP_FIN (cruzar linea de meta)",   None, self._cmd_fin,  is_mso_required=False)
         .add_cmd("res",  "Ultimo ISP_RES (resultado confirmado)",   None, self._cmd_res,  is_mso_required=False)
         .add_cmd("crs",  "Ultimo ISP_CRS (reset del coche)",        None, self._cmd_crs,  is_mso_required=False)
         .add_cmd("axo",  "Ultimo ISP_AXO (golpe objeto autocross)", None, self._cmd_axo,  is_mso_required=False)
         .add_cmd("con",  "Ultimo ISP_CON (colision coche-coche)",   None, self._cmd_con,  is_mso_required=False)
         .add_cmd("obh",  "Ultimo ISP_OBH (colision coche-objeto)",  None, self._cmd_obh,  is_mso_required=False)
         .add_cmd("hlv",  "Ultimo ISP_HLV (infraccion HLVC)",        None, self._cmd_hlv,  is_mso_required=False)
         .add_cmd("uco",  "Ultimo ISP_UCO (checkpoint InSim)",       None, self._cmd_uco,  is_mso_required=False)
         .add_cmd("slc",  "Ultimo ISP_SLC (coche seleccionado)",     None, self._cmd_slc,  is_mso_required=False)
         .add_cmd("csc",  "Ultimo ISP_CSC (estado del coche)",       None, self._cmd_csc,  is_mso_required=False)
         .add_cmd("cim",  "Ultimo ISP_CIM (modo interfaz)",          None, self._cmd_cim,  is_mso_required=False)
         .add_cmd("vtn",  "Ultimo ISP_VTN (voto)",                   None, self._cmd_vtn,  is_mso_required=False)
         .add_cmd("iii",  "Ultimo ISP_III (mensaje InSim info)",     None, self._cmd_iii,  is_mso_required=False)
         .add_cmd("acr",  "Ultimo ISP_ACR (comando admin)",          None, self._cmd_acr,  is_mso_required=False)
         .add_cmd("axm",  "Ultimo ISP_AXM (objeto layout)",          None, self._cmd_axm,  is_mso_required=False)
         .add_cmd("plp",  "Ultimo ISP_PLP (jugador a espectador)",  None, self._cmd_plp,  is_mso_required=False)
        )

    # --- Handlers ---

    def on_ISP_CPR(self, packet: ISP_CPR):
        self._last_cpr = packet
        self.logger.info(f"CPR: UCID {packet.UCID} -> '{packet.PName}' | Plate='{packet.Plate}'")

    def on_ISP_LAP(self, packet: ISP_LAP):
        self._last_lap = packet
        self.logger.info(f"LAP: PLID {packet.PLIP} | LTime={_ms(packet.LTime)} | Vuelta {packet.LapsDone}")

    def on_ISP_SPX(self, packet: ISP_SPX):
        self._last_spx = packet
        self.logger.info(f"SPX: PLID {packet.PLIP} | STime={_ms(packet.STime)} | Split {packet.Split}")

    def on_ISP_PIT(self, packet: ISP_PIT):
        self._last_pit = packet
        self.logger.info(f"PIT: PLID {packet.PLID} | Vuelta {packet.LapsDone} | FuelAdd={packet.FuelAdd}")

    def on_ISP_PSF(self, packet: ISP_PSF):
        self._last_psf = packet
        self.logger.info(f"PSF: PLID {packet.PLID} | STime={_ms(packet.STime)}")

    def on_ISP_PLA(self, packet: ISP_PLA):
        self._last_pla = packet
        self.logger.info(f"PLA: PLID {packet.PLID} | Fact={_en(PITLANE, packet.Fact)}")

    def on_ISP_CCH(self, packet: ISP_CCH):
        self._last_cch = packet
        self.logger.info(f"CCH: PLID {packet.PLID} | Camera={_en(VIEW, packet.Camera)}")

    def on_ISP_PEN(self, packet: ISP_PEN):
        self._last_pen = packet
        self.logger.info(f"PEN: PLID {packet.PLID} | {_en(PENALTY, packet.OldPen)}->{_en(PENALTY, packet.NewPen)} Reason={_en(PENR, packet.Reason)}")

    def on_ISP_TOC(self, packet: ISP_TOC):
        self._last_toc = packet
        self.logger.info(f"TOC: PLID {packet.PLID} | UCID {packet.OldUCID}->{packet.NewUCID}")

    def on_ISP_FLG(self, packet: ISP_FLG):
        self._last_flg = packet
        self.logger.info(f"FLG: PLID {packet.PLID} | {_en(BYF, packet.Flag)} {'ON' if packet.OffOn == OFFON.ON else 'OFF'}")

    def on_ISP_PFL(self, packet: ISP_PFL):
        self._last_pfl = packet
        self.logger.info(f"PFL: PLID {packet.PLID} | Flags={int(packet.Flags):#06x}")

    def on_ISP_FIN(self, packet: ISP_FIN):
        self._last_fin = packet
        self.logger.info(f"FIN: PLID {packet.PLID} | TTime={_ms(packet.TTime)} | Vueltas={packet.LapsDone}")

    def on_ISP_RES(self, packet: ISP_RES):
        self._last_res = packet
        self.logger.info(f"RES: PLID {packet.PLID} | {packet.Pname} | TTime={_ms(packet.TTime)} | Pos={packet.ResultNum}")

    def on_ISP_CRS(self, packet: ISP_CRS):
        self._last_crs = packet
        self.logger.info(f"CRS: PLID {packet.PLID} reset del coche")

    def on_ISP_AXO(self, packet: ISP_AXO):
        self._last_axo = packet
        self.logger.info(f"AXO: PLID {packet.PLID} golpeo un objeto autocross")

    def on_ISP_CON(self, packet: ISP_CON):
        self._last_con = packet
        self.logger.info(f"CON: PLID {packet.A.PLID} vs PLID {packet.B.PLID} | SpClose={packet.SpClose}")

    def on_ISP_OBH(self, packet: ISP_OBH):
        self._last_obh = packet
        self.logger.info(f"OBH: PLID {packet.PLID} golpeo objeto Index={_en(AXO_INDEX, packet.Index)}")

    def on_ISP_HLV(self, packet: ISP_HLV):
        self._last_hlv = packet
        self.logger.info(f"HLV: PLID {packet.PLID} | HLVC={_en(HLVC, packet.HLVC)}")

    def on_ISP_UCO(self, packet: ISP_UCO):
        self._last_uco = packet
        self.logger.info(f"UCO: PLID {packet.PLID} | Action={_en(UCO, packet.UCOAction)}")

    def on_ISP_SLC(self, packet: ISP_SLC):
        self._last_slc = packet
        self.logger.info(f"SLC: UCID {packet.UCID} selecciono coche '{packet.CName}'")

    def on_ISP_CSC(self, packet: ISP_CSC):
        self._last_csc = packet
        self.logger.info(f"CSC: UCID {packet.UCID} | Action={_en(CSC, packet.CSCAction)}")

    def on_ISP_CIM(self, packet: ISP_CIM):
        self._last_cim = packet
        self.logger.info(f"CIM: UCID {packet.UCID} | Mode={_en(CIM, packet.Mode)} SubMode={int(packet.SubMode)}")

    def on_ISP_VTN(self, packet: ISP_VTN):
        self._last_vtn = packet
        self.logger.info(f"VTN: UCID {packet.UCID} | Action={_en(VOTE, packet.Action)}")

    def on_ISP_III(self, packet: ISP_III):
        self._last_iii = packet
        self.logger.info(f"III: UCID {packet.UCID} PLID {packet.PLID} | '{packet.Msg[:40]}'")

    def on_ISP_ACR(self, packet: ISP_ACR):
        self._last_acr = packet
        self.logger.info(f"ACR: UCID {packet.UCID} | Result={_en(RESULT, packet.Result)} | '{packet.Text[:40]}'")

    def on_ISP_AXM(self, packet: ISP_AXM):
        self._last_axm = packet
        self.logger.info(f"AXM: {packet.NumO} objetos | Action={_en(PMO, packet.PMOAction)}")

    def on_ISP_PLP(self, packet: ISP_PLP):
        self._last_plp = packet
        self.logger.info(f"PLP: PLID {packet.PLID} paso a espectador")

    # --- Comandos de display ---

    def _cmd_cpr(self):
        p = self._last_cpr
        if not p: self.send_ISP_MSL(Msg=_no_event("CPR")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[CPR] UCID {p.UCID} -> '{p.PName}' | Plate='{p.Plate}'")

    def _cmd_lap(self):
        p = self._last_lap
        if not p: self.send_ISP_MSL(Msg=_no_event("LAP")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[LAP] PLID {p.PLIP} | {_ms(p.LTime)} | Vuelta {p.LapsDone}")

    def _cmd_spx(self):
        p = self._last_spx
        if not p: self.send_ISP_MSL(Msg=_no_event("SPX")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[SPX] PLID {p.PLIP} | {_ms(p.STime)} | Split {p.Split}")

    def _cmd_pit(self):
        p = self._last_pit
        if not p: self.send_ISP_MSL(Msg=_no_event("PIT")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[PIT] PLID {p.PLID} | Vuelta {p.LapsDone} | Fuel+{p.FuelAdd}")

    def _cmd_psf(self):
        p = self._last_psf
        if not p: self.send_ISP_MSL(Msg=_no_event("PSF")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[PSF] PLID {p.PLID} | Tiempo en boxes: {_ms(p.STime)}")

    def _cmd_pla(self):
        p = self._last_pla
        if not p: self.send_ISP_MSL(Msg=_no_event("PLA")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[PLA] PLID {p.PLID} | {_en(PITLANE, p.Fact)}")

    def _cmd_cch(self):
        p = self._last_cch
        if not p: self.send_ISP_MSL(Msg=_no_event("CCH")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[CCH] PLID {p.PLID} | Camera={_en(VIEW, p.Camera)}")

    def _cmd_pen(self):
        p = self._last_pen
        if not p: self.send_ISP_MSL(Msg=_no_event("PEN")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[PEN] PLID {p.PLID} | {_en(PENALTY, p.OldPen)}->{_en(PENALTY, p.NewPen)} Reason={_en(PENR, p.Reason)}")

    def _cmd_toc(self):
        p = self._last_toc
        if not p: self.send_ISP_MSL(Msg=_no_event("TOC")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[TOC] PLID {p.PLID} | UCID {p.OldUCID}->{p.NewUCID}")

    def _cmd_flg(self):
        p = self._last_flg
        if not p: self.send_ISP_MSL(Msg=_no_event("FLG")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[FLG] PLID {p.PLID} | {_en(BYF, p.Flag)} {_en(OFFON, p.OffOn)}")

    def _cmd_pfl(self):
        p = self._last_pfl
        if not p: self.send_ISP_MSL(Msg=_no_event("PFL")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[PFL] PLID {p.PLID} | Flags={int(p.Flags):#06x}")

    def _cmd_fin(self):
        p = self._last_fin
        if not p: self.send_ISP_MSL(Msg=_no_event("FIN")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[FIN] PLID {p.PLID} | {_ms(p.TTime)} | Vueltas {p.LapsDone}")

    def _cmd_res(self):
        p = self._last_res
        if not p: self.send_ISP_MSL(Msg=_no_event("RES")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[RES] PLID {p.PLID} | {p.Pname} | Pos {p.ResultNum} | {_ms(p.TTime)}")

    def _cmd_crs(self):
        p = self._last_crs
        if not p: self.send_ISP_MSL(Msg=_no_event("CRS")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[CRS] PLID {p.PLID} reseteo su coche")

    def _cmd_axo(self):
        p = self._last_axo
        if not p: self.send_ISP_MSL(Msg=_no_event("AXO")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[AXO] PLID {p.PLID} golpeo un objeto de autocross")

    def _cmd_con(self):
        p = self._last_con
        if not p: self.send_ISP_MSL(Msg=_no_event("CON")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[CON] PLID {p.A.PLID} vs PLID {p.B.PLID} | SpClose={p.SpClose}")

    def _cmd_obh(self):
        p = self._last_obh
        if not p: self.send_ISP_MSL(Msg=_no_event("OBH")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[OBH] PLID {p.PLID} | Index={_en(AXO_INDEX, p.Index)} | OBHFlags={p.OBHFlags!r}")

    def _cmd_hlv(self):
        p = self._last_hlv
        if not p: self.send_ISP_MSL(Msg=_no_event("HLV")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[HLV] PLID {p.PLID} | HLVC={_en(HLVC, p.HLVC)}")

    def _cmd_uco(self):
        p = self._last_uco
        if not p: self.send_ISP_MSL(Msg=_no_event("UCO")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[UCO] PLID {p.PLID} | Action={_en(UCO, p.UCOAction)}")

    def _cmd_slc(self):
        p = self._last_slc
        if not p: self.send_ISP_MSL(Msg=_no_event("SLC")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[SLC] UCID {p.UCID} | Coche='{p.CName}'")

    def _cmd_csc(self):
        p = self._last_csc
        if not p: self.send_ISP_MSL(Msg=_no_event("CSC")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[CSC] UCID {p.UCID} | Action={_en(CSC, p.CSCAction)}")

    def _cmd_cim(self):
        p = self._last_cim
        if not p: self.send_ISP_MSL(Msg=_no_event("CIM")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[CIM] UCID {p.UCID} | Mode={_en(CIM, p.Mode)} Sub={int(p.SubMode)}")

    def _cmd_vtn(self):
        p = self._last_vtn
        if not p: self.send_ISP_MSL(Msg=_no_event("VTN")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[VTN] UCID {p.UCID} | Action={_en(VOTE, p.Action)}")

    def _cmd_iii(self):
        p = self._last_iii
        if not p: self.send_ISP_MSL(Msg=_no_event("III")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[III] UCID {p.UCID} PLID {p.PLID} | '{p.Msg[:40]}'")

    def _cmd_acr(self):
        p = self._last_acr
        if not p: self.send_ISP_MSL(Msg=_no_event("ACR")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[ACR] UCID {p.UCID} | Result={_en(RESULT, p.Result)} | '{p.Text[:30]}'")

    def _cmd_axm(self):
        p = self._last_axm
        if not p: self.send_ISP_MSL(Msg=_no_event("AXM")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[AXM] {p.NumO} objetos | Action={_en(PMO, p.PMOAction)}")

    def _cmd_plp(self):
        p = self._last_plp
        if not p: self.send_ISP_MSL(Msg=_no_event("PLP")); return
        self.send_ISP_MSL(Msg=f"{c.GREEN}[PLP] PLID {p.PLID} paso a espectador")
