# 🗺️ Plan de trabajo — AP_LFS_InSim

> Plan por fases. Cada fase tiene criterios de aceptación. Se marca lo completado con `[x]`.
> Referencias `Pn` remiten a los problemas de `DIAGNOSTICO.md`.
> **Rama de trabajo:** todo ocurre en `refactor/estabilizacion`; merge a `main` solo cuando
> el proyecto esté estable (ver "Merge a `main`" al final).
>
> **Reorientación (S04, 2026-07-02):** el usuario fijó como objetivo llevar el **framework**
> a nivel profesional (usable felizmente por otros desarrolladores, buenas prácticas).
> Romper los insims existentes es aceptable. El plan antiguo de `ai_control` (caracterizar →
> estabilizar → trocear) se conserva como Fases 5–6, después del core.

---

## Fase 0 — Cimientos  ✅ COMPLETADA (S03, 2026-07-02)

**Objetivo:** entorno reproducible, suite corriendo y deuda de bajo riesgo eliminada.

- [x] Crear `.venv` e instalar `pip install -e ".[dev]"` (**P1**) — S02, Python 3.14.6 + pytest 9.1.1
- [x] Ejecutar `pytest`; registrar cuántos de los 221 tests pasan (**P1**) — S02, 216/221 en el primer run
- [x] Dejar los tests en verde — S02, corregidos 5 tests de padding erróneos → **221/221** (ver P8)
- [x] Eliminar `src/lfs_insim/utils_temp.py` (**P6**) — S03, sin usos
- [x] Limpiar `config/settings.py` (**P5**) — S03: env + `settings_local.py`; `interval` se queda en 10
- [x] Anclar la ruta de `rutas_grabadas.txt` (**P6**) — S03: `RUTAS_FILE = BASE_DIR / ...`; sigue versionado
- [x] (descubierto) Declarar dependencia `matplotlib` de `ai_control` (**P10**) — S03

**Extra S04:** protocolo actualizado a **LFS 0.8C5** (ISP_SET, ISF_SET, RIFlags/RIF/SAI,
CCI_RETIRED, NLP_MAX_CARS=48, HOSTF nuevos) con 12 tests; spec completa restaurada en
`docs/InSim.txt`; suite **233/233**.

---

## Fase 1 — Red de seguridad del CORE  ◀️ ACTIVA

**Objetivo:** congelar el comportamiento del core antes de refactorizarlo (P11–P14 lo van
a remover todo). Sin LFS: sockets falsos y bytes de oro.

- [ ] **Golden-bytes de serialización**: para cada paquete enviable, test que fija los bytes
      exactos que produce `prepare()+pack` (captura el layout binario actual) (**P19**)
- [ ] **Golden-bytes de decodificación**: bytes reales (capturados de LFS o construidos según
      spec) → dataclass esperado, para los paquetes info más usados (STA, NCN, NPL, MCI,
      MSO, VER...) (**P19**)
- [ ] Tests del **dispatch** de `InSimClient`: registro de handlers activos, orden
      master→módulos, aislamiento de errores por handler
- [ ] Tests del **loader**: carga con dependencias, coup d'état actual (caracterizar),
      fallos (módulo inexistente, sin clase InSimApp, versión insuficiente) (**P20**)
- [ ] Tests de **packet_io** con socket falso: reensamblado TCP (paquetes fragmentados /
      pegados), byte Size=0, cierre de conexión
- [ ] Infra: fixture de "LFS falso" (servidor TCP loopback que reproduce trazas) reutilizable

**Criterio de aceptación:** el comportamiento actual del core queda descrito por tests que
fallarían ante una regresión; base para refactorizar con confianza.

---

## Fase 2 — Arquitectura del core (composición y API)

**Objetivo:** eliminar los defectos estructurales de raíz. **Rompe la API de los insims**
(aceptado por el usuario en S04).

- [ ] **P11**: invertir la herencia — `InSimApp` deja de heredar de `InSimClient`.
      Un cliente, N apps: `client.register(app)`; el loader construye el cliente y registra
      las apps en orden de dependencias. Eliminar coup d'état y aplanado de `modules[]`
- [ ] **P13**: encapsular la conexión (objeto transporte TCP/UDP inyectado); eliminar los
      singletons de `insim_state`; `send` viaja por el cliente, no por globals
- [ ] **P14**: config del paquete con defaults internos (`InSimConfig` o similar); el CLI
      carga config de proyecto/env; el core no importa `config.settings` del CWD
- [ ] **P15**: definir API pública — exports en `lfs_insim/__init__.py`, `__all__` por
      módulo, deprecar `insim_packet_class` (facade), eliminar `import *` internos
- [ ] **P17/P20 (de paso)**: borrar `_resolve_dependencies` muerto, alinear comentarios,
      fail-fast en el loader
- [ ] Migrar `users_management`, `ai_control` y `test_insim` a la nueva API
- [ ] Decisión de diseño: idioma de la API pública del core (identificadores ya en inglés;
      ¿docstrings/errores en inglés para comunidad LFS internacional?) — **recomendación:
      inglés en el core, español en docs/dev** — decidir con el usuario

