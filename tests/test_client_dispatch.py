"""
Tests del DISPATCH de InSimClient (Fase 2, arquitectura de composición — P11).

Cubre lo que faltaba del ítem "dispatch" del plan (el registro de handlers
activos y los filtros pre/post-decode ya están en test_active_packet_registry.py):

  - orden de entrega: primero el cliente (self), luego las apps en orden
    de registro (client.register);
  - aislamiento de errores: un handler que explota no rompe el dispatch ni
    afecta a los demás handlers;
  - keep-alive reactivo: un ISP_TINY con SubT=NONE se contesta con otro igual;
  - dispatch de lifecycle (on_connect/on_tick/...): orden, aislamiento y
    apps sin el hook;
  - cola + worker de dispatch (P2): la recepción solo encola (un handler
    lento no la bloquea), el worker entrega en orden FIFO y stop() vacía
    lo pendiente antes de salir;
  - apagado limpio (Fase 3): stop() concurrente ejecuta la secuencia de
    apagado UNA sola vez (check-and-set atómico de `running`);
  - política de errores de handlers (Fase 3): `handler_errors` = 'log'
    (default, aísla y loguea) | 'raise' (fail-fast: el primer error detiene
    el cliente y se propaga desde start()); durante stop() los errores de
    on_disconnect se aíslan siempre para que el apagado se complete;
  - tick configurable (Fase 3): `tick_interval` controla la cadencia de
    on_tick (default 0.1 s = comportamiento de siempre) SIN tocar el sondeo
    interno del bucle principal (≤100 ms), que sigue detectando caídas de
    conexión y errores fail-fast aunque el tick sea lento.
"""

import threading
import time

from unittest.mock import patch

import pytest

import lfs_insim.insim_state as state
from lfs_insim.exceptions import InSimConfigurationError
from lfs_insim.insim_app import InSimApp
from lfs_insim.insim_client import InSimClient
from lfs_insim.insim_enums import ISP, TINY
from lfs_insim.packets import ISP_MSO, ISP_TINY


def _esperar(condicion, timeout=2.0):
    """Sondea `condicion()` hasta que sea verdadera o venza el timeout."""
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.005)
    return condicion()


class _ClienteGrabador(InSimClient):
    """Cliente con un handler propio que apunta su turno en el diario."""

    def __init__(self, diario):
        super().__init__(config={})
        self._diario = diario

    def on_ISP_MSO(self, packet):
        self._diario.append("cliente")


class _AppGrabadora:
    """App mínima: apunta su etiqueta en el diario al recibir MSO."""

    def __init__(self, etiqueta, diario, explota=False):
        self.name = etiqueta
        self._etiqueta = etiqueta
        self._diario = diario
        self._explota = explota

    def on_ISP_MSO(self, packet):
        if self._explota:
            raise ValueError(f"boom en {self._etiqueta}")
        self._diario.append(self._etiqueta)


class _AppLifecycle:
    def __init__(self, etiqueta, diario, explota=False):
        self.name = etiqueta
        self._etiqueta = etiqueta
        self._diario = diario
        self._explota = explota

    def on_connect(self):
        if self._explota:
            raise RuntimeError(f"boom en {self._etiqueta}")
        self._diario.append(self._etiqueta)


class _Base:
    def setup_method(self):
        state.reset_insim_client()

    def teardown_method(self):
        state.reset_insim_client()


class TestRegister(_Base):
    def test_register_encola_y_asigna_el_cliente(self):
        client = InSimClient(config={})
        app_a = _AppGrabadora("A", [])
        app_b = _AppGrabadora("B", [])

        assert client.register(app_a) is app_a  # devuelve la app (chaining)
        client.register(app_b)

        assert client.apps == [app_a, app_b]
        assert app_a.client is client
        assert app_b.client is client

    def test_register_dos_veces_no_duplica(self):
        client = InSimClient(config={})
        app = _AppGrabadora("A", [])

        client.register(app)
        client.register(app)

        assert client.apps == [app]


