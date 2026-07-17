"""
UI de mapeo de la ZONA de intersección (Fase 8, bloque 8.6.5) en `map_ui.py`.

Rediseño S44, mecanismo del que **cruza de RECTO**: varias vías que se cortan
físicamente sin que medie ningún link — si todos siguen rectos, chocan en mitad
del cruce. Es lo ÚNICO que resuelve la zona, y es ortogonal al link: no se
refieren jamás el uno al otro (`yield_zone_id` murió).

El detalle de una zona (pestaña Elementos) ya no edita `radius_m` ni la matriz
de pares `priority_rules` —los dos murieron— sino:

  - el **polígono** (≥3 puntos, sin máximo): su contorno ES el borde donde se
    para. Se graba con el grabador normal (`type="zone"`), el de la pestaña
    Grabar;
  - **T** con el float efectivo + **[Usar default]**;
  - la **tabla de vías** auto-poblada: un toggle `NONE|YIELD|STOP` por road y
    una **[X]** para borrar los falsos cruces.

Política de la tabla (decidida con el usuario en S46): se auto-puebla SOLO al
grabar el polígono y con **[Re-detectar]**. Entre medias lo que se borre a mano
se queda borrado — si no, "auto-poblada" y "borrable" se contradicen.

Red primero (MODUS §3) sobre el harness `ai_control`.
"""

from __future__ import annotations

from insims.ai_control.nav_modes.freeroam.enums import YieldType
from insims.ai_control.nav_modes.freeroam.graph import IntersectionZone
from insims.users_management.um_class import User

_ZONE_ID = "CRUCE"


class _FakePkt:
    """ISP_MSO mínimo: los comandos del recorder solo miran el UCID."""

    def __init__(self, ucid: int):
        self.UCID = ucid


def _btns(app):
    return [p for p in app.client.sent if type(p).__name__ == "ISP_BTN"]


def _texts(app):
    return [b.Text for b in _btns(app)]


def _btn(app, cid):
    """El último BTN dibujado con ese ClickID (el redibujado pisa al anterior)."""
    match = [b for b in _btns(app) if b.ClickID == cid]
    return match[-1] if match else None


def _cuadrado(make_coords, lado=10.0):
    """Polígono cuadrado centrado en el origen."""
    h = lado / 2.0
    return [
        make_coords(-h, -h),
        make_coords(h, -h),
        make_coords(h, h),
        make_coords(-h, h),
    ]


def _setup_zone_detail(
    app,
    make_road,
    populate_graph,
    make_coords,
    *,
    nodes=None,
    roads_tabla=None,
    yield_t=None,
):
    """Deja `app` en el detalle de la zona CRUCE (pestaña Elementos).

    Geometría: dos roads que se cortan en el origen SIN ningún link de por
    medio (el caso que solo la zona resuelve) y una tercera lejos.
    """
    populate_graph(
        app.map_recorder,
        roads=[
            make_road("H", [(-30, 0), (30, 0)]),  # horizontal, pisa la zona
            make_road("V", [(0, -30), (0, 30)]),  # vertical, pisa la zona
            make_road("LEJOS", [(200, 200), (200, 250)]),  # no la pisa
        ],
    )
    zona = IntersectionZone(
        zone_id=_ZONE_ID,
        nodes=_cuadrado(make_coords) if nodes is None else nodes,
    )
    zona.yield_time_s = yield_t
    if roads_tabla:
        zona.roads = dict(roads_tabla)
    app.map_recorder.zones[_ZONE_ID] = zona
    app.map_recorder.active_map_name = "test"
    app.map_recorder.client = app.client
    app._init_ui_state()
    app._ui_ucid = 3
    app._ui_tab = "elementos"
    app._ui_elem_type = "zone"
    app._ui_elem_detail_id = _ZONE_ID
    return zona


def _user_on_track(app, make_player, make_telemetry, x_m, y_m, ucid=3, plid=5):
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


