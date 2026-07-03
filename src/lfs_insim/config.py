"""
lfs_insim/config.py - Framework configuration defaults (P14).

The core ships its own defaults so it works as an installed package, with no
project files around. Override any key by passing a dict to InSimClient /
InSimApp / InSimLoader; the CLI additionally loads the project's
``config/settings.py`` (``INSIM_CONFIG``) from the working directory when it
exists — the core itself never reads project files.

The config stays a plain dict (read with ``self.config.get(key, default)``)
to keep the surface every existing module relies on.
"""

from typing import Any, Dict, Optional

__all__ = ['DEFAULT_CONFIG', 'build_config']

DEFAULT_CONFIG: Dict[str, Any] = {
    # --- TCP connection (InSim) ---
    'tcp_host':   '127.0.0.1',
    'tcp_port':   29999,        # must match /insim <port> in LFS
    'tcp_buffer': 4096,

    # --- Initialization packet (ISI) ---
    'insim_name': 'LFS-InSim',  # IName shown by LFS
    'admin_pass': '',           # LFS admin password (per machine, never versioned)
    'insim_ver':  10,           # InSim v10 for LFS 0.7F+
    'prefix':     '!',          # chat command prefix
    'interval':   10,           # NLP/MCI interval in ms
    'insim_udp_port': 0,        # 0 = NLP/MCI over TCP; != 0 redirects them to UDP

    # --- UDP (OutSim / OutGauge) ---
    # Port this process listens on for LFS UDP packets; must match
    # "OutSim Port" in LFS cfg.txt. The socket only opens if some app
    # declares outsim_opts in set_outsim().
    'udp_host':   '0.0.0.0',
    'udp_port':   30000,
    'udp_buffer': 4096,

    # --- Dispatch ---
    'use_thread_pool': False,   # dispatch packets through a thread pool
    'max_workers': 5,           # pool size when use_thread_pool is True
}


def build_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a fresh config dict: package defaults merged with `overrides`."""
    config = dict(DEFAULT_CONFIG)
    if overrides:
        config.update(overrides)
    return config
