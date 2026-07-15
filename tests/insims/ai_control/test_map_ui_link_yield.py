"""
UI de mapeo de la CESIÓN de un RoadLink (Fase 8, bloque 8.4) en `map_ui.py`.

Diseño S38 punto 8: en el detalle del link (pestaña Elementos) una sección
"Cesion" muestra el estado (`yield_line` / T / zona) y da acceso a:

  - un GRABADOR de puntos de la línea de detención, que nace SIEMPRE en modo
    manual (aunque el toggle "Auto" general esté activo) y al Terminar pide T
    automáticamente (TypeIn con default);
  - un PICKER de zonas (misma UX que el picker de vías) para `yield_zone_id`;
  - el TypeIn de T en el propio detalle y el botón "Quitar" para retirar la
    cesión del giro.

El estado del grabador vive en `map_recorder.current_recording` (sobrevive a
cerrar/reabrir el menú, como "Link auto"): `type="yield_line"`, `link_id` y
`auto_phase` ("manual" | "recording" | "ask_t"; solo "recording" deja capturar
a `update_recording`). Red primero (MODUS §3) sobre el harness `ai_control`.
"""

from __future__ import annotations

import pytest

from insims.ai_control.nav_modes.freeroam.graph import IntersectionZone
from insims.users_management.um_class import User
from lfs_insim.packets import ISP_BTT

# CIDs del grabador (pantalla completa; misma semántica que la pestaña Grabar).
_CID_ANADIR_PUNTO = 112
_CID_AUTO = 113
_CID_TERMINAR = 114
_CID_CANCELAR = 115
# CIDs de la pantalla "ask_t" (pedir T al terminar).
_CID_GUARDAR_T = 116
_CID_VOLVER_T = 117
_TI1 = 130
# CIDs del picker de zonas (misma mecánica que el picker de vías).
_CID_ZONA_ITEM0 = 122
_CID_ZONA_NINGUNA = 116
_CID_ZONA_CANCELAR = 117

_LINK_ID = "R1->R2"


def _btns(app):
    return [p for p in app.client.sent if type(p).__name__ == "ISP_BTN"]


def _texts(app):
    return [b.Text for b in _btns(app)]


def _setup_link_detail(
    app,
    make_road,
    make_road_link,
    populate_graph,
    make_coords,
    *,
    yield_pts=None,
    yield_t=None,
    yield_zone=None,
    zones=(),
):
    """Deja `app` en el detalle del RoadLink R1->R2 (pestaña Elementos)."""
    populate_graph(
        app.map_recorder,
        roads=[
            make_road("R1", [(-50, 0), (0, 0)]),
            make_road("R2", [(0, 0), (0, 50)]),
        ],
        road_links=[make_road_link("R1", "R2", [(0, 0), (0, 5)])],
    )
    link = app.map_recorder.road_links[_LINK_ID]
    if yield_pts:
        link.yield_line = [make_coords(x, y) for x, y in yield_pts]
    link.yield_time_s = yield_t
    link.yield_zone_id = yield_zone
    for zone_id in zones:
        app.map_recorder.zones[zone_id] = IntersectionZone(
            zone_id=zone_id, nodes=[make_coords(0, 0)]
        )
    app.map_recorder.active_map_name = "test"
    app.map_recorder.client = app.client
    app._init_ui_state()
    app._ui_ucid = 3
    app._ui_tab = "elementos"
    app._ui_elem_type = "roadlink"
    app._ui_elem_detail_id = _LINK_ID
    return link


def _user_on_track(app, make_player, make_telemetry, x_m, y_m, ucid=3, plid=5):
    """Pone al usuario `ucid` en pista con su coche en (x_m, y_m)."""
    tele = make_telemetry(x_m=x_m, y_m=y_m)
    app.user_manager.players[plid] = make_player(plid=plid, ucid=ucid, telemetry=tele)
    app.user_manager.users[ucid] = User(
        user_name="mapper",
        ucid=ucid,
        player_name="Mapper",
        admin=0,
        connection_type=0,
        plid=plid,
    )


def _open_recorder(app):
    """Abre el grabador de la línea desde el detalle del link."""
    app._map_ui_click_elementos(app._LINK_YIELD_REC)
    return app.map_recorder.current_recording


# ─── Sección "Cesion" del detalle ────────────────────────────────────────────


