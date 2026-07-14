"""Control de crucero adaptativo (ACC) de 3 zonas: roja (frenar a cero),
naranja (rampa hasta la velocidad del de delante) y verde (velocidad base).

El viejo «PARCHE DE SEGURIDAD MATEMÁTICO» se eliminó en S21: los `min_dist_m`
y `max_dist_m` del llamador se respetan tal cual (ver DIAGNOSTICO § P25)."""

from __future__ import annotations

from insims.ai_control.base import _MixinBase

# Hueco mínimo entre coches (m) en parado: por debajo se pide 0 en seco. Es el
# suelo duro de la ley ACC y también el offset con el que la cesión (Fase 8)
# coloca su "coche parado" fantasma tras la línea de detención, para que el
# morro acabe EN la línea. Ajustable (dial del hueco junto a MIN_GAP_FLOOR_M).
PARADA_ABSOLUTA_M = 7.0


class _CruiseControlMixin(_MixinBase):
    def _apply_adaptive_cruise_control(
        self,
        base_speed_kmh: float,
        closest_speed_kmh: float,
        closest_dist_m: float,
        min_dist_m: float,
        max_dist_m: float,
    ) -> float:
        """Velocidad que se pide a la IA teniendo en cuenta al coche de delante.

        Ley CONTINUA (sin escalones, que son los que excitan la oscilación):

            PARADA      (dist ≤ 7 m)             → 0            suelo duro
            EMERGENCIA  (7 < dist ≤ critical)    → rampa 0 → match
            SEGUIMIENTO (critical < dist ≤ min)  → match        IGUALA al de delante
            ADAPTACIÓN  (min < dist < max)       → lerp match → base
            libre       (dist ≥ max)             → base

        `match = min(velocidad_del_de_delante, base)`. En `critical` la rampa ya vale
        `match`, en `min` el seguimiento vale `match` (= inicio del lerp) y en `max` el
        lerp vale `base` → la curva empalma en los tres bordes.

        S35 (tras probar en LFS): **al ir bloqueado se IGUALA la velocidad del de
        delante, no se reduce.** Reducir (lo que hacía la vieja "zona naranja") abría el
        hueco → la IA aceleraba → volvía a cerrarlo → oscilaba. Reducir solo es legítimo
        si te has metido demasiado cerca, así que esa rampa vive ahora en la franja de
        EMERGENCIA, por debajo de `critical`. Los `min`/`max` del llamador se respetan
        tal cual (el "PARCHE DE SEGURIDAD MATEMÁTICO" se eliminó en S21 — ver P25).
        """
        # ==========================================
        # CONSTANTES DE LA LEY DE CONTROL
        # ==========================================
        # (PARADA_ABSOLUTA_M vive a nivel de módulo: la cesión también la usa.)
        CRITICAL_FRACTION = 0.5  # la emergencia empieza a la mitad del min de seguridad
        ANTICREEP_KMH = 2.0  # por debajo de esto, parar en seco (no arrastrarse)
        EPSILON = 1e-6  # blinda los denominadores contra el 0

        # Nunca se pide ir más rápido que la base por seguir a alguien más rápido.
        match_speed = min(closest_speed_kmh, base_speed_kmh)

        # ==========================================
        # PARADA: suelo duro, explícito y fuera de la matemática de zonas
        # ==========================================
        if closest_dist_m <= PARADA_ABSOLUTA_M:
            return 0.0

        # El inicio de la emergencia escala con el min de seguridad (que el llamador
        # deriva de la velocidad: time-gap), pero nunca baja del suelo. Si min es tan
        # pequeño que critical == PARADA, la franja de emergencia se COLAPSA: el ε evita
        # el 0/0 y el ratio se satura a 1 → se entra directo en SEGUIMIENTO.
        critical_dist_m = max(PARADA_ABSOLUTA_M, min_dist_m * CRITICAL_FRACTION)

        # ==========================================
        # EMERGENCIA: demasiado cerca → frenar para recuperar el hueco
        # ==========================================
        if closest_dist_m <= critical_dist_m:
            denom = max(critical_dist_m - PARADA_ABSOLUTA_M, EPSILON)
            ratio = min(1.0, max(0.0, (closest_dist_m - PARADA_ABSOLUTA_M) / denom))
            target_speed = match_speed * ratio

            # Arrastrarse a 1 km/h no sirve de nada: se para del todo.
            if target_speed < ANTICREEP_KMH:
                return 0.0

            return target_speed

        # ==========================================
        # SEGUIMIENTO: bloqueado pero a distancia sana → IGUALAR, no reducir
        # ==========================================
        if closest_dist_m <= min_dist_m:
            if match_speed < ANTICREEP_KMH:
                return 0.0  # el de delante está parado/arrastrándose → parar
            return match_speed

        # ==========================================
        # ADAPTACIÓN: hay hueco → interpolar hacia la velocidad base
        # ==========================================
        if closest_dist_m < max_dist_m:
            denom = max(max_dist_m - min_dist_m, EPSILON)
            ratio = min(1.0, max(0.0, (closest_dist_m - min_dist_m) / denom))
            target_speed = match_speed + (base_speed_kmh - match_speed) * ratio
            return min(target_speed, base_speed_kmh)

        # Fuera del alcance del radar: velocidad base.
        return base_speed_kmh
