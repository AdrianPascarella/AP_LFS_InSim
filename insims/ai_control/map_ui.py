from __future__ import annotations

import copy
import math
import os
import time
from typing import Optional

from insims.ai_control.base import _MixinBase
from insims.ai_control.nav_modes.freeroam.geometry import find_road_pointed_at
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from insims.ai_control.traffic.yielding import DEFAULT_YIELD_TIME_S
from lfs_insim.insim_enums import BFN, ISB_STYLE, TYPEIN_FLAGS
from lfs_insim.packets import ISP_BTC, ISP_BTT, ISP_MSO
from lfs_insim.utils import TextColors as c


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
        ("road_id", "readonly"),
        ("nodes", "readonly"),
        ("speed_limit_kmh", "float"),
        ("is_circular", "bool"),
        ("is_closed", "bool"),
        ("traffic_rule", "enum_traffic"),
    ],
    "roadlink": [
        ("from_road_id", "readonly"),
        ("to_road_id", "readonly"),
        ("nodes", "readonly"),
        ("speed_limit_kmh", "float"),
        ("from_suffix", "readonly"),
        ("to_suffix", "readonly"),
        ("by_road_id", "str"),
        ("indicators", "enum_indicators"),
    ],
    "latlink": [
        ("road_a", "readonly"),
        ("road_b", "readonly"),
        ("nodes", "readonly"),
        ("allow_a_to_b", "bool"),
        ("allow_b_to_a", "bool"),
        ("opposing", "bool"),
        ("is_circular", "bool"),
        ("made_to_overtake", "bool"),
    ],
    "zone": [
        ("zone_id", "readonly"),
        ("nodes", "readonly"),
        ("radius_m", "float"),
    ],
    "rule": [
        ("rule_id", "readonly"),
        ("nodes", "readonly"),
        ("radius_m", "float"),
        ("speed_limit", "float"),
        ("no_lane_change", "bool"),
    ],
}

