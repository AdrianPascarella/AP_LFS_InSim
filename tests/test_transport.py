"""
Tests de InSimTransport (Fase 2 — P13; sucesor de test_packet_io.py).

Cubre la capa de red sin LFS real:
  - `_tcp_listen_loop` con socket guionizado: reensamblado del flujo TCP
    (paquetes fragmentados y pegados), byte Size=0, cierre de conexión,
    errores de recv y stop event;
  - `_udp_listen_loop` con socket guionizado: un datagrama = un paquete;
  - `close()`: cierre de sockets por instancia (sin estado global); cierre
    determinista — espera a los receptores y un cierre deliberado nunca
    dispara `on_connection_lost` (carrera detectada en S11);
  - `connect_tcp` / `connect_udp`: fallo de conexión e integración real por
    loopback contra la fixture `fake_lfs` (conftest.py);
  - **criterio de aceptación de Fase 2 (P13): dos clientes coexisten en un
    mismo proceso**, cada uno con su transporte, recepción y envío propios.

La barrera pre-decode (ahora en `InSimClient._on_raw_bytes`) está cubierta
en test_active_packet_registry.py.

Comportamientos que se conservan de la caracterización de Fase 1:
  - un byte Size=0 se descarta de uno en uno (resincronización byte a byte);
  - un resto incompleto en el buffer al cerrar la conexión se pierde en
    silencio;
  - una excepción en recv termina el hilo sin propagar (no hay reconexión —
    ver P12 en DIAGNOSTICO.md).
"""

import socket
import threading
import time
from unittest.mock import MagicMock

import pytest

import lfs_insim.insim_state as state
from lfs_insim.exceptions import InSimConnectionError
from lfs_insim.insim_client import InSimClient
from lfs_insim.insim_enums import ISP
from lfs_insim.insim_transport import InSimTransport
from lfs_insim.packets import ISP_TINY, ISP_VER

# Paquetes reales mínimos para las trazas (mismos bytes que los golden-decode).
TINY = bytes([1, ISP.TINY, 0, 0])
VER = (
    bytes([5, ISP.VER, 1, 0])
    + b"0.8C5".ljust(8, b"\x00")  # Version[8]
    + b"S3".ljust(6, b"\x00")  # Product[6]
    + bytes([10, 0])  # InSimVer, Spare
)


@pytest.fixture(autouse=True)
def _cliente_por_defecto_limpio():
    state.reset_insim_client()
    yield
    state.reset_insim_client()


class _ClienteRecolector(InSimClient):
    """Cliente que acumula los paquetes decodificados que recibe."""

    def __init__(self, name="Recolector"):
        super().__init__(config={}, name=name)
        self.paquetes = []

    def on_packet_received(self, packet):
        self.paquetes.append(packet)


@pytest.fixture
def cliente_factory():
    """Crea clientes recolectores y cierra sus transportes al terminar."""
    clientes = []

    def crear(name="Recolector") -> _ClienteRecolector:
        c = _ClienteRecolector(name)
        clientes.append(c)
        return c

    yield crear
    for c in clientes:
        c.transport.close()


class _SocketTcpGuionizado:
    """Socket falso: cada recv() devuelve el siguiente trozo del guion.

    Un elemento Exception se lanza en vez de devolverse; agotado el guion,
    recv() devuelve b'' (LFS cierra la conexión).
    """

    def __init__(self, *guion):
        self._guion = list(guion)
        self.llamadas = 0

    def recv(self, bufsize):
        self.llamadas += 1
        if not self._guion:
            return b""
        paso = self._guion.pop(0)
        if isinstance(paso, BaseException):
            raise paso
        return paso


