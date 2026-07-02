# 🗺️ Plan de trabajo — AP_LFS_InSim

> Plan por fases. Cada fase tiene criterios de aceptación. Se marca lo completado con `[x]`.
> Referencias `Pn` remiten a los problemas de `DIAGNOSTICO.md`.
> **Orden acordado (S01):** empezar por Fase 0.
> **Rama de trabajo:** todo ocurre en `refactor/estabilizacion`; merge a `main` solo cuando
> el proyecto esté estable (ver "Merge a `main`" al final).

---

## Fase 0 — Cimientos  ✅ COMPLETADA (S03, 2026-07-02)

**Objetivo:** entorno reproducible, suite corriendo y deuda de bajo riesgo eliminada.
Sin esto no se puede refactorizar con seguridad. Riesgo casi nulo.

- [x] Crear `.venv` e instalar `pip install -e ".[dev]"` (**P1**) — S02, Python 3.14.6 + pytest 9.1.1
- [x] Ejecutar `pytest`; registrar cuántos de los 221 tests pasan (**P1**) — S02, 216/221 en el primer run
- [x] Dejar los tests en verde — S02, corregidos 5 tests de padding erróneos (no el código) → **221/221** (ver P8)
- [x] Eliminar `src/lfs_insim/utils_temp.py` (verificar antes que ningún test lo use) (**P6**) — S03, sin usos
- [x] Limpiar `config/settings.py`: quitar import muerto de `ISF`; mover `admin_pass` y
      `LFS_DIR` a config local / env; **decidir y alinear** el valor de `interval` con la
      documentación (**P5**) — S03: env + `settings_local.py`; `interval` se queda en 10 y docs alineadas
- [x] Anclar la ruta de `rutas_grabadas.txt` al proyecto (ruta absoluta, no relativa al CWD)
      y decidir si el fichero de datos sigue versionado (**P6**) — S03: `RUTAS_FILE = BASE_DIR / ...`; sigue versionado
- [x] (descubierto en S03) Declarar la dependencia `matplotlib` de `ai_control` (**P10**) —
      `insim.json` + extra `[dev]` + instalada en `.venv`

**Criterio de aceptación:** `pytest` verde desde `.venv`; `settings.py` sin import muerto
ni secretos hardcodeados; `utils_temp.py` fuera; ruta de rutas robusta. ✅ Cumplido (221/221).

---

## Fase 1 — Red de seguridad (tests de caracterización)  ◀️ ACTIVA

**Objetivo:** capturar el comportamiento ACTUAL de la lógica frágil antes de tocarla.

- [ ] Tests de caracterización de `navigation.py` (planificación de enlaces, nodo más cercano)
- [ ] Tests de caracterización de `traffic.py` (radar / `_scan_lane_ahead`, ACC, overtake)
- [ ] Tests de `physics.py` (volante/pedales/marchas) con telemetría sintética
- [ ] Infra de fixtures: telemetría y grafo de calles sintéticos, sin conexión a LFS

**Criterio de aceptación:** la lógica de P2 queda "congelada" por tests que pasan con el
código actual y que fallarían ante una regresión de comportamiento.

---

## Fase 2 — Estabilizar la lógica frágil (P2)

**Objetivo:** eliminar la causa raíz de los bugs recurrentes de radar/tráfico, con la red puesta.

- [ ] Revisar el "PARCHE DE SEGURIDAD MATEMÁTICO" (`traffic.py:655`) y sustituirlo por lógica correcta
- [ ] Auditar el hot-loop `on_ISP_MCI`: coste por tick, trabajo en el hilo de IO, frecuencia real
- [ ] Consolidar detección de vehículos (radar) y su geometría en una unidad testeable
- [ ] Revisar FSM de adelantamiento y detección en RoadLink siguiente (origen de varios fixes)

**Criterio de aceptación:** sin nuevos parches ad-hoc; los tests de Fase 1 siguen verdes;
el usuario valida en LFS que el comportamiento mejora o se mantiene.

---

## Fase 3 — Refactor estructural (P3, P4)

**Objetivo:** trocear los ficheros gigantes y reducir el acoplamiento cruzado.

- [ ] Dividir `map_ui.py` (1841) por tabs/responsabilidad
- [ ] Dividir `map_recorder.py` (1604) (grabación vs edición vs persistencia)
- [ ] Dividir `traffic.py` (1084) (radar / ACC / overtake / zonas)
- [ ] Reducir la superficie cross-mixin de `base.py`: pasar de "todo vía self" a
      colaboradores explícitos donde tenga sentido

**Criterio de aceptación:** ningún archivo de `ai_control` supera ~500 líneas sin justificación;
menos métodos cross-mixin; tests verdes.

---

## Fase 4 — Consolidación

- [ ] Limpiar nombres confusos del modelo de estado (`behavior.py`, P7)
- [ ] Actualizar `README.md` / `CLAUDE.md` con la arquitectura resultante
- [ ] Revisión final de deuda y actualización del diagnóstico

---

## 🔀 Merge a `main`

Todo el refactor vive en la rama **`refactor/estabilizacion`**. `main` permanece intacta
hasta el merge. **Criterio para mergear a `main` ("estable"):**

- Las fases del plan acordadas están completadas.
- `pytest` en **verde** desde `.venv`.
- El usuario ha **validado el comportamiento en LFS** (no hay regresiones funcionales).

El merge lo decide y autoriza el usuario. Tras el merge, se continúa desde `main`.

## Ideas / pendientes sin fase asignada

- **P9**: decidir qué hacer con `tools/setup_lfs.py` (roto: importa `DESIRED_LFS_CONFIG`,
  que no existe en `settings.py`) — recuperarlo o eliminarlo.
- Migrar `rutas_grabadas.txt` a JSON cuando se toque `RouteManager` (ver P6).
- **P8**: confirmar contra `docs/InSim.txt` el caso de string variable vacío sin padding.
