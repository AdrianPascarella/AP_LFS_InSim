from __future__ import annotations
import copy
import os
from typing import Optional

from lfs_insim.insim_enums import ISB_STYLE, BFN, INST, TYPEIN_FLAGS
from lfs_insim.packets import ISP_BTC, ISP_BTT, ISP_MSO
from lfs_insim.utils import TextColors as c
from insims.ai_control.base import _MixinBase


class _FakePkt:
    """Objeto mínimo que simula ISP_MSO para pasar UCID a métodos que lo requieren."""
    def __init__(self, ucid: int):
        self.UCID = ucid


class _MapUIMixin(_MixinBase):
    """
    Interfaz gráfica de botones para el map_recorder.
    Activar con: .map ui
    """

    # ──────────────────────────────────────────────────────────────────────────
    # ClickID reservados (100–139)
    # ──────────────────────────────────────────────────────────────────────────
    _UI_CID_CLOSE    = 100   # [X] Cerrar
    _UI_CID_SAVE     = 101   # [Guardar] header shortcut
    _UI_CID_LBL_MAP  = 102   # Label "Mapa: X"  (no clickable)
    _UI_CID_LBL_REC  = 103   # Label estado grabación (no clickable)
    _UI_CID_TAB_MAPA = 104
    _UI_CID_TAB_GRAB = 105
    _UI_CID_TAB_INFO = 106
    _UI_CID_TAB_EDIT = 107
    # 108-109 libres
    # 110-129 área de contenido (se limpian y redibujan en cada cambio de tab)
    _UI_CID_TI1      = 130   # TypeIn primario   (ID / nombre mapa / obj_id)
    _UI_CID_TI2      = 131   # TypeIn secundario (road_b / prop_name)
    _UI_CID_TI3      = 132   # TypeIn terciario  (prop_value para .set)
    _UI_CID_LBL_CONF = 133   # Label de confirmación

    # ──────────────────────────────────────────────────────────────────────────
    # Estado
    # ──────────────────────────────────────────────────────────────────────────

    def _init_ui_state(self):
        self._ui_ucid: int = 0
        self._ui_tab: str = "grabar"
        self._ui_pending_action: Optional[str] = None
        self._ui_input_buffer: dict = {}

    # ──────────────────────────────────────────────────────────────────────────
    # Entrada: .map ui
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_open(self, packet: ISP_MSO):
        self._init_ui_state()
        self._ui_ucid = packet.UCID
        self._map_ui_draw_header()
        self._map_ui_draw_tabs()
        self._map_ui_redraw_content()

    # ──────────────────────────────────────────────────────────────────────────
    # Header (T=4, H=6)
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_draw_header(self):
        u = self._ui_ucid
        map_name = self.map_recorder.active_map_name or "(sin mapa)"
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_LBL_MAP,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                          L=2, T=4, W=76, H=6, Text=f"Mapa: {map_name}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_LBL_REC,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                          L=80, T=4, W=74, H=6, Text=self._map_ui_rec_status())
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_SAVE,
                          BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
                          L=156, T=4, W=18, H=6, Text="Guardar")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_CLOSE,
                          BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
                          L=176, T=4, W=8, H=6, Text="X")

    def _map_ui_update_header(self):
        """Actualiza solo el texto de las dos labels del header (W=0, H=0)."""
        u = self._ui_ucid
        map_name = self.map_recorder.active_map_name or "(sin mapa)"
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_LBL_MAP,
                          BStyle=0, L=0, T=0, W=0, H=0, Text=f"Mapa: {map_name}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_LBL_REC,
                          BStyle=0, L=0, T=0, W=0, H=0, Text=self._map_ui_rec_status())

    def _map_ui_rec_status(self) -> str:
        rec = self.map_recorder.current_recording
        if not rec:
            return "Sin grabacion activa"
        rec_type = rec.get("type", "?").upper()
        obj_id = (rec.get("road_id") or rec.get("link_id") or
                  rec.get("zone_id") or rec.get("rule_id", "?"))
        n = len(rec.get("nodes", []))
        auto = " AUTO" if self.map_recorder.auto_recording_enabled else ""
        return f"REC: {rec_type} '{obj_id}' ({n}pts{auto})"

    # ──────────────────────────────────────────────────────────────────────────
    # Tabs (T=11, H=7)
    # ──────────────────────────────────────────────────────────────────────────

    _TAB_LAYOUT = [
        (_UI_CID_TAB_MAPA, "Mapa",   2),
        (_UI_CID_TAB_GRAB, "Grabar", 36),
        (_UI_CID_TAB_INFO, "Info",   70),
        (_UI_CID_TAB_EDIT, "Editar", 104),
    ]
    _TAB_CID_TO_NAME = {
        _UI_CID_TAB_MAPA: "mapa",
        _UI_CID_TAB_GRAB: "grabar",
        _UI_CID_TAB_INFO: "info",
        _UI_CID_TAB_EDIT: "editar",
    }

    def _map_ui_draw_tabs(self):
        u = self._ui_ucid
        active_cid = next(
            (cid for cid, name, _ in self._TAB_LAYOUT if name.lower() == self._ui_tab),
            self._UI_CID_TAB_GRAB
        )
        for cid, label, L in self._TAB_LAYOUT:
            style = (ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if cid == active_cid else (ISB_STYLE.DARK | ISB_STYLE.CLICK)
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=cid, BStyle=style,
                              L=L, T=11, W=32, H=7, Text=label)

    # ──────────────────────────────────────────────────────────────────────────
    # Área de contenido
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_clear_content(self):
        self.send_ISP_BFN(SubT=BFN.DEL_BTN, UCID=0, ClickID=108, ClickMax=133)

    def _map_ui_redraw_content(self):
        self._map_ui_clear_content()
        if self._ui_tab == "mapa":
            self._map_ui_draw_tab_mapa()
        elif self._ui_tab == "grabar":
            self._map_ui_draw_tab_grabar()
        elif self._ui_tab == "info":
            self._map_ui_draw_tab_info()
        elif self._ui_tab == "editar":
            self._map_ui_draw_tab_editar()

    # ──────────────────────────────────────────────────────────────────────────
    # Tab: Mapa
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_draw_tab_mapa(self):
        u = self._ui_ucid
        current_map = self.map_recorder.active_map_name or ""

        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI1,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 32,
                          L=2, T=21, W=80, H=8,
                          Text=current_map or "Nombre del mapa")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=110,
                          BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
                          L=84, T=21, W=32, H=8, Text="Seleccionar")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=111,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.CLICK,
                          L=2, T=31, W=40, H=8, Text="Guardar")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=112,
                          BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
                          L=44, T=31, W=40, H=8, Text="Borrar mapa")

        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=113,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                          L=2, T=42, W=60, H=5, Text="Mapas en disco:")
        maps = self._map_ui_get_map_list()
        if maps:
            for i, name in enumerate(maps[:6]):
                is_active = (name == current_map)
                style = (ISB_STYLE.OK | ISB_STYLE.CLICK) if is_active else (ISB_STYLE.TEXT_STRING | ISB_STYLE.CLICK)
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=114 + i, BStyle=style,
                                  L=2 + i * 30, T=49, W=28, H=7, Text=name)
        else:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=114,
                              BStyle=ISB_STYLE.DARK,
                              L=2, T=49, W=60, H=7, Text="(sin mapas guardados)")

        rule = self.map_recorder.default_traffic_rule
        rule_label = f"Trafico: {rule.name}"
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=120,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.CLICK,
                          L=2, T=70, W=50, H=8, Text=rule_label)

    def _map_ui_get_map_list(self) -> list:
        from insims.ai_control.nav_modes.freeroam import map_recorder as _mr_mod
        base_dir = os.path.dirname(os.path.abspath(_mr_mod.__file__))
        maps_folder = os.path.join(base_dir, "maps")
        if not os.path.exists(maps_folder):
            return []
        return sorted(f.replace(".json", "") for f in os.listdir(maps_folder) if f.endswith(".json"))

    # ──────────────────────────────────────────────────────────────────────────
    # Tab: Grabar
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_draw_tab_grabar(self):
        rec = self.map_recorder.current_recording
        if rec:
            self._map_ui_draw_grabar_active(rec)
        elif self._ui_pending_action in ("rec_roadlink", "rec_laterallink"):
            self._map_ui_draw_grabar_two_args()
        else:
            self._map_ui_draw_grabar_idle()

    def _map_ui_draw_grabar_idle(self):
        u = self._ui_ucid
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI1,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=40,
                          L=2, T=21, W=100, H=8, Text="ID del elemento...")

        for cid, label, L, T in [
            (110, "Road",         2,  31),
            (111, "RoadLink",    36,  31),
            (112, "LatLink",     70,  31),
            (113, "Zona",         2,  41),
            (114, "Reg. Especial", 36, 41),
        ]:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=cid,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.CLICK,
                              L=L, T=T, W=32, H=8, Text=label)

        auto_on = self.map_recorder.auto_recording_enabled
        style = ISB_STYLE.OK | ISB_STYLE.CLICK if auto_on else ISB_STYLE.DARK | ISB_STYLE.CLICK
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=115,
                          BStyle=style,
                          L=2, T=53, W=40, H=8,
                          Text="Auto: ON" if auto_on else "Auto: OFF")

    def _map_ui_draw_grabar_two_args(self):
        u = self._ui_ucid
        is_roadlink = (self._ui_pending_action == "rec_roadlink")
        label_a = "Road origen:" if is_roadlink else "Road A:"
        label_b = "Road destino:" if is_roadlink else "Road B:"
        action_name = "RoadLink" if is_roadlink else "LatLink"

        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=110,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                          L=2, T=21, W=50, H=6, Text=label_a)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI1,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 40,
                          L=2, T=28, W=100, H=8,
                          Text=self._ui_input_buffer.get(self._UI_CID_TI1, ""))
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=111,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                          L=2, T=38, W=50, H=6, Text=label_b)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI2,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 40,
                          L=2, T=45, W=100, H=8,
                          Text=self._ui_input_buffer.get(self._UI_CID_TI2, ""))
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=116,
                          BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
                          L=2, T=57, W=50, H=8, Text=f"Iniciar {action_name}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=117,
                          BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
                          L=54, T=57, W=30, H=8, Text="Cancelar")

    def _map_ui_draw_grabar_active(self, rec: dict):
        u = self._ui_ucid
        rec_type = rec.get("type", "?").upper()
        obj_id = (rec.get("road_id") or rec.get("link_id") or
                  rec.get("zone_id") or rec.get("rule_id", "?"))
        n = len(rec.get("nodes", []))

        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=110,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                          L=2, T=21, W=182, H=7,
                          Text=f"Grabando: {rec_type} '{obj_id}'")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=111,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                          L=2, T=29, W=80, H=6,
                          Text=f"Nodos grabados: {n}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=112,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.CLICK,
                          L=2, T=37, W=60, H=8, Text="+ Anadir punto")
        auto_on = self.map_recorder.auto_recording_enabled
        auto_style = ISB_STYLE.OK | ISB_STYLE.CLICK if auto_on else ISB_STYLE.DARK | ISB_STYLE.CLICK
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=113,
                          BStyle=auto_style,
                          L=64, T=37, W=40, H=8,
                          Text="Auto: ON" if auto_on else "Auto: OFF")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=114,
                          BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
                          L=2, T=48, W=60, H=9, Text="Finalizar")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=115,
                          BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
                          L=64, T=48, W=60, H=9, Text="Cancelar")

    # ──────────────────────────────────────────────────────────────────────────
    # Tab: Info
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_draw_tab_info(self):
        u = self._ui_ucid
        for cid, label, L in [(110, "Stats", 2), (111, "Check", 42), (112, "Roads cerradas", 82)]:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=cid,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.CLICK,
                              L=L, T=21, W=38, H=8, Text=label)
        for cid, label, L in [(113, "Whereami road", 2), (114, "Whereami link", 42), (115, "Whereami zone", 82)]:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=cid,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.CLICK,
                              L=L, T=31, W=38, H=8, Text=label)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI1,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=40, L=2, T=43, W=100, H=8, Text="ID del objeto...")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=116,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.CLICK,
                          L=104, T=43, W=30, H=8, Text="Info")

    # ──────────────────────────────────────────────────────────────────────────
    # Tab: Editar
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_draw_tab_editar(self):
        u = self._ui_ucid
        for cid, label, ti_cid, T, hint in [
            (self._UI_CID_LBL_CONF, "ID:",       self._UI_CID_TI1, 21, "ID del objeto..."),
            (110,                   "Propiedad:", self._UI_CID_TI2, 31, "nombre_propiedad"),
            (111,                   "Valor:",     self._UI_CID_TI3, 41, "nuevo_valor"),
        ]:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=cid,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                              L=2, T=T, W=30, H=6, Text=label)
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=ti_cid,
                              BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                              TypeIn=40, L=34, T=T, W=80, H=8, Text=hint)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=112,
                          BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
                          L=2, T=53, W=50, H=8, Text="Set propiedad")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=113,
                          BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
                          L=54, T=53, W=50, H=8, Text="Borrar objeto")

    # ──────────────────────────────────────────────────────────────────────────
    # Handlers de eventos
    # ──────────────────────────────────────────────────────────────────────────

    def on_ISP_BTC(self, packet: ISP_BTC):
        if not self._ui_ucid or packet.UCID != self._ui_ucid:
            return
        self._map_ui_handle_click(packet.ClickID)

    def on_ISP_BTT(self, packet: ISP_BTT):
        if not self._ui_ucid or packet.UCID != self._ui_ucid:
            return
        self._ui_input_buffer[packet.ClickID] = packet.Text.strip()

    def _map_ui_handle_click(self, cid: int):
        # Header
        if cid == self._UI_CID_CLOSE:
            self._map_ui_close()
            return
        if cid == self._UI_CID_SAVE:
            self.map_recorder._cmd_save_map()
            self._map_ui_update_header()
            return
        # Tabs
        if cid in self._TAB_CID_TO_NAME:
            self._ui_tab = self._TAB_CID_TO_NAME[cid]
            self._ui_pending_action = None
            self._ui_input_buffer = {}
            self._map_ui_draw_tabs()
            self._map_ui_redraw_content()
            return
        # Content
        if self._ui_tab == "mapa":
            self._map_ui_click_mapa(cid)
        elif self._ui_tab == "grabar":
            self._map_ui_click_grabar(cid)
        elif self._ui_tab == "info":
            self._map_ui_click_info(cid)
        elif self._ui_tab == "editar":
            self._map_ui_click_editar(cid)

    # ──────────────────────────────────────────────────────────────────────────
    # Click handlers por tab
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_click_mapa(self, cid: int):
        buf = self._ui_input_buffer
        name = buf.get(self._UI_CID_TI1, "").strip()
        if cid == 110:  # Seleccionar
            if name:
                self.map_recorder._cmd_set_map(name)
                self._map_ui_update_header()
                self._map_ui_redraw_content()
            else:
                self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el nombre del mapa primero.")
        elif cid == 111:  # Guardar
            self.map_recorder._cmd_save_map()
            self._map_ui_update_header()
        elif cid == 112:  # Borrar mapa
            if name:
                self.map_recorder._cmd_del_map(name)
                self._map_ui_update_header()
                self._map_ui_redraw_content()
            else:
                self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el nombre del mapa a borrar primero.")
        elif 114 <= cid <= 119:  # Click en mapa de la lista
            maps = self._map_ui_get_map_list()
            idx = cid - 114
            if idx < len(maps):
                self.map_recorder._cmd_set_map(maps[idx])
                self._map_ui_update_header()
                self._map_ui_redraw_content()
        elif cid == 120:  # Toggle tráfico LHT/RHT
            from insims.ai_control.nav_modes.freeroam.enums import TrafficRule
            current = self.map_recorder.default_traffic_rule
            new_rule = TrafficRule.RHT if current == TrafficRule.LHT else TrafficRule.LHT
            self.map_recorder._cmd_rec_road_rule(new_rule.name)
            self._map_ui_redraw_content()

    def _map_ui_click_grabar(self, cid: int):
        rec = self.map_recorder.current_recording
        buf = self._ui_input_buffer

        if rec:
            # ── Grabación activa ──────────────────────────────────────────────
            if cid == 112:  # Añadir punto
                coords = self.map_recorder.get_coords_fn(self._ui_ucid)
                if coords:
                    self.map_recorder.current_recording["nodes"].append(copy.deepcopy(coords))
                    n = len(self.map_recorder.current_recording["nodes"])
                    self.send_ISP_MSL(Msg=f"{c.GREEN}Nodo #{n} añadido manualmente.")
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(Msg=f"{c.RED}Error: No se pudo obtener telemetria (en pista?).")
            elif cid == 113:  # Toggle auto
                new = not self.map_recorder.auto_recording_enabled
                self.map_recorder._cmd_rec_auto("true" if new else "false")
                self._map_ui_redraw_content()
                self._map_ui_update_header()
            elif cid == 114:  # Finalizar
                self.map_recorder._cmd_rec_end()
                self._map_ui_redraw_content()
                self._map_ui_update_header()
            elif cid == 115:  # Cancelar
                self.map_recorder._cmd_rec_cancel()
                self._map_ui_redraw_content()
                self._map_ui_update_header()

        elif self._ui_pending_action in ("rec_roadlink", "rec_laterallink"):
            # ── Pendiente de 2 args ───────────────────────────────────────────
            if cid == 116:  # Confirmar
                road_a = buf.get(self._UI_CID_TI1, "").strip()
                road_b = buf.get(self._UI_CID_TI2, "").strip()
                if road_a and road_b:
                    if self._ui_pending_action == "rec_roadlink":
                        self.map_recorder._cmd_rec_roadlink(road_a, road_b)
                    else:
                        self.map_recorder._cmd_rec_laterallink(road_a, road_b)
                    self._ui_pending_action = None
                    self._ui_input_buffer = {}
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(Msg=f"{c.RED}Rellena ambos campos antes de confirmar.")
            elif cid == 117:  # Cancelar acción
                self._ui_pending_action = None
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()

        else:
            # ── Reposo: iniciar grabación ─────────────────────────────────────
            obj_id = buf.get(self._UI_CID_TI1, "").strip()
            if cid == 110:  # Road
                if obj_id:
                    self.map_recorder._cmd_rec_road(obj_id)
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el ID del elemento primero.")
            elif cid == 111:  # RoadLink — flujo 2 args
                self._ui_pending_action = "rec_roadlink"
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()
            elif cid == 112:  # LatLink — flujo 2 args
                self._ui_pending_action = "rec_laterallink"
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()
            elif cid == 113:  # Zona
                if obj_id:
                    self.map_recorder._cmd_rec_zone(obj_id)
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el ID del elemento primero.")
            elif cid == 114:  # Regla especial
                if obj_id:
                    self.map_recorder._cmd_rec_special_rule(obj_id)
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el ID del elemento primero.")
            elif cid == 115:  # Toggle auto (sin grabación activa)
                new = not self.map_recorder.auto_recording_enabled
                self.map_recorder._cmd_rec_auto("true" if new else "false")
                self._map_ui_redraw_content()

    def _map_ui_click_info(self, cid: int):
        buf = self._ui_input_buffer
        fake = _FakePkt(self._ui_ucid)
        if cid == 110:
            self.map_recorder._cmd_stats()
        elif cid == 111:
            self.map_recorder._cmd_check_map()
        elif cid == 112:
            self.map_recorder._cmd_is_closed_road()
        elif cid == 113:
            self.map_recorder._cmd_whereami(fake, "road")
        elif cid == 114:
            self.map_recorder._cmd_whereami(fake, "link")
        elif cid == 115:
            self.map_recorder._cmd_whereami(fake, "zone")
        elif cid == 116:
            obj_id = buf.get(self._UI_CID_TI1, "").strip()
            if obj_id:
                self.map_recorder._cmd_info(obj_id)
            else:
                self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el ID del objeto primero.")

    def _map_ui_click_editar(self, cid: int):
        buf = self._ui_input_buffer
        obj_id = buf.get(self._UI_CID_TI1, "").strip()
        prop   = buf.get(self._UI_CID_TI2, "").strip()
        val    = buf.get(self._UI_CID_TI3, "").strip()
        if cid == 112:  # Set propiedad
            if obj_id and prop and val:
                self.map_recorder._cmd_set(obj_id, prop, val)
            else:
                self.send_ISP_MSL(Msg=f"{c.YELLOW}Rellena ID, Propiedad y Valor antes de aplicar.")
        elif cid == 113:  # Borrar objeto
            if obj_id:
                self.map_recorder._cmd_del(obj_id)
                self._map_ui_redraw_content()
                self._map_ui_update_header()
            else:
                self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el ID del objeto a borrar.")

    # ──────────────────────────────────────────────────────────────────────────
    # Cierre
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_close(self):
        self.send_ISP_BFN(SubT=BFN.CLEAR, UCID=self._ui_ucid)
        self._ui_ucid = 0
        self._ui_pending_action = None
        self._ui_input_buffer = {}
