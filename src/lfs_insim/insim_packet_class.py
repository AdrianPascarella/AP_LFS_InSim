"""
[DEPRECATED FACADE] lfs_insim/insim_packet_class.py

Kept only for backwards compatibility with code written before the packets
package existed. Import packet classes from ``lfs_insim.packets`` and
protocol enums from ``lfs_insim.insim_enums`` instead.

This module re-exports BOTH namespaces because the old monolithic file
exposed them together (P15).
"""

import warnings

warnings.warn(
    "lfs_insim.insim_packet_class is deprecated; import packet classes from "
    "lfs_insim.packets and protocol enums from lfs_insim.insim_enums instead.",
    DeprecationWarning,
    stacklevel=2,
)

from lfs_insim.insim_enums import *  # noqa: E402,F401,F403
from lfs_insim.packets import *  # noqa: E402,F401,F403
