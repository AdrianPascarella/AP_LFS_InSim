"""
Red de CARACTERIZACIÓN del orquestador de tráfico (`_update_traffic_behavior`)
previa al bloque 8.3 (MODUS §3: caracterizar ANTES de tocar).

S34 le puso la primera red (el gatillo IDLE→EVALUATING, en test_traffic.py);
aquí se congela el MARCO que el 8.3 debe dejar intacto al sustituir el control
de intersecciones:

  - Asignación final: `behavior.speed_request = min(velocidad_segura, base)` y
    `behavior.point_request` = punto de lookahead sobre la vía (SIEMPRE, también
    en el camino de caché).
  - Compuerta del radar: dentro de `_radar_interval` NO se rescanea; manda
    `_cached_target_speed` (limitada por la base).
  - Reglas especiales: se activan al pasar por su nodo inicial y se desactivan
    en el final, y su override de velocidad se aplica en el SIGUIENTE scan (la
    base se calcula al principio de la pasada, la activación ocurre al final).

El control de intersecciones NUEVO (cesión por RoadLink, Fase 8) se testea más
abajo cuando exista; el modelo viejo (zona-área + priority_rules) NO se
caracteriza porque este mismo bloque lo retira.

Convenciones (mismas que test_traffic.py): coordenadas en metros vía
`make_coords`; velocidades en km/h; vía recta en +Y con nodos cada 10 m;
heading LFS 0 = +Y (Norte).
"""

from __future__ import annotations

import math
import time

import pytest

from insims.ai_control.nav_modes.freeroam.enums import YieldType
from insims.ai_control.nav_modes.freeroam.graph import SpecialRule
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from insims.ai_control.traffic.cruise_control import PARADA_ABSOLUTA_M

# ─── Helpers locales (mismo estilo que test_traffic.py) ──────────────────────


def _pts_y(x=0.0, y0=0.0, y1=90.0, step=10.0):
    """Puntos (x, y) de una recta en +Y (por defecto índices 0..9 cada 10 m)."""
    n = int(round((y1 - y0) / step))
    return [(x, y0 + i * step) for i in range(n + 1)]


def _place_ai(
    make_ai,
    make_behavior,
    plid,
    x_m,
    y_m,
    speed_kmh=0.0,
    heading_deg=0.0,
    mode_fields=None,
):
    """AI en pista con FreeroamMode en extra['aic'].active_mode.

    mode_fields=None → active_mode=None (sin topología: el radar la ignora).
    """
    mode = FreeroamMode(**mode_fields) if mode_fields is not None else None
    return make_ai(
        plid=plid,
        name=f"AI{plid}",
        behavior=make_behavior(active_mode=mode),
        x_m=x_m,
        y_m=y_m,
        speed_kmh=speed_kmh,
        heading_deg=heading_deg,
    )


def _set_ais(ai_control, *ais):
    ai_control.user_manager.ais = {a.player.plid: a for a in ais}


def _place_human(ai_control, make_player, make_telemetry, plid, **telem):
    """Jugador humano con telemetría, registrado en user_manager.players."""
    player = make_player(plid=plid, ucid=plid, telemetry=make_telemetry(**telem))
    ai_control.user_manager.players[plid] = player
    return player


def _scanner_en_r1(ai_control, populate_graph, make_road, make_ai, **mode_kw):
    """Escenario base: R1 recta en +Y (0..90), IA en (0,50) a 30 km/h, nodo 5."""
    populate_graph(ai_control.map_recorder, roads=[make_road("R1", _pts_y())])
    scanner = make_ai(plid=1, x_m=0, y_m=50, speed_kmh=30)
    mode = FreeroamMode(
        current_type="Road",
        current_id="R1",
        current_road_id="R1",
        node_index=5,
        **mode_kw,
    )
    scanner.extra["aic"].active_mode = mode
    _set_ais(ai_control, scanner)
    return scanner, mode


# Velocidad base con los defaults del grafo: speed_limit 30 → min 15 → bias 0.5.
BASE_KMH = 22.5


# ─── Marco base: asignación final ────────────────────────────────────────────


