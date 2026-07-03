"""
Tests de reconexión automática (Fase 3 — P12).

Dos niveles:
  - Transporte: `on_connection_lost` se dispara cuando el bucle receptor TCP
    muere de forma inesperada (recv vacío o excepción) y NO se dispara en un
    cierre deliberado (`close()` pone el stop antes).
  - Cliente: el bucle principal de `start()` detecta la caída, despacha
    `on_disconnect` a las apps, reintenta con backoff, reenvía el ISI,
    re-solicita el estado (TINY.NCN/NPL) y despacha `on_reconnect`. Si la
    reconexión está desactivada o se agotan los intentos, el cliente se
    detiene limpiamente (sin proceso zombie — el defecto original de P12).

Integración real por loopback contra FakeLFS (conftest.py), que acepta
conexiones sucesivas.
"""

import logging
import threading
import time
from unittest.mock import patch

import pytest

import lfs_insim.insim_state as state
from lfs_insim.exceptions import InSimConnectionError
from lfs_insim.insim_app import InSimApp
from lfs_insim.insim_client import InSimClient
from lfs_insim.insim_enums import ISP, TINY
from lfs_insim.insim_packet_sender import encode_packet
from lfs_insim.insim_transport import InSimTransport
from lfs_insim.packets import ISP_TINY


TINY_KEEPALIVE = bytes([1, ISP.TINY, 0, 0])


@pytest.fixture(autouse=True)
def _cliente_por_defecto_limpio():
    state.reset_insim_client()
    yield
    state.reset_insim_client()


def _esperar(condicion, timeout=3.0):
    """Espera activa a que `condicion()` sea verdadera (para hilos reales)."""
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.005)
    return condicion()


# ---------------------------------------------------------------------------
# Transporte: el callback on_connection_lost
# ---------------------------------------------------------------------------


class _SocketTcpGuionizado:
    """Socket falso: cada recv() devuelve el siguiente trozo del guion.

    Un elemento Exception se lanza en vez de devolverse; agotado el guion,
    recv() devuelve b'' (LFS cierra la conexión).
    """

    def __init__(self, *guion):
        self._guion = list(guion)

    def recv(self, bufsize):
        if not self._guion:
            return b""
        paso = self._guion.pop(0)
        if isinstance(paso, BaseException):
            raise paso
        return paso


class TestCallbackDeCaidaDelTransporte:
    def _correr(self, *guion, stop_previo=False):
        avisos = []
        transporte = InSimTransport(on_raw=lambda data: None)
        transporte.on_connection_lost = lambda: avisos.append(True)
        if stop_previo:
            transporte._stop.set()
        transporte._tcp_listen_loop(_SocketTcpGuionizado(*guion))
        return avisos

    def test_recv_vacio_avisa_una_vez(self):
        # LFS cierra la conexión: el bucle termina y avisa al dueño.
        assert self._correr(TINY_KEEPALIVE) == [True]

    def test_excepcion_de_recv_tambien_avisa(self):
        assert self._correr(ConnectionResetError("boom")) == [True]

    def test_con_stop_puesto_no_avisa(self):
        # close() pone el stop antes de cerrar el socket: cierre deliberado,
        # no debe dispararse la reconexión.
        assert self._correr(TINY_KEEPALIVE, stop_previo=True) == []

    def test_error_del_callback_no_propaga(self):
        transporte = InSimTransport(on_raw=lambda data: None)
        transporte.on_connection_lost = lambda: 1 / 0
        transporte._tcp_listen_loop(_SocketTcpGuionizado())  # no debe lanzar

    def test_sin_callback_no_revienta(self):
        transporte = InSimTransport(on_raw=lambda data: None)
        transporte._tcp_listen_loop(_SocketTcpGuionizado())


# ---------------------------------------------------------------------------
# Cliente: detección, hooks, restauración y política de reintentos
# ---------------------------------------------------------------------------


class _AppEspia(InSimApp):
    """App que apunta en un diario los eventos de ciclo de vida que recibe."""

    def __init__(self, name, diario):
        super().__init__(name=name)
        self.diario = diario

    def on_connect(self):
        self.diario.append((self.name, "connect"))

    def on_disconnect(self):
        self.diario.append((self.name, "disconnect"))

    def on_reconnect(self):
        self.diario.append((self.name, "reconnect"))


