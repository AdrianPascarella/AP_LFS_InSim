"""
UI de mapeo de la CESIÓN de un RoadLink (Fase 8, bloque 8.6.5) en `map_ui.py`.

Rediseño S44, mecanismo del que **hace la maniobra**. En el detalle del link
(pestaña Elementos) la sección "Cesion" ya no gestiona una polilínea grabada ni
una zona a vigilar —los dos murieron con el rediseño— sino:

  - un **toggle** `NONE|YIELD|STOP` (vocabulario único de la cesión);
  - **[+ Marcar punto]**: UN solo punto, el del coche del que clica (se acabó el
    grabador por fases del 8.4: el punto implica la línea, que se deriva
    perpendicular a la tangente);
  - **[Auto]**: coloca el punto retrocediendo `yield_auto_setback_m` desde el
    primer punto de conflicto real (reusa la detección de "qué roads piso");
  - **[Borrar]** el punto;
  - **T** con el float efectivo + **[Usar default]**.

Invariante del modelo (`graph.py::has_yield`): hace falta **tipo Y punto**. Un
toggle en YIELD sin punto está a medias y NO cede — la UI tiene que decirlo.

Red primero (MODUS §3) sobre el harness `ai_control`.
"""

from __future__ import annotations

from insims.ai_control.nav_modes.freeroam.enums import YieldType
from insims.users_management.um_class import User

_LINK_ID = "R1->R2"
_TI1 = 130


def _btns(app):
    return [p for p in app.client.sent if type(p).__name__ == "ISP_BTN"]


def _texts(app):
    return [b.Text for b in _btns(app)]


def _btn(app, cid):
    """El último BTN dibujado con ese ClickID (el redibujado pisa al anterior)."""
    match = [b for b in _btns(app) if b.ClickID == cid]
    return match[-1] if match else None


def _setup_link_detail(
    app,
    make_road,
    make_road_link,
    populate_graph,
    make_coords,
    *,
    yield_type=YieldType.NONE,
    yield_point=None,
    yield_t=None,
):
    """Deja `app` en el detalle del RoadLink R1->R2 (pestaña Elementos).

    Geometría: R1 llega por el eje X y R2 sube en +Y; el link va de (0,0) a
    (0,20) y en el camino CRUZA R3, una road horizontal por y=10. Ese cruce
    en (0, 10) es el "primer cruce real" que tiene que encontrar [Auto].
    """
    populate_graph(
        app.map_recorder,
        roads=[
            make_road("R1", [(-50, 0), (0, 0)]),
            make_road("R2", [(0, 0), (0, 50)]),
            make_road("R3", [(-20, 10), (20, 10)]),
        ],
        road_links=[make_road_link("R1", "R2", [(0, 0), (0, 20)])],
    )
    link = app.map_recorder.road_links[_LINK_ID]
    link.yield_type = yield_type
    link.yield_point = make_coords(*yield_point) if yield_point else None
    link.yield_time_s = yield_t
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


# ─── Sección "Cesion" del detalle ────────────────────────────────────────────


