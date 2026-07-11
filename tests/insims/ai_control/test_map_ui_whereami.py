"""
Overlay whereami "pineado" de map_ui (mitad-derecha, independiente del menú).

Caracteriza el comportamiento NUEVO pedido por el usuario: al seleccionar un
whereami en la pestaña Info, deja de ser una fila dentro del menú y pasa a ser un
overlay fijo anclado a la mitad-derecha de la pantalla que:

  - usa CIDs propios FUERA del rango de contenido (108-165) → sobrevive a los
    redibujados de pestaña,
  - persiste aunque se cierre el menú (solo se quita deseleccionándolo),
  - se refresca aunque el menú esté cerrado, usando el UCID del dueño del overlay.

Se ejercita sobre la AIControl real del harness (client que captura los envíos).
"""

from __future__ import annotations

from insims.ai_control.map_ui import _FakePkt
from lfs_insim.insim_enums import BFN

# CID del toggle "WA Road" en la fila de Info (113 = primer tipo, "road").
_CID_WA_ROAD = 113


def _btns(app):
    return [p for p in app.client.sent if type(p).__name__ == "ISP_BTN"]


def _bfns(app):
    return [p for p in app.client.sent if type(p).__name__ == "ISP_BFN"]


def _open_info(app, ucid=3):
    """Estado mínimo: menú abierto por `ucid`, en la pestaña Info."""
    app.map_recorder.active_map_name = "test"
    app._init_ui_state()
    app._ui_ucid = ucid
    app._ui_tab = "info"


def test_seleccionar_dibuja_overlay_pineado_a_la_derecha(ai_control):
    app = ai_control
    _open_info(app, ucid=3)
    app.client.sent.clear()

    app._map_ui_handle_click(_CID_WA_ROAD)  # WA Road ON

    pin = [
        p
        for p in _btns(app)
        if p.ClickID in (app._WA_PIN_CID_TITLE, app._WA_PIN_CID_BASE)
    ]
    assert pin, "seleccionar un whereami debe dibujar el overlay pineado"
    # Fuera del rango de contenido (108-165) → no lo borra un cambio de pestaña.
    assert all(p.ClickID > 165 for p in pin)
    # El overlay pertenece al usuario que lo activó.
    assert app._ui_whereami_ucid == 3

    row = next(p for p in pin if p.ClickID == app._WA_PIN_CID_BASE)  # road = idx 0
    assert row.L == app._WA_PIN_L
    assert row.L + row.W <= 200  # cabe en pantalla, anclado a la derecha
    # Anclado a la mitad vertical (centrado en ~100 para 1 fila + título).
    assert 80 <= row.T <= 120


def test_overlay_persiste_al_cambiar_de_pestana(ai_control):
    app = ai_control
    _open_info(app, ucid=3)
    app._map_ui_handle_click(_CID_WA_ROAD)  # WA Road ON
    app.client.sent.clear()

    app._map_ui_handle_click(app._UI_CID_TAB_GRAB)  # cambia a "Grabar"

    # El clear de contenido nunca abarca los CIDs del overlay (>165).
    for p in _bfns(app):
        if p.SubT == BFN.DEL_BTN:
            assert not (p.ClickID <= app._WA_PIN_CID_TITLE <= p.ClickMax)
    assert app._ui_whereami == {"road"}


def test_overlay_sobrevive_al_cierre_del_menu(ai_control):
    app = ai_control
    _open_info(app, ucid=3)
    app._map_ui_handle_click(_CID_WA_ROAD)  # WA Road ON
    app.client.sent.clear()

    app._map_ui_handle_click(app._UI_CID_CLOSE)  # X

    assert app._ui_ucid is None  # el menú se cierra
    assert app._ui_whereami_ucid == 3  # pero el overlay conserva su dueño
    # BFN.CLEAR borró todo; el overlay se redibujó a continuación.
    assert any(p.SubT == BFN.CLEAR for p in _bfns(app))
    assert any(p.ClickID == app._WA_PIN_CID_TITLE for p in _btns(app))


def test_deseleccionar_el_ultimo_borra_el_overlay(ai_control):
    app = ai_control
    _open_info(app, ucid=3)
    app._map_ui_handle_click(_CID_WA_ROAD)  # ON
    app.client.sent.clear()

    app._map_ui_handle_click(_CID_WA_ROAD)  # OFF (último) → limpia

    assert app._ui_whereami == set()
    assert app._ui_whereami_ucid is None
    # Se borró el rango del overlay (título .. última fila posible).
    dels = [p for p in _bfns(app) if p.SubT == BFN.DEL_BTN]
    assert any(
        p.ClickID == app._WA_PIN_CID_TITLE
        and p.ClickMax == app._WA_PIN_CID_BASE + len(app._WA_TYPES) - 1
        for p in dels
    )


def test_on_tick_refresca_overlay_con_menu_cerrado(ai_control):
    app = ai_control
    _open_info(app, ucid=3)
    app._map_ui_handle_click(_CID_WA_ROAD)  # ON
    app._map_ui_handle_click(app._UI_CID_CLOSE)  # cierra el menú
    assert app._ui_ucid is None and app._ui_whereami_ucid == 3

    app._ui_whereami_last_update = 0.0  # fuerza el refresco en el próximo tick
    app.client.sent.clear()
    app.on_tick()

    rows = [p for p in _btns(app) if p.ClickID == app._WA_PIN_CID_BASE]
    assert rows, "el overlay debe refrescarse aunque el menú esté cerrado"
    # Refresco = solo texto (W=0/H=0), no recoloca el botón.
    assert all(p.W == 0 and p.H == 0 for p in rows)


def test_compute_usa_el_ucid_del_overlay_no_el_del_menu(ai_control):
    app = ai_control
    _open_info(app, ucid=7)
    llamadas = []
    app.map_recorder.get_coords_fn = lambda ucid: llamadas.append(ucid) or None

    app._map_ui_handle_click(_CID_WA_ROAD)  # ON → redibuja → compute
    app._map_ui_close()  # menú cerrado: _ui_ucid pasa a None
    llamadas.clear()
    app._ui_whereami_last_update = 0.0
    app.on_tick()

    assert llamadas, "el overlay debe seguir computando con el menú cerrado"
    assert all(u == 7 for u in llamadas)  # nunca con None (el UCID del menú)


def test_overlay_persiste_al_reabrir_el_menu(ai_control):
    app = ai_control
    _open_info(app, ucid=3)
    app._map_ui_handle_click(_CID_WA_ROAD)  # ON
    app._map_ui_close()

    app._map_ui_open(_FakePkt(3))  # reabrir el menú

    # _init_ui_state NO resetea el overlay: la selección sigue viva.
    assert app._ui_whereami == {"road"}
    assert app._ui_whereami_ucid == 3
