"""A Python library for the Live for Speed InSim protocol (InSim, OutSim, OutGauge)."""

from importlib.metadata import version as _version

from lfs_insim._connection import InSim

__version__ = _version("lfs-insim")

__all__ = ["InSim", "__version__"]