class TestOrquestadorMarcoBase:
    def test_sin_trafico_va_a_velocidad_base(
        self, ai_control, populate_graph, make_road, make_ai
    ):
        scanner, mode = _scanner_en_r1(ai_control, populate_graph, make_road, make_ai)

        ai_control._update_traffic_behavior(scanner)

        behavior = scanner.extra["aic"]
        assert behavior.speed_request == pytest.approx(BASE_KMH)
        # Lookahead: max(5, v*0.4) = 5 m desde (0,50) sobre la recta → (0, 55).
        assert behavior.point_request == pytest.approx((0.0, 55.0))
        assert mode.blocking_plid is None
        assert mode._cached_target_speed == pytest.approx(BASE_KMH)

    def test_coche_lento_delante_manda_el_acc(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = _scanner_en_r1(ai_control, populate_graph, make_road, make_ai)
        # Cooldown en el futuro: congela el gatillo de adelantamiento para que
        # este test mida SOLO la rama del ACC (el gatillo ya tiene su red en S34).
        mode.overtake_cooldown = time.time() + 1000.0
        lento = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            65,
            speed_kmh=10,
            mode_fields={"current_id": "R1", "node_index": 6},
        )
        _set_ais(ai_control, scanner, lento)

        # El valor esperado se calcula con las MISMAS piezas que usa el orquestador
        # (mismos min/max por time-gap), así el test fija el cableado, no la ley ACC.
        v_ms = 30.0 / 3.6
        ahead = ai_control._scan_lane_ahead(scanner, mode, max(15.0, v_ms * 10.0))
        dist_m, speed_kmh, plid = ahead[0]
        esperado = ai_control._apply_adaptive_cruise_control(
            BASE_KMH, speed_kmh, dist_m, max(8.0, v_ms * 2.0), max(15.0, v_ms * 3.5)
        )

        ai_control._update_traffic_behavior(scanner)

        behavior = scanner.extra["aic"]
        assert behavior.speed_request == pytest.approx(esperado)
        assert behavior.speed_request < BASE_KMH
        assert mode.blocking_plid == 2
        assert mode.blocking_dist == pytest.approx(dist_m)

    def test_geometria_desconocida_no_toca_nada(
        self, ai_control, populate_graph, make_road, make_ai
    ):
        scanner, mode = _scanner_en_r1(ai_control, populate_graph, make_road, make_ai)
        mode.current_id = "NO_EXISTE"

        ai_control._update_traffic_behavior(scanner)

        behavior = scanner.extra["aic"]
        assert behavior.speed_request is None
        assert behavior.point_request is None

    def test_sin_modo_activo_no_revienta(self, ai_control, make_ai):
        scanner = make_ai(plid=1, x_m=0, y_m=50, speed_kmh=30)  # active_mode=None
        _set_ais(ai_control, scanner)

        ai_control._update_traffic_behavior(scanner)

        assert scanner.extra["aic"].speed_request is None


# ─── Compuerta del radar (Sense-Think-Act con caché) ─────────────────────────


class TestOrquestadorCompuerta:
    def test_dentro_del_intervalo_manda_la_cache_y_no_se_rescanea(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = _scanner_en_r1(ai_control, populate_graph, make_road, make_ai)
        lento = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            65,
            speed_kmh=10,
            mode_fields={"current_id": "R1", "node_index": 6},
        )
        _set_ais(ai_control, scanner, lento)
        mode._last_radar_time = time.time() + 100.0  # compuerta cerrada seguro
        mode._cached_target_speed = 5.0

        ai_control._update_traffic_behavior(scanner)

        behavior = scanner.extra["aic"]
        assert behavior.speed_request == pytest.approx(5.0)
        # No se rescaneó: el coche lento de delante NO quedó registrado…
        assert mode.blocking_plid is None
        # …pero la dirección se sigue pilotando (la asignación final SIEMPRE corre).
        assert behavior.point_request == pytest.approx((0.0, 55.0))

    def test_la_cache_no_supera_la_velocidad_base(
        self, ai_control, populate_graph, make_road, make_ai
    ):
        scanner, mode = _scanner_en_r1(ai_control, populate_graph, make_road, make_ai)
        mode._last_radar_time = time.time() + 100.0
        mode._cached_target_speed = 99.0

        ai_control._update_traffic_behavior(scanner)

        assert scanner.extra["aic"].speed_request == pytest.approx(BASE_KMH)


# ─── Reglas especiales (activación / desactivación / override) ───────────────


def _regla(make_coords, rule_id="SR1", start=(0, 52), end=(0, 120), **rules):
    return SpecialRule(
        rule_id=rule_id,
        nodes=[make_coords(*start), make_coords(*end)],
        radius_m=8.0,
        rules=rules or {"speed_limit": 10.0},
    )


