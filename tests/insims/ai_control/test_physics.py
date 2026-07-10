"""
Tests de CARACTERIZACIÓN de _PhysicsMixin (insims/ai_control/physics.py).

Congelan el comportamiento ACTUAL del volante, pedales y gestión de marchas
antes de tocar nada (red de seguridad, MODUS_OPERANDI §3). Los valores exactos
que se afirman son los que produce HOY el código con PIDs deterministas
(conftest._fixed_pids) e interval_mci_s = 0.1 s; si un refactor los cambia, el
test debe saltar para que decidamos si el cambio es deliberado.

Convenciones LFS relevantes:
  - Volante InSim: 1 = HARD_LEFT, 32768 = CENTRE, 65535 = HARD_RIGHT.
  - Pedales InSim: 0 = MIN (suelto), 65535 = MAX (a fondo).
  - Ejes de mundo: +Y = Norte, +X = Oeste.
"""

from lfs_insim.insim_enums import CS, CSVAL

CENTRE = CSVAL.STEER.CENTRE  # 32768
HARD_LEFT = CSVAL.STEER.HARD_LEFT  # 1
HARD_RIGHT = CSVAL.STEER.HARD_RIGHT  # 65535
PEDAL_MIN = CSVAL.MIN_MID_MAX.MIN  # 0
PEDAL_MAX = CSVAL.MIN_MID_MAX.MAX  # 65535


def _inputs_by_type(inputs: list) -> dict:
    """Mapa {CS: Value} del último valor por tipo de input (para asertar cómodo)."""
    return {aiv.Input: aiv.Value for aiv in inputs}


# ─── _calculate_steering: geometría pura → valor de volante ──────────────────


class TestCalculateSteering:
    def test_sin_target_devuelve_centro(self, ai_control, make_behavior):
        behavior = make_behavior(point_resolved=None)
        steer = ai_control._calculate_steering(
            behavior=behavior,
            telemetry=_telem_ahead(),
        )
        assert steer == CENTRE

    def test_objetivo_al_frente_mantiene_centro(
        self, ai_control, make_behavior, make_coords, make_telemetry
    ):
        # AI en (0,0) mirando al Norte (heading 0); objetivo 10 m al Norte (+Y).
        behavior = make_behavior(point_resolved=make_coords(0.0, 10.0))
        telemetry = make_telemetry(x_m=0.0, y_m=0.0, heading_deg=0.0)
        steer = ai_control._calculate_steering(behavior=behavior, telemetry=telemetry)
        assert steer == CENTRE

    def test_objetivo_a_la_izquierda_gira_a_tope(
        self, ai_control, make_behavior, make_coords, make_telemetry
    ):
        # Objetivo al Este (-X): el PID satura hacia HARD_LEFT.
        behavior = make_behavior(point_resolved=make_coords(-10.0, 0.0))
        telemetry = make_telemetry(x_m=0.0, y_m=0.0, heading_deg=0.0)
        steer = ai_control._calculate_steering(behavior=behavior, telemetry=telemetry)
        assert steer == HARD_LEFT

    def test_objetivo_a_la_derecha_gira_a_tope(
        self, ai_control, make_behavior, make_coords, make_telemetry
    ):
        # Objetivo al Oeste (+X): el PID satura hacia HARD_RIGHT.
        behavior = make_behavior(point_resolved=make_coords(10.0, 0.0))
        telemetry = make_telemetry(x_m=0.0, y_m=0.0, heading_deg=0.0)
        steer = ai_control._calculate_steering(behavior=behavior, telemetry=telemetry)
        assert steer == HARD_RIGHT

    def test_marcha_atras_invierte_el_giro(
        self, ai_control, make_behavior, make_coords, make_telemetry
    ):
        from insims.ai_control.behavior import GearMode

        # Mismo objetivo a la derecha, pero en REVERSE → el signo se invierte.
        behavior = make_behavior(
            point_resolved=make_coords(10.0, 0.0),
            gear_mode=GearMode.REVERSE,
        )
        telemetry = make_telemetry(x_m=0.0, y_m=0.0, heading_deg=0.0)
        steer = ai_control._calculate_steering(behavior=behavior, telemetry=telemetry)
        assert steer == HARD_LEFT


# ─── _calculate_pedals: reparto PID → throttle/brake ─────────────────────────


