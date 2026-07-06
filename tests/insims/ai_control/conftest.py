"""
Infra de fixtures de ai_control SIN LFS (Fase 5).

`ai_control` no tenía tests: toca lógica frágil (física, navegación, tráfico)
que hoy solo se puede ejercitar con el juego abierto. Esta infra sintetiza —sin
conexión a LFS— el estado que esa lógica consume:

  - Telemetría sintética: Coordinates / Speed / Angle / Telemetry / Player / AI
    a partir de unidades HUMANAS (metros, km/h, grados). Las conversiones a
    unidades LFS reutilizan las mismas funciones que el core (utils.lfs_*), así
    los valores coinciden con los que produciría LFS.
  - Grafo de calles sintético: se puebla un MapRecorder REAL con
    RoadSegment / RoadLink / LateralLink / IntersectionZone / SpecialRule, de
    forma que get_location_context() (lógica real) se ejercita de verdad.
  - Harness de la app: una AIControl real con el cliente reemplazado por uno que
    CAPTURA los paquetes enviados (client.sent), un UsersManagement real vacío
    como user_manager y su MapRecorder poblable.

Todo se expone como fixtures-factoría (igual estilo que tests/conftest.py), para
que los tests no importen nada pesado y no haya choques de nombres de módulo.
"""

from __future__ import annotations

import os

# matplotlib se importa al cargar map_ui (dep de ai_control); backend headless.
os.environ.setdefault("MPLBACKEND", "Agg")

import pytest

from insims.ai_control.behavior import AIBehavior
from insims.ai_control.nav_modes.freeroam.graph import (
    LateralLink,
    RoadLink,
    RoadSegment,
)
from insims.users_management.um_class import (
    AI,
    Angle,
    AngularVelocity,
    CCIFlags,
    Coordinates,
    Player,
    Speed,
    Telemetry,
)
from lfs_insim.utils import (
    PIDController,
    lfs_angle_to_degrees,
    lfs_angvel_to_degrees_per_second,
    lfs_pos_to_meters,
    lfs_speed_to_kmh,
)

_MISSING = object()


# ─── Telemetría sintética ────────────────────────────────────────────────────


def _coords(x_m: float, y_m: float, z_m: float = 0.0) -> Coordinates:
    """Coordinates a partir de metros (se guardan en unidades LFS, como el MCI)."""
    return Coordinates(
        lfs_pos_to_meters(x_m, rev=True),
        lfs_pos_to_meters(y_m, rev=True),
        lfs_pos_to_meters(z_m, rev=True),
    )


def _telemetry(
    x_m: float = 0.0,
    y_m: float = 0.0,
    z_m: float = 0.0,
    speed_kmh: float = 0.0,
    heading_deg: float = 0.0,
    direction_deg: float | None = None,
    angvel_dps: float = 0.0,
    node: int = 0,
    lap: int = 0,
    position_race: int = 0,
    info: int = 0,
) -> Telemetry:
    """Telemetry sintética desde unidades humanas (m, km/h, grados)."""
    if direction_deg is None:
        direction_deg = heading_deg
    return Telemetry(
        node=node,
        lap=lap,
        position_race=position_race,
        info=CCIFlags(info),
        coordinates=_coords(x_m, y_m, z_m),
        speed=Speed(lfs_speed_to_kmh(speed_kmh, rev=True)),
        direction=Angle(lfs_angle_to_degrees(direction_deg, rev=True)),
        heading=Angle(lfs_angle_to_degrees(heading_deg, rev=True)),
        angvel=AngularVelocity(lfs_angvel_to_degrees_per_second(angvel_dps, rev=True)),
    )


def _player(
    plid: int = 1,
    ucid: int = 1,
    telemetry: Telemetry | None = None,
    car_name: str = "XFG",
) -> Player:
    """Player con defaults inocuos (los campos de setup no los lee la lógica de IA)."""
    return Player(
        plid=plid,
        player_type=0,
        plate="",
        flags=0,
        car_name=car_name,
        skin_name="",
        tyres=(0, 0, 0, 0),
        handicap_mass=0,
        handicap_throttle=0,
        driver_model=0,
        passengers=0,
        rwadj=0,
        fwadj=0,
        set_up_flags=0,
        configuration=0,
        starting_fuel=0,
        ucid=ucid,
        telemetry=telemetry,
    )


def _fixed_pids() -> tuple[PIDController, PIDController]:
    """PIDs DETERMINISTAS (no aleatorios) para congelar la salida física.

    Los mismos ganancias que produce _generate_random_pid para 'direction'
    (que son fijas en el código) y un juego representativo para 'speed'.
    """
    pid_speed = PIDController(kp=0.06, ki=0.003, kd=0.02, out_min=-1.0, out_max=1.0)
    pid_direction = PIDController(
        kp=0.00018, ki=0.0000015, kd=0.00004, out_min=-1.0, out_max=1.0
    )
    return pid_speed, pid_direction