class TestOrquestadorSpecialRules:
    def test_la_activacion_aplica_el_override_en_el_siguiente_scan(
        self, ai_control, populate_graph, make_road, make_ai, make_coords
    ):
        scanner, mode = _scanner_en_r1(ai_control, populate_graph, make_road, make_ai)
        regla = _regla(make_coords, speed_limit=10.0)  # inicio (0,52), a 2 m de la IA
        ai_control.map_recorder.special_rules = {"SR1": regla}

        # 1ª pasada: la regla se ACTIVA (al final del scan), pero la base de esta
        # pasada ya estaba calculada → aún se pide la velocidad sin override.
        ai_control._update_traffic_behavior(scanner)
        assert "SR1" in mode.active_special_rules
        assert scanner.extra["aic"].speed_request == pytest.approx(BASE_KMH)

        # 2ª pasada (compuerta reabierta): el override ya rige la base:
        # limite=10, min=5 → base = 5 + (10-5)*0.5 = 7.5.
        mode._last_radar_time = 0.0
        ai_control._update_traffic_behavior(scanner)
        assert scanner.extra["aic"].speed_request == pytest.approx(7.5)

    def test_la_desactivacion_en_el_nodo_final_mantiene_el_override_esa_pasada(
        self, ai_control, populate_graph, make_road, make_ai, make_coords
    ):
        scanner, mode = _scanner_en_r1(ai_control, populate_graph, make_road, make_ai)
        # Nodo final (0,52) a 2 m de la IA; el inicial lejos (la regla ya está activa).
        regla = _regla(make_coords, start=(0, 200), end=(0, 52), speed_limit=10.0)
        ai_control.map_recorder.special_rules = {"SR1": regla}
        mode.active_special_rules.append("SR1")

        ai_control._update_traffic_behavior(scanner)

        # Se desactiva al final de la pasada, pero la base de ESTA pasada ya
        # llevaba el override (misma asimetría que la activación, congelada aquí).
        assert "SR1" not in mode.active_special_rules
        assert scanner.extra["aic"].speed_request == pytest.approx(7.5)


# ═══════════════════════════════════════════════════════════════════════════
# Bloque 8.3 — CONDUCTA de la cesión de paso (cesión por RoadLink, diseño S38)
# ═══════════════════════════════════════════════════════════════════════════
#
# Escenario del cruce (metros; +Y Norte, +X Este; heading LFS 0=N, 90=-X/O,
# 180=S, 270=+X/E):
#
#   R1 (from): recta en +Y, x=0, y 0..90 (la IA que cede sube por aquí).
#   R2 (to):   recta en +X, y=100, x -50..50 → el punto de unión (10,100) es
#              su nodo 6. El tráfico vigilado circula hacia +X (viene del oeste).
#   Link "R1->R2": (0,90) → (2,94) → (6,98) → (10,100). Su ÚLTIMO nodo es el
#              punto de unión. yield_line = [(-2,93), (2,93)]: cruza el carril
#              de R1 en y=93; el punto de unión queda al otro lado (cruzarla
#              compromete la maniobra).
#   R3 (solo tests de zona): recta en -Y, x=5, y 140..60 (cruza el punto de
#              conflicto de la zona "Z" en (5,100) bajando hacia el sur).


def _cruce(
    ai_control,
    populate_graph,
    make_road,
    make_road_link,
    make_coords,
    con_linea=True,
    yield_time_s=None,
    yield_type=YieldType.YIELD,
    con_r3=False,
):
    """Construye el cruce de arriba y devuelve el RoadLink R1->R2."""
    roads = [
        make_road("R1", _pts_y()),
        make_road("R2", [(x, 100.0) for x in range(-50, 51, 10)]),
    ]
    if con_r3:
        roads.append(make_road("R3", [(5.0, y) for y in range(140, 59, -10)]))
    # El primer tramo del link sube recto en +Y: así la línea DERIVADA del
    # yield_point (perpendicular a la tangente) sale horizontal, en y=93.
    link = make_road_link("R1", "R2", [(0, 90), (0, 94), (6, 98), (10, 100)])
    if con_linea:
        link.yield_type = yield_type
        link.yield_point = make_coords(0, 93)
    link.yield_time_s = yield_time_s
    populate_graph(ai_control.map_recorder, roads=roads, road_links=[link])
    return link


