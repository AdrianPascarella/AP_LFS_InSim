"""
_cmds_request.py - Comandos que envian un TINY/SMALL de peticion
y muestran la respuesta cuando LFS la devuelve.
Cubre: VER, STA, ISM, RST, AXI, NLP, NCI, MAL, PLH, IPB, RIP, PING.
"""
from lfs_insim.packets import *
from lfs_insim.utils import CMDManager, TextColors as c


def _ms(secs: int) -> str:
    """Convierte milisegundos a MM:SS.mmm."""
    m, s = divmod(secs // 1000, 60)
    return f"{m:02d}:{s:02d}.{secs % 1000:03d}"


class _RequestMixin:

    def _reg_request_cmds(self, cmds: CMDManager) -> None:
        (cmds
         .add_cmd("ver",  "Solicita ISP_VER (version LFS)",        None, self._cmd_ver,  is_mso_required=False)
         .add_cmd("sta",  "Solicita ISP_STA (estado del juego)",   None, self._cmd_sta,  is_mso_required=False)
         .add_cmd("ism",  "Solicita ISP_ISM (info multijugador)",  None, self._cmd_ism,  is_mso_required=False)
         .add_cmd("rst",  "Solicita ISP_RST (configuracion carrera)", None, self._cmd_rst, is_mso_required=False)
         .add_cmd("axi",  "Solicita ISP_AXI (info layout autocross)", None, self._cmd_axi, is_mso_required=False)
         .add_cmd("nlp",  "Solicita ISP_NLP (nodo/vuelta de coches)", None, self._cmd_nlp, is_mso_required=False)
         .add_cmd("nci",  "Solicita ISP_NCI (info extra conexiones)", None, self._cmd_nci, is_mso_required=False)
         .add_cmd("mal",  "Solicita ISP_MAL (mods permitidos)",    None, self._cmd_mal,  is_mso_required=False)
         .add_cmd("plh",  "Solicita ISP_PLH (handicaps jugadores)", None, self._cmd_plh,  is_mso_required=False)
         .add_cmd("ipb",  "Solicita ISP_IPB (IPs baneadas)",       None, self._cmd_ipb,  is_mso_required=False)
         .add_cmd("rip",  "Solicita ISP_RIP (info replay)",        None, self._cmd_rip,  is_mso_required=False)
         .add_cmd("ping", "Envia TINY_PING y espera TINY_REPLY",   None, self._cmd_ping, is_mso_required=False)
        )

    # --- Comandos ---

    def _cmd_ver(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.VER)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[VER] Peticion enviada...")

    def _cmd_sta(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.SST)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[STA] Peticion enviada...")

    def _cmd_ism(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.ISM)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[ISM] Peticion enviada...")

    def _cmd_rst(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.RST)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[RST] Peticion enviada...")

    def _cmd_axi(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.AXI)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[AXI] Peticion enviada...")

    def _cmd_nlp(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NLP)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[NLP] Peticion enviada...")

    def _cmd_nci(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NCI)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[NCI] Peticion enviada...")

    def _cmd_mal(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.MAL)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[MAL] Peticion enviada...")

    def _cmd_plh(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.PLH)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[PLH] Peticion enviada...")

    def _cmd_ipb(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.IPB)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[IPB] Peticion enviada...")

    def _cmd_rip(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.RIP)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[RIP] Peticion enviada...")

    def _cmd_ping(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.PING)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}[TINY_PING] Enviado, esperando TINY_REPLY...")

    # --- Handlers de respuesta ---

    def on_ISP_VER(self, packet: ISP_VER):
        self.send_ISP_MSL(Msg=f"{c.GREEN}[VER] {packet.Product} v{packet.Version} InSimVer={packet.InSimVer}")

    def on_ISP_STA(self, packet: ISP_STA):
        race = {0: "Sin carrera", 1: "Carrera", 2: "Clasificacion"}.get(int(packet.RaceInProg), "?")
        self.send_ISP_MSL(Msg=f"{c.GREEN}[STA] {packet.Track} | {race} | {packet.NumP}j {packet.NumConns}c")

    def on_ISP_ISM(self, packet: ISP_ISM):
        role = "Host" if packet.Host else "Guest"
        self.send_ISP_MSL(Msg=f"{c.GREEN}[ISM] {role}: {packet.Hname}")

    def on_ISP_RST(self, packet: ISP_RST):
        self.send_ISP_MSL(Msg=f"{c.GREEN}[RST] {packet.Track} | Vueltas={packet.RaceLaps} | Coches={packet.NumP}")

    def on_ISP_AXI(self, packet: ISP_AXI):
        name = packet.LName or "(sin layout)"
        self.send_ISP_MSL(Msg=f"{c.GREEN}[AXI] '{name}' | Objetos={packet.NumO} | CPs={packet.NumCP}")

    def on_ISP_NLP(self, packet: ISP_NLP):
        self.send_ISP_MSL(Msg=f"{c.GREEN}[NLP] {packet.NumP} coches:")
        for info in packet.Info:
            self.send_ISP_MSL(Msg=f"  PLID {info.PLID} | Nodo {info.Node} | Vuelta {info.Lap} | Pos {info.Position}")

    def on_ISP_NCI(self, packet: ISP_NCI):
        ip = f"{(packet.IPAddress >> 24) & 0xFF}.{(packet.IPAddress >> 16) & 0xFF}.{(packet.IPAddress >> 8) & 0xFF}.{packet.IPAddress & 0xFF}"
        self.send_ISP_MSL(Msg=f"{c.GREEN}[NCI] UCID {packet.UCID} | UserID={packet.UserID} | IP={ip}")

    def on_ISP_MAL(self, packet: ISP_MAL):
        self.send_ISP_MSL(Msg=f"{c.GREEN}[MAL] {packet.NumM} mods permitidos")

    def on_ISP_PLH(self, packet: ISP_PLH):
        self.send_ISP_MSL(Msg=f"{c.GREEN}[PLH] {packet.NumP} handicaps recibidos")

    def on_ISP_IPB(self, packet: ISP_IPB):
        self.send_ISP_MSL(Msg=f"{c.GREEN}[IPB] {packet.NumB} IPs baneadas")

    def on_ISP_RIP(self, packet: ISP_RIP):
        playing = "reproduciendo" if packet.MPR else "no replay"
        self.send_ISP_MSL(Msg=f"{c.GREEN}[RIP] {playing} | '{packet.RName}' | Error={int(packet.Error)}")

    def on_ISP_TINY(self, packet: ISP_TINY):
        if packet.SubT == TINY.REPLY:
            self.send_ISP_MSL(Msg=f"{c.GREEN}[TINY_REPLY] OK - conexion activa")