def _behavior(
    pid_speed: PIDController | None = None,
    pid_direction: PIDController | None = None,
    **overrides,
) -> AIBehavior:
    """AIBehavior con PIDs deterministas; cualquier campo se sobreescribe por kwargs."""
    ps, pd = _fixed_pids()
    behavior = AIBehavior(
        pid_speed=pid_speed or ps,
        pid_direction=pid_direction or pd,
    )
    for key, value in overrides.items():
        setattr(behavior, key, value)
    return behavior


def _ai(
    plid: int = 1,
    ucid: int = 1,
    name: str = "AI1",
    behavior=_MISSING,
    **telem,
) -> AI:
    """AI en pista con telemetría; adjunta un AIBehavior en extra['aic'].

    behavior:
      - omitido  → se crea uno determinista.
      - None     → no se adjunta ninguno (extra['aic'] ausente).
      - AIBehavior → se usa ese.
    """
    telemetry = _telemetry(**telem)
    player = _player(plid=plid, ucid=ucid, telemetry=telemetry)
    ai = AI(player=player, ai_name=name)
    if behavior is _MISSING:
        behavior = _behavior()
    if behavior is not None:
        ai.extra["aic"] = behavior
    return ai


@pytest.fixture
def make_coords():
    return _coords


@pytest.fixture
def make_telemetry():
    return _telemetry


@pytest.fixture
def make_player():
    return _player


@pytest.fixture
def make_behavior():
    return _behavior


@pytest.fixture
def make_ai():
    return _ai


# ─── Grafo de calles sintético ───────────────────────────────────────────────
#
# Puebla un MapRecorder REAL con RoadSegment / RoadLink / LateralLink, keyeados
# IGUAL que producción (roads por road_id; links por su propiedad .link_id, p. ej.
# "R1->R2" y "R1<<>>R3"), para ejercitar de verdad la planificación de enlaces
# (_get_raw_candidates / _calculate_next_link / _plan_next_link) y la geometría de
# navigation.py. (IntersectionZone / SpecialRule se añadirán cuando traffic los pida.)


def _graph_nodes(points) -> list:
    """Lista de Coordinates desde puntos (x_m, y_m) o (x_m, y_m, z_m) en metros."""
    nodes = []
    for p in points:
        x_m, y_m = p[0], p[1]
        z_m = p[2] if len(p) > 2 else 0.0
        nodes.append(_coords(x_m, y_m, z_m))
    return nodes


def _road(road_id: str, points, **overrides) -> RoadSegment:
    """RoadSegment con nodos en metros; cualquier campo se sobreescribe por kwargs."""
    road = RoadSegment(road_id=road_id, nodes=_graph_nodes(points))
    for key, value in overrides.items():
        setattr(road, key, value)
    return road


def _road_link(from_road_id: str, to_road_id: str, points, **overrides) -> RoadLink:
    """RoadLink longitudinal (from → to); su .link_id es 'from->to' por defecto."""
    link = RoadLink(
        from_road_id=from_road_id, to_road_id=to_road_id, nodes=_graph_nodes(points)
    )
    for key, value in overrides.items():
        setattr(link, key, value)
    return link


def _lateral_link(road_a: str, road_b: str, points, **overrides) -> LateralLink:
    """LateralLink entre carriles (a <<>> b); su .link_id es 'a<<>>b' por defecto."""
    link = LateralLink(road_a=road_a, road_b=road_b, nodes=_graph_nodes(points))
    for key, value in overrides.items():
        setattr(link, key, value)
    return link


def _populate_graph(map_recorder, roads=(), road_links=(), lateral_links=()) -> None:
    """Vuelca las geometrías en un MapRecorder con la MISMA clave que producción."""
    for road in roads:
        map_recorder.roads[road.road_id] = road
    for link in road_links:
        map_recorder.road_links[link.link_id] = link
    for link in lateral_links:
        map_recorder.lateral_links[link.link_id] = link


@pytest.fixture
def make_road():
    return _road


@pytest.fixture
def make_road_link():
    return _road_link


@pytest.fixture
def make_lateral_link():
    return _lateral_link


@pytest.fixture
def populate_graph():
    return _populate_graph


# ─── Harness de la app (AIControl sin cliente real) ──────────────────────────


class CapturingClient:
    """Cliente falso: en vez de enviar por socket, captura los paquetes."""

    def __init__(self):
        self.sent = []

    def send(self, packet) -> None:
        self.sent.append(packet)


@pytest.fixture
def ai_control():
    """AIControl real, lista para ejercitar su lógica sin LFS.

    - client → CapturingClient (los send_ISP_* quedan en app.client.sent).
    - user_manager → UsersManagement real vacío (poblar .players/.ais a mano).
    - route_manager → RouteManager real.
    - map_recorder → el que crea AIControl.__init__ (poblable con `graph`).
    """
    from insims.ai_control.app import AIControl
    from insims.ai_control.nav_modes.route.manager import RouteManager
    from insims.users_management.main import UsersManagement

    app = AIControl(config={"interval": 100})
    client = CapturingClient()
    app.client = client

    user_manager = UsersManagement(config={"interval": 100})
    user_manager.client = client
    app.user_manager = user_manager

    app.route_manager = RouteManager()
    return app
