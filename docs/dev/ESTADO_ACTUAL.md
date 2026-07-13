# 📍 Estado actual

> Actualizado: **2026-07-13** — **S37**: aplicado el **protocolo agéntico** a este repo — handoff
> partido a ≤120 líneas (la narrativa histórica está ÍNTEGRA en `HISTORIAL.md § Anexo (S37)`),
> **cola de validación** montada abajo, `scripts/close_check.py` instalado (MODUS §2) y
> **presupuesto de lectura** escrito (MODUS §1). No se tocó código del framework; suite
> **773/773** verificada en este equipo tras el pull. Árbol limpio y en sync.
>
> **▶️ PRÓXIMO: Fase 8 — rediseño de las intersecciones. Es una sesión de DISEÑO primero, no de
> código.** Leer `PLAN.md § Fase 8`: propuesta del usuario (línea de detención + tiempo T colgados
> del RoadLink; zonas por tiempo en vez de por área) y sus **preguntas abiertas**, que hay que
> cerrar ANTES de tocar código. **Falta que el usuario explique cómo quiere mapearlo en la UI** —
> preguntárselo al arrancar; usar la skill `ai-control-map-ui`.

**Rama de trabajo: `refactor/estabilizacion`** (`main` intacta hasta el merge). Sync por GitHub:
`git pull` al arrancar, commit + `git push` al cerrar (si el push se cuelga: MODUS §7 y la memoria
del equipo `git-push-gcm-workaround`).

## Dónde estamos

- **Fases 1–6 completas.** Core refactorizado y publicable; Fase 6 (pre-publish: W1 split
  `utils.py`, W5 sweep de API, W2 `init` con perfiles, W3 refactor interno + radar) cerrada en S31.
  Solo queda abierta **W4** (ceda-el-paso en LFS), que se rehace en la Fase 8.
- **Fase 7 (robustez de conducción freeroam) COMPLETA EN CÓDIGO** (S34): los 5 fixes hechos; el
  (2) validado; (1)(3)(4)(5) + el guard están en la cola de abajo. Sin trabajo offline pendiente.
- **Fase 8 (intersecciones) es la fase activa.** El usuario probó el modelo actual (zona +
  `priority_rules`): *"funcionan, pero son difíciles de crear y su funcionamiento es regular"* →
  NO se da por bueno; trae un diseño propio (semilla y preguntas en `PLAN.md § Fase 8`).
- **Merge a `main` + publish a PyPI esperan** a Fase 8 validada y a la cola de abajo (criterios en
  `PLAN.md § Merge`). PyPI está **preparado sin publicar** (S17; runbook `PUBLICACION.md`).
- S36 fue META (protocolo agéntico portable en `.meta/agentic-protocol/`); S37 lo aplicó aquí.

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
- [ ] ⏳ S33 — **Fix (5): histéresis del ceda-el-paso** (`73bbae7`) → ya no tiembla (gas a fondo
      + freno de mano a ~100 Hz). OJO: validar solo la ausencia de temblor; el ceda-el-paso en sí
      se rehace en la Fase 8.

Herramientas de mapeo (probablemente ya usadas al mapear — confirmar de pasada):

- [ ] ⏳ S32 — **"Link auto"** (pestaña Grabar) → graba un RoadLink sin teclear origen/destino
      (confirmación / conflicto de nombre / sobrescribir).
- [ ] ⏳ S32 — **Ajustes de Grabar** → toggle "Trafico" movido a Grabar, campo "Vel. grabar
      (km/h)", "Auto" pegajoso (cancelar un road ya no lo desmarca).
- [ ] ⏳ S33 — **Editor de `priority_rules` de zonas** (Elementos → Zona, picker de vías) → se usó
      para crear `test1`; confirmar que el flujo completo (alta/quitar reglas) va fino.

Cerradas (referencia):

- [x] ❌ **W4 ceda-el-paso** — probado S35: *"funciona, pero regular"* → **NO superado**; motiva la
      Fase 8. No perder tiempo afinando el modelo viejo.
- [x] ✅ Ya validados: 3 bugs del radar con humanos (S35, "desaparecieron todos los tirones"),
      "Apunta" (S31), fin de vía → espectadores (S29→S30), reconexión de `ai_control` (S20).

## Bloqueos / restricciones ahora mismo

- **La Fase 8 necesita al usuario:** la sesión de diseño no puede cerrarse sin su respuesta sobre
  la UI de mapeo y las preguntas abiertas del PLAN (a quién se vigila, compatibilidad del JSON de
  South City, qué pasa con las `priority_rules` actuales).
- El **merge** espera a: Fase 8 hecha y validada + cola de arriba despejada + pytest y CI verdes.
- Pendiente del protocolo (PLAN § Tooling): **revisión adversarial en sesión fresca**, DESPUÉS de
  haberlo usado unas sesiones (regla §6 del propio protocolo).

## Notas operativas

- Tests: `.venv\Scripts\python.exe -m pytest -q` (**773/773**). Python 3.9 se verifica vía CI:
  `gh run list --branch refactor/estabilizacion` (en este equipo no hay `.venv39`).
- Cierre de sesión: MODUS §2 — el último paso es `.venv\Scripts\python.exe scripts\close_check.py`
  (debe dar PASS) y pegar su salida.
- Presupuesto de lectura al arrancar: MODUS §1 (qué se lee entero, qué en parte y qué NO).
- Backlog offline sin fase (no bloquea el merge): desacople profundo de `base.py` (P4), tipado
  gradual, DX del connect fallido, splits post-merge de `map_ui`/`map_recorder` → `PLAN.md § Ideas`.
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py` y
  `pip install -e ".[dev]"`.