class TestSeccionCesionDetalle:
    def test_link_sin_cesion_muestra_boton_grabar(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)
        btns = _btns(ai_control)
        texts = [b.Text for b in btns]
        assert any("Cesion" in t for t in texts)  # título de la sección
        assert any("no cede" in t for t in texts)  # estado
        assert any(b.ClickID == ai_control._LINK_YIELD_REC for b in btns)
        # Sin línea no hay ni Quitar ni fila de T ni fila de zona.
        assert not any(b.ClickID == ai_control._LINK_YIELD_CLEAR for b in btns)
        assert not any(b.ClickID == ai_control._LINK_YIELD_T_VAL for b in btns)
        assert not any(b.ClickID == ai_control._LINK_YIELD_ZONE_VAL for b in btns)

    def test_link_con_cesion_muestra_t_zona_y_quitar(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_pts=[(0, -2), (0, 2)],
            yield_t=3.0,
            yield_zone="CRUCE",
            zones=("CRUCE",),
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)
        btns = _btns(ai_control)
        texts = [b.Text for b in btns]
        assert any("2 puntos" in t for t in texts)
        t_btn = next(b for b in btns if b.ClickID == ai_control._LINK_YIELD_T_VAL)
        assert "3.0" in t_btn.Text
        zone_btn = next(b for b in btns if b.ClickID == ai_control._LINK_YIELD_ZONE_VAL)
        assert "CRUCE" in zone_btn.Text
        assert any(b.ClickID == ai_control._LINK_YIELD_CLEAR for b in btns)
        rec_btn = next(b for b in btns if b.ClickID == ai_control._LINK_YIELD_REC)
        assert "Regrabar" in rec_btn.Text

    def test_t_sin_fijar_muestra_default(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_pts=[(0, -2), (0, 2)],
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)
        t_btn = next(
            b for b in _btns(ai_control) if b.ClickID == ai_control._LINK_YIELD_T_VAL
        )
        assert "default" in t_btn.Text

    def test_quitar_cesion_limpia_los_tres_campos(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_pts=[(0, -2), (0, 2)],
            yield_t=3.0,
            yield_zone="CRUCE",
            zones=("CRUCE",),
        )
        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_CLEAR)
        assert link.yield_line == []
        assert link.yield_time_s is None
        assert link.yield_zone_id is None


# ─── Grabador de la línea ────────────────────────────────────────────────────


