"""
Tests de CARACTERIZACIÃ“N de _TrafficMixin (insims/ai_control/traffic/).

Congelan el comportamiento ACTUAL de la lÃ³gica DETERMINISTA de trÃ¡fico antes de
tocar nada (red de seguridad, MODUS_OPERANDI Â§3). Cubre, de menor a mayor setup:

  - MatemÃ¡tica pura (sin grafo ni estado): `_apply_adaptive_cruise_control` (el
    ACC de 3 zonas), `_estimate_overtake_distance`, `_get_relative_dist_to_cover`,
    `_calc_path_length`, `_get_lookahead_point`.

El gran orquestador `_update_traffic_behavior` NO se cubre a propÃ³sito: usa
`time.time()` y muta muchÃ­simo estado del `mode` (mismo criterio que los mÃ©todos
gordos de navigation.py `_update_freeroam_navigation` / `_get_radar_speed_limit`).

Sobre el "PARCHE DE SEGURIDAD MATEMÃTICO" del ACC: los 2 tests que lo congelaban se
reescribieron en S21, cuando el parche se ELIMINÃ“ (ver DIAGNOSTICO Â§ P25). Hoy estos
tests fijan el ACC sin parche: los `min_dist`/`max_dist` del llamador se respetan.

Los mÃ©todos viven repartidos por responsabilidad en el paquete `traffic/` (radar,
cruise_control, zones, overtake, paths, orchestrator); `_TrafficMixin` los compone.
Los tests los ejercitan a travÃ©s de `AIControl` (fixture `ai_control`), asÃ­ que el
reparto interno les es transparente.

Convenciones LFS relevantes (mismas que test_physics / test_navigation):
  - Coordenadas en metros; `make_coords` guarda en unidades LFS (1 m = 65536 units).
  - Velocidades en km/h; el ACC trabaja internamente pasando a m/s (Ã·3.6).
"""

import random

import pytest

from insims.ai_control.nav_modes.freeroam.enums import AIManeuverState, TrafficRule
from insims.ai_control.nav_modes.freeroam.geometry import (
    apply_antilag_window,
    evaluate_dynamic_capture,
)
from insims.ai_control.nav_modes.freeroam.graph import IntersectionZone
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from insims.ai_control.traffic.radar import _is_near_link_entry, _lane_chain_ids
from insims.users_management.main import Coordinates
from lfs_insim.insim_enums import CSVAL
from lfs_insim.utils import lfs_pos_to_meters


def _coords_xy(x_m: float, y_m: float) -> Coordinates:
    """Coordinates desde metros (mismo constructor que `make_coords` del conftest)."""
    return Coordinates(
        lfs_pos_to_meters(x_m, rev=True),
        lfs_pos_to_meters(y_m, rev=True),
        lfs_pos_to_meters(0.0, rev=True),
    )


LEFT = CSVAL.INDICATORS.LEFT
RIGHT = CSVAL.INDICATORS.RIGHT

# Heading en unidades LFS (0..65536 = una vuelta): 0 = mirando a +Y (Norte),
# 32768 = mirando a -Y (Sur). Mismos ejes que test_navigation (+Y Norte, +X Oeste).
HEADING_NORTH = 0
HEADING_SOUTH = 32768


# â”€â”€â”€ _apply_adaptive_cruise_control: ACC de 3 zonas (S21: parche eliminado) â”€â”€â”€â”€
#
# Firma: (base_speed_kmh, closest_speed_kmh, closest_dist_m, min_dist_m, max_dist_m)
# Los min/max del llamador se respetan tal cual (el viejo "PARCHE DE SEGURIDAD
# MATEMÃTICO" que los reescribÃ­a se eliminÃ³ en S21; ver DIAGNOSTICO Â§ P25). Zonas:
#   critical = max(5.0, min_dist*0.5)   (suelo duro de parada incluido)
#   ROJA    (dist â‰¤ critical)          â†’ 0.0
#   NARANJA (critical < dist â‰¤ min)    â†’ closest_speed * ratio; <2 km/h â†’ 0.0 (anti-creep)
#   AMARILLA(min < dist < max)         â†’ lerp hacia match_speed = min(closest, base)
#   fuera   (dist â‰¥ max)               â†’ base_speed
# Ratios acotados a [0,1] y denominadores blindados con Îµ â†’ nunca ZeroDivisionError.


class TestApplyAdaptiveCruiseControl:
    # Setup "limpio": min=10, max=20 â‡’ el parche NO altera nada (critical=5,
    # minâ‰¥7 y maxâ‰¥15 ya se cumplen), asÃ­ cada zona se razona directamente.

    def test_zona_roja_para_en_seco(self, ai_control):
        # dist == critical (5) â†’ parada absoluta.
        assert ai_control._apply_adaptive_cruise_control(50, 30, 5.0, 10, 20) == 0.0
        # dist < critical â†’ tambiÃ©n 0.
        assert ai_control._apply_adaptive_cruise_control(50, 30, 3.0, 10, 20) == 0.0

    def test_zona_naranja_frena_proporcional_a_la_distancia(self, ai_control):
        # dist=7 en (5, 10]: ratio=(7-5)/(10-5)=0.4 â†’ 30*0.4 = 12 km/h.
        got = ai_control._apply_adaptive_cruise_control(50, 30, 7.0, 10, 20)
        assert got == pytest.approx(12.0)

    def test_zona_naranja_en_el_borde_min_iguala_al_lider(self, ai_control):
        # dist == min_dist (10): ratio=1.0 â†’ target = closest_speed exacto.
        got = ai_control._apply_adaptive_cruise_control(50, 30, 10.0, 10, 20)
        assert got == pytest.approx(30.0)

    def test_zona_naranja_anticreep_para_si_baja_de_2(self, ai_control):
        # dist=6, closest=3: ratio=0.2 â†’ 0.6 km/h < 2 â†’ frena en seco (0.0).
        got = ai_control._apply_adaptive_cruise_control(50, 3, 6.0, 10, 20)
        assert got == 0.0

    def test_zona_amarilla_interpola_hacia_el_lider(self, ai_control):
        # dist=15 en (10, 20): ratio=0.5, match=min(30,50)=30 â†’ 30+(50-30)*0.5 = 40.
        got = ai_control._apply_adaptive_cruise_control(50, 30, 15.0, 10, 20)
        assert got == pytest.approx(40.0)

    def test_zona_amarilla_lider_mas_rapido_no_supera_base(self, ai_control):
        # closest=80 > base=50: match=min(80,50)=50 â†’ target=50 (nunca por encima de base).
        got = ai_control._apply_adaptive_cruise_control(50, 80, 15.0, 10, 20)
        assert got == pytest.approx(50.0)

    def test_fuera_de_rango_va_a_velocidad_base(self, ai_control):
        # dist > max â†’ base. Y en el borde exacto dist==max tambiÃ©n (el test es `< max`).
        assert ai_control._apply_adaptive_cruise_control(50, 30, 25.0, 10, 20) == 50.0
        assert ai_control._apply_adaptive_cruise_control(50, 30, 20.0, 10, 20) == 50.0

    def test_critical_escala_con_min_dist_grande(self, ai_control):
        # min=20 â†’ critical=max(5, 10)=10. dist==10 â†’ roja (0.0); dist=11 â†’ naranja.
        assert ai_control._apply_adaptive_cruise_control(50, 30, 10.0, 20, 30) == 0.0
        # ratio=(11-10)/(20-10)=0.1 â†’ 30*0.1 = 3.0.
        got = ai_control._apply_adaptive_cruise_control(50, 30, 11.0, 20, 30)
        assert got == pytest.approx(3.0)

    def test_min_pequeno_no_se_reescribe_cae_en_amarilla(self, ai_control):
        # S21: el min del llamador (2) YA NO se empuja a 7. critical=max(5, 1)=5.
        # dist=6 > min=2 â†’ AMARILLA: ratio=(6-2)/(20-2)=0.222, match=30 â†’
        # 30+(50-30)*0.222 = 34.44. (Con el viejo parche caÃ­a en NARANJA = 15.)
        got = ai_control._apply_adaptive_cruise_control(50, 30, 6.0, 2, 20)
        assert got == pytest.approx(34.4444, abs=1e-3)

    def test_max_menor_que_min_no_se_reescribe(self, ai_control):
        # S21: max=12 YA NO se empuja a 15. dist=14 â‰¥ max=12 â†’ fuera de rango â†’
        # base=50. (Con el viejo parche caÃ­a en AMARILLA = 46.)
        got = ai_control._apply_adaptive_cruise_control(50, 30, 14.0, 10, 12)
        assert got == pytest.approx(50.0)

    def test_min_en_el_suelo_no_lanza(self, ai_control):
        # S21: a baja velocidad min llega a su suelo (5) y critical=max(5, 2.5)=5,
        # con lo que la zona naranja se colapsa. NO hay ZeroDivisionError: distâ‰¤5 â†’
        # parada; dist>5 â†’ amarilla directamente. (Antes el parche empujaba min a 7
        # para crear una franja naranja artificial y asÃ­ tapar el denominador.)
        assert ai_control._apply_adaptive_cruise_control(50, 30, 5.0, 5, 15) == 0.0
        # dist=10 en amarilla: ratio=(10-5)/(15-5)=0.5, match=min(30,50)=30 â†’ 40.
        got = ai_control._apply_adaptive_cruise_control(50, 30, 10.0, 5, 15)
        assert got == pytest.approx(40.0)

    def test_max_igual_a_min_no_lanza(self, ai_control):
        # Denominador amarillo (max-min) = 0 blindado con Îµ: no ZeroDivisionError.
        # dist=12 > min=10 y â‰¥ max=10 â†’ fuera â†’ base. dist=10 â†’ borde de naranja.
        assert ai_control._apply_adaptive_cruise_control(50, 30, 12.0, 10, 10) == 50.0
        got = ai_control._apply_adaptive_cruise_control(50, 30, 10.0, 10, 10)
        assert got == pytest.approx(30.0)  # dist==min â†’ naranja, ratio=1 â†’ closest


# â”€â”€â”€ _estimate_overtake_distance: asfalto y tiempo para adelantar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#
# Firma: (overtake_lane_speed_kmh, target_vehicle_speed_kmh, relative_dist_to_cover_m)
# â†’ (metros_de_asfalto, segundos). Si el delta de velocidad â‰¤ 0.1 m/s â†’ (inf, inf).


class TestEstimateOvertakeDistance:
    def test_caso_normal(self, ai_control):
        # 72 km/h (20 m/s) vs 36 km/h (10 m/s), cubrir 50 m: delta=10, t=5 s, asfalto=100 m.
        dist, t = ai_control._estimate_overtake_distance(72, 36, 50)
        assert dist == pytest.approx(100.0)
        assert t == pytest.approx(5.0)

    def test_delta_nulo_es_infinito(self, ai_control):
        # Misma velocidad â†’ delta 0 â‰¤ 0.1 â†’ (inf, inf).
        assert ai_control._estimate_overtake_distance(36, 36, 50) == (
            float("inf"),
            float("inf"),
        )

    def test_carril_mas_lento_es_infinito(self, ai_control):
        # El carril de adelantamiento es mÃ¡s lento que el objetivo â†’ imposible.
        assert ai_control._estimate_overtake_distance(36, 72, 50) == (
            float("inf"),
            float("inf"),
        )

    def test_objetivo_parado_usa_suelo_de_velocidad(self, ai_control):
        # target=0 â†’ target_ms = max(0, 0.1) = 0.1. 36 km/h = 10 m/s â†’ delta=9.9.
        dist, t = ai_control._estimate_overtake_distance(36, 0, 99)
        assert t == pytest.approx(99 / 9.9)
        assert dist == pytest.approx(10.0 * (99 / 9.9))


# â”€â”€â”€ _get_relative_dist_to_cover: distancia total a cubrir (convoy) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestGetRelativeDistToCover:
    def test_lista_vacia_es_cero(self, ai_control):
        assert ai_control._get_relative_dist_to_cover([]) == 0.0

    def test_un_solo_coche(self, ai_control):
        # last=first=10 â†’ 10 + 10 + extra(5) = 25.
        assert ai_control._get_relative_dist_to_cover([10.0], extra_dist=5) == 25.0

    def test_convoy_pegado_se_agrupa(self, ai_control):
        # [10,15]: gap=5 â‰¤ first+extra(15) â†’ last=15 â†’ 15 + 10 + 5 = 30.
        assert (
            ai_control._get_relative_dist_to_cover([10.0, 15.0], extra_dist=5) == 30.0
        )

    def test_hueco_grande_corta_el_convoy(self, ai_control):
        # [10,40]: gap=30 > first+extra(15) â†’ break con last=10 â†’ 10 + 10 + 5 = 25.
        assert (
            ai_control._get_relative_dist_to_cover([10.0, 40.0], extra_dist=5) == 25.0
        )

    def test_ordena_la_lista_de_entrada_in_place(self, ai_control):
        # Efecto documentado: la funciÃ³n ORDENA el argumento in-place.
        entrada = [15.0, 10.0]
        ai_control._get_relative_dist_to_cover(entrada, extra_dist=5)
        assert entrada == [10.0, 15.0]


# â”€â”€â”€ _calc_path_length: longitud de un trazado desde un Ã­ndice â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestCalcPathLength:
    def test_longitud_completa(self, ai_control, make_coords):
        nodes = [make_coords(0, 0), make_coords(0, 10), make_coords(0, 30)]
        assert ai_control._calc_path_length(nodes) == pytest.approx(30.0)

    def test_desde_un_indice_intermedio(self, ai_control, make_coords):
        nodes = [make_coords(0, 0), make_coords(0, 10), make_coords(0, 30)]
        assert ai_control._calc_path_length(nodes, start_idx=1) == pytest.approx(20.0)

    def test_indice_en_el_ultimo_nodo_es_cero(self, ai_control, make_coords):
        nodes = [make_coords(0, 0), make_coords(0, 10), make_coords(0, 30)]
        assert ai_control._calc_path_length(nodes, start_idx=2) == 0.0
        assert ai_control._calc_path_length(nodes, start_idx=5) == 0.0

    def test_indice_negativo_se_trata_como_cero(self, ai_control, make_coords):
        # start_idx negativo no dispara la guarda (>= len-1) y luego se sube a 0 â†’ longitud completa.
        nodes = [make_coords(0, 0), make_coords(0, 10), make_coords(0, 30)]
        assert ai_control._calc_path_length(nodes, start_idx=-1) == pytest.approx(30.0)

    def test_lista_vacia_o_un_nodo(self, ai_control, make_coords):
        assert ai_control._calc_path_length([]) == 0.0
        assert ai_control._calc_path_length([make_coords(0, 0)]) == 0.0

    def test_es_2d_ignora_la_z(self, ai_control, make_coords):
        # hypot 2D: una diferencia de Z pura no suma longitud.
        nodes = [make_coords(0, 0, 0), make_coords(0, 0, 100)]
        assert ai_control._calc_path_length(nodes) == pytest.approx(0.0)


# â”€â”€â”€ _get_lookahead_point: punto a `lookahead_m` sobre la polilÃ­nea â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestGetLookaheadPoint:
    def test_punto_intermedio_del_primer_tramo(self, ai_control, make_coords):
        # Desde (0,0), 5 m sobre una vÃ­a recta en +Y â†’ (0, 5).
        nodes = [make_coords(0, 0), make_coords(0, 10), make_coords(0, 20)]
        x, y = ai_control._get_lookahead_point(0.0, 0.0, 0, nodes, 5.0)
        assert (x, y) == pytest.approx((0.0, 5.0))

    def test_mas_alla_del_final_devuelve_el_ultimo_nodo(self, ai_control, make_coords):
        nodes = [make_coords(0, 0), make_coords(0, 10), make_coords(0, 20)]
        x, y = ai_control._get_lookahead_point(0.0, 0.0, 0, nodes, 100.0)
        assert (x, y) == pytest.approx((0.0, 20.0))

    def test_lista_vacia_devuelve_mi_posicion(self, ai_control):
        assert ai_control._get_lookahead_point(3.0, 7.0, 0, [], 5.0) == (3.0, 7.0)

    def test_reverse_avanza_hacia_indices_menores(self, ai_control, make_coords):
        # reverse: desde (0,20) en el Ã­ndice 2, 5 m hacia atrÃ¡s â†’ (0, 15).
        nodes = [make_coords(0, 0), make_coords(0, 10), make_coords(0, 20)]
        x, y = ai_control._get_lookahead_point(0.0, 20.0, 2, nodes, 5.0, reverse=True)
        assert (x, y) == pytest.approx((0.0, 15.0))

    def test_reverse_mas_alla_devuelve_el_primer_nodo(self, ai_control, make_coords):
        nodes = [make_coords(0, 0), make_coords(0, 10), make_coords(0, 20)]
        x, y = ai_control._get_lookahead_point(0.0, 20.0, 2, nodes, 100.0, reverse=True)
        assert (x, y) == pytest.approx((0.0, 0.0))


# â”€â”€â”€ GeometrÃ­a de zonas de intersecciÃ³n (cÃ­rculo / cÃ¡psula / polÃ­gono) â”€â”€â”€â”€â”€â”€â”€â”€
#
# _is_point_in_zone / _get_dist_to_zone_edge / _get_zone_centroid interpretan los
# nodos de la IntersectionZone segÃºn cuÃ¡ntos haya: 0 (vacÃ­a), 1 (cÃ­rculo de radio
# radius_m), 2 (cÃ¡psula = segmento con grosor radius_m), 3+ (polÃ­gono, radius
# ignorado para la pertenencia).


def _zone(zone_id, points, radius_m=10.0, make_coords=None):
    """IntersectionZone con nodos en metros (helper local; no hay factorÃ­a aÃºn)."""
    nodes = [make_coords(*p) for p in points]
    return IntersectionZone(zone_id=zone_id, nodes=nodes, radius_m=radius_m)


class TestGetZoneCentroid:
    def test_zona_vacia_es_el_origen(self, ai_control):
        assert ai_control._get_zone_centroid(IntersectionZone(zone_id="Z")) == (
            0.0,
            0.0,
        )

    def test_un_nodo_es_ese_nodo(self, ai_control, make_coords):
        zone = _zone("Z", [(3, 7)], make_coords=make_coords)
        assert ai_control._get_zone_centroid(zone) == pytest.approx((3.0, 7.0))

    def test_varios_nodos_es_la_media(self, ai_control, make_coords):
        zone = _zone("Z", [(0, 0), (10, 0), (10, 10), (0, 10)], make_coords=make_coords)
        assert ai_control._get_zone_centroid(zone) == pytest.approx((5.0, 5.0))


class TestIsPointInZone:
    def test_zona_vacia_nunca_contiene(self, ai_control):
        assert (
            ai_control._is_point_in_zone(0, 0, IntersectionZone(zone_id="Z")) is False
        )

    def test_circulo_dentro_borde_y_fuera(self, ai_control, make_coords):
        z = _zone("Z", [(0, 50)], radius_m=10.0, make_coords=make_coords)
        assert ai_control._is_point_in_zone(0, 55, z) is True  # a 5 m del centro
        assert (
            ai_control._is_point_in_zone(0, 60, z) is True
        )  # justo en el radio (10 m)
        assert ai_control._is_point_in_zone(0, 65, z) is False  # a 15 m

    def test_capsula_mide_distancia_al_segmento(self, ai_control, make_coords):
        # Segmento (0,0)-(0,20) con grosor 5: 3 m de lado entra, 8 m no.
        z = _zone("Z", [(0, 0), (0, 20)], radius_m=5.0, make_coords=make_coords)
        assert ai_control._is_point_in_zone(3, 10, z) is True
        assert ai_control._is_point_in_zone(8, 10, z) is False

    def test_poligono_usa_ray_casting(self, ai_control, make_coords):
        z = _zone("Z", [(0, 0), (10, 0), (10, 10), (0, 10)], make_coords=make_coords)
        assert ai_control._is_point_in_zone(5, 5, z) is True
        assert ai_control._is_point_in_zone(20, 5, z) is False


