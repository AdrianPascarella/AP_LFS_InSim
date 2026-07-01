# 📜 Historial de sesiones

> Bitácora append-only. Una entrada por sesión, la más reciente arriba.
> Formato: fecha, qué se hizo, decisiones, commits.

---

## S01 — 2026-07-01 — Escaneo inicial y creación del sistema de contexto

**Qué se hizo:**
- Escaneo general del proyecto (estructura, core, `ai_control`, config, tests, git).
- Diagnóstico completo volcado en `DIAGNOSTICO.md` (7 problemas P1–P7 + inventario de lo sano).
- Plan por fases (0–4) en `PLAN.md`.
- Creado el sistema de contexto persistente en `docs/dev/`: `00_INDEX`, `MODUS_OPERANDI`,
  `ESTADO_ACTUAL`, `DIAGNOSTICO`, `PLAN`, `HISTORIAL`.
- Enganchado el arranque automático en `CLAUDE.md` (leer `docs/dev/` al iniciar sesión).
- Creada la rama **`refactor/estabilizacion`** para todo el trabajo de refactor; `main`
  queda intacta hasta el merge final.

**Decisiones tomadas (con el usuario):**
1. El contexto de trabajo se **versiona** en `docs/dev/` (no en `.claude/` local).
2. Se empieza por la **Fase 0 (Cimientos)**.
3. Red de seguridad para refactorizar = **tests de caracterización primero**.
4. Todo el refactor va en la rama **`refactor/estabilizacion`**; **merge a `main` solo
   cuando esté todo estable** (suite verde + validación en LFS).

**Hallazgos clave:**
- Core sano; deuda concentrada en `ai_control`.
- Entorno no reproducible: paquete sin instalar y `pytest` ausente (Python sistema 3.14).
  221 tests sin poder ejecutarse.
- Lógica frágil (traffic/navigation/radar): la mayoría de commits recientes son fixes.
- `interval:10` en settings contradice los 100 ms documentados.

**Estado del repo:** partimos de `main` limpia (commit `131c966`). Creada la rama
`refactor/estabilizacion`; los archivos nuevos de `docs/dev/` y la edición de `CLAUDE.md`
están en el working tree de esa rama, **sin commitear** (a la espera de que el usuario
decida commitear).

**Próximo paso:** ver `ESTADO_ACTUAL.md` → montar `.venv`, instalar deps, correr `pytest`.
