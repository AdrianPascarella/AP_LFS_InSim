# 📍 Estado actual

> Actualizado: **2026-07-15** — **S41**: **U1 y U2 validadas** por el usuario ("funciona
> perfectamente") → el 8.4 quedó desbloqueado y **se hizo en la misma sesión, en verde
> (838/838)**: sección **"Cesion (ceda el paso)"** en el detalle del RoadLink (Elementos) con
> grabador de la `yield_line` (nace **SIEMPRE manual**, diseño S38), TypeIn de **T** al
> Terminar, picker de **zona a vigilar**, edición de T en el detalle y botón Quitar. Backend:
> rama `yield_line` en `_cmd_rec_end` + `yield_time_s`/`yield_zone_id` en `_cmd_set`
> (`yield_line` bloqueada a mano). 29 tests nuevos (`test_map_ui_link_yield.py`, red en rojo
> primero). Detalle en `HISTORIAL.md` S41.
>
> **▶️ PRÓXIMO: bloque 8.5 — render** — pintar las líneas de detención y los puntos de zona
> (con su T) en `map_renderer.py` → `*_rendered.png` y, si aplica, en la pestaña Elementos.
> No está bloqueado por nada (no toca Grabar ni la conducción). Después: 8.6 migración
> (`test1` con la UI del 8.4 + retirar `priority_rules` del JSON, del código y su editor de
> la UI) → 8.7 validación en LFS.
>
> ⚠️ Sigue siendo esperado que **en el juego no ceda nadie** hasta que existan `yield_line`
> en el mapa (ya se pueden grabar con la UI del 8.4 → U8) o se migre `test1` (8.6).

**Rama de trabajo: `refactor/estabilizacion`** (`main` intacta hasta el merge). Sync por GitHub:
`git pull` al arrancar, commit + `git push` al cerrar (si el push se cuelga: MODUS §7 y la memoria
del equipo `git-push-gcm-workaround`).

## Dónde estamos

- **Fases 1–6 completas.** Core refactorizado y publicable; Fase 6 (pre-publish) cerrada en S31.
  Solo quedaba abierta **W4** (ceda-el-paso en LFS), que se rehace en la Fase 8.
- **Fase 7 (robustez de conducción freeroam) COMPLETA EN CÓDIGO** (S34): los 5 fixes hechos; el
  (2) validado; (1)(3)(4) + el guard están en la cola de abajo. Sin trabajo offline pendiente.
- **Fase 8 (intersecciones) es la fase activa; diseño cerrado en S38.** Bloques **8.1–8.4
  hechos** (8.1/8.2 en S38, 8.3 en S39, 8.4 en S41); quedan 8.5 render → 8.6 migración → 8.7
  validación (decisiones + checklist en `PLAN.md § Fase 8`), red de tests primero en cada bloque.
- **Merge a `main` + publish a PyPI esperan** a Fase 8 validada y a la cola de abajo (criterios en
  `PLAN.md § Merge`). PyPI está **preparado sin publicar** (S17; runbook `PUBLICACION.md`).

## Lo que te toca a ti

**6 acciones pendientes, ninguna bloquea el 8.5** → **[`ACCIONES_USUARIO.md`](ACCIONES_USUARIO.md)**.
Empieza por **U8** (la UI nueva del 8.4, ~10 min): el 8.6 mapeará `test1` con esa herramienta,
así que conviene su veredicto antes de llegar allí. Las 5 de conducción (U3–U7) siguen sin
bloquear nada, pero la cola es larga: sigue recomendada una ronda de validación en LFS antes de
apilar más cambios de tráfico.

Las fichas llevan pasos, resultado esperado y qué contarme si falla. No se cierran solas: las
cierro yo cuando me das tu veredicto (`MODUS_OPERANDI.md §8`).

## Bloqueos / restricciones ahora mismo

- **Nada bloquea el 8.5** (render offline: no toca la pestaña Grabar ni la conducción).
- **El 8.6 queda bloqueado en blando por U8**: migrar `test1` significa grabar sus `yield_line`
  con la UI del 8.4; hacerlo sobre una herramienta sin validar dejaría dos sospechosos si luego
  la cesión falla en el juego.
- El **merge** espera a: Fase 8 hecha y validada + cola de `ACCIONES_USUARIO.md` despejada +
  pytest y CI verdes.
- Pendiente del protocolo (PLAN § Tooling): **revisión adversarial en sesión fresca**, DESPUÉS de
  haberlo usado unas sesiones (regla §6 del propio protocolo).

## Notas operativas

- Tests: `.venv\Scripts\python.exe -m pytest -q` (**838/838**; 809 de S39 + 29 del 8.4).
  Python 3.9 se verifica vía CI: `gh run list --branch refactor/estabilizacion`.
- Cierre de sesión: MODUS §2 — el último paso es `.venv\Scripts\python.exe scripts\close_check.py`
  (debe dar PASS) y pegar su salida.
- Presupuesto de lectura al arrancar: MODUS §1 (qué se lee entero, qué en parte y qué NO).
- La skill `ai-control-map-ui` ya documenta el patrón nuevo del 8.4 (sección por tipo en el
  detalle + sub-pantallas con fase en `current_recording`); usarla ANTES de abrir `map_ui.py`.
- Backlog offline sin fase (no bloquea el merge): desacople profundo de `base.py` (P4), tipado
  gradual, DX del connect fallido, splits post-merge de `map_ui`/`map_recorder` → `PLAN.md § Ideas`.
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py` y
  `pip install -e ".[dev]"`.