class TestCalculatePedals:
    def test_objetivo_parar_frena_a_fondo(self, ai_control, make_behavior):
        behavior = make_behavior(speed_resolved_kmh=0.0)
        throttle, brake = ai_control._calculate_pedals(behavior, current_speed_kmh=0.0)
        assert (throttle, brake) == (PEDAL_MIN, PEDAL_MAX)

    def test_acelerar_desde_parado(self, ai_control, make_behavior):
        # target 50 > current 0 → acelera (throttle saturado, freno suelto).
        behavior = make_behavior(speed_resolved_kmh=50.0)
        throttle, brake = ai_control._calculate_pedals(behavior, current_speed_kmh=0.0)
        assert throttle == PEDAL_MAX
        assert brake == PEDAL_MIN

    def test_frenar_por_exceso_de_velocidad(self, ai_control, make_behavior):
        # target 20 < current 100 → frena (freno saturado, acelerador suelto).
        behavior = make_behavior(speed_resolved_kmh=20.0)
        throttle, brake = ai_control._calculate_pedals(
            behavior, current_speed_kmh=100.0
        )
        assert throttle == PEDAL_MIN
        assert brake == PEDAL_MAX

    def test_reparto_es_excluyente(self, ai_control, make_behavior):
        # Nunca acelera y frena a la vez.
        behavior = make_behavior(speed_resolved_kmh=30.0)
        throttle, brake = ai_control._calculate_pedals(behavior, current_speed_kmh=15.0)
        assert not (throttle > 0 and brake > 0)


# ─── _handle_pedals_and_gears: máquina de encendido/marchas ───────────────────


class TestHandlePedalsAndGears:
    def test_apagado_completo_cuando_esta_parado(self, ai_control, make_ai):
        # Sin objetivo de velocidad, parado y encendido → secuencia de apagado.
        from insims.ai_control.behavior import GearMode

        ai = make_ai(speed_kmh=0.0)
        behavior = ai.extra["aic"]
        behavior.speed_request = None
        behavior.active_ready = True

        actions = ai_control._handle_pedals_and_gears(ai)

        values = _inputs_by_type(actions)
        assert values[CS.IGNITION] == CSVAL.TOGGLE.OFF
        assert values[CS.GEAR] == CSVAL.GEAR.NEUTRAL
        assert values[CS.HANDBRAKE] == CSVAL.MIN_MID_MAX.MAX
        assert behavior.active_ready is False
        assert behavior.gear_mode == GearMode.NEUTRAL

    def test_parado_y_ya_apagado_no_hace_nada(self, ai_control, make_ai):
        ai = make_ai(speed_kmh=0.0)
        behavior = ai.extra["aic"]
        behavior.speed_request = None
        behavior.active_ready = False

        actions = ai_control._handle_pedals_and_gears(ai)
        assert actions is None

    def test_arranque_enciende_y_mete_primera(self, ai_control, make_ai):
        from insims.ai_control.behavior import GearMode

        ai = make_ai(speed_kmh=0.0)
        behavior = ai.extra["aic"]
        behavior.speed_request = 30.0  # float directo
        behavior.active_ready = False

        actions = ai_control._handle_pedals_and_gears(ai)

        values = _inputs_by_type(actions)
        assert values[CS.IGNITION] == CSVAL.TOGGLE.ON
        assert values[CS.GEAR] == CSVAL.GEAR.FIRST
        assert values[CS.SET_HELP_FLAGS] == CSVAL.AI_HELP.AUTOGEARS
        assert behavior.active_ready is True
        assert behavior.gear_mode == GearMode.NORMAL

    def test_watchdog_registra_atasco(self, ai_control, make_ai):
        # Quiere moverse (target != 0) pero está parado → arranca el cronómetro.
        from insims.ai_control.behavior import GearMode

        ai = make_ai(speed_kmh=0.0)
        behavior = ai.extra["aic"]
        behavior.speed_request = 40.0
        behavior.active_ready = True
        behavior.gear_mode = GearMode.NORMAL
        behavior.stuck_start_time = 0.0

        ai_control._handle_pedals_and_gears(ai)
        assert behavior.stuck_start_time > 0.0

    def test_watchdog_se_resetea_si_avanza(self, ai_control, make_ai):
        from insims.ai_control.behavior import GearMode

        ai = make_ai(speed_kmh=25.0)
        behavior = ai.extra["aic"]
        behavior.speed_request = 40.0
        behavior.active_ready = True
        behavior.gear_mode = GearMode.NORMAL
        behavior.stuck_start_time = 123.0  # venía atascado

        ai_control._handle_pedals_and_gears(ai)
        assert behavior.stuck_start_time == 0.0

    def test_factor_humano_escala_la_velocidad(self, ai_control, make_ai):
        from insims.ai_control.behavior import GearMode

        ai = make_ai(speed_kmh=20.0)
        behavior = ai.extra["aic"]
        behavior.speed_request = 100.0
        behavior.active_ready = True
        behavior.gear_mode = GearMode.NORMAL  # evita el corte por cambio de marcha
        behavior.ignore_human = False
        behavior.human_speed_factor = 0.5

        ai_control._handle_pedals_and_gears(ai)

        # 100 * 0.5 = 50, y el flag ignore_human se rearma a False cada tick.
        assert behavior.speed_resolved_kmh == 50.0
        assert behavior.ignore_human is False

    def test_ignore_human_no_escala(self, ai_control, make_ai):
        from insims.ai_control.behavior import GearMode

        ai = make_ai(speed_kmh=20.0)
        behavior = ai.extra["aic"]
        behavior.speed_request = 100.0
        behavior.active_ready = True
        behavior.gear_mode = GearMode.NORMAL
        behavior.ignore_human = True
        behavior.human_speed_factor = 0.5

        ai_control._handle_pedals_and_gears(ai)
        assert behavior.speed_resolved_kmh == 100.0