@pytest.fixture
def arrancar_cliente(fake_lfs):
    """Arranca un InSimClient real (start() en un hilo) contra el FakeLFS.

    Devuelve una función `(config_extra, apps) -> (cliente, hilo)`; al
    terminar el test detiene los clientes y espera a sus hilos.
    """
    arrancados = []

    def _arrancar(config_extra=None, apps=()):
        config = {
            "tcp_host": fake_lfs.host,
            "tcp_port": fake_lfs.port,
            "reconnect_delay": 0.02,
            "reconnect_backoff": 1.0,  # sin crecimiento: tests rápidos
        }
        if config_extra:
            config.update(config_extra)
        cliente = InSimClient(config=config, name="Reconexion")
        for app in apps:
            cliente.register(app)
        hilo = threading.Thread(target=cliente.start, daemon=True)
        hilo.start()
        arrancados.append((cliente, hilo))
        return cliente, hilo

    yield _arrancar

    for cliente, hilo in arrancados:
        cliente.stop()
        hilo.join(2.0)
        cliente.transport.close()  # por si start() murió antes de stop()


class TestReconexionDelCliente:
    def test_caida_despacha_on_disconnect_y_reconecta(self, fake_lfs, arrancar_cliente):
        diario = []
        cliente, _ = arrancar_cliente(
            apps=[_AppEspia("A", diario), _AppEspia("B", diario)]
        )
        assert fake_lfs.espera_conexion()
        assert _esperar(lambda: cliente.connected)

        fake_lfs.cerrar_conexion()

        # Reconecta (segunda conexión aceptada) y la sesión vuelve a estar viva
        assert fake_lfs.espera_conexiones(2)
        assert _esperar(lambda: cliente.connected)
        assert cliente.running

        # Eventos en orden y a todas las apps: connect → disconnect → reconnect
        assert _esperar(lambda: diario.count(("B", "reconnect")) == 1)
        for name in ("A", "B"):
            eventos = [e for n, e in diario if n == name]
            assert eventos == ["connect", "disconnect", "reconnect"]

    def test_al_reconectar_reenvia_isi_y_resolicita_estado(
        self, fake_lfs, arrancar_cliente
    ):
        cliente, _ = arrancar_cliente()
        assert fake_lfs.espera_conexion()
        assert _esperar(lambda: cliente.connected)

        # Lo único enviado hasta ahora es el ISI final (flags ya agregados)
        isi = encode_packet(cliente.isi)
        assert _esperar(lambda: fake_lfs.recibido == isi)

        fake_lfs.cerrar_conexion()
        assert fake_lfs.espera_conexiones(2)

        # Tras reconectar: mismo ISI otra vez + re-solicitud de NCN y NPL
        esperado = (
            isi
            + isi
            + encode_packet(ISP_TINY(ReqI=1, SubT=TINY.NCN))
            + encode_packet(ISP_TINY(ReqI=1, SubT=TINY.NPL))
        )
        assert _esperar(lambda: fake_lfs.recibido == esperado)

    def test_on_reconnect_se_despacha_antes_de_resolicitar_estado(self):
        # P22: la limpieza de estado de las apps (on_reconnect) debe ocurrir
        # ANTES de enviar TINY.NCN/NPL — así sus respuestas nunca pueden
        # llegar antes que la limpieza y ser borradas por ella.
        orden = []

        class _EspiaReconnect(InSimApp):
            def on_reconnect(self):
                orden.append("reconnect")

        cliente = InSimClient(config={}, name="OrdenRestauracion")
        cliente.register(_EspiaReconnect(name="A"))

        def _capturar(packet):
            if isinstance(packet, ISP_TINY):
                orden.append(("tiny", int(packet.SubT)))
            else:
                orden.append(type(packet).__name__)

        with patch.object(cliente, "send", side_effect=_capturar):
            cliente._restore_session()

        assert orden == [
            "ISP_ISI",
            "reconnect",
            ("tiny", int(TINY.NCN)),
            ("tiny", int(TINY.NPL)),
        ]
        assert cliente.connected

    def test_dos_caidas_seguidas_reconecta_las_dos_veces(
        self, fake_lfs, arrancar_cliente
    ):
        cliente, _ = arrancar_cliente()
        assert fake_lfs.espera_conexion()
        assert _esperar(lambda: cliente.connected)

        fake_lfs.cerrar_conexion()
        assert fake_lfs.espera_conexiones(2)
        assert _esperar(lambda: cliente.connected)

        fake_lfs.cerrar_conexion()
        assert fake_lfs.espera_conexiones(3)
        assert _esperar(lambda: cliente.connected)
        assert cliente.running

    def test_reconnect_desactivado_detiene_el_cliente(self, fake_lfs, arrancar_cliente):
        diario = []
        cliente, hilo = arrancar_cliente(
            config_extra={"reconnect": False}, apps=[_AppEspia("A", diario)]
        )
        assert fake_lfs.espera_conexion()
        assert _esperar(lambda: cliente.connected)

        fake_lfs.cerrar_conexion()

        # Sin reconexión: el cliente se detiene (no hay proceso zombie)
        hilo.join(3.0)
        assert not hilo.is_alive()
        assert not cliente.running
        assert cliente.transport._tcp_sock is None  # stop() cerró el transporte
        assert fake_lfs.conexiones == 1  # no lo reintentó
        # on_disconnect llegó una sola vez (la caída; stop() no lo duplica)
        assert [e for _, e in diario] == ["connect", "disconnect"]

    def test_intentos_agotados_detiene_el_cliente(self, fake_lfs, arrancar_cliente):
        # El connect real a un puerto cerrado tarda segundos en Windows;
        # aquí se prueba la POLÍTICA de reintentos, así que se parchea el
        # transporte para que cada intento falle al instante.
        cliente, hilo = arrancar_cliente(config_extra={"reconnect_max_attempts": 2})
        assert fake_lfs.espera_conexion()
        assert _esperar(lambda: cliente.connected)

        intentos = []

        def _conexion_rechazada(host, port):
            intentos.append((host, port))
            raise InSimConnectionError("LFS no está")

        cliente.transport.connect_tcp = _conexion_rechazada
        fake_lfs.cerrar_conexion()

        hilo.join(3.0)
        assert not hilo.is_alive()
        assert not cliente.running
        assert len(intentos) == 2  # exactamente max_attempts intentos

    def test_stop_durante_la_reconexion_sale_limpio(self, fake_lfs, arrancar_cliente):
        cliente, hilo = arrancar_cliente(
            config_extra={"reconnect_delay": 0.2}  # intentos infinitos
        )
        assert fake_lfs.espera_conexion()
        assert _esperar(lambda: cliente.connected)

        def _conexion_rechazada(host, port):
            raise InSimConnectionError("LFS no está")

        cliente.transport.connect_tcp = _conexion_rechazada
        fake_lfs.cerrar_conexion()
        assert _esperar(lambda: not cliente.connected)  # ya está reintentando

        cliente.stop()  # debe despertar el backoff y salir

        hilo.join(2.0)
        assert not hilo.is_alive()