class TestGrabadorLinea:
    def test_grabar_abre_el_grabador_siempre_en_manual(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        # Aunque el toggle Auto general esté ACTIVO, el grabador nace manual.
        ai_control.map_recorder.auto_recording_enabled = True
        rec = _open_recorder(ai_control)
        assert rec is not None
        assert rec["type"] == "yield_line"
        assert rec["link_id"] == _LINK_ID
        assert rec["auto_phase"] == "manual"
        texts = _texts(ai_control)
        assert any("+ Anadir punto" in t for t in texts)
        assert any(t == "Terminar" for t in texts)
        assert any(t == "Cancelar" for t in texts)
        assert any(t == "Auto: OFF" for t in texts)  # manual pese al global ON
        # Y la captura automática está congelada de verdad.
        ai_control.map_recorder.update_recording(make_coords(1, 1), 30.0)
        assert rec["nodes"] == []

    def test_grabar_no_pisa_otra_grabacion_activa(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        otra = {"type": "road", "road_id": "X", "nodes": [], "is_new": True}
        ai_control.map_recorder.current_recording = otra
        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_REC)
        assert ai_control.map_recorder.current_recording is otra

    def test_anadir_punto_manual_usa_el_coche_del_usuario(
        self,
        ai_control,
        make_road,
        make_road_link,
        populate_graph,
        make_coords,
        make_player,
        make_telemetry,
    ):
        _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        _user_on_track(ai_control, make_player, make_telemetry, 10.0, 20.0)
        rec = _open_recorder(ai_control)
        ai_control._map_ui_click_elementos(_CID_ANADIR_PUNTO)
        assert len(rec["nodes"]) == 1
        assert rec["nodes"][0].x_m == pytest.approx(10.0, abs=0.1)
        assert rec["nodes"][0].y_m == pytest.approx(20.0, abs=0.1)

    def test_anadir_punto_sin_telemetria_no_anade(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        rec = _open_recorder(ai_control)
        ai_control._map_ui_click_elementos(_CID_ANADIR_PUNTO)
        assert rec["nodes"] == []

    def test_toggle_auto_activa_la_captura_y_vuelve(
        self,
        ai_control,
        make_road,
        make_road_link,
        populate_graph,
        make_coords,
        make_player,
        make_telemetry,
    ):
        mr = ai_control.map_recorder
        _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        _user_on_track(ai_control, make_player, make_telemetry, 0.0, 0.0, plid=5)
        rec = _open_recorder(ai_control)

        ai_control._map_ui_click_elementos(_CID_AUTO)  # ON
        assert rec["auto_phase"] == "recording"
        assert mr.auto_recording_enabled is True
        assert mr.recording_plid == 5  # se fija al coche del usuario
        mr.update_recording(make_coords(1, 1), 30.0)
        assert len(rec["nodes"]) == 1  # ahora sí captura

        ai_control._map_ui_click_elementos(_CID_AUTO)  # OFF
        assert rec["auto_phase"] == "manual"
        mr.update_recording(make_coords(50, 50), 30.0)
        assert len(rec["nodes"]) == 1  # congelado otra vez

    def test_terminar_requiere_dos_puntos(
        self,
        ai_control,
        make_road,
        make_road_link,
        populate_graph,
        make_coords,
    ):
        _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        rec = _open_recorder(ai_control)
        rec["nodes"].append(make_coords(0, -2))
        ai_control._map_ui_click_elementos(_CID_TERMINAR)
        assert rec["auto_phase"] != "ask_t"  # no avanza
        assert ai_control.map_recorder.current_recording is rec

    def test_terminar_pide_t_con_typein(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        rec = _open_recorder(ai_control)
        rec["nodes"] += [make_coords(0, -2), make_coords(0, 2)]
        ai_control.client.sent.clear()
        ai_control._map_ui_click_elementos(_CID_TERMINAR)
        assert rec["auto_phase"] == "ask_t"
        btns = _btns(ai_control)
        assert any(b.ClickID == _TI1 for b in btns)  # TypeIn de T
        assert any(b.Text == "Guardar" for b in btns)
        # En ask_t la captura automática queda congelada.
        ai_control.map_recorder.auto_recording_enabled = True
        ai_control.map_recorder.update_recording(make_coords(9, 9), 30.0)
        assert len(rec["nodes"]) == 2

    def test_guardar_comete_linea_y_t(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        rec = _open_recorder(ai_control)
        rec["nodes"] += [make_coords(0, -2), make_coords(0, 2)]
        ai_control._map_ui_click_elementos(_CID_TERMINAR)
        ai_control._ui_input_buffer[_TI1] = "2.5"
        ai_control._map_ui_click_elementos(_CID_GUARDAR_T)
        assert len(link.yield_line) == 2
        assert link.yield_time_s == 2.5
        assert ai_control.map_recorder.current_recording is None

    def test_guardar_sin_teclear_deja_t_default(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        rec = _open_recorder(ai_control)
        rec["nodes"] += [make_coords(0, -2), make_coords(0, 2)]
        ai_control._map_ui_click_elementos(_CID_TERMINAR)
        ai_control._map_ui_click_elementos(_CID_GUARDAR_T)  # sin escribir nada
        assert len(link.yield_line) == 2
        assert link.yield_time_s is None  # None ⇒ default global
        assert ai_control.map_recorder.current_recording is None

    def test_guardar_t_invalido_no_comete(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        rec = _open_recorder(ai_control)
        rec["nodes"] += [make_coords(0, -2), make_coords(0, 2)]
        ai_control._map_ui_click_elementos(_CID_TERMINAR)
        ai_control._ui_input_buffer[_TI1] = "abc"
        ai_control._map_ui_click_elementos(_CID_GUARDAR_T)
        assert rec["auto_phase"] == "ask_t"  # sigue pidiendo T
        assert ai_control.map_recorder.current_recording is rec
        assert link.yield_line == []

    def test_volver_de_ask_t_conserva_los_puntos(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        rec = _open_recorder(ai_control)
        rec["nodes"] += [make_coords(0, -2), make_coords(0, 2)]
        ai_control._map_ui_click_elementos(_CID_TERMINAR)
        ai_control._map_ui_click_elementos(_CID_VOLVER_T)
        assert rec["auto_phase"] == "manual"
        assert len(rec["nodes"]) == 2

    def test_cancelar_descarta_sin_tocar_el_link(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        rec = _open_recorder(ai_control)
        rec["nodes"] += [make_coords(0, -2), make_coords(0, 2)]
        ai_control._map_ui_click_elementos(_CID_CANCELAR)
        assert ai_control.map_recorder.current_recording is None
        assert link.yield_line == []


# ─── Picker de zonas ─────────────────────────────────────────────────────────


class TestPickerZona:
    def _abrir_picker(
        self, app, make_road, make_road_link, populate_graph, make_coords, **kw
    ):
        link = _setup_link_detail(
            app,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_pts=[(0, -2), (0, 2)],
            zones=("CRUCE", "OTRA"),
            **kw,
        )
        app._map_ui_click_elementos(app._LINK_YIELD_ZONE_VAL)
        return link

    def test_boton_zona_abre_el_picker(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        self._abrir_picker(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        assert ai_control._ui_link_zone_picking is True
        texts = _texts(ai_control)
        assert "CRUCE" in texts and "OTRA" in texts
        assert any(t == "Ninguna" for t in texts)
        assert any(t == "Cancelar" for t in texts)

    def test_elegir_zona_la_asigna_y_cierra(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = self._abrir_picker(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        ai_control._map_ui_click_elementos(_CID_ZONA_ITEM0)  # "CRUCE" (orden alfab.)
        assert link.yield_zone_id == "CRUCE"
        assert ai_control._ui_link_zone_picking is False

    def test_ninguna_limpia_la_zona(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = self._abrir_picker(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_zone="CRUCE",
        )
        ai_control._map_ui_click_elementos(_CID_ZONA_NINGUNA)
        assert link.yield_zone_id is None
        assert ai_control._ui_link_zone_picking is False

    def test_cancelar_no_cambia_nada(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = self._abrir_picker(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_zone="CRUCE",
        )
        ai_control._map_ui_click_elementos(_CID_ZONA_CANCELAR)
        assert link.yield_zone_id == "CRUCE"
        assert ai_control._ui_link_zone_picking is False


# ─── TypeIn de T en el detalle (via on_ISP_BTT) ──────────────────────────────


class TestTypeInTDetalle:
    def _detail_con_linea(
        self, app, make_road, make_road_link, populate_graph, make_coords, yield_t=None
    ):
        link = _setup_link_detail(
            app,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_pts=[(0, -2), (0, 2)],
            yield_t=yield_t,
        )
        app._map_ui_draw_elem_detail(_LINK_ID)  # puebla _ui_detail_field_map
        return link

    def test_btt_fija_t(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = self._detail_con_linea(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        ai_control.on_ISP_BTT(
            ISP_BTT(UCID=3, ClickID=ai_control._LINK_YIELD_T_VAL, Text="5")
        )
        assert link.yield_time_s == 5.0

    def test_btt_default_vuelve_a_none(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = self._detail_con_linea(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_t=3.0,
        )
        ai_control.on_ISP_BTT(
            ISP_BTT(UCID=3, ClickID=ai_control._LINK_YIELD_T_VAL, Text="default")
        )
        assert link.yield_time_s is None

    def test_btt_invalido_no_cambia(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = self._detail_con_linea(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_t=3.0,
        )
        ai_control.on_ISP_BTT(
            ISP_BTT(UCID=3, ClickID=ai_control._LINK_YIELD_T_VAL, Text="abc")
        )
        assert link.yield_time_s == 3.0


# ─── Backend en map_recorder (_cmd_set / _cmd_rec_end) ──────────────────────


class TestRecorderBackend:
    def _mr(self, app, make_road, make_road_link, populate_graph, make_coords, **kw):
        link = _setup_link_detail(
            app, make_road, make_road_link, populate_graph, make_coords, **kw
        )
        return app.map_recorder, link

    def test_cmd_set_yield_time_s_float_y_none(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        mr, link = self._mr(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        mr._cmd_set(_LINK_ID, "yield_time_s", "2.0")
        assert link.yield_time_s == 2.0
        mr._cmd_set(_LINK_ID, "yield_time_s", "none")
        assert link.yield_time_s is None

    def test_cmd_set_yield_time_s_invalido_no_cambia(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        mr, link = self._mr(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_t=3.0,
        )
        mr._cmd_set(_LINK_ID, "yield_time_s", "abc")
        assert link.yield_time_s == 3.0
        mr._cmd_set(_LINK_ID, "yield_time_s", "-1")
        assert link.yield_time_s == 3.0  # T debe ser positivo

    def test_cmd_set_yield_zone_id(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        mr, link = self._mr(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            zones=("CRUCE",),
        )
        mr._cmd_set(_LINK_ID, "yield_zone_id", "CRUCE")
        assert link.yield_zone_id == "CRUCE"
        mr._cmd_set(_LINK_ID, "yield_zone_id", "none")
        assert link.yield_zone_id is None

    def test_cmd_set_yield_line_esta_bloqueado(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        mr, link = self._mr(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_pts=[(0, -2), (0, 2)],
        )
        antes = list(link.yield_line)
        mr._cmd_set(_LINK_ID, "yield_line", "clear")
        assert link.yield_line == antes  # se graba, no se edita a mano

    def test_cmd_rec_end_comete_la_linea(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        mr, link = self._mr(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        mr.current_recording = {
            "type": "yield_line",
            "link_id": _LINK_ID,
            "nodes": [make_coords(0, -2), make_coords(0, 2)],
            "auto_phase": "manual",
        }
        mr._cmd_rec_end()
        assert len(link.yield_line) == 2
        assert mr.current_recording is None

    def test_cmd_rec_end_con_un_punto_descarta(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        mr, link = self._mr(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        mr.current_recording = {
            "type": "yield_line",
            "link_id": _LINK_ID,
            "nodes": [make_coords(0, -2)],
            "auto_phase": "manual",
        }
        mr._cmd_rec_end()
        assert link.yield_line == []
        assert mr.current_recording is None
