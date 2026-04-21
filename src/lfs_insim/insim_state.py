"""
lfs_insim/insim_state.py - Estado global compartido del framework.

Este módulo gestiona las referencias únicas a los sockets y al cliente principal
para que todos los módulos (InSimApps) compartan la misma conexión con LFS.
"""

import socket
from typing import TYPE_CHECKING, Optional
from .insim_enums import OSO

if TYPE_CHECKING:
    from .insim_client import InSimClient

# =============================================================================
# VARIABLES GLOBALES (Estado único compartido)
# =============================================================================

_insim_client: Optional['InSimClient'] = None
_socket_tcp: Optional[socket.socket] = None
_socket_udp: Optional[socket.socket] = None
_oso_opts: OSO = OSO.MAIN | OSO.TIME  # Configuración por defecto de OutSim


# =============================================================================
# GESTIÓN DEL CLIENTE (ORQUESTADOR)
# =============================================================================

def set_insim_client(client: 'InSimClient') -> None:
    """
    Registra el cliente InSim principal.
    
    IMPORTANTE: Solo el primer cliente que se instancia (el Master) se registra.
    Esto evita que las apps que actúan como dependencias sobrescriban al 
    orquestador principal.
    """
    global _insim_client
    if _insim_client is None:
        _insim_client = client


def get_insim_client() -> Optional['InSimClient']:
    """Obtiene la instancia del cliente que está gestionando el tráfico."""
    return _insim_client


def reset_insim_client() -> None:
    """Limpia el cliente registrado para permitir re-registro."""
    global _insim_client
    _insim_client = None


def force_set_insim_client(client: 'InSimClient') -> None:
    """Fuerza el registro de un cliente (usado por el Loader durante la carga)."""
    global _insim_client
    _insim_client = client


# =============================================================================
# GESTIÓN DE RED (SOCKETS)
# =============================================================================

def set_socket_tcp(sock: socket.socket) -> None:
    """Registra el socket TCP activo."""
    global _socket_tcp
    _socket_tcp = sock


def get_socket_tcp() -> Optional[socket.socket]:
    """Obtiene el socket TCP para envío de paquetes."""
    return _socket_tcp


def set_socket_udp(sock: socket.socket) -> None:
    """Registra el socket UDP activo (OutSim/OutGauge)."""
    global _socket_udp
    _socket_udp = sock


def get_socket_udp() -> Optional[socket.socket]:
    """Obtiene el socket UDP."""
    return _socket_udp


# =============================================================================
# CONFIGURACIÓN DINÁMICA
# =============================================================================

def set_oso_opts(opts: OSO) -> None:
    """Establece las opciones de OutSim para la decodificación dinámica."""
    global _oso_opts
    _oso_opts = opts


def get_oso_opts() -> OSO:
    """Retorna las opciones actuales de OutSim."""
    return _oso_opts