class TestReconexionProvisional:
    """P24: una reconexión solo es PROVISIONAL — LFS puede aceptar el TCP y
    tirar la conexión justo tras el ISI (p. ej. admin password incorrecta).
    Antes, cada "reconexión con éxito" reseteaba el backoff → tormenta de
    ~10 conexiones/s contra LFS (visto en vivo en S12: "InSim - TCP excess").
    Si la sesión muere antes de `reconnect_stable_time`, el siguiente ciclo
    retoma la racha: espera el delay acumulado y sigue escalando."""

    def _cliente(self, **config_extra):
        config = {
            "reconnect_delay": 1.0,
            "reconnect_backoff": 2.0,
            "reconnect_max_delay": 30.0,
            "reconnect_stable_time": 10.0,
        }
        config.update(config_extra)
        cliente = InSimClient(config=config, name="Tormenta")
        cliente.running = True
        return cliente

    def _estado_post_start(self, cliente):
        """Deja al cliente como lo deja start() al levantar la sesión inicial."""
        cliente._session_started_at = time.monotonic()
        cliente._reconnect_attempt = 0
        cliente._reconnect_delay = 1.0

    def test_sesion_que_muere_joven_retoma_el_backoff(self):
        cliente = self._cliente()
        esperas = []

        with (
            patch.object(cliente, "_sleep_while_running", side_effect=esperas.append),
            patch.object(cliente.transport, "connect_tcp"),
            patch.object(cliente, "_restore_session"),
        ):
            self._estado_post_start(cliente)
            # Siete caídas inmediatas seguidas: cada _reconnect "tiene éxito"
            # (TCP + ISI enviados) pero la sesión nunca llega a estable.
            for _ in range(7):
                cliente._reconnect()

        # Espera acumulada ANTES de cada reintento, con tope en max_delay —
        # sin el fix no había NINGUNA espera (tormenta a toda velocidad).
        assert esperas == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0]

    def test_sesion_estable_resetea_el_backoff(self):
        cliente = self._cliente()
        esperas = []

        with (
            patch.object(cliente, "_sleep_while_running", side_effect=esperas.append),
            patch.object(cliente.transport, "connect_tcp"),
            patch.object(cliente, "_restore_session"),
        ):
            # Resto de una racha vieja, pero la sesión duró 60 s (> estable)
            cliente._session_started_at = time.monotonic() - 60.0
            cliente._reconnect_attempt = 7
            cliente._reconnect_delay = 30.0
            cliente._reconnect()

        assert esperas == []  # reintento inmediato
        assert cliente._reconnect_attempt == 1  # racha nueva

    def test_la_racha_cuenta_para_max_attempts(self):
        # Antes, cada ciclo de la tormenta contaba como "attempt 1" y
        # reconnect_max_attempts no agotaba nunca.
        cliente = self._cliente(reconnect_max_attempts=3)
        esperas = []

        with (
            patch.object(cliente, "_sleep_while_running", side_effect=esperas.append),
            patch.object(cliente.transport, "connect_tcp"),
            patch.object(cliente, "_restore_session"),
        ):
            self._estado_post_start(cliente)
            for _ in range(4):
                if not cliente.running:
                    break
                cliente._reconnect()

        assert not cliente.running  # la racha agotó los intentos y paró