class TestSeccionCesionDetalle:
    def test_link_sin_cesion_muestra_el_toggle_en_none(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        assert any("Cesion" in t for t in _texts(ai_control))  # título
        toggle = _btn(ai_control, ai_control._LINK_YIELD_TYPE)
        assert toggle is not None
        assert "NONE" in toggle.Text
        # Sin cesión no se pide ni punto ni T: el giro no cede y punto.
        assert _btn(ai_control, ai_control._LINK_YIELD_T_VAL) is None
        assert _btn(ai_control, ai_control._LINK_YIELD_MARK) is None

    def test_yield_sin_punto_avisa_de_que_no_cede(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        """`has_yield` exige tipo Y punto: la UI no puede callarse que está a medias."""
        _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        assert _btn(ai_control, ai_control._LINK_YIELD_MARK) is not None
        assert _btn(ai_control, ai_control._LINK_YIELD_AUTO) is not None
        estado = _btn(ai_control, ai_control._LINK_YIELD_STATUS)
        assert "NO cede" in estado.Text or "Sin punto" in estado.Text

    def test_yield_con_punto_muestra_punto_t_y_borrar(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
            yield_point=(0, 5),
            yield_t=3.0,
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        assert _btn(ai_control, ai_control._LINK_YIELD_CLEAR) is not None
        assert "3.0" in _btn(ai_control, ai_control._LINK_YIELD_T_VAL).Text

    def test_t_sin_valor_muestra_el_float_efectivo_no_un_none(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        """Feedback de U8: el default se enseña como número, no como 'None'."""
        _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.STOP,
            yield_point=(0, 5),
            yield_t=None,
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        t_btn = _btn(ai_control, ai_control._LINK_YIELD_T_VAL)
        default = ai_control._map_ui_yield_default_t()
        assert f"{default:g}" in t_btn.Text
        assert "None" not in t_btn.Text
        # Con T por defecto no se ofrece "Usar default": ya lo está.
        assert _btn(ai_control, ai_control._LINK_YIELD_T_DEF) is None

    def test_t_propio_ofrece_volver_al_default(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
            yield_point=(0, 5),
            yield_t=7.5,
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        assert _btn(ai_control, ai_control._LINK_YIELD_T_DEF) is not None


class TestToggleTipo:
    def test_el_toggle_cicla_none_yield_stop_none(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_TYPE)
        assert link.yield_type is YieldType.YIELD
        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_TYPE)
        assert link.yield_type is YieldType.STOP
        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_TYPE)
        assert link.yield_type is YieldType.NONE

    def test_pasar_a_none_no_borra_el_punto(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        """Apagar la cesión no tira el trabajo: el punto sigue ahí si vuelves."""
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.STOP,
            yield_point=(0, 5),
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_TYPE)  # STOP -> NONE

        assert link.yield_type is YieldType.NONE
        assert link.yield_point is not None
        assert link.has_yield is False  # NONE no cede, tenga punto o no


class TestMarcarPunto:
    def test_marcar_punto_usa_el_coche_del_que_clica(
        self,
        ai_control,
        make_road,
        make_road_link,
        populate_graph,
        make_coords,
        make_player,
        make_telemetry,
    ):
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
        )
        _user_on_track(ai_control, make_player, make_telemetry, 0.0, 4.0)
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_MARK)

        assert link.yield_point is not None
        assert round(link.yield_point.y_m, 1) == 4.0
        assert link.has_yield is True  # tipo + punto ⇒ ya cede

    def test_marcar_punto_sin_coche_avisa_y_no_toca_el_link(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_MARK)

        assert link.yield_point is None
        assert any(
            "telemetria" in str(getattr(p, "Msg", "")) for p in ai_control.client.sent
        )

    def test_remarcar_pisa_el_punto_anterior(
        self,
        ai_control,
        make_road,
        make_road_link,
        populate_graph,
        make_coords,
        make_player,
        make_telemetry,
    ):
        """Es UN punto, no una lista: marcar otra vez lo mueve."""
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
            yield_point=(0, 2),
        )
        _user_on_track(ai_control, make_player, make_telemetry, 0.0, 8.0)
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_MARK)

        assert round(link.yield_point.y_m, 1) == 8.0

    def test_borrar_quita_el_punto_pero_respeta_el_tipo(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
            yield_point=(0, 5),
            yield_t=3.0,
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_CLEAR)

        assert link.yield_point is None
        assert link.yield_type is YieldType.YIELD  # el toggle no se toca
        assert link.has_yield is False


class TestAutoPunto:
    def test_auto_coloca_el_punto_antes_del_primer_cruce(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        """R3 cruza el link en (0, 10): el punto va `setback` metros antes."""
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_AUTO)

        assert link.yield_point is not None
        setback = ai_control._map_ui_yield_setback()
        assert round(link.yield_point.y_m, 1) == round(10.0 - setback, 1)
        assert round(link.yield_point.x_m, 1) == 0.0

    def test_auto_no_necesita_coche_en_pista(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        """Es geometría pura: no lee telemetría (a diferencia de Marcar punto)."""
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_AUTO)

        assert link.yield_point is not None

    def test_auto_sin_cruces_usa_el_punto_de_union(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        """Un link que no pisa ninguna road sigue teniendo dónde ceder: la
        INCORPORACIÓN. El punto de unión con la `to_road` es un punto de
        conflicto más (decisión S45), así que [Auto] para antes de mezclarse.
        """
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", [(-50, 0), (0, 0)]),
                make_road("R2", [(-20, 20), (20, 20)]),  # se incorpora en (0, 20)
            ],
            road_links=[make_road_link("R1", "R2", [(0, 0), (0, 20)])],
        )
        link = ai_control.map_recorder.road_links[_LINK_ID]
        link.yield_type = YieldType.YIELD
        ai_control.map_recorder.active_map_name = "test"
        ai_control.map_recorder.client = ai_control.client
        ai_control._init_ui_state()
        ai_control._ui_ucid = 3
        ai_control._ui_tab = "elementos"
        ai_control._ui_elem_detail_id = _LINK_ID
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_AUTO)

        setback = ai_control._map_ui_yield_setback()
        assert round(link.yield_point.y_m, 1) == round(20.0 - setback, 1)

    def test_auto_sin_destino_avisa_y_no_inventa_punto(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        """Link colgado (su `to_road` no existe): no hay ni cruce ni unión."""
        populate_graph(
            ai_control.map_recorder,
            roads=[make_road("R1", [(-50, 0), (0, 0)])],  # R2 no existe
            road_links=[make_road_link("R1", "R2", [(0, 0), (0, 20)])],
        )
        link = ai_control.map_recorder.road_links[_LINK_ID]
        link.yield_type = YieldType.YIELD
        ai_control.map_recorder.active_map_name = "test"
        ai_control.map_recorder.client = ai_control.client
        ai_control._init_ui_state()
        ai_control._ui_ucid = 3
        ai_control._ui_tab = "elementos"
        ai_control._ui_elem_detail_id = _LINK_ID
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_AUTO)

        assert link.yield_point is None
        assert any(
            "cruce" in str(getattr(p, "Msg", "")).lower()
            for p in ai_control.client.sent
        )

    def test_auto_ignora_la_from_road(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        """De la vía que dejas atrás no se cede (decisión S45): R1 no cuenta,
        aunque el link nazca sobre ella. El primer cruce es R3, en (0, 10)."""
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_AUTO)

        setback = ai_control._map_ui_yield_setback()
        assert round(link.yield_point.y_m, 1) == round(10.0 - setback, 1)


class TestTiempoT:
    def test_guardar_t_valido(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
            yield_point=(0, 5),
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._ui_input_buffer[ai_control._LINK_YIELD_T_VAL] = "2.5"
        ai_control._map_ui_yield_apply_t(ai_control._LINK_YIELD_T_VAL)

        assert link.yield_time_s == 2.5

    def test_t_invalido_no_comete(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
            yield_point=(0, 5),
            yield_t=3.0,
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        for basura in ("-1", "0", "hola"):
            ai_control._ui_input_buffer[ai_control._LINK_YIELD_T_VAL] = basura
            ai_control._map_ui_yield_apply_t(ai_control._LINK_YIELD_T_VAL)
            assert link.yield_time_s == 3.0  # intacto

    def test_usar_default_devuelve_t_a_none(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
            yield_point=(0, 5),
            yield_t=9.0,
        )
        ai_control._map_ui_draw_elem_detail(_LINK_ID)

        ai_control._map_ui_click_elementos(ai_control._LINK_YIELD_T_DEF)

        assert link.yield_time_s is None  # None ⇒ default global de config


class TestRecorderBackend:
    """Lo que la UI delega en `map_recorder` (`_cmd_set`), por el camino real."""

    def test_set_yield_type_acepta_el_vocabulario(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        mr = ai_control.map_recorder

        mr._cmd_set(_LINK_ID, "yield_type", "stop")
        assert link.yield_type is YieldType.STOP
        mr._cmd_set(_LINK_ID, "yield_type", "YIELD")
        assert link.yield_type is YieldType.YIELD

    def test_set_yield_type_rechaza_lo_que_no_es_del_vocabulario(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        ai_control.map_recorder._cmd_set(_LINK_ID, "yield_type", "CEDA")

        assert link.yield_type is YieldType.NONE  # intacto

    def test_el_punto_no_se_edita_a_mano(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        link = _setup_link_detail(
            ai_control, make_road, make_road_link, populate_graph, make_coords
        )
        ai_control.map_recorder._cmd_set(_LINK_ID, "yield_point", "0,5")

        assert link.yield_point is None

    def test_check_avisa_del_tipo_sin_punto(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.YIELD,
        )
        _errores, advertencias = ai_control.map_recorder.collect_check_results()

        assert any("NO cede" in a for a in advertencias)

    def test_check_avisa_del_punto_huerfano(
        self, ai_control, make_road, make_road_link, populate_graph, make_coords
    ):
        _setup_link_detail(
            ai_control,
            make_road,
            make_road_link,
            populate_graph,
            make_coords,
            yield_type=YieldType.NONE,
            yield_point=(0, 5),
        )
        _errores, advertencias = ai_control.map_recorder.collect_check_results()

        assert any("se ignora" in a for a in advertencias)
