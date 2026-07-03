"""
lfs_insim/insim_state.py - Optional default-client registry.

Since P13 the framework has no mandatory global state: sockets and receiver
threads live in each client's InSimTransport, and packets are delivered
through direct callbacks. Several clients can coexist in one process.

What remains here is convenience sugar: a reference to the process's
"default" client (the first one created). PacketSenderMixin uses it as a
fallback for helper classes that are not registered to a client
(e.g. utils.Command / CMDManager).
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .insim_client import InSimClient

_default_client: Optional["InSimClient"] = None


def set_insim_client(client: "InSimClient") -> None:
    """Register the default client. Only the first one wins."""
    global _default_client
    if _default_client is None:
        _default_client = client


def get_insim_client() -> Optional["InSimClient"]:
    """Return the process's default client (None if none was created)."""
    return _default_client


def reset_insim_client() -> None:
    """Clear the default client (used by tests and full restarts)."""
    global _default_client
    _default_client = None