def _scanner_hacia_cruce(make_ai, y_m=60.0, speed_kmh=30.0):
    """IA subiendo por R1 hacia el cruce, con el link R1->R2 ya planificado."""
    scanner = make_ai(plid=1, x_m=0, y_m=y_m, speed_kmh=speed_kmh)
    mode = FreeroamMode(
        current_type="Road",
        current_id="R1",
        current_road_id="R1",
        node_index=min(9, int(y_m // 10) + 1),
        next_link_id="R1->R2",
        next_link_type="RoadLink",
    )
    scanner.extra["aic"].active_mode = mode
    return scanner, mode


def _scanner_en_link(make_ai, x_m, y_m, speed_kmh=10.0, node_index=1):
    """IA ya dentro del RoadLink R1->R2."""
    scanner = make_ai(plid=1, x_m=x_m, y_m=y_m, speed_kmh=speed_kmh)
    mode = FreeroamMode(
        current_type="RoadLink",
        current_id="R1->R2",
        current_road_id="R1",
        node_index=node_index,
    )
    scanner.extra["aic"].active_mode = mode
    return scanner, mode


def _amenaza_en_r2(make_ai, make_behavior, x_m=-30.0, speed_kmh=40.0, plid=2):
    """Coche circulando por R2 hacia el este (hacia el punto de unión)."""
    return _place_ai(
        make_ai,
        make_behavior,
        plid,
        x_m,
        100,
        speed_kmh=speed_kmh,
        heading_deg=270.0,  # +X (Este)
        mode_fields={"current_id": "R2", "node_index": 3},
    )


def _acc_de_cesion(ai_control, dist_a_linea_m, scanner, base_kmh=BASE_KMH):
    """La velocidad de freno esperada: ACC contra un 'coche parado' colocado
    PARADA_ABSOLUTA_M más allá de la línea (así el morro acaba EN la línea).

    La velocidad se lee de la telemetría del scanner (cuantizada en unidades
    LFS), que es la que usa el orquestador para derivar min/max por time-gap.
    """
    v_ms = scanner.player.telemetry.speed.speed_kmh / 3.6
    return ai_control._apply_adaptive_cruise_control(
        base_kmh,
        0.0,
        dist_a_linea_m + PARADA_ABSOLUTA_M,
        max(8.0, v_ms * 2.0),
        max(15.0, v_ms * 5.0),
    )


class TestCesionEndToEnd:
    """La cesión integrada en `_update_traffic_behavior` (cableado completo)."""

    def test_amenaza_en_el_to_road_frena_hacia_la_linea(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        _cruce(ai_control, populate_graph, make_road, make_road_link, make_coords)
        scanner, mode = _scanner_hacia_cruce(make_ai)  # (0,60): a 33 m de la línea
        _set_ais(ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior))

        ai_control._update_traffic_behavior(scanner)

        esperado = _acc_de_cesion(ai_control, 33.0, scanner)
        assert scanner.extra["aic"].speed_request == pytest.approx(esperado)
        assert scanner.extra["aic"].speed_request < BASE_KMH
        assert mode.yield_active is True
        assert mode.yield_link_id == "R1->R2"

    def test_sin_amenaza_no_cede(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
    ):
        _cruce(ai_control, populate_graph, make_road, make_road_link, make_coords)
        scanner, mode = _scanner_hacia_cruce(make_ai)
        _set_ais(ai_control, scanner)

        ai_control._update_traffic_behavior(scanner)

        assert scanner.extra["aic"].speed_request == pytest.approx(BASE_KMH)
        assert mode.yield_active is False
        assert mode.yield_link_id is None

    def test_link_sin_cesion_ignora_el_trafico_cruzado(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        # El campo nace vacío ⇒ ese giro NO cede (diseño S38, punto 1).
        _cruce(
            ai_control,
            populate_graph,
            make_road,
            make_road_link,
            make_coords,
            con_linea=False,
        )
        scanner, mode = _scanner_hacia_cruce(make_ai)
        _set_ais(ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior))

        ai_control._update_traffic_behavior(scanner)

        assert scanner.extra["aic"].speed_request == pytest.approx(BASE_KMH)
        assert mode.yield_active is False

    def test_lejos_de_la_linea_todavia_no_cede(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        _cruce(ai_control, populate_graph, make_road, make_road_link, make_coords)
        # A 73 m de la línea > alcance max(15, v·5s)=41.7 m → aún no toca frenar.
        scanner, mode = _scanner_hacia_cruce(make_ai, y_m=20.0)
        _set_ais(ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior))

        ai_control._update_traffic_behavior(scanner)

        assert scanner.extra["aic"].speed_request == pytest.approx(BASE_KMH)
        assert mode.yield_active is False

    def test_dentro_del_link_antes_de_la_linea_sigue_cediendo(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        _cruce(ai_control, populate_graph, make_road, make_road_link, make_coords)
        # Ya dentro del enlace pero ANTES de la línea (y=91.5 < 93), casi parada.
        scanner, mode = _scanner_en_link(make_ai, 0.0, 91.5, speed_kmh=10.0)
        _set_ais(ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior))

        ai_control._update_traffic_behavior(scanner)

        esperado = _acc_de_cesion(ai_control, 1.5, scanner)
        assert scanner.extra["aic"].speed_request == pytest.approx(esperado)
        assert scanner.extra["aic"].speed_request < 5.0  # prácticamente parar
        assert mode.yield_active is True

    def test_compromiso_pasada_la_linea_no_frena_en_el_cruce(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        _cruce(ai_control, populate_graph, make_road, make_road_link, make_coords)
        # Pasada la línea (y=95 > 93, mismo lado que el punto de unión): la
        # maniobra está comprometida — NO se frena en mitad del cruce aunque
        # el vigilado siga viniendo (diseño S38, punto 4).
        scanner, mode = _scanner_en_link(make_ai, 3.0, 95.0, speed_kmh=20.0)
        mode.yield_active = True  # venía cediendo hasta cruzar
        mode.yield_link_id = "R1->R2"
        _set_ais(ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior))

        ai_control._update_traffic_behavior(scanner)

        assert scanner.extra["aic"].speed_request == pytest.approx(BASE_KMH)
        assert mode.yield_active is False
        assert mode.yield_link_id is None

    def test_histeresis_mantiene_y_luego_suelta(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        _cruce(ai_control, populate_graph, make_road, make_road_link, make_coords)
        scanner, mode = _scanner_hacia_cruce(make_ai)
        _set_ais(ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior))

        # 1) Detección: arma el hold (reusa la histéresis del fix (5), S33).
        ai_control._update_traffic_behavior(scanner)
        assert mode.yield_active is True

        # 2) La amenaza desaparece pero el hold no expiró → se sigue cediendo
        #    (sin acelerón contra el freno de mano por un tick sin detección).
        _set_ais(ai_control, scanner)
        mode._last_radar_time = 0.0
        ai_control._update_traffic_behavior(scanner)
        assert mode.yield_active is True

        # 3) Hold expirado y sin detección → suelta y limpia el estado.
        mode._yield_hold_until = time.time() - 1.0
        mode._last_radar_time = 0.0
        ai_control._update_traffic_behavior(scanner)
        assert mode.yield_active is False
        assert mode.yield_link_id is None
        assert scanner.extra["aic"].speed_request == pytest.approx(BASE_KMH)

    def test_el_default_global_de_config_manda_si_el_link_no_trae_t(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        _cruce(ai_control, populate_graph, make_road, make_road_link, make_coords)
        scanner, mode = _scanner_hacia_cruce(make_ai)
        # Coche a 60 m del punto a 40 km/h → t = 5.4 s: fuera de la ventana
        # por defecto (4 s)…
        lejano = _amenaza_en_r2(make_ai, make_behavior, x_m=-50.0)
        _set_ais(ai_control, scanner, lejano)

        ai_control._update_traffic_behavior(scanner)
        assert mode.yield_active is False

        # …pero dentro si la config global sube la ventana a 10 s.
        ai_control.config["yield_time_s"] = 10.0
        mode._last_radar_time = 0.0
        ai_control._update_traffic_behavior(scanner)
        assert mode.yield_active is True


class TestVigiladosDeLaCesion:
    """Unitarios de `_yield_threat_detected`: QUÉ cuenta como amenaza."""

    def _setup(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        **kwargs,
    ):
        link = _cruce(
            ai_control, populate_graph, make_road, make_road_link, make_coords, **kwargs
        )
        scanner, _ = _scanner_hacia_cruce(make_ai)
        return link, scanner

    def test_coche_acercandose_por_el_to_road_es_amenaza(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        link, scanner = self._setup(
            ai_control, populate_graph, make_road, make_road_link, make_coords, make_ai
        )
        # A 40 m del punto de unión a 40 km/h → t = 3.6 s < 4 s.
        _set_ais(ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior))

        assert ai_control._yield_threat_detected(scanner, link) is True

    def test_coche_parado_en_el_to_road_no_es_amenaza(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        # Cambio DELIBERADO respecto al modelo viejo (que le ponía un suelo de
        # 0.5 m/s y lo contaba): un coche detenido no viene (t = inf).
        link, scanner = self._setup(
            ai_control, populate_graph, make_road, make_road_link, make_coords, make_ai
        )
        _set_ais(
            ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior, speed_kmh=0.0)
        )

        assert ai_control._yield_threat_detected(scanner, link) is False

    def test_coche_que_ya_paso_el_punto_no_es_amenaza(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        link, scanner = self._setup(
            ai_control, populate_graph, make_road, make_road_link, make_coords, make_ai
        )
        # En (30,100), nodo 8 > punto de unión (nodo 6): ya pasó — se aleja.
        _set_ais(ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior, x_m=30.0))

        assert ai_control._yield_threat_detected(scanner, link) is False

    def test_coche_a_contramano_alejandose_no_es_amenaza(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        link, scanner = self._setup(
            ai_control, populate_graph, make_road, make_road_link, make_coords, make_ai
        )
        # Mismo sitio que la amenaza normal pero mirando al OESTE (se aleja
        # del punto de unión aunque el arco diga que "viene").
        contramano = _place_ai(
            make_ai,
            make_behavior,
            2,
            -30,
            100,
            speed_kmh=40,
            heading_deg=90.0,  # -X (Oeste)
            mode_fields={"current_id": "R2", "node_index": 2},
        )
        _set_ais(ai_control, scanner, contramano)

        assert ai_control._yield_threat_detected(scanner, link) is False

    def test_humano_en_el_to_road_tambien_cuenta(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_player,
        make_telemetry,
    ):
        # Los humanos no publican topología: se localizan por posición.
        link, scanner = self._setup(
            ai_control, populate_graph, make_road, make_road_link, make_coords, make_ai
        )
        _set_ais(ai_control, scanner)
        _place_human(
            ai_control,
            make_player,
            make_telemetry,
            plid=7,
            x_m=-30,
            y_m=100,
            speed_kmh=40,
            heading_deg=270.0,
        )

        assert ai_control._yield_threat_detected(scanner, link) is True

    def test_el_t_del_link_hace_override_del_default(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        # Con T=2 s, el coche a t=3.6 s deja de ser amenaza.
        link, scanner = self._setup(
            ai_control,
            populate_graph,
            make_road,
            make_road_link,
            make_coords,
            make_ai,
            yield_time_s=2.0,
        )
        _set_ais(ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior))

        assert ai_control._yield_threat_detected(scanner, link) is False


class TestVigiladosPorGeometria:
    """El link vigila TODA road que su trazado pisa, sin zona de por medio (S44).

    Es la promesa central del rediseño: lo que antes exigía apuntar a una zona
    con `yield_zone_id` ahora sale solo de la geometría. R3 (vertical por x=5)
    la cruza el trazado del link en ~(5, 97.3) sin ser la `to_road`.
    """

    def _setup(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        yield_time_s=None,
    ):
        link = _cruce(
            ai_control,
            populate_graph,
            make_road,
            make_road_link,
            make_coords,
            yield_time_s=yield_time_s,
            con_r3=True,
        )
        scanner, _ = _scanner_hacia_cruce(make_ai)
        return link, scanner

    def _cruzado_por_r3(self, make_ai, make_behavior, y_m=130.0, speed_kmh=40.0):
        """Coche bajando por R3 hacia el punto de conflicto (~5, 97)."""
        return _place_ai(
            make_ai,
            make_behavior,
            3,
            5,
            y_m,
            speed_kmh=speed_kmh,
            heading_deg=180.0,  # -Y (Sur)
            mode_fields={"current_id": "R3", "node_index": 1},
        )

    def test_el_trazado_cruza_r3_asi_que_r3_se_vigila(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        link, scanner = self._setup(
            ai_control, populate_graph, make_road, make_road_link, make_coords, make_ai
        )
        # A 30 m del punto a 40 km/h → t = 2.7 s < 4: amenaza. Va por R3, que
        # NO es el to_road — con el modelo viejo hacía falta una zona.
        _set_ais(ai_control, scanner, self._cruzado_por_r3(make_ai, make_behavior))

        assert ai_control._yield_threat_detected(scanner, link) is True

    def test_una_road_que_el_trazado_no_pisa_no_se_vigila(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        """Control: sin R3 en el mapa, el mismo coche deja de contar."""
        link, scanner = self._setup(
            ai_control, populate_graph, make_road, make_road_link, make_coords, make_ai
        )
        del ai_control.map_recorder.roads["R3"]
        ai_control.map_recorder._invalidate_road_index()
        _set_ais(ai_control, scanner, self._cruzado_por_r3(make_ai, make_behavior))

        assert ai_control._yield_threat_detected(scanner, link) is False

    def test_el_que_va_por_la_from_road_se_excluye(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        # Viene por R1 (la vía que la IA deja atrás): de esa no se cede — si
        # contara, tus propios seguidores te dejarían clavado en la línea.
        link, scanner = self._setup(
            ai_control, populate_graph, make_road, make_road_link, make_coords, make_ai
        )
        seguidor = _place_ai(
            make_ai,
            make_behavior,
            3,
            0,
            40,
            speed_kmh=60,
            heading_deg=0.0,  # +Y, hacia el cruce
            mode_fields={"current_id": "R1", "node_index": 5},
        )
        _set_ais(ai_control, scanner, seguidor)

        assert ai_control._yield_threat_detected(scanner, link) is False

    def test_parado_en_r3_no_es_amenaza(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        link, scanner = self._setup(
            ai_control, populate_graph, make_road, make_road_link, make_coords, make_ai
        )
        _set_ais(
            ai_control,
            scanner,
            self._cruzado_por_r3(make_ai, make_behavior, speed_kmh=0.0),
        )

        assert ai_control._yield_threat_detected(scanner, link) is False

    def test_el_t_del_link_manda_tambien_en_el_cruce_geometrico(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        # Con T = 2 s, el cruzado a t = 2.7 s deja de ser amenaza.
        link, scanner = self._setup(
            ai_control,
            populate_graph,
            make_road,
            make_road_link,
            make_coords,
            make_ai,
            yield_time_s=2.0,
        )
        _set_ais(ai_control, scanner, self._cruzado_por_r3(make_ai, make_behavior))

        assert ai_control._yield_threat_detected(scanner, link) is False

    def test_un_puente_sobre_el_cruce_no_se_vigila(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        """R3 elevada 10 m: pasa POR ENCIMA, no es un cruce (tolerancia en Z)."""
        link, scanner = self._setup(
            ai_control, populate_graph, make_road, make_road_link, make_coords, make_ai
        )
        for node in ai_control.map_recorder.roads["R3"].nodes:
            node.z_m = 10.0
        ai_control.map_recorder._invalidate_road_index()
        _set_ais(ai_control, scanner, self._cruzado_por_r3(make_ai, make_behavior))

        assert ai_control._yield_threat_detected(scanner, link) is False


class TestStop:
    """`STOP` (S44): para SIEMPRE, aguanta ~1 s y luego evalúa como `YIELD`."""

    def _stop(self, ai_control, populate_graph, make_road, make_road_link, make_coords):
        return _cruce(
            ai_control,
            populate_graph,
            make_road,
            make_road_link,
            make_coords,
            yield_type=YieldType.STOP,
        )

    def test_para_aunque_no_venga_nadie(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
    ):
        """La diferencia con YIELD: sin tráfico, un YIELD ni levanta el pie."""
        self._stop(ai_control, populate_graph, make_road, make_road_link, make_coords)
        scanner, mode = _scanner_hacia_cruce(make_ai)
        _set_ais(ai_control, scanner)

        ai_control._update_traffic_behavior(scanner)

        assert mode.yield_active is True
        assert scanner.extra["aic"].speed_request < BASE_KMH

    def test_yield_sin_trafico_no_frena_pero_stop_si(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
    ):
        """El contraste que define el toggle, en un solo test."""
        _cruce(
            ai_control,
            populate_graph,
            make_road,
            make_road_link,
            make_coords,
            yield_type=YieldType.YIELD,
        )
        scanner, mode = _scanner_hacia_cruce(make_ai)
        _set_ais(ai_control, scanner)
        ai_control._update_traffic_behavior(scanner)
        assert mode.yield_active is False

        ai_control.map_recorder.road_links["R1->R2"].yield_type = YieldType.STOP
        mode._last_radar_time = 0.0
        ai_control._update_traffic_behavior(scanner)
        assert mode.yield_active is True

    def test_none_no_cede_aunque_haya_amenaza(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        _cruce(
            ai_control,
            populate_graph,
            make_road,
            make_road_link,
            make_coords,
            yield_type=YieldType.NONE,
        )
        scanner, mode = _scanner_hacia_cruce(make_ai)
        _set_ais(ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior))

        ai_control._update_traffic_behavior(scanner)

        assert mode.yield_active is False
        assert scanner.extra["aic"].speed_request == pytest.approx(BASE_KMH)

    def test_rodando_no_arranca_el_reloj_de_la_parada(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
    ):
        link = self._stop(
            ai_control, populate_graph, make_road, make_road_link, make_coords
        )
        _, mode = _scanner_en_link(make_ai, 0.0, 91.5, speed_kmh=10.0)
        now = time.time()

        # Primer tick ante el STOP: se apunta el link y se frena.
        assert ai_control._stop_pending(mode, link, 10.0 / 3.6, now) is True
        assert mode.yield_stop_link_id == "R1->R2"
        # Sigue rodando: la cuenta no empieza.
        assert ai_control._stop_pending(mode, link, 10.0 / 3.6, now) is True
        assert mode._yield_stopped_since == 0.0

    def test_al_detenerse_arranca_el_reloj_y_aguanta(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
    ):
        link = self._stop(
            ai_control, populate_graph, make_road, make_road_link, make_coords
        )
        _, mode = _scanner_en_link(make_ai, 0.0, 91.5, speed_kmh=0.0)
        now = time.time()

        ai_control._stop_pending(mode, link, 0.0, now)  # apunta el link
        assert ai_control._stop_pending(mode, link, 0.0, now) is True
        assert mode._yield_stopped_since == pytest.approx(now)
        # Dentro del aguante (1 s por defecto) se sigue parado.
        assert ai_control._stop_pending(mode, link, 0.0, now + 0.5) is True
        assert mode.yield_stop_done_link_id is None

    def test_cumplido_el_aguante_deja_de_estar_pendiente(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
    ):
        link = self._stop(
            ai_control, populate_graph, make_road, make_road_link, make_coords
        )
        _, mode = _scanner_en_link(make_ai, 0.0, 91.5, speed_kmh=0.0)
        now = time.time()

        ai_control._stop_pending(mode, link, 0.0, now)
        ai_control._stop_pending(mode, link, 0.0, now)

        assert ai_control._stop_pending(mode, link, 0.0, now + 1.5) is False
        assert mode.yield_stop_done_link_id == "R1->R2"
        # Y ya no vuelve a exigir parada en ESTE link (evalúa como YIELD).
        assert ai_control._stop_pending(mode, link, 0.0, now + 99.0) is False

    def test_el_aguante_sale_de_config(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
    ):
        link = self._stop(
            ai_control, populate_graph, make_road, make_road_link, make_coords
        )
        _, mode = _scanner_en_link(make_ai, 0.0, 91.5, speed_kmh=0.0)
        ai_control.config["yield_stop_hold_s"] = 5.0
        now = time.time()

        ai_control._stop_pending(mode, link, 0.0, now)
        ai_control._stop_pending(mode, link, 0.0, now)

        assert ai_control._stop_pending(mode, link, 0.0, now + 1.5) is True
        assert ai_control._stop_pending(mode, link, 0.0, now + 5.5) is False

    def test_cumplida_la_parada_el_stop_evalua_como_yield(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
        make_behavior,
    ):
        self._stop(ai_control, populate_graph, make_road, make_road_link, make_coords)
        scanner, mode = _scanner_hacia_cruce(make_ai)
        mode.yield_stop_done_link_id = "R1->R2"  # ya cumplió su parada

        # Sin tráfico: como un YIELD, no cede.
        _set_ais(ai_control, scanner)
        ai_control._update_traffic_behavior(scanner)
        assert mode.yield_active is False

        # Con tráfico vigilado: cede, ahora sí por la amenaza.
        _set_ais(ai_control, scanner, _amenaza_en_r2(make_ai, make_behavior))
        mode._last_radar_time = 0.0
        ai_control._update_traffic_behavior(scanner)
        assert mode.yield_active is True

    def test_otro_link_exige_parar_otra_vez(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_coords,
        make_ai,
    ):
        link = self._stop(
            ai_control, populate_graph, make_road, make_road_link, make_coords
        )
        _, mode = _scanner_en_link(make_ai, 0.0, 91.5, speed_kmh=0.0)
        mode.yield_stop_done_link_id = "OTRO->LINK"

        assert ai_control._stop_pending(mode, link, 0.0, time.time()) is True


class TestDistanciaALaLinea:
    """Unitarios de `_dist_to_yield_line_m` (distancia 2D a la polilínea)."""

    def test_distancia_minima_entre_los_segmentos(self, ai_control, make_coords):
        # Polilínea en L: (0,0)→(10,0)→(10,10). Desde (14,8) el segmento
        # vertical queda a 4 m (el horizontal a ~8.9).
        linea = [make_coords(0, 0), make_coords(10, 0), make_coords(10, 10)]
        assert ai_control._dist_to_yield_line_m(14.0, 8.0, linea) == pytest.approx(4.0)

    def test_sobre_la_linea_es_cero(self, ai_control, make_coords):
        linea = [make_coords(-2, 93), make_coords(2, 93)]
        assert ai_control._dist_to_yield_line_m(0.0, 93.0, linea) == pytest.approx(0.0)

    def test_linea_inutilizable_es_infinita(self, ai_control, make_coords):
        assert ai_control._dist_to_yield_line_m(0.0, 0.0, []) == math.inf
        assert ai_control._dist_to_yield_line_m(0.0, 0.0, [make_coords(1, 1)]) == (
            math.inf
        )
