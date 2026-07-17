# 📍 Estado actual

> Actualizado: **2026-07-17** — **S46**: **8.6.5 (UI de mapeo) HECHO**. La herramienta de cesión
> está entera en el modelo nuevo: el link con toggle + un punto + T, la zona con polígono + tabla
> auto-poblada. **Suite y CI VERDES otra vez: 914 pasan, 0 fallan** (los 9 rojos que dejó S45 a
> propósito han caído, que era justo lo que este bloque tenía que arreglar).
>
> ✅ **YA PUEDES MAPEAR EN LFS.** La restricción de S45 se levanta: `map_ui.py` y `map_recorder.py`
> ya no tocan campos borrados. El `AttributeError` que acechaba en `!map whereami`/overlay de zona
> está arreglado **y con red** (no tenía ninguna: por eso se coló hasta aquí).
>
> **▶️ PRÓXIMO: 8.6.6 (render)** → 8.6.7 (conducta de la zona) → 8.6.8 (cierre del bloque).
> **Tienes 1 ficha pendiente: [U9](ACCIONES_USUARIO.md)** — validar la herramienta en LFS. **Ya la
> empezaste** (el mapa trae `Erase_test->PitLane` con `yield_type=YIELD` y punto marcado ⇒ la
> herramienta graba bien): **falta tu veredicto**. **No bloquea** el 8.6.6 (el render no toca la
> UI). Contrato: `PLAN.md § Fase 8, bloque 8.6`.
>
> 🗺️ **El mapa creció en S46** (roads **226**, road_links **387**, lateral_links **50**) y el JSON
> quedó **migrado al modelo del 8.6** en el primer guardado: los 374 links cambiaron de esquema sin
> cambiar de valores. `test1` perdió en disco `radius_m` y `priority_rules` — **rescatadas a
> `PLAN.md § 8.7`** antes de que solo vivieran en el historial de git.

**Rama de trabajo: `refactor/estabilizacion`** (`main` intacta hasta el merge). Sync por GitHub:
`git pull` al arrancar, commit + `git push` al cerrar (si el push se cuelga: MODUS §7 y la memoria
del equipo `git-push-gcm-workaround`).

## Dónde estamos

- **Fases 1–6 completas.** Core refactorizado y publicable; Fase 6 (pre-publish) cerrada en S31.
- **Fase 7 (robustez de conducción freeroam) COMPLETA Y VALIDADA** (código S34; validada en LFS en
  S43: U3–U7 todos OK). Cerrada.
- **Fase 8 (intersecciones) es la fase activa.** 8.1–8.5 hechos; **8.6 (rediseño de la cesión)**
  con el diseño cerrado en S44 y la implementación en marcha: **8.6.1/2/3 (S45) + 8.6.5 (S46)**
  hechos. Faltan **8.6.6 (render)**, **8.6.7 (conducta de la zona)** y **8.6.8 (ficha U de cierre)**.
- **Merge a `main` + publish a PyPI esperan** a Fase 8 validada y a la cola de abajo (criterios en
  `PLAN.md § Merge`). PyPI está **preparado sin publicar** (S17; runbook `PUBLICACION.md`).

## Lo que hizo S46 (para no releerlo del historial)

- **Detalle del link:** toggle `[NONE|YIELD|STOP]` · `[+ Marcar punto]` (UN punto, un clic, del
  coche del que clica) · `[Auto]` · `[Borrar]` · T con **float efectivo** + `[Usar default]`.
- **Detalle de la zona:** grabador de polígono (reusa el grabador normal `type="zone"`) · T ·
  **tabla auto-poblada** con toggle por road, `[X]` y `[Re-detectar]`.
- **Muertos:** grabador por fases de la `yield_line`, pantalla `ask_t`, picker de zonas del link,
  editor de `priority_rules`, `_ELEM_FIELDS["zone"]["radius_m"]` y `LocationContext.zone_radius`.
- **Backend:** `_cmd_set` (`yield_type` + tabla `roads` con `set;Via,TIPO` / `del;Via` / `clear`) ·
  `_cmd_rec_end` (zona ⇒ **≥3 puntos** + auto-poblado) · `_cmd_check` al modelo nuevo ·
  `!map whereami` y `!map info` sin campos muertos · `autodetect_zone_roads` (re-escaneo que
  conserva los tipos).