class TestGetDistToZoneEdge:
    def test_zona_vacia_es_infinito(self, ai_control):
        z = IntersectionZone(zone_id="Z")
        assert ai_control._get_dist_to_zone_edge(0, 0, z) == float("inf")

    def test_circulo_resta_el_radio_y_no_baja_de_cero(self, ai_control, make_coords):
        z = _zone("Z", [(0, 50)], radius_m=10.0, make_coords=make_coords)
        # Fuera: hypot(50) - 10 = 40.
        assert ai_control._get_dist_to_zone_edge(0, 0, z) == pytest.approx(40.0)
        # Dentro: distancia negativa recortada a 0.
        assert ai_control._get_dist_to_zone_edge(0, 55, z) == 0.0

    def test_capsula_resta_el_radio(self, ai_control, make_coords):
        z = _zone("Z", [(0, 0), (0, 20)], radius_m=5.0, make_coords=make_coords)
        assert ai_control._get_dist_to_zone_edge(8, 10, z) == pytest.approx(3.0)

    def test_poligono_dentro_es_cero_fuera_mide_al_borde(self, ai_control, make_coords):
        z = _zone("Z", [(0, 0), (10, 0), (10, 10), (0, 10)], make_coords=make_coords)
        assert ai_control._get_dist_to_zone_edge(5, 5, z) == 0.0
        # (20,5): el borde mÃ¡s cercano es la arista x=10 â†’ 10 m.
        assert ai_control._get_dist_to_zone_edge(20, 5, z) == pytest.approx(10.0)


class TestIsPriorityVehicleActiveAtZone:
    def test_dentro_de_la_zona_siempre_activo(self, ai_control, make_coords):
        # Dentro del cÃ­rculo â†’ True aunque vaya despacio y mire hacia otro lado.
        z = _zone("Z", [(0, 50)], radius_m=10.0, make_coords=make_coords)
        got = ai_control._is_priority_vehicle_active_at_zone(
            make_coords(0, 52), 5.0, HEADING_SOUTH, z, approach_time_s=4.0
        )
        assert got is True

    def test_lejos_para_su_velocidad_no_esta_activo(self, ai_control, make_coords):
        # Borde a 40 m, 18 km/h (5 m/s) â†’ 8 s > 4 s de anticipaciÃ³n â†’ False.
        z = _zone("Z", [(0, 50)], radius_m=10.0, make_coords=make_coords)
        got = ai_control._is_priority_vehicle_active_at_zone(
            make_coords(0, 0), 18.0, HEADING_NORTH, z, approach_time_s=4.0
        )
        assert got is False

    def test_cerca_y_apuntando_a_la_zona_esta_activo(self, ai_control, make_coords):
        # Borde a 10 m, 36 km/h (10 m/s) â†’ 1 s â‰¤ 4 s, y mira a +Y (hacia la zona) â†’ True.
        z = _zone("Z", [(0, 50)], radius_m=10.0, make_coords=make_coords)
        got = ai_control._is_priority_vehicle_active_at_zone(
            make_coords(0, 30), 36.0, HEADING_NORTH, z, approach_time_s=4.0
        )
        assert got is True

    def test_cerca_pero_alejandose_no_esta_activo(self, ai_control, make_coords):
        # Mismo caso pero mirando a -Y (se aleja de la zona) â†’ producto escalar â‰¤ 0 â†’ False.
        z = _zone("Z", [(0, 50)], radius_m=10.0, make_coords=make_coords)
        got = ai_control._is_priority_vehicle_active_at_zone(
            make_coords(0, 30), 36.0, HEADING_SOUTH, z, approach_time_s=4.0
        )
        assert got is False


# â”€â”€â”€ _should_keep_yielding: histÃ©resis anti-parpadeo del ceda-el-paso â”€â”€â”€â”€â”€â”€â”€â”€â”€
#
# Fase 7: la decisiÃ³n de ceder no debe soltarse al primer tick sin prioritario
# (causaba oscilaciÃ³n gas-a-fondo/freno-de-mano). Detectar un prioritario renueva
# el "hold"; sin detecciÃ³n se sigue cediendo hasta que el hold expira.


class TestShouldKeepYielding:
    def test_detectado_siempre_cede(self, ai_control):
        # Con prioritario detectado se cede, aunque el hold ya hubiera expirado.
        assert ai_control._should_keep_yielding(True, 0.0, 100.0) is True

    def test_sin_deteccion_dentro_del_hold_sigue_cediendo(self, ai_control):
        # No detectado este tick, pero el hold aÃºn no expirÃ³ â†’ mantiene el yield.
        assert ai_control._should_keep_yielding(False, 101.0, 100.0) is True

    def test_sin_deteccion_hold_expirado_suelta(self, ai_control):
        # Hold expirado (o justo en el lÃ­mite) sin detecciÃ³n â†’ suelta el yield.
        assert ai_control._should_keep_yielding(False, 100.0, 100.0) is False
        assert ai_control._should_keep_yielding(False, 99.0, 100.0) is False


# â”€â”€â”€ _find_valid_overtake_lane: elecciÃ³n del carril de adelantamiento â”€â”€â”€â”€â”€â”€â”€â”€â”€
#
# RHT (conducciÃ³n por la derecha) â†’ se adelanta por la IZQUIERDA; LHT â†’ por la
# DERECHA. El carril vecino se acepta si `_get_indicator_to_use` (navigation.py)
# da ese lado. Ejes: vÃ­a en +Y; vecino a -X = LEFT, a +X = RIGHT.


class TestFindValidOvertakeLane:
    @staticmethod
    def _graph_with_neighbor(
        ai_control, make_road, make_lateral_link, populate_graph, neighbor_x
    ):
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", [(0, 0), (0, 100)]),
                make_road("R2", [(neighbor_x, 0), (neighbor_x, 100)]),
            ],
            lateral_links=[
                make_lateral_link(
                    "R1", "R2", [(neighbor_x / 2, 0), (neighbor_x / 2, 100)]
                )
            ],
        )
        return ai_control.map_recorder.roads["R1"].nodes

    def test_rht_adelanta_por_la_izquierda(
        self, ai_control, make_road, make_lateral_link, populate_graph
    ):
        # Vecino a -X (izquierda). RHT quiere LEFT â†’ coincide.
        r1_nodes = self._graph_with_neighbor(
            ai_control, make_road, make_lateral_link, populate_graph, neighbor_x=-5
        )
        got = ai_control._find_valid_overtake_lane("R1", TrafficRule.RHT, r1_nodes, 0)
        assert got == ("R2", "R1<<>>R2")

    def test_lht_con_vecino_izquierdo_no_encuentra(
        self, ai_control, make_road, make_lateral_link, populate_graph
    ):
        # Vecino a -X (izquierda) pero LHT quiere RIGHT â†’ no coincide.
        r1_nodes = self._graph_with_neighbor(
            ai_control, make_road, make_lateral_link, populate_graph, neighbor_x=-5
        )
        got = ai_control._find_valid_overtake_lane("R1", TrafficRule.LHT, r1_nodes, 0)
        assert got == (None, None)

    def test_lht_adelanta_por_la_derecha(
        self, ai_control, make_road, make_lateral_link, populate_graph
    ):
        # Vecino a +X (derecha). LHT quiere RIGHT â†’ coincide.
        r1_nodes = self._graph_with_neighbor(
            ai_control, make_road, make_lateral_link, populate_graph, neighbor_x=5
        )
        got = ai_control._find_valid_overtake_lane("R1", TrafficRule.LHT, r1_nodes, 0)
        assert got == ("R2", "R1<<>>R2")

    def test_sin_laterales_devuelve_none(self, ai_control, make_road, populate_graph):
        populate_graph(
            ai_control.map_recorder, roads=[make_road("R1", [(0, 0), (0, 100)])]
        )
        got = ai_control._find_valid_overtake_lane(
            "R1", TrafficRule.RHT, ai_control.map_recorder.roads["R1"].nodes, 0
        )
        assert got == (None, None)

    def test_carril_vecino_cerrado_no_se_usa(
        self, ai_control, make_road, make_lateral_link, populate_graph
    ):
        # Fase 7 Â· fix (4): un carril vecino que geomÃ©tricamente valdrÃ­a para
        # adelantar (RHT + vecino a la IZQUIERDA) pero cuya vÃ­a estÃ¡ CERRADA
        # (is_closed) NO debe usarse â€” la IA no puede meterse en una vÃ­a cerrada.
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", [(0, 0), (0, 100)]),
                make_road("R2", [(-5, 0), (-5, 100)], is_closed=True),
            ],
            lateral_links=[make_lateral_link("R1", "R2", [(-2.5, 0), (-2.5, 100)])],
        )
        r1_nodes = ai_control.map_recorder.roads["R1"].nodes
        got = ai_control._find_valid_overtake_lane("R1", TrafficRule.RHT, r1_nodes, 0)
        assert got == (None, None)


# â”€â”€â”€ Helpers del FSM de adelantamiento (mutaciones de estado del mode) â”€â”€â”€â”€â”€â”€â”€â”€