class TestOrdenDeDispatch(_Base):
    def test_cliente_primero_luego_apps_en_orden(self):
        diario = []
        client = _ClienteGrabador(diario)
        client.register(_AppGrabadora("A", diario))
        client.register(_AppGrabadora("B", diario))
        client._active_handler_names = {"on_ISP_MSO"}

        client._dispatch_packet(ISP_MSO())

        assert diario == ["cliente", "A", "B"]

    def test_paquete_none_no_hace_nada(self):
        diario = []
        client = _ClienteGrabador(diario)
        client.register(_AppGrabadora("A", diario))

        client._dispatch_packet(None)

        assert diario == []

    def test_app_sin_handler_se_salta_sin_error(self):
        diario = []
        client = _ClienteGrabador(diario)

        class SinHandler:
            name = "muda"

        client.register(SinHandler())
        client.register(_AppGrabadora("B", diario))
        client._active_handler_names = {"on_ISP_MSO"}

        client._dispatch_packet(ISP_MSO())

        assert diario == ["cliente", "B"]


class TestAislamientoDeErrores(_Base):
    def test_handler_que_explota_no_corta_a_los_demas(self):
        diario = []
        client = _ClienteGrabador(diario)
        client.register(_AppGrabadora("A", diario, explota=True))
        client.register(_AppGrabadora("B", diario))
        client._active_handler_names = {"on_ISP_MSO"}

        client._dispatch_packet(ISP_MSO())  # no debe propagar la excepción

        assert diario == ["cliente", "B"]

    def test_error_en_el_cliente_no_corta_a_las_apps(self):
        diario = []

        class ClienteQueExplota(InSimClient):
            def __init__(self):
                super().__init__(config={})

            def on_ISP_MSO(self, packet):
                raise ValueError("boom en el cliente")

        client = ClienteQueExplota()
        client.register(_AppGrabadora("A", diario))
        client._active_handler_names = {"on_ISP_MSO"}

        client._dispatch_packet(ISP_MSO())

        assert diario == ["A"]


class TestKeepAliveReactivo(_Base):
    def test_tiny_none_se_contesta_con_tiny_none(self):
        client = InSimClient(config={})

        with patch.object(client, "send") as mock_send:
            client.on_packet_received(ISP_TINY(SubT=TINY.NONE))

        assert mock_send.call_count == 1
        respuesta = mock_send.call_args[0][0]
        assert isinstance(respuesta, ISP_TINY)
        assert respuesta.SubT == TINY.NONE
        assert respuesta.ReqI == 0

    def test_tiny_con_otro_subt_no_se_contesta(self):
        client = InSimClient(config={})

        with patch.object(client, "send") as mock_send:
            client.on_packet_received(ISP_TINY(ReqI=1, SubT=TINY.VER))

        mock_send.assert_not_called()

    def test_paquete_no_tiny_no_se_contesta(self):
        client = InSimClient(config={})

        with patch.object(client, "send") as mock_send:
            client.on_packet_received(ISP_MSO())

        mock_send.assert_not_called()


class TestDispatchLifecycle(_Base):
    def test_orden_de_apps(self):
        diario = []
        client = InSimClient(config={})
        client.register(_AppLifecycle("A", diario))
        client.register(_AppLifecycle("B", diario))

        client._dispatch_lifecycle("on_connect")

        assert diario == ["A", "B"]

    def test_error_aislado_por_app(self):
        diario = []
        client = InSimClient(config={})
        client.register(_AppLifecycle("A", diario, explota=True))
        client.register(_AppLifecycle("B", diario))

        client._dispatch_lifecycle("on_connect")  # no debe propagar

        assert diario == ["B"]

    def test_app_sin_hook_se_salta(self):
        diario = []
        client = InSimClient(config={})

        class SinHook:
            name = "muda"

        client.register(SinHook())
        client.register(_AppLifecycle("B", diario))

        client._dispatch_lifecycle("on_connect")

        assert diario == ["B"]

    def test_evento_inexistente_no_hace_nada(self):
        client = InSimClient(config={})
        client.register(_AppLifecycle("A", []))
        client._dispatch_lifecycle("on_evento_que_no_existe")


class _AppAcumuladora:
    """App que acumula los Msg de los MSO recibidos, en orden de llegada."""

    def __init__(self, bloqueo=None):
        self.name = "acumuladora"
        self.procesados = []
        self._bloqueo = bloqueo  # Event: si existe, el handler espera en él

    def on_ISP_MSO(self, packet):
        if self._bloqueo is not None:
            self._bloqueo.wait(2.0)
        self.procesados.append(packet.Msg)


