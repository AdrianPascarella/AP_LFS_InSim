"""
Tests del editor de REGLAS DE PRIORIDAD de Zonas en la pestaña Elementos
(`map_ui.py`). Antes las `priority_rules` de una `IntersectionZone` solo se
podían fijar por el comando de chat (`!map set <zona> priority_rules add;A,B`);
esto las expone en la UI gráfica (soporte para crear la intersección de W4).

Red primero (MODUS §3), sobre el harness `ai_control` (CapturingClient: los
envíos quedan en `app.client.sent`). Regla `[A, B]`: A tiene prioridad, B cede.
"""

from insims.ai_control.nav_modes.freeroam.graph import IntersectionZone


def _btns(app):
    return [p for p in app.client.sent if type(p).__name__ == "ISP_BTN"]


def _setup_zone_detail(app, make_road, populate_graph, make_coords, rules=None):
    """Deja `app` en el detalle de la zona CRUCE con 3 vías reales en el mapa."""
    populate_graph(
        app.map_recorder,
        roads=[
            make_road("VIA_P", [(0, 0), (0, 50)]),
            make_road("VIA_C", [(0, 0), (50, 0)]),
            make_road("VIA_X", [(0, 0), (0, -50)]),
        ],
    )
    zone = IntersectionZone(zone_id="CRUCE", nodes=[make_coords(0, 0)])
    if rules:
        zone.priority_rules = [list(r) for r in rules]
    app.map_recorder.zones["CRUCE"] = zone
    app.map_recorder.active_map_name = "test"
    app.map_recorder.client = app.client
    app._init_ui_state()
    app._ui_ucid = 3
    app._ui_tab = "elementos"
    app._ui_elem_type = "zone"
    app._ui_elem_detail_id = "CRUCE"
    return zone


class TestZonePriorityEditor:
    def test_detalle_zona_dibuja_editor_prioridad(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        ai_control._map_ui_draw_elem_detail("CRUCE")
        btns = _btns(ai_control)
        texts = [b.Text for b in btns]
        assert any("Prioridad" in t for t in texts)  # título de la sección
        assert any(t == "Anadir" for t in texts)  # botón de alta
        assert any(b.ClickID == ai_control._ZONE_PRIO_ADD for b in btns)

    def test_zona_sin_reglas_muestra_aviso(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        ai_control._map_ui_draw_elem_detail("CRUCE")
        assert any("Sin reglas" in b.Text for b in _btns(ai_control))

    def test_reglas_existentes_se_dibujan_con_quitar(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            rules=[("VIA_P", "VIA_C")],
        )
        ai_control._map_ui_draw_elem_detail("CRUCE")
        texts = [b.Text for b in _btns(ai_control)]
        assert any("VIA_P" in t and "VIA_C" in t for t in texts)  # fila de la regla
        assert any(t == "Quitar" for t in texts)
        assert ("VIA_P", "VIA_C") in ai_control._ui_zone_prio_map.values()

    def test_anadir_regla_valida(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        zone = _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        ai_control._ui_input_buffer[ai_control._ZONE_PRIO_TI_A] = "VIA_P"
        ai_control._ui_input_buffer[ai_control._ZONE_PRIO_TI_B] = "VIA_C"
        ai_control._map_ui_click_elementos(ai_control._ZONE_PRIO_ADD)
        assert ["VIA_P", "VIA_C"] in zone.priority_rules

    def test_anadir_rechaza_via_inexistente(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        zone = _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        ai_control._ui_input_buffer[ai_control._ZONE_PRIO_TI_A] = "VIA_P"
        ai_control._ui_input_buffer[ai_control._ZONE_PRIO_TI_B] = "NOPE"
        ai_control._map_ui_click_elementos(ai_control._ZONE_PRIO_ADD)
        assert zone.priority_rules == []

    def test_anadir_rechaza_ids_iguales(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        zone = _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        ai_control._ui_input_buffer[ai_control._ZONE_PRIO_TI_A] = "VIA_P"
        ai_control._ui_input_buffer[ai_control._ZONE_PRIO_TI_B] = "VIA_P"
        ai_control._map_ui_click_elementos(ai_control._ZONE_PRIO_ADD)
        assert zone.priority_rules == []

    def test_quitar_regla(self, ai_control, make_road, populate_graph, make_coords):
        zone = _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            rules=[("VIA_P", "VIA_C"), ("VIA_X", "VIA_C")],
        )
        ai_control._map_ui_draw_elem_detail("CRUCE")  # popula _ui_zone_prio_map
        del_cid = next(
            cid
            for cid, pair in ai_control._ui_zone_prio_map.items()
            if pair == ("VIA_P", "VIA_C")
        )
        ai_control._map_ui_click_elementos(del_cid)
        assert ["VIA_P", "VIA_C"] not in zone.priority_rules
        assert ["VIA_X", "VIA_C"] in zone.priority_rules  # la otra se conserva
