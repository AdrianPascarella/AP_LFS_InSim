# 📍 Estado actual

> Actualizado: **2026-07-17** — **S45**: **8.6 implementado a MEDIAS**, a propósito y con cierre
> pactado. Hechos y verdes: **modelo de datos** (8.6.1), **geometría/predicados** (8.6.2) y
> **conducta del link** (8.6.3). Faltan **UI** (8.6.5) y **render** (8.6.6). El 8.6.4 (conducta de
> la zona) **no está**: ver abajo.
>
> ⚠️ **LA SUITE Y EL CI ESTÁN ROJOS A PROPÓSITO: 888 pasan, 9 fallan.** Los 9 son de la UI vieja
> (`test_map_ui_link_yield.py`, `test_map_ui_zone_priority.py`), que edita campos que el 8.6 ya
> borró. **No es una regresión: es el trabajo a medias.** Se arreglan al hacer el 8.6.5.
>
> 🚫 **NO MAPEES EN LFS HASTA QUE EL 8.6.5 ESTÉ HECHO.** `map_ui.py` y partes de `map_recorder.py`
> siguen tocando `yield_line` / `yield_zone_id` / `radius_m` / `priority_rules`, que ya NO existen:
> abrir el detalle de un link o de una zona, o usar `!map check` / `!map whereami`, **puede petar
> con AttributeError**. Conducir sí es seguro (la conducta está migrada entera).
>
> **▶️ PRÓXIMO: 8.6.5 (UI de mapeo)** → 8.6.6 (render) → 8.6.7 (conducta de la zona, ex-8.6.4) →
> ficha U de validación → 8.7 migración → 8.8 validación. Contrato: `PLAN.md § Fase 8, bloque 8.6`
> (**léelo entero antes de tocar nada**) y la skill `ai-control-map-ui` ANTES de abrir `map_ui.py`.

**Rama de trabajo: `refactor/estabilizacion`** (`main` intacta hasta el merge). Sync por GitHub:
`git pull` al arrancar, commit + `git push` al cerrar (si el push se cuelga: MODUS §7 y la memoria
del equipo `git-push-gcm-workaround`).

## Dónde estamos

- **Fases 1–6 completas.** Core refactorizado y publicable; Fase 6 (pre-publish) cerrada en S31.
- **Fase 7 (robustez de conducción freeroam) COMPLETA Y VALIDADA** (código S34; validada en LFS en
  S43: U3–U7 todos OK). Cerrada.
- **Fase 8 (intersecciones) es la fase activa.** 8.1–8.5 hechos; **8.6 (rediseño de la cesión)** con
  el diseño cerrado en S44 y la implementación **empezada en S45** (checklist con sub-bloques en
  `PLAN.md § Fase 8`).
- ⚠️ **El 8.6 invalida parte de lo hecho en 8.1–8.5, y es lo esperado**: cambió el modelo de datos,
  así que la UI del 8.4 y el render del 8.5 se rehacen (8.6.5 / 8.6.6).
- **Merge a `main` + publish a PyPI esperan** a Fase 8 validada y a la cola de abajo (criterios en
  `PLAN.md § Merge`). PyPI está **preparado sin publicar** (S17; runbook `PUBLICACION.md`).

## Lo que hizo S45 (para no releerlo del historial)

- **Modelo (8.6.1):** `YieldType` (`NONE|YIELD|STOP`, str-enum) en `enums.py`; `RoadLink` con
  `yield_type` + `yield_point` (**un punto**) + `yield_time_s`; `IntersectionZone` con polígono
  (`has_polygon` ⇒ ≥3) + `yield_time_s` + `roads: Dict[str, YieldType]`. **Borrados**: `yield_line`,
  `yield_zone_id`, `radius_m`, `priority_rules`.
- **Geometría (8.6.2):** `segment_intersection_2d` (en `geometry.py`) + en `traffic/yielding.py`:
  `link_conflict_points` (todas las roads que el trazado pisa, con tolerancia en Z),
  `derive_yield_line` (perpendicular a la tangente) y `roads_touching_polygon` (auto-poblado).
- **Conducta del link (8.6.3):** `zones.py::_yield_threat_detected` reescrito contra los puntos de
  conflicto (**la rama de zona murió**); `orchestrator.py::_stop_pending` implementa el `STOP`
  (para → aguanta `yield_stop_hold_s` → evalúa como `YIELD`); estado nuevo en `FreeroamMode`.