class TestColaYWorkerDeDispatch(_Base):
    """P2: la recepción encola; un worker dedicado despacha en FIFO."""

    def test_on_packet_received_solo_encola(self):
        # Sin worker corriendo, el paquete queda en la cola y nadie lo despacha
        client = InSimClient(config={})
        pkt = ISP_MSO()

        with patch.object(client, "_dispatch_packet") as mock_dispatch:
            client.on_packet_received(pkt)

        mock_dispatch.assert_not_called()
        assert client._dispatch_queue.get_nowait() is pkt

    def test_worker_despacha_en_orden_fifo(self):
        client = InSimClient(config={})
        app = _AppAcumuladora()
        client.register(app)
        client._active_handler_names = {"on_ISP_MSO"}

        client._start_dispatch_worker()
        try:
            for i in range(20):
                client.on_packet_received(ISP_MSO(Msg=str(i)))
            assert _esperar(lambda: len(app.procesados) == 20)
        finally:
            client._stop_dispatch_worker()

        assert app.procesados == [str(i) for i in range(20)]

    def test_handler_lento_no_bloquea_la_recepcion(self):
        # Criterio de Fase 3: con el handler BLOQUEADO, on_packet_received
        # (lo que llama el hilo de IO) sigue aceptando paquetes al instante.
        bloqueo = threading.Event()
        client = InSimClient(config={})
        app = _AppAcumuladora(bloqueo=bloqueo)
        client.register(app)
        client._active_handler_names = {"on_ISP_MSO"}

        client._start_dispatch_worker()
        try:
            client.on_packet_received(ISP_MSO(Msg="0"))
            # El worker está dentro del handler, esperando en `bloqueo`
            assert _esperar(lambda: not client._dispatch_queue.qsize())

            inicio = time.monotonic()
            for i in range(1, 51):
                client.on_packet_received(ISP_MSO(Msg=str(i)))
            assert time.monotonic() - inicio < 0.5  # no esperó al handler
            assert app.procesados == []  # sigue en el primero

            # El keep-alive tampoco espera al handler: se contesta en el acto
            with patch.object(client, "send") as mock_send:
                client.on_packet_received(ISP_TINY(SubT=TINY.NONE))
            assert mock_send.call_count == 1

            bloqueo.set()
            assert _esperar(lambda: len(app.procesados) == 51)
            assert app.procesados == [str(i) for i in range(51)]
        finally:
            bloqueo.set()
            client._stop_dispatch_worker()

    def test_stop_despacha_lo_pendiente_antes_de_salir(self):
        # El centinela entra DETRÁS de lo encolado: nada se pierde al parar
        client = InSimClient(config={})
        app = _AppAcumuladora()
        client.register(app)
        client._active_handler_names = {"on_ISP_MSO"}

        for i in range(5):
            client.on_packet_received(ISP_MSO(Msg=str(i)))

        client._start_dispatch_worker()
        client._stop_dispatch_worker()

        assert app.procesados == [str(i) for i in range(5)]
        assert client._dispatch_thread is None

    def test_worker_sobrevive_a_un_handler_que_explota(self):
        diario = []
        client = InSimClient(config={})
        client.register(_AppGrabadora("A", diario, explota=True))
        client.register(_AppGrabadora("B", diario))
        client._active_handler_names = {"on_ISP_MSO"}

        client._start_dispatch_worker()
        try:
            client.on_packet_received(ISP_MSO())
            client.on_packet_received(ISP_MSO())
            assert _esperar(lambda: diario.count("B") == 2)
        finally:
            client._stop_dispatch_worker()

        assert diario == ["B", "B"]

    def test_start_dispatch_worker_es_idempotente(self):
        client = InSimClient(config={})
        client._start_dispatch_worker()
        hilo = client._dispatch_thread
        try:
            client._start_dispatch_worker()
            assert client._dispatch_thread is hilo
        finally:
            client._stop_dispatch_worker()


