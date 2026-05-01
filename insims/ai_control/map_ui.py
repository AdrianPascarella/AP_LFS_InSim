from __future__ import annotations
import copy
import math
import os
import time
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
        ("indicators",       "enum_indicators"),
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
        self._ui_info_stats: bool = False
        self._ui_info_check: bool = False
        self._ui_check_filter: str = "all"   # "all" | "error" | "warn"
        self._ui_check_page: int = 0
        self._ui_check_search: str = ""
        self._ui_info_roads: bool = False
        self._ui_roads_filter: str = "all"   # "all" | "open" | "closed"
        self._ui_roads_page: int = 0
        self._ui_roads_search: str = ""
        self._ui_whereami: set = set()
        self._ui_whereami_interval: float = 5.0
        self._ui_whereami_last_update: float = 0.0
        self._ui_road_picker_page: int = 0
        self._ui_road_picker_slot: str = "a"  # "a" | "b"

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
        self.send_ISP_BFN(SubT=BFN.DEL_BTN, UCID=0, ClickID=108, ClickMax=165)

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
        elif self._ui_pending_action in ("rec_road", "rec_zona", "rec_rule"):
            self._map_ui_draw_grabar_one_arg()
        else:
            self._map_ui_draw_grabar_idle()

    def _map_ui_draw_grabar_idle(self):
        u = self._ui_ucid
        for cid, label, L, T in [
            (110, "Road",          2,  21),
            (111, "RoadLink",     36,  21),
            (112, "LatLink",      70,  21),
            (113, "Zona",          2,  31),
            (114, "Reg. Especial", 36, 31),
        ]:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=cid,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                              L=L, T=T, W=32, H=8, Text=label)

        auto_on = self.map_recorder.auto_recording_enabled
        style = ISB_STYLE.OK | ISB_STYLE.CLICK if auto_on else ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=115,
                          BStyle=style, L=2, T=43, W=40, H=8,
                          Text="Auto: ON" if auto_on else "Auto: OFF")

    def _map_ui_draw_grabar_one_arg(self):
        u = self._ui_ucid
        labels = {"rec_road": "ID de la vía:", "rec_zona": "ID de la zona:", "rec_rule": "ID de la regla:"}
        names  = {"rec_road": "Road",          "rec_zona": "Zona",           "rec_rule": "Reg. Especial"}
        label = labels.get(self._ui_pending_action, "ID:")
        name  = names.get(self._ui_pending_action, "")

        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=110,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=2, T=21, W=80, H=6, Text=label)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI1,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 40,
                          L=2, T=28, W=100, H=8,
                          Text=self._ui_input_buffer.get(self._UI_CID_TI1, ""))
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=116,
                          BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
                          L=2, T=39, W=50, H=8, Text=f"Iniciar {name}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=117,
                          BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
                          L=54, T=39, W=30, H=8, Text="Cancelar")

    # CIDs 118/119 se usan como TypeIn de sufijo en el formulario de dos args
    _UI_CID_TI_SUF_A = 118
    _UI_CID_TI_SUF_B = 119

    _UI_ROAD_PICKER_ITEMS = 6  # items visibles en el picker

    def _map_ui_draw_grabar_two_args(self):
        u = self._ui_ucid
        is_roadlink = (self._ui_pending_action == "rec_roadlink")
        label_a = "Road origen:" if is_roadlink else "Road A:"
        label_b = "Road destino:" if is_roadlink else "Road B:"
        action_name = "RoadLink" if is_roadlink else "LatLink"

        # ── Columna izquierda: picker de roads (L=2, W=68) ──────────────────
        all_roads = sorted(self.map_recorder.roads.keys())
        total = len(all_roads)
        per_page = self._UI_ROAD_PICKER_ITEMS
        max_page = max(0, (total - 1) // per_page) if total else 0
        page = min(self._ui_road_picker_page, max_page)
        self._ui_road_picker_page = page
        items = all_roads[page * per_page:(page + 1) * per_page]

        # Toggle slot A / B
        slot = self._ui_road_picker_slot
        style_a = (ISB_STYLE.OK | ISB_STYLE.CLICK) if slot == "a" else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        style_b = (ISB_STYLE.OK | ISB_STYLE.CLICK) if slot == "b" else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=120,
                          BStyle=style_a, L=2, T=21, W=32, H=6, Text=f"→ A")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=121,
                          BStyle=style_b, L=36, T=21, W=32, H=6, Text=f"→ B")

        if not all_roads:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=122,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                              L=2, T=28, W=68, H=6, Text="Sin roads")
        else:
            for i, road_id in enumerate(items):
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=122 + i,
                                  BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK | ISB_STYLE.LEFT,
                                  L=2, T=28 + i * 7, W=68, H=6,
                                  Text=road_id)
            # Rellena slots vacíos para no dejar botones huérfanos
            for i in range(len(items), per_page):
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=122 + i,
                                  BStyle=ISB_STYLE.DARK, L=2, T=28 + i * 7, W=68, H=6, Text="")

        # Paginación picker
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=128,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                          L=2, T=71, W=20, H=6, Text="<")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=129,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                          L=24, T=71, W=24, H=6, Text=f"{page+1}/{max_page+1}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=132,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                          L=50, T=71, W=20, H=6, Text=">")

        # ── Columna derecha: formulario (L=72) ──────────────────────────────
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=110,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=72, T=21, W=66, H=6, Text=label_a)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=111,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=140, T=21, W=44, H=6, Text="sufijo:")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI1,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 40,
                          L=72, T=28, W=66, H=8,
                          Text=self._ui_input_buffer.get(self._UI_CID_TI1, ""))
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI_SUF_A,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 20,
                          L=140, T=28, W=44, H=8,
                          Text=self._ui_input_buffer.get(self._UI_CID_TI_SUF_A, ""))

        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=112,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=72, T=39, W=66, H=6, Text=label_b)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=113,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                          L=140, T=39, W=44, H=6, Text="sufijo:")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI2,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 40,
                          L=72, T=46, W=66, H=8,
                          Text=self._ui_input_buffer.get(self._UI_CID_TI2, ""))
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._UI_CID_TI_SUF_B,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 20,
                          L=140, T=46, W=44, H=8,
                          Text=self._ui_input_buffer.get(self._UI_CID_TI_SUF_B, ""))

        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=116,
                          BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
                          L=72, T=58, W=56, H=8, Text=f"Iniciar {action_name}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=117,
                          BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
                          L=130, T=58, W=34, H=8, Text="Cancelar")

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

    _CHECK_ITEMS_PER_PAGE = 4
    _WA_TYPES = ["road", "roadlink", "latlink", "zone", "rule"]
    _WA_CID_BASE = 153

    def _map_ui_draw_tab_info(self):
        u = self._ui_ucid
        # Fila 1: Stats / Check / Roads cerradas
        stats_style = (ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if self._ui_info_stats else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        check_style = (ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if self._ui_info_check else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        roads_style = (ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if self._ui_info_roads else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=110, BStyle=stats_style, L=2,  T=21, W=38, H=8, Text="Stats")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=111, BStyle=check_style, L=42, T=21, W=38, H=8, Text="Check")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=112, BStyle=roads_style, L=82, T=21, W=38, H=8, Text="Roads cerradas")

        # Fila 2: Whereami toggles (5 tipos) + TypeIn intervalo
        for i, label in enumerate(["WA Road", "WA RLink", "WA LLink", "WA Zone", "WA Regla"]):
            active = self._WA_TYPES[i] in self._ui_whereami
            style = (ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if active else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=113 + i, BStyle=style,
                              L=2 + i * 34, T=31, W=30, H=8, Text=label)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=147,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 8,
                          L=172, T=31, W=14, H=8,
                          Text=str(self._ui_whereami_interval))

        T = 42
        if self._ui_info_stats:
            mr = self.map_recorder
            counts = [
                ("Roads",     len(mr.roads)),
                ("RoadLinks", len(mr.road_links)),
                ("LatLinks",  len(mr.lateral_links)),
                ("Zonas",     len(mr.zones)),
                ("Reglas",    len(mr.special_rules)),
            ]
            for i, (label, n) in enumerate(counts):
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=148 + i,
                                  BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                                  L=2 + i * 38, T=T, W=36, H=8,
                                  Text=f"{label}: {n}")
            T += 10

        if self._ui_info_check:
            self._map_ui_draw_check_panel(T)
            T += 9 + 9 + self._CHECK_ITEMS_PER_PAGE * 8 + 8

        if self._ui_info_roads:
            self._map_ui_draw_roads_panel(T)
            T += 9 + 9 + self._ROADS_ITEMS_PER_PAGE * 8 + 6

        self._map_ui_draw_whereami_panels(T)

    def _map_ui_draw_check_panel(self, T: int):
        u = self._ui_ucid
        if not self.map_recorder.active_map_name:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=121,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                              L=2, T=T, W=180, H=7, Text="Sin mapa activo")
            return

        errores, advertencias = self.map_recorder.collect_check_results()
        search = self._ui_check_search.lower()
        all_items = [("E", m) for m in errores] + [("W", m) for m in advertencias]
        if self._ui_check_filter == "error":
            all_items = [x for x in all_items if x[0] == "E"]
        elif self._ui_check_filter == "warn":
            all_items = [x for x in all_items if x[0] == "W"]
        if search:
            all_items = [x for x in all_items if search in x[1].lower()]

        n_err, n_warn = len(errores), len(advertencias)
        total_pages = max(1, (len(all_items) + self._CHECK_ITEMS_PER_PAGE - 1) // self._CHECK_ITEMS_PER_PAGE)
        self._ui_check_page = max(0, min(self._ui_check_page, total_pages - 1))

        # Buscador (CID 121 TypeIn, CID 122 botón)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=121,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 60,
                          L=2, T=T, W=132, H=7,
                          Text=self._ui_check_search or "Buscar...")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=122,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                          L=136, T=T, W=22, H=7, Text="Filtrar")
        T += 9

        # Filtros tipo (CIDs 123–125)
        for i, (key, label) in enumerate([("all", f"Todos ({n_err}E {n_warn}W)"), ("error", f"Errores ({n_err})"), ("warn", f"Avisos ({n_warn})")]):
            active = (self._ui_check_filter == key)
            style = (ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if active else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=123 + i, BStyle=style,
                              L=2 + i * 62, T=T, W=60, H=7, Text=label)
        T += 9

        # Items (CIDs 126–129)
        start = self._ui_check_page * self._CHECK_ITEMS_PER_PAGE
        page_items = all_items[start:start + self._CHECK_ITEMS_PER_PAGE]
        if not page_items:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=126,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                              L=2, T=T, W=180, H=7, Text="Sin resultados")
        else:
            for i, (sev, msg) in enumerate(page_items):
                style = ISB_STYLE.CANCEL | ISB_STYLE.DARK if sev == "E" else ISB_STYLE.TITLE | ISB_STYLE.DARK
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=126 + i, BStyle=style,
                                  L=2, T=T + i * 8, W=180, H=7, Text=msg)

        # Paginación (CIDs 130–132)
        prev_style = (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if self._ui_check_page > 0 else (ISB_STYLE.DARK | ISB_STYLE.SELECTED)
        next_style = (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if self._ui_check_page < total_pages - 1 else (ISB_STYLE.DARK | ISB_STYLE.SELECTED)
        pag_T = T + self._CHECK_ITEMS_PER_PAGE * 8
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=130, BStyle=prev_style, L=2,  T=pag_T, W=16, H=6, Text="<")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=131, BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                          L=20, T=pag_T, W=50, H=6, Text=f"Pag {self._ui_check_page + 1}/{total_pages}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=132, BStyle=next_style, L=72, T=pag_T, W=16, H=6, Text=">")

    _ROADS_ITEMS_PER_PAGE = 6

    def _map_ui_draw_roads_panel(self, T: int):
        u = self._ui_ucid
        if not self.map_recorder.active_map_name:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=133,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                              L=2, T=T, W=180, H=7, Text="Sin mapa activo")
            return

        search = self._ui_roads_search.lower()
        all_roads = [(r_id, road.is_closed) for r_id, road in self.map_recorder.roads.items()]
        if self._ui_roads_filter == "open":
            all_roads = [(r, c) for r, c in all_roads if not c]
        elif self._ui_roads_filter == "closed":
            all_roads = [(r, c) for r, c in all_roads if c]
        if search:
            all_roads = [(r, c) for r, c in all_roads if search in r.lower()]
        all_roads.sort(key=lambda x: x[0])

        n_open   = sum(1 for road in self.map_recorder.roads.values() if not road.is_closed)
        n_closed = sum(1 for road in self.map_recorder.roads.values() if road.is_closed)
        total_pages = max(1, (len(all_roads) + self._ROADS_ITEMS_PER_PAGE - 1) // self._ROADS_ITEMS_PER_PAGE)
        self._ui_roads_page = max(0, min(self._ui_roads_page, total_pages - 1))

        # Buscador (CID 133 TypeIn, 134 botón)
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=133,
                          BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                          TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 60,
                          L=2, T=T, W=132, H=7,
                          Text=self._ui_roads_search or "Buscar...")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=134,
                          BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                          L=136, T=T, W=22, H=7, Text="Filtrar")
        T += 9

        # Filtros tipo (CIDs 135–137)
        for i, (key, label) in enumerate([("all", f"Todos ({n_open}A {n_closed}C)"), ("open", f"Abiertos ({n_open})"), ("closed", f"Cerrados ({n_closed})")]):
            active = (self._ui_roads_filter == key)
            style = (ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if active else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=135 + i, BStyle=style,
                              L=2 + i * 62, T=T, W=60, H=7, Text=label)
        T += 9

        # Items (CIDs 138–143)
        start = self._ui_roads_page * self._ROADS_ITEMS_PER_PAGE
        page_items = all_roads[start:start + self._ROADS_ITEMS_PER_PAGE]
        if not page_items:
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=138,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                              L=2, T=T, W=180, H=7, Text="Sin resultados")
        else:
            for i, (r_id, is_closed) in enumerate(page_items):
                style = (ISB_STYLE.CANCEL | ISB_STYLE.DARK | ISB_STYLE.CLICK) if is_closed else (ISB_STYLE.OK | ISB_STYLE.CLICK)
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=138 + i, BStyle=style,
                                  L=2, T=T + i * 8, W=180, H=7, Text=r_id)

        # Paginación (CIDs 144–146)
        prev_style = (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if self._ui_roads_page > 0 else (ISB_STYLE.DARK | ISB_STYLE.SELECTED)
        next_style = (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK) if self._ui_roads_page < total_pages - 1 else (ISB_STYLE.DARK | ISB_STYLE.SELECTED)
        pag_T = T + self._ROADS_ITEMS_PER_PAGE * 8
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=144, BStyle=prev_style, L=2,  T=pag_T, W=16, H=6, Text="<")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=145, BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                          L=20, T=pag_T, W=50, H=6, Text=f"Pag {self._ui_roads_page + 1}/{total_pages}")
        self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=146, BStyle=next_style, L=72, T=pag_T, W=16, H=6, Text=">")

    def _map_ui_draw_whereami_panels(self, T: int) -> int:
        u = self._ui_ucid
        for i, wa_type in enumerate(self._WA_TYPES):
            if wa_type not in self._ui_whereami:
                continue
            result = self._map_ui_compute_whereami(wa_type)
            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=self._WA_CID_BASE + i,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                              L=2, T=T, W=180, H=7, Text=result)
            T += 8
        return T

    def _map_ui_compute_whereami(self, target: str) -> str:
        mr = self.map_recorder
        if not mr.active_map_name:
            return "Sin mapa activo"
        coords = mr.get_coords_fn(self._ui_ucid)
        if not coords:
            return "Sin telemetria"
        px, py, pz = coords.x_m, coords.y_m, coords.z_m

        if target == "road":
            if not mr.roads:
                return "WA Road: Sin roads"
            res = mr.get_closest_geometry(px, py, pz, mr.roads.items(), lambda r: r.nodes)
            if res['id'] is None:
                return "WA Road: Sin datos"
            status = "TOCANDO" if res['dist'] <= 3.0 else f"{res['dist']:.1f}m"
            return f"WA Road: {res['id']} | {status}"

        elif target == "roadlink":
            if not mr.road_links:
                return "WA RLink: Sin links"
            res = mr.get_closest_geometry(px, py, pz, mr.road_links.items(), lambda l: l.nodes)
            if res['id'] is None:
                return "WA RLink: Sin datos"
            status = "TOCANDO" if res['dist'] <= 2.0 else f"{res['dist']:.1f}m"
            return f"WA RLink: {res['id']} | {status}"

        elif target == "latlink":
            if not mr.lateral_links:
                return "WA LLink: Sin links"
            res = mr.get_closest_geometry(px, py, pz, mr.lateral_links.items(), lambda l: l.nodes)
            if res['id'] is None:
                return "WA LLink: Sin datos"
            status = "TOCANDO" if res['dist'] <= 2.0 else f"{res['dist']:.1f}m"
            return f"WA LLink: {res['id']} | {status}"

        elif target == "zone":
            ctx = mr.get_location_context(px, py, pz, find_roads=False, find_links=False, find_zones=True)
            if ctx.zone_id is None:
                return "WA Zona: Sin zonas"
            status = "DENTRO" if ctx.zone_dist <= ctx.zone_radius else f"{ctx.zone_dist:.1f}m"
            return f"WA Zona: {ctx.zone_id} | {status}"

        elif target == "rule":
            if not mr.special_rules:
                return "WA Regla: Sin reglas"
            best_id = None
            best_dist = float('inf')
            best_node_idx = 0
            best_radius = 8.0
            for rule_id, rule in mr.special_rules.items():
                for n_idx, node in enumerate(rule.nodes[:2]):
                    d = math.sqrt((px - node.x_m)**2 + (py - node.y_m)**2 + (pz - node.z_m)**2)
                    if d < best_dist:
                        best_dist = d
                        best_id = rule_id
                        best_node_idx = n_idx
                        best_radius = rule.radius_m
            if best_id is None:
                return "WA Regla: Sin datos"
            node_label = "ACTIVAR" if best_node_idx == 0 else "DESACTIVAR"
            status = "TOCANDO" if best_dist <= best_radius else f"{best_dist:.1f}m"
            return f"WA Regla: {best_id} [{node_label}] | {status}"

        return "WA: tipo desconocido"

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

        # Filas de campos (máx. 8 filas, spacing=7 para que row7 quede en T=78)
        self._ui_detail_field_map = {}
        for row, (fname, ftype) in enumerate(fields_def[:8]):
            T = 29 + row * 7
            label_cid = 111 + row * 2
            val_cid   = 112 + row * 2

            val_str = self._map_ui_elem_field_value_str(obj, fname)

            self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=label_cid,
                              BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                              L=2, T=T, W=68, H=6, Text=f"{fname}:")

            if ftype == "readonly":
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=val_cid,
                                  BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                                  L=72, T=T, W=108, H=6, Text=val_str)
            elif ftype == "bool":
                is_true = val_str.lower() in ("true", "yes", "si", "1")
                style = (ISB_STYLE.OK | ISB_STYLE.CLICK) if is_true else (ISB_STYLE.CANCEL | ISB_STYLE.CLICK)
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=val_cid,
                                  BStyle=style, L=72, T=T, W=108, H=6,
                                  Text="ON" if is_true else "OFF")
                self._ui_detail_field_map[val_cid] = (fname, "bool")
            elif ftype == "enum_traffic":
                style = ISB_STYLE.OK | ISB_STYLE.CLICK if val_str == "RHT" else ISB_STYLE.TITLE | ISB_STYLE.CLICK
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=val_cid,
                                  BStyle=style, L=72, T=T, W=108, H=6,
                                  Text=val_str if val_str else "RHT")
                self._ui_detail_field_map[val_cid] = (fname, "enum_traffic")
            elif ftype == "enum_indicators":
                ind_styles = {"OFF": ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                              "LEFT": ISB_STYLE.TITLE | ISB_STYLE.CLICK,
                              "RIGHT": ISB_STYLE.OK | ISB_STYLE.CLICK}
                style = ind_styles.get(val_str, ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=val_cid,
                                  BStyle=style, L=72, T=T, W=108, H=6,
                                  Text=val_str if val_str else "OFF")
                self._ui_detail_field_map[val_cid] = (fname, "enum_indicators")
            else:
                self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=val_cid,
                                  BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                                  TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 48,
                                  L=72, T=T, W=108, H=6, Text=val_str)
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

    def on_tick(self):
        super().on_tick()
        if self._ui_ucid is None or self._ui_tab != "info" or not self._ui_whereami:
            return
        now = time.time()
        if now - self._ui_whereami_last_update < self._ui_whereami_interval:
            return
        self._ui_whereami_last_update = now
        for i, wa_type in enumerate(self._WA_TYPES):
            if wa_type in self._ui_whereami:
                result = self._map_ui_compute_whereami(wa_type)
                self.send_ISP_BTN(ReqI=1, UCID=self._ui_ucid,
                                  ClickID=self._WA_CID_BASE + i,
                                  BStyle=0, L=0, T=0, W=0, H=0, Text=result)

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
        # Intervalo de refresco whereami
        if self._ui_tab == "info" and packet.ClickID == 147:
            try:
                val = float(text)
                if val > 0:
                    self._ui_whereami_interval = val
                    self._ui_whereami_last_update = 0.0
            except ValueError:
                self.send_ISP_BTN(ReqI=1, UCID=self._ui_ucid,
                                  ClickID=147, BStyle=0, L=0, T=0, W=0, H=0,
                                  Text=str(self._ui_whereami_interval))
            return

        # En la vista detalle de Elementos, aplicar cambio inmediatamente
        if (self._ui_tab == "elementos"
                and self._ui_elem_detail_id is not None
                and packet.ClickID in self._ui_detail_field_map):
            fname, ftype = self._ui_detail_field_map[packet.ClickID]
            if ftype not in ("bool", "enum_traffic", "enum_indicators") and text:
                if ftype == "float":
                    try:
                        float(text)
                    except ValueError:
                        obj = self._map_ui_elem_get_obj(self._ui_elem_detail_id)
                        prev = self._map_ui_elem_field_value_str(obj, fname) if obj else ""
                        self.send_ISP_BTN(ReqI=1, UCID=self._ui_ucid,
                                          ClickID=packet.ClickID,
                                          BStyle=0, L=0, T=0, W=0, H=0,
                                          Text=prev if prev else " ")
                        return
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
            if cid == 120:  # toggle slot A
                self._ui_road_picker_slot = "a"
                self._map_ui_redraw_content()
            elif cid == 121:  # toggle slot B
                self._ui_road_picker_slot = "b"
                self._map_ui_redraw_content()
            elif 122 <= cid <= 127:  # seleccionar road del picker
                all_roads = sorted(self.map_recorder.roads.keys())
                per_page = self._UI_ROAD_PICKER_ITEMS
                idx = self._ui_road_picker_page * per_page + (cid - 122)
                if idx < len(all_roads):
                    road_id = all_roads[idx]
                    if self._ui_road_picker_slot == "a":
                        buf[self._UI_CID_TI1] = road_id
                        self._ui_road_picker_slot = "b"  # avanza al slot B automáticamente
                    else:
                        buf[self._UI_CID_TI2] = road_id
                    self._map_ui_redraw_content()
            elif cid == 128:  # página anterior picker
                if self._ui_road_picker_page > 0:
                    self._ui_road_picker_page -= 1
                    self._map_ui_redraw_content()
            elif cid == 132:  # página siguiente picker
                all_roads = sorted(self.map_recorder.roads.keys())
                max_page = max(0, (len(all_roads) - 1) // self._UI_ROAD_PICKER_ITEMS)
                if self._ui_road_picker_page < max_page:
                    self._ui_road_picker_page += 1
                    self._map_ui_redraw_content()
            elif cid == 116:
                road_a = buf.get(self._UI_CID_TI1, "").strip()
                suf_a  = buf.get(self._UI_CID_TI_SUF_A, "").strip()
                road_b = buf.get(self._UI_CID_TI2, "").strip()
                suf_b  = buf.get(self._UI_CID_TI_SUF_B, "").strip()
                if road_a and road_b:
                    arg_a = f"{road_a},{suf_a}" if suf_a else road_a
                    arg_b = f"{road_b},{suf_b}" if suf_b else road_b
                    self.map_recorder._current_cmd_ucid = self._ui_ucid
                    if self._ui_pending_action == "rec_roadlink":
                        self.map_recorder._cmd_rec_roadlink(arg_a, arg_b)
                    else:
                        self.map_recorder._cmd_rec_laterallink(arg_a, arg_b)
                    self._ui_pending_action = None
                    self._ui_input_buffer = {}
                    self._ui_road_picker_page = 0
                    self._ui_road_picker_slot = "a"
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(Msg=f"{c.RED}Rellena ambos campos antes de confirmar.")
            elif cid == 117:
                self._ui_pending_action = None
                self._ui_input_buffer = {}
                self._ui_road_picker_page = 0
                self._ui_road_picker_slot = "a"
                self._map_ui_redraw_content()

        elif self._ui_pending_action in ("rec_road", "rec_zona", "rec_rule"):
            if cid == 116:
                obj_id = buf.get(self._UI_CID_TI1, "").strip()
                if obj_id:
                    self.map_recorder._current_cmd_ucid = self._ui_ucid
                    if self._ui_pending_action == "rec_road":
                        self.map_recorder._cmd_rec_road(obj_id)
                    elif self._ui_pending_action == "rec_zona":
                        self.map_recorder._cmd_rec_zone(obj_id)
                    else:
                        self.map_recorder._cmd_rec_special_rule(obj_id)
                    self._ui_pending_action = None
                    self._ui_input_buffer = {}
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(Msg=f"{c.RED}Escribe el ID antes de confirmar.")
            elif cid == 117:
                self._ui_pending_action = None
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()

        else:
            if cid == 110:
                self._ui_pending_action = "rec_road"
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()
            elif cid == 111:
                self._ui_pending_action = "rec_roadlink"
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()
            elif cid == 112:
                self._ui_pending_action = "rec_laterallink"
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()
            elif cid == 113:
                self._ui_pending_action = "rec_zona"
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()
            elif cid == 114:
                self._ui_pending_action = "rec_rule"
                self._ui_input_buffer = {}
                self._map_ui_redraw_content()
            elif cid == 115:
                new = not self.map_recorder.auto_recording_enabled
                self.map_recorder._cmd_rec_auto("true" if new else "false")
                self._map_ui_redraw_content()

    def _map_ui_click_info(self, cid: int):
        fake = _FakePkt(self._ui_ucid)
        if cid == 110:
            self._ui_info_stats = not self._ui_info_stats
            self._map_ui_redraw_content()
        elif cid == 111:
            self._ui_info_check = not self._ui_info_check
            self._ui_check_page = 0
            self._map_ui_redraw_content()
        elif cid == 122:  # Aplicar buscador
            self._ui_check_search = self._ui_input_buffer.get(121, "").strip()
            self._ui_check_page = 0; self._map_ui_redraw_content()
        elif cid == 123:
            self._ui_check_filter = "all";   self._ui_check_page = 0; self._map_ui_redraw_content()
        elif cid == 124:
            self._ui_check_filter = "error"; self._ui_check_page = 0; self._map_ui_redraw_content()
        elif cid == 125:
            self._ui_check_filter = "warn";  self._ui_check_page = 0; self._map_ui_redraw_content()
        elif cid == 130 and self._ui_check_page > 0:
            self._ui_check_page -= 1; self._map_ui_redraw_content()
        elif cid == 132:
            errores, advertencias = self.map_recorder.collect_check_results()
            search = self._ui_check_search.lower()
            all_items = [("E", m) for m in errores] + [("W", m) for m in advertencias]
            if self._ui_check_filter == "error":
                all_items = [x for x in all_items if x[0] == "E"]
            elif self._ui_check_filter == "warn":
                all_items = [x for x in all_items if x[0] == "W"]
            if search:
                all_items = [x for x in all_items if search in x[1].lower()]
            total_pages = max(1, (len(all_items) + self._CHECK_ITEMS_PER_PAGE - 1) // self._CHECK_ITEMS_PER_PAGE)
            if self._ui_check_page < total_pages - 1:
                self._ui_check_page += 1; self._map_ui_redraw_content()
        elif cid == 112:
            self._ui_info_roads = not self._ui_info_roads
            self._ui_roads_page = 0
            self._map_ui_redraw_content()
        elif cid == 134:  # Aplicar buscador roads
            self._ui_roads_search = self._ui_input_buffer.get(133, "").strip()
            self._ui_roads_page = 0; self._map_ui_redraw_content()
        elif cid == 135:
            self._ui_roads_filter = "all";    self._ui_roads_page = 0; self._map_ui_redraw_content()
        elif cid == 136:
            self._ui_roads_filter = "open";   self._ui_roads_page = 0; self._map_ui_redraw_content()
        elif cid == 137:
            self._ui_roads_filter = "closed"; self._ui_roads_page = 0; self._map_ui_redraw_content()
        elif 138 <= cid <= 143:  # Toggle is_closed de un road
            start = self._ui_roads_page * self._ROADS_ITEMS_PER_PAGE
            search = self._ui_roads_search.lower()
            all_roads = [(r_id, road.is_closed) for r_id, road in self.map_recorder.roads.items()]
            if self._ui_roads_filter == "open":
                all_roads = [(r, c) for r, c in all_roads if not c]
            elif self._ui_roads_filter == "closed":
                all_roads = [(r, c) for r, c in all_roads if c]
            if search:
                all_roads = [(r, c) for r, c in all_roads if search in r.lower()]
            all_roads.sort(key=lambda x: x[0])
            idx = start + (cid - 138)
            if idx < len(all_roads):
                r_id, is_closed = all_roads[idx]
                self._map_ui_silent_set(r_id, "is_closed", "false" if is_closed else "true")
                self._map_ui_redraw_content()
        elif cid == 144 and self._ui_roads_page > 0:
            self._ui_roads_page -= 1; self._map_ui_redraw_content()
        elif cid == 146:
            search = self._ui_roads_search.lower()
            all_roads = [(r_id, road.is_closed) for r_id, road in self.map_recorder.roads.items()]
            if self._ui_roads_filter == "open":
                all_roads = [(r, c) for r, c in all_roads if not c]
            elif self._ui_roads_filter == "closed":
                all_roads = [(r, c) for r, c in all_roads if c]
            if search:
                all_roads = [(r, c) for r, c in all_roads if search in r.lower()]
            total_pages = max(1, (len(all_roads) + self._ROADS_ITEMS_PER_PAGE - 1) // self._ROADS_ITEMS_PER_PAGE)
            if self._ui_roads_page < total_pages - 1:
                self._ui_roads_page += 1; self._map_ui_redraw_content()
        elif 113 <= cid <= 117:
            wa_type = self._WA_TYPES[cid - 113]
            if wa_type in self._ui_whereami:
                self._ui_whereami.discard(wa_type)
            else:
                self._ui_whereami.add(wa_type)
            self._map_ui_redraw_content()

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
                elif ftype == "enum_indicators":
                    obj = self._map_ui_elem_get_obj(self._ui_elem_detail_id)
                    if obj is not None:
                        cur = self._map_ui_elem_field_value_str(obj, fname)
                        cycle = {"OFF": "left", "LEFT": "right", "RIGHT": "off", "": "off"}
                        new_val = cycle.get(cur, "off")
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
