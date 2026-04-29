from __future__ import annotations
import copy
import os
from typing import Optional

from lfs_insim.insim_enums import ISB_STYLE, BFN, TYPEIN_FLAGS
from lfs_insim.packets import ISP_BTC, ISP_BTT, ISP_MSO
from lfs_insim.utils import TextColors as c
from insims.ai_control.base import _MixinBase


class _FakePkt:
    """Objeto mínimo que simula ISP_MSO para pasar UCID a métodos que lo requieren."""
    def __init__(self, ucid: int):
        self.UCID = ucid


# ──────────────────────────────────────────────────────────────────────────────
# Definición de campos editables por tipo de objeto del mapa
# Formato: (field_name, field_type)
# field_type: "bool" | "float" | "str" | "readonly"
# ──────────────────────────────────────────────────────────────────────────────
_ELEM_FIELDS: dict[str, list[tuple[str, str]]] = {
    "road": [
        ("road_id",          "readonly"),
        ("nodes",            "readonly"),
        ("speed_limit_kmh",  "float"),
        ("is_circular",      "bool"),
        ("is_closed",        "bool"),
        ("traffic_rule",     "enum_traffic"),
    ],
    "roadlink": [
        ("from_road_id",     "readonly"),
        ("to_road_id",       "readonly"),
        ("nodes",            "readonly"),
        ("speed_limit_kmh",  "float"),
        ("from_suffix",      "readonly"),
        ("to_suffix",        "readonly"),
        ("by_road_id",       "str"),
        ("indicators",       "str"),
    ],
    "latlink": [
        ("road_a",           "readonly"),
        ("road_b",           "readonly"),
        ("nodes",            "readonly"),
        ("allow_a_to_b",     "bool"),
        ("allow_b_to_a",     "bool"),
        ("opposing",         "bool"),
        ("is_circular",      "bool"),
        ("made_to_overtake", "bool"),
    ],
    "zone": [
        ("zone_id",          "readonly"),
        ("nodes",            "readonly"),
        ("radius_m",         "float"),
    ],
    "rule": [
        ("rule_id",          "readonly"),
        ("nodes",            "readonly"),
        ("radius_m",         "float"),
        ("speed_limit",      "float"),
        ("no_lane_change",   "bool"),
    ],
}

_ELEM_TYPE_LABELS: dict[str, str] = {
    "road":     "Roads",
    "roadlink": "RoadLinks",
    "latlink":  "LatLinks",
    "zone":     "Zonas",
    "rule":     "Reglas",
}

_ELEM_TYPE_LIST = ["road", "roadlink", "latlink", "zone", "rule"]

_ITEMS_PER_PAGE = 6


