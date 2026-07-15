# 📍 Estado actual

> Actualizado: **2026-07-15** — **S43**: **cola de validación despejada + re-plan de la cesión**.
> El usuario validó en LFS: **U3–U7 OK** (ACC, radar en cruce, guards de adelantamiento,
> intermitente) y **U8 = "funciona, a mejorar"** — el flujo de mapeo del 8.4 va bien pero pide
> cambios. Las **6 fichas cerradas** (cola a 0). Antes, esta misma jornada, **S42** cerró el
> **bloque 8.5 (render de la cesión)** en verde (855/855): `map_renderer.py` pinta la `yield_line`
> (magenta) con su T y la T de las zonas; 17 tests. Detalle en `HISTORIAL.md` S42/S43.
>
> **▶️ PRÓXIMO: bloque 8.6 — REDISEÑO de la UX/modelo de cesión** (nace del veredicto de U8 + ideas
> del usuario). Flujo **DISEÑAR → APROBAR → EJECUTAR**: **NO tocar código hasta cerrar el diseño**
> (como en S38). Cuatro frentes: (1) `yield_time_s` como **float** en la UI (hoy muestra el texto
> `"default (4)"`); (2) aclarar/redefinir **`yield_zone_id`**; (3) **auto-`yield_line`** con un
> botón; (4) **zonas con tabla auto-poblada de roads que cruzan + toggle de prioridades** (con
> borrado de falsos cruces por altura). Frentes + recomendaciones de Claude en
> `PLAN.md § Fase 8, bloque 8.6`. Después: **8.7** migración de `test1` (ya con la herramienta
> rediseñada) → **8.8** validación en LFS.
>
> ⚠️ Sigue siendo esperado que **en el juego no ceda nadie** hasta que exista `yield_line` en el
> mapa o se migre `test1` (ahora en el 8.7, tras el rediseño). El punto 4 puede **revivir
> parcialmente** las `priority_rules` que S38 retiró (pero auto-pobladas) — a decidir en el diseño.

**Rama de trabajo: `refactor/estabilizacion`** (`main` intacta hasta el merge). Sync por GitHub:
`git pull` al arrancar, commit + `git push` al cerrar (si el push se cuelga: MODUS §7 y la memoria
del equipo `git-push-gcm-workaround`).

## Dónde estamos

- **Fases 1–6 completas.** Core refactorizado y publicable; Fase 6 (pre-publish) cerrada en S31.
  Solo quedaba abierta **W4** (ceda-el-paso en LFS), que se rehace en la Fase 8.
- **Fase 7 (robustez de conducción freeroam) COMPLETA Y VALIDADA** (código S34; **validada en LFS
  en S43**: U3–U7 todos OK). Cerrada.
- **Fase 8 (intersecciones) es la fase activa; diseño cerrado en S38.** Bloques **8.1–8.5
  hechos** (8.1/8.2 en S38, 8.3 en S39, 8.4 en S41, 8.5 en S42); ahora **8.6 = rediseño de la
  UX/modelo de cesión** (S43, a raíz de U8) → 8.7 migración → 8.8 validación (checklist en
  `PLAN.md § Fase 8`), red de tests primero en cada bloque.
- **Merge a `main` + publish a PyPI esperan** a Fase 8 validada y a la cola de abajo (criterios en
  `PLAN.md § Merge`). PyPI está **preparado sin publicar** (S17; runbook `PUBLICACION.md`).

## Lo que te toca a ti

**0 acciones pendientes** → **[`ACCIONES_USUARIO.md`](ACCIONES_USUARIO.md)** (cola despejada en
S43). El próximo paso (8.6 rediseño) es diseño/código mío; **arranca con una conversación de
diseño** de los 4 frentes, y solo tras aprobarlo se ejecuta. Cuando esté construido generará una
**ficha U nueva** — validar la herramienta rediseñada en LFS.

## Bloqueos / restricciones ahora mismo

- **El 8.6 es DISEÑO primero, no código**: no se implementa nada hasta cerrar y aprobar el diseño
  de los 4 frentes (regla del propio bloque, estilo S38). La migración de `test1` (8.7) espera al
  rediseño — hacerla ahora con la UI actual sería trabajo tirado.
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