class TestDetalleZona:
    def test_zona_con_poligono_dibuja_sus_tres_secciones(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            roads_tabla={"H": YieldType.NONE, "V": YieldType.YIELD},
        )
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)

        assert _btn(ai_control, ai_control._ZONE_YIELD_TITLE) is not None
        assert _btn(ai_control, ai_control._ZONE_YIELD_T_VAL) is not None
        assert _btn(ai_control, ai_control._ZONE_ROADS_TITLE) is not None
        assert _btn(ai_control, ai_control._ZONE_ROADS_REDETECT) is not None
        poly = _btn(ai_control, ai_control._ZONE_YIELD_POLY)
        assert "4" in poly.Text  # los 4 puntos del cuadrado

    def test_zona_a_medias_avisa_de_que_no_gobierna(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        """Menos de 3 puntos no encierra nada: la zona está a medias (S44)."""
        _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            nodes=[make_coords(0, 0), make_coords(5, 0)],
        )
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)

        poly = _btn(ai_control, ai_control._ZONE_YIELD_POLY)
        assert "NO" in poly.Text or "medias" in poly.Text.lower()

    def test_t_sin_valor_muestra_el_float_efectivo(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        _setup_zone_detail(
            ai_control, make_road, populate_graph, make_coords, yield_t=None
        )
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)

        t_btn = _btn(ai_control, ai_control._ZONE_YIELD_T_VAL)
        default = ai_control._map_ui_yield_default_t()
        assert f"{default:g}" in t_btn.Text
        assert "None" not in t_btn.Text
        assert _btn(ai_control, ai_control._ZONE_YIELD_T_DEF) is None

    def test_t_propio_ofrece_volver_al_default(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        zona = _setup_zone_detail(
            ai_control, make_road, populate_graph, make_coords, yield_t=6.0
        )
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)
        assert _btn(ai_control, ai_control._ZONE_YIELD_T_DEF) is not None

        ai_control._map_ui_click_elementos(ai_control._ZONE_YIELD_T_DEF)

        assert zona.yield_time_s is None

    def test_guardar_t_valido(self, ai_control, make_road, populate_graph, make_coords):
        zona = _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)

        ai_control._ui_input_buffer[ai_control._ZONE_YIELD_T_VAL] = "2.5"
        ai_control._map_ui_yield_apply_t(ai_control._ZONE_YIELD_T_VAL)

        assert zona.yield_time_s == 2.5


class TestTablaDeVias:
    def test_tabla_vacia_avisa_de_que_nadie_cede(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)

        assert any("adie cede" in t for t in _texts(ai_control))

    def test_cada_via_tiene_su_toggle_y_su_borrar(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            roads_tabla={"H": YieldType.NONE, "V": YieldType.YIELD},
        )
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)

        assert len(ai_control._ui_zone_roads_toggle) == 2
        assert len(ai_control._ui_zone_roads_del) == 2
        textos = _texts(ai_control)
        assert any("H" in t and "NONE" in t for t in textos)
        assert any("V" in t and "YIELD" in t for t in textos)

    def test_el_toggle_cicla_el_tipo_de_esa_via(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        zona = _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            roads_tabla={"H": YieldType.NONE, "V": YieldType.NONE},
        )
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)
        cid_v = next(
            cid for cid, via in ai_control._ui_zone_roads_toggle.items() if via == "V"
        )

        ai_control._map_ui_click_elementos(cid_v)
        assert zona.roads["V"] is YieldType.YIELD
        assert zona.roads["H"] is YieldType.NONE  # la otra no se toca

        ai_control._map_ui_click_elementos(cid_v)
        assert zona.roads["V"] is YieldType.STOP
        ai_control._map_ui_click_elementos(cid_v)
        assert zona.roads["V"] is YieldType.NONE

    def test_borrar_una_via_la_saca_de_la_tabla(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        zona = _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            roads_tabla={"H": YieldType.NONE, "V": YieldType.YIELD},
        )
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)
        cid_h = next(
            cid for cid, via in ai_control._ui_zone_roads_del.items() if via == "H"
        )

        ai_control._map_ui_click_elementos(cid_h)

        assert "H" not in zona.roads
        assert zona.roads["V"] is YieldType.YIELD

    def test_el_borrado_sobrevive_a_redibujar(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        """La tabla NO se auto-puebla al abrir el detalle: si lo hiciera, los
        falsos cruces borrados reaparecerían al salir y entrar (S46)."""
        zona = _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            roads_tabla={"H": YieldType.NONE},
        )
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)
        cid_h = next(
            cid for cid, via in ai_control._ui_zone_roads_del.items() if via == "H"
        )
        ai_control._map_ui_click_elementos(cid_h)

        ai_control._map_ui_draw_elem_detail(_ZONE_ID)  # reabrir el detalle

        assert zona.roads == {}