class _SocketTcpBloqueante:
    """Socket falso que bloquea en recv() hasta que se cierra, y que tras el
    cierre tarda `retardo` en despertar (simula el jitter del SO al despertar
    un recv bloqueado — la ventana exacta de la carrera de S11)."""

    def __init__(self, retardo=0.05):
        self._cerrado = threading.Event()
        self._retardo = retardo

    def recv(self, bufsize):
        self._cerrado.wait(2.0)
        time.sleep(self._retardo)
        raise OSError("socket cerrado")

    def shutdown(self, how):
        pass

    def close(self):
        self._cerrado.set()


class _SocketUdpGuionizado:
    """Socket UDP falso: cada recvfrom() devuelve el siguiente datagrama.

    Agotado el guion lanza OSError (equivale a cerrar el socket).
    """

    def __init__(self, *guion):
        self._guion = list(guion)

    def recvfrom(self, bufsize):
        if not self._guion:
            raise OSError("fin del guion")
        paso = self._guion.pop(0)
        if isinstance(paso, BaseException):
            raise paso
        return paso, ("127.0.0.1", 30000)


def _correr_tcp(*guion, stop_previo=False):
    """Ejecuta _tcp_listen_loop con un guion y devuelve (procesados, socket)."""
    sock = _SocketTcpGuionizado(*guion)
    procesados = []
    transporte = InSimTransport(on_raw=procesados.append)
    if stop_previo:
        transporte._stop.set()
    transporte._tcp_listen_loop(sock)
    return procesados, sock


def _correr_udp(*guion):
    sock = _SocketUdpGuionizado(*guion)
    procesados = []
    transporte = InSimTransport(on_raw=procesados.append)
    transporte._udp_listen_loop(sock)
    return procesados


def _esperar(condicion, timeout=2.0):
    """Espera activa a que `condicion()` sea verdadera (para hilos reales)."""
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.005)
    return condicion()


# ---------------------------------------------------------------------------
# Reensamblado del flujo TCP
# ---------------------------------------------------------------------------


class TestReensambladoTCP:
    def test_paquete_completo_en_un_recv(self):
        procesados, _ = _correr_tcp(TINY)
        assert procesados == [TINY]

    def test_dos_paquetes_pegados_en_un_recv(self):
        procesados, _ = _correr_tcp(TINY + VER)
        assert procesados == [TINY, VER]

    def test_paquete_fragmentado_en_dos_recv(self):
        procesados, _ = _correr_tcp(VER[:10], VER[10:])
        assert procesados == [VER]

    def test_paquete_fragmentado_byte_a_byte(self):
        procesados, _ = _correr_tcp(*(VER[i : i + 1] for i in range(len(VER))))
        assert procesados == [VER]

    def test_pegado_mas_fragmento_del_siguiente(self):
        # Un recv trae TINY completo + el principio de VER; el resto después.
        procesados, _ = _correr_tcp(TINY + VER[:7], VER[7:])
        assert procesados == [TINY, VER]

    def test_rafaga_de_muchos_paquetes_pegados(self):
        procesados, _ = _correr_tcp(TINY * 10)
        assert procesados == [TINY] * 10


class TestByteSizeCero:
    def test_byte_cero_se_descarta_y_resincroniza(self):
        procesados, _ = _correr_tcp(b"\x00" + TINY)
        assert procesados == [TINY]

    def test_varios_ceros_seguidos(self):
        procesados, _ = _correr_tcp(b"\x00\x00\x00" + TINY)
        assert procesados == [TINY]

    def test_solo_ceros_no_procesa_nada(self):
        procesados, _ = _correr_tcp(b"\x00\x00")
        assert procesados == []


