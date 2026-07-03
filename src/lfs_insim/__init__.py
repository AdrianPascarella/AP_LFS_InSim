"""
lfs_insim - Composable framework for the LFS InSim protocol.

Public API (P15) — recommended import points:
    lfs_insim              core classes, config, exceptions (this module)
    lfs_insim.packets      packet dataclasses (ISP_*, structures, OutSim)
    lfs_insim.insim_enums  protocol enums and constants (ISF, TINY, ...)
    lfs_insim.utils        helpers (commands, colors, PID, geometry)
"""

# Single source of version: pyproject.toml reads it from here (dynamic).
__version__ = "0.2.0"

from .config import DEFAULT_CONFIG, build_config
from .insim_client import InSimClient
from .insim_app import InSimApp
from .insim_loader import InSimLoader
from .insim_transport import InSimTransport
from .packet_sender_mixin import PacketSenderMixin
from .exceptions import (
    InSimError, InSimConnectionError, InSimConfigurationError,
    InSimPacketError, InSimModuleError, InSimProtocolError, InSimCommandError,
)
from .insim_packet_sender import mute_send_logs, unmute_send_logs

__all__ = [
    '__version__',
    'DEFAULT_CONFIG',
    'build_config',
    'InSimClient',
    'InSimApp',
    'InSimLoader',
    'InSimTransport',
    'PacketSenderMixin',
    'InSimError',
    'InSimConnectionError',
    'InSimConfigurationError',
    'InSimPacketError',
    'InSimModuleError',
    'InSimProtocolError',
    'InSimCommandError',
    'mute_send_logs',
    'unmute_send_logs',
]