**Criterio de aceptación:** cero estado global obligatorio; dos clientes pueden coexistir en
un proceso (test); los 3 insims corren con la nueva API; tests de Fase 1 adaptados y verdes.

---

## Fase 3 — Robustez en runtime

**Objetivo:** comportamiento profesional ante fallos y carga.

- [ ] **P12**: reconexión automática con backoff configurable; `on_disconnect`/`on_reconnect`;
      reenvío de ISI y re-solicitud de estado al reconectar
- [ ] **P2 (parte core)**: sacar el dispatch del hilo de IO (cola + worker dedicado);
      documentar el contrato de threading para autores de módulos; revisar/retirar
      `use_thread_pool` (orden no garantizado)
- [ ] **P18**: eliminar o implementar bien el envío UDP
- [ ] **P19**: una sola ruta de serialización (prepare→pack) apoyada en los golden-bytes;
      revisar `.strip()` del decoder (espacios significativos)
- [ ] Apagado limpio y determinista (STOP_EVENT compartido/carreras en `stop_all_threads`)
- [ ] Política de errores de handlers configurable (resiliente en prod, fail-fast en dev)

**Criterio de aceptación:** matar/levantar LFS con el InSim corriendo → se reconecta solo;
un handler lento no bloquea la recepción; suite verde.

---

## Fase 4 — Experiencia de desarrollador (DX) y packaging

**Objetivo:** que un tercero pueda instalar, crear y publicar un InSim sin leer el código
fuente. (**P16**)

- [ ] Arreglar metadata: `readme = "README.md"`, `license`, keywords/classifiers; eliminar
      `requirements.txt` redundante; una sola fuente de versión
- [ ] `generate-stubs`/`update-all` → subcomandos del CLI (`lfs-insim stubs`, ...)
- [ ] Adoptar **ruff** (lint + format) y **mypy** gradual (empezando por el core)
- [ ] **CI** (GitHub Actions): pytest + ruff en push/PR a la rama de trabajo y main
- [ ] Docs de usuario: quickstart "tu primer InSim en 5 min", guía de módulos y dependencias,
      referencia de la API pública; revisar plantilla de `lfs-insim init`
- [ ] CHANGELOG.md y convención de versionado (semver)
- [ ] (Opcional, decidir con el usuario) publicación en PyPI

**Criterio de aceptación:** `pip install` desde el repo funciona fuera del proyecto;
CI verde; un desarrollador externo puede seguir el quickstart sin ayuda.

---

## Fase 5 — ai_control: red de seguridad y estabilización (antiguo plan F1–F2)

- [ ] Tests de caracterización de `navigation.py` (planificación de enlaces, nodo más cercano)
- [ ] Tests de caracterización de `traffic.py` (radar / `_scan_lane_ahead`, ACC, overtake)
- [ ] Tests de `physics.py` (volante/pedales/marchas) con telemetría sintética
- [ ] Infra de fixtures: telemetría y grafo de calles sintéticos, sin conexión a LFS
- [ ] Revisar el "PARCHE DE SEGURIDAD MATEMÁTICO" (`traffic.py:655`) y sustituirlo por lógica correcta
- [ ] Auditar el hot-loop `on_ISP_MCI` (coste por tick, frecuencia real) — con el dispatch
      ya fuera del hilo IO (Fase 3)
- [ ] Consolidar radar/geometría en unidad testeable; revisar FSM de adelantamiento

**Criterio de aceptación:** lógica de P2 congelada por tests; sin parches ad-hoc; el usuario
valida en LFS.

---

## Fase 6 — ai_control: refactor estructural y consolidación (antiguo plan F3–F4)

- [ ] Dividir `map_ui.py` (1841), `map_recorder.py` (1604), `traffic.py` (1084) (**P3**)
- [ ] Reducir superficie cross-mixin de `base.py` (**P4**)
- [ ] Limpiar nombres del modelo de estado (`behavior.py`, **P7**)
- [ ] Actualizar README/CLAUDE.md con la arquitectura final; revisión final del diagnóstico

---

## 🔀 Merge a `main`

Todo el refactor vive en la rama **`refactor/estabilizacion`**. `main` permanece intacta
hasta el merge. **Criterio para mergear a `main` ("estable"):**

- Las fases del plan acordadas están completadas.
- `pytest` en **verde** desde `.venv` (+ CI verde cuando exista, Fase 4).
- El usuario ha **validado el comportamiento en LFS** (no hay regresiones funcionales).

El merge lo decide y autoriza el usuario. Tras el merge, se continúa desde `main`.

## Ideas / pendientes sin fase asignada

- **P9**: decidir qué hacer con `tools/setup_lfs.py` (roto: importa `DESIRED_LFS_CONFIG`,
  que no existe en `settings.py`) — recuperarlo o eliminarlo.
- Migrar `rutas_grabadas.txt` a JSON cuando se toque `RouteManager` (ver P6).
- **P8**: confirmar contra `docs/InSim.txt` el caso de string variable vacío sin padding.
- `interval` a 100 ms como cambio deliberado, si se quiere, al auditar el hot-loop (Fase 5).