class TestCierreYErrores:
    def test_recv_vacio_termina_el_bucle(self):
        procesados, sock = _correr_tcp(TINY)
        assert procesados == [TINY]
        assert sock.llamadas == 2  # el segundo recv devuelve b'' y corta

    def test_resto_incompleto_al_cerrar_se_pierde(self):
        # Solo llegan 4 de los 20 bytes de VER antes del cierre.
        procesados, _ = _correr_tcp(VER[:4])
        assert procesados == []

    def test_excepcion_en_recv_termina_sin_propagar(self):
        procesados, _ = _correr_tcp(TINY, ConnectionResetError("boom"))
        assert procesados == [TINY]

    def test_stop_previo_impide_leer(self):
        procesados, sock = _correr_tcp(TINY, stop_previo=True)
        assert procesados == []
        assert sock.llamadas == 0

    def test_callback_ausente_no_revienta(self):
        transporte = InSimTransport()  # sin on_raw
        transporte._tcp_listen_loop(_SocketTcpGuionizado(TINY))

    def test_error_del_callback_no_corta_el_bucle(self):
        recibidos = []

        def explota_una_vez(data):
            if not recibidos:
                recibidos.append("boom")
                raise ValueError("boom")
            recibidos.append(data)

        transporte = InSimTransport(on_raw=explota_una_vez)
        transporte._tcp_listen_loop(_SocketTcpGuionizado(TINY + VER))

        assert recibidos == ["boom", VER]


# ---------------------------------------------------------------------------
# Bucle UDP
# ---------------------------------------------------------------------------


class TestBucleUDP:
    def test_cada_datagrama_es_un_paquete(self):
        # UDP no reensambla: cada datagrama se procesa tal cual llega.
        assert _correr_udp(TINY, VER) == [TINY, VER]

    def test_datagrama_vacio_se_ignora_sin_cortar(self):
        assert _correr_udp(b"", TINY) == [TINY]

    def test_excepcion_termina_sin_propagar(self):
        assert _correr_udp(OSError("boom")) == []


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------


class TestClose:
    def test_sin_sockets_no_falla_y_deja_el_stop_limpio(self):
        transporte = InSimTransport()
        transporte.close()
        assert not transporte._stop.is_set()

    def test_cierra_y_resetea_ambos_sockets(self):
        transporte = InSimTransport()
        tcp, udp = MagicMock(), MagicMock()
        transporte._tcp_sock, transporte._udp_sock = tcp, udp

        transporte.close()

        tcp.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        tcp.close.assert_called_once()
        udp.close.assert_called_once()
        assert transporte._tcp_sock is None
        assert transporte._udp_sock is None

    def test_errores_al_cerrar_se_tragan(self):
        transporte = InSimTransport()
        tcp = MagicMock()
        tcp.shutdown.side_effect = OSError("ya cerrado")
        udp = MagicMock()
        udp.close.side_effect = OSError("ya cerrado")
        transporte._tcp_sock, transporte._udp_sock = tcp, udp

        transporte.close()  # no debe propagar

        assert transporte._tcp_sock is None
        assert transporte._udp_sock is None

    def test_close_espera_a_los_receptores_y_no_avisa_connection_lost(self):
        # Carrera S11: close() re-armaba _stop sin esperar a los receptores;
        # un receptor que despertara TARDE por el socket cerrado veía el
        # evento ya limpio → log de error falso + on_connection_lost espurio
        # (posible intento de reconexión tras un cierre deliberado).
        transporte = InSimTransport()
        avisos = []
        transporte.on_connection_lost = lambda: avisos.append("perdida")

        sock = _SocketTcpBloqueante()
        transporte._tcp_sock = sock
        hilo = threading.Thread(
            target=transporte._tcp_listen_loop, args=(sock,), daemon=True
        )
        transporte._tcp_thread = hilo
        hilo.start()

        transporte.close()

        assert not hilo.is_alive(), "close() debe esperar a que el receptor salga"
        assert avisos == [], "un cierre deliberado no debe disparar on_connection_lost"
        assert not transporte._stop.is_set()  # transporte re-armado (reutilizable)

    def test_close_desde_el_propio_hilo_receptor_no_bloquea_ni_avisa(self):
        # Un callback puede cerrar el transporte desde el hilo receptor:
        # close() no puede hacer join de sí mismo, pero el bucle debe salir
        # limpio (sin releer) y sin aviso espurio.
        transporte = InSimTransport()
        avisos = []
        transporte.on_connection_lost = lambda: avisos.append("perdida")
        transporte.on_raw = lambda data: transporte.close()

        sock = _SocketTcpGuionizado(TINY, VER)
        hilo = threading.Thread(
            target=transporte._tcp_listen_loop, args=(sock,), daemon=True
        )
        transporte._tcp_thread = hilo
        hilo.start()

        hilo.join(2.0)
        assert not hilo.is_alive()
        assert sock.llamadas == 1  # tras close() el bucle no vuelve a leer
        assert avisos == []


