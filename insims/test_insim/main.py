from lfs_insim import InSimApp
from lfs_insim.packets import *
from lfs_insim.insim_enums import ISF
from lfs_insim.utils import CMDManager, separate_command_args


class TestInsim(InSimApp):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd_prefix: str = self.config.get("prefix", "!")
        self.cmd_base: str = "test_insim"
        self.cmds: CMDManager
        self.logger.info(f"Modulo {self.name} inicializado.")

    def set_isi_packet(self):
        super().set_isi_packet()
        # Añade aqui los flags ISF que necesites, por ejemplo:
        # self.isi.Flags |= ISF.LOCAL | ISF.MCI

    def on_connect(self):
        self.cmds = (
            CMDManager(self.cmd_prefix, self.cmd_base)
            .add_cmd(
                name="hola",
                description="Saluda al servidor",
                args=None,
                funct=self._cmd_hola,
            )
            .submit()
        )
        self.send_ISP_MSL(Msg=f"^2{self.name} ^7conectado")

    def on_ISP_MSO(self, packet: ISP_MSO):
        cmd, args = separate_command_args(self.cmd_prefix, packet)
        if cmd == self.cmd_base:
            self.cmds.handle_commands(packet, args)

    def _cmd_hola(self):
        self.send_ISP_MSL(Msg="^2Hola desde test_insim!")

    def on_disconnect(self):
        self.logger.info(f"Modulo {self.name} desconectado.")
