"""Control de crucero adaptativo (ACC) de 3 zonas: roja (frenar a cero),
naranja (rampa hasta la velocidad del de delante) y verde (velocidad base).

El viejo «PARCHE DE SEGURIDAD MATEMÁTICO» se eliminó en S21: los `min_dist_m`
y `max_dist_m` del llamador se respetan tal cual (ver DIAGNOSTICO § P25)."""

from __future__ import annotations

from insims.ai_control.base import _MixinBase


class _CruiseControlMixin(_MixinBase):
    def _apply_adaptive_cruise_control(
        self,
        base_speed_kmh: float,
        closest_speed_kmh: float,
        closest_dist_m: float,
        min_dist_m: float,
        max_dist_m: float,
    ) -> float:
        """
        Regula la velocidad de la IA con 3 zonas: Adaptación suave, Frenado agresivo y Parada crítica.
        """
        # ==========================================
        # CONSTANTES DE LA LEY DE CONTROL
        # (antes eran números mágicos dispersos por el cuerpo del método)
        # ==========================================
        PARADA_ABSOLUTA_M = 5.0  # suelo físico: nunca acercarse a menos de esto
        CRITICAL_FRACTION = 0.5  # zona roja = mitad del min de seguridad
        ANTICREEP_KMH = 2.0  # por debajo de esto en naranja, parar en seco
        EPSILON = 1e-6  # blinda los denominadores contra el 0

        # Suelo duro de parada, explícito y separado de la matemática de zonas.
        if closest_dist_m <= PARADA_ABSOLUTA_M:
            return 0.0

        # La distancia crítica (inicio de la zona roja) nunca baja del suelo absoluto.
        # Al llevar el suelo DENTRO de `critical` (en vez de en un parche que reescribe
        # los min/max del llamador), el umbral rojo efectivo sigue siendo max(5, min/2)
        # —comportamiento histórico— y la rampa naranja arranca de 0 justo en ese punto.
        # Como en zona naranja se cumple critical < dist ≤ min ⇒ min > critical, el
        # denominador naranja (min − critical) es > 0 por construcción; el ε es un
        # cinturón extra. Los min/max del llamador se respetan tal cual (el viejo
        # "PARCHE DE SEGURIDAD MATEMÁTICO" que los inflaba se eliminó — ver P25).
        critical_dist_m = max(PARADA_ABSOLUTA_M, min_dist_m * CRITICAL_FRACTION)

        # ==========================================
        # ZONA ROJA: Peligro inminente de colisión
        # ==========================================
        if closest_dist_m <= critical_dist_m:
            return 0.0

        # ==========================================
        # ZONA NARANJA: Warning Area (Frenado directo)
        # ==========================================
        if closest_dist_m <= min_dist_m:
            # Aquí frenamos agresivamente de forma proporcional (ratio acotado a [0,1]).
            denom = max(min_dist_m - critical_dist_m, EPSILON)
            ratio_frenado = min(
                1.0, max(0.0, (closest_dist_m - critical_dist_m) / denom)
            )

            # Pedimos ir MÁS LENTO que el coche de delante para recuperar la distancia de seguridad
            target_speed = closest_speed_kmh * ratio_frenado

            # ANTI-CREEP: Evita el frenado asintótico. Si la velocidad objetivo es ridículamente
            # baja (ej. arrastrarse a 1.5 km/h frente a un ceda el paso), frenamos en seco.
            if target_speed < ANTICREEP_KMH:
                return 0.0

            return target_speed

        # ==========================================
        # ZONA AMARILLA: Safety Area (Adaptación)
        # ==========================================
        if closest_dist_m < max_dist_m:
            # Interpolación (Lerp) para igualar la velocidad del líder de forma suave
            # (ratio acotado a [0,1] y denominador blindado con ε contra max ≤ min).
            denom = max(max_dist_m - min_dist_m, EPSILON)
            ratio_adaptacion = min(1.0, max(0.0, (closest_dist_m - min_dist_m) / denom))

            # Buscamos igualar la velocidad del coche de delante
            match_speed = min(closest_speed_kmh, base_speed_kmh)

            # A medida que nos acercamos al min_dist_m, la velocidad cae a match_speed
            target_speed = (
                match_speed + (base_speed_kmh - match_speed) * ratio_adaptacion
            )
            return min(target_speed, base_speed_kmh)

        # Si está fuera de los radares (más lejos que max_dist_m), vamos a la velocidad base
        return base_speed_kmh