# ---------------------------------------------------------------------------
# Fallos de conexión y envío
# ---------------------------------------------------------------------------


class TestConexionFallida:
    def test_tcp_puerto_cerrado_lanza_insim_connection_error(self):
        # Reservar y soltar un puerto efímero: queda cerrado con casi total certeza.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
        s.close()

        with pytest.raises(InSimConnectionError):
            InSimTransport().connect_tcp("127.0.0.1", puerto)

    def test_udp_puerto_ocupado_lanza_insim_connection_error(self):
        ocupado = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ocupado.bind(("127.0.0.1", 0))
        puerto = ocupado.getsockname()[1]
        try:
            with pytest.raises(InSimConnectionError):
                InSimTransport().connect_udp("127.0.0.1", puerto)
        finally:
            ocupado.close()

    def test_enviar_sin_conectar_lanza_insim_connection_error(self):
        with pytest.raises(InSimConnectionError):
            InSimTransport().send(TINY)

    def test_enviar_es_siempre_tcp_aunque_haya_socket_udp(self):
        # P18: el envío UDP se eliminó — LFS solo recibe InSim por TCP y el
        # socket UDP es solo de escucha. Sin TCP, send falla aunque haya UDP.
        transporte = InSimTransport()
        transporte._udp_sock = MagicMock()
        try:
            with pytest.raises(InSimConnectionError):
                transporte.send(TINY)
            transporte._udp_sock.sendall.assert_not_called()
        finally:
            transporte._udp_sock = None


# ---------------------------------------------------------------------------
# Integración por loopback con el "LFS falso" (fixtures de conftest.py)
# ---------------------------------------------------------------------------


