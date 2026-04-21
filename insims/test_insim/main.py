from lfs_insim import InSimApp
from lfs_insim.packets import *
from lfs_insim.insim_enums import ISF, TINY


class TestInsim(InSimApp):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"Modulo {self.name} inicializado.")

    def set_isi_packet(self):
        super().set_isi_packet()
        # Añade aqui los flags ISF que necesites, por ejemplo:
        # self.isi.Flags |= ISF.LOCAL | ISF.MCI

    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NCN)
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NPL)

    def on_disconnect(self):
        self.logger.info(f"Modulo {self.name} desconectado.")
