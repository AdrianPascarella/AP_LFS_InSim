"""
lfs_insim/insim_app.py - Base class for composable modules.

An InSimApp is one piece of the puzzle: it declares which other modules it
needs, contributes its ISI flags and OutSim opts, and handles packets and
lifecycle events. It does NOT own the connection: apps are attached to a
single InSimClient with `client.register(app)` (the loader does this
automatically) and the client dispatches to them.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

from .config import build_config
from .packets import ISP_ISI
from .packet_sender_mixin import PacketSenderMixin
from .insim_enums import OSO

if TYPE_CHECKING:
    from .insim_client import InSimClient
    from .insim_loader import InSimLoader

logger = logging.getLogger(__name__)

class InSimApp(PacketSenderMixin):
    """
    Base class for every framework module.

    Attributes:
        dependencies: Names of other required modules.
        version: Module version (read from insim.json).
        description: Module description.
        client: The InSimClient this app is registered into (set by
            `client.register(app)`; None until then).
    """

    dependencies: List[str] = []
    version: str = "0.0.0"
    description: str = ""

    def __init__(
        self,
        config: Optional[dict] = None,
        name: Optional[str] = None,
        _loader: Optional['InSimLoader'] = None,
        _insim_path: Optional[Path] = None,
    ):
        self.config = build_config(config)

        # Default to the class name when no name is given
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"InSim.{self.name}")

        # Set by InSimClient.register(); apps must not create clients
        self.client: Optional['InSimClient'] = None

        self._loader = _loader
        self._insim_path = _insim_path
        self._module_instances: Dict[str, 'InSimApp'] = {}

        # Copy the class-level dependency list so _load_metadata() does not
        # mutate the attribute shared by every module.
        self.dependencies = list(self.__class__.dependencies)

        # ISI contribution: the client merges each app's isi.Flags into the
        # final ISI it sends. Override set_isi_packet() to add flags.
        self.isi = ISP_ISI()

        # OutSim: OSO flags this module needs. None by default.
        # Override set_outsim() to enable specific blocks.
        self.outsim_opts: OSO = OSO.NONE

        # Load metadata from insim.json when available
        if self._insim_path:
            self._load_metadata()

    def _load_metadata(self):
        """Load metadata from the module's manifest (insim.json)."""
        manifest_path = self._insim_path / "insim.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.version = data.get("version", self.version)
                    self.description = data.get("description", self.description)
                    # Dependencies declared in the JSON extend the class ones
                    json_deps = data.get("insim_dependencies", {})
                    for dep_name in json_deps.keys():
                        if dep_name not in self.dependencies:
                            self.dependencies.append(dep_name)
            except Exception as e:
                self.logger.warning(f"Could not load the manifest: {e}")

    def get_insim(self, name: str) -> Optional['InSimApp']:
        """
        Return the instance of a module this app depends on.

        Usage:
            tracker = self.get_insim("player_tracker")
            p = tracker.get_player(6)
        """
        # 1. Direct dependencies
        if name in self._module_instances:
            return self._module_instances[name]

        # 2. Fall back to the loader's global instance cache
        if self._loader and name in self._loader._instances:
            return self._loader._instances[name]

        return None

    def set_isi_packet(self) -> None:
        """
        Hook to declare the ISI flags this module needs. Override and add
        flags after calling super():

            def set_isi_packet(self):
                super().set_isi_packet()
                self.isi.Flags |= ISF.LOCAL | ISF.MCI

        The client merges every app's isi.Flags into the final ISI in start().
        Other ISI fields (Interval, IName, Admin...) come from the client's
        config, not from apps.
        """
        self.isi.Flags = 0

    def set_outsim(self) -> None:
        """
        Hook to declare which OutSim2 blocks this module needs. Override to
        enable OSO flags:

            def set_outsim(self):
                super().set_outsim()
                self.outsim_opts |= OSO.TIME | OSO.MAIN | OSO.INPUTS

        InSimClient aggregates the opts of every app in start() and opens the
        UDP socket only when the combined result is not OSO.NONE.
        """
        pass

    # Empty lifecycle hooks (the client calls them if defined)
    def on_connect(self): pass
    def on_disconnect(self): pass
    def on_tick(self): pass

    # send() and send_ISP_*() inherited from PacketSenderMixin