# ─── _handle_steering: resolución de objetivo (coords / PLID / tupla) ─────────


class TestHandleSteering:
    def test_sin_target_manda_centro(self, ai_control, make_ai):
        ai = make_ai()
        ai.extra["aic"].point_request = None

        actions = ai_control._handle_steering(ai)
        assert len(actions) == 1
        assert actions[0].Input == CS.STEER
        assert actions[0].Value == CENTRE

    def test_target_tupla_estatica_se_convierte_en_coords(self, ai_control, make_ai):
        # Tupla (x_m, y_m) en metros → fija point_resolved con la Z de la IA.
        ai = make_ai(x_m=0.0, y_m=0.0, heading_deg=0.0)
        behavior = ai.extra["aic"]
        behavior.point_request = (10.0, 0.0)  # 10 m al Oeste

        actions = ai_control._handle_steering(ai)

        assert behavior.point_resolved is not None
        assert actions[0].Input == CS.STEER
        assert actions[0].Value == HARD_RIGHT

    def test_target_plid_resuelve_coords_de_otra_ai(self, ai_control, make_ai):
        # La IA persigue a otra IA por su PLID.
        chaser = make_ai(plid=1, x_m=0.0, y_m=0.0, heading_deg=0.0)
        target = make_ai(plid=2, x_m=10.0, y_m=0.0, name="AI2")
        ai_control.user_manager.ais[1] = chaser
        ai_control.user_manager.ais[2] = target

        behavior = chaser.extra["aic"]
        behavior.point_request = 2  # PLID objetivo

        actions = ai_control._handle_steering(chaser)

        assert behavior.point_resolved is target.player.telemetry.coordinates
        assert actions[0].Value == HARD_RIGHT

    def test_target_plid_desaparecido_resetea_y_centra(self, ai_control, make_ai):
        ai = make_ai(plid=1)
        behavior = ai.extra["aic"]
        behavior.point_request = 999  # PLID que no existe

        actions = ai_control._handle_steering(ai)

        assert actions[0].Value == CENTRE
        assert behavior.point_request is None  # reset_direction() lo limpió


# ─── Helper local ────────────────────────────────────────────────────────────


def _telem_ahead():
    """Telemetría trivial (todo a cero) para tests que no dependen de la pose."""
    from insims.users_management.um_class import (
        Angle,
        AngularVelocity,
        CCIFlags,
        Coordinates,
        Speed,
        Telemetry,
    )

    return Telemetry(
        node=0,
        lap=0,
        position_race=0,
        info=CCIFlags(0),
        coordinates=Coordinates(0, 0, 0),
        speed=Speed(0),
        direction=Angle(0),
        heading=Angle(0),
        angvel=AngularVelocity(0),
    )