- **Caché:** `map_recorder.get_link_conflict_points()` es perezosa y cacheada por
  `(link_id, tolerancia Z)` — cruzar un link contra 223 roads no cabe en el hot loop. La invalidan
  `_invalidate_road_index()` (roads) y `_invalidate_link_conflicts()` (links).

## Decisiones de S45 (no las rediscutas: están razonadas en HISTORIAL)

1. **Los campos muertos se borran en el 8.6, no en el 8.7.** El PLAN era ambiguo (el 8.7 heredaba
   esa frase de S43, antes de que existiera el diseño S44). El loader filtra claves desconocidas
   (`map_recorder.py::_graph_item_from_json`), así que `south_city.json` carga igual; `test1` ya
   estaba inerte. El 8.7 se queda con lo que sí te necesita: **regrabar `test1`**.
2. **`has_yield` exige tipo Y punto.** Un toggle en `YIELD` sin punto marcado está a medias: no hay
   línea que derivar ⇒ no cede.
3. **La `from_road` no es punto de conflicto** (de la vía que dejas no se cede), y **el punto de
   unión con la `to_road` se añade a mano**: el trazado ACABA ahí y su cruce es degenerado, así que
   la geometría no lo garantiza.
4. **El 8.6.4 (conducta de la zona) se mueve DESPUÉS de la UI** y pasa a llamarse 8.6.7: hoy no hay
   forma de grabar un polígono, así que esa conducta no se podría probar en LFS ni con `test1`.

## Bloqueos / restricciones ahora mismo

- **El diseño del 8.6 está aprobado (S44): se implementa, no se rediscute.** Si al implementar
  aparece algo que el diseño no previó, **parar y preguntar** en vez de improvisar una variante.
- **No mapees en LFS** hasta el 8.6.5 (arriba, en el aviso). Conducir sí es seguro.
- La migración de `test1` (8.7) espera a que el 8.6 esté entero.
- El **merge** espera a: Fase 8 hecha y validada + cola de `ACCIONES_USUARIO.md` despejada +
  pytest y CI verdes.
- Pendiente del protocolo (PLAN § Tooling): **revisión adversarial en sesión fresca**, DESPUÉS de
  haberlo usado unas sesiones (regla §6 del propio protocolo).

## Lo que te toca a ti

**0 acciones pendientes** → **[`ACCIONES_USUARIO.md`](ACCIONES_USUARIO.md)** (la cola sigue a 0
desde S43). Terminar el 8.6 es código mío y **no te necesita**. Cuando esté entero generará una
**ficha U** (validar la herramienta rediseñada en LFS), y el 8.7 traerá otra: **regrabar `test1`
como polígono** (≥3 puntos; su forma no se convierte sola).

## Notas operativas

- Tests: `.venv\Scripts\python.exe -m pytest -q` (**888 pasan / 9 fallan**, los 9 esperados: ver el
  aviso de arriba). El conteo de `south_city` en `test_map_persistencia.py` es de **caracterización**:
  se re-basa cuando el usuario amplía el mapa (S42, S44) — que falle tras un remapeo es normal.
  Python 3.9 se verifica vía CI: `gh run list --branch refactor/estabilizacion` (**rojo esperado**).
- Cierre de sesión: MODUS §2 — el último paso es `.venv\Scripts\python.exe scripts\close_check.py`
  (debe dar PASS) y pegar su salida.
- Presupuesto de lectura al arrancar: MODUS §1 (qué se lee entero, qué en parte y qué NO).
- La skill `ai-control-map-ui` documenta el patrón del 8.4 (sección por tipo en el detalle +
  sub-pantallas con fase en `current_recording`); usarla ANTES de abrir `map_ui.py`. ⚠️ El 8.6
  **mata el grabador por fases** para el punto del link (pasa a ser **un** punto): la skill habrá
  que actualizarla al hacer el 8.6.5.
- Backlog offline sin fase (no bloquea el merge): desacople profundo de `base.py` (P4), tipado
  gradual, DX del connect fallido, splits post-merge de `map_ui`/`map_recorder` → `PLAN.md § Ideas`.
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py` y
  `pip install -e ".[dev]"`.