class TestOvertakeFSMHelpers:
    def test_trigger_return_arma_el_retorno(self, ai_control):
        mode = FreeroamMode()
        ai_control._trigger_return(mode, current_time=100.0)
        assert mode.overtake_state == "RETURNING"
        assert mode.maneuver_state == AIManeuverState.RETURNING
        assert mode.overtake_change_lane is True
        assert mode._returning_start_time == 100.0

    def test_finish_overtake_resetea_todo_el_estado(self, ai_control):
        # Ensuciamos el mode como si estuviera en pleno adelantamiento.
        mode = FreeroamMode()
        mode.overtake_state = "OVERTAKING"
        mode.maneuver_state = AIManeuverState.OVERTAKING
        mode.overtake_target_plid = 7
        mode.is_driving_opposing = True
        mode.overtake_fast_lane_id = "R2"
        mode.overtake_lat_link_id = "R1<<>>R2"
        mode.overtake_change_lane = True
        mode._fast_lane_logged = True

        ai_control._finish_overtake(mode, current_time=200.0)

        assert mode.overtake_state == "IDLE"
        assert mode.maneuver_state == AIManeuverState.NORMAL
        assert mode.overtake_target_plid is None
        assert mode.is_driving_opposing is False
        assert mode.overtake_fast_lane_id is None
        assert mode.overtake_lat_link_id is None
        assert mode.overtake_change_lane is False
        assert mode._fast_lane_logged is False
        # Cooldown de 8 s tras cerrar el adelantamiento.
        assert mode.overtake_cooldown == pytest.approx(208.0)


# â”€â”€â”€ Radar de trÃ¡fico (_scan_lane_ahead / _scan_target_lane / _scan_return_lane_gap) â”€â”€
#
# Se ejercita SOLO con vehÃ­culos IA (no jugadores humanos): la rama de IA lee la
# topologÃ­a directa de `extra['aic'].active_mode` y es DETERMINISTA, mientras que la
# de humanos usa `time.time()` + `get_location_context` (misma razÃ³n por la que los
# mÃ©todos gordos con tiempo se dejan fuera). Escenario base: vÃ­a recta R1 en +Y con
# nodos cada 10 m (Ã­ndices 0..9) y el coche que escanea en (0,50), node_index=5.


def _pts_y(x=0.0, y0=0.0, y1=90.0, step=10.0):
    """Puntos (x, y) de una recta en +Y (por defecto Ã­ndices 0..9 cada 10 m)."""
    n = int(round((y1 - y0) / step))
    return [(x, y0 + i * step) for i in range(n + 1)]


def _place_ai(make_ai, make_behavior, plid, x_m, y_m, speed_kmh=0.0, mode_fields=None):
    """AI en pista con FreeroamMode en extra['aic'].active_mode.

    mode_fields=None â†’ active_mode=None (sin topologÃ­a: el radar lo ignora).
    """
    mode = FreeroamMode(**mode_fields) if mode_fields is not None else None
    return make_ai(
        plid=plid,
        name=f"AI{plid}",
        behavior=make_behavior(active_mode=mode),
        x_m=x_m,
        y_m=y_m,
        speed_kmh=speed_kmh,
    )


def _set_ais(ai_control, *ais):
    ai_control.user_manager.ais = {a.player.plid: a for a in ais}


