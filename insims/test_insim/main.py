#!/usr/bin/env python3
"""
test_insim - InSim para Live for Speed.

Descripción de tu InSim aquí.
"""
import logging

from lfs_insim import InSimApp

logger = logging.getLogger(__name__)


class App(InSimApp):
    """
    Tu InSim principal.

    Para depender de otros InSims, añádelos a 'dependencies':
        dependencies = ["player_tracker>=1.0.0"]
    """

    # Dependencias de otros InSims (opcional)
    dependencies = []

    def on_connect(self):
        """Llamado cuando se conecta a LFS."""
        logger.info(f"{self.name} conectado!")
        self.send_ISP_MSL(Msg="^2test_insim ^7conectado")

    def on_disconnect(self):
        """Llamado cuando se desconecta."""
        logger.info(f"{self.name} desconectado")


# Para ejecución directa: python main.py
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = App()
    app.start()
