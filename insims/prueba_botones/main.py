from lfs_insim import InSimApp
from lfs_insim.packets import *
from lfs_insim.insim_enums import ISF, ISB_STYLE, ISB_CLICK, BFN, INST, TYPEIN_FLAGS
from lfs_insim.utils import CMDManager, separate_command_args, TextColors as c

# ClickIDs reservados para cada prueba
CID_COLORES     = range(1,  9)   # 1-8:  8 colores
CID_LIGHT       = 10
CID_DARK        = 11
CID_PLAIN       = 12
CID_LEFT        = 13
CID_CENTER      = 14
CID_RIGHT       = 15
CID_CLICK       = 16
CID_TYPEIN      = 17
CID_TYPEIN_INIT = 18
CID_ALWAYS_ON   = 19
CID_CAPTION     = 20
CID_UPDATE      = 21


class PruebaBotones(InSimApp):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd_prefix: str = self.config.get("prefix", "!")
        self.cmd_base: str = "botones"
        self.cmds: CMDManager
        self._active_screen: str | None = None  # para re-enviar en BFN_REQUEST
        self.logger.info(f"Modulo {self.name} inicializado.")

    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.LOCAL

    def on_connect(self):
        self.cmds = (
            CMDManager(self.cmd_prefix, self.cmd_base)
            .add_cmd("colores",     "8 botones con los colores estándar de LFS",     None,                  self._cmd_colores)
            .add_cmd("estilos",     "Botones LIGHT, DARK y sin estilo",              None,                  self._cmd_estilos)
            .add_cmd("alineacion",  "Alineación de texto: izquierda, centro, derecha", None,                self._cmd_alineacion)
            .add_cmd("click",       "Botón clickable: recibe IS_BTC",                None,                  self._cmd_click)
            .add_cmd("typein",      "Botón de entrada de texto: recibe IS_BTT",      None,                  self._cmd_typein)
            .add_cmd("typein_init", "TypeIn con texto inicial pre-rellenado",        None,                  self._cmd_typein_init)
            .add_cmd("caption",     "Botón con caption personalizado en el diálogo", None,                  self._cmd_caption)
            .add_cmd("always_on",   "Botón visible en todas las pantallas (INST_ALWAYS_ON)", None,          self._cmd_always_on)
            .add_cmd("update",      "Crea un botón y luego actualiza solo su texto (W=0 H=0)", None,        self._cmd_update)
            .add_cmd("del",         "Borra un botón por su ClickID",                 (("id", int),),        self._cmd_del)
            .add_cmd("del_range",   "Borra un rango de botones [from..to]",          (("desde", int), ("hasta", int)), self._cmd_del_range)
            .add_cmd("clear",       "Borra todos los botones de este InSim",         None,                  self._cmd_clear)
            .submit()
        )
        self.send_ISP_MSL(Msg=f"{c.GREEN}{self.name} {c.WHITE}conectado")

    def on_ISP_MSO(self, packet: ISP_MSO):
        cmd, args = separate_command_args(self.cmd_prefix, packet)
        if cmd == self.cmd_base:
            self.cmds.handle_commands(packet, args)

    # ------------------------------------------------------------------ #
    # Prueba 1: 8 colores estándar (bits C1, C2, C4 → valores 0 a 7)     #
    # ------------------------------------------------------------------ #
    def _cmd_colores(self):
        self._cmd_clear()
        self._active_screen = "colores"
        etiquetas = ["Grey", "Title", "Unsel", "Sel", "OK", "Cancel", "String", "Unavail"]
        colores   = [
            ISB_STYLE.LIGHT_GREY, ISB_STYLE.TITLE,    ISB_STYLE.UNSELECTED, ISB_STYLE.SELECTED,
            ISB_STYLE.OK,         ISB_STYLE.CANCEL,    ISB_STYLE.TEXT_STRING, ISB_STYLE.UNAVAILABLE,
        ]
        for i, (label, color) in enumerate(zip(etiquetas, colores)):
            self.send_ISP_BTN(
                ReqI=1, UCID=0,
                ClickID=CID_COLORES.start + i,
                BStyle=color,
                L=4 + i * 24, T=10, W=23, H=8,
                Text=label,
            )
        self.send_ISP_MSL(Msg=f"{c.YELLOW}8 colores estándar de LFS mostrados (T=10)")

    # ------------------------------------------------------------------ #
    # Prueba 2: LIGHT, DARK y sin estilo                                  #
    # ------------------------------------------------------------------ #
    def _cmd_estilos(self):
        self._cmd_clear()
        self._active_screen = "estilos"
        self.send_ISP_BTN(ReqI=1, UCID=0, ClickID=CID_LIGHT,  BStyle=ISB_STYLE.LIGHT, L=10, T=10, W=40, H=10, Text="LIGHT")
        self.send_ISP_BTN(ReqI=1, UCID=0, ClickID=CID_DARK,   BStyle=ISB_STYLE.DARK,  L=55, T=10, W=40, H=10, Text="DARK")
        self.send_ISP_BTN(ReqI=1, UCID=0, ClickID=CID_PLAIN,  BStyle=0,               L=100, T=10, W=40, H=10, Text="Sin estilo")
        self.send_ISP_MSL(Msg=f"{c.YELLOW}Estilos: LIGHT / DARK / Sin estilo (T=10)")

    # ------------------------------------------------------------------ #
    # Prueba 3: alineación de texto LEFT, CENTER, RIGHT                   #
    # ------------------------------------------------------------------ #
    def _cmd_alineacion(self):
        self._cmd_clear()
        self._active_screen = "alineacion"
        self.send_ISP_BTN(ReqI=1, UCID=0, ClickID=CID_LEFT,   BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,  L=10,  T=10, W=50, H=10, Text="Izquierda")
        self.send_ISP_BTN(ReqI=1, UCID=0, ClickID=CID_CENTER, BStyle=ISB_STYLE.DARK,                    L=65,  T=10, W=50, H=10, Text="Centro")
        self.send_ISP_BTN(ReqI=1, UCID=0, ClickID=CID_RIGHT,  BStyle=ISB_STYLE.DARK | ISB_STYLE.RIGHT, L=120, T=10, W=50, H=10, Text="Derecha")
        self.send_ISP_MSL(Msg=f"{c.YELLOW}Alineacion: LEFT / CENTER / RIGHT (T=10)")

    # ------------------------------------------------------------------ #
    # Prueba 4: botón clickable — responde con IS_BTC                     #
    # ------------------------------------------------------------------ #
    def _cmd_click(self):
        self._cmd_clear()
        self._active_screen = "click"
        self.send_ISP_BTN(
            ReqI=1, UCID=0,
            ClickID=CID_CLICK,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.CLICK,
            L=60, T=20, W=80, H=12,
            Text="Haz click aqui",
        )
        self.send_ISP_MSL(Msg=f"{c.YELLOW}Boton clickable activo. Haz clic (LMB/RMB + CTRL/SHIFT)")

    def on_ISP_BTC(self, packet: ISP_BTC):
        flags = []
        if packet.CFlags & ISB_CLICK.LMB:   flags.append("LMB")
        if packet.CFlags & ISB_CLICK.RMB:   flags.append("RMB")
        if packet.CFlags & ISB_CLICK.CTRL:  flags.append("CTRL")
        if packet.CFlags & ISB_CLICK.SHIFT: flags.append("SHIFT")
        modificadores = "+".join(flags) if flags else "sin modificadores"
        self.send_ISP_MSL(Msg=f"{c.GREEN}BTC: ClickID={packet.ClickID} UCID={packet.UCID} | {modificadores}")

    # ------------------------------------------------------------------ #
    # Prueba 5: TypeIn básico — responde con IS_BTT                       #
    # ------------------------------------------------------------------ #
    def _cmd_typein(self):
        self._cmd_clear()
        self._active_screen = "typein"
        self.send_ISP_BTN(
            ReqI=1, UCID=0,
            ClickID=CID_TYPEIN,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.CLICK,
            TypeIn=20,          # acepta hasta 20 caracteres
            L=60, T=20, W=80, H=12,
            Text="Escribe algo",
        )
        self.send_ISP_MSL(Msg=f"{c.YELLOW}TypeIn activo (max 20 chars). Haz clic y escribe.")

    # ------------------------------------------------------------------ #
    # Prueba 6: TypeIn con texto inicial (bit 128)                        #
    # ------------------------------------------------------------------ #
    def _cmd_typein_init(self):
        self._cmd_clear()
        self._active_screen = "typein_init"
        self.send_ISP_BTN(
            ReqI=1, UCID=0,
            ClickID=CID_TYPEIN_INIT,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 20,  # pre-rellena el diálogo con el texto del botón
            L=60, T=20, W=80, H=12,
            Text="Edita este texto",
        )
        self.send_ISP_MSL(Msg=f"{c.YELLOW}TypeIn con texto inicial pre-rellenado.")

    def on_ISP_BTT(self, packet: ISP_BTT):
        self.send_ISP_MSL(Msg=f"{c.GREEN}BTT: ClickID={packet.ClickID} UCID={packet.UCID} | Texto: \"{packet.Text}\"")

    # ------------------------------------------------------------------ #
    # Prueba 7: caption personalizado en el diálogo TypeIn                #
    # El formato es: \x00 + caption + \x00 + texto_visible                #
    # ------------------------------------------------------------------ #
    def _cmd_caption(self):
        self._cmd_clear()
        self._active_screen = "caption"
        self.send_ISP_BTN(
            ReqI=1, UCID=0,
            ClickID=CID_CAPTION,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.CLICK,
            TypeIn=30,
            L=60, T=20, W=80, H=12,
            Text="\x00Introduce tu nombre\x00Nombre del piloto",
        )
        self.send_ISP_MSL(Msg=f"{c.YELLOW}Caption personalizado. Haz clic para ver el dialogo.")

    # ------------------------------------------------------------------ #
    # Prueba 8: INST_ALWAYS_ON — visible en todas las pantallas           #
    # ------------------------------------------------------------------ #
    def _cmd_always_on(self):
        self._active_screen = "always_on"
        self.send_ISP_BTN(
            ReqI=1, UCID=0,
            ClickID=CID_ALWAYS_ON,
            Inst=INST.ALWAYS_ON,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.DARK,
            L=0, T=0, W=30, H=6,
            Text="ALWAYS ON",
        )
        self.send_ISP_MSL(Msg=f"{c.YELLOW}Boton ALWAYS_ON activo (esquina sup. izq.). Abre el garage para comprobarlo.")

    # ------------------------------------------------------------------ #
    # Prueba 9: actualizar solo el texto (W=0, H=0)                       #
    # ------------------------------------------------------------------ #
    def _cmd_update(self):
        self._cmd_clear()
        self._active_screen = "update"
        # Paso 1: crear el botón con su posición
        self.send_ISP_BTN(
            ReqI=1, UCID=0,
            ClickID=CID_UPDATE,
            BStyle=ISB_STYLE.DARK,
            L=60, T=20, W=80, H=12,
            Text="Texto original",
        )
        self.send_ISP_MSL(Msg=f"{c.YELLOW}Boton creado. Actualizando texto en 0.5s...")

        # Paso 2: actualizar solo el texto sin conocer la posición (W=0, H=0)
        import threading
        def _do_update():
            import time; time.sleep(0.5)
            self.send_ISP_BTN(
                ReqI=1, UCID=0,
                ClickID=CID_UPDATE,
                BStyle=0,           # ignorado cuando W=0 H=0
                L=0, T=0, W=0, H=0,
                Text="Texto actualizado!",
            )
            self.send_ISP_MSL(Msg=f"{c.GREEN}Texto del boton actualizado (W=0 H=0).")
        threading.Thread(target=_do_update, daemon=True).start()

    # ------------------------------------------------------------------ #
    # Prueba 10: borrar un botón por ClickID                              #
    # ------------------------------------------------------------------ #
    def _cmd_del(self, click_id: int):
        self.send_ISP_BFN(SubT=BFN.DEL_BTN, UCID=0, ClickID=click_id, ClickMax=click_id)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}Boton ClickID={click_id} eliminado.")

    # ------------------------------------------------------------------ #
    # Prueba 11: borrar un rango de botones                               #
    # ------------------------------------------------------------------ #
    def _cmd_del_range(self, desde: int, hasta: int):
        self.send_ISP_BFN(SubT=BFN.DEL_BTN, UCID=0, ClickID=desde, ClickMax=hasta)
        self.send_ISP_MSL(Msg=f"{c.YELLOW}Rango ClickID [{desde}..{hasta}] eliminado.")

    # ------------------------------------------------------------------ #
    # Prueba 12: limpiar todos los botones                                #
    # ------------------------------------------------------------------ #
    def _cmd_clear(self):
        self.send_ISP_BFN(SubT=BFN.CLEAR, UCID=0)
        self._active_screen = None

    # ------------------------------------------------------------------ #
    # BFN_REQUEST: el usuario pulsó SHIFT+B — re-enviar pantalla activa  #
    # ------------------------------------------------------------------ #
    def on_ISP_BFN(self, packet: ISP_BFN):
        if packet.SubT == BFN.REQUEST and self._active_screen:
            self.send_ISP_MSL(Msg=f"{c.YELLOW}BFN_REQUEST recibido. Re-enviando pantalla '{self._active_screen}'...")
            handler = getattr(self, f"_cmd_{self._active_screen}", None)
            if handler:
                handler()
        elif packet.SubT == BFN.USER_CLEAR:
            self._active_screen = None
            self.send_ISP_MSL(Msg=f"{c.YELLOW}BFN_USER_CLEAR: el usuario limpio los botones.")

    def on_disconnect(self):
        self.logger.info(f"Modulo {self.name} desconectado.")
