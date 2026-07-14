# 📍 Estado actual

> Actualizado: **2026-07-14** — **S39**: **bloque 8.3 (conducta de cesión) hecho en verde
> (809/809)**: el orquestador frena ante la `yield_line` del RoadLink comprometido (ACC contra un
> coche fantasma a `PARADA_ABSOLUTA_M` tras la línea → el morro para EN la línea), con punto de
> compromiso e histéresis del fix (5); `_yield_threat_detected` (zones.py) compone los predicados
> de `traffic/yielding.py`. **Modelo viejo (zona-área + `priority_rules`) RETIRADO de la
> conducta** (sus restos de datos/UI caen en 8.6). Red primero: caracterización del marco del
> orquestador + 21 tests de conducta en rojo (`test_orchestrator.py`).
>
> **▶️ PRÓXIMO: bloque 8.4 — UI de mapeo.** Grabador de puntos de la `yield_line` + T + picker de
> zona en el detalle del link (diseño S38 punto 8: default SIEMPRE manual, TypeIn de T al
> terminar). **Usar la skill `ai-control-map-ui` ANTES de abrir `map_ui.py`**; tests
> `test_map_ui_*`. Después: 8.5 render → 8.6 migración (`test1` + retirar editor de
> `priority_rules`) → 8.7 validación en LFS.
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

## Cola de validación en LFS (solo la cierra el usuario)

Conducción (Fase 7 + ACC):

- [ ] ⏳ S35 — **Ley nueva de seguimiento del ACC** (`35870bb`) → al ir bloqueado, IGUALA la
      velocidad del de delante (sin oscilar ni descolgarse); hueco 7 m parado / 8 m en cola.
      Diales: `PARADA_ABSOLUTA_M` (cruise_control.py), `MIN_GAP_FLOOR_M` (orchestrator.py).
- [ ] ⏳ S34 — **Fix (3): radar en la transición road↔roadlink** (`3a628c3`) → en cruces:
      (a) sigue frenando por el lento que se le quedó de frente en la vía que deja; (b) ve a los
      que ya circulan en la vía de destino; (c) NO frena por fantasmas de una transversal lejos
      del cruce. Dial: `_LINK_TRANSITION_WINDOW_M` (radar.py, 25 m).
- [ ] ⏳ S34 — **Guard: no adelantar dentro de un cruce** (`8af862d`) → si resulta demasiado
      conservador, se revierte SOLO ese commit, sin tocar el radar.
- [ ] ⏳ S33 — **Fix (4)** (`d968abf`) → ya no adelanta metiéndose por una vía cerrada.
- [ ] ⏳ S33 — **Fix (1)** (`1a8eaac`) → el intermitente ya no hace flip en salidas RoadLink
      muy juntas (enlace comprometido pegajoso-si-válido).

Herramientas de mapeo (probablemente ya usadas al mapear — confirmar de pasada):

- [ ] ⏳ S32 — **"Link auto"** (pestaña Grabar) → graba un RoadLink sin teclear origen/destino
      (confirmación / conflicto de nombre / sobrescribir).
- [ ] ⏳ S32 — **Ajustes de Grabar** → toggle "Trafico" movido a Grabar, campo "Vel. grabar
      (km/h)", "Auto" pegajoso (cancelar un road ya no lo desmarca).

Cerradas (referencia):

- [x] ♻️ S33 — **Fix (5): histéresis del ceda-el-paso** (`73bbae7`) → OBSOLETA como estaba
      escrita: el modelo viejo ya no existe en la conducta (8.3). La histéresis en sí se
      REUTILIZA en la cesión nueva y se valida con ella en 8.7.
- [x] ♻️ S33 — **Editor de `priority_rules` de zonas** → obsoleto: `priority_rules` ya no rige
      la conducta (8.3); el editor se retira en 8.4/8.6.
- [x] ❌ **W4 ceda-el-paso** — probado S35: *"funciona, pero regular"* → **NO superado**; motiva la
      Fase 8. No perder tiempo afinando el modelo viejo.
- [x] ✅ Ya validados: 3 bugs del radar con humanos (S35, "desaparecieron todos los tirones"),
      "Apunta" (S31), fin de vía → espectadores (S29→S30), reconexión de `ai_control` (S20).

## Bloqueos / restricciones ahora mismo

- Nada bloquea el 8.4 (UI): el diseño S38 ya fija cómo debe ser el grabador de la línea.
- Lo que necesita al usuario es la **validación en LFS** (cola de arriba + 8.7 cuando llegue).
- El **merge** espera a: Fase 8 hecha y validada + cola de arriba despejada + pytest y CI verdes.
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