class _MapUIMixin(_MixinBase):
    """
    Interfaz gráfica de botones para el map_recorder.
    Activar con: .map ui
    """

    # ──────────────────────────────────────────────────────────────────────────
    # ClickID reservados (100–139)
    # ──────────────────────────────────────────────────────────────────────────
    _UI_CID_CLOSE    = 100
    _UI_CID_SAVE     = 101
    _UI_CID_LBL_MAP  = 102
    _UI_CID_LBL_REC  = 103
    _UI_CID_TAB_MAPA = 104
    _UI_CID_TAB_GRAB = 105
    _UI_CID_TAB_INFO = 106
    _UI_CID_TAB_ELEM = 107
    # 108-129: área de contenido (se limpian y redibujan en cada cambio de tab)
    _UI_CID_TI1      = 130   # TypeIn primario
    _UI_CID_TI2      = 131   # TypeIn secundario
    _UI_CID_TI3      = 132   # TypeIn terciario
    _UI_CID_LBL_CONF = 133   # Label de confirmación

    # ──────────────────────────────────────────────────────────────────────────
    # Estado
    # ──────────────────────────────────────────────────────────────────────────

    def _init_ui_state(self):
        self._ui_ucid: Optional[int] = None
        self._ui_tab: str = "grabar"
        self._ui_pending_action: Optional[str] = None
        self._ui_input_buffer: dict = {}
        self._ui_elem_type: str = "road"
        self._ui_elem_page: int = 0
        self._ui_elem_search: str = ""
        self._ui_elem_detail_id: Optional[str] = None
        self._ui_detail_field_map: dict = {}   # {ClickID: (field_name, field_type)}

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
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=2, T=4, W=76, H=6, Text=f"Mapa: {map_name}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_LBL_REC,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=80, T=4, W=74, H=6, Text=self._map_ui_rec_status())
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_SAVE,
                          BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
                          L=156, T=4, W=18, H=6, Text="Guardar")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_CLOSE,
                          BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
                          L=176, T=4, W=8, H=6, Text="X")

    def _map_ui_update_header(self):
        """Actualiza solo el texto de las labels del header (W=0, H=0)."""
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
        (_UI_CID_TAB_MAPA, "mapa",      "Mapa",      2,   34),
        (_UI_CID_TAB_GRAB, "grabar",    "Grabar",    38,  34),
        (_UI_CID_TAB_INFO, "info",      "Info",      74,  34),
        (_UI_CID_TAB_ELEM, "elementos", "Elementos", 110, 44),
    ]
    _TAB_CID_TO_NAME = {
        _UI_CID_TAB_MAPA: "mapa",
        _UI_CID_TAB_GRAB: "grabar",
        _UI_CID_TAB_INFO: "info",
        _UI_CID_TAB_ELEM: "elementos",
    }

    def _map_ui_draw_tabs(self):
        u = self._ui_ucid
        for cid, tab_name, label, L, W in self._TAB_LAYOUT:
            is_active = (tab_name == self._ui_tab)
            style = (ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if is_active else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=cid, BStyle=style,
                              L=L, T=11, W=W, H=7, Text=label)

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
        elif self._ui_tab == "elementos":
            self._map_ui_draw_tab_elementos()

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
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                          L=2, T=31, W=40, H=8, Text="Guardar")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=112,
                          BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
                          L=44, T=31, W=40, H=8, Text="Borrar mapa")

        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=113,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=2, T=42, W=60, H=5, Text="Mapas en disco:")
        maps = self._map_ui_get_map_list()
        if maps:
            for i, name in enumerate(maps[:6]):
                is_active = (name == current_map)
                style = (ISB_STYLE.OK | ISB_STYLE.CLICK) if is_active else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=114 + i, BStyle=style,
                                  L=2 + i * 30, T=49, W=28, H=7, Text=name)
        else:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=114,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                              L=2, T=49, W=60, H=7, Text="(sin mapas guardados)")

        rule = self.map_recorder.default_traffic_rule
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=120,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                          L=2, T=70, W=50, H=8, Text=f"Trafico: {rule.name}")

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
                          TypeIn=40, L=2, T=21, W=100, H=8, Text="ID del elemento...")

        for cid, label, L, T in [
            (110, "Road",         2,  31),
            (111, "RoadLink",    36,  31),
            (112, "LatLink",     70,  31),
            (113, "Zona",         2,  41),
            (114, "Reg. Especial", 36, 41),
        ]:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=cid,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                              L=L, T=T, W=32, H=8, Text=label)

        auto_on = self.map_recorder.auto_recording_enabled
        style = ISB_STYLE.OK | ISB_STYLE.CLICK if auto_on else ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=115,
                          BStyle=style, L=2, T=53, W=40, H=8,
                          Text="Auto: ON" if auto_on else "Auto: OFF")

    def _map_ui_draw_grabar_two_args(self):
        u = self._ui_ucid
        is_roadlink = (self._ui_pending_action == "rec_roadlink")
        label_a = "Road origen:" if is_roadlink else "Road A:"
        label_b = "Road destino:" if is_roadlink else "Road B:"
        action_name = "RoadLink" if is_roadlink else "LatLink"

        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=110,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=2, T=21, W=50, H=6, Text=label_a)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI1,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 40,
                          L=2, T=28, W=100, H=8,
                          Text=self._ui_input_buffer.get(self._UI_CID_TI1, ""))
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=111,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
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
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=2, T=21, W=182, H=7,
                          Text=f"Grabando: {rec_type} '{obj_id}'")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=111,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=2, T=29, W=80, H=6,
                          Text=f"Nodos grabados: {n}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=112,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                          L=2, T=37, W=60, H=8, Text="+ Anadir punto")
        auto_on = self.map_recorder.auto_recording_enabled
        auto_style = ISB_STYLE.OK | ISB_STYLE.CLICK if auto_on else ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=113,
                          BStyle=auto_style, L=64, T=37, W=40, H=8,
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
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                              L=L, T=21, W=38, H=8, Text=label)
        for cid, label, L in [(113, "Whereami road", 2), (114, "Whereami link", 42), (115, "Whereami zone", 82)]:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=cid,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                              L=L, T=31, W=38, H=8, Text=label)

    # ──────────────────────────────────────────────────────────────────────────
    # Tab: Elementos — dispatcher
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_draw_tab_elementos(self):
        if self._ui_elem_detail_id is not None:
            self._map_ui_draw_elem_detail(self._ui_elem_detail_id)
        else:
            self._map_ui_draw_elem_list()

    # ──────────────────────────────────────────────────────────────────────────
    # Elementos — Vista Lista
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_draw_elem_list(self):
        u = self._ui_ucid

        # Filtros de tipo (CIDs 108–112)
        for i, etype in enumerate(_ELEM_TYPE_LIST):
            is_active = (etype == self._ui_elem_type)
            style = (ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if is_active else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=108 + i, BStyle=style,
                              L=2 + i * 38, T=21, W=36, H=7,
                              Text=_ELEM_TYPE_LABELS[etype])

        # Buscador (TI1=130) + botón Filtrar (CID=113)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI1,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 40,
                          L=2, T=30, W=132, H=7,
                          Text=self._ui_elem_search or "Buscar...")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=113,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                          L=136, T=30, W=22, H=7, Text="Filtrar")

        if not self.map_recorder.active_map_name:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=114,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                              L=2, T=39, W=180, H=7, Text="Sin mapa activo")
            return

        items = self._map_ui_elem_get_filtered()
        total_pages = max(1, (len(items) + _ITEMS_PER_PAGE - 1) // _ITEMS_PER_PAGE)
        self._ui_elem_page = max(0, min(self._ui_elem_page, total_pages - 1))
        start = self._ui_elem_page * _ITEMS_PER_PAGE
        page_items = items[start:start + _ITEMS_PER_PAGE]

        if not page_items:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=114,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                              L=2, T=39, W=180, H=7, Text="Sin resultados")
        else:
            for i, item_id in enumerate(page_items):
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=114 + i,
                                  BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                                  L=2, T=39 + i * 7, W=180, H=6,
                                  Text=item_id)

        # Paginación (CIDs 120–122)
        prev_style = (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if self._ui_elem_page > 0 else ISB_STYLE.DARK | ISB_STYLE.SELECTED
        next_style = (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if self._ui_elem_page < total_pages - 1 else ISB_STYLE.DARK | ISB_STYLE.SELECTED
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=120, BStyle=prev_style,
                          L=2, T=82, W=16, H=6, Text="<")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=121, BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                          L=20, T=82, W=50, H=6,
                          Text=f"Pag {self._ui_elem_page + 1}/{total_pages}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=122, BStyle=next_style,
                          L=72, T=82, W=16, H=6, Text=">")

    # ──────────────────────────────────────────────────────────────────────────
    # Elementos — Vista Detalle
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_draw_elem_detail(self, obj_id: str):
        u = self._ui_ucid
        obj = self._map_ui_elem_get_obj(obj_id)
        if obj is None:
            self._ui_elem_detail_id = None
            self._map_ui_draw_elem_list()
            return

        obj_type = self._map_ui_elem_get_type(obj_id)
        fields_def = _ELEM_FIELDS.get(obj_type, [])

        # Header de detalle
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=108,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                          L=2, T=21, W=20, H=6, Text="< Volver")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=109,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=24, T=21, W=118, H=6,
                          Text=f"{obj_type.upper()}: {obj_id}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=110,
                          BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
                          L=144, T=21, W=22, H=6, Text="Borrar")

        # Filas de campos (máx. 7 filas)
        self._ui_detail_field_map = {}
        for row, (fname, ftype) in enumerate(fields_def[:7]):
            T = 29 + row * 8
            label_cid = 111 + row * 2
            val_cid   = 112 + row * 2

            val_str = self._map_ui_elem_field_value_str(obj, fname)

            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=label_cid,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                              L=2, T=T, W=68, H=7, Text=f"{fname}:")

            if ftype == "readonly":
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=val_cid,
                                  BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                                  L=72, T=T, W=108, H=7, Text=val_str)
            elif ftype == "bool":
                is_true = val_str.lower() in ("true", "yes", "si", "1")
                style = (ISB_STYLE.OK | ISB_STYLE.CLICK) if is_true else (ISB_STYLE.CANCEL | ISB_STYLE.CLICK)
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=val_cid,
                                  BStyle=style, L=72, T=T, W=108, H=7,
                                  Text="ON" if is_true else "OFF")
                self._ui_detail_field_map[val_cid] = (fname, "bool")
            elif ftype == "enum_traffic":
                style = ISB_STYLE.OK | ISB_STYLE.CLICK if val_str == "RHT" else ISB_STYLE.TITLE | ISB_STYLE.CLICK
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=val_cid,
                                  BStyle=style, L=72, T=T, W=108, H=7,
                                  Text=val_str if val_str else "RHT")
                self._ui_detail_field_map[val_cid] = (fname, "enum_traffic")
            else:
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=val_cid,
                                  BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                                  TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 48,
                                  L=72, T=T, W=108, H=7, Text=val_str)
                self._ui_detail_field_map[val_cid] = (fname, ftype)

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers del tab Elementos
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_elem_get_filtered(self) -> list:
        mr = self.map_recorder
        collections = {
            "road":     mr.roads,
            "roadlink": mr.road_links,
            "latlink":  mr.lateral_links,
            "zone":     mr.zones,
            "rule":     mr.special_rules,
        }
        coll = collections.get(self._ui_elem_type, {})
        search = self._ui_elem_search.lower()
        return sorted(k for k in coll if search in k.lower())

    def _map_ui_elem_get_obj(self, obj_id: str):
        mr = self.map_recorder
        for coll in (mr.roads, mr.road_links, mr.lateral_links, mr.zones, mr.special_rules):
            if obj_id in coll:
                return coll[obj_id]
        return None

    def _map_ui_elem_get_type(self, obj_id: str) -> str:
        mr = self.map_recorder
        if obj_id in mr.roads:         return "road"
        if obj_id in mr.road_links:    return "roadlink"
        if obj_id in mr.lateral_links: return "latlink"
        if obj_id in mr.zones:         return "zone"
        if obj_id in mr.special_rules: return "rule"
        return "?"

    def _map_ui_elem_field_value_str(self, obj, field_name: str) -> str:
        if field_name == "nodes":
            return f"{len(getattr(obj, 'nodes', []))} nodos"
        if field_name in ("speed_limit", "no_lane_change"):
            val = getattr(obj, "rules", {}).get(field_name)
        else:
            val = getattr(obj, field_name, None)
        if val is None:
            return ""
        if hasattr(val, "name"):  # Enum
            return val.name
        return str(val)

    def _map_ui_silent_set(self, obj_id: str, field: str, val: str):
        """Llama a _cmd_set suprimiendo los mensajes MSL."""
        self.map_recorder.send = lambda pkt: None
        try:
            self.map_recorder._cmd_set(obj_id, field, val)
        finally:
            del self.map_recorder.send

    def _map_ui_silent_del(self, obj_id: str):
        """Llama a _cmd_del suprimiendo los mensajes MSL."""
        self.map_recorder.send = lambda pkt: None
        try:
            self.map_recorder._cmd_del(obj_id)
        finally:
            del self.map_recorder.send

    # ──────────────────────────────────────────────────────────────────────────
    # Handlers de eventos
    # ──────────────────────────────────────────────────────────────────────────

    def on_ISP_BTC(self, packet: ISP_BTC):
        if self._ui_ucid is None or packet.UCID != self._ui_ucid:
            return
        self._map_ui_handle_click(packet.ClickID)

    def on_ISP_BTT(self, packet: ISP_BTT):
        if self._ui_ucid is None or packet.UCID != self._ui_ucid:
            return
        text = packet.Text.strip()
        self._ui_input_buffer[packet.ClickID] = text
        self.send_ISP_BTN(ReqI=1, UCID=self._ui_ucid,
                          ClickID=packet.ClickID,
                          BStyle=0, L=0, T=0, W=0, H=0,
                          Text=text if text else " ")
        # En la vista detalle de Elementos, aplicar cambio inmediatamente
        if (self._ui_tab == "elementos"
                and self._ui_elem_detail_id is not None
                and packet.ClickID in self._ui_detail_field_map):
            fname, ftype = self._ui_detail_field_map[packet.ClickID]
            if ftype not in ("bool", "enum_traffic") and text:
                self._map_ui_silent_set(self._ui_elem_detail_id, fname, text)

    def _map_ui_handle_click(self, cid: int):
        if cid == self._UI_CID_CLOSE:
            self._map_ui_close()
            return
        if cid == self._UI_CID_SAVE:
            self.map_recorder._cmd_save_map()
            self._map_ui_update_header()
            return
        if cid in self._TAB_CID_TO_NAME:
            self._ui_tab = self._TAB_CID_TO_NAME[cid]
            self._ui_pending_action = None
            self._ui_input_buffer = {}
            self._ui_elem_detail_id = None
            self._ui_detail_field_map = {}
            self._map_ui_draw_tabs()
            self._map_ui_redraw_content()
            return
        if self._ui_tab == "mapa":
            self._map_ui_click_mapa(cid)
        elif self._ui_tab == "grabar":
            self._map_ui_click_grabar(cid)
        elif self._ui_tab == "info":
            self._map_ui_click_info(cid)
        elif self._ui_tab == "elementos":
            self._map_ui_click_elementos(cid)

    # ──────────────────────────────────────────────────────────────────────────
    # Click handlers por tab
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_click_mapa(self, cid: int):
        buf = self._ui_input_buffer
        name = buf.get(self._UI_CID_TI1, "").strip()
        if cid == 110:
            if name:
                self.map_recorder._cmd_set_map(name)
                self._map_ui_update_header()
                self._map_ui_redraw_content()
            else:
                self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el nombre del mapa primero.")
        elif cid == 111:
            self.map_recorder._cmd_save_map()
            self._map_ui_update_header()
        elif cid == 112:
            if name:
                self.map_recorder._cmd_del_map(name)
                self._map_ui_update_header()
                self._map_ui_redraw_content()
            else:
                self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el nombre del mapa a borrar primero.")
        elif 114 <= cid <= 119:
            maps = self._map_ui_get_map_list()
            idx = cid - 114
            if idx < len(maps):
                self.map_recorder._cmd_set_map(maps[idx])
                self._map_ui_update_header()
                self._map_ui_redraw_content()
        elif cid == 120:
            from insims.ai_control.nav_modes.freeroam.enums import TrafficRule
            current = self.map_recorder.default_traffic_rule
            new_rule = TrafficRule.RHT if current == TrafficRule.LHT else TrafficRule.LHT
            self.map_recorder._cmd_rec_road_rule(new_rule.name)
            self._map_ui_redraw_content()

    def _map_ui_click_grabar(self, cid: int):
        rec = self.map_recorder.current_recording
        buf = self._ui_input_buffer

        if rec:
            if cid == 112:
                coords = self.map_recorder.get_coords_fn(self._ui_ucid)
                if coords:
                    self.map_recorder.current_recording["nodes"].append(copy.deepcopy(coords))
                    n = len(self.map_recorder.current_recording["nodes"])
                    self.send_ISP_MSL(Msg=f"{c.GREEN}Nodo #{n} añadido manualmente.")
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(Msg=f"{c.RED}Error: No se pudo obtener telemetria (en pista?).")
            elif cid == 113:
                new = not self.map_recorder.auto_recording_enabled
                self.map_recorder._cmd_rec_auto("true" if new else "false")
                self._map_ui_redraw_content()
                self._map_ui_update_header()
            elif cid == 114:
                self.map_recorder._cmd_rec_end()
                self._map_ui_redraw_content()
                self._map_ui_update_header()
            elif cid == 115:
                self.map_recorder._cmd_rec_cancel()
                self._map_ui_redraw_content()
                self._map_ui_update_header()

        elif self._ui_pending_action in ("rec_roadlink", "rec_laterallink"):
            if cid == 116:
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
            elif cid == 117:
                self._ui_pending_action = None
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()

        else:
            obj_id = buf.get(self._UI_CID_TI1, "").strip()
            if cid == 110:
                if obj_id:
                    self.map_recorder._cmd_rec_road(obj_id)
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el ID del elemento primero.")
            elif cid == 111:
                self._ui_pending_action = "rec_roadlink"
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()
            elif cid == 112:
                self._ui_pending_action = "rec_laterallink"
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()
            elif cid == 113:
                if obj_id:
                    self.map_recorder._cmd_rec_zone(obj_id)
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el ID del elemento primero.")
            elif cid == 114:
                if obj_id:
                    self.map_recorder._cmd_rec_special_rule(obj_id)
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(Msg=f"{c.YELLOW}Escribe el ID del elemento primero.")
            elif cid == 115:
                new = not self.map_recorder.auto_recording_enabled
                self.map_recorder._cmd_rec_auto("true" if new else "false")
                self._map_ui_redraw_content()

    def _map_ui_click_info(self, cid: int):
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

    def _map_ui_click_elementos(self, cid: int):
        # ── Vista detalle ──────────────────────────────────────────────────
        if self._ui_elem_detail_id is not None:
            if cid == 108:  # Volver
                self._ui_elem_detail_id = None
                self._map_ui_redraw_content()
            elif cid == 110:  # Borrar
                obj_id = self._ui_elem_detail_id
                self._ui_elem_detail_id = None
                self._map_ui_silent_del(obj_id)
                self._map_ui_redraw_content()
                self._map_ui_update_header()
            elif cid in self._ui_detail_field_map:
                fname, ftype = self._ui_detail_field_map[cid]
                if ftype == "bool":
                    obj = self._map_ui_elem_get_obj(self._ui_elem_detail_id)
                    if obj is not None:
                        cur = self._map_ui_elem_field_value_str(obj, fname)
                        new_val = "false" if cur.lower() == "true" else "true"
                        self._map_ui_silent_set(self._ui_elem_detail_id, fname, new_val)
                        self._map_ui_redraw_content()
                elif ftype == "enum_traffic":
                    obj = self._map_ui_elem_get_obj(self._ui_elem_detail_id)
                    if obj is not None:
                        cur = self._map_ui_elem_field_value_str(obj, fname)
                        cycle = {"RHT": "lht", "LHT": "rht", "": "rht"}
                        new_val = cycle.get(cur, "rht")
                        self._map_ui_silent_set(self._ui_elem_detail_id, fname, new_val)
                        self._map_ui_redraw_content()
            return

        # ── Vista lista ────────────────────────────────────────────────────
        if 108 <= cid <= 112:  # Filtros de tipo
            self._ui_elem_type = _ELEM_TYPE_LIST[cid - 108]
            self._ui_elem_page = 0
            self._ui_elem_search = ""
            self._ui_input_buffer = {}
            self._map_ui_redraw_content()
        elif cid == 113:  # Aplicar buscador
            self._ui_elem_search = self._ui_input_buffer.get(self._UI_CID_TI1, "").strip()
            self._ui_elem_page = 0
            self._map_ui_redraw_content()
        elif 114 <= cid <= 119:  # Click en item
            items = self._map_ui_elem_get_filtered()
            idx = self._ui_elem_page * _ITEMS_PER_PAGE + (cid - 114)
            if idx < len(items):
                self._ui_elem_detail_id = items[idx]
                self._map_ui_redraw_content()
        elif cid == 120:  # Página anterior
            if self._ui_elem_page > 0:
                self._ui_elem_page -= 1
                self._map_ui_redraw_content()
        elif cid == 122:  # Página siguiente
            items = self._map_ui_elem_get_filtered()
            total_pages = max(1, (len(items) + _ITEMS_PER_PAGE - 1) // _ITEMS_PER_PAGE)
            if self._ui_elem_page < total_pages - 1:
                self._ui_elem_page += 1
                self._map_ui_redraw_content()

    # ──────────────────────────────────────────────────────────────────────────
    # Cierre
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_close(self):
        self.send_ISP_BFN(SubT=BFN.CLEAR, UCID=self._ui_ucid)
        self._ui_ucid = None
        self._ui_pending_action = None
        self._ui_input_buffer = {}