class TestPistaDeIsiRechazado:
    """Idea DX de S12: LFS no da NINGÚN feedback en el socket cuando rechaza
    un ISI (p. ej. admin password incorrecta) — solo cierra. El cliente
    detecta la firma "sesión joven Y muda" y deja una pista explícita en el
    log, que es lo que faltó en el diagnóstico del incidente de S12."""

    PISTA = "the ISI was likely rejected"

    def _cliente_caido(self, recibio_datos):
        cliente = InSimClient(config={"reconnect": False}, name="Pista")
        cliente.running = True
        cliente.connected = True
        cliente._session_started_at = time.monotonic()  # sesión recién nacida
        cliente._session_received_data = recibio_datos
        return cliente

    def test_caida_joven_y_muda_loguea_la_pista(self, caplog):
        cliente = self._cliente_caido(recibio_datos=False)
        with caplog.at_level(logging.WARNING):
            cliente._handle_connection_lost()
        assert any(self.PISTA in r.message for r in caplog.records)

    def test_si_llego_algun_paquete_no_hay_pista(self, caplog):
        # La sesión murió joven pero LFS SÍ habló: el ISI fue aceptado
        # (caída real, no rechazo) — la pista sobraría y confundiría.
        cliente = self._cliente_caido(recibio_datos=True)
        with caplog.at_level(logging.WARNING):
            cliente._handle_connection_lost()
        assert not any(self.PISTA in r.message for r in caplog.records)

    def test_cualquier_byte_recibido_marca_la_sesion_como_hablada(self):
        cliente = InSimClient(config={}, name="Pista")
        assert not cliente._session_received_data
        with patch.object(cliente, "send"):  # el keep-alive reactivo no viene al caso
            cliente._on_raw_bytes(TINY_KEEPALIVE)  # cualquier dato de LFS cuenta
        assert cliente._session_received_data

    def test_restore_session_resetea_el_flag(self):
        # Cada sesión evalúa su propio silencio: la reconexión limpia el flag
        # ANTES de reenviar el ISI (la respuesta ya cuenta para la nueva).
        cliente = InSimClient(config={}, name="Pista")
        cliente._session_received_data = True
        with patch.object(cliente, "send"):
            cliente._restore_session()
        assert not cliente._session_received_data
