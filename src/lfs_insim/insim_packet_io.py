"""
lfs_insim/insim_packet_io.py - Capa de Comunicación de Red.

Maneja hilos de lectura TCP/UDP, mantiene la reconexión y fragmenta 
el flujo de bytes en paquetes individuales listos para ser procesados.
"""

import socket
import logging
import threading
import time
from typing import Optional

from .insim_packet_decoders import decode_packet
from .insim_state import (
    get_insim_client,
    set_socket_tcp,
    set_socket_udp,
    get_socket_tcp,
    get_socket_udp,
    reset_sockets,
)
from .exceptions import InSimConnectionError

logger = logging.getLogger(__name__)

# Eventos para control de parada de hilos
STOP_EVENT = threading.Event()

def connect_tcp_lfs(host: str, port: int):
    """Establece la conexión TCP principal con LFS."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((host, port))
        sock.settimeout(None) # Volver a modo bloqueante para el hilo
        
        set_socket_tcp(sock)
        
        # Iniciar hilo de escucha
        thread = threading.Thread(
            target=_tcp_listen_loop, 
            args=(sock,), 
            name="InSim_TCP_Receiver",
            daemon=True
        )
        thread.start()
        logger.info(f"Conectado a LFS vía TCP en {host}:{port}")
    except Exception as e:
        raise InSimConnectionError(f"No se pudo conectar a LFS (TCP): {e}")

def connect_udp_lfs(host: str, port: int, buffer_size: int = 4096):
    """Prepara el socket UDP para OutSim/OutGauge."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((host, port))
        set_socket_udp(sock)

        thread = threading.Thread(
            target=_udp_listen_loop,
            args=(sock, buffer_size),
            name="InSim_UDP_Receiver",
            daemon=True
        )
        thread.start()
        logger.info(f"Escuchando OutSim vía UDP en el puerto {port}")
    except Exception as e:
        raise InSimConnectionError(f"No se pudo abrir el puerto UDP {port}: {e}")

def _tcp_listen_loop(sock: socket.socket):
    """Bucle infinito de recepción TCP con reensamblado de paquetes."""
    buffer = bytearray()
    
    while not STOP_EVENT.is_set():
        try:
            data = sock.recv(4096)
            if not data:
                logger.warning("Conexión cerrada por LFS.")
                break
                
            buffer.extend(data)
            
            # Procesar todos los paquetes completos que haya en el buffer
            while len(buffer) >= 1:
                # En InSim, el primer byte indica el tamaño total / 4
                # Si el primer byte es 0, es un caso especial o error de protocolo
                size_byte = buffer[0]
                if size_byte == 0:
                    buffer.pop(0)
                    continue
                
                packet_len = size_byte * 4
                
                if len(buffer) < packet_len:
                    # Paquete incompleto, esperar a más datos
                    break
                
                # Extraer los bytes del paquete completo
                raw_packet = bytes(buffer[:packet_len])
                del buffer[:packet_len]
                
                _process_raw_bytes(raw_packet)
                
        except Exception as e:
            if not STOP_EVENT.is_set():
                logger.error(f"Error en hilo TCP: {e}")
            break

    logger.debug("Hilo TCP finalizado.")

def _udp_listen_loop(sock: socket.socket, buffer_size: int = 4096):
    """Bucle de recepción UDP (OutSim/OutGauge no requieren buffer de reensamblado)."""
    while not STOP_EVENT.is_set():
        try:
            data, _ = sock.recvfrom(buffer_size)
            if data:
                _process_raw_bytes(data)
        except Exception as e:
            if not STOP_EVENT.is_set():
                logger.error(f"Error en hilo UDP: {e}")
            break

def _process_raw_bytes(data: bytes):
    """Convierte bytes en objetos y los entrega al cliente orquestador."""
    try:
        client = get_insim_client()
        if client is None:
            return

        # Barrera pre-decode: omite struct.unpack + dataclass para tipos sin handler.
        # Solo aplica a paquetes InSim TCP (data[0]*4 == len(data)).
        # UDP OutSim/OutGauge no cumple esa firma y siempre pasa.
        active_ids = getattr(client, '_active_type_ids', None)
        if (active_ids is not None
                and len(data) >= 2
                and data[0] * 4 == len(data)
                and data[1] not in active_ids):
            return

        packet = decode_packet(data)
        if packet:
            client.on_packet_received(packet)
    except Exception as e:
        logger.error(f"Error decodificando paquete: {e}", exc_info=True)

def stop_all_threads():
    """Detiene todos los hilos y cierra sockets."""
    STOP_EVENT.set()

    tcp_sock = get_socket_tcp()
    if tcp_sock:
        try:
            tcp_sock.shutdown(socket.SHUT_RDWR)
            tcp_sock.close()
        except Exception:
            pass

    udp_sock = get_socket_udp()
    if udp_sock:
        try:
            udp_sock.close()
        except Exception:
            pass

    reset_sockets()
    STOP_EVENT.clear()