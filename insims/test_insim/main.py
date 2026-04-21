from lfs_insim import InSimApp
from lfs_insim.packets import *
from lfs_insim.insim_enums import ISF, PTYPE
from lfs_insim.utils import CMDManager, separate_command_args, TextColors as c

from ._cmds_request import _RequestMixin
from ._cmds_send import _SendMixin
from ._handlers_event import _EventMixin


class TestInsim(_RequestMixin, _SendMixin, _EventMixin, InSimApp):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd_prefix: str = self.config.get("prefix", "!")
        self.cmd_base: str = "test_insim"
        self.cmds: CMDManager

        # UCID -> {"uname": str, "pname": str, "plid": int | None}
        self.users: dict[int, dict] = {}
        # PLID -> {"ucid": int, "car": str, "plate": str, "is_ai": bool, "ai_name": str}
        self.players: dict[int, dict] = {}

        self._init_event_state()
        self.logger.info(f"Modulo {self.name} inicializado.")

    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= (
            ISF.LOCAL    |  # eventos de invitado/SP
            ISF.NLP      |  # paquetes NLP (nodo y vuelta)
            ISF.MCI      |  # paquetes MCI (telemetria detallada)
            ISF.CON      |  # colisiones coche-coche
            ISF.HLV      |  # infracciones HLVC
            ISF.AXM_LOAD |  # AXM al cargar layout
            ISF.AXM_EDIT    # AXM al editar objetos
        )

    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NCN)
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NPL)

        cmds = CMDManager(self.cmd_prefix, self.cmd_base)

        # comandos base: estado interno
        (cmds
         .add_cmd("users",   "Lista usuarios conectados",  None, self._cmd_users,   is_mso_required=False)
         .add_cmd("players", "Lista coches en pista",      None, self._cmd_players, is_mso_required=False)
        )

        # comandos de peticion request/response
        self._reg_request_cmds(cmds)

        # comandos de instruccion (enviar paquetes a LFS)
        self._reg_send_cmds(cmds)

        # comandos de eventos (muestra ultimo evento recibido)
        self._reg_event_cmds(cmds)

        self.cmds = cmds.submit()
        self.send_ISP_MSL(Msg=f"{c.GREEN}{self.name} {c.WHITE}conectado")

    # --- Conexiones ---

    def on_ISP_NCN(self, packet: ISP_NCN):
        self.users[packet.UCID] = {
            "uname": packet.UName,
            "pname": packet.PName,
            "plid": None,
        }
        self.logger.info(f"NCN: {packet.UName} (UCID {packet.UCID})")

    def on_ISP_CNL(self, packet: ISP_CNL):
        user = self.users.pop(packet.UCID, None)
        if user:
            self.logger.info(f"CNL: {user['uname']} (UCID {packet.UCID})")

    # --- Jugadores ---

    def on_ISP_NPL(self, packet: ISP_NPL):
        is_ai = bool(packet.PType & PTYPE.AI)
        self.players[packet.PLID] = {
            "ucid": packet.UCID,
            "car": packet.CName,
            "plate": packet.Plate,
            "is_ai": is_ai,
            "ai_name": packet.PName if is_ai else "",
        }
        if not is_ai and packet.UCID in self.users:
            self.users[packet.UCID]["plid"] = packet.PLID
        self.logger.info(f"NPL: {'AI ' + packet.PName if is_ai else packet.CName} (PLID {packet.PLID})")

    def on_ISP_PLL(self, packet: ISP_PLL):
        player = self.players.pop(packet.PLID, None)
        if player and not player["is_ai"] and player["ucid"] in self.users:
            self.users[player["ucid"]]["plid"] = None
        self.logger.info(f"PLL: PLID {packet.PLID} salio de pista")

    # --- Telemetria ---

    def on_ISP_MCI(self, packet: ISP_MCI):
        for car in packet.Info:
            if car.PLID in self.players:
                self.logger.debug(f"MCI PLID {car.PLID}: speed={car.Speed} node={car.Node} lap={car.Lap}")

    # --- Comandos base ---

    def on_ISP_MSO(self, packet: ISP_MSO):
        cmd, args = separate_command_args(self.cmd_prefix, packet)
        if cmd == self.cmd_base:
            self.cmds.handle_commands(packet, args)

    def _cmd_users(self):
        if not self.users:
            self.send_ISP_MSL(Msg=f"{c.YELLOW}No hay usuarios conectados.")
            return
        self.send_ISP_MSL(Msg=f"{c.WHITE}=== Usuarios ({len(self.users)}) ===")
        for ucid, u in self.users.items():
            status = f"{c.GREEN}En pista (PLID {u['plid']})" if u["plid"] else f"{c.YELLOW}Espectador"
            self.send_ISP_MSL(Msg=f"UCID {ucid} | {u['uname']} | {status}")

    def _cmd_players(self):
        if not self.players:
            self.send_ISP_MSL(Msg=f"{c.YELLOW}No hay coches en pista.")
            return
        self.send_ISP_MSL(Msg=f"{c.WHITE}=== Coches en pista ({len(self.players)}) ===")
        for plid, p in self.players.items():
            label = f"AI:{p['ai_name']}" if p["is_ai"] else p["plate"]
            self.send_ISP_MSL(Msg=f"PLID {plid} | {p['car']} | {label} | UCID {p['ucid']}")

    def on_disconnect(self):
        self.logger.info(f"Modulo {self.name} desconectado.")
