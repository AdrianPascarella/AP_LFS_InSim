"""Comportamiento de tráfico de las IAs, repartido por responsabilidad.

`_TrafficMixin` no tiene lógica propia: compone los submixins de este paquete y
existe para que `AIControl` (app.py) siga heredando de un único mixin de tráfico.

    radar.py           barrido de vehículos (carril propio / objetivo / regreso)
    cruise_control.py  ACC de 3 zonas
    zones.py           geometría de intersecciones y prioridad de paso
    overtake.py        maniobra de adelantamiento (matemática + FSM)
    paths.py           helpers geométricos sobre listas de nodos
    orchestrator.py    `_update_traffic_behavior`, que coordina todo lo anterior
"""

from __future__ import annotations

from insims.ai_control.traffic.cruise_control import _CruiseControlMixin
from insims.ai_control.traffic.orchestrator import _OrchestratorMixin
from insims.ai_control.traffic.overtake import _OvertakeMixin
from insims.ai_control.traffic.paths import _PathsMixin
from insims.ai_control.traffic.radar import _RadarMixin
from insims.ai_control.traffic.zones import _ZonesMixin


class _TrafficMixin(
    _OrchestratorMixin,
    _RadarMixin,
    _CruiseControlMixin,
    _ZonesMixin,
    _OvertakeMixin,
    _PathsMixin,
):
    """Fachada: agrupa todos los submixins de tráfico en un solo mixin."""


__all__ = ["_TrafficMixin"]
