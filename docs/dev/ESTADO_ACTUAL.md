# 📍 Estado actual

> Actualizado: **2026-07-15** — **S42**: **bloque 8.5 (render de la cesión) hecho en verde
> (855/855)**. `map_renderer.py` pinta ahora la **`yield_line`** de cada RoadLink como línea de
> detención (magenta grueso con marcadores, color reservado nuevo `YIELDLINE_COLOR`) rotulada
> con su **T**, y las **zonas** muestran su T (`T=<n>s` / `T=def`). Se extrajo primero un seam
> puro y testeable `_draw_elements(ax, data, road_lw, link_lw)` (**verificado byte-idéntico** al
> render anterior) y luego se añadió el dibujo de cesión, con red en rojo primero: 17 tests
> nuevos (`test_map_renderer.py`, 10 de caracterización + 7 de cesión). La parte "en Elementos"
> del diseño ya la cubre el detalle textual del 8.4 (whereami es texto, no lienzo). Detalle en
> `HISTORIAL.md` S42.
>
> **Al arrancar** había mapas sin commitear (nuevo mapeo de `south_city`: +vías) → protegidos
> (backup+commit+push, `4cfc95e`) e integrados los 3 commits de S41 por rebase. El mapa creció
> (223 roads / 374 links / 40 laterales) → re-basados los conteos de `test_map_persistencia.py`.
>
> **▶️ PRÓXIMO: bloque 8.6 — migración** — convertir `test1` al modelo nuevo (grabar su
> `yield_line` con la UI del 8.4) y **retirar `priority_rules`** del JSON, del código muerto y de
> su editor en la UI. **Bloqueado en blando por U8** (migrar usa la UI del 8.4, aún sin validar).
> Después: 8.7 validación en LFS.
>
> ⚠️ Sigue siendo esperado que **en el juego no ceda nadie** hasta que existan `yield_line`
> en el mapa (ya se pueden grabar con la UI del 8.4 → U8) o se migre `test1` (8.6). El render
> nuevo tampoco muestra líneas de cesión en los 3 mapas actuales porque aún no tienen datos.

**Rama de trabajo: `refactor/estabilizacion`** (`main` intacta hasta el merge). Sync por GitHub:
`git pull` al arrancar, commit + `git push` al cerrar (si el push se cuelga: MODUS §7 y la memoria
del equipo `git-push-gcm-workaround`).

## Dónde estamos

- **Fases 1–6 completas.** Core refactorizado y publicable; Fase 6 (pre-publish) cerrada en S31.
  Solo quedaba abierta **W4** (ceda-el-paso en LFS), que se rehace en la Fase 8.
- **Fase 7 (robustez de conducción freeroam) COMPLETA EN CÓDIGO** (S34): los 5 fixes hechos; el
  (2) validado; (1)(3)(4) + el guard están en la cola de abajo. Sin trabajo offline pendiente.
- **Fase 8 (intersecciones) es la fase activa; diseño cerrado en S38.** Bloques **8.1–8.5
  hechos** (8.1/8.2 en S38, 8.3 en S39, 8.4 en S41, 8.5 en S42); quedan 8.6 migración → 8.7
  validación (decisiones + checklist en `PLAN.md § Fase 8`), red de tests primero en cada bloque.
- **Merge a `main` + publish a PyPI esperan** a Fase 8 validada y a la cola de abajo (criterios en
  `PLAN.md § Merge`). PyPI está **preparado sin publicar** (S17; runbook `PUBLICACION.md`).

## Lo que te toca a ti

**6 acciones pendientes; ahora U8 SÍ bloquea el próximo paso** → **[`ACCIONES_USUARIO.md`](ACCIONES_USUARIO.md)**.
Empieza por **U8** (la UI nueva del 8.4, ~10 min): el 8.6 mapeará `test1` con esa herramienta y
es lo siguiente, así que su veredicto desbloquea la Fase 8. Las 5 de conducción (U3–U7) siguen
sin bloquear nada, pero la cola es larga: sigue recomendada una ronda de validación en LFS antes
de apilar más cambios de tráfico.

Las fichas llevan pasos, resultado esperado y qué contarme si falla. No se cierran solas: las
cierro yo cuando me das tu veredicto (`MODUS_OPERANDI.md §8`).

## Bloqueos / restricciones ahora mismo

- **El 8.6 (próximo paso) está bloqueado en blando por U8**: migrar `test1` significa grabar sus
  `yield_line` con la UI del 8.4; hacerlo sobre una herramienta sin validar dejaría dos
  sospechosos si luego la cesión falla en el juego. Se puede saltar el bloqueo si lo pides.
- El **merge** espera a: Fase 8 hecha y validada + cola de `ACCIONES_USUARIO.md` despejada +
  pytest y CI verdes.
- Pendiente del protocolo (PLAN § Tooling): **revisión adversarial en sesión fresca**, DESPUÉS de
  haberlo usado unas sesiones (regla §6 del propio protocolo).

## Notas operativas

- Tests: `.venv\Scripts\python.exe -m pytest -q` (**855/855**; 838 de S41 + 17 del 8.5).
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
