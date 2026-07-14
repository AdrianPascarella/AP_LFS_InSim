# 📍 Estado actual

> Actualizado: **2026-07-14** — **S40** (meta, no toca el proyecto): el protocolo gana
> **`ACCIONES_USUARIO.md`** — un archivo propio para todo lo que necesita tus manos o tu criterio,
> con ficha por acción (pasos, resultado esperado, señales de fallo) y **bloqueo blando**: paro y
> pregunto antes de trabajar sobre algo que una ficha abierta bloquea. Cambio hecho en las **tres
> capas** (portable, skill de Claude y este proyecto) y verificado por `close_check.py` +
> `parity_check.py`. Detalle en `HISTORIAL.md` S40 y en `MODUS_OPERANDI.md §8`.
>
> **S39**: **bloque 8.3 (conducta de cesión) hecho en verde (809/809)**: el orquestador frena ante
> la `yield_line` del RoadLink comprometido (ACC contra un coche fantasma a `PARADA_ABSOLUTA_M`
> tras la línea → el morro para EN la línea), con punto de compromiso e histéresis del fix (5);
> `_yield_threat_detected` (zones.py) compone los predicados de `traffic/yielding.py`. **Modelo
> viejo (zona-área + `priority_rules`) RETIRADO de la conducta** (sus restos de datos/UI caen en
> 8.6).
>
> **▶️ PRÓXIMO: bloque 8.4 — UI de mapeo** — pero **U1 y U2 lo bloquean** (validar la pestaña
> Grabar antes de volver a tocarla: ver "Lo que te toca a ti"). Contenido del 8.4: grabador de
> puntos de la `yield_line` + T + picker de zona en el detalle del link (diseño S38 punto 8: default
> SIEMPRE manual, TypeIn de T al terminar). **Usar la skill `ai-control-map-ui` ANTES de abrir
> `map_ui.py`**; tests `test_map_ui_*`. Después: 8.5 render → 8.6 migración (`test1` + retirar
> editor de `priority_rules`) → 8.7 validación en LFS.
>
> ⚠️ **Desde el 8.3, en el juego NO cede nadie en ningún cruce** hasta que existan `yield_line`
> en el mapa (8.4) o se migre `test1` (8.6). Es lo esperado, no una regresión.

**Rama de trabajo: `refactor/estabilizacion`** (`main` intacta hasta el merge). Sync por GitHub:
`git pull` al arrancar, commit + `git push` al cerrar (si el push se cuelga: MODUS §7 y la memoria
del equipo `git-push-gcm-workaround`).

## Dónde estamos

- **Fases 1–6 completas.** Core refactorizado y publicable; Fase 6 (pre-publish) cerrada en S31.
  Solo quedaba abierta **W4** (ceda-el-paso en LFS), que se rehace en la Fase 8.
- **Fase 7 (robustez de conducción freeroam) COMPLETA EN CÓDIGO** (S34): los 5 fixes hechos; el
  (2) validado; (1)(3)(4) + el guard están en la cola de abajo. Sin trabajo offline pendiente.
- **Fase 8 (intersecciones) es la fase activa; diseño cerrado en S38.** Bloques **8.1, 8.2 y 8.3
  hechos** (8.1/8.2 en S38, 8.3 en S39); quedan 8.4 UI → 8.5 render → 8.6 migración → 8.7
  validación (decisiones + checklist en `PLAN.md § Fase 8`), red de tests primero en cada bloque.
- **Merge a `main` + publish a PyPI esperan** a Fase 8 validada y a la cola de abajo (criterios en
  `PLAN.md § Merge`). PyPI está **preparado sin publicar** (S17; runbook `PUBLICACION.md`).

## Lo que te toca a ti

**7 acciones pendientes, 2 de ellas bloquean el 8.4** → **[`ACCIONES_USUARIO.md`](ACCIONES_USUARIO.md)**.
Empieza por **U1** y **U2** (las dos de la pestaña Grabar, ~8 min en total: probablemente ya las
usaste al mapear y basta confirmar). Las 5 de conducción (U3–U7) no bloquean nada, pero la cola es
larga: conviene una ronda de validación en LFS antes de apilar más cambios de tráfico.

Las fichas llevan pasos, resultado esperado y qué contarme si falla. No se cierran solas: las cierro
yo cuando me das tu veredicto (`MODUS_OPERANDI.md §8`).

## Bloqueos / restricciones ahora mismo

- **El 8.4 (UI de mapeo) está bloqueado en blando por U1 y U2**: el 8.4 vuelve a tocar la pestaña
  Grabar, y esos dos cambios de S32 siguen sin validar. Si se apila el 8.4 encima, un fallo posterior
  tendrá dos sospechosos y tu veredicto dejará de distinguirlos. Se puede saltar el bloqueo si lo
  pides — se registra en la ficha y en el historial.
- El **diseño** del 8.4 no está bloqueado por nada: S38 ya fija cómo debe ser el grabador de la línea.
- El **merge** espera a: Fase 8 hecha y validada + cola de `ACCIONES_USUARIO.md` despejada + pytest
  y CI verdes.
- Pendiente del protocolo (PLAN § Tooling): **revisión adversarial en sesión fresca**, DESPUÉS de
  haberlo usado unas sesiones (regla §6 del propio protocolo).

## Notas operativas

- Tests: `.venv\Scripts\python.exe -m pytest -q` (**809/809**; 824 de S39 − 15 del modelo viejo).
  Python 3.9 se verifica vía CI: `gh run list --branch refactor/estabilizacion`.
- Cierre de sesión: MODUS §2 — el último paso es `.venv\Scripts\python.exe scripts\close_check.py`
  (debe dar PASS) y pegar su salida.
- Presupuesto de lectura al arrancar: MODUS §1 (qué se lee entero, qué en parte y qué NO).
- Backlog offline sin fase (no bloquea el merge): desacople profundo de `base.py` (P4), tipado
  gradual, DX del connect fallido, splits post-merge de `map_ui`/`map_recorder` → `PLAN.md § Ideas`.
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py` y
  `pip install -e ".[dev]"`.
