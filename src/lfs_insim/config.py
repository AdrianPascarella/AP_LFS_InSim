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

__all__ = ["DEFAULT_CONFIG", "build_config"]

DEFAULT_CONFIG: Dict[str, Any] = {
    # --- TCP connection (InSim) ---
    "tcp_host": "127.0.0.1",
    "tcp_port": 29999,  # must match /insim <port> in LFS
    "tcp_buffer": 4096,
    # --- Initialization packet (ISI) ---
    "insim_name": "LFS-InSim",  # IName shown by LFS
    "admin_pass": "",  # LFS admin password (per machine, never versioned)
    "insim_ver": 10,  # InSim v10 for LFS 0.7F+
    "prefix": "!",  # chat command prefix
    "interval": 10,  # NLP/MCI interval in ms
    "insim_udp_port": 0,  # 0 = NLP/MCI over TCP; != 0 redirects them to UDP
    # --- UDP (OutSim / OutGauge) ---
    # Port this process listens on for LFS UDP packets; must match
    # "OutSim Port" in LFS cfg.txt. The socket only opens if some app
    # declares outsim_opts in set_outsim().
    "udp_host": "0.0.0.0",
    "udp_port": 30000,
    "udp_buffer": 4096,
    # --- Reconnection (P12) ---
    # When LFS drops the TCP connection, the client's main loop retries with
    # exponential backoff, resends the ISI and re-requests the state
    # (TINY.NCN/NPL) so app trackers rebuild themselves.
    # A reconnect is only PROVISIONAL: LFS may accept the TCP connection and
    # drop it right after the ISI (e.g. admin password mismatch). If the
    # session dies again within `reconnect_stable_time` seconds, the next
    # cycle resumes the escalating backoff instead of retrying at full
    # speed (P24 — otherwise a rejected ISI becomes a connection storm).
    "reconnect": True,  # auto-reconnect on connection loss
    "reconnect_delay": 1.0,  # initial delay between attempts (seconds)
    "reconnect_backoff": 2.0,  # delay multiplier after each failed attempt
    "reconnect_max_delay": 30.0,  # upper bound for the delay
    "reconnect_max_attempts": 0,  # 0 = retry forever
    "reconnect_stable_time": 10.0,  # session shorter than this keeps the backoff escalating (P24)
    # --- Main loop tick ---
    # Seconds between on_tick dispatches (client hook + apps). The main
    # loop's internal poll stays at <=100 ms regardless, so a slow tick
    # never delays connection-loss detection (P12) or fail-fast handler
    # errors. Not a precision timer (rides on time.sleep granularity,
    # ~15 ms on Windows): high-frequency work belongs in packet handlers
    # (MCI/OutSim), not in on_tick. Minimum 0.01; there is no catch-up
    # after a stall (e.g. while reconnecting).
    "tick_interval": 0.1,
    # --- Error policy ---
    # What to do when an app packet handler (`on_ISP_*`) or lifecycle hook
    # raises:
    #   'log'   (default) isolate the error: log it with traceback and keep
    #           running — resilient, for production;
    #   'raise' fail-fast: the first error stops the client and re-raises
    #           out of start() — for development.
    # Exception: on_disconnect errors during stop() are always isolated so
    # the shutdown sequence completes.
    "handler_errors": "log",
}


def build_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a fresh config dict: package defaults merged with `overrides`."""
    config = dict(DEFAULT_CONFIG)
    if overrides:
        config.update(overrides)
    return config