class TestIntegracionConLFSFalso:
    def test_conectar_guarda_socket_y_arranca_el_hilo(self, fake_lfs, cliente_factory):
        c = cliente_factory()
        c.transport.connect_tcp(fake_lfs.host, fake_lfs.port)

        assert fake_lfs.espera_conexion()
        assert c.transport._tcp_sock is not None
        assert c.transport._tcp_thread.is_alive()

    def test_traza_completa_llega_decodificada(self, fake_lfs, cliente_factory):
        c = cliente_factory()
        c.transport.connect_tcp(fake_lfs.host, fake_lfs.port)

        fake_lfs.enviar(VER)

        assert _esperar(lambda: len(c.paquetes) == 1)
        pkt = c.paquetes[0]
        assert isinstance(pkt, ISP_VER)
        assert pkt.Version == "0.8C5"

    def test_traza_fragmentada_se_reensambla(self, fake_lfs, cliente_factory):
        c = cliente_factory()
        c.transport.connect_tcp(fake_lfs.host, fake_lfs.port)

        fake_lfs.enviar(VER[:6])
        time.sleep(0.05)  # forzar que llegue en dos recv distintos
        fake_lfs.enviar(VER[6:] + TINY)

        assert _esperar(lambda: len(c.paquetes) == 2)
        assert isinstance(c.paquetes[0], ISP_VER)
        assert isinstance(c.paquetes[1], ISP_TINY)

    def test_client_send_llega_al_lfs_falso(self, fake_lfs, cliente_factory):
        # Ruta completa de envío P13: client.send → encode_packet → transport
        c = cliente_factory()
        c.transport.connect_tcp(fake_lfs.host, fake_lfs.port)
        assert fake_lfs.espera_conexion()

        c.send(ISP_TINY())

        assert _esperar(lambda: fake_lfs.recibido == TINY)

    def test_caida_de_lfs_termina_el_hilo_receptor(self, fake_lfs, cliente_factory):
        c = cliente_factory()
        c.transport.connect_tcp(fake_lfs.host, fake_lfs.port)
        assert fake_lfs.espera_conexion()
        hilo = c.transport._tcp_thread
        assert hilo.is_alive()

        fake_lfs.cerrar_conexion()

        hilo.join(2.0)
        assert not hilo.is_alive()  # y NO se reconecta (P12)

    def test_close_termina_el_hilo_y_limpia(self, fake_lfs, cliente_factory):
        c = cliente_factory()
        c.transport.connect_tcp(fake_lfs.host, fake_lfs.port)
        assert fake_lfs.espera_conexion()
        hilo = c.transport._tcp_thread

        c.transport.close()

        hilo.join(2.0)
        assert not hilo.is_alive()
        assert c.transport._tcp_sock is None

    def test_transporte_reutilizable_tras_close(self, fake_lfs, cliente_factory):
        # Invariante del docstring de close(): el transporte queda re-armado
        # y una conexión posterior recibe con normalidad.
        c = cliente_factory()
        c.transport.connect_tcp(fake_lfs.host, fake_lfs.port)
        assert fake_lfs.espera_conexion()
        c.transport.close()

        c.transport.connect_tcp(fake_lfs.host, fake_lfs.port)
        assert fake_lfs.espera_conexiones(2)
        fake_lfs.enviar(VER)

        assert _esperar(lambda: len(c.paquetes) == 1)
        assert isinstance(c.paquetes[0], ISP_VER)

    def test_udp_datagrama_llega_decodificado(self, cliente_factory):
        c = cliente_factory()
        c.transport.connect_udp("127.0.0.1", 0)  # puerto efímero
        puerto = c.transport._udp_sock.getsockname()[1]

        emisor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            emisor.sendto(TINY, ("127.0.0.1", puerto))
            assert _esperar(lambda: len(c.paquetes) == 1)
            assert isinstance(c.paquetes[0], ISP_TINY)
        finally:
            emisor.close()


class TestDosClientesCoexisten:
    """Criterio de aceptación de Fase 2 (P13): cero estado global obligatorio."""

    def test_cada_cliente_recibe_y_envia_solo_lo_suyo(
        self, fake_lfs_factory, cliente_factory
    ):
        lfs_a, lfs_b = fake_lfs_factory(), fake_lfs_factory()
        a, b = cliente_factory("A"), cliente_factory("B")

        a.transport.connect_tcp(lfs_a.host, lfs_a.port)
        b.transport.connect_tcp(lfs_b.host, lfs_b.port)
        assert lfs_a.espera_conexion() and lfs_b.espera_conexion()

        # Recepción independiente: cada LFS falso envía un paquete distinto
        lfs_a.enviar(VER)
        lfs_b.enviar(TINY)
        assert _esperar(lambda: len(a.paquetes) == 1 and len(b.paquetes) == 1)
        assert isinstance(a.paquetes[0], ISP_VER)
        assert isinstance(b.paquetes[0], ISP_TINY)
        assert len(a.paquetes) == 1 and len(b.paquetes) == 1  # sin cruces

        # Envío independiente: cada cliente escribe por SU transporte
        a.send(ISP_TINY())
        b.send(ISP_TINY(ReqI=7))
        assert _esperar(lambda: lfs_a.recibido == bytes([1, ISP.TINY, 0, 0]))
        assert _esperar(lambda: lfs_b.recibido == bytes([1, ISP.TINY, 7, 0]))

        # El cliente por defecto (azúcar para helpers) es el primero creado
        assert state.get_insim_client() is a
