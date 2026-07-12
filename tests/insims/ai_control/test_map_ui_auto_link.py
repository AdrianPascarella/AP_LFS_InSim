"""
Herramienta "Link auto" de la pestaña Grabar de map_ui.

Caracteriza el flujo pedido por el usuario para mapear cómodo RoadLinks: un botón
que graba un enlace SIN teclear origen ni destino. El ORIGEN se captura de la
posición del coche al iniciar y el DESTINO al finalizar (ambos por la vía más
cercana al coche que se graba, recording_plid). Al finalizar:

  - si origen->destino ya existe → pantalla de CONFLICTO (sufijo+recomprobar /
    sobrescribir / cancelar),
  - si no existe → pantalla de CONFIRMACIÓN (Aprobar / Cancelar).

Se ejercita sobre la AIControl real del harness (client que captura los envíos) y
un MapRecorder real poblado con get_location_context() de verdad.
"""

from __future__ import annotations

# ClickIDs de la UI (ver map_ui.py).
_CID_LINK_AUTO = 118  # botón idle "Link auto"
_CID_ROADLINK = 111  # botón idle "RoadLink" (el auto va justo debajo)
_CID_FINALIZAR = 114  # Finalizar (recording) / Aprobar (confirm)
_CID_CANCELAR = 115  # Cancelar (recording / confirm)
_CID_RECOMPROBAR = 116  # Recomprobar con sufijo (conflict)
_CID_SOBRESCRIBIR = 118  # Sobrescribir (conflict)
_CID_CANCELAR_CONFLICT = 117  # Cancelar (conflict)


def _btns(app):
    return [p for p in app.client.sent if type(p).__name__ == "ISP_BTN"]


def _open_grabar(app, ucid=3):
    """Menú abierto por `ucid` en la pestaña Grabar, con mapa activo."""
    app.map_recorder.active_map_name = "test"
    # map_recorder.send (usado por _cmd_rec_end/_cancel/_auto) → cliente que captura.
    app.map_recorder.client = app.client
    app._init_ui_state()
    app._ui_ucid = ucid
    app._ui_tab = "grabar"


def _place_car(app, make_player, make_telemetry, x_m, y_m, plid=5, ucid=3):
    """Coloca (o mueve) el coche a grabar en (x_m, y_m) y lo marca como recording."""
    tele = make_telemetry(x_m=x_m, y_m=y_m)
    app.user_manager.players[plid] = make_player(plid=plid, ucid=ucid, telemetry=tele)
    app.map_recorder.recording_plid = plid


def _setup_roads(app, make_road, populate_graph):
    """Dos vías separadas: A cerca de (0,0), F cerca de (100,0)."""
    populate_graph(
        app.map_recorder,
        roads=[
            make_road("A", [(-5, 0), (5, 0)]),
            make_road("F", [(95, 0), (105, 0)]),
        ],
    )


def _reach_recording_on_dest(
    app,
    make_player,
    make_telemetry,
    make_road,
    populate_graph,
    with_conflict=False,
    make_road_link=None,
):
    """Deja la app grabando un Link auto con origen A y el coche ya sobre F
    (listo para Finalizar). Si with_conflict, pre-crea el enlace A->F."""
    _open_grabar(app)
    _setup_roads(app, make_road, populate_graph)
    _place_car(app, make_player, make_telemetry, 0.0, 0.0)  # sobre A
    app._map_ui_click_grabar(_CID_LINK_AUTO)  # inicia → captura origen A
    _place_car(app, make_player, make_telemetry, 100.0, 0.0)  # se mueve a F
    if with_conflict:
        app.map_recorder.road_links["A->F"] = make_road_link(
            "A", "F", [(0, 0), (100, 0)]
        )
    return app


# ─── Botón e inicio ──────────────────────────────────────────────────────────


def test_idle_dibuja_boton_link_auto_bajo_roadlink(ai_control):
    app = ai_control
    _open_grabar(app)
    app.client.sent.clear()

    app._map_ui_redraw_content()

    btns = _btns(app)
    auto = [p for p in btns if p.ClickID == _CID_LINK_AUTO]
    assert auto, "el panel Grabar debe mostrar el botón 'Link auto'"
    assert auto[0].Text == "Link auto"
    # Justo debajo del botón RoadLink: misma columna, una fila más abajo.
    rl = next(p for p in btns if p.ClickID == _CID_ROADLINK)
    assert auto[0].L == rl.L and auto[0].T > rl.T