class TestRedetectar:
    def test_redetectar_puebla_con_las_vias_que_pisan_el_poligono(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        zona = _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)

        ai_control._map_ui_click_elementos(ai_control._ZONE_ROADS_REDETECT)

        assert set(zona.roads) == {"H", "V"}  # LEJOS no pisa el cuadrado
        assert all(t is YieldType.NONE for t in zona.roads.values())

    def test_redetectar_conserva_los_tipos_ya_puestos(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        """No se tira el trabajo hecho: V sigue siendo YIELD tras re-escanear."""
        zona = _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            roads_tabla={"V": YieldType.YIELD},
        )
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)

        ai_control._map_ui_click_elementos(ai_control._ZONE_ROADS_REDETECT)

        assert zona.roads["V"] is YieldType.YIELD  # conservado
        assert zona.roads["H"] is YieldType.NONE  # nueva

    def test_redetectar_sin_poligono_no_puebla_nada(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        zona = _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            nodes=[make_coords(0, 0), make_coords(5, 0)],
        )
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)

        ai_control._map_ui_click_elementos(ai_control._ZONE_ROADS_REDETECT)

        assert zona.roads == {}


class TestGrabadorDelPoligono:
    def test_grabar_abre_el_grabador_normal_de_zona(
        self,
        ai_control,
        make_road,
        populate_graph,
        make_coords,
        make_player,
        make_telemetry,
    ):
        _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        _user_on_track(ai_control, make_player, make_telemetry, 0.0, 0.0)
        ai_control._map_ui_draw_elem_detail(_ZONE_ID)

        ai_control._map_ui_click_elementos(ai_control._ZONE_YIELD_REC)

        rec = ai_control.map_recorder.current_recording
        assert rec is not None
        assert rec["type"] == "zone"
        assert rec["zone_id"] == _ZONE_ID


class TestWhereamiZona:
    """El overlay "WA Zona" y `!map whereami`, contra el polígono.

    Sin red hasta el 8.6.5: leían `ctx.zone_radius`, que el 8.6 borró del
    modelo — o sea que petaban con AttributeError en cuanto pineabas la zona.
    Por eso estos tests existen, y no solo por la conducta nueva.
    """

    def _wa_zona(self, app, make_player, make_telemetry, x_m, y_m):
        _user_on_track(app, make_player, make_telemetry, x_m, y_m)
        app._ui_whereami_ucid = 3
        return app._map_ui_compute_whereami("zone")

    def test_dentro_del_poligono(
        self,
        ai_control,
        make_road,
        populate_graph,
        make_coords,
        make_player,
        make_telemetry,
    ):
        _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)

        texto = self._wa_zona(ai_control, make_player, make_telemetry, 0.0, 0.0)

        assert "DENTRO" in texto
        assert _ZONE_ID in texto

    def test_fuera_reporta_la_distancia_al_borde(
        self,
        ai_control,
        make_road,
        populate_graph,
        make_coords,
        make_player,
        make_telemetry,
    ):
        """El cuadrado llega a x=5: desde x=15 el borde está a 10 m."""
        _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)

        texto = self._wa_zona(ai_control, make_player, make_telemetry, 15.0, 0.0)

        assert "DENTRO" not in texto
        assert "10.0m" in texto

    def test_zona_a_medias_nunca_esta_dentro(
        self,
        ai_control,
        make_road,
        populate_graph,
        make_coords,
        make_player,
        make_telemetry,
    ):
        """Sin polígono no hay interior que pisar (S44)."""
        _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            nodes=[make_coords(0, 0), make_coords(5, 0)],
        )

        texto = self._wa_zona(ai_control, make_player, make_telemetry, 0.0, 0.0)

        assert "DENTRO" not in texto

    def test_cmd_whereami_no_peta_y_dice_donde_estas(
        self,
        ai_control,
        make_road,
        populate_graph,
        make_coords,
        make_player,
        make_telemetry,
    ):
        """`!map whereami zone` por su camino real (el que petaba)."""
        _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        _user_on_track(ai_control, make_player, make_telemetry, 0.0, 0.0)

        ai_control.map_recorder._cmd_whereami(_FakePkt(3), "zone")

        msgs = [str(getattr(p, "Msg", "")) for p in ai_control.client.sent]
        assert any("DENTRO" in m and _ZONE_ID in m for m in msgs)


