"""
lfs_insim/insim_transport.py - Network transport layer.

One InSimTransport owns the sockets and receiver threads of ONE connection
to LFS (TCP for InSim, optional UDP for OutSim/OutGauge or NLP/MCI). It
reassembles the TCP byte stream into individual packets and hands every raw
packet to the `on_raw` callback (set by the owning InSimClient).

Sending is always TCP — LFS only accepts InSim packets on the TCP
connection; the UDP socket is receive-only.

Several transports can coexist in the same process: all state (sockets,
stop event, send lock) is per-instance — there are no module globals.
"""

import socket
import logging
import threading
from typing import Callable, Optional

from .exceptions import InSimConnectionError

logger = logging.getLogger(__name__)


class InSimTransport:
    """Sockets + receiver threads for a single LFS connection."""

    def __init__(self, on_raw: Optional[Callable[[bytes], None]] = None):
        # Callback that receives every raw packet (bytes). The owning
        # InSimClient assigns it; tests can plug a recorder here.
        self.on_raw = on_raw

        # Callback invoked (from the dying receiver thread) when the TCP
        # connection is lost UNEXPECTEDLY — i.e. the receive loop ends
        # without close() having been called. The owning InSimClient uses
        # it to drive reconnection (P12).
        self.on_connection_lost: Optional[Callable[[], None]] = None

        self._tcp_sock: Optional[socket.socket] = None
        self._udp_sock: Optional[socket.socket] = None
        self._stop = threading.Event()
        self._send_lock = threading.Lock()
        self._tcp_thread: Optional[threading.Thread] = None
        self._udp_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ #
    # Connection
    # ------------------------------------------------------------------ #

    def connect_tcp(self, host: str, port: int) -> None:
        """Open the main TCP connection with LFS and start the receiver.

        Reconnecting over a dead connection is allowed: any previous TCP
        socket is closed and replaced.
        """
        if self._tcp_sock is not None:
            try:
                self._tcp_sock.close()
            except OSError:
                pass
            self._tcp_sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((host, port))
            sock.settimeout(None)  # back to blocking mode for the thread

            self._tcp_sock = sock

            self._tcp_thread = threading.Thread(
                target=self._tcp_listen_loop,
                args=(sock,),
                name="InSim_TCP_Receiver",
                daemon=True
            )
            self._tcp_thread.start()
            logger.info(f"Connected to LFS via TCP at {host}:{port}")
        except Exception as e:
            raise InSimConnectionError(f"Could not connect to LFS (TCP): {e}")

    def connect_udp(self, host: str, port: int, buffer_size: int = 4096) -> None:
        """Bind the UDP socket (OutSim/OutGauge) and start the receiver."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((host, port))
            self._udp_sock = sock

            self._udp_thread = threading.Thread(
                target=self._udp_listen_loop,
                args=(sock, buffer_size),
                name="InSim_UDP_Receiver",
                daemon=True
            )
            self._udp_thread.start()
            logger.info(f"Listening for OutSim via UDP on port {port}")
        except Exception as e:
            raise InSimConnectionError(f"Could not open UDP port {port}: {e}")

    # ------------------------------------------------------------------ #
    # Sending
    # ------------------------------------------------------------------ #

    def send(self, data: bytes) -> bool:
        """Send raw bytes to LFS over TCP (thread-safe).

        Sending is always TCP: LFS only accepts InSim packets on the TCP
        connection. The UDP socket is receive-only (OutSim/OutGauge frames
        or NLP/MCI when `UDPPort` is set in the ISI).
        """
        sock = self._tcp_sock
        if sock is None:
            raise InSimConnectionError("Could not send: socket not available (disconnected?)", host=None, port=None)
        try:
            with self._send_lock:
                sock.sendall(data)
            return True
        except Exception as e:
            raise InSimConnectionError(f"Network error while sending: {e}") from e

    # ------------------------------------------------------------------ #
    # Receiver loops
    # ------------------------------------------------------------------ #

    def _tcp_listen_loop(self, sock: socket.socket):
        """TCP receive loop with packet reassembly."""
        buffer = bytearray()

        while not self._stop.is_set():
            try:
                data = sock.recv(4096)
                if not data:
                    logger.warning("Connection closed by LFS.")
                    break

                buffer.extend(data)

                # Process every complete packet in the buffer
                while len(buffer) >= 1:
                    # In InSim the first byte is the total size / 4.
                    # A zero first byte is a protocol error: drop it and resync.
                    size_byte = buffer[0]
                    if size_byte == 0:
                        buffer.pop(0)
                        continue

                    packet_len = size_byte * 4

                    if len(buffer) < packet_len:
                        # Incomplete packet: wait for more data
                        break

                    # Extract the complete packet
                    raw_packet = bytes(buffer[:packet_len])
                    del buffer[:packet_len]

                    self._deliver(raw_packet)

            except Exception as e:
                if not self._stop.is_set():
                    logger.error(f"Error in TCP thread: {e}")
                break

        logger.debug("TCP thread finished.")

        # Unexpected end of the receive loop (LFS closed or network error):
        # let the owner know so it can reconnect. A deliberate close() sets
        # _stop first and must NOT trigger this.
        if not self._stop.is_set():
            self._notify_connection_lost()

    def _udp_listen_loop(self, sock: socket.socket, buffer_size: int = 4096):
        """UDP receive loop (OutSim/OutGauge frames need no reassembly)."""
        while not self._stop.is_set():
            try:
                data, _ = sock.recvfrom(buffer_size)
                if data:
                    self._deliver(data)
            except Exception as e:
                if not self._stop.is_set():
                    logger.error(f"Error in UDP thread: {e}")
                break

    def _deliver(self, data: bytes):
        """Hand a raw packet to the callback, isolating its errors."""
        if self.on_raw is None:
            return
        try:
            self.on_raw(data)
        except Exception as e:
            logger.error(f"Error handling packet: {e}", exc_info=True)

    def _notify_connection_lost(self):
        """Invoke the connection-lost callback, isolating its errors."""
        if self.on_connection_lost is None:
            return
        try:
            self.on_connection_lost()
        except Exception as e:
            logger.error(f"Error in connection-lost callback: {e}", exc_info=True)

    # ------------------------------------------------------------------ #
    # Shutdown
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Stop the receiver threads and close both sockets.

        The transport is reusable afterwards (connect_* can be called again).
        """
        self._stop.set()

        if self._tcp_sock:
            try:
                self._tcp_sock.shutdown(socket.SHUT_RDWR)
                self._tcp_sock.close()
            except Exception:
                pass

        if self._udp_sock:
            try:
                self._udp_sock.close()
            except Exception:
                pass

        self._tcp_sock = None
        self._udp_sock = None
        self._stop.clear()
