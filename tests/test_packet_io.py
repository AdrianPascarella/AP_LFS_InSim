"""
Tests de caracterización de insim_packet_io (Fase 1).

Cubre la capa de red sin LFS real:
  - `_tcp_listen_loop` con socket guionizado: reensamblado del flujo TCP
    (paquetes fragmentados y pegados), byte Size=0, cierre de conexión,
    errores de recv y STOP_EVENT;
  - `_udp_listen_loop` con socket guionizado: un datagrama = un paquete;
  - `stop_all_threads`: cierre de sockets y reseteo del estado global;
  - `connect_tcp_lfs` / `connect_udp_lfs`: fallo de conexión e integración
    real por loopback contra la fixture `fake_lfs` (conftest.py).

El filtro pre-decode de `_process_raw_bytes` ya está cubierto en
test_active_packet_registry.py.

Comportamientos actuales que se CARACTERIZAN tal cual:
  - un byte Size=0 se descarta de uno en uno (resincronización byte a byte);
  - un resto incompleto en el buffer al cerrar la conexión se pierde en
    silencio (nunca se procesa);
  - una excepción en recv termina el hilo sin propagar (no hay reconexión —
    ver P12 en DIAGNOSTICO.md).
"""
import socket
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

import lfs_insim.insim_packet_io as io
import lfs_insim.insim_state as state
from lfs_insim.exceptions import InSimConnectionError
from lfs_insim.insim_enums import ISP
from lfs_insim.insim_packet_io import (
    _tcp_listen_loop,
    _udp_listen_loop,
    connect_tcp_lfs,
    connect_udp_lfs,
    stop_all_threads,
)
from lfs_insim.packets import ISP_TINY, ISP_VER


# Paquetes reales mínimos para las trazas (mismos bytes que los golden-decode).
TINY = bytes([1, ISP.TINY, 0, 0])
VER = (
    bytes([5, ISP.VER, 1, 0])
    + b'0.8C5'.ljust(8, b'\x00')   # Version[8]
    + b'S3'.ljust(6, b'\x00')      # Product[6]
    + bytes([10, 0])               # InSimVer, Spare
)


@pytest.fixture(autouse=True)
def _entorno_limpio():
    """Estado global y STOP_EVENT limpios antes y después de cada test."""
    state.reset_insim_client()
    state.reset_sockets()
    io.STOP_EVENT.clear()
    yield
    stop_all_threads()   # cierra sockets/hilos que un test dejara vivos
    state.reset_insim_client()


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
            return b''
        paso = self._guion.pop(0)
        if isinstance(paso, BaseException):
            raise paso
        return paso


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


def _correr_tcp(*guion):
    """Ejecuta _tcp_listen_loop con un guion y devuelve (procesados, socket)."""
    sock = _SocketTcpGuionizado(*guion)
    procesados = []
    with patch.object(io, '_process_raw_bytes', side_effect=procesados.append):
        _tcp_listen_loop(sock)
    return procesados, sock


def _correr_udp(*guion):
    sock = _SocketUdpGuionizado(*guion)
    procesados = []
    with patch.object(io, '_process_raw_bytes', side_effect=procesados.append):
        _udp_listen_loop(sock)
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
        procesados, _ = _correr_tcp(*(VER[i:i + 1] for i in range(len(VER))))
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
        procesados, _ = _correr_tcp(b'\x00' + TINY)
        assert procesados == [TINY]

    def test_varios_ceros_seguidos(self):
        procesados, _ = _correr_tcp(b'\x00\x00\x00' + TINY)
        assert procesados == [TINY]

    def test_solo_ceros_no_procesa_nada(self):
        procesados, _ = _correr_tcp(b'\x00\x00')
        assert procesados == []


class TestCierreYErrores:

    def test_recv_vacio_termina_el_bucle(self):
        procesados, sock = _correr_tcp(TINY)
        assert procesados == [TINY]
        assert sock.llamadas == 2   # el segundo recv devuelve b'' y corta

    def test_resto_incompleto_al_cerrar_se_pierde(self):
        # Solo llegan 4 de los 20 bytes de VER antes del cierre.
        procesados, _ = _correr_tcp(VER[:4])
        assert procesados == []

    def test_excepcion_en_recv_termina_sin_propagar(self):
        procesados, _ = _correr_tcp(TINY, ConnectionResetError("boom"))
        assert procesados == [TINY]

    def test_stop_event_previo_impide_leer(self):
        io.STOP_EVENT.set()
        procesados, sock = _correr_tcp(TINY)
        assert procesados == []
        assert sock.llamadas == 0


# ---------------------------------------------------------------------------
# Bucle UDP
# ---------------------------------------------------------------------------

class TestBucleUDP:

    def test_cada_datagrama_es_un_paquete(self):
        # UDP no reensambla: cada datagrama se procesa tal cual llega.
        assert _correr_udp(TINY, VER) == [TINY, VER]

    def test_datagrama_vacio_se_ignora_sin_cortar(self):
        assert _correr_udp(b'', TINY) == [TINY]

    def test_excepcion_termina_sin_propagar(self):
        assert _correr_udp(OSError("boom")) == []


# ---------------------------------------------------------------------------
# stop_all_threads
# ---------------------------------------------------------------------------

