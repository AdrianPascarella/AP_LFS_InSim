"""Fix S20: `ai_control` consciente de la reconexión (P12).

`ai_control` lanza sus gestores de tráfico en hilos daemon persistentes
(`_run_test_freeroam` y el cargador de rutas `_test`). Antes de este fix esos
bucles:

  - morían con `InSimConnectionError` al enviar sobre un socket caído (visto en
    S10, traceback a stderr invisible en el log), y
  - ignoraban toda señal de parada: el flag `_is_freeroam_loop_running` no se
    consultaba dentro del bucle, así que ni "Detener" en la UI los paraba.

Además `AIControl` no definía `on_disconnect`/`on_reconnect`, así que tras la
limpieza de memoria de la reconexión el bucle veía "0 coches" y recreaba IAs con
ownership desincronizado ("La AI X no es una de tus AI's").

Estos tests fijan el contrato del fix:
  - `on_disconnect` detiene TODOS los bucles de tráfico de forma limpia y pronta.
  - un `send` que lanza `InSimConnectionError` corta el bucle sin propagar.
  - `on_reconnect` resetea el estado de sesión (target + cachés) y NO reanuda el
    tráfico automático (evita arrastrar el UCID viejo).
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from lfs_insim import InSimConnectionError


def test_on_disconnect_detiene_gestor_freeroam(ai_control, make_ai):
    app = ai_control
    # 1 IA en pista → count(1) == target(1): el bucle entra en la espera larga
    # (sin envíos), aislando la señal de parada de cualquier otra lógica.
    app.user_manager.ais[1] = make_ai(plid=1, ucid=5)

    app._test_freeroam(SimpleNamespace(UCID=5), 1)
    assert app._is_freeroam_loop_running is True
    thread = app._traffic_threads[-1]
    assert thread.is_alive()

    app.on_disconnect()  # corre en el hilo principal, como en producción

    assert app._traffic_stop_event.is_set()
    assert not thread.is_alive()  # paró de verdad (no ignoró la señal)
    assert app._is_freeroam_loop_running is False


def test_on_disconnect_es_pronto(ai_control, make_ai):
    """La parada no depende de agotar el `time.sleep` de 5 s del bucle."""
    app = ai_control
    app.user_manager.ais[1] = make_ai(plid=1, ucid=5)
    app._test_freeroam(SimpleNamespace(UCID=5), 1)  # entra en stop.wait(5)
    thread = app._traffic_threads[-1]

    t0 = time.monotonic()
    app.on_disconnect()
    elapsed = time.monotonic() - t0

    assert not thread.is_alive()
    assert elapsed < 2.0  # muy por debajo del sleep de 5 s del bucle


def test_on_disconnect_detiene_cargador_rutas(ai_control):
    """El otro bucle daemon (cargador masivo de rutas) también obedece la parada."""
    app = ai_control
    app.route_manager.loaded_routes = {"ruta1"}

    app._test_routes(SimpleNamespace(UCID=5), "ruta1")
    thread = app._traffic_threads[-1]
    assert thread.is_alive()

    app.on_disconnect()

    assert not thread.is_alive()


def test_gestor_corta_limpio_si_cae_conexion(ai_control):
    """Un `send` que lanza `InSimConnectionError` corta el bucle sin propagar."""
    app = ai_control

    class RaisingClient:
        def send(self, packet):
            raise InSimConnectionError("socket caído")

    app.client = RaisingClient()
    app._target_freeroam_count = 1  # count(0) < target(1) → _cmd_add → send → raise
    app._traffic_stop_event.clear()
    app._is_freeroam_loop_running = True

    thread = threading.Thread(
        target=app._run_test_freeroam, args=(SimpleNamespace(UCID=5),), daemon=True
    )
    thread.start()
    thread.join(timeout=2.0)

    assert not thread.is_alive()  # cortó limpio, no se colgó
    assert app._is_freeroam_loop_running is False  # el finally lo apagó


def test_on_reconnect_resetea_estado_de_sesion(ai_control):
    app = ai_control
    app._target_freeroam_count = 7
    app._radar_human_cache[1] = (0.0, "R1", 3)
    app._target_lane_human_cache[2] = (0.0, "R2", 5)

    app.on_reconnect()  # idempotente aunque no haya ningún bucle corriendo

    assert app._target_freeroam_count == 0
    assert app._radar_human_cache == {}
    assert app._target_lane_human_cache == {}


def test_on_reconnect_detiene_gestor_en_marcha(ai_control, make_ai):
    """on_reconnect no debe dejar vivo un gestor con el UCID viejo."""
    app = ai_control
    app.user_manager.ais[1] = make_ai(plid=1, ucid=5)
    app._test_freeroam(SimpleNamespace(UCID=5), 1)
    thread = app._traffic_threads[-1]
    assert thread.is_alive()

    app.on_reconnect()

    assert not thread.is_alive()
    assert app._is_freeroam_loop_running is False
    assert app._target_freeroam_count == 0
