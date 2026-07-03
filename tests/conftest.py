"""
Fixtures compartidas de la suite (Fase 1; ampliadas en Fase 3).

FakeLFS: servidor TCP loopback que simula a LFS a nivel de transporte —
acepta conexiones sucesivas (una a la vez; las sucesivas permiten probar la
reconexión de P12), reproduce trazas de bytes hacia el cliente y registra
todo lo que el cliente le envía. No implementa lógica de protocolo: los
tests deciden qué bytes reproducir (p. ej. capturas reales o construidos
según la spec de docs/InSim.txt).
"""

import socket
import threading
import time

import pytest


class FakeLFS:
    """Servidor TCP loopback que simula a LFS (solo transporte).

    Uso típico en un test:
        connect_tcp_lfs(fake_lfs.host, fake_lfs.port)
        fake_lfs.enviar(traza_bytes)     # LFS → cliente
        fake_lfs.recibido                # bytes cliente → LFS
        fake_lfs.cerrar_conexion()       # simula la caída de LFS
        fake_lfs.espera_conexiones(2)    # el cliente reconectó (P12)
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
        self.conexiones = 0  # nº de conexiones aceptadas hasta ahora
        self._hilo = threading.Thread(target=self._atender, name="FakeLFS", daemon=True)
        self._hilo.start()

    def _atender(self):
        """Acepta conexiones sucesivas y acumula en `recibido` lo que envíe
        el cliente. Cuando una conexión cae, vuelve a aceptar la siguiente
        (permite probar la reconexión de P12)."""
        while True:
            try:
                conn, _ = self._server.accept()
            except OSError:
                return  # el servidor se paró
            with self._lock:
                self._conn = conn
                self.conexiones += 1
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

    def espera_conexiones(self, n: int, timeout: float = 2.0) -> bool:
        """Espera a que se hayan aceptado al menos `n` conexiones (la
        segunda en adelante son reconexiones). Devuelve False si expira."""
        limite = time.monotonic() + timeout
        while time.monotonic() < limite:
            with self._lock:
                if self.conexiones >= n:
                    return True
            time.sleep(0.005)
        with self._lock:
            return self.conexiones >= n

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