class TestStopAllThreads:

    def test_sin_sockets_no_falla_y_deja_el_evento_limpio(self):
        stop_all_threads()
        assert not io.STOP_EVENT.is_set()

    def test_cierra_y_resetea_ambos_sockets(self):
        tcp, udp = MagicMock(), MagicMock()
        state.set_socket_tcp(tcp)
        state.set_socket_udp(udp)

        stop_all_threads()

        tcp.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        tcp.close.assert_called_once()
        udp.close.assert_called_once()
        assert state.get_socket_tcp() is None
        assert state.get_socket_udp() is None

    def test_errores_al_cerrar_se_tragan(self):
        tcp = MagicMock()
        tcp.shutdown.side_effect = OSError("ya cerrado")
        udp = MagicMock()
        udp.close.side_effect = OSError("ya cerrado")
        state.set_socket_tcp(tcp)
        state.set_socket_udp(udp)

        stop_all_threads()   # no debe propagar

        assert state.get_socket_tcp() is None
        assert state.get_socket_udp() is None


# ---------------------------------------------------------------------------
# Fallos de conexión
# ---------------------------------------------------------------------------

class TestConexionFallida:

    def test_tcp_puerto_cerrado_lanza_insim_connection_error(self):
        # Reservar y soltar un puerto efímero: queda cerrado con casi total certeza.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
        s.close()

        with pytest.raises(InSimConnectionError):
            connect_tcp_lfs("127.0.0.1", puerto)

    def test_udp_puerto_ocupado_lanza_insim_connection_error(self):
        ocupado = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ocupado.bind(("127.0.0.1", 0))
        puerto = ocupado.getsockname()[1]
        try:
            with pytest.raises(InSimConnectionError):
                connect_udp_lfs("127.0.0.1", puerto)
        finally:
            ocupado.close()


# ---------------------------------------------------------------------------
# Integración por loopback con el "LFS falso" (fixture fake_lfs)
# ---------------------------------------------------------------------------

class _ClienteStub:
    """Cliente mínimo: acumula los paquetes decodificados que le entregan.

    Sin `_active_type_ids`, así que la barrera pre-decode deja pasar todo.
    """

    def __init__(self):
        self.paquetes = []

    def on_packet_received(self, packet):
        self.paquetes.append(packet)


def _hilo_receptor_tcp():
    return next(
        (t for t in threading.enumerate() if t.name == "InSim_TCP_Receiver"),
        None,
    )


class TestIntegracionConLFSFalso:

    def test_conectar_registra_socket_y_arranca_el_hilo(self, fake_lfs):
        connect_tcp_lfs(fake_lfs.host, fake_lfs.port)

        assert fake_lfs.espera_conexion()
        assert state.get_socket_tcp() is not None
        hilo = _hilo_receptor_tcp()
        assert hilo is not None and hilo.is_alive()

    def test_traza_completa_llega_decodificada(self, fake_lfs):
        stub = _ClienteStub()
        state.force_set_insim_client(stub)
        connect_tcp_lfs(fake_lfs.host, fake_lfs.port)

        fake_lfs.enviar(VER)

        assert _esperar(lambda: len(stub.paquetes) == 1)
        pkt = stub.paquetes[0]
        assert isinstance(pkt, ISP_VER)
        assert pkt.Version == '0.8C5'

    def test_traza_fragmentada_se_reensambla(self, fake_lfs):
        stub = _ClienteStub()
        state.force_set_insim_client(stub)
        connect_tcp_lfs(fake_lfs.host, fake_lfs.port)

        fake_lfs.enviar(VER[:6])
        time.sleep(0.05)   # forzar que llegue en dos recv distintos
        fake_lfs.enviar(VER[6:] + TINY)

        assert _esperar(lambda: len(stub.paquetes) == 2)
        assert isinstance(stub.paquetes[0], ISP_VER)
        assert isinstance(stub.paquetes[1], ISP_TINY)

    def test_el_lfs_falso_registra_lo_que_envia_el_cliente(self, fake_lfs):
        connect_tcp_lfs(fake_lfs.host, fake_lfs.port)
        assert fake_lfs.espera_conexion()

        state.get_socket_tcp().sendall(TINY)

        assert _esperar(lambda: fake_lfs.recibido == TINY)

    def test_caida_de_lfs_termina_el_hilo_receptor(self, fake_lfs):
        connect_tcp_lfs(fake_lfs.host, fake_lfs.port)
        assert fake_lfs.espera_conexion()
        hilo = _hilo_receptor_tcp()
        assert hilo is not None and hilo.is_alive()

        fake_lfs.cerrar_conexion()

        hilo.join(2.0)
        assert not hilo.is_alive()   # y NO se reconecta (P12)

    def test_stop_all_threads_termina_el_hilo_y_resetea(self, fake_lfs):
        connect_tcp_lfs(fake_lfs.host, fake_lfs.port)
        assert fake_lfs.espera_conexion()
        hilo = _hilo_receptor_tcp()

        stop_all_threads()

        hilo.join(2.0)
        assert not hilo.is_alive()
        assert state.get_socket_tcp() is None

    def test_udp_datagrama_llega_decodificado(self):
        stub = _ClienteStub()
        state.force_set_insim_client(stub)
        connect_udp_lfs("127.0.0.1", 0)   # puerto efímero
        puerto = state.get_socket_udp().getsockname()[1]

        emisor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            emisor.sendto(TINY, ("127.0.0.1", puerto))
            assert _esperar(lambda: len(stub.paquetes) == 1)
            assert isinstance(stub.paquetes[0], ISP_TINY)
        finally:
            emisor.close()