class TestScanLaneAhead:
    @staticmethod
    def _scanner_and_mode(
        ai_control, populate_graph, make_road, make_ai, plid=1, **mode_kw
    ):
        populate_graph(ai_control.map_recorder, roads=[make_road("R1", _pts_y())])
        scanner = make_ai(plid=plid, x_m=0, y_m=50, speed_kmh=0)
        mode = FreeroamMode(
            current_type="Road", current_id="R1", node_index=5, **mode_kw
        )
        return scanner, mode

    def test_detecta_coche_delante_mismo_segmento(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            65,
            speed_kmh=20,
            mode_fields={"current_id": "R1", "node_index": 6},
        )
        _set_ais(ai_control, scanner, other)
        got = ai_control._scan_lane_ahead(scanner, mode, 30.0)
        assert len(got) == 1
        dist, speed, plid = got[0]
        assert dist == pytest.approx(15.0)
        assert speed == pytest.approx(20.0, abs=0.1)  # cuantizaciÃ³n de speed_lfs
        assert plid == 2

    def test_ignora_coche_detras_por_indice(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        # node_index 4 < 5 â†’ idx_diff negativo â†’ detrÃ¡s â†’ ignorado (aunque estÃ© cerca).
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            40,
            mode_fields={"current_id": "R1", "node_index": 4},
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_lane_ahead(scanner, mode, 30.0) == []

    def test_ignora_el_propio_coche(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        _set_ais(ai_control, scanner)  # solo Ã©l mismo â†’ se salta por plid
        assert ai_control._scan_lane_ahead(scanner, mode, 30.0) == []

    def test_ignora_ia_sin_modo_activo(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        # extra['aic'] presente pero active_mode=None â†’ sin current_id â†’ ignorado.
        other = _place_ai(make_ai, make_behavior, 2, 0, 65, mode_fields=None)
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_lane_ahead(scanner, mode, 30.0) == []

    def test_ignora_otro_segmento_no_relacionado(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        # En otra vÃ­a (R2) y sin next_link declarado â†’ ni mismo segmento ni next_link.
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            65,
            mode_fields={"current_id": "R2", "node_index": 3},
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_lane_ahead(scanner, mode, 30.0) == []

    def test_mismo_indice_mas_cerca_del_nodo_se_detecta(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        # Mismo node_index (5) pero MÃS cerca del nodo objetivo (0,60) que nosotros â†’ delante.
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            55,
            mode_fields={"current_id": "R1", "node_index": 5},
        )
        _set_ais(ai_control, scanner, other)
        got = ai_control._scan_lane_ahead(scanner, mode, 30.0)
        assert [(round(d, 3), p) for d, _, p in got] == [(5.0, 2)]

    def test_mismo_indice_mas_lejos_del_nodo_se_ignora(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        # Mismo node_index pero MÃS lejos del nodo objetivo â†’ detrÃ¡s â†’ ignorado.
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            45,
            mode_fields={"current_id": "R1", "node_index": 5},
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_lane_ahead(scanner, mode, 30.0) == []

    def test_empate_al_nodo_el_plid_menor_cede(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        # Empate de distancia al nodo (<0.3 m): el coche de plid MENOR cede (no lo ve).
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai, plid=1
        )
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            50.1,
            mode_fields={"current_id": "R1", "node_index": 5},
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_lane_ahead(scanner, mode, 30.0) == []

    def test_empate_al_nodo_el_plid_mayor_si_lo_ve(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        # El mismo empate, pero ahora el que escanea tiene plid MAYOR â†’ sÃ­ lo ve.
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai, plid=9
        )
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            50.1,
            mode_fields={"current_id": "R1", "node_index": 5},
        )
        _set_ais(ai_control, scanner, other)
        got = ai_control._scan_lane_ahead(scanner, mode, 30.0)
        assert [p for _, _, p in got] == [2]

    def test_indice_cercano_usa_producto_cruzado(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        # idx_diff=2 (â‰¤3): aunque el Ã­ndice diga "delante", si geomÃ©tricamente estÃ¡
        # DETRÃS (0,45) el producto cruzado lo descarta.
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            45,
            mode_fields={"current_id": "R1", "node_index": 7},
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_lane_ahead(scanner, mode, 30.0) == []

    def test_indice_lejano_ignora_el_producto_cruzado(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        # idx_diff=4 (>3): ya NO hay chequeo de producto cruzado â†’ se detecta aun estando
        # geomÃ©tricamente detrÃ¡s (0,45). Es el comportamiento actual (confÃ­a en el Ã­ndice).
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            45,
            mode_fields={"current_id": "R1", "node_index": 9},
        )
        _set_ais(ai_control, scanner, other)
        got = ai_control._scan_lane_ahead(scanner, mode, 30.0)
        assert [(round(d, 3), p) for d, _, p in got] == [(5.0, 2)]

    def test_respeta_max_dist_en_la_distancia_final(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        # Coche delante a 25 m: fuera con max_dist=20, dentro con max_dist=30.
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            75,
            mode_fields={"current_id": "R1", "node_index": 7},
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_lane_ahead(scanner, mode, 20.0) == []
        got = ai_control._scan_lane_ahead(scanner, mode, 30.0)
        assert [(round(d, 3), p) for d, _, p in got] == [(25.0, 2)]

    def test_ordena_por_distancia_ascendente(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        lejos = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            80,
            mode_fields={"current_id": "R1", "node_index": 8},
        )
        cerca = _place_ai(
            make_ai,
            make_behavior,
            3,
            0,
            60,
            mode_fields={"current_id": "R1", "node_index": 6},
        )
        _set_ais(ai_control, scanner, lejos, cerca)
        got = ai_control._scan_lane_ahead(scanner, mode, 40.0)
        assert [(round(d, 3), p) for d, _, p in got] == [(10.0, 3), (30.0, 2)]

    def test_coche_en_nuestro_proximo_roadlink_cuenta_como_delante(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        # En un Road, un coche ya metido en nuestro prÃ³ximo RoadLink se trata como
        # obstÃ¡culo delante (evita pileup en la entrada del enlace).
        scanner, mode = self._scanner_and_mode(
            ai_control,
            populate_graph,
            make_road,
            make_ai,
            next_link_id="R1->R2",
            next_link_type="RoadLink",
        )
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            70,
            mode_fields={
                "current_id": "R1->R2",
                "current_type": "RoadLink",
                "node_index": 0,
            },
        )
        _set_ais(ai_control, scanner, other)
        got = ai_control._scan_lane_ahead(scanner, mode, 30.0)
        assert [(round(d, 3), p) for d, _, p in got] == [(20.0, 2)]


# â”€â”€â”€ Fase 7 Â· fix (3): la cadena topolÃ³gica from_road â†’ link â†’ to_road â”€â”€â”€â”€â”€â”€â”€â”€
#
# El radar solo aceptaba coches en `mode.current_id` (+ el prÃ³ximo RoadLink yendo
# por un Road). Al entrar en un RoadLink, la IA conmuta su topologÃ­a ANTES de
# separarse fÃ­sicamente de la vÃ­a vieja (navigation.py: `dist_to_link < TRIGGER_DIST_M`,
# 3.5 m) â†’ dejaba de ver (a) al coche lento que aÃºn tenÃ­a delante en la vÃ­a que deja
# y (b) a los que ya circulaban dentro de la vÃ­a destino. `_lane_chain_ids` ensancha
# el match a esa cadena, acotado por una VENTANA de transiciÃ³n medida al nodo de
# entrada del enlace: lejos del cruce el filtro vuelve a ser estricto (sin frenado
# fantasma por coches de una transversal).

# Grafo de los tests de cadena: R1 recta en +Y (0..200); el enlace R1->R2 arranca en
# (0,100) y sigue recto hasta (0,140); R2 continÃºa de (0,140) a (0,220). R1 sigue
# existiendo mÃ¡s allÃ¡ del cruce (un coche puede seguir de frente sin tomar el enlace).
_CHAIN_LINK_NODES = [
    (0.0, 100.0),
    (0.0, 110.0),
    (0.0, 120.0),
    (0.0, 130.0),
    (0.0, 140.0),
]


def _chain_graph(ai_control, populate_graph, make_road, make_road_link):
    populate_graph(
        ai_control.map_recorder,
        roads=[
            make_road("R1", _pts_y(y1=200.0)),
            make_road("R2", _pts_y(y0=140.0, y1=220.0)),
        ],
        road_links=[make_road_link("R1", "R2", _CHAIN_LINK_NODES)],
    )


class TestLaneChainIds:
    """Unitarios de los helpers puros de la cadena (sin radar de por medio)."""

    @staticmethod
    def _link(make_road_link):
        return make_road_link("R1", "R2", _CHAIN_LINK_NODES)

    def test_sin_nodos_nunca_esta_en_la_ventana(self, make_road_link):
        link = make_road_link("R1", "R2", [])
        assert _is_near_link_entry(link, 0.0, 100.0, 25.0) is False

    def test_ventana_se_mide_al_nodo_de_entrada(self, make_road_link):
        link = self._link(make_road_link)  # entrada en (0,100)
        assert _is_near_link_entry(link, 0.0, 90.0, 25.0) is True  # a 10 m
        assert _is_near_link_entry(link, 0.0, 70.0, 25.0) is False  # a 30 m

    def test_en_road_sin_next_link_la_cadena_esta_vacia(self):
        mode = FreeroamMode(current_type="Road", current_id="R1")
        assert _lane_chain_ids(mode, None, None, 0.0, 90.0, 25.0) == set()

    def test_en_road_un_next_latlink_no_entra_en_la_cadena(self, make_road_link):
        # Solo los RoadLink cuentan: un LatLink es un cambio de carril, no un cruce.
        mode = FreeroamMode(
            current_type="Road",
            current_id="R1",
            next_link_id="R1<<>>R3",
            next_link_type="LatLink",
        )
        link = self._link(make_road_link)
        assert _lane_chain_ids(mode, None, link, 0.0, 90.0, 25.0) == set()

    def test_en_road_lejos_del_enlace_solo_el_enlace(self, make_road_link):
        # Comportamiento de ANTES (`in_our_next_link`): el enlace sÃ­, su destino no.
        mode = FreeroamMode(
            current_type="Road",
            current_id="R1",
            next_link_id="R1->R2",
            next_link_type="RoadLink",
        )
        link = self._link(make_road_link)
        assert _lane_chain_ids(mode, None, link, 0.0, 50.0, 25.0) == {"R1->R2"}

    def test_en_road_dentro_de_la_ventana_entra_la_via_destino(self, make_road_link):
        mode = FreeroamMode(
            current_type="Road",
            current_id="R1",
            next_link_id="R1->R2",
            next_link_type="RoadLink",
        )
        link = self._link(make_road_link)
        assert _lane_chain_ids(mode, None, link, 0.0, 90.0, 25.0) == {"R1->R2", "R2"}

    def test_en_roadlink_la_via_destino_siempre_cuenta(self, make_road_link):
        # Ya comprometidos con el enlace: to_road es nuestro carril â†’ siempre.
        mode = FreeroamMode(current_type="RoadLink", current_id="R1->R2")
        link = self._link(make_road_link)
        assert _lane_chain_ids(mode, link, None, 0.0, 135.0, 25.0) == {"R2"}

    def test_en_roadlink_dentro_de_la_ventana_entra_la_via_que_deja(
        self, make_road_link
    ):
        mode = FreeroamMode(current_type="RoadLink", current_id="R1->R2")
        link = self._link(make_road_link)
        assert _lane_chain_ids(mode, link, None, 0.0, 105.0, 25.0) == {"R2", "R1"}

    def test_enlace_no_encontrado_no_revienta(self):
        mode = FreeroamMode(current_type="RoadLink", current_id="FANTASMA")
        assert _lane_chain_ids(mode, None, None, 0.0, 105.0, 25.0) == set()


class TestScanLaneAheadChain:
    """El radar, ya con la cadena: los dos choques que reportÃ³ el usuario."""

    @staticmethod
    def _scanner_in_link(make_ai, y_m, node_index):
        scanner = make_ai(plid=1, x_m=0, y_m=y_m, speed_kmh=0)
        mode = FreeroamMode(
            current_type="RoadLink",
            current_id="R1->R2",
            current_road_id="R1",
            node_index=node_index,
        )
        return scanner, mode

    def test_en_roadlink_ve_al_lento_que_sigue_en_la_via_que_deja(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_ai,
        make_behavior,
    ):
        # BUG A: acabamos de entrar al enlace (a 5 m de su entrada) y el coche lento
        # que venÃ­amos siguiendo sigue de frente por R1 â†’ antes desaparecÃ­a del radar.
        _chain_graph(ai_control, populate_graph, make_road, make_road_link)
        scanner, mode = self._scanner_in_link(make_ai, y_m=105.0, node_index=1)
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            115,
            speed_kmh=10,
            mode_fields={"current_type": "Road", "current_id": "R1", "node_index": 11},
        )
        _set_ais(ai_control, scanner, other)
        got = ai_control._scan_lane_ahead(scanner, mode, 30.0)
        assert [(round(d, 3), p) for d, _, p in got] == [(10.0, 2)]

    def test_en_roadlink_ve_a_los_que_ya_circulan_en_la_via_destino(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_ai,
        make_behavior,
    ):
        # BUG B: vamos por el enlace y en R2 (nuestra vÃ­a destino) ya circula alguien
        # delante â†’ antes no existÃ­a para el radar y se le echaba encima.
        _chain_graph(ai_control, populate_graph, make_road, make_road_link)
        scanner, mode = self._scanner_in_link(make_ai, y_m=130.0, node_index=3)
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            145,
            speed_kmh=10,
            mode_fields={"current_type": "Road", "current_id": "R2", "node_index": 0},
        )
        _set_ais(ai_control, scanner, other)
        got = ai_control._scan_lane_ahead(scanner, mode, 30.0)
        assert [(round(d, 3), p) for d, _, p in got] == [(15.0, 2)]

    def test_en_roadlink_ignora_al_de_la_via_que_deja_si_va_detras(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_ai,
        make_behavior,
    ):
        # Mismo tramo, pero DETRÃS (producto escalar â‰¤ 0) â†’ no es obstÃ¡culo.
        _chain_graph(ai_control, populate_graph, make_road, make_road_link)
        scanner, mode = self._scanner_in_link(make_ai, y_m=105.0, node_index=1)
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            95,
            mode_fields={"current_type": "Road", "current_id": "R1", "node_index": 9},
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_lane_ahead(scanner, mode, 30.0) == []

    def test_pasada_la_ventana_la_via_que_deja_deja_de_mirarse(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_ai,
        make_behavior,
    ):
        # Ya metidos en el enlace (a 30 m de su entrada > ventana): fÃ­sicamente hemos
        # dejado R1 â†’ un coche suyo "delante" ya no estÃ¡ en nuestra trayectoria.
        _chain_graph(ai_control, populate_graph, make_road, make_road_link)
        scanner, mode = self._scanner_in_link(make_ai, y_m=130.0, node_index=3)
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            140,
            mode_fields={"current_type": "Road", "current_id": "R1", "node_index": 14},
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_lane_ahead(scanner, mode, 30.0) == []

    def test_en_road_cerca_del_cruce_ya_ve_la_via_destino(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_ai,
        make_behavior,
    ):
        # AproximaciÃ³n: a 10 m de la entrada del enlace, un coche parado en R2 (justo
        # al otro lado del cruce) ya cuenta â†’ frena a tiempo en vez de al entrar.
        _chain_graph(ai_control, populate_graph, make_road, make_road_link)
        scanner = make_ai(plid=1, x_m=0, y_m=90, speed_kmh=0)
        mode = FreeroamMode(
            current_type="Road",
            current_id="R1",
            current_road_id="R1",
            node_index=9,
            next_link_id="R1->R2",
            next_link_type="RoadLink",
        )
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            145,
            mode_fields={"current_type": "Road", "current_id": "R2", "node_index": 0},
        )
        _set_ais(ai_control, scanner, other)
        got = ai_control._scan_lane_ahead(scanner, mode, 60.0)
        assert [(round(d, 3), p) for d, _, p in got] == [(55.0, 2)]

    def test_en_road_lejos_del_cruce_no_frena_por_la_via_destino(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_ai,
        make_behavior,
    ):
        # A 50 m de la entrada (fuera de la ventana): el coche de R2 NO cuenta. Es lo
        # que evita el frenado fantasma por trÃ¡fico de una vÃ­a transversal lejana.
        _chain_graph(ai_control, populate_graph, make_road, make_road_link)
        scanner = make_ai(plid=1, x_m=0, y_m=50, speed_kmh=0)
        mode = FreeroamMode(
            current_type="Road",
            current_id="R1",
            current_road_id="R1",
            node_index=5,
            next_link_id="R1->R2",
            next_link_type="RoadLink",
        )
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            145,
            mode_fields={"current_type": "Road", "current_id": "R2", "node_index": 0},
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_lane_ahead(scanner, mode, 100.0) == []


class TestScanLaneAheadHumano:
    """Un HUMANO delante, en la misma vÃ­a: Â¿lo ve la IA en TODO momento?

    Los humanos van por la otra rama del radar: no publican topologÃ­a, asÃ­ que se les
    calcula. La IA compara `other_node_index` con su `mode.node_index`, y ahÃ­ estÃ¡ el
    problema: **son dos cosas distintas**. El `node_index` de una IA es el nodo que
    PERSIGUE (lo captura ~5 m ANTES de llegar: `evaluate_dynamic_capture`), mientras
    que al humano se le asigna el nodo MÃS CERCANO. Comparar "objetivo" contra
    "cercano" mete un sesgo de un nodo â†’ un humano que va fÃ­sicamente DELANTE puede
    dar `idx_diff < 0` ("va detrÃ¡s") y desaparecer del radar.

    Esto reproduce el escenario del usuario en LFS: la IA le sigue a distancia normal
    mientras ambos avanzan. El humano tiene que estar detectado en CADA paso.
    """

    def test_humano_delante_se_ve_en_todo_el_recorrido(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_ai,
        make_player,
        make_telemetry,
    ):
        # VÃ­a recta con nodos cada 10 m (espaciado tÃ­pico de los mapas grabados).
        road = make_road("R1", _pts_y(y0=0.0, y1=300.0))
        populate_graph(ai_control.map_recorder, roads=[road])

        GAP_M = 7.0  # el humano va 7 m por delante: claramente delante, y cerca
        SPEED_KMH = 30.0
        node_index = 0
        fallos = []

        # La pareja avanza 1 m por paso. El `node_index` de la IA se mantiene EXACTAMENTE
        # como en producciÃ³n (`navigation.py`): con `evaluate_dynamic_capture`.
        for paso in range(0, 200):
            y_ia = 20.0 + paso
            # Secuencia EXACTA de navigation.py: antilag (engancha el nodo) y luego
            # captura dinÃ¡mica (lo adelanta al acercarse). Ese +1 es el sesgo.
            mis_coords = _coords_xy(0.0, y_ia)
            node_index = apply_antilag_window(
                my_coords=mis_coords,
                current_idx=node_index,
                list_of_nodes=road.nodes,
                window_size=5,
                is_waypoint=False,
            )
            siguiente = evaluate_dynamic_capture(
                my_coords=mis_coords,
                current_target_idx=node_index,
                list_of_nodes=road.nodes,
                speed_kmh=SPEED_KMH,
                min_radius=2.5,
                max_radius=12.0,
                lookahead_time=0.3,
                is_waypoint=False,
            )
            if siguiente > node_index:
                node_index = siguiente
            scanner = make_ai(plid=1, x_m=0, y_m=y_ia, speed_kmh=SPEED_KMH)
            mode = FreeroamMode(
                current_type="Road",
                current_id="R1",
                current_road_id="R1",
                node_index=node_index,
            )
            ai_control.user_manager.ais = {1: scanner}
            ai_control.user_manager.players = {
                2: make_player(
                    plid=2,
                    ucid=2,
                    telemetry=make_telemetry(x_m=0.0, y_m=y_ia + GAP_M, speed_kmh=20.0),
                )
            }
            ai_control._radar_human_cache.clear()  # sin cachÃ©: medimos la decisiÃ³n, no el lag

            visto = [p for _, _, p in ai_control._scan_lane_ahead(scanner, mode, 40.0)]
            if 2 not in visto:
                fallos.append((round(y_ia, 1), node_index))

        assert not fallos, (
            f"La IA PIERDE al humano que lleva 7 m delante en {len(fallos)}/200 pasos "
            f"(y_ia, node_index): {fallos[:12]}..."
        )

    def test_otra_ia_escaneando_desde_otra_via_no_ciega_el_radar(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_ai,
        make_behavior,
        make_player,
        make_telemetry,
    ):
        # La caché de humanos (`_radar_human_cache`) es COMPARTIDA por todas las IAs,
        # pero el índice de nodo que guardaba se medía contra la geometría de QUIEN
        # escaneó primero. Una IA que va por otra vía dejaba ahí un índice inválido
        # (-1, porque el humano no iba en SU vía) y la IA de detrás del humano lo leía
        # como "va detrás" → lo perdía durante toda la ventana de caché (0,1 s).
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", _pts_y(y1=200.0)),
                make_road("R2", _pts_y(x=50.0, y1=200.0)),
            ],
        )
        # La IA de detrás del humano, en R1.
        detras = make_ai(plid=1, x_m=0, y_m=50, speed_kmh=30)
        mode = FreeroamMode(
            current_type="Road", current_id="R1", current_road_id="R1", node_index=5
        )
        # Otra IA, lejos y en OTRA vía (R2). Escanea primero y toca la misma caché.
        otra = _place_ai(
            make_ai,
            make_behavior,
            3,
            50,
            50,
            speed_kmh=30,
            mode_fields={"current_type": "Road", "current_id": "R2", "node_index": 5},
        )
        otra_mode = otra.extra["aic"].active_mode
        ai_control.user_manager.ais = {1: detras, 3: otra}
        ai_control.user_manager.players = {
            2: make_player(
                plid=2, ucid=2, telemetry=make_telemetry(x_m=0, y_m=58, speed_kmh=10)
            )
        }

        # La IA de R2 escanea primero (envenena la caché del humano).
        ai_control._scan_lane_ahead(otra, otra_mode, 40.0)
        # Y ahora la que va justo detrás del humano, dentro de la ventana de caché.
        visto = [p for _, _, p in ai_control._scan_lane_ahead(detras, mode, 40.0)]

        assert 2 in visto, "la IA de detrás perdió al humano por la caché de otra IA"


class TestOvertakeTriggerGuard:
    """El gatillo IDLEâ†’EVALUATING del FSM, con y sin cruce de por medio.

    Primera red sobre `_update_traffic_behavior` (el orquestador se dejÃ³ sin cubrir
    por usar `time.time()`; aquÃ­ el tiempo solo entra en comparaciones de cooldown
    con 0.0, asÃ­ que el gatillo es determinista). Va ligada al fix (3): al ver ahora
    a los coches de la cadena del cruce, la IA podÃ­a dispararse a adelantar DENTRO de
    un RoadLink â€” donde `_find_valid_overtake_lane` mira los laterales de la vÃ­a que
    ya dejÃ³ y `node_index` es el del enlace. El adelantamiento se inicia solo en Road.
    """

    @staticmethod
    def _slow_car(make_ai, make_behavior, x_m, y_m, road_id, node_index):
        return _place_ai(
            make_ai,
            make_behavior,
            2,
            x_m,
            y_m,
            speed_kmh=5,
            mode_fields={
                "current_type": "Road",
                "current_id": road_id,
                "node_index": node_index,
            },
        )

    def test_en_un_road_el_coche_lento_dispara_el_adelantamiento(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_ai,
        make_behavior,
    ):
        # Caso normal (sin cruce): sigue disparÃ¡ndose como siempre.
        _chain_graph(ai_control, populate_graph, make_road, make_road_link)
        scanner = make_ai(plid=1, x_m=0, y_m=50, speed_kmh=30)
        mode = FreeroamMode(
            current_type="Road", current_id="R1", current_road_id="R1", node_index=5
        )
        scanner.extra["aic"].active_mode = mode
        _set_ais(
            ai_control, scanner, self._slow_car(make_ai, make_behavior, 0, 60, "R1", 6)
        )

        ai_control._update_traffic_behavior(scanner)

        assert mode.overtake_state == "EVALUATING"
        assert mode.overtake_target_plid == 2

    def test_dentro_de_un_roadlink_no_se_inicia_un_adelantamiento(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_ai,
        make_behavior,
    ):
        # Mismo coche lento, pero nosotros vamos DENTRO del enlace: se frena por Ã©l
        # (ACC) y NO se abre la maniobra. El FSM se queda en IDLE.
        _chain_graph(ai_control, populate_graph, make_road, make_road_link)
        scanner = make_ai(plid=1, x_m=0, y_m=105, speed_kmh=30)
        mode = FreeroamMode(
            current_type="RoadLink",
            current_id="R1->R2",
            current_road_id="R1",
            node_index=1,
        )
        scanner.extra["aic"].active_mode = mode
        _set_ais(
            ai_control,
            scanner,
            self._slow_car(make_ai, make_behavior, 0, 115, "R1", 11),
        )

        ai_control._update_traffic_behavior(scanner)

        assert mode.overtake_state == "IDLE"
        assert mode.overtake_target_plid is None
        # Pero el coche del cruce SÃ se ve: es el que nos bloquea (fix (3)).
        assert mode.blocking_plid == 2


class TestScanTargetLane:
    @staticmethod
    def _scanner_and_mode(ai_control, populate_graph, make_road, make_ai):
        populate_graph(ai_control.map_recorder, roads=[make_road("R1", _pts_y())])
        scanner = make_ai(plid=1, x_m=0, y_m=50, speed_kmh=0)
        mode = FreeroamMode(current_type="Road", current_id="R1", node_index=5)
        return scanner, mode

    def test_detecta_coche_delante_en_el_carril_objetivo(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        other = _place_ai(
            make_ai, make_behavior, 2, 0, 60, mode_fields={"current_id": "R2"}
        )
        _set_ais(ai_control, scanner, other)
        got = ai_control._scan_target_lane(scanner, mode, "R2", 30.0)
        assert [(round(d, 3), p) for d, _, p in got] == [(10.0, 2)]

    def test_ignora_coche_detras_en_el_carril_objetivo(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        # Mismo carril objetivo pero DETRÃS (producto escalar â‰¤ 0) â†’ ignorado.
        other = _place_ai(
            make_ai, make_behavior, 2, 0, 40, mode_fields={"current_id": "R2"}
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_target_lane(scanner, mode, "R2", 30.0) == []

    def test_ignora_coche_en_otro_carril(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        # Delante pero en R3, no en el carril objetivo R2 â†’ ignorado.
        other = _place_ai(
            make_ai, make_behavior, 2, 0, 60, mode_fields={"current_id": "R3"}
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_target_lane(scanner, mode, "R2", 30.0) == []


class TestScanReturnLaneGap:
    @staticmethod
    def _scanner_and_mode(
        ai_control, populate_graph, make_road, make_ai, return_lane="R1"
    ):
        populate_graph(ai_control.map_recorder, roads=[make_road("R1", _pts_y())])
        scanner = make_ai(plid=1, x_m=0, y_m=50, speed_kmh=0)
        mode = FreeroamMode(current_type="Road", current_id="R1", node_index=5)
        mode.overtake_return_lane_id = return_lane
        return scanner, mode

    def test_sin_coches_es_infinito(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        _set_ais(ai_control, scanner)
        assert ai_control._scan_return_lane_gap(scanner, mode, 30.0) == (
            float("inf"),
            float("inf"),
        )

    def test_carril_de_retorno_inexistente_es_infinito(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai, return_lane="NOPE"
        )
        other = _place_ai(
            make_ai, make_behavior, 2, 0, 60, mode_fields={"current_road_id": "R1"}
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_return_lane_gap(scanner, mode, 30.0) == (
            float("inf"),
            float("inf"),
        )

    def test_separa_coche_delante_y_detras(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        # current_road_id (no current_id) es el campo que mira este escÃ¡ner.
        delante = _place_ai(
            make_ai, make_behavior, 2, 0, 60, mode_fields={"current_road_id": "R1"}
        )
        detras = _place_ai(
            make_ai, make_behavior, 3, 0, 40, mode_fields={"current_road_id": "R1"}
        )
        _set_ais(ai_control, scanner, delante, detras)
        ahead, behind = ai_control._scan_return_lane_gap(scanner, mode, 30.0)
        assert ahead == pytest.approx(10.0)
        assert behind == pytest.approx(10.0)

    def test_ignora_coches_en_otro_carril(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        scanner, mode = self._scanner_and_mode(
            ai_control, populate_graph, make_road, make_ai
        )
        other = _place_ai(
            make_ai, make_behavior, 2, 0, 60, mode_fields={"current_road_id": "R2"}
        )
        _set_ais(ai_control, scanner, other)
        assert ai_control._scan_return_lane_gap(scanner, mode, 30.0) == (
            float("inf"),
            float("inf"),
        )


# â”€â”€â”€ Equivalencia: rejilla espacial de vehÃ­culos vs. barrido lineal (W3) â”€â”€â”€â”€â”€â”€
#
# La rejilla dinÃ¡mica (`_build_vehicle_grid`) devuelve un SUPERCONJUNTO de los
# vehÃ­culos dentro del radio de culling â†’ cada barrido debe dar EXACTAMENTE la misma
# salida que iterando todos los vehÃ­culos. Se comprueba corriendo cada escÃ¡ner dos
# veces â€”sin rejilla (referencia) y con rejillaâ€” sobre muchas configuraciones
# aleatorias, y comparando bit a bit. Es la caracterizaciÃ³n del radar "como unidad"
# que el plan (W3) exige ANTES de meter la rejilla en producciÃ³n, y el anÃ¡logo del
# fuzz de equivalencia del Ã­ndice espacial de geometrÃ­a (S23).


class TestRadarSpatialGridEquivalence:
    @staticmethod
    def _run_both(app, scan_call):
        """Devuelve (salida_sin_rejilla, salida_con_rejilla).

        Limpia las cachÃ©s de humanos antes de CADA corrida: asÃ­ la rama de humano
        (que usa `time.time()` + cachÃ© por PLID) recomputa de forma determinista y
        ambas corridas parten del mismo estado. La Ãºnica diferencia entre las dos es
        de dÃ³nde salen los candidatos (todos vs. vecindario de la rejilla).
        """
        app._radar_human_cache.clear()
        app._target_lane_human_cache.clear()
        app._vehicle_grid = None
        app._vehicle_index = {}
        reference = scan_call()

        app._radar_human_cache.clear()
        app._target_lane_human_cache.clear()
        app._build_vehicle_grid()
        with_grid = scan_call()
        return reference, with_grid

    @staticmethod
    def _spread(rng, app, scanner, make_ai, make_behavior, make_player, make_telemetry):
        """Puebla user_manager con una mezcla aleatoria de IAs (con topologÃ­a) y
        humanos. Mezcla vehÃ­culos CERCA del escÃ¡ner (para producir detecciones) y
        LEJOS (para ejercitar el culling y celdas de rejilla distantes). El
        `node_index` de los que van en R1 se deriva de su `y` (como en producciÃ³n:
        R1 tiene nodos en y=0,10,â€¦,400). Devuelve el nÂº de vehÃ­culos colocados."""
        ais = {scanner.player.plid: scanner}
        humans: dict = {}
        for k in range(2, 2 + rng.randint(5, 14)):
            if rng.random() < 0.6:  # cerca del escÃ¡ner (0,100)
                x = rng.uniform(-18.0, 18.0)
                y = rng.uniform(60.0, 220.0)
            else:  # lejos: cubre culling y celdas distantes
                x = rng.uniform(-70.0, 70.0)
                y = rng.uniform(-30.0, 340.0)
            spd = rng.uniform(0.0, 40.0)
            road = "R1" if rng.random() < 0.55 else rng.choice(["R2", "R3"])
            if rng.random() < 0.7:
                ni = int(round(y / 10.0)) if road == "R1" else rng.randint(0, 39)
                ais[k] = _place_ai(
                    make_ai,
                    make_behavior,
                    k,
                    x,
                    y,
                    speed_kmh=spd,
                    mode_fields={
                        "current_type": "Road",
                        "current_id": road,
                        "current_road_id": road,
                        "node_index": max(0, min(ni, 40)),
                    },
                )
            else:
                humans[k] = make_player(
                    plid=k,
                    ucid=k,
                    telemetry=make_telemetry(x_m=x, y_m=y, speed_kmh=spd),
                )
        app.user_manager.ais = ais
        app.user_manager.players = humans
        return len(ais) + len(humans)

    def test_scan_lane_ahead_equivale_al_barrido_lineal(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_ai,
        make_behavior,
        make_player,
        make_telemetry,
    ):
        populate_graph(
            ai_control.map_recorder, roads=[make_road("R1", _pts_y(y1=400.0))]
        )
        non_empty = 0
        for seed in range(40):
            rng = random.Random(seed)
            scanner = make_ai(plid=1, x_m=0.0, y_m=100.0, speed_kmh=rng.uniform(10, 40))
            self._spread(
                rng,
                ai_control,
                scanner,
                make_ai,
                make_behavior,
                make_player,
                make_telemetry,
            )
            mode = FreeroamMode(current_type="Road", current_id="R1", node_index=10)
            max_dist = rng.choice([15.0, 25.0, 40.0])
            ref, got = self._run_both(
                ai_control, lambda: ai_control._scan_lane_ahead(scanner, mode, max_dist)
            )
            assert got == ref, f"seed={seed} max_dist={max_dist}"
            non_empty += bool(ref)
        assert non_empty >= 5  # el fuzz ejercita de verdad casos con detecciones

    def test_scan_lane_ahead_en_roadlink_equivale_al_barrido_lineal(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_road_link,
        make_ai,
        make_behavior,
        make_player,
        make_telemetry,
    ):
        # Fase 7 Â· fix (3): con el escÃ¡ner DENTRO de un RoadLink, la cadena topolÃ³gica
        # (from_road/to_road) admite muchos mÃ¡s vehÃ­culos que antes â†’ hay que volver a
        # demostrar que la rejilla no pierde ninguno respecto al barrido lineal. El
        # escÃ¡ner recorre el enlace (dentro y fuera de la ventana de transiciÃ³n).
        populate_graph(
            ai_control.map_recorder,
            roads=[
                make_road("R1", _pts_y(y1=400.0)),
                make_road("R2", _pts_y(y0=140.0, y1=400.0)),
            ],
            road_links=[make_road_link("R1", "R2", _CHAIN_LINK_NODES)],
        )
        non_empty = 0
        for seed in range(40):
            rng = random.Random(seed)
            y = rng.choice([102.0, 112.0, 130.0, 138.0])  # dentro y fuera de la ventana
            scanner = make_ai(plid=1, x_m=0.0, y_m=y, speed_kmh=rng.uniform(10, 40))
            self._spread(
                rng,
                ai_control,
                scanner,
                make_ai,
                make_behavior,
                make_player,
                make_telemetry,
            )
            mode = FreeroamMode(
                current_type="RoadLink",
                current_id="R1->R2",
                current_road_id="R1",
                node_index=int((y - 100.0) // 10.0),
            )
            max_dist = rng.choice([15.0, 25.0, 40.0])
            ref, got = self._run_both(
                ai_control, lambda: ai_control._scan_lane_ahead(scanner, mode, max_dist)
            )
            assert got == ref, f"seed={seed} y={y} max_dist={max_dist}"
            non_empty += bool(ref)
        assert non_empty >= 5  # la cadena detecta de verdad en un buen puÃ±ado de casos

    def test_scan_target_lane_equivale_al_barrido_lineal(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_ai,
        make_behavior,
        make_player,
        make_telemetry,
    ):
        populate_graph(
            ai_control.map_recorder, roads=[make_road("R1", _pts_y(y1=400.0))]
        )
        for seed in range(40):
            rng = random.Random(seed)
            scanner = make_ai(plid=1, x_m=0.0, y_m=100.0, speed_kmh=rng.uniform(10, 40))
            self._spread(
                rng,
                ai_control,
                scanner,
                make_ai,
                make_behavior,
                make_player,
                make_telemetry,
            )
            mode = FreeroamMode(current_type="Road", current_id="R1", node_index=10)
            target = rng.choice(["R1", "R2", "R3"])
            max_dist = rng.choice([15.0, 25.0, 40.0])
            ref, got = self._run_both(
                ai_control,
                lambda: ai_control._scan_target_lane(scanner, mode, target, max_dist),
            )
            assert got == ref, f"seed={seed} target={target} max_dist={max_dist}"

    def test_scan_return_lane_gap_equivale_al_barrido_lineal(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_ai,
        make_behavior,
        make_player,
        make_telemetry,
    ):
        populate_graph(
            ai_control.map_recorder, roads=[make_road("R1", _pts_y(y1=400.0))]
        )
        for seed in range(40):
            rng = random.Random(seed)
            scanner = make_ai(plid=1, x_m=0.0, y_m=100.0, speed_kmh=rng.uniform(10, 40))
            self._spread(
                rng,
                ai_control,
                scanner,
                make_ai,
                make_behavior,
                make_player,
                make_telemetry,
            )
            mode = FreeroamMode(current_type="Road", current_id="R1", node_index=10)
            mode.overtake_return_lane_id = "R1"
            max_dist = rng.choice([15.0, 25.0, 40.0])
            ref, got = self._run_both(
                ai_control,
                lambda: ai_control._scan_return_lane_gap(scanner, mode, max_dist),
            )
            assert got == ref, f"seed={seed} max_dist={max_dist}"

    def test_grid_no_pierde_candidato_diagonal_dentro_del_radio(
        self, ai_control, populate_graph, make_road, make_ai, make_behavior
    ):
        # Coche DETECTADO (dentro de max_dist) pero en una celda de rejilla distinta
        # a la del escÃ¡ner (diagonal). La consulta por CAJA lo incluye; una consulta
        # de solo-celda-central lo perderÃ­a â†’ aquÃ­ got != ref. Discrimina el bug.
        populate_graph(
            ai_control.map_recorder, roads=[make_road("R1", _pts_y(y1=400.0))]
        )
        scanner = make_ai(plid=1, x_m=0.0, y_m=100.0, speed_kmh=0)  # celda (0, 2)
        mode = FreeroamMode(current_type="Road", current_id="R1", node_index=10)
        # (20,120): dist 2D = hypot(20,20) = 28.28 < max_dist(30); celda (0, 3).
        other = _place_ai(
            make_ai,
            make_behavior,
            2,
            20.0,
            120.0,
            mode_fields={"current_id": "R1", "node_index": 12},
        )
        ai_control.user_manager.ais = {1: scanner, 2: other}
        ai_control.user_manager.players = {}
        ref, got = self._run_both(
            ai_control, lambda: ai_control._scan_lane_ahead(scanner, mode, 30.0)
        )
        assert got == ref
        assert [p for _, _, p in got] == [2]  # detectado por ambos caminos


# â”€â”€â”€ _get_available_overtake_distance: asfalto disponible para maniobrar â”€â”€â”€â”€â”€â”€


class TestGetAvailableOvertakeDistance:
    def test_lateral_circular_es_infinito(
        self, ai_control, make_lateral_link, make_coords
    ):
        lat = make_lateral_link("R1", "R2", [(0, 0), (0, 30)], is_circular=True)
        mode = FreeroamMode(current_road_id="R1", node_index=0)
        got = ai_control._get_available_overtake_distance(mode, make_coords(0, 0), lat)
        assert got == float("inf")

    def test_sin_next_link_usa_solo_la_longitud_del_lateral(
        self, ai_control, make_lateral_link, make_coords
    ):
        # Sin prÃ³ximo giro, la ruta no limita (inf) â†’ manda la lÃ­nea discontinua.
        lat = make_lateral_link("R1", "R2", [(0, 0), (0, 20), (0, 50)])
        mode = FreeroamMode(current_road_id="R1", node_index=0, next_link_id=None)
        got = ai_control._get_available_overtake_distance(mode, make_coords(0, 0), lat)
        assert got == pytest.approx(50.0)

    def test_con_next_link_manda_el_mas_corto(
        self, ai_control, make_road, make_lateral_link, make_coords, populate_graph
    ):
        # Ruta (R1 desde node 7 = 20 m) mÃ¡s corta que el lateral (50 m) â†’ gana 20 m.
        populate_graph(ai_control.map_recorder, roads=[make_road("R1", _pts_y())])
        lat = make_lateral_link("R1", "R2", [(0, 0), (0, 50)])
        mode = FreeroamMode(current_road_id="R1", node_index=7, next_link_id="R1->R2")
        got = ai_control._get_available_overtake_distance(mode, make_coords(0, 0), lat)
        assert got == pytest.approx(20.0)


# â”€â”€â”€ _is_lane_safe_to_overtake: puerta de seguridad del adelantamiento â”€â”€â”€â”€â”€â”€â”€â”€
#
# Combina piezas ya congeladas: chequeo de salida (next RoadLink), lÃ­mite fÃ­sico
# (_get_available_overtake_distance) y escaneo del carril objetivo (_scan_target_lane).
# El coche escanea desde (0,0) a 36 km/h (â‰ˆ10 m/s â†’ safe_gap â‰ˆ 20 m).


class TestIsLaneSafeToOvertake:
    @staticmethod
    def _scanner(ai_control, populate_graph, make_road, make_ai, **mode_kw):
        populate_graph(ai_control.map_recorder, roads=[make_road("R1", _pts_y())])
        ai = make_ai(plid=1, x_m=0, y_m=0, speed_kmh=36)
        mode = FreeroamMode(
            current_type="Road",
            current_id="R1",
            current_road_id="R1",
            node_index=0,
            **mode_kw,
        )
        return ai, mode

    def test_carril_libre_y_espacio_de_sobra_es_seguro(
        self, ai_control, populate_graph, make_road, make_ai, make_lateral_link
    ):
        ai, mode = self._scanner(ai_control, populate_graph, make_road, make_ai)
        lat = make_lateral_link("R1", "R2", [(0, 0), (0, 100)], is_circular=True)
        _set_ais(ai_control, ai)  # sin trÃ¡fico en el carril objetivo
        got = ai_control._is_lane_safe_to_overtake(
            ai,
            mode,
            "R2",
            lat,
            is_opposing=False,
            req_dist_m=50,
            time_to_overtake_s=5.0,
        )
        assert got is True

    def test_sin_asfalto_fisico_no_es_seguro(
        self, ai_control, populate_graph, make_road, make_ai, make_lateral_link
    ):
        ai, mode = self._scanner(ai_control, populate_graph, make_road, make_ai)
        # Lateral de solo 30 m; req(50) + safe_gap(â‰ˆ20) > 30 â†’ no cabe.
        lat = make_lateral_link("R1", "R2", [(0, 0), (0, 30)])
        _set_ais(ai_control, ai)
        got = ai_control._is_lane_safe_to_overtake(
            ai,
            mode,
            "R2",
            lat,
            is_opposing=False,
            req_dist_m=50,
            time_to_overtake_s=5.0,
        )
        assert got is False

    def test_giro_de_salida_demasiado_cerca_no_es_seguro(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_ai,
        make_road_link,
        make_lateral_link,
    ):
        # next RoadLink (salida) a 10 m; req(50) > 10 â†’ la maniobra no cabe antes del giro.
        ai, mode = self._scanner(
            ai_control,
            populate_graph,
            make_road,
            make_ai,
            next_link_id="R1->EXIT",
            next_link_type="RoadLink",
        )
        ai_control.map_recorder.road_links["R1->EXIT"] = make_road_link(
            "R1", "EXIT", [(0, 10), (0, 12)]
        )
        lat = make_lateral_link("R1", "R2", [(0, 0), (0, 100)], is_circular=True)
        _set_ais(ai_control, ai)
        got = ai_control._is_lane_safe_to_overtake(
            ai,
            mode,
            "R2",
            lat,
            is_opposing=False,
            req_dist_m=50,
            time_to_overtake_s=5.0,
        )
        assert got is False

    def test_coche_lento_en_el_carril_objetivo_no_es_seguro(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_ai,
        make_behavior,
        make_lateral_link,
    ):
        ai, mode = self._scanner(ai_control, populate_graph, make_road, make_ai)
        lat = make_lateral_link("R1", "R2", [(0, 0), (0, 100)], is_circular=True)
        # Coche parado a 20 m en R2: su posiciÃ³n futura no deja el hueco de seguridad.
        blocker = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            20,
            speed_kmh=0,
            mode_fields={"current_id": "R2"},
        )
        _set_ais(ai_control, ai, blocker)
        got = ai_control._is_lane_safe_to_overtake(
            ai,
            mode,
            "R2",
            lat,
            is_opposing=False,
            req_dist_m=10,
            time_to_overtake_s=5.0,
        )
        assert got is False

    def test_coche_de_frente_cerca_no_es_seguro(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_ai,
        make_behavior,
        make_lateral_link,
    ):
        ai, mode = self._scanner(ai_control, populate_graph, make_road, make_ai)
        lat = make_lateral_link("R1", "R2", [(0, 0), (0, 100)], is_circular=True)
        # Carril contrario: coche a 30 m acercÃ¡ndose a 36 km/h â†’ consume demasiado asfalto.
        oncoming = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            30,
            speed_kmh=36,
            mode_fields={"current_id": "R2"},
        )
        _set_ais(ai_control, ai, oncoming)
        got = ai_control._is_lane_safe_to_overtake(
            ai, mode, "R2", lat, is_opposing=True, req_dist_m=50, time_to_overtake_s=5.0
        )
        assert got is False

    def test_coche_de_frente_lejos_si_es_seguro(
        self,
        ai_control,
        populate_graph,
        make_road,
        make_ai,
        make_behavior,
        make_lateral_link,
    ):
        ai, mode = self._scanner(ai_control, populate_graph, make_road, make_ai)
        lat = make_lateral_link("R1", "R2", [(0, 0), (0, 100)], is_circular=True)
        # Contrario pero parado y lejos (90 m), maniobra corta (1 s) â†’ hay margen â†’ seguro.
        oncoming = _place_ai(
            make_ai,
            make_behavior,
            2,
            0,
            90,
            speed_kmh=0,
            mode_fields={"current_id": "R2"},
        )
        _set_ais(ai_control, ai, oncoming)
        got = ai_control._is_lane_safe_to_overtake(
            ai, mode, "R2", lat, is_opposing=True, req_dist_m=50, time_to_overtake_s=1.0
        )
        assert got is True