class TestStopConcurrente(_Base):
    """Apagado limpio (Fase 3): la secuencia de stop() corre UNA sola vez."""

    def test_stops_simultaneos_despachan_on_disconnect_una_vez(self):
        # Carrera del check-and-set de `running`: dos hilos parando a la vez
        # (p. ej. un handler que llama a stop() y un Ctrl+C simultáneo)
        # pasaban ambos la guarda y despachaban on_disconnect dos veces.
        client = InSimClient(config={})
        client.running = True
        client.connected = True

        desconexiones = []

        class _Testigo:
            name = "testigo"

            def on_disconnect(self):
                desconexiones.append("off")

        client.register(_Testigo())

        n_hilos = 8
        barrera = threading.Barrier(n_hilos)

        def parar():
            barrera.wait(2.0)
            client.stop()

        hilos = [threading.Thread(target=parar) for _ in range(n_hilos)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(2.0)

        assert desconexiones == ["off"]
        assert client.running is False

    def test_stop_reentrante_desde_on_disconnect_no_se_bloquea(self):
        # El lock solo cubre el flip del flag: un hook on_disconnect que
        # llame a stop() otra vez debe volver al instante, sin deadlock.
        client = InSimClient(config={})
        client.running = True
        client.connected = True

        desconexiones = []

        class _Reentrante:
            name = "reentrante"

            def on_disconnect(self):
                desconexiones.append("off")
                client.stop()  # reentrada deliberada

        client.register(_Reentrante())

        hilo = threading.Thread(target=client.stop, daemon=True)
        hilo.start()
        hilo.join(2.0)

        assert not hilo.is_alive()  # sin deadlock
        assert desconexiones == ["off"]


class TestPoliticaDeErroresDeHandlers(_Base):
    """Fase 3: `handler_errors` = 'log' (resiliente, default) | 'raise' (fail-fast)."""

    def test_valor_invalido_falla_al_crear_el_cliente(self):
        with pytest.raises(InSimConfigurationError):
            InSimClient(config={"handler_errors": "explota"})

    def test_raise_propaga_el_error_y_corta_el_dispatch_del_paquete(self):
        # Fail-fast: el primer handler que explota propaga; las apps
        # posteriores ya no reciben ese paquete.
        diario = []
        client = InSimClient(config={"handler_errors": "raise"})
        client.register(_AppGrabadora("A", diario, explota=True))
        client.register(_AppGrabadora("B", diario))
        client._active_handler_names = {"on_ISP_MSO"}

        with pytest.raises(ValueError):
            client._dispatch_packet(ISP_MSO())

        assert diario == []

    def test_log_sigue_siendo_el_default(self):
        # Sin configurar nada, el comportamiento es el de siempre: aislar.
        diario = []
        client = InSimClient(config={})
        client.register(_AppGrabadora("A", diario, explota=True))
        client.register(_AppGrabadora("B", diario))
        client._active_handler_names = {"on_ISP_MSO"}

        client._dispatch_packet(ISP_MSO())  # no propaga

        assert diario == ["B"]

    def test_raise_el_worker_guarda_el_error_y_deja_de_despachar(self):
        # El worker no puede re-lanzar hacia el hilo principal directamente:
        # guarda la excepción en _handler_error, deja de despachar (los
        # paquetes pendientes se descartan) y sale.
        diario = []
        client = InSimClient(config={"handler_errors": "raise"})
        client.register(_AppGrabadora("A", diario, explota=True))
        client.register(_AppGrabadora("B", diario))
        client._active_handler_names = {"on_ISP_MSO"}

        client.on_packet_received(ISP_MSO())  # provocará el error
        client.on_packet_received(ISP_MSO())  # queda detrás, no debe entregarse

        client._start_dispatch_worker()
        hilo = client._dispatch_thread
        try:
            assert _esperar(lambda: client._handler_error is not None)
            assert isinstance(client._handler_error, ValueError)
            assert _esperar(lambda: not hilo.is_alive())  # el worker salió
            assert client._dispatch_queue.qsize() == 1  # el 2º quedó sin despachar
            assert diario == []  # B no recibió nada
        finally:
            client._stop_dispatch_worker()

    def test_raise_detiene_el_cliente_y_propaga_desde_start(self, fake_lfs):
        # Integración: el error del worker llega al hilo principal, que
        # re-lanza la excepción original desde start() y para el cliente.
        class _AppQueExplota(InSimApp):
            def __init__(self):
                super().__init__(name="explosiva")

            def on_ISP_TINY(self, packet):
                raise ValueError("boom en TINY")

        client = InSimClient(
            config={
                "tcp_host": fake_lfs.host,
                "tcp_port": fake_lfs.port,
                "handler_errors": "raise",
            },
            name="FailFast",
        )
        client.register(_AppQueExplota())

        capturadas = []

        def _correr():
            try:
                client.start()
            except ValueError as e:
                capturadas.append(e)

        hilo = threading.Thread(target=_correr, daemon=True)
        hilo.start()
        try:
            assert fake_lfs.espera_conexion()
            assert _esperar(lambda: client.connected)

            fake_lfs.enviar(bytes([1, ISP.TINY, 0, 0]))  # keep-alive → boom

            hilo.join(3.0)
            assert not hilo.is_alive()  # start() terminó
            assert capturadas and isinstance(capturadas[0], ValueError)
            assert client.running is False  # y paró el cliente
        finally:
            client.stop()
            hilo.join(2.0)
            client.transport.close()

    def test_raise_tambien_aplica_a_los_hooks_de_lifecycle(self):
        diario = []
        client = InSimClient(config={"handler_errors": "raise"})
        client.register(_AppLifecycle("A", diario, explota=True))
        client.register(_AppLifecycle("B", diario))

        with pytest.raises(RuntimeError):
            client._dispatch_lifecycle("on_connect")

        assert diario == []

    def test_raise_durante_stop_aisla_y_completa_el_apagado(self):
        # Excepción a la política: el apagado debe completarse SIEMPRE y
        # todas las apps deben recibir su on_disconnect aunque una explote.
        client = InSimClient(config={"handler_errors": "raise"})
        client.running = True
        client.connected = True

        desconexiones = []

        class _Explosiva:
            name = "explosiva"

            def on_disconnect(self):
                raise RuntimeError("boom en on_disconnect")

        class _Testigo:
            name = "testigo"

            def on_disconnect(self):
                desconexiones.append("off")

        client.register(_Explosiva())
        client.register(_Testigo())

        client.stop()  # no debe propagar

        assert desconexiones == ["off"]
        assert client.running is False


class _AppTicker(InSimApp):
    """App que apunta el instante de cada on_tick recibido."""

    def __init__(self):
        super().__init__(name="ticker")
        self.ticks = []

    def on_tick(self):
        self.ticks.append(time.monotonic())


class TestTickInterval(_Base):
    """Fase 3: `tick_interval` regula on_tick sin tocar el sondeo interno."""

    def _arrancar(self, fake_lfs, config_extra):
        config = {
            "tcp_host": fake_lfs.host,
            "tcp_port": fake_lfs.port,
            "reconnect_delay": 0.02,
            "reconnect_backoff": 1.0,
        }
        config.update(config_extra)
        app = _AppTicker()
        client = InSimClient(config=config, name="Tick")
        client.register(app)
        hilo = threading.Thread(target=client.start, daemon=True)
        hilo.start()
        return client, hilo, app

    def test_valor_invalido_falla_al_crear_el_cliente(self):
        # No numérico, cero/negativo o por debajo del suelo (0.01 s)
        for malo in ("rapido", None, 0, -1, 0.001):
            with pytest.raises(InSimConfigurationError):
                InSimClient(config={"tick_interval": malo})

    def test_on_tick_respeta_un_intervalo_mas_lento(self, fake_lfs):
        # Con tick_interval=0.3 los ticks no pueden llegar a la cadencia
        # vieja de ~100 ms: cada hueco entre ticks debe rondar el intervalo.
        client, hilo, app = self._arrancar(fake_lfs, {"tick_interval": 0.3})
        try:
            assert fake_lfs.espera_conexion()
            assert _esperar(lambda: len(app.ticks) >= 3, timeout=3.0)

            huecos = [b - a for a, b in zip(app.ticks, app.ticks[1:])]
            assert all(h >= 0.25 for h in huecos), huecos  # margen de jitter
        finally:
            client.stop()
            hilo.join(2.0)
            client.transport.close()

    def test_on_tick_puede_ir_mas_rapido_que_el_poll_viejo(self, fake_lfs):
        # Con tick_interval=0.02, acumular 12 ticks debe costar MUCHO menos
        # que a la cadencia vieja (11 huecos de 100 ms ≥ 1.1 s).
        client, hilo, app = self._arrancar(fake_lfs, {"tick_interval": 0.02})
        try:
            assert fake_lfs.espera_conexion()
            assert _esperar(lambda: len(app.ticks) >= 12, timeout=3.0)

            assert app.ticks[11] - app.ticks[0] < 0.9
        finally:
            client.stop()
            hilo.join(2.0)
            client.transport.close()

    def test_un_tick_lento_no_retrasa_la_deteccion_de_caida(self, fake_lfs):
        # El sondeo interno queda desacoplado: con tick_interval=5.0 la
        # caída se detecta y reconecta igual en fracciones de segundo.
        client, hilo, app = self._arrancar(fake_lfs, {"tick_interval": 5.0})
        try:
            assert fake_lfs.espera_conexion()
            assert _esperar(lambda: client.connected)

            fake_lfs.cerrar_conexion()

            assert fake_lfs.espera_conexiones(2, timeout=2.0)  # << 5 s
            assert _esperar(lambda: client.connected)
        finally:
            client.stop()
            hilo.join(2.0)
            client.transport.close()
