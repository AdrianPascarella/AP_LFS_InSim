"""A Python library for the Live for Speed InSim protocol (InSim, OutSim, OutGauge)."""

from importlib.metadata import version as _version

from lfs_insim._commands import Command
from lfs_insim._connection import InSim
from lfs_insim._run import run
from lfs_insim._udp import OutGauge, OutSim

__version__ = _version("lfs-insim")

__all__ = ["Command", "InSim", "OutGauge", "OutSim", "__version__", "run"]
