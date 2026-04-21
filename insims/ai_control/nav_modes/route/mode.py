from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from insims.ai_control.nav_modes import AINavModeState


@dataclass
class RouteMode(AINavModeState):
    """Estado exclusivo del modo de Rutas."""
    active_route_name: Optional[str] = None
    route_wp_index: int = 0
    route_started: bool = False

    def __init__(self, route_name: str):
        self.active_route_name = route_name
        self.extra_inputs_to_send = None