- **Geometría nueva:** `auto_yield_point` (retrocede **por el trazado**, dobla la esquina en un
  link en L) + dial **`yield_auto_setback_m`** (5.0).
- **Skill `ai-control-map-ui` actualizada**: documenta los dos mecanismos, el reparto de CIDs
  (zona 134-151 / link 152-160) y una lista de "muerto, no lo resucites".

## Decisiones de S46 (no las rediscutas: están en PLAN § 8.6 y en HISTORIAL)

1. **`[Auto]` retrocede `yield_auto_setback_m` = 5 m** (elegido por el usuario por selector). El
   diseño no decía cuánto; el cruce cae en el EJE de la road que cruzas. Es **dial**, no
   constante, para afinarlo en LFS sin tocar código.
2. **La tabla de la zona se repuebla SOLO al grabar el polígono y con `[Re-detectar]`** (elegido
   por el usuario por selector): "auto-poblada" y "borrable" se contradicen si se repuebla sola.
3. **`[Auto]` también vale para el link que no cruza nada**: el punto de unión con la `to_road` es
   un punto de conflicto más (S45) ⇒ Auto para antes de la **incorporación**.
4. **El `rec_end` inválido descarta los puntos**: contrato preexistente de TODOS los tipos, no del
   8.6. No se tocó; solo se hizo explícito en el mensaje.

## Bloqueos / restricciones ahora mismo

- **El diseño del 8.6 está aprobado (S44): se implementa, no se rediscute.** Si al implementar
  aparece algo que el diseño no previó, **parar y preguntar** en vez de improvisar una variante
  (en S46 pasó dos veces: los dos huecos se preguntaron por selector — ver decisiones 1 y 2).
- **U9 no bloquea el 8.6.6** (el render no toca la UI), pero sí conviene hacerla pronto: el 8.6.7
  (conducta de la zona) sí se apoya en que el polígono se pueda grabar bien.
- La migración de `test1` (8.7) espera a que el 8.6 esté entero.
- El **merge** espera a: Fase 8 hecha y validada + cola de `ACCIONES_USUARIO.md` despejada +
  pytest y CI verdes.
- Pendiente del protocolo (PLAN § Tooling): **revisión adversarial en sesión fresca**, DESPUÉS de
  haberlo usado unas sesiones (regla §6 del propio protocolo).

## Lo que te toca a ti

**1 acción pendiente: [U9](ACCIONES_USUARIO.md)** — **ya la empezaste en el juego**; lo que falta
es tu **veredicto** (las fichas no las cierro yo). De paso, dime si `Erase_test` (37 nodos + su
link) es basura de la prueba o la quieres: está commiteada y **no la borro por mi cuenta**.

Después traerá otra: **regrabar `test1` como polígono** (8.7; su forma vieja no se convierte sola,
pero sus reglas ya están rescatadas en `PLAN.md § 8.7`).

## Notas operativas

- Tests: `.venv\Scripts\python.exe -m pytest -q` (**914 pasan / 0 fallan**). El conteo de
  `south_city` en `test_map_persistencia.py` es de **caracterización**: se re-basa cuando el
  usuario amplía el mapa (S42, S44, **S46 → 226/387/50**) — que falle tras un remapeo es normal.
  Python 3.9 se verifica vía CI: `gh run list --branch refactor/estabilizacion` (**verde**).
- Cierre de sesión: MODUS §2 — el último paso es `.venv\Scripts\python.exe scripts\close_check.py`
  (debe dar PASS) y pegar su salida.
- Presupuesto de lectura al arrancar: MODUS §1 (qué se lee entero, qué en parte y qué NO).
- La skill `ai-control-map-ui` está **al día con el 8.6.5**: úsala ANTES de abrir `map_ui.py`.
- El **render (8.6.6)** es el próximo y está entero en el modelo viejo: `map_renderer.py` pinta
  `yield_line` (lista) y `radius_m`, que ya no existen — hay que pasarlo a la línea **derivada**
  del `yield_point` y al polígono con su tabla. Su red es `test_map_renderer.py` (del 8.5).
- Backlog offline sin fase (no bloquea el merge): desacople profundo de `base.py` (P4), tipado
  gradual, DX del connect fallido, splits post-merge de `map_ui`/`map_recorder` → `PLAN.md § Ideas`.
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py` y
  `pip install -e ".[dev]"`.