class TestRecorderBackend:
    """Lo que la UI delega en `map_recorder`, por el camino real."""

    def test_rec_end_rechaza_y_descarta_un_poligono_de_menos_de_3_puntos(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        """Lo importante: un polígono inválido NO se comete sobre la zona buena.

        Los puntos se pierden, sí: `_cmd_rec_end` tiene un `finally` que limpia
        `current_recording` pase lo que pase, y eso es el contrato de TODOS los
        tipos desde antes del 8.6 (una SpecialRule con 3 nodos se descarta
        igual). No se toca aquí; el mensaje avisa de que se descartan.
        """
        _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        mr = ai_control.map_recorder
        original = list(mr.zones[_ZONE_ID].nodes)
        mr.current_recording = {
            "type": "zone",
            "zone_id": _ZONE_ID,
            "nodes": [make_coords(0, 0), make_coords(5, 0)],
            "is_new": False,
        }

        mr._cmd_rec_end()

        assert mr.zones[_ZONE_ID].nodes == original  # la zona buena, intacta
        assert mr.current_recording is None  # descartada (contrato preexistente)
        assert any(
            "descarta" in str(getattr(p, "Msg", "")).lower()
            for p in ai_control.client.sent
        )

    def test_rec_end_guarda_el_poligono_y_autopuebla_la_tabla(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        _setup_zone_detail(ai_control, make_road, populate_graph, make_coords, nodes=[])
        mr = ai_control.map_recorder
        mr.current_recording = {
            "type": "zone",
            "zone_id": _ZONE_ID,
            "nodes": _cuadrado(make_coords),
            "is_new": False,
        }

        mr._cmd_rec_end()

        zona = mr.zones[_ZONE_ID]
        assert len(zona.nodes) == 4
        assert set(zona.roads) == {"H", "V"}
        assert mr.current_recording is None

    def test_set_roads_acepta_el_vocabulario(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        zona = _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)
        mr = ai_control.map_recorder

        mr._cmd_set(_ZONE_ID, "roads", "set;H,STOP")
        assert zona.roads["H"] is YieldType.STOP

        mr._cmd_set(_ZONE_ID, "roads", "del;H")
        assert "H" not in zona.roads

    def test_set_roads_rechaza_un_tipo_inventado(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        zona = _setup_zone_detail(ai_control, make_road, populate_graph, make_coords)

        ai_control.map_recorder._cmd_set(_ZONE_ID, "roads", "set;H,PREFERENTE")

        assert zona.roads == {}

    def test_check_avisa_de_la_zona_sin_poligono(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            nodes=[make_coords(0, 0), make_coords(5, 0)],
        )
        errores, _adv = ai_control.map_recorder.collect_check_results()

        assert any("poligono" in e.lower() for e in errores)

    def test_check_avisa_si_todas_las_vias_ceden(
        self, ai_control, make_road, populate_graph, make_coords
    ):
        """Sin ninguna NONE nadie tiene prioridad: el cruce se bloquea solo."""
        _setup_zone_detail(
            ai_control,
            make_road,
            populate_graph,
            make_coords,
            roads_tabla={"H": YieldType.YIELD, "V": YieldType.STOP},
        )
        _errores, advertencias = ai_control.map_recorder.collect_check_results()

        assert any("Ninguna via es NONE" in a for a in advertencias)
