"""
Fixtures compartidas de la suite (Fase 1).

FakeLFS: servidor TCP loopback que simula a LFS a nivel de transporte —
acepta una conexión, reproduce trazas de bytes hacia el cliente y registra
todo lo que el cliente le envía. No implementa lógica de protocolo: los
tests deciden qué bytes reproducir (p. ej. capturas reales o construidos
según la spec de docs/InSim.txt).
"""
import socket
import threading

import pytest


class FakeLFS:
    """Servidor TCP loopback que simula a LFS (solo transporte).

    Uso típico en un test:
        connect_tcp_lfs(fake_lfs.host, fake_lfs.port)
        fake_lfs.enviar(traza_bytes)     # LFS → cliente
        fake_lfs.recibido                # bytes cliente → LFS
        fake_lfs.cerrar_conexion()       # simula la caída de LFS
    """

    def __init__(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(1)
        self.host, self.port = self._server.getsockname()
        self._conn = None
        self._conectado = threading.Event()
        self._recibido = bytearray()
        self._lock = threading.Lock()
        self._hilo = threading.Thread(
            target=self._atender, name="FakeLFS", daemon=True
        )
        self._hilo.start()

    def _atender(self):
        """Acepta una conexión y acumula en `recibido` lo que envíe el cliente."""
        try:
            conn, _ = self._server.accept()
        except OSError:
            return  # el servidor se paró antes de que conectara nadie
        self._conn = conn
        self._conectado.set()
        while True:
            try:
                data = conn.recv(4096)
            except OSError:
                break
            if not data:
                break
            with self._lock:
                self._recibido.extend(data)

    # ---- API para los tests ----

    @property
    def recibido(self) -> bytes:
        """Bytes que el cliente ha enviado hasta ahora."""
        with self._lock:
            return bytes(self._recibido)

    def espera_conexion(self, timeout: float = 2.0) -> bool:
        """Espera a que el cliente conecte. Devuelve False si expira."""
        return self._conectado.wait(timeout)

    def enviar(self, data: bytes) -> None:
        """Envía bytes al cliente (reproduce una traza LFS → InSim)."""
        assert self.espera_conexion(), "ningún cliente conectado al FakeLFS"
        self._conn.sendall(data)

    def cerrar_conexion(self) -> None:
        """Cierra la conexión con el cliente (simula la caída de LFS)."""
        if self._conn is not None:
            try:
                self._conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._conn.close()

    def parar(self) -> None:
        """Apaga el servidor y libera recursos."""
        self.cerrar_conexion()
        try:
            self._server.close()
        except OSError:
            pass


@pytest.fixture
def fake_lfs_factory():
    """Factory de servidores "LFS falso" (permite varios en un mismo test)."""
    servidores = []

    def crear() -> FakeLFS:
        servidor = FakeLFS()
        servidores.append(servidor)
        return servidor

    yield crear
    for servidor in servidores:
        servidor.parar()


@pytest.fixture
def fake_lfs(fake_lfs_factory):
    """Servidor "LFS falso" por loopback, listo para aceptar una conexión."""
    return fake_lfs_factory()
