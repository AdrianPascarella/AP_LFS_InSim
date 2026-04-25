"""
_cmds_send.py - Comandos que envian paquetes de instruccion a LFS.
Cubre: MSL, MST, MSX, MTC, BTN, BFN, SCC, SSH, SMALL,
       SCH, SFP, HCP, OCO, TTC, PLC.
"""
from lfs_insim.packets import *
from lfs_insim.utils import CMDManager, TextColors as c

_BTN_ID = 200  # ClickID reservado para el boton de prueba


class _SendMixin:

    def _reg_send_cmds(self, cmds: CMDManager) -> None:
        (cmds
         .add_cmd("msl",   "Envia ISP_MSL (mensaje local con sonido)",     None, self._cmd_msl,   is_mso_required=False)
         .add_cmd("mst",   "Envia ISP_MST (escribe como servidor)",         None, self._cmd_mst,   is_mso_required=False)
         .add_cmd("msx",   "Envia ISP_MSX (mensaje extendido servidor)",    None, self._cmd_msx,   is_mso_required=False)
         .add_cmd("mtc",   "Envia ISP_MTC (mensaje a UCID 0 local)",        None, self._cmd_mtc,   is_mso_required=False)
         .add_cmd("btn",   "Envia ISP_BTN (muestra boton de prueba)",       None, self._cmd_btn,   is_mso_required=False)
         .add_cmd("bfn",   "Envia ISP_BFN (elimina todos los botones)",     None, self._cmd_bfn,   is_mso_required=False)
         .add_cmd("scc",   "Envia ISP_SCC (cambia camara a TV)",            None, self._cmd_scc,   is_mso_required=False)
         .add_cmd("ssh",   "Envia ISP_SSH (captura pantalla)",              None, self._cmd_ssh,   is_mso_required=False)
         .add_cmd("small", "Envia ISP_SMALL (SMALL_NLI, intervalo NLP=200)", None, self._cmd_small, is_mso_required=False)
         .add_cmd("sch",   "Envia ISP_SCH (simula tecla 'T' del teclado)",  None, self._cmd_sch,   is_mso_required=False)
         .add_cmd("sfp",   "Envia ISP_SFP (activa/desactiva vista 2D)",     None, self._cmd_sfp,   is_mso_required=False)
         .add_cmd("hcp",   "Envia ISP_HCP (reinicia handicaps a 0)",        None, self._cmd_hcp,   is_mso_required=False)
         .add_cmd("oco",   "Envia ISP_OCO (resetea luces de semaforo)",     None, self._cmd_oco,   is_mso_required=False)
         .add_cmd("ttc",   "Envia ISP_TTC (pide AXM de seleccion layout)",  None, self._cmd_ttc,   is_mso_required=False)
         .add_cmd("plc",   "Envia ISP_PLC (sin restriccion de coches)",     None, self._cmd_plc,   is_mso_required=False)
        )

    def _cmd_msl(self):
        self.send_ISP_MSL(Msg=f"{c.GREEN}[MSL] {c.WHITE}Mensaje de prueba ISP_MSL", Sound=SND.SYSMESSAGE)
        self.logger.info("TEST MSL enviado")

    def _cmd_mst(self):
        self.send_ISP_MST(Msg="/say [MST] Mensaje de prueba ISP_MST")
        self.send_ISP_MSL(Msg=f"{c.GREEN}[MST] {c.WHITE}ISP_MST enviado")

    def _cmd_msx(self):
        self.send_ISP_MSX(Msg="[MSX] Mensaje extendido de prueba ISP_MSX - hasta 96 chars")
        self.send_ISP_MSL(Msg=f"{c.GREEN}[MSX] {c.WHITE}ISP_MSX enviado")

    def _cmd_mtc(self):
        self.send_ISP_MTC(UCID=0, PLID=0, Text=f"[MTC] Mensaje de prueba ISP_MTC a UCID=0")
        self.send_ISP_MSL(Msg=f"{c.GREEN}[MTC] {c.WHITE}ISP_MTC enviado a UCID=0")

    def _cmd_btn(self):
        self.send_ISP_BTN(
            ReqI=1,
            UCID=0,
            ClickID=_BTN_ID,
            BStyle=ISB_STYLE.DARK,
            L=40, T=80, W=120, H=30,
            Text=f"^2[BTN] Prueba OK - usa !test_insim bfn para borrar",
        )
        self.send_ISP_MSL(Msg=f"{c.GREEN}[BTN] {c.WHITE}Boton mostrado (ClickID={_BTN_ID})")

    def _cmd_bfn(self):
        self.send_ISP_BFN(SubT=BFN.DEL_BTN, UCID=0, ClickID=_BTN_ID)
        self.send_ISP_MSL(Msg=f"{c.GREEN}[BFN] {c.WHITE}Boton eliminado (ClickID={_BTN_ID})")

    def _cmd_scc(self):
        self.send_ISP_SCC(ViewPLID=0, InGameCam=VIEW.HELI)
        self.send_ISP_MSL(Msg=f"{c.GREEN}[SCC] {c.WHITE}Camara cambiada a HELI")

    def _cmd_ssh(self):
        self.send_ISP_SSH(ReqI=1, Name="test_insim_screenshot")
        self.send_ISP_MSL(Msg=f"{c.GREEN}[SSH] {c.WHITE}Screenshot solicitado")

    def _cmd_small(self):
        self.send_ISP_SMALL(SubT=SMALL.NLI, UVal=200)
        self.send_ISP_MSL(Msg=f"{c.GREEN}[SMALL] {c.WHITE}SMALL_NLI enviado (intervalo NLP=200ms)")

    def _cmd_sch(self):
        self.send_ISP_SCH(CharB=ord('9'), Flags=SCH_FLAGS.NONE)
        self.send_ISP_MSL(Msg=f"{c.GREEN}[SCH] {c.WHITE}Tecla '9' simulada")

    def _cmd_sfp(self):
        self.send_ISP_SFP(Flag=ISS_SFP.SHOW_2D, OffOn=OFFON.ON)
        self.send_ISP_MSL(Msg=f"{c.GREEN}[SFP] {c.WHITE}Vista 2D activada (ISS_SHOW_2D ON)")

    def _cmd_hcp(self):
        self.send_ISP_HCP(Info=[CarHCP(30, 30)])
        self.send_ISP_MSL(Msg=f"{c.GREEN}[HCP] {c.WHITE}Handicaps reseteados a 0 para todos los coches")

    def _cmd_oco(self):
        self.send_ISP_OCO(OCOAction=OCO.LIGHTS_RESET, Index=0, Identifier=0, Data=0)
        self.send_ISP_MSL(Msg=f"{c.GREEN}[OCO] {c.WHITE}Luces reseteadas (LIGHTS_RESET)")

    def _cmd_ttc(self):
        self.send_ISP_TTC(SubT=TTC.SEL, UCID=0)
        self.send_ISP_MSL(Msg=f"{c.GREEN}[TTC] {c.WHITE}TTC_SEL enviado a UCID=0 (pide AXM de seleccion)")

    def _cmd_plc(self):
        self.send_ISP_PLC(UCID=0, Cars=0)
        self.send_ISP_MSL(Msg=f"{c.GREEN}[PLC] {c.WHITE}Sin restriccion de coches para UCID=0 (Cars=0)")

    def on_ISP_SSH(self, packet: ISP_SSH):
        if packet.ReqI:
            status = "OK" if packet.Error == 0 else f"Error={int(packet.Error)}"
            self.send_ISP_MSL(Msg=f"{c.GREEN}[SSH] {c.WHITE}Screenshot: {status} | '{packet.Name}'")

    def on_ISP_BTC(self, packet: ISP_BTC):
        self.send_ISP_MSL(Msg=f"{c.GREEN}[BTC] {c.WHITE}Click en boton ID={packet.ClickID} UCID={packet.UCID}")

    def on_ISP_BTT(self, packet: ISP_BTT):
        self.send_ISP_MSL(Msg=f"{c.GREEN}[BTT] {c.WHITE}Texto en boton ID={packet.ClickID}: '{packet.Text[:40]}'")