_ELEM_TYPE_LABELS: dict[str, str] = {
    "road": "Roads",
    "roadlink": "RoadLinks",
    "latlink": "LatLinks",
    "zone": "Zonas",
    "rule": "Reglas",
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
    _UI_CID_CLOSE = 100
    _UI_CID_SAVE = 101
    _UI_CID_LBL_MAP = 102
    _UI_CID_LBL_REC = 103
    _UI_CID_TAB_MAPA = 104
    _UI_CID_TAB_GRAB = 105
    _UI_CID_TAB_INFO = 106
    _UI_CID_TAB_ELEM = 107
    _UI_CID_TAB_DBG = 99
    _UI_CID_TAB_RUN = 98
    # 108-129: área de contenido (se limpian y redibujan en cada cambio de tab)
    _UI_CID_TI1 = 130  # TypeIn primario
    _UI_CID_TI2 = 131  # TypeIn secundario
    _UI_CID_TI3 = 132  # TypeIn terciario
    _UI_CID_LBL_CONF = 133  # Label de confirmación

    # Editor de reglas de prioridad de Zonas (solo en el detalle de una zona,
    # tras sus campos estándar). CIDs 140-151, dentro del área de contenido
    # (108-165) que se limpia en cada redibujado.
    _ZONE_PRIO_TITLE = 140
    _ZONE_PRIO_ADD = 141  # botón "+ Anadir regla" (abre el picker de vías)
    _ZONE_PRIO_ROW_BASE = 142  # regla i: label 142+i*2, quitar 143+i*2
    _ZONE_PRIO_MAX_ROWS = 5
    # La sub-pantalla de alta (picker de vías) REUTILIZA los CIDs y la mecánica
    # del picker de RoadLink/LatLink: slots 120/121, lista 122-127, paginación
    # 128/129/132, seleccionados 110/112, Confirmar 116, Cancelar 117. Las vías
    # elegidas viven en _UI_CID_TI1 (prioritaria) y _UI_CID_TI2 (cede).

    # Sección de CESIÓN del detalle de un RoadLink (Fase 8, bloque 8.4).
    # CIDs 152-159, dentro del área de contenido (108-165), tras las filas de
    # campos (111-126) y sin pisar el editor de prioridad de Zonas (140-151).
    _LINK_YIELD_TITLE = 152
    _LINK_YIELD_STATUS = 153  # label de estado ("no cede" / "N puntos")
    _LINK_YIELD_REC = 154  # "+ Grabar linea" / "Regrabar" (abre el grabador)
    _LINK_YIELD_CLEAR = 155  # "Quitar" la cesión (solo si hay línea)
    _LINK_YIELD_T_LBL = 156
    _LINK_YIELD_T_VAL = 157  # TypeIn de T (s) en el propio detalle
    _LINK_YIELD_ZONE_LBL = 158
    _LINK_YIELD_ZONE_VAL = 159  # abre el picker de zonas
    # Las sub-pantallas del grabador REUTILIZAN la semántica de la pestaña
    # Grabar: 112 añadir punto, 113 auto, 114 terminar, 115 cancelar; la de
    # "pedir T" usa TI1 (130) + 116 Guardar + 117 Volver; el picker de zonas
    # usa la mecánica del picker de vías (items 122-127, pág. 128/129/132,
    # 116 Ninguna, 117 Cancelar). El estado del grabador vive en
    # map_recorder.current_recording (type="yield_line", auto_phase) para
    # sobrevivir a cerrar/reabrir el menú, como "Link auto".

    # Overlay whereami "pineado" — CIDs FUERA del rango de contenido (108-165)
    # para sobrevivir a cambios de pestaña y al cierre del menú. Anclado a la
    # mitad-derecha de la pantalla; solo se quita deseleccionándolo en Info.
    _WA_PIN_CID_TITLE = 166
    _WA_PIN_CID_BASE = 167  # una fila por tipo activo (167..171, orden de _WA_TYPES)
    _WA_PIN_L = 150
    _WA_PIN_W = 48
    _WA_PIN_H = 7
    _WA_PIN_ROW_STEP = 8

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
        self._ui_detail_field_map: dict = {}  # {ClickID: (field_name, field_type)}
        self._ui_zone_prio_map: dict = {}  # {ClickID quitar: (via_a, via_b)}
        self._ui_zone_prio_adding: bool = False  # sub-pantalla de alta de regla
        self._ui_link_zone_picking: bool = False  # picker de zona de un RoadLink
        self._ui_info_stats: bool = False
        self._ui_info_check: bool = False
        self._ui_check_filter: str = "all"  # "all" | "error" | "warn"
        self._ui_check_page: int = 0
        self._ui_check_search: str = ""
        self._ui_info_roads: bool = False
        self._ui_roads_filter: str = "all"  # "all" | "open" | "closed"
        self._ui_roads_page: int = 0
        self._ui_roads_search: str = ""
        # Overlay whereami "pineado": vive FUERA de la sesión de menú. Persiste al
        # cambiar de pestaña y al cerrar/reabrir el menú; solo se quita
        # deseleccionándolo en Info. Por eso NO se resetea en cada apertura del
        # menú: se inicializa una única vez (al construir el módulo).
        if not hasattr(self, "_ui_whereami"):
            self._ui_whereami: set = set()
            self._ui_whereami_ucid: Optional[int] = None
            self._ui_whereami_interval: float = 0.5
            self._ui_whereami_last_update: float = 0.0
        self._ui_road_picker_page: int = 0
        self._ui_road_picker_slot: str = "a"  # "a" | "b"
        self._ui_grabar_player_page: int = 0
        self._ui_debug_plid: Optional[int] = None
        self._ui_debug_interval: float = 1.0
        self._ui_debug_last_update: float = 0.0
        self._ui_debug_page: int = 0
        self._ui_node_flash_time: float = 0.0  # timestamp del último flash de nodo
        self._ui_run_target: int = getattr(self, "_target_freeroam_count", 1)
        self._ui_run_interval: float = getattr(self, "_freeroam_spawn_interval", 2.0)

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
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_LBL_MAP,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=4,
            W=76,
            H=6,
            Text=f"Mapa: {map_name}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_LBL_REC,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=80,
            T=4,
            W=74,
            H=6,
            Text=self._map_ui_rec_status(),
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_SAVE,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=156,
            T=4,
            W=18,
            H=6,
            Text="Guardar",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_CLOSE,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=176,
            T=4,
            W=8,
            H=6,
            Text="X",
        )

    def _map_ui_update_header(self):
        """Actualiza solo el texto de las labels del header (W=0, H=0)."""
        u = self._ui_ucid
        map_name = self.map_recorder.active_map_name or "(sin mapa)"
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_LBL_MAP,
            BStyle=0,
            L=0,
            T=0,
            W=0,
            H=0,
            Text=f"Mapa: {map_name}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_LBL_REC,
            BStyle=0,
            L=0,
            T=0,
            W=0,
            H=0,
            Text=self._map_ui_rec_status(),
        )

    def _map_ui_rec_status(self) -> str:
        rec = self.map_recorder.current_recording
        if not rec:
            return "Sin grabacion activa"
        if rec.get("auto"):
            origin = rec.get("origin_id", "?")
            dest = rec.get("dest_id") or "?"
            name = rec.get("pending_link_id") or f"{origin}->{dest}"
            n = len(rec.get("nodes", []))
            auto = " AUTO" if self.map_recorder.auto_recording_enabled else ""
            return f"REC: LINK-AUTO '{name}' ({n}pts{auto})"
        rec_type = rec.get("type", "?").upper()
        obj_id = (
            rec.get("road_id")
            or rec.get("link_id")
            or rec.get("zone_id")
            or rec.get("rule_id", "?")
        )
        n = len(rec.get("nodes", []))
        auto_flag = self.map_recorder.auto_recording_enabled
        if rec.get("type") == "yield_line":
            auto_flag = auto_flag and rec.get("auto_phase") == "recording"
        auto = " AUTO" if auto_flag else ""
        return f"REC: {rec_type} '{obj_id}' ({n}pts{auto})"

    # ──────────────────────────────────────────────────────────────────────────
    # Tabs (T=11, H=7)
    # ──────────────────────────────────────────────────────────────────────────

    _TAB_LAYOUT = [
        (_UI_CID_TAB_MAPA, "mapa", "Mapa", 2, 28),
        (_UI_CID_TAB_GRAB, "grabar", "Grabar", 32, 28),
        (_UI_CID_TAB_INFO, "info", "Info", 62, 24),
        (_UI_CID_TAB_ELEM, "elementos", "Elementos", 88, 34),
        (_UI_CID_TAB_DBG, "debug", "Debug", 124, 26),
        (_UI_CID_TAB_RUN, "run", "Run", 152, 32),
    ]
    _TAB_CID_TO_NAME = {
        _UI_CID_TAB_MAPA: "mapa",
        _UI_CID_TAB_GRAB: "grabar",
        _UI_CID_TAB_INFO: "info",
        _UI_CID_TAB_ELEM: "elementos",
        _UI_CID_TAB_DBG: "debug",
        _UI_CID_TAB_RUN: "run",
    }

    def _map_ui_draw_tabs(self):
        u = self._ui_ucid
        for cid, tab_name, label, L, W in self._TAB_LAYOUT:
            is_active = tab_name == self._ui_tab
            style = (
                (ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
                if is_active
                else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            )
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=cid,
                BStyle=style,
                L=L,
                T=11,
                W=W,
                H=7,
                Text=label,
            )

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
        elif self._ui_tab == "debug":
            self._map_ui_draw_tab_debug()
        elif self._ui_tab == "run":
            self._map_ui_draw_tab_run()

    # ──────────────────────────────────────────────────────────────────────────
    # Tab: Mapa
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_draw_tab_mapa(self):
        u = self._ui_ucid
        current_map = self.map_recorder.active_map_name or ""

        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_TI1,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 32,
            L=2,
            T=21,
            W=80,
            H=8,
            Text=current_map or "Nombre del mapa",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=84,
            T=21,
            W=32,
            H=8,
            Text="Seleccionar",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=111,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=31,
            W=40,
            H=8,
            Text="Guardar",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=112,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=44,
            T=31,
            W=40,
            H=8,
            Text="Borrar mapa",
        )

        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=113,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=42,
            W=60,
            H=5,
            Text="Mapas en disco:",
        )
        maps = self._map_ui_get_map_list()
        if maps:
            for i, name in enumerate(maps[:6]):
                is_active = name == current_map
                style = (
                    (ISB_STYLE.OK | ISB_STYLE.CLICK)
                    if is_active
                    else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
                )
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=114 + i,
                    BStyle=style,
                    L=2 + i * 30,
                    T=49,
                    W=28,
                    H=7,
                    Text=name,
                )
        else:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=114,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                L=2,
                T=49,
                W=60,
                H=7,
                Text="(sin mapas guardados)",
            )

    def _map_ui_get_map_list(self) -> list:
        from insims.ai_control.nav_modes.freeroam import map_recorder as _mr_mod

        base_dir = os.path.dirname(os.path.abspath(_mr_mod.__file__))
        maps_folder = os.path.join(base_dir, "maps")
        if not os.path.exists(maps_folder):
            return []
        return sorted(
            f.replace(".json", "")
            for f in os.listdir(maps_folder)
            if f.endswith(".json")
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Tab: Grabar
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_draw_tab_grabar(self):
        rec = self.map_recorder.current_recording
        if rec and rec.get("auto"):
            phase = rec.get("auto_phase")
            if phase == "confirm":
                self._map_ui_draw_auto_link_confirm(rec)
            elif phase == "conflict":
                self._map_ui_draw_auto_link_conflict(rec)
            else:
                self._map_ui_draw_auto_link_recording(rec)
        elif rec:
            self._map_ui_draw_grabar_active(rec)
        elif self._ui_pending_action in ("rec_roadlink", "rec_laterallink"):
            self._map_ui_draw_grabar_two_args()
        elif self._ui_pending_action in ("rec_road", "rec_zona", "rec_rule"):
            self._map_ui_draw_grabar_one_arg()
        elif self._ui_pending_action == "select_recorder_plid":
            self._map_ui_draw_grabar_select_plid()
        else:
            self._map_ui_draw_grabar_idle()

    _UI_GRABAR_PLAYER_ITEMS = 8

    def _map_ui_draw_grabar_idle(self):
        u = self._ui_ucid
        for cid, label, L, T in [
            (110, "Road", 2, 21),
            (111, "RoadLink", 36, 21),
            (112, "LatLink", 70, 21),
            (118, "Link auto", 36, 31),  # RoadLink con origen/destino auto
            (113, "Zona", 2, 41),
            (114, "Reg. Especial", 36, 41),
        ]:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=cid,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                L=L,
                T=T,
                W=32,
                H=8,
                Text=label,
            )

        # Fila de preferencias de grabado: Auto (captura de nodos) + Trafico (norma
        # por defecto de las nuevas vías) + velocidad por defecto de las nuevas vías.
        auto_on = self.map_recorder.auto_recording_enabled
        style = (
            ISB_STYLE.OK | ISB_STYLE.CLICK
            if auto_on
            else ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=115,
            BStyle=style,
            L=2,
            T=52,
            W=40,
            H=8,
            Text="Auto: ON" if auto_on else "Auto: OFF",
        )
        rule = self.map_recorder.default_traffic_rule
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=108,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=46,
            T=52,
            W=58,
            H=8,
            Text=f"Trafico: {rule.name}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=109,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=63,
            W=88,
            H=8,
            Text="Vel. grabar (km/h):",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=129,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 8,
            L=92,
            T=63,
            W=44,
            H=8,
            Text=str(self.map_recorder.default_speed_limit_kmh),
        )

        # Selección de jugador a grabar
        rec_plid = self.map_recorder.recording_plid
        if rec_plid is not None:
            sel_name = self._map_ui_grabar_plid_label(rec_plid)
            sel_text = f"Grabando PLID {rec_plid}: {sel_name}"
        else:
            sel_text = "Grabando: (ninguno seleccionado)"
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=116,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=2,
            T=74,
            W=130,
            H=8,
            Text=sel_text,
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=117,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=134,
            T=74,
            W=50,
            H=8,
            Text="Cambiar...",
        )

    def _map_ui_grabar_plid_label(self, plid: int) -> str:
        """Devuelve 'NombreJugador' o 'NombreAI (dueño)' para un PLID."""
        player = self.user_manager.players.get(plid)
        if player:
            user = self.user_manager.users.get(player.ucid)
            return user.player_name if user else f"UCID {player.ucid}"
        ai = self.user_manager.ais.get(plid)
        if ai:
            owner = self.user_manager.users.get(ai.player.ucid)
            owner_name = owner.player_name if owner else f"UCID {ai.player.ucid}"
            return f"{ai.ai_name} ({owner_name})"
        return "desconocido"

    def _map_ui_draw_grabar_select_plid(self):
        """Pantalla de selección de PLID para grabar."""
        u = self._ui_ucid

        # Construir lista de todos los coches en pista
        all_cars = []
        for p in self.user_manager.players.values():
            user = self.user_manager.users.get(p.ucid)
            name = user.player_name if user else f"UCID {p.ucid}"
            all_cars.append((p.plid, f"[H] PLID {p.plid}  {name}"))
        for ai in self.user_manager.ais.values():
            owner = self.user_manager.users.get(ai.player.ucid)
            owner_name = owner.player_name if owner else f"UCID {ai.player.ucid}"
            all_cars.append(
                (
                    ai.player.plid,
                    f"[AI] PLID {ai.player.plid}  {ai.ai_name} ({owner_name})",
                )
            )
        all_cars.sort(key=lambda x: x[0])

        per_page = self._UI_GRABAR_PLAYER_ITEMS
        total = len(all_cars)
        max_page = max(0, (total - 1) // per_page) if total else 0
        page = min(self._ui_grabar_player_page, max_page)
        self._ui_grabar_player_page = page
        items = all_cars[page * per_page : (page + 1) * per_page]

        rec_plid = self.map_recorder.recording_plid

        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=108,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=21,
            W=36,
            H=7,
            Text="<- Volver",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=109,
            BStyle=ISB_STYLE.TITLE | ISB_STYLE.LEFT,
            L=40,
            T=21,
            W=144,
            H=7,
            Text="Selecciona el PLID a grabar:",
        )

        if not all_cars:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=110,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                L=2,
                T=30,
                W=182,
                H=7,
                Text="No hay coches en pista",
            )
        else:
            for i, (plid, label) in enumerate(items):
                active = plid == rec_plid
                style = (
                    (ISB_STYLE.OK | ISB_STYLE.CLICK | ISB_STYLE.LEFT)
                    if active
                    else (
                        ISB_STYLE.DARK
                        | ISB_STYLE.SELECTED
                        | ISB_STYLE.CLICK
                        | ISB_STYLE.LEFT
                    )
                )
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=110 + i,
                    BStyle=style,
                    L=2,
                    T=30 + i * 8,
                    W=182,
                    H=7,
                    Text=label,
                )
            for i in range(len(items), per_page):
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=110 + i,
                    BStyle=ISB_STYLE.DARK,
                    L=2,
                    T=30 + i * 8,
                    W=182,
                    H=7,
                    Text="",
                )

        T_pag = 30 + per_page * 8
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=120,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=T_pag,
            W=20,
            H=7,
            Text="<",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=121,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=24,
            T=T_pag,
            W=30,
            H=7,
            Text=f"{page + 1}/{max_page + 1}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=122,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=56,
            T=T_pag,
            W=20,
            H=7,
            Text=">",
        )

    def _map_ui_draw_grabar_one_arg(self):
        u = self._ui_ucid
        labels = {
            "rec_road": "ID de la vía:",
            "rec_zona": "ID de la zona:",
            "rec_rule": "ID de la regla:",
        }
        names = {"rec_road": "Road", "rec_zona": "Zona", "rec_rule": "Reg. Especial"}
        label = labels.get(self._ui_pending_action, "ID:")
        name = names.get(self._ui_pending_action, "")

        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=21,
            W=80,
            H=6,
            Text=label,
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_TI1,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 40,
            L=2,
            T=28,
            W=100,
            H=8,
            Text=self._ui_input_buffer.get(self._UI_CID_TI1, ""),
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=116,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=2,
            T=39,
            W=50,
            H=8,
            Text=f"Iniciar {name}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=117,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=54,
            T=39,
            W=30,
            H=8,
            Text="Cancelar",
        )

    # CIDs 118/119 se usan como TypeIn de sufijo en el formulario de dos args
    _UI_CID_TI_SUF_A = 118
    _UI_CID_TI_SUF_B = 119

    _UI_ROAD_PICKER_ITEMS = 6  # items visibles en el picker

    def _map_ui_draw_grabar_two_args(self):
        u = self._ui_ucid
        is_roadlink = self._ui_pending_action == "rec_roadlink"
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
        items = all_roads[page * per_page : (page + 1) * per_page]

        # Toggle slot A / B
        slot = self._ui_road_picker_slot
        style_a = (
            (ISB_STYLE.OK | ISB_STYLE.CLICK)
            if slot == "a"
            else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        )
        style_b = (
            (ISB_STYLE.OK | ISB_STYLE.CLICK)
            if slot == "b"
            else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=120,
            BStyle=style_a,
            L=2,
            T=21,
            W=32,
            H=6,
            Text="→ A",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=121,
            BStyle=style_b,
            L=36,
            T=21,
            W=32,
            H=6,
            Text="→ B",
        )

        if not all_roads:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=122,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                L=2,
                T=28,
                W=68,
                H=6,
                Text="Sin roads",
            )
        else:
            for i, road_id in enumerate(items):
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=122 + i,
                    BStyle=ISB_STYLE.DARK
                    | ISB_STYLE.SELECTED
                    | ISB_STYLE.CLICK
                    | ISB_STYLE.LEFT,
                    L=2,
                    T=28 + i * 7,
                    W=68,
                    H=6,
                    Text=road_id,
                )
            # Rellena slots vacíos para no dejar botones huérfanos
            for i in range(len(items), per_page):
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=122 + i,
                    BStyle=ISB_STYLE.DARK,
                    L=2,
                    T=28 + i * 7,
                    W=68,
                    H=6,
                    Text="",
                )

        # Paginación picker
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=128,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=71,
            W=20,
            H=6,
            Text="<",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=129,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=24,
            T=71,
            W=24,
            H=6,
            Text=f"{page + 1}/{max_page + 1}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=132,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=50,
            T=71,
            W=20,
            H=6,
            Text=">",
        )

        # ── Columna derecha: formulario (L=72) ──────────────────────────────
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=72,
            T=21,
            W=66,
            H=6,
            Text=label_a,
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=111,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=140,
            T=21,
            W=44,
            H=6,
            Text="sufijo:",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_TI1,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 40,
            L=72,
            T=28,
            W=66,
            H=8,
            Text=self._ui_input_buffer.get(self._UI_CID_TI1, ""),
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_TI_SUF_A,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 20,
            L=140,
            T=28,
            W=44,
            H=8,
            Text=self._ui_input_buffer.get(self._UI_CID_TI_SUF_A, ""),
        )

        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=112,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=72,
            T=39,
            W=66,
            H=6,
            Text=label_b,
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=113,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=140,
            T=39,
            W=44,
            H=6,
            Text="sufijo:",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_TI2,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 40,
            L=72,
            T=46,
            W=66,
            H=8,
            Text=self._ui_input_buffer.get(self._UI_CID_TI2, ""),
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_TI_SUF_B,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 20,
            L=140,
            T=46,
            W=44,
            H=8,
            Text=self._ui_input_buffer.get(self._UI_CID_TI_SUF_B, ""),
        )

        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=116,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=72,
            T=58,
            W=56,
            H=8,
            Text=f"Iniciar {action_name}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=117,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=130,
            T=58,
            W=34,
            H=8,
            Text="Cancelar",
        )

    def _map_ui_draw_grabar_active(self, rec: dict):
        u = self._ui_ucid
        rec_type = rec.get("type", "?").upper()
        obj_id = (
            rec.get("road_id")
            or rec.get("link_id")
            or rec.get("zone_id")
            or rec.get("rule_id", "?")
        )
        n = len(rec.get("nodes", []))

        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=21,
            W=125,
            H=7,
            Text=f"Grabando: {rec_type} '{obj_id}'",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=111,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=129,
            T=21,
            W=55,
            H=7,
            Text=f"● {n} nodos",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=112,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=37,
            W=60,
            H=8,
            Text="+ Anadir punto",
        )
        auto_on = self.map_recorder.auto_recording_enabled
        if rec.get("type") == "yield_line":
            # La línea de cesión solo captura en fase "recording" (nace manual).
            auto_on = auto_on and rec.get("auto_phase") == "recording"
        auto_style = (
            ISB_STYLE.OK | ISB_STYLE.CLICK
            if auto_on
            else ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=113,
            BStyle=auto_style,
            L=64,
            T=37,
            W=40,
            H=8,
            Text="Auto: ON" if auto_on else "Auto: OFF",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=114,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=2,
            T=48,
            W=60,
            H=9,
            Text="Finalizar",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=115,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=64,
            T=48,
            W=60,
            H=9,
            Text="Cancelar",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Grabar: "Link auto" (RoadLink con origen/destino auto-detectados)
    #
    # Flujo pensado para mapear cómodo: te colocas en el road de ORIGEN, pulsas
    # "Link auto" (no hay que teclear origen ni destino), conduces hasta el road
    # de DESTINO y pulsas Finalizar. El origen se captura al iniciar y el destino
    # al finalizar, ambos por la posición del coche que se está grabando
    # (recording_plid). Al finalizar:
    #   - si la combinación origen->destino YA existe → pantalla de CONFLICTO
    #     (añadir sufijo y recomprobar / sobrescribir / cancelar),
    #   - si no existe → pantalla de CONFIRMACIÓN (Aprobar / Cancelar).
    # El estado del flujo vive en current_recording["auto_phase"] para sobrevivir
    # a cerrar/reabrir el menú (la grabación sigue viva en el recorder).
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_recording_coords(self):
        """Coordenadas del coche que se está grabando (recording_plid), sea
        humano o IA. None si no hay PLID seleccionado o no tiene telemetría."""
        plid = self.map_recorder.recording_plid
        if plid is None:
            return None
        player = self.user_manager.players.get(plid)
        if player and player.telemetry:
            return player.telemetry.coordinates
        ai = self.user_manager.ais.get(plid)
        if ai and ai.player.telemetry:
            return ai.player.telemetry.coordinates
        return None

    def _map_ui_start_auto_link(self):
        """Inicia una grabación de RoadLink capturando el ORIGEN de la posición
        actual del coche a grabar. No pide origen/destino: los detecta solos."""
        mr = self.map_recorder
        if not mr.active_map_name:
            self.send_ISP_MSL(Msg=f"{c.RED}Selecciona un mapa primero.")
            return
        coords = self._map_ui_recording_coords()
        if not coords:
            self.send_ISP_MSL(
                Msg=f"{c.RED}No se pudo leer la telemetria del coche a grabar (en pista?)."
            )
            return
        ctx = mr.get_location_context(
            coords.x_m, coords.y_m, coords.z_m, find_links=False, find_zones=False
        )
        origin = ctx.road_id
        if origin is None:
            self.send_ISP_MSL(
                Msg=f"{c.RED}No hay vias en el mapa: graba primero el road de origen."
            )
            return
        mr.current_recording = {
            "type": "road_link",
            "link_id": None,
            "origin_id": origin,
            "dest_id": None,
            "from_suffix": "",
            "to_suffix": "",
            "nodes": [copy.deepcopy(coords)],
            "is_new": True,
            "auto": True,
            "auto_phase": "recording",
        }
        mr.auto_recording_enabled = True
        self.send_ISP_MSL(
            Msg=f"{c.GREEN}Link auto: origen {c.WHITE}{origin}{c.GREEN}. Conduce al destino y pulsa Finalizar."
        )
        self._map_ui_redraw_content()
        self._map_ui_update_header()

    def _map_ui_draw_auto_link_recording(self, rec: dict):
        u = self._ui_ucid
        origin = rec.get("origin_id", "?")
        n = len(rec.get("nodes", []))
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=21,
            W=125,
            H=7,
            Text=f"Link auto: {origin} -> (conduce al destino)",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=111,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=129,
            T=21,
            W=55,
            H=7,
            Text=f"* {n} nodos",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=112,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=37,
            W=60,
            H=8,
            Text="+ Anadir punto",
        )
        auto_on = self.map_recorder.auto_recording_enabled
        auto_style = (
            ISB_STYLE.OK | ISB_STYLE.CLICK
            if auto_on
            else ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=113,
            BStyle=auto_style,
            L=64,
            T=37,
            W=40,
            H=8,
            Text="Auto: ON" if auto_on else "Auto: OFF",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=114,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=2,
            T=48,
            W=60,
            H=9,
            Text="Finalizar",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=115,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=64,
            T=48,
            W=60,
            H=9,
            Text="Cancelar",
        )

    def _map_ui_click_auto_link_recording(self, cid: int):
        mr = self.map_recorder
        if cid == 112:  # + Anadir punto (coords del coche que se graba)
            coords = self._map_ui_recording_coords()
            if coords:
                mr.current_recording["nodes"].append(copy.deepcopy(coords))
                n = len(mr.current_recording["nodes"])
                self.send_ISP_MSL(Msg=f"{c.GREEN}Nodo #{n} anadido manualmente.")
                self._map_ui_redraw_content()
                self._map_ui_update_header()
            else:
                self.send_ISP_MSL(Msg=f"{c.RED}Error: no se pudo leer la telemetria.")
        elif cid == 113:  # toggle auto
            new = not mr.auto_recording_enabled
            mr._cmd_rec_auto("true" if new else "false")
            self._map_ui_redraw_content()
            self._map_ui_update_header()
        elif cid == 114:  # Finalizar → detecta destino
            self._map_ui_finalize_auto_link()
        elif cid == 115:  # Cancelar
            mr._cmd_rec_cancel()
            self._map_ui_redraw_content()
            self._map_ui_update_header()

    def _map_ui_finalize_auto_link(self):
        """Detecta el road DESTINO por la posición actual del coche y pasa a la
        pantalla de confirmación o de conflicto según exista ya el enlace."""
        mr = self.map_recorder
        rec = mr.current_recording
        coords = self._map_ui_recording_coords()
        if not coords:
            self.send_ISP_MSL(
                Msg=f"{c.RED}No se pudo leer la telemetria para detectar el destino."
            )
            return
        ctx = mr.get_location_context(
            coords.x_m, coords.y_m, coords.z_m, find_links=False, find_zones=False
        )
        dest = ctx.road_id
        if dest is None:
            self.send_ISP_MSL(
                Msg=f"{c.RED}El coche no esta sobre ninguna via. Colocate en el road destino."
            )
            return
        rec["dest_id"] = dest
        rec["nodes"].append(copy.deepcopy(coords))  # cierra el trazado en el destino
        # La captura se congela sola al salir de la fase "recording" (gate por
        # auto_phase en update_recording); no tocamos la preferencia Auto.
        self._map_ui_auto_link_evaluate("", "")

    def _map_ui_auto_link_evaluate(self, suffix_a: str, suffix_b: str):
        """Construye el nombre origen[suf]->destino[suf] y decide la pantalla:
        conflicto si ya existe en road_links, confirmación si está libre."""
        mr = self.map_recorder
        rec = mr.current_recording
        origin = rec["origin_id"]
        dest = rec["dest_id"]
        link_id = f"{origin}{suffix_a}->{dest}{suffix_b}"
        rec["from_suffix"] = suffix_a
        rec["to_suffix"] = suffix_b
        rec["pending_link_id"] = link_id
        rec["auto_phase"] = "conflict" if link_id in mr.road_links else "confirm"
        self._map_ui_redraw_content()
        self._map_ui_update_header()

    def _map_ui_commit_auto_link(self, is_new: bool):
        """Materializa el RoadLink pendiente reutilizando el commit del recorder."""
        mr = self.map_recorder
        rec = mr.current_recording
        rec["link_id"] = rec.get("pending_link_id")
        rec["is_new"] = is_new
        mr._cmd_rec_end()  # crea/actualiza el RoadLink y limpia current_recording
        self._ui_input_buffer = {}
        self._map_ui_redraw_content()
        self._map_ui_update_header()

    def _map_ui_draw_auto_link_confirm(self, rec: dict):
        u = self._ui_ucid
        link_id = rec.get("pending_link_id", "?")
        n = len(rec.get("nodes", []))
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.TITLE | ISB_STYLE.LEFT,
            L=2,
            T=21,
            W=182,
            H=7,
            Text="Enlace listo para crear:",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=111,
            BStyle=ISB_STYLE.OK | ISB_STYLE.LEFT,
            L=2,
            T=30,
            W=182,
            H=8,
            Text=f"{link_id}   ({n} nodos)",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=114,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=2,
            T=42,
            W=60,
            H=9,
            Text="Aprobar",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=115,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=64,
            T=42,
            W=60,
            H=9,
            Text="Cancelar",
        )

    def _map_ui_click_auto_link_confirm(self, cid: int):
        if cid == 114:  # Aprobar
            self._map_ui_commit_auto_link(is_new=True)
        elif cid == 115:  # Cancelar
            self.map_recorder._cmd_rec_cancel()
            self._map_ui_redraw_content()
            self._map_ui_update_header()

    def _map_ui_draw_auto_link_conflict(self, rec: dict):
        u = self._ui_ucid
        link_id = rec.get("pending_link_id", "?")
        origin = rec.get("origin_id", "?")
        dest = rec.get("dest_id", "?")
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.LEFT,
            L=2,
            T=21,
            W=182,
            H=7,
            Text=f"Ya existe el link: {link_id}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=111,
            BStyle=ISB_STYLE.TITLE | ISB_STYLE.LEFT,
            L=2,
            T=30,
            W=182,
            H=6,
            Text="Opcion 1: anade sufijo a origen y/o destino",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=112,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=38,
            W=130,
            H=8,
            Text=f"Origen {origin}   sufijo:",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_TI1,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 20,
            L=134,
            T=38,
            W=50,
            H=8,
            Text=self._ui_input_buffer.get(self._UI_CID_TI1, ""),
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=113,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=48,
            W=130,
            H=8,
            Text=f"Destino {dest}   sufijo:",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_TI2,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 20,
            L=134,
            T=48,
            W=50,
            H=8,
            Text=self._ui_input_buffer.get(self._UI_CID_TI2, ""),
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=116,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=2,
            T=58,
            W=182,
            H=8,
            Text="Recomprobar con sufijo",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=118,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=68,
            W=90,
            H=9,
            Text="Opcion 2: Sobrescribir",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=117,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=94,
            T=68,
            W=90,
            H=9,
            Text="Opcion 3: Cancelar",
        )

    def _map_ui_click_auto_link_conflict(self, cid: int):
        mr = self.map_recorder
        if cid == 116:  # Recomprobar con los sufijos escritos
            suffix_a = self._ui_input_buffer.get(self._UI_CID_TI1, "").strip()
            suffix_b = self._ui_input_buffer.get(self._UI_CID_TI2, "").strip()
            self._map_ui_auto_link_evaluate(suffix_a, suffix_b)
            if mr.current_recording.get("auto_phase") == "conflict":
                self.send_ISP_MSL(
                    Msg=f"{c.YELLOW}Ese nombre tambien existe. Prueba otro sufijo."
                )
        elif cid == 118:  # Sobrescribir el existente
            self._map_ui_commit_auto_link(is_new=False)
        elif cid == 117:  # Cancelar
            mr._cmd_rec_cancel()
            self._map_ui_redraw_content()
            self._map_ui_update_header()

    # ──────────────────────────────────────────────────────────────────────────
    # Tab: Info
    # ──────────────────────────────────────────────────────────────────────────

    _CHECK_ITEMS_PER_PAGE = 4
    _WA_TYPES = ["road", "roadlink", "latlink", "zone", "rule", "ahead"]
    # "Apunta": alcance máx. del rayo que busca la vía a la que apunta el morro (m).
    _AHEAD_MAX_DIST_M = 300.0

    def _map_ui_draw_tab_info(self):
        u = self._ui_ucid
        # Fila 1: Stats / Check / Roads cerradas
        stats_style = (
            (ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            if self._ui_info_stats
            else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        )
        check_style = (
            (ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            if self._ui_info_check
            else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        )
        roads_style = (
            (ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            if self._ui_info_roads
            else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=stats_style,
            L=2,
            T=21,
            W=38,
            H=8,
            Text="Stats",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=111,
            BStyle=check_style,
            L=42,
            T=21,
            W=38,
            H=8,
            Text="Check",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=112,
            BStyle=roads_style,
            L=82,
            T=21,
            W=38,
            H=8,
            Text="Roads cerradas",
        )

        # Fila 2: Whereami toggles (5) + "Apunta" (vía a la que apunta el morro) + intervalo
        for i, label in enumerate(
            ["WA Road", "WA RLink", "WA LLink", "WA Zone", "WA Regla", "Apunta"]
        ):
            active = self._WA_TYPES[i] in self._ui_whereami
            style = (
                (ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
                if active
                else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            )
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=113 + i,
                BStyle=style,
                L=2 + i * 28,
                T=31,
                W=26,
                H=8,
                Text=label,
            )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=147,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 8,
            L=172,
            T=31,
            W=14,
            H=8,
            Text=str(self._ui_whereami_interval),
        )

        T = 42
        if self._ui_info_stats:
            mr = self.map_recorder
            counts = [
                ("Roads", len(mr.roads)),
                ("RoadLinks", len(mr.road_links)),
                ("LatLinks", len(mr.lateral_links)),
                ("Zonas", len(mr.zones)),
                ("Reglas", len(mr.special_rules)),
            ]
            for i, (label, n) in enumerate(counts):
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=148 + i,
                    BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                    L=2 + i * 38,
                    T=T,
                    W=36,
                    H=8,
                    Text=f"{label}: {n}",
                )
            T += 10

        if self._ui_info_check:
            self._map_ui_draw_check_panel(T)
            T += 9 + 9 + self._CHECK_ITEMS_PER_PAGE * 8 + 8

        if self._ui_info_roads:
            self._map_ui_draw_roads_panel(T)
            T += 9 + 9 + self._ROADS_ITEMS_PER_PAGE * 8 + 6

        # El whereami ya NO se dibuja aquí: es un overlay "pineado" independiente
        # del menú (mitad-derecha), gestionado por _map_ui_redraw_pinned_whereami.

    def _map_ui_draw_check_panel(self, T: int):
        u = self._ui_ucid
        if not self.map_recorder.active_map_name:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=121,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                L=2,
                T=T,
                W=180,
                H=7,
                Text="Sin mapa activo",
            )
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
        total_pages = max(
            1,
            (len(all_items) + self._CHECK_ITEMS_PER_PAGE - 1)
            // self._CHECK_ITEMS_PER_PAGE,
        )
        self._ui_check_page = max(0, min(self._ui_check_page, total_pages - 1))

        # Buscador (CID 121 TypeIn, CID 122 botón)
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=121,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 60,
            L=2,
            T=T,
            W=132,
            H=7,
            Text=self._ui_check_search or "Buscar...",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=122,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=136,
            T=T,
            W=22,
            H=7,
            Text="Filtrar",
        )
        T += 9

        # Filtros tipo (CIDs 123–125)
        for i, (key, label) in enumerate(
            [
                ("all", f"Todos ({n_err}E {n_warn}W)"),
                ("error", f"Errores ({n_err})"),
                ("warn", f"Avisos ({n_warn})"),
            ]
        ):
            active = self._ui_check_filter == key
            style = (
                (ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
                if active
                else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            )
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=123 + i,
                BStyle=style,
                L=2 + i * 62,
                T=T,
                W=60,
                H=7,
                Text=label,
            )
        T += 9

        # Items (CIDs 126–129)
        start = self._ui_check_page * self._CHECK_ITEMS_PER_PAGE
        page_items = all_items[start : start + self._CHECK_ITEMS_PER_PAGE]
        if not page_items:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=126,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                L=2,
                T=T,
                W=180,
                H=7,
                Text="Sin resultados",
            )
        else:
            for i, (sev, msg) in enumerate(page_items):
                style = (
                    ISB_STYLE.CANCEL | ISB_STYLE.DARK
                    if sev == "E"
                    else ISB_STYLE.TITLE | ISB_STYLE.DARK
                )
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=126 + i,
                    BStyle=style,
                    L=2,
                    T=T + i * 8,
                    W=180,
                    H=7,
                    Text=msg,
                )

        # Paginación (CIDs 130–132)
        prev_style = (
            (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            if self._ui_check_page > 0
            else (ISB_STYLE.DARK | ISB_STYLE.SELECTED)
        )
        next_style = (
            (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            if self._ui_check_page < total_pages - 1
            else (ISB_STYLE.DARK | ISB_STYLE.SELECTED)
        )
        pag_T = T + self._CHECK_ITEMS_PER_PAGE * 8
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=130,
            BStyle=prev_style,
            L=2,
            T=pag_T,
            W=16,
            H=6,
            Text="<",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=131,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
            L=20,
            T=pag_T,
            W=50,
            H=6,
            Text=f"Pag {self._ui_check_page + 1}/{total_pages}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=132,
            BStyle=next_style,
            L=72,
            T=pag_T,
            W=16,
            H=6,
            Text=">",
        )

    _ROADS_ITEMS_PER_PAGE = 6

    def _map_ui_draw_roads_panel(self, T: int):
        u = self._ui_ucid
        if not self.map_recorder.active_map_name:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=133,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                L=2,
                T=T,
                W=180,
                H=7,
                Text="Sin mapa activo",
            )
            return

        search = self._ui_roads_search.lower()
        all_roads = [
            (r_id, road.is_closed) for r_id, road in self.map_recorder.roads.items()
        ]
        if self._ui_roads_filter == "open":
            all_roads = [(r, c) for r, c in all_roads if not c]
        elif self._ui_roads_filter == "closed":
            all_roads = [(r, c) for r, c in all_roads if c]
        if search:
            all_roads = [(r, c) for r, c in all_roads if search in r.lower()]
        all_roads.sort(key=lambda x: x[0])

        n_open = sum(
            1 for road in self.map_recorder.roads.values() if not road.is_closed
        )
        n_closed = sum(1 for road in self.map_recorder.roads.values() if road.is_closed)
        total_pages = max(
            1,
            (len(all_roads) + self._ROADS_ITEMS_PER_PAGE - 1)
            // self._ROADS_ITEMS_PER_PAGE,
        )
        self._ui_roads_page = max(0, min(self._ui_roads_page, total_pages - 1))

        # Buscador (CID 133 TypeIn, 134 botón)
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=133,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 60,
            L=2,
            T=T,
            W=132,
            H=7,
            Text=self._ui_roads_search or "Buscar...",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=134,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=136,
            T=T,
            W=22,
            H=7,
            Text="Filtrar",
        )
        T += 9

        # Filtros tipo (CIDs 135–137)
        for i, (key, label) in enumerate(
            [
                ("all", f"Todos ({n_open}A {n_closed}C)"),
                ("open", f"Abiertos ({n_open})"),
                ("closed", f"Cerrados ({n_closed})"),
            ]
        ):
            active = self._ui_roads_filter == key
            style = (
                (ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
                if active
                else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            )
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=135 + i,
                BStyle=style,
                L=2 + i * 62,
                T=T,
                W=60,
                H=7,
                Text=label,
            )
        T += 9

        # Items (CIDs 138–143)
        start = self._ui_roads_page * self._ROADS_ITEMS_PER_PAGE
        page_items = all_roads[start : start + self._ROADS_ITEMS_PER_PAGE]
        if not page_items:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=138,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                L=2,
                T=T,
                W=180,
                H=7,
                Text="Sin resultados",
            )
        else:
            for i, (r_id, is_closed) in enumerate(page_items):
                style = (
                    (ISB_STYLE.CANCEL | ISB_STYLE.DARK | ISB_STYLE.CLICK)
                    if is_closed
                    else (ISB_STYLE.OK | ISB_STYLE.CLICK)
                )
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=138 + i,
                    BStyle=style,
                    L=2,
                    T=T + i * 8,
                    W=180,
                    H=7,
                    Text=r_id,
                )

        # Paginación (CIDs 144–146)
        prev_style = (
            (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            if self._ui_roads_page > 0
            else (ISB_STYLE.DARK | ISB_STYLE.SELECTED)
        )
        next_style = (
            (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            if self._ui_roads_page < total_pages - 1
            else (ISB_STYLE.DARK | ISB_STYLE.SELECTED)
        )
        pag_T = T + self._ROADS_ITEMS_PER_PAGE * 8
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=144,
            BStyle=prev_style,
            L=2,
            T=pag_T,
            W=16,
            H=6,
            Text="<",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=145,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
            L=20,
            T=pag_T,
            W=50,
            H=6,
            Text=f"Pag {self._ui_roads_page + 1}/{total_pages}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=146,
            BStyle=next_style,
            L=72,
            T=pag_T,
            W=16,
            H=6,
            Text=">",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Overlay whereami "pineado" (mitad-derecha, independiente del menú)
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_active_whereami(self) -> list[tuple[int, str]]:
        """(índice en _WA_TYPES, tipo) de los whereami activos, en orden fijo."""
        return [(i, t) for i, t in enumerate(self._WA_TYPES) if t in self._ui_whereami]

    def _map_ui_pinned_whereami_top(self, n_rows: int) -> int:
        """T de la primera fila para centrar verticalmente el overlay (título + filas)."""
        total = (n_rows + 1) * self._WA_PIN_ROW_STEP
        return max(20, 100 - total // 2)

    def _map_ui_clear_pinned_whereami(self):
        """Borra los botones del overlay (título + todas las filas posibles)."""
        u = self._ui_whereami_ucid
        if u is None:
            return
        self.send_ISP_BFN(
            SubT=BFN.DEL_BTN,
            UCID=u,
            ClickID=self._WA_PIN_CID_TITLE,
            ClickMax=self._WA_PIN_CID_BASE + len(self._WA_TYPES) - 1,
        )

    def _map_ui_redraw_pinned_whereami(self):
        """Redibuja (geometría completa) el overlay whereami anclado a la mitad-derecha.

        Se llama al conmutar una selección, al cerrar el menú (BFN.CLEAR lo borra) y
        al reconectar (LFS pierde los botones). Es no-op si no hay nada seleccionado.
        """
        u = self._ui_whereami_ucid
        if u is None:
            return
        self._map_ui_clear_pinned_whereami()
        active = self._map_ui_active_whereami()
        if not active:
            return
        top = self._map_ui_pinned_whereami_top(len(active))
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._WA_PIN_CID_TITLE,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
            L=self._WA_PIN_L,
            T=top,
            W=self._WA_PIN_W,
            H=self._WA_PIN_H,
            Text=f"{c.YELLOW}Ubicación",
        )
        t = top + self._WA_PIN_ROW_STEP
        for idx, wa_type in active:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=self._WA_PIN_CID_BASE + idx,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                L=self._WA_PIN_L,
                T=t,
                W=self._WA_PIN_W,
                H=self._WA_PIN_H,
                Text=self._map_ui_compute_whereami(wa_type),
            )
            t += self._WA_PIN_ROW_STEP

    def _map_ui_refresh_pinned_whereami(self):
        """Actualiza solo el TEXTO de las filas activas (sin recolocar botones)."""
        u = self._ui_whereami_ucid
        if u is None:
            return
        for idx, wa_type in self._map_ui_active_whereami():
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=self._WA_PIN_CID_BASE + idx,
                BStyle=0,
                L=0,
                T=0,
                W=0,
                H=0,
                Text=self._map_ui_compute_whereami(wa_type),
            )

    def _map_ui_compute_whereami(self, target: str) -> str:
        mr = self.map_recorder
        if not mr.active_map_name:
            return "Sin mapa activo"
        coords = mr.get_coords_fn(self._ui_whereami_ucid)
        if not coords:
            return "Sin telemetria"
        px, py, pz = coords.x_m, coords.y_m, coords.z_m

        if target == "road":
            if not mr.roads:
                return "WA Road: Sin roads"
            res = mr.get_closest_geometry(
                px, py, pz, mr.roads.items(), lambda r: r.nodes
            )
            if res["id"] is None:
                return "WA Road: Sin datos"
            status = "TOCANDO" if res["dist"] <= 3.0 else f"{res['dist']:.1f}m"
            return f"WA Road: {res['id']} | {status}"

        elif target == "roadlink":
            if not mr.road_links:
                return "WA RLink: Sin links"
            res = mr.get_closest_geometry(
                px, py, pz, mr.road_links.items(), lambda l: l.nodes
            )
            if res["id"] is None:
                return "WA RLink: Sin datos"
            status = "TOCANDO" if res["dist"] <= 2.0 else f"{res['dist']:.1f}m"
            return f"WA RLink: {res['id']} | {status}"

        elif target == "latlink":
            if not mr.lateral_links:
                return "WA LLink: Sin links"
            res = mr.get_closest_geometry(
                px, py, pz, mr.lateral_links.items(), lambda l: l.nodes
            )
            if res["id"] is None:
                return "WA LLink: Sin datos"
            status = "TOCANDO" if res["dist"] <= 2.0 else f"{res['dist']:.1f}m"
            return f"WA LLink: {res['id']} | {status}"

        elif target == "zone":
            ctx = mr.get_location_context(
                px, py, pz, find_roads=False, find_links=False, find_zones=True
            )
            if ctx.zone_id is None:
                return "WA Zona: Sin zonas"
            status = (
                "DENTRO"
                if ctx.zone_dist <= ctx.zone_radius
                else f"{ctx.zone_dist:.1f}m"
            )
            return f"WA Zona: {ctx.zone_id} | {status}"

        elif target == "rule":
            if not mr.special_rules:
                return "WA Regla: Sin reglas"
            best_id = None
            best_dist = float("inf")
            best_node_idx = 0
            best_radius = 8.0
            for rule_id, rule in mr.special_rules.items():
                for n_idx, node in enumerate(rule.nodes[:2]):
                    d = math.sqrt(
                        (px - node.x_m) ** 2
                        + (py - node.y_m) ** 2
                        + (pz - node.z_m) ** 2
                    )
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

        elif target == "ahead":
            if not mr.roads:
                return "Apunta: Sin roads"
            fwd = self._map_ui_forward_vector(self._ui_whereami_ucid)
            if fwd is None:
                return "Apunta: Sin rumbo"
            # La vía sobre la que estás = la más cercana a tu posición → se excluye.
            cur = mr.get_closest_geometry(
                px, py, pz, mr.roads.items(), lambda r: r.nodes
            )
            rid, dist = find_road_pointed_at(
                px,
                py,
                fwd[0],
                fwd[1],
                mr.roads.items(),
                cur["id"],
                self._AHEAD_MAX_DIST_M,
            )
            if rid is None:
                return "Apunta: --"
            return f"Apunta: {rid} | {dist:.1f}m"

        return "WA: tipo desconocido"

    def _map_ui_forward_vector(
        self, ucid: Optional[int]
    ) -> Optional[tuple[float, float]]:
        """Vector unitario (x, y) al que apunta el morro del coche del UCID, o None.

        Usa el mismo criterio que la navegación de las IAs (heading LFS →
        (-sin, cos)), coherente con cómo el resto del módulo entiende "hacia
        delante".
        """
        um = self.user_manager
        if um is None or ucid is None:
            return None
        user = um.users.get(ucid)
        if not user or not user.plid:
            return None
        player = um.players.get(user.plid)
        if not player or not player.telemetry:
            return None
        rad = player.telemetry.heading.angle_lfs * 2.0 * math.pi / 65536.0
        return (-math.sin(rad), math.cos(rad))

    def _map_ui_navigate_to_element(self, obj_id: str):
        """Navega al detalle del objeto recién grabado en el tab Elementos."""
        if not getattr(self, "_ui_ucid", None):
            return
        self._ui_tab = "elementos"
        self._ui_elem_detail_id = obj_id
        self._map_ui_clear_content()
        self._map_ui_draw_tab_elementos()

    def _map_ui_node_flash(self, node_count: int, is_curve: bool):
        """Actualiza el contador de nodos en el tab Grabar con color flash."""
        import time

        if not getattr(self, "_ui_ucid", None):
            return
        color = "^3" if is_curve else "^2"
        self.send_ISP_BTN(
            ReqI=1,
            UCID=self._ui_ucid,
            ClickID=111,
            T=0,
            L=0,
            W=0,
            H=0,
            BStyle=0,
            Text=f"{color}● {node_count} nodos",
        )
        self._ui_node_flash_time = time.time()

    # ──────────────────────────────────────────────────────────────────────────
    # Tab: Elementos — dispatcher
    #
    # TODO (S32, pedido del usuario — pendiente, su propia sesión): edición MASIVA.
    # Un modo de esta pestaña con buscador (como el de la lista de elementos) +
    # multi-selección (marcar N elementos) para aplicar un mismo ajuste a todos a
    # la vez (p. ej. speed_limit_kmh, is_closed, traffic_rule...). Requiere: estado
    # de selección múltiple, un selector de campo+valor, y aplicar el cambio en
    # bucle sobre los seleccionados. Hacerlo con red primero (test_map_ui_*).
    # Ver PLAN § "Tooling de trabajo — Skills"/Ideas.
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
            is_active = etype == self._ui_elem_type
            style = (
                (ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
                if is_active
                else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            )
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=108 + i,
                BStyle=style,
                L=2 + i * 38,
                T=21,
                W=36,
                H=7,
                Text=_ELEM_TYPE_LABELS[etype],
            )

        # Buscador (TI1=130) + botón Filtrar (CID=113)
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_TI1,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 40,
            L=2,
            T=30,
            W=132,
            H=7,
            Text=self._ui_elem_search or "Buscar...",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=113,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=136,
            T=30,
            W=22,
            H=7,
            Text="Filtrar",
        )

        if not self.map_recorder.active_map_name:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=114,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                L=2,
                T=39,
                W=180,
                H=7,
                Text="Sin mapa activo",
            )
            return

        items = self._map_ui_elem_get_filtered()
        total_pages = max(1, (len(items) + _ITEMS_PER_PAGE - 1) // _ITEMS_PER_PAGE)
        self._ui_elem_page = max(0, min(self._ui_elem_page, total_pages - 1))
        start = self._ui_elem_page * _ITEMS_PER_PAGE
        page_items = items[start : start + _ITEMS_PER_PAGE]

        if not page_items:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=114,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
                L=2,
                T=39,
                W=180,
                H=7,
                Text="Sin resultados",
            )
        else:
            for i, item_id in enumerate(page_items):
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=114 + i,
                    BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                    L=2,
                    T=39 + i * 7,
                    W=180,
                    H=6,
                    Text=item_id,
                )

        # Paginación (CIDs 120–122)
        prev_style = (
            (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            if self._ui_elem_page > 0
            else ISB_STYLE.DARK | ISB_STYLE.SELECTED
        )
        next_style = (
            (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
            if self._ui_elem_page < total_pages - 1
            else ISB_STYLE.DARK | ISB_STYLE.SELECTED
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=120,
            BStyle=prev_style,
            L=2,
            T=82,
            W=16,
            H=6,
            Text="<",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=121,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED,
            L=20,
            T=82,
            W=50,
            H=6,
            Text=f"Pag {self._ui_elem_page + 1}/{total_pages}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=122,
            BStyle=next_style,
            L=72,
            T=82,
            W=16,
            H=6,
            Text=">",
        )

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

        # Sub-pantalla de alta de regla de prioridad (picker de vías): ocupa todo
        # el contenido, como el formulario de RoadLink/LatLink.
        if obj_type == "zone" and self._ui_zone_prio_adding:
            self._map_ui_draw_zone_prio_picker(obj, u)
            return

        # Sub-pantallas de la cesión de un RoadLink (grabador de la línea /
        # pedir T / picker de zona): también a pantalla completa.
        if obj_type == "roadlink":
            rec = self.map_recorder.current_recording
            if rec and rec.get("type") == "yield_line" and rec.get("link_id") == obj_id:
                if rec.get("auto_phase") == "ask_t":
                    self._map_ui_draw_link_yield_ask_t(obj, u, rec)
                else:
                    self._map_ui_draw_link_yield_recorder(obj, u, rec)
                return
            if self._ui_link_zone_picking:
                self._map_ui_draw_link_zone_picker(obj, u)
                return

        fields_def = _ELEM_FIELDS.get(obj_type, [])

        # Header de detalle
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=108,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=21,
            W=20,
            H=6,
            Text="< Volver",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=109,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=24,
            T=21,
            W=118,
            H=6,
            Text=f"{obj_type.upper()}: {obj_id}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=144,
            T=21,
            W=22,
            H=6,
            Text="Borrar",
        )

        # Filas de campos (máx. 8 filas, spacing=7 para que row7 quede en T=78)
        self._ui_detail_field_map = {}
        self._ui_zone_prio_map = {}
        for row, (fname, ftype) in enumerate(fields_def[:8]):
            T = 29 + row * 7
            label_cid = 111 + row * 2
            val_cid = 112 + row * 2

            val_str = self._map_ui_elem_field_value_str(obj, fname)

            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=label_cid,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                L=2,
                T=T,
                W=68,
                H=6,
                Text=f"{fname}:",
            )

            if ftype == "readonly":
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=val_cid,
                    BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                    L=72,
                    T=T,
                    W=108,
                    H=6,
                    Text=val_str,
                )
            elif ftype == "bool":
                is_true = val_str.lower() in ("true", "yes", "si", "1")
                style = (
                    (ISB_STYLE.OK | ISB_STYLE.CLICK)
                    if is_true
                    else (ISB_STYLE.CANCEL | ISB_STYLE.CLICK)
                )
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=val_cid,
                    BStyle=style,
                    L=72,
                    T=T,
                    W=108,
                    H=6,
                    Text="ON" if is_true else "OFF",
                )
                self._ui_detail_field_map[val_cid] = (fname, "bool")
            elif ftype == "enum_traffic":
                style = (
                    ISB_STYLE.OK | ISB_STYLE.CLICK
                    if val_str == "RHT"
                    else ISB_STYLE.TITLE | ISB_STYLE.CLICK
                )
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=val_cid,
                    BStyle=style,
                    L=72,
                    T=T,
                    W=108,
                    H=6,
                    Text=val_str if val_str else "RHT",
                )
                self._ui_detail_field_map[val_cid] = (fname, "enum_traffic")
            elif ftype == "enum_indicators":
                ind_styles = {
                    "OFF": ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
                    "LEFT": ISB_STYLE.TITLE | ISB_STYLE.CLICK,
                    "RIGHT": ISB_STYLE.OK | ISB_STYLE.CLICK,
                }
                style = ind_styles.get(
                    val_str, ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK
                )
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=val_cid,
                    BStyle=style,
                    L=72,
                    T=T,
                    W=108,
                    H=6,
                    Text=val_str if val_str else "OFF",
                )
                self._ui_detail_field_map[val_cid] = (fname, "enum_indicators")
            else:
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=val_cid,
                    BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
                    TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 48,
                    L=72,
                    T=T,
                    W=108,
                    H=6,
                    Text=val_str,
                )
                self._ui_detail_field_map[val_cid] = (fname, ftype)

        # Editor de reglas de prioridad (solo Zonas, tras sus campos estándar)
        if obj_type == "zone":
            self._map_ui_draw_zone_priority(obj, u)

        # Sección de cesión (solo RoadLinks, tras sus campos estándar)
        if obj_type == "roadlink":
            self._map_ui_draw_link_yield(obj, u)

    def _map_ui_draw_zone_priority(self, zone, u):
        """Editor de `priority_rules` de una Zona: botón de alta (abre el picker
        de vías) y la lista de reglas existentes con su botón Quitar. Regla
        `[A, B]`: A tiene prioridad, B cede el paso."""
        # Título de la sección
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._ZONE_PRIO_TITLE,
            BStyle=ISB_STYLE.TITLE | ISB_STYLE.LEFT,
            L=2,
            T=50,
            W=180,
            H=6,
            Text="Prioridad (A>B: A pasa, B cede)",
        )
        # Botón de alta: abre la sub-pantalla con el picker de vías
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._ZONE_PRIO_ADD,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=2,
            T=57,
            W=164,
            H=6,
            Text="+ Anadir regla",
        )
        # Reglas existentes (cada una con su Quitar); se registran en el mapa de
        # clicks para el handler. Se muestran hasta _ZONE_PRIO_MAX_ROWS.
        self._ui_zone_prio_map = {}
        rules = [r for r in zone.priority_rules if len(r) == 2]
        if not rules:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=self._ZONE_PRIO_ROW_BASE,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                L=2,
                T=64,
                W=164,
                H=6,
                Text="Sin reglas: la IA no cede el paso en esta zona.",
            )
            return
        for i, rule in enumerate(rules[: self._ZONE_PRIO_MAX_ROWS]):
            T = 64 + i * 7
            lbl_cid = self._ZONE_PRIO_ROW_BASE + i * 2
            del_cid = self._ZONE_PRIO_ROW_BASE + i * 2 + 1
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=lbl_cid,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                L=2,
                T=T,
                W=140,
                H=6,
                Text=f"{rule[0]} > {rule[1]}",
            )
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=del_cid,
                BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
                L=144,
                T=T,
                W=22,
                H=6,
                Text="Quitar",
            )
            self._ui_zone_prio_map[del_cid] = (rule[0], rule[1])

    def _map_ui_draw_zone_prio_picker(self, zone, u):
        """Sub-pantalla de alta de regla: se eligen las dos vías de una lista
        (misma UX que crear un RoadLink/LatLink), no se teclean. Slot A =
        prioritaria (_UI_CID_TI1), slot B = la que cede (_UI_CID_TI2)."""
        buf = self._ui_input_buffer
        # Título
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=109,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=21,
            W=182,
            H=6,
            Text=f"Nueva regla en {zone.zone_id}",
        )
        # ── Columna izquierda: picker de vías ───────────────────────────────
        slot = self._ui_road_picker_slot
        style_a = (
            (ISB_STYLE.OK | ISB_STYLE.CLICK)
            if slot == "a"
            else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        )
        style_b = (
            (ISB_STYLE.OK | ISB_STYLE.CLICK)
            if slot == "b"
            else (ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK)
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=120,
            BStyle=style_a,
            L=2,
            T=28,
            W=33,
            H=6,
            Text="-> Prio",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=121,
            BStyle=style_b,
            L=37,
            T=28,
            W=33,
            H=6,
            Text="-> Cede",
        )
        all_roads = sorted(self.map_recorder.roads.keys())
        per_page = self._UI_ROAD_PICKER_ITEMS
        max_page = max(0, (len(all_roads) - 1) // per_page) if all_roads else 0
        page = min(self._ui_road_picker_page, max_page)
        self._ui_road_picker_page = page
        items = all_roads[page * per_page : (page + 1) * per_page]
        if not all_roads:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=122,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                L=2,
                T=35,
                W=68,
                H=6,
                Text="Sin roads",
            )
        else:
            for i, road_id in enumerate(items):
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=122 + i,
                    BStyle=ISB_STYLE.DARK
                    | ISB_STYLE.SELECTED
                    | ISB_STYLE.CLICK
                    | ISB_STYLE.LEFT,
                    L=2,
                    T=35 + i * 7,
                    W=68,
                    H=6,
                    Text=road_id,
                )
            for i in range(len(items), per_page):
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=122 + i,
                    BStyle=ISB_STYLE.DARK,
                    L=2,
                    T=35 + i * 7,
                    W=68,
                    H=6,
                    Text="",
                )
        # Paginación
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=128,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=77,
            W=20,
            H=6,
            Text="<",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=129,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=24,
            T=77,
            W=24,
            H=6,
            Text=f"{page + 1}/{max_page + 1}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=132,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=50,
            T=77,
            W=20,
            H=6,
            Text=">",
        )
        # ── Columna derecha: seleccionados + acciones ───────────────────────
        prio = buf.get(self._UI_CID_TI1) or "-"
        cede = buf.get(self._UI_CID_TI2) or "-"
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=72,
            T=28,
            W=112,
            H=6,
            Text=f"Prioritaria: {prio}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=112,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=72,
            T=39,
            W=112,
            H=6,
            Text=f"Cede: {cede}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=116,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=72,
            T=55,
            W=54,
            H=8,
            Text="Confirmar",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=117,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=130,
            T=55,
            W=54,
            H=8,
            Text="Cancelar",
        )

    def _map_ui_click_zone_prio_picker(self, cid: int):
        """Clicks de la sub-pantalla de alta de regla (picker de vías)."""
        buf = self._ui_input_buffer
        if cid == 120:  # slot prioritaria
            self._ui_road_picker_slot = "a"
            self._map_ui_redraw_content()
        elif cid == 121:  # slot cede
            self._ui_road_picker_slot = "b"
            self._map_ui_redraw_content()
        elif 122 <= cid <= 127:  # elegir vía del picker
            all_roads = sorted(self.map_recorder.roads.keys())
            idx = self._ui_road_picker_page * self._UI_ROAD_PICKER_ITEMS + (cid - 122)
            if idx < len(all_roads):
                road_id = all_roads[idx]
                if self._ui_road_picker_slot == "a":
                    buf[self._UI_CID_TI1] = road_id
                    self._ui_road_picker_slot = "b"  # avanza al slot B
                else:
                    buf[self._UI_CID_TI2] = road_id
                self._map_ui_redraw_content()
        elif cid == 128:  # página anterior
            if self._ui_road_picker_page > 0:
                self._ui_road_picker_page -= 1
                self._map_ui_redraw_content()
        elif cid == 132:  # página siguiente
            all_roads = sorted(self.map_recorder.roads.keys())
            max_page = max(0, (len(all_roads) - 1) // self._UI_ROAD_PICKER_ITEMS)
            if self._ui_road_picker_page < max_page:
                self._ui_road_picker_page += 1
                self._map_ui_redraw_content()
        elif cid == 116:  # Confirmar
            a = (buf.get(self._UI_CID_TI1) or "").strip()
            b = (buf.get(self._UI_CID_TI2) or "").strip()
            if a and b and a != b:
                self._map_ui_silent_set(
                    self._ui_elem_detail_id, "priority_rules", f"add;{a},{b}"
                )
                self._map_ui_zone_prio_exit_picker()
            else:
                self.send_ISP_MSL(
                    Msg=f"{c.YELLOW}Elige dos vias distintas (prioritaria y la que cede)."
                )
        elif cid == 117:  # Cancelar
            self._map_ui_zone_prio_exit_picker()

    def _map_ui_zone_prio_exit_picker(self):
        """Sale del picker de alta y vuelve al detalle de la zona."""
        self._ui_zone_prio_adding = False
        self._ui_input_buffer.pop(self._UI_CID_TI1, None)
        self._ui_input_buffer.pop(self._UI_CID_TI2, None)
        self._ui_road_picker_page = 0
        self._ui_road_picker_slot = "a"
        self._map_ui_redraw_content()

    # ──────────────────────────────────────────────────────────────────────────
    # Elementos — Cesión de un RoadLink (Fase 8, bloque 8.4)
    #
    # La cesión cuelga del propio giro (diseño S38): una `yield_line` grabada
    # con el coche, un tiempo T (None ⇒ default global) y, opcionalmente, la
    # zona a vigilar. El grabador nace SIEMPRE en manual (aunque el toggle
    # "Auto" general esté activo) y al Terminar pide T (TypeIn con default).
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_yield_default_t(self) -> float:
        """Default global de T (s) — el mismo que consume la conducta (zones.py)."""
        return self.config.get("yield_time_s", DEFAULT_YIELD_TIME_S)

    def _map_ui_draw_link_yield(self, link, u):
        """Sección "Cesion" del detalle de un RoadLink, tras sus campos."""
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._LINK_YIELD_TITLE,
            BStyle=ISB_STYLE.TITLE | ISB_STYLE.LEFT,
            L=2,
            T=86,
            W=180,
            H=6,
            Text="Cesion (ceda el paso)",
        )
        if not link.yield_line:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=self._LINK_YIELD_STATUS,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
                L=2,
                T=93,
                W=108,
                H=6,
                Text="Este giro no cede.",
            )
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=self._LINK_YIELD_REC,
                BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
                L=112,
                T=93,
                W=54,
                H=6,
                Text="+ Grabar linea",
            )
            return

        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._LINK_YIELD_STATUS,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=93,
            W=68,
            H=6,
            Text=f"Linea: {len(link.yield_line)} puntos",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._LINK_YIELD_REC,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=72,
            T=93,
            W=54,
            H=6,
            Text="Regrabar",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._LINK_YIELD_CLEAR,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=144,
            T=93,
            W=22,
            H=6,
            Text="Quitar",
        )
        # Fila de T: TypeIn editable en el propio detalle.
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._LINK_YIELD_T_LBL,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=100,
            W=68,
            H=6,
            Text="yield_time_s:",
        )
        t_txt = (
            str(link.yield_time_s)
            if link.yield_time_s is not None
            else f"default ({self._map_ui_yield_default_t():g})"
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._LINK_YIELD_T_VAL,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 12,
            L=72,
            T=100,
            W=108,
            H=6,
            Text=t_txt,
        )
        self._ui_detail_field_map[self._LINK_YIELD_T_VAL] = ("yield_time_s", "yield_t")
        # Fila de la zona a vigilar: abre el picker.
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._LINK_YIELD_ZONE_LBL,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=107,
            W=68,
            H=6,
            Text="yield_zone_id:",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._LINK_YIELD_ZONE_VAL,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=72,
            T=107,
            W=108,
            H=6,
            Text=link.yield_zone_id or "(ninguna)",
        )

    def _map_ui_draw_link_yield_recorder(self, link, u, rec: dict):
        """Grabador de la línea de detención (pantalla completa del contenido)."""
        n = len(rec.get("nodes", []))
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=109,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=21,
            W=182,
            H=6,
            Text=f"Linea de detencion: {rec.get('link_id', '?')}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=2,
            T=28,
            W=182,
            H=6,
            Text="Para el morro DONDE debe detenerse la IA y anade 2+ puntos a lo ancho del carril.",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=111,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=2,
            T=35,
            W=60,
            H=6,
            Text=f"● {n} puntos",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=112,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=44,
            W=60,
            H=8,
            Text="+ Anadir punto",
        )
        auto_on = (
            rec.get("auto_phase") == "recording"
            and self.map_recorder.auto_recording_enabled
        )
        auto_style = (
            ISB_STYLE.OK | ISB_STYLE.CLICK
            if auto_on
            else ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=113,
            BStyle=auto_style,
            L=64,
            T=44,
            W=40,
            H=8,
            Text="Auto: ON" if auto_on else "Auto: OFF",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=114,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=2,
            T=55,
            W=60,
            H=9,
            Text="Terminar",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=115,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=64,
            T=55,
            W=60,
            H=9,
            Text="Cancelar",
        )

    def _map_ui_draw_link_yield_ask_t(self, link, u, rec: dict):
        """Al Terminar la línea se pide T automáticamente (TypeIn con default)."""
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=109,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=21,
            W=182,
            H=6,
            Text=f"Tiempo T de la cesion: {rec.get('link_id', '?')}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=2,
            T=28,
            W=182,
            H=6,
            Text="La IA cede si el trafico vigilado llega en menos de T segundos.",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=111,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=37,
            W=30,
            H=7,
            Text="T (s):",
        )
        t_txt = (
            str(link.yield_time_s)
            if link.yield_time_s is not None
            else f"default ({self._map_ui_yield_default_t():g})"
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=self._UI_CID_TI1,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 12,
            L=34,
            T=37,
            W=60,
            H=7,
            Text=t_txt,
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=116,
            BStyle=ISB_STYLE.OK | ISB_STYLE.CLICK,
            L=2,
            T=48,
            W=60,
            H=9,
            Text="Guardar",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=117,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=64,
            T=48,
            W=60,
            H=9,
            Text="< Volver",
        )

    def _map_ui_draw_link_zone_picker(self, link, u):
        """Picker de la zona a vigilar (misma UX que el picker de vías)."""
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=109,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=2,
            T=21,
            W=182,
            H=6,
            Text=f"Zona a vigilar: {self._ui_elem_detail_id}",
        )
        all_zones = sorted(self.map_recorder.zones.keys())
        per_page = self._UI_ROAD_PICKER_ITEMS
        max_page = max(0, (len(all_zones) - 1) // per_page) if all_zones else 0
        page = min(self._ui_road_picker_page, max_page)
        self._ui_road_picker_page = page
        items = all_zones[page * per_page : (page + 1) * per_page]
        if not all_zones:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=122,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                L=2,
                T=35,
                W=68,
                H=6,
                Text="Sin zonas en el mapa",
            )
        else:
            for i, zone_id in enumerate(items):
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=122 + i,
                    BStyle=ISB_STYLE.DARK
                    | ISB_STYLE.SELECTED
                    | ISB_STYLE.CLICK
                    | ISB_STYLE.LEFT,
                    L=2,
                    T=35 + i * 7,
                    W=68,
                    H=6,
                    Text=zone_id,
                )
        # Paginación (solo tiene efecto con >6 zonas)
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=128,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=77,
            W=20,
            H=6,
            Text="<",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=129,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=24,
            T=77,
            W=24,
            H=6,
            Text=f"{page + 1}/{max_page + 1}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=132,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=50,
            T=77,
            W=20,
            H=6,
            Text=">",
        )
        # Columna derecha: actual + acciones
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.LEFT,
            L=72,
            T=28,
            W=112,
            H=6,
            Text=f"Actual: {link.yield_zone_id or '-'}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=116,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=72,
            T=55,
            W=54,
            H=8,
            Text="Ninguna",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=117,
            BStyle=ISB_STYLE.CANCEL | ISB_STYLE.CLICK,
            L=130,
            T=55,
            W=54,
            H=8,
            Text="Cancelar",
        )

    def _map_ui_click_link_yield_recorder(self, cid: int):
        """Clicks del grabador de la línea de detención."""
        mr = self.map_recorder
        rec = mr.current_recording
        if cid == 112:  # añadir punto manual (coche del usuario que clica)
            coords = mr.get_coords_fn(self._ui_ucid)
            if coords:
                rec["nodes"].append(copy.deepcopy(coords))
                self.send_ISP_MSL(
                    Msg=f"{c.GREEN}Punto #{len(rec['nodes'])} de la linea añadido."
                )
                self._map_ui_redraw_content()
                self._map_ui_update_header()
            else:
                self.send_ISP_MSL(
                    Msg=f"{c.RED}No se pudo leer tu telemetria (en pista?)."
                )
        elif cid == 113:  # toggle Auto (el grabador nace SIEMPRE manual)
            self._map_ui_yield_toggle_auto()
        elif cid == 114:  # Terminar → pedir T
            if len(rec.get("nodes", [])) < 2:
                self.send_ISP_MSL(
                    Msg=f"{c.YELLOW}La linea necesita al menos 2 puntos "
                    f"(lleva {len(rec.get('nodes', []))})."
                )
                return
            rec["auto_phase"] = "ask_t"  # congela la captura mientras se pide T
            self._ui_input_buffer.pop(self._UI_CID_TI1, None)
            self._map_ui_redraw_content()
            self._map_ui_update_header()
        elif cid == 115:  # Cancelar: descarta sin tocar el link
            mr._cmd_rec_cancel()
            self._map_ui_redraw_content()
            self._map_ui_update_header()

    def _map_ui_yield_toggle_auto(self):
        """Enciende/apaga la captura automática del grabador de la línea.

        ON exige un coche que grabar: si no hay `recording_plid`, se toma el
        del usuario que clica. La fase y la preferencia global van en lockstep
        a partir del primer toggle (al nacer, la fase es manual sin tocar la
        preferencia global — diseño S38: default SIEMPRE manual)."""
        mr = self.map_recorder
        rec = mr.current_recording
        effective = rec.get("auto_phase") == "recording" and mr.auto_recording_enabled
        if effective:
            rec["auto_phase"] = "manual"
            mr.auto_recording_enabled = False
        else:
            if mr.recording_plid is None:
                user = self.user_manager.users.get(self._ui_ucid)
                plid = user.plid if user else None
                if plid is None:
                    self.send_ISP_MSL(
                        Msg=f"{c.RED}No tienes coche en pista para la captura automatica."
                    )
                    return
                mr.recording_plid = plid
            mr.auto_recording_enabled = True
            rec["auto_phase"] = "recording"
        self._map_ui_redraw_content()
        self._map_ui_update_header()

    def _map_ui_click_link_yield_ask_t(self, cid: int):
        """Clicks de la pantalla de T (tras Terminar la línea)."""
        mr = self.map_recorder
        rec = mr.current_recording
        if cid == 116:  # Guardar: comete la línea y fija T
            raw = (self._ui_input_buffer.get(self._UI_CID_TI1) or "").strip().lower()
            if raw in ("", "none") or raw.startswith("default"):
                t_str = "none"  # None ⇒ default global de config
            else:
                try:
                    if float(raw) <= 0:
                        raise ValueError
                    t_str = raw
                except ValueError:
                    self.send_ISP_MSL(
                        Msg=f"{c.RED}T invalido: numero de segundos positivo o 'default'."
                    )
                    return
            link_id = rec["link_id"]
            mr._cmd_rec_end()  # rama yield_line: comete link.yield_line
            self._map_ui_silent_set(link_id, "yield_time_s", t_str)
            self._ui_input_buffer.pop(self._UI_CID_TI1, None)
            self._map_ui_redraw_content()
            self._map_ui_update_header()
        elif cid == 117:  # Volver al grabador (en manual), sin perder puntos
            rec["auto_phase"] = "manual"
            self._map_ui_redraw_content()

    def _map_ui_click_link_zone_picker(self, cid: int):
        """Clicks del picker de la zona a vigilar."""
        all_zones = sorted(self.map_recorder.zones.keys())
        per_page = self._UI_ROAD_PICKER_ITEMS
        if 122 <= cid <= 127:  # elegir zona
            idx = self._ui_road_picker_page * per_page + (cid - 122)
            if idx < len(all_zones):
                self._map_ui_silent_set(
                    self._ui_elem_detail_id, "yield_zone_id", all_zones[idx]
                )
                self._map_ui_link_zone_exit_picker()
        elif cid == 128:  # página anterior
            if self._ui_road_picker_page > 0:
                self._ui_road_picker_page -= 1
                self._map_ui_redraw_content()
        elif cid == 132:  # página siguiente
            max_page = max(0, (len(all_zones) - 1) // per_page)
            if self._ui_road_picker_page < max_page:
                self._ui_road_picker_page += 1
                self._map_ui_redraw_content()
        elif cid == 116:  # Ninguna
            self._map_ui_silent_set(self._ui_elem_detail_id, "yield_zone_id", "none")
            self._map_ui_link_zone_exit_picker()
        elif cid == 117:  # Cancelar
            self._map_ui_link_zone_exit_picker()

    def _map_ui_link_zone_exit_picker(self):
        """Sale del picker de zonas y vuelve al detalle del link."""
        self._ui_link_zone_picking = False
        self._ui_road_picker_page = 0
        self._map_ui_redraw_content()

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers del tab Elementos
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_elem_get_filtered(self) -> list:
        mr = self.map_recorder
        collections = {
            "road": mr.roads,
            "roadlink": mr.road_links,
            "latlink": mr.lateral_links,
            "zone": mr.zones,
            "rule": mr.special_rules,
        }
        coll = collections.get(self._ui_elem_type, {})
        search = self._ui_elem_search.lower()
        return sorted(k for k in coll if search in k.lower())

    def _map_ui_elem_get_obj(self, obj_id: str):
        mr = self.map_recorder
        for coll in (
            mr.roads,
            mr.road_links,
            mr.lateral_links,
            mr.zones,
            mr.special_rules,
        ):
            if obj_id in coll:
                return coll[obj_id]
        return None

    def _map_ui_elem_get_type(self, obj_id: str) -> str:
        mr = self.map_recorder
        if obj_id in mr.roads:
            return "road"
        if obj_id in mr.road_links:
            return "roadlink"
        if obj_id in mr.lateral_links:
            return "latlink"
        if obj_id in mr.zones:
            return "zone"
        if obj_id in mr.special_rules:
            return "rule"
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
        now = time.time()
        # Overlay whereami: se refresca aunque el menú esté cerrado (persiste hasta
        # que se deselecciona en Info). Es lo único de la UI que vive fuera de la
        # sesión de menú.
        if getattr(self, "_ui_whereami_ucid", None) is not None and self._ui_whereami:
            if now - self._ui_whereami_last_update >= self._ui_whereami_interval:
                self._ui_whereami_last_update = now
                self._map_ui_refresh_pinned_whereami()

        # El resto del refresco requiere el menú abierto.
        if getattr(self, "_ui_ucid", None) is None:
            return
        if self._ui_tab == "debug" and self._ui_debug_plid is not None:
            if now - self._ui_debug_last_update >= self._ui_debug_interval:
                self._ui_debug_last_update = now
                self._map_ui_refresh_debug_detail()

        if self._ui_node_flash_time and now - self._ui_node_flash_time >= 0.5:
            self._ui_node_flash_time = 0.0
            rec = self.map_recorder.current_recording
            if rec:
                n = len(rec.get("nodes", []))
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=self._ui_ucid,
                    ClickID=111,
                    T=0,
                    L=0,
                    W=0,
                    H=0,
                    BStyle=0,
                    Text=f"● {n} nodos",
                )

    def on_ISP_BTC(self, packet: ISP_BTC):
        # UCID=0 en BTC/BTT significa "local" (InSim en la misma máquina que LFS)
        if self._ui_ucid is None or (packet.UCID != self._ui_ucid and packet.UCID != 0):
            return
        self._map_ui_handle_click(packet.ClickID)

    def on_ISP_BTT(self, packet: ISP_BTT):
        if self._ui_ucid is None or (packet.UCID != self._ui_ucid and packet.UCID != 0):
            return
        text = packet.Text.strip()
        self._ui_input_buffer[packet.ClickID] = text
        self.send_ISP_BTN(
            ReqI=1,
            UCID=self._ui_ucid,
            ClickID=packet.ClickID,
            BStyle=0,
            L=0,
            T=0,
            W=0,
            H=0,
            Text=text if text else " ",
        )
        # Intervalo de spawn de AIs (Run tab) — CID 119
        if packet.ClickID == 119:
            try:
                val = float(text)
                if val > 0:
                    self._ui_run_interval = val
                    self._freeroam_spawn_interval = val
                else:
                    raise ValueError
            except ValueError:
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=self._ui_ucid,
                    ClickID=119,
                    BStyle=0,
                    L=0,
                    T=0,
                    W=0,
                    H=0,
                    Text=str(self._ui_run_interval),
                )
            return

        # Intervalo de refresco (whereami / debug) — CID 147 compartido
        if packet.ClickID == 147:
            try:
                val = float(text)
                if val > 0:
                    if self._ui_tab == "info":
                        self._ui_whereami_interval = val
                        self._ui_whereami_last_update = 0.0
                    elif self._ui_tab == "debug":
                        self._ui_debug_interval = val
                        self._ui_debug_last_update = 0.0
            except ValueError:
                interval = (
                    self._ui_whereami_interval
                    if self._ui_tab == "info"
                    else self._ui_debug_interval
                )
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=self._ui_ucid,
                    ClickID=147,
                    BStyle=0,
                    L=0,
                    T=0,
                    W=0,
                    H=0,
                    Text=str(interval),
                )
            return

        # Velocidad por defecto de grabado (pestaña Grabar) — CID 129
        if packet.ClickID == 129 and self._ui_tab == "grabar":
            try:
                val = float(text)
                if val <= 0:
                    raise ValueError
                self.map_recorder.default_speed_limit_kmh = val
            except ValueError:
                # Texto inválido: revertir al valor válido actual.
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=self._ui_ucid,
                    ClickID=129,
                    BStyle=0,
                    L=0,
                    T=0,
                    W=0,
                    H=0,
                    Text=str(self.map_recorder.default_speed_limit_kmh),
                )
            return

        # En la vista detalle de Elementos, aplicar cambio inmediatamente
        if (
            self._ui_tab == "elementos"
            and self._ui_elem_detail_id is not None
            and packet.ClickID in self._ui_detail_field_map
        ):
            fname, ftype = self._ui_detail_field_map[packet.ClickID]
            if ftype not in ("bool", "enum_traffic", "enum_indicators") and text:
                if ftype == "yield_t":
                    # T de la cesión: número positivo, o "default"/"none" ⇒ None.
                    low = text.lower()
                    if low == "none" or low.startswith("default"):
                        text = "none"
                    else:
                        try:
                            if float(text) <= 0:
                                raise ValueError
                        except ValueError:
                            self._map_ui_redraw_content()  # restaura el valor real
                            return
                elif ftype == "float":
                    try:
                        float(text)
                    except ValueError:
                        obj = self._map_ui_elem_get_obj(self._ui_elem_detail_id)
                        prev = (
                            self._map_ui_elem_field_value_str(obj, fname) if obj else ""
                        )
                        self.send_ISP_BTN(
                            ReqI=1,
                            UCID=self._ui_ucid,
                            ClickID=packet.ClickID,
                            BStyle=0,
                            L=0,
                            T=0,
                            W=0,
                            H=0,
                            Text=prev if prev else " ",
                        )
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
            self._ui_zone_prio_adding = False
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
        elif self._ui_tab == "debug":
            self._map_ui_click_debug(cid)
        elif self._ui_tab == "run":
            self._map_ui_click_run(cid)

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
                self.send_ISP_MSL(
                    Msg=f"{c.YELLOW}Escribe el nombre del mapa a borrar primero."
                )
        elif 114 <= cid <= 119:
            maps = self._map_ui_get_map_list()
            idx = cid - 114
            if idx < len(maps):
                self.map_recorder._cmd_set_map(maps[idx])
                self._map_ui_update_header()
                self._map_ui_redraw_content()

    def _map_ui_click_grabar(self, cid: int):
        rec = self.map_recorder.current_recording
        buf = self._ui_input_buffer

        if rec and rec.get("auto"):
            phase = rec.get("auto_phase")
            if phase == "confirm":
                self._map_ui_click_auto_link_confirm(cid)
            elif phase == "conflict":
                self._map_ui_click_auto_link_conflict(cid)
            else:
                self._map_ui_click_auto_link_recording(cid)
            return

        if rec:
            if cid == 112:
                coords = self.map_recorder.get_coords_fn(self._ui_ucid)
                if coords:
                    self.map_recorder.current_recording["nodes"].append(
                        copy.deepcopy(coords)
                    )
                    n = len(self.map_recorder.current_recording["nodes"])
                    self.send_ISP_MSL(Msg=f"{c.GREEN}Nodo #{n} añadido manualmente.")
                    self._map_ui_redraw_content()
                    self._map_ui_update_header()
                else:
                    self.send_ISP_MSL(
                        Msg=f"{c.RED}Error: No se pudo obtener telemetria (en pista?)."
                    )
            elif cid == 113:
                if rec.get("type") == "yield_line":
                    # La captura de la línea se congela por fase: el toggle
                    # debe mover fase y preferencia global a la vez.
                    self._map_ui_yield_toggle_auto()
                    return
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
                        self._ui_road_picker_slot = (
                            "b"  # avanza al slot B automáticamente
                        )
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
                suf_a = buf.get(self._UI_CID_TI_SUF_A, "").strip()
                road_b = buf.get(self._UI_CID_TI2, "").strip()
                suf_b = buf.get(self._UI_CID_TI_SUF_B, "").strip()
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
                    self.send_ISP_MSL(
                        Msg=f"{c.RED}Rellena ambos campos antes de confirmar."
                    )
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

        elif self._ui_pending_action == "select_recorder_plid":
            if cid == 108:  # Volver
                self._ui_pending_action = None
                self._ui_grabar_player_page = 0
                self._map_ui_redraw_content()
            elif 110 <= cid <= 117:  # items de la lista
                all_cars = []
                for p in self.user_manager.players.values():
                    all_cars.append(p.plid)
                for ai in self.user_manager.ais.values():
                    all_cars.append(ai.player.plid)
                all_cars.sort()
                per_page = self._UI_GRABAR_PLAYER_ITEMS
                idx = self._ui_grabar_player_page * per_page + (cid - 110)
                if idx < len(all_cars):
                    self.map_recorder.recording_plid = all_cars[idx]
                    self._ui_pending_action = None
                    self._ui_grabar_player_page = 0
                    self._map_ui_redraw_content()
            elif cid == 120:  # página anterior
                if self._ui_grabar_player_page > 0:
                    self._ui_grabar_player_page -= 1
                    self._map_ui_redraw_content()
            elif cid == 122:  # página siguiente
                all_cars_count = len(self.user_manager.players) + len(
                    self.user_manager.ais
                )
                max_page = max(0, (all_cars_count - 1) // self._UI_GRABAR_PLAYER_ITEMS)
                if self._ui_grabar_player_page < max_page:
                    self._ui_grabar_player_page += 1
                    self._map_ui_redraw_content()

        else:  # idle
            if (
                cid in (110, 111, 112, 113, 114, 118)
                and self.map_recorder.recording_plid is None
            ):
                self.send_ISP_MSL(
                    Msg=f"{c.RED}Selecciona primero el jugador a grabar (botón Cambiar...)."
                )
                return
            if cid == 108:  # Toggle norma de trafico por defecto (nuevas vias)
                from insims.ai_control.nav_modes.freeroam.enums import TrafficRule

                current = self.map_recorder.default_traffic_rule
                new_rule = (
                    TrafficRule.RHT if current == TrafficRule.LHT else TrafficRule.LHT
                )
                self.map_recorder._cmd_rec_road_rule(new_rule.name)
                self._map_ui_redraw_content()
            elif cid == 118:  # Link auto (RoadLink con origen/destino auto-detectados)
                self._map_ui_start_auto_link()
            elif cid == 110:
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
            elif cid == 117:  # Cambiar jugador
                self._ui_pending_action = "select_recorder_plid"
                self._ui_grabar_player_page = 0
                self._map_ui_redraw_content()

    def _map_ui_click_info(self, cid: int):
        if cid == 110:
            self._ui_info_stats = not self._ui_info_stats
            self._map_ui_redraw_content()
        elif cid == 111:
            self._ui_info_check = not self._ui_info_check
            self._ui_check_page = 0
            self._map_ui_redraw_content()
        elif cid == 122:  # Aplicar buscador
            self._ui_check_search = self._ui_input_buffer.get(121, "").strip()
            self._ui_check_page = 0
            self._map_ui_redraw_content()
        elif cid == 123:
            self._ui_check_filter = "all"
            self._ui_check_page = 0
            self._map_ui_redraw_content()
        elif cid == 124:
            self._ui_check_filter = "error"
            self._ui_check_page = 0
            self._map_ui_redraw_content()
        elif cid == 125:
            self._ui_check_filter = "warn"
            self._ui_check_page = 0
            self._map_ui_redraw_content()
        elif cid == 130 and self._ui_check_page > 0:
            self._ui_check_page -= 1
            self._map_ui_redraw_content()
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
            total_pages = max(
                1,
                (len(all_items) + self._CHECK_ITEMS_PER_PAGE - 1)
                // self._CHECK_ITEMS_PER_PAGE,
            )
            if self._ui_check_page < total_pages - 1:
                self._ui_check_page += 1
                self._map_ui_redraw_content()
        elif cid == 112:
            self._ui_info_roads = not self._ui_info_roads
            self._ui_roads_page = 0
            self._map_ui_redraw_content()
        elif cid == 134:  # Aplicar buscador roads
            self._ui_roads_search = self._ui_input_buffer.get(133, "").strip()
            self._ui_roads_page = 0
            self._map_ui_redraw_content()
        elif cid == 135:
            self._ui_roads_filter = "all"
            self._ui_roads_page = 0
            self._map_ui_redraw_content()
        elif cid == 136:
            self._ui_roads_filter = "open"
            self._ui_roads_page = 0
            self._map_ui_redraw_content()
        elif cid == 137:
            self._ui_roads_filter = "closed"
            self._ui_roads_page = 0
            self._map_ui_redraw_content()
        elif 138 <= cid <= 143:  # Toggle is_closed de un road
            start = self._ui_roads_page * self._ROADS_ITEMS_PER_PAGE
            search = self._ui_roads_search.lower()
            all_roads = [
                (r_id, road.is_closed) for r_id, road in self.map_recorder.roads.items()
            ]
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
                self._map_ui_silent_set(
                    r_id, "is_closed", "false" if is_closed else "true"
                )
                self._map_ui_redraw_content()
        elif cid == 144 and self._ui_roads_page > 0:
            self._ui_roads_page -= 1
            self._map_ui_redraw_content()
        elif cid == 146:
            search = self._ui_roads_search.lower()
            all_roads = [
                (r_id, road.is_closed) for r_id, road in self.map_recorder.roads.items()
            ]
            if self._ui_roads_filter == "open":
                all_roads = [(r, c) for r, c in all_roads if not c]
            elif self._ui_roads_filter == "closed":
                all_roads = [(r, c) for r, c in all_roads if c]
            if search:
                all_roads = [(r, c) for r, c in all_roads if search in r.lower()]
            total_pages = max(
                1,
                (len(all_roads) + self._ROADS_ITEMS_PER_PAGE - 1)
                // self._ROADS_ITEMS_PER_PAGE,
            )
            if self._ui_roads_page < total_pages - 1:
                self._ui_roads_page += 1
                self._map_ui_redraw_content()
        elif 113 <= cid <= 118:
            wa_type = self._WA_TYPES[cid - 113]
            if wa_type in self._ui_whereami:
                self._ui_whereami.discard(wa_type)
            else:
                self._ui_whereami.add(wa_type)
                self._ui_whereami_ucid = self._ui_ucid
            if self._ui_whereami:
                self._map_ui_redraw_pinned_whereami()
                self._ui_whereami_last_update = 0.0  # fuerza refresco inmediato
            else:
                # Última selección quitada → borra el overlay y suelta el UCID.
                self._map_ui_clear_pinned_whereami()
                self._ui_whereami_ucid = None
            self._map_ui_redraw_content()  # refresca el resaltado de los botones WA

    # ──────────────────────────────────────────────────────────────────────────
    # Tab: Debug
    # ──────────────────────────────────────────────────────────────────────────

    _UI_DEBUG_ITEMS = 6

    def _map_ui_draw_tab_debug(self):
        if self._ui_debug_plid is None:
            self._map_ui_draw_debug_list()
        else:
            self._map_ui_draw_debug_detail()

    def _map_ui_get_freeroam_ais(self) -> list:
        """Devuelve lista de (plid, ai_name, behavior) de AIs en FreeroamMode."""
        result = []
        for plid, ai in self.user_manager.ais.items():
            if "aic" not in ai.extra:
                continue
            behavior = ai.extra["aic"]
            if isinstance(behavior.active_mode, FreeroamMode):
                result.append((plid, ai.ai_name, behavior))
        return sorted(result, key=lambda x: x[0])

    def _map_ui_build_debug_lines(self, plid: int) -> list[str]:
        """Genera las líneas de estado de una AI (equivalente a ai_state)."""
        ai = self.user_manager.ais.get(plid)
        if not ai or "aic" not in ai.extra:
            return [f"PLID {plid} no encontrado o sin AIBehavior"]
        behavior = ai.extra["aic"]
        mode = behavior.active_mode

        t_speed = (
            behavior.speed_request
            if isinstance(behavior.speed_request, (int, float))
            else 0.0
        )
        gear = getattr(behavior.gear_mode, "name", str(behavior.gear_mode))

        if not isinstance(mode, FreeroamMode):
            modo_str = type(mode).__name__ if mode else "Parada"
            return [
                f"Vel. Obj: {t_speed:.1f} km/h  |  Marcha: {gear}",
                f"Modo activo: {modo_str}",
                "",
                "",
                "",
                "",
            ]

        maneuver = getattr(mode.maneuver_state, "name", str(mode.maneuver_state))
        ov_state = getattr(mode, "overtake_state", "N/A")
        c_type = mode.current_type or "–"
        c_id = mode.current_id or "N/A"
        n_type = mode.next_link_type or "–"
        n_id = mode.next_link_id or "N/A"
        blinkers = getattr(mode.blinkers_active, "name", str(mode.blinkers_active))
        opposing = mode.is_driving_opposing
        p_road = mode.previous_road_id or "N/A"
        c_road = mode.current_road_id or "N/A"
        v_base = getattr(mode, "_debug_speed_base", 0.0)

        # Motivo de reducción de velocidad respecto a la base
        reduccion = ""
        bp = mode.blocking_plid
        bd = getattr(mode, "blocking_dist", 0.0)
        if abs(t_speed - v_base) > 0.5:
            if getattr(mode, "yield_active", False):
                reduccion = "Ceda el paso"
            elif ov_state == "OVERTAKING":
                reduccion = "Adelantando"
            elif ov_state == "RETURNING":
                reduccion = "Volviendo al carril"
            elif bp is not None:
                p = self.user_manager.players.get(bp)
                a = self.user_manager.ais.get(bp)
                bname = None
                if p:
                    u2 = self.user_manager.users.get(p.ucid)
                    bname = u2.player_name if u2 else None
                if not bname and a:
                    bname = a.ai_name
                bname = bname or f"PLID {bp}"
                reduccion = f"ACC: {bname} ({bp}) a {bd:.1f}m"
            elif mode.active_special_rules:
                reduccion = "Reg. especial"
            else:
                reduccion = "Reducida"

        vel_line = f"Vel: {t_speed:.1f}  Base: {v_base:.1f} km/h"
        if reduccion:
            vel_line += f"  ^3{reduccion}"

        return [
            vel_line,
            f"Maniobra: {maneuver}  |  Estado OT: {ov_state}",
            f"Loc: {c_type} ({c_id})  |  Nodo: {mode.node_index}",
            f"Proximo: {n_type} ({n_id})",
            f"Intermi: {blinkers}  |  Contrario: {opposing}",
            f"Viene de: {p_road}  |  Via: {c_road}",
        ]

    def _map_ui_draw_debug_list(self):
        u = self._ui_ucid
        ais = self._map_ui_get_freeroam_ais()
        per_page = self._UI_DEBUG_ITEMS
        total = len(ais)
        max_page = max(0, (total - 1) // per_page) if total else 0
        page = min(self._ui_debug_page, max_page)
        self._ui_debug_page = page
        items = ais[page * per_page : (page + 1) * per_page]

        # Cabecera + TypeIn intervalo
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=108,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=2,
            T=21,
            W=130,
            H=7,
            Text=f"AIs en FreeroamMode: {total}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=109,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=134,
            T=21,
            W=20,
            H=7,
            Text="Int:",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=147,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 6,
            L=156,
            T=21,
            W=28,
            H=7,
            Text=str(self._ui_debug_interval),
        )

        if not ais:
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=110,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                L=2,
                T=30,
                W=182,
                H=7,
                Text="Ninguna AI en modo Freeroam",
            )
        else:
            for i, (plid, ai_name, behavior) in enumerate(items):
                maneuver = getattr(
                    behavior.active_mode.maneuver_state,
                    "name",
                    str(behavior.active_mode.maneuver_state),
                )
                label = f"PLID {plid}   {ai_name}   [{maneuver}]"
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=110 + i,
                    BStyle=ISB_STYLE.DARK
                    | ISB_STYLE.SELECTED
                    | ISB_STYLE.CLICK
                    | ISB_STYLE.LEFT,
                    L=2,
                    T=30 + i * 8,
                    W=182,
                    H=7,
                    Text=label,
                )
            for i in range(len(items), per_page):
                self.send_ISP_BTN(
                    ReqI=1,
                    UCID=u,
                    ClickID=110 + i,
                    BStyle=ISB_STYLE.DARK,
                    L=2,
                    T=30 + i * 8,
                    W=182,
                    H=7,
                    Text="",
                )

        T_pag = 30 + per_page * 8
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=120,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=T_pag,
            W=20,
            H=7,
            Text="<",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=121,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=24,
            T=T_pag,
            W=30,
            H=7,
            Text=f"{page + 1}/{max_page + 1}",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=122,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=56,
            T=T_pag,
            W=20,
            H=7,
            Text=">",
        )

    def _map_ui_draw_debug_detail(self):
        u = self._ui_ucid
        plid = self._ui_debug_plid
        ai = self.user_manager.ais.get(plid)
        ai_name = ai.ai_name if ai else f"PLID {plid}"

        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=108,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=21,
            W=30,
            H=7,
            Text="<- Volver",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=109,
            BStyle=ISB_STYLE.TITLE | ISB_STYLE.LEFT,
            L=34,
            T=21,
            W=100,
            H=7,
            Text=f"{ai_name} (PLID {plid})",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=147,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 6,
            L=156,
            T=21,
            W=28,
            H=7,
            Text=str(self._ui_debug_interval),
        )

        lines = self._map_ui_build_debug_lines(plid)
        for i, line in enumerate(lines[:8]):
            self.send_ISP_BTN(
                ReqI=1,
                UCID=u,
                ClickID=110 + i,
                BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
                L=2,
                T=30 + i * 8,
                W=182,
                H=7,
                Text=line,
            )

    def _map_ui_refresh_debug_detail(self):
        """Actualiza en-place las líneas de estado sin redibujar toda la UI."""
        plid = self._ui_debug_plid
        if plid is None:
            return
        lines = self._map_ui_build_debug_lines(plid)
        for i, line in enumerate(lines[:8]):
            self.send_ISP_BTN(
                ReqI=1,
                UCID=self._ui_ucid,
                ClickID=110 + i,
                BStyle=0,
                L=0,
                T=0,
                W=0,
                H=0,
                Text=line,
            )

    def _map_ui_click_debug(self, cid: int):
        if self._ui_debug_plid is not None:
            if cid == 108:  # Volver
                self._ui_debug_plid = None
                self._ui_debug_last_update = 0.0
                self._map_ui_redraw_content()
        else:
            if 110 <= cid <= 115:
                ais = self._map_ui_get_freeroam_ais()
                idx = self._ui_debug_page * self._UI_DEBUG_ITEMS + (cid - 110)
                if idx < len(ais):
                    self._ui_debug_plid = ais[idx][0]
                    self._ui_debug_last_update = 0.0
                    self._map_ui_redraw_content()
            elif cid == 120:
                if self._ui_debug_page > 0:
                    self._ui_debug_page -= 1
                    self._map_ui_redraw_content()
            elif cid == 122:
                ais = self._map_ui_get_freeroam_ais()
                max_page = max(0, (len(ais) - 1) // self._UI_DEBUG_ITEMS) if ais else 0
                if self._ui_debug_page < max_page:
                    self._ui_debug_page += 1
                    self._map_ui_redraw_content()

    def _map_ui_click_elementos(self, cid: int):
        # ── Vista detalle ──────────────────────────────────────────────────
        if self._ui_elem_detail_id is not None:
            rec = self.map_recorder.current_recording
            if (  # grabador de la línea de cesión de ESTE link
                rec
                and rec.get("type") == "yield_line"
                and rec.get("link_id") == self._ui_elem_detail_id
            ):
                if rec.get("auto_phase") == "ask_t":
                    self._map_ui_click_link_yield_ask_t(cid)
                else:
                    self._map_ui_click_link_yield_recorder(cid)
                return
            if self._ui_link_zone_picking:  # picker de zona a vigilar
                self._map_ui_click_link_zone_picker(cid)
                return
            if self._ui_zone_prio_adding:  # sub-pantalla de alta de regla
                self._map_ui_click_zone_prio_picker(cid)
                return
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
                        cycle = {
                            "OFF": "left",
                            "LEFT": "right",
                            "RIGHT": "off",
                            "": "off",
                        }
                        new_val = cycle.get(cur, "off")
                        self._map_ui_silent_set(self._ui_elem_detail_id, fname, new_val)
                        self._map_ui_redraw_content()
            elif cid == self._ZONE_PRIO_ADD:  # abre el picker de vías
                self._ui_zone_prio_adding = True
                self._ui_road_picker_page = 0
                self._ui_road_picker_slot = "a"
                self._ui_input_buffer.pop(self._UI_CID_TI1, None)
                self._ui_input_buffer.pop(self._UI_CID_TI2, None)
                self._map_ui_redraw_content()
            elif cid in self._ui_zone_prio_map:  # Quitar una regla
                via_a, via_b = self._ui_zone_prio_map[cid]
                self._map_ui_silent_set(
                    self._ui_elem_detail_id, "priority_rules", f"del;{via_a},{via_b}"
                )
                self._map_ui_redraw_content()
            elif cid == self._LINK_YIELD_REC:  # abre el grabador de la línea
                if self.map_recorder.current_recording:
                    self.send_ISP_MSL(
                        Msg=f"{c.YELLOW}Ya hay una grabacion en curso: "
                        "terminala o cancelala primero."
                    )
                    return
                self.map_recorder.current_recording = {
                    "type": "yield_line",
                    "link_id": self._ui_elem_detail_id,
                    "nodes": [],
                    # Nace SIEMPRE manual, aunque el Auto general esté activo
                    # (diseño S38); update_recording congela toda fase que no
                    # sea "recording".
                    "auto_phase": "manual",
                }
                self._map_ui_redraw_content()
                self._map_ui_update_header()
            elif cid == self._LINK_YIELD_CLEAR:  # retira la cesión del giro
                obj = self._map_ui_elem_get_obj(self._ui_elem_detail_id)
                if obj is not None:
                    obj.yield_line = []
                    obj.yield_time_s = None
                    obj.yield_zone_id = None
                    self._map_ui_redraw_content()
            elif cid == self._LINK_YIELD_ZONE_VAL:  # abre el picker de zonas
                self._ui_link_zone_picking = True
                self._ui_road_picker_page = 0
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
            self._ui_elem_search = self._ui_input_buffer.get(
                self._UI_CID_TI1, ""
            ).strip()
            self._ui_elem_page = 0
            self._map_ui_redraw_content()
        elif 114 <= cid <= 119:  # Click en item
            items = self._map_ui_elem_get_filtered()
            idx = self._ui_elem_page * _ITEMS_PER_PAGE + (cid - 114)
            if idx < len(items):
                self._ui_elem_detail_id = items[idx]
                self._ui_zone_prio_adding = False
                self._ui_link_zone_picking = False
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
    # Tab: Run
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_draw_tab_run(self):
        u = self._ui_ucid
        running = getattr(self, "_is_freeroam_loop_running", False)
        target = self._ui_run_target
        n_ais = len(self.user_manager.ais)
        n_players = len(self.user_manager.players)
        n_total = n_ais + n_players

        # Estado general
        status_style = ISB_STYLE.OK if running else ISB_STYLE.DARK | ISB_STYLE.SELECTED
        status_text = "^2● Activo" if running else "^7● Inactivo"
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=110,
            BStyle=status_style | ISB_STYLE.LEFT,
            L=2,
            T=21,
            W=184,
            H=7,
            Text=status_text,
        )

        # Coches en pista
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=111,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=2,
            T=30,
            W=184,
            H=6,
            Text=f"En pista: {n_total}  ({n_ais} AIs + {n_players} jugadores)",
        )

        # Selector de objetivo
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=112,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=2,
            T=40,
            W=14,
            H=8,
            Text="-",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=113,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=18,
            T=40,
            W=80,
            H=8,
            Text=f"Objetivo: {target} coches",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=114,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=100,
            T=40,
            W=14,
            H=8,
            Text="+",
        )

        # Intervalo entre spawns
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=118,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.LEFT,
            L=2,
            T=51,
            W=70,
            H=6,
            Text="Intervalo entre AIs (s):",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=119,
            BStyle=ISB_STYLE.LIGHT | ISB_STYLE.CLICK,
            TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | 8,
            L=74,
            T=51,
            W=40,
            H=6,
            Text=str(self._ui_run_interval),
        )

        # Botones acción
        start_style = (
            ISB_STYLE.DARK | ISB_STYLE.SELECTED
            if running
            else ISB_STYLE.OK | ISB_STYLE.CLICK
        )
        stop_style = (
            ISB_STYLE.CANCEL | ISB_STYLE.CLICK
            if running
            else ISB_STYLE.DARK | ISB_STYLE.SELECTED
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=115,
            BStyle=start_style,
            L=2,
            T=60,
            W=58,
            H=9,
            Text="Iniciar",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=116,
            BStyle=stop_style,
            L=62,
            T=60,
            W=58,
            H=9,
            Text="Detener",
        )
        self.send_ISP_BTN(
            ReqI=1,
            UCID=u,
            ClickID=117,
            BStyle=ISB_STYLE.DARK | ISB_STYLE.SELECTED | ISB_STYLE.CLICK,
            L=122,
            T=60,
            W=64,
            H=9,
            Text="Limpiar AIs",
        )

    def _map_ui_click_run(self, cid: int):
        if cid == 112:  # -
            self._ui_run_target = max(0, self._ui_run_target - 1)
            self._target_freeroam_count = self._ui_run_target
            self._map_ui_redraw_content()
        elif cid == 114:  # +
            self._ui_run_target += 1
            self._target_freeroam_count = self._ui_run_target
            self._map_ui_redraw_content()
        elif cid == 115:  # Iniciar
            if not getattr(self, "_is_freeroam_loop_running", False):
                self._target_freeroam_count = self._ui_run_target

                # Reutilizamos _test_freeroam pasando un packet simulado con el UCID actual
                class _FakePacket:
                    UCID = self._ui_ucid

                self._test_freeroam(_FakePacket(), self._ui_run_target)
            self._map_ui_redraw_content()
        elif cid == 116:  # Detener
            self._stop_traffic_loops()
            self._map_ui_redraw_content()
        elif cid == 117:  # Limpiar AIs
            for plid in list(self.user_manager.ais.keys()):
                self._cmd_spec(plid)
            self._map_ui_redraw_content()

    # ──────────────────────────────────────────────────────────────────────────
    # Cierre
    # ──────────────────────────────────────────────────────────────────────────

    def _map_ui_close(self):
        self.send_ISP_BFN(SubT=BFN.CLEAR, UCID=self._ui_ucid)
        self._ui_ucid = None
        self._ui_pending_action = None
        self._ui_input_buffer = {}
        # El overlay whereami sobrevive al cierre del menú (solo se quita
        # deseleccionándolo). BFN.CLEAR acaba de borrarlo → lo redibujamos.
        if self._ui_whereami:
            self._map_ui_redraw_pinned_whereami()