def test_link_auto_sin_plid_no_inicia(ai_control, make_road, populate_graph):
    app = ai_control
    _open_grabar(app)
    _setup_roads(app, make_road, populate_graph)
    app.map_recorder.recording_plid = None

    app._map_ui_click_grabar(_CID_LINK_AUTO)

    assert app.map_recorder.current_recording is None


def test_link_auto_captura_origen_de_la_posicion(
    ai_control, make_player, make_telemetry, make_road, populate_graph
):
    app = ai_control
    _open_grabar(app)
    _setup_roads(app, make_road, populate_graph)
    _place_car(app, make_player, make_telemetry, 0.0, 0.0)  # sobre A

    app._map_ui_click_grabar(_CID_LINK_AUTO)

    rec = app.map_recorder.current_recording
    assert rec is not None
    assert rec["auto"] is True
    assert rec["auto_phase"] == "recording"
    assert rec["origin_id"] == "A"
    assert rec["dest_id"] is None
    assert app.map_recorder.auto_recording_enabled is True
    assert len(rec["nodes"]) == 1  # se siembra el nodo de origen


def test_link_auto_sin_vias_error(ai_control, make_player, make_telemetry):
    app = ai_control
    _open_grabar(app)
    _place_car(app, make_player, make_telemetry, 0.0, 0.0)  # coche ok, pero sin roads

    app._map_ui_click_grabar(_CID_LINK_AUTO)

    assert app.map_recorder.current_recording is None


# ─── Finalizar sin conflicto → confirmación ──────────────────────────────────


def test_finalizar_sin_conflicto_va_a_confirm(
    ai_control, make_player, make_telemetry, make_road, populate_graph, make_coords
):
    app = _reach_recording_on_dest(
        ai_control, make_player, make_telemetry, make_road, populate_graph
    )

    app._map_ui_click_grabar(_CID_FINALIZAR)  # Finalizar → detecta destino F

    rec = app.map_recorder.current_recording
    assert rec["auto_phase"] == "confirm"
    assert rec["dest_id"] == "F"
    assert rec["pending_link_id"] == "A->F"
    # La preferencia Auto NO se apaga (es "pegajosa"); la captura se congela por
    # fase: un update_recording durante la confirmación no añade nodos.
    assert app.map_recorder.auto_recording_enabled is True
    n_before = len(rec["nodes"])
    app.map_recorder.update_recording(make_coords(500.0, 0.0), 30.0)
    assert len(rec["nodes"]) == n_before
    # La pantalla de confirmación ofrece Aprobar y Cancelar.
    textos = {p.Text for p in _btns(app)}
    assert "Aprobar" in textos and "Cancelar" in textos


def test_confirm_aprobar_crea_el_roadlink(
    ai_control, make_player, make_telemetry, make_road, populate_graph
):
    app = _reach_recording_on_dest(
        ai_control, make_player, make_telemetry, make_road, populate_graph
    )
    app._map_ui_click_grabar(_CID_FINALIZAR)  # → confirm

    app._map_ui_click_grabar(_CID_FINALIZAR)  # Aprobar

    assert app.map_recorder.current_recording is None
    assert "A->F" in app.map_recorder.road_links
    link = app.map_recorder.road_links["A->F"]
    assert link.from_road_id == "A" and link.to_road_id == "F"


def test_confirm_cancelar_no_crea_nada(
    ai_control, make_player, make_telemetry, make_road, populate_graph
):
    app = _reach_recording_on_dest(
        ai_control, make_player, make_telemetry, make_road, populate_graph
    )
    app._map_ui_click_grabar(_CID_FINALIZAR)  # → confirm

    app._map_ui_click_grabar(_CID_CANCELAR)  # Cancelar

    assert app.map_recorder.current_recording is None
    assert "A->F" not in app.map_recorder.road_links


# ─── Finalizar con conflicto → pantalla de conflicto ─────────────────────────


def test_finalizar_con_conflicto_va_a_conflict(
    ai_control, make_player, make_telemetry, make_road, populate_graph, make_road_link
):
    app = _reach_recording_on_dest(
        ai_control,
        make_player,
        make_telemetry,
        make_road,
        populate_graph,
        with_conflict=True,
        make_road_link=make_road_link,
    )

    app._map_ui_click_grabar(_CID_FINALIZAR)  # Finalizar → A->F ya existe

    rec = app.map_recorder.current_recording
    assert rec["auto_phase"] == "conflict"
    assert rec["pending_link_id"] == "A->F"
    # La pantalla ofrece las 3 opciones + campos de sufijo.
    btns = _btns(app)
    cids = {p.ClickID for p in btns}
    assert _CID_RECOMPROBAR in cids  # opción 1
    assert _CID_SOBRESCRIBIR in cids  # opción 2
    assert _CID_CANCELAR_CONFLICT in cids  # opción 3
    assert app._UI_CID_TI1 in cids and app._UI_CID_TI2 in cids  # sufijos


