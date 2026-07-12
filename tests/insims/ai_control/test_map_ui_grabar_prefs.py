"""
Preferencias de grabado en la pestaña Grabar de map_ui + "Auto" pegajoso.

Caracteriza tres ajustes pedidos por el usuario (S32):
  1. El toggle "Trafico: LHT/RHT" (norma por defecto de las nuevas vías) se movió
     de la pestaña Mapa a la pestaña Grabar (CID 108).
  2. Nuevo campo "Vel. grabar (km/h)" (CID 129) en Grabar que fija la velocidad por
     defecto de las nuevas vías; se aplica al crear un road.
  3. "Auto" (captura de nodos) es una preferencia PEGAJOSA: cancelar o terminar una
     grabación ya NO la apaga.
"""

from __future__ import annotations

from types import SimpleNamespace

from insims.ai_control.nav_modes.freeroam.enums import TrafficRule

_CID_TRAFICO = 108
_CID_VEL_TYPEIN = 129


def _btns(app):
    return [p for p in app.client.sent if type(p).__name__ == "ISP_BTN"]


def _open_grabar(app, ucid=3):
    app.map_recorder.active_map_name = "test"
    app.map_recorder.client = app.client
    app._init_ui_state()
    app._ui_ucid = ucid
    app._ui_tab = "grabar"


# ─── #1 · Trafico movido a Grabar ────────────────────────────────────────────


def test_grabar_dibuja_toggle_trafico(ai_control):
    app = ai_control
    _open_grabar(app)
    app.client.sent.clear()

    app._map_ui_redraw_content()

    traf = [p for p in _btns(app) if p.ClickID == _CID_TRAFICO]
    assert traf, "la pestaña Grabar debe mostrar el toggle de Trafico"
    assert "Trafico" in traf[0].Text


def test_mapa_ya_no_dibuja_trafico(ai_control):
    app = ai_control
    _open_grabar(app)
    app._ui_tab = "mapa"
    app.client.sent.clear()

    app._map_ui_redraw_content()

    assert not [p for p in _btns(app) if "Trafico" in (p.Text or "")]


def test_click_trafico_alterna_la_norma(ai_control):
    app = ai_control
    _open_grabar(app)
    app.map_recorder.default_traffic_rule = TrafficRule.LHT

    app._map_ui_click_grabar(_CID_TRAFICO)
    assert app.map_recorder.default_traffic_rule == TrafficRule.RHT

    app._map_ui_click_grabar(_CID_TRAFICO)
    assert app.map_recorder.default_traffic_rule == TrafficRule.LHT


def test_click_trafico_no_exige_plid(ai_control):
    # Es una preferencia global: no requiere jugador seleccionado (a diferencia de
    # los botones de iniciar grabación).
    app = ai_control
    _open_grabar(app)
    app.map_recorder.recording_plid = None
    app.map_recorder.default_traffic_rule = TrafficRule.LHT

    app._map_ui_click_grabar(_CID_TRAFICO)

    assert app.map_recorder.default_traffic_rule == TrafficRule.RHT


# ─── #2 · Velocidad por defecto de grabado ───────────────────────────────────


def test_grabar_dibuja_campo_velocidad(ai_control):
    app = ai_control
    _open_grabar(app)
    app.map_recorder.default_speed_limit_kmh = 30.0
    app.client.sent.clear()

    app._map_ui_redraw_content()

    vel = [p for p in _btns(app) if p.ClickID == _CID_VEL_TYPEIN]
    assert vel, "la pestaña Grabar debe mostrar el campo de velocidad por defecto"
    assert "30" in vel[0].Text


def test_typein_velocidad_fija_el_default(ai_control):
    app = ai_control
    _open_grabar(app)

    app.on_ISP_BTT(SimpleNamespace(UCID=3, Text="55", ClickID=_CID_VEL_TYPEIN))

    assert app.map_recorder.default_speed_limit_kmh == 55.0


def test_typein_velocidad_invalida_no_cambia_el_default(ai_control):
    app = ai_control
    _open_grabar(app)
    app.map_recorder.default_speed_limit_kmh = 40.0

    app.on_ISP_BTT(SimpleNamespace(UCID=3, Text="abc", ClickID=_CID_VEL_TYPEIN))
    assert app.map_recorder.default_speed_limit_kmh == 40.0

    app.on_ISP_BTT(SimpleNamespace(UCID=3, Text="-5", ClickID=_CID_VEL_TYPEIN))
    assert app.map_recorder.default_speed_limit_kmh == 40.0


def test_road_grabado_usa_la_velocidad_default(ai_control, make_coords):
    app = ai_control
    _open_grabar(app)
    app.map_recorder.default_speed_limit_kmh = 70.0
    app.map_recorder.current_recording = {
        "type": "road",
        "road_id": "R1",
        "nodes": [make_coords(0.0, 0.0), make_coords(10.0, 0.0)],
        "is_new": True,
    }

    app.map_recorder._cmd_rec_end()

    assert "R1" in app.map_recorder.roads
    assert app.map_recorder.roads["R1"].speed_limit_kmh == 70.0


# ─── #3 · "Auto" pegajoso ────────────────────────────────────────────────────


def test_cancelar_no_apaga_auto(ai_control, make_coords):
    app = ai_control
    _open_grabar(app)
    app.map_recorder.auto_recording_enabled = True
    app.map_recorder.current_recording = {
        "type": "road",
        "road_id": "R1",
        "nodes": [make_coords(0.0, 0.0)],
        "is_new": True,
    }

    app.map_recorder._cmd_rec_cancel()

    assert app.map_recorder.current_recording is None
    assert app.map_recorder.auto_recording_enabled is True


def test_terminar_sin_nodos_no_apaga_auto(ai_control):
    app = ai_control
    _open_grabar(app)
    app.map_recorder.auto_recording_enabled = True
    app.map_recorder.current_recording = {
        "type": "road",
        "road_id": "R2",
        "nodes": [],
        "is_new": True,
    }

    app.map_recorder._cmd_rec_end()

    assert app.map_recorder.current_recording is None
    assert app.map_recorder.auto_recording_enabled is True