def test_conflicto_sufijo_recomprobar_libera_el_nombre(
    ai_control, make_player, make_telemetry, make_road, populate_graph, make_road_link
):
    app = _reach_recording_on_dest(
        ai_control,
        make_player,
        make_telemetry,
        make_road,
        populate_graph,
        with_conflict=True,
        make_road_link=make_road_link,
    )
    app._map_ui_click_grabar(_CID_FINALIZAR)  # → conflict (A->F)

    # Sufijo "b" al destino → A->Fb (libre) → confirmación.
    app._ui_input_buffer[app._UI_CID_TI1] = ""
    app._ui_input_buffer[app._UI_CID_TI2] = "b"
    app._map_ui_click_grabar(_CID_RECOMPROBAR)

    rec = app.map_recorder.current_recording
    assert rec["auto_phase"] == "confirm"
    assert rec["pending_link_id"] == "A->Fb"

    app._map_ui_click_grabar(_CID_FINALIZAR)  # Aprobar
    assert "A->Fb" in app.map_recorder.road_links
    assert "A->F" in app.map_recorder.road_links  # el original sigue intacto


def test_conflicto_recomprobar_sin_sufijo_sigue_en_conflicto(
    ai_control, make_player, make_telemetry, make_road, populate_graph, make_road_link
):
    app = _reach_recording_on_dest(
        ai_control,
        make_player,
        make_telemetry,
        make_road,
        populate_graph,
        with_conflict=True,
        make_road_link=make_road_link,
    )
    app._map_ui_click_grabar(_CID_FINALIZAR)  # → conflict

    app._ui_input_buffer[app._UI_CID_TI1] = ""
    app._ui_input_buffer[app._UI_CID_TI2] = ""
    app._map_ui_click_grabar(_CID_RECOMPROBAR)  # mismo nombre → sigue en conflicto

    assert app.map_recorder.current_recording["auto_phase"] == "conflict"


def test_conflicto_sobrescribir_reemplaza_los_nodos(
    ai_control, make_player, make_telemetry, make_road, populate_graph, make_road_link
):
    app = _reach_recording_on_dest(
        ai_control,
        make_player,
        make_telemetry,
        make_road,
        populate_graph,
        with_conflict=True,
        make_road_link=make_road_link,
    )
    existing = app.map_recorder.road_links["A->F"]
    app._map_ui_click_grabar(_CID_FINALIZAR)  # → conflict

    app._map_ui_click_grabar(_CID_SOBRESCRIBIR)  # Opción 2: sobrescribir

    assert app.map_recorder.current_recording is None
    # Mismo objeto RoadLink, pero con los nodos de esta grabación (origen+destino).
    assert app.map_recorder.road_links["A->F"] is existing
    assert len(existing.nodes) == 2


def test_conflicto_cancelar_deja_el_link_intacto(
    ai_control, make_player, make_telemetry, make_road, populate_graph, make_road_link
):
    app = _reach_recording_on_dest(
        ai_control,
        make_player,
        make_telemetry,
        make_road,
        populate_graph,
        with_conflict=True,
        make_road_link=make_road_link,
    )
    original = app.map_recorder.road_links["A->F"]
    app._map_ui_click_grabar(_CID_FINALIZAR)  # → conflict

    app._map_ui_click_grabar(_CID_CANCELAR_CONFLICT)  # Opción 3: cancelar

    assert app.map_recorder.current_recording is None
    assert app.map_recorder.road_links["A->F"] is original  # sin tocar


# ─── Persistencia del flujo al cerrar/reabrir el menú ────────────────────────


def test_flujo_sobrevive_al_cambiar_de_pestana(
    ai_control, make_player, make_telemetry, make_road, populate_graph
):
    app = _reach_recording_on_dest(
        ai_control, make_player, make_telemetry, make_road, populate_graph
    )
    app._map_ui_click_grabar(_CID_FINALIZAR)  # → confirm

    # Cambiar a Info y volver a Grabar no pierde el estado (vive en el recorder).
    app._map_ui_handle_click(app._UI_CID_TAB_INFO)
    app._map_ui_handle_click(app._UI_CID_TAB_GRAB)

    assert app.map_recorder.current_recording["auto_phase"] == "confirm"
    textos = {p.Text for p in _btns(app)}
    assert "Aprobar" in textos
