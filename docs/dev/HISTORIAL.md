# 📜 Historial de sesiones

> Bitácora append-only. Una entrada por sesión, la más reciente arriba.
> Formato: fecha, qué se hizo, decisiones, commits.

---

## S04 — 2026-07-02 — Protocolo 0.8C5 + auditoría del core y plan profesional

**Qué se hizo:**
- El usuario reemplazó `docs/InSim.txt` por el nuevo de LFS, que resultó ser **solo un
  puntero de 6 líneas** a lfs.net/programmer. Se recuperó la spec completa **0.8C5** de
  `lfs.net/programmer/insim` (extraída del HTML) y se restauró como `docs/InSim.txt`.
- Diff spec vieja (0.8A) vs nueva (0.8C5): cambios acotados. **Framework actualizado**:
  - `ISP.SET=70` + dataclass `ISP_SET` (136 bytes, `Setup[120]` crudo) + registro en
    `INSIM_PACKETS` + stub `.pyi` regenerado.
  - `ISF.SET` (bit 12); `ISP_NPL.Sp2` → `RIFlags` + enums `RIF`/`SAI` + `RIF_SAI_SHIFTS`;
    `CCI.RETIRED`; `NLP_MAX_CARS` 40→48; `HOSTF` +6 valores (SHOW_FUEL..NO_FLOOD).
  - 12 tests nuevos (`tests/test_protocol_08c5.py`), incluida decodificación real de un
    IS_SET de 136 bytes. Suite: **233/233 verde**.
  - Fichas del tutorial actualizadas (nueva `ISP_SET.md`; ISI/MCI/NLP/NPL/SLC).
- **Nueva directiva del usuario:** revisar el framework, identificar problemas de diseño y
  hacer un plan para llevarlo a **nivel profesional** (usable por otros desarrolladores).
  Romper los insims existentes es aceptable.
- **Auditoría del core completa** (client, app, loader, io, sender, state, cli, packets):
  registrados **P11–P20** en `DIAGNOSTICO.md`. Los graves: P11 (InSimApp hereda de
  InSimClient; el "coup d'état" compensa esa herencia), P12 (sin reconexión: proceso
  zombie si LFS se cae), P13 (sockets/cliente como singletons de módulo), P14 (el core
  importa `config.settings` del CWD; `sys.path` hack en cli.py). Otros: API pública
  indefinida (P15), packaging/tooling (P16: `readme="README"` roto, sin CI/lint/mypy),
  código muerto (`_resolve_dependencies`, P17), envío UDP roto (P18), serialización
  duplicada (P19), loader traga errores (P20).
- **`PLAN.md` reescrito**: F1 red de seguridad del core (golden-bytes + sockets falsos) →
  F2 arquitectura (composición, sin globals, config del paquete, API pública) → F3
  robustez (reconexión, dispatch fuera del hilo IO) → F4 DX/packaging (ruff, mypy, CI,
  docs, PyPI opcional) → F5–F6 ai_control (el plan antiguo).
- Corregido de paso CLAUDE.md: `on_tick` corre a ~100 ms fijos (sleep hardcodeado),
  no cada `interval` ms (P17).

**Decisiones tomadas:**
1. La spec del protocolo se mantiene **versionada y completa** en `docs/InSim.txt` aunque
   LFS ya no la distribuya (fuente de verdad offline).
2. El core primero, `ai_control` después: no tiene sentido trocear `ai_control` sobre una
   API que va a cambiar (F2 rompe la herencia InSimApp→InSimClient).
3. `Setup[120]` de ISP_SET se modela como `list[int]` (`('B', 120)`), no como string
   (el decoder de strings corrompería datos binarios).

**Pendiente de decisión del usuario:** idioma de la API pública del core (recomendación:
inglés) y publicación en PyPI (Fase 4).

**Estado del repo:** rama `refactor/estabilizacion`, suite 233/233. Commits: spec 0.8C5,
soporte de protocolo, fichas del tutorial, auditoría + plan (docs/dev).

**Próximo paso:** ver `ESTADO_ACTUAL.md` → Fase 1: golden-bytes de serialización.

---

## S03 — 2026-07-02 — Cierre de Fase 0: limpieza de bajo riesgo

**Qué se hizo:**
- Arranque según protocolo: rama al día con origin, working tree limpio, docs leídas.
- **Eliminado `src/lfs_insim/utils_temp.py`** (P6): verificado con grep que nadie lo importaba.
- **Limpiado `config/settings.py`** (P5): import muerto de `ISF` fuera; `admin_pass` y
  `LFS_DIR` ahora se leen de env (`LFS_ADMIN_PASS`, `LFS_DIR`) con override local en
  `config/settings_local.py` (gitignorado; plantilla versionada `settings_local.example.py`;
  creado el local con los valores que estaban hardcodeados para no cambiar nada en esta máquina).
- **Anclada la ruta de `rutas_grabadas.txt`** (P6): `RUTAS_FILE = BASE_DIR / 'rutas_grabadas.txt'`
  en `nav_modes/route/manager.py` (antes ruta relativa al CWD). `import os` muerto eliminado.
- **Descubierto y resuelto P10**: `map_renderer.py` importa `matplotlib` sin declararlo en
  ningún sitio → cualquier import de `ai_control` fallaba en el venv (habría bloqueado la
  Fase 1). Declarado en `insim.json` (`python_dependencies`), añadido al extra `[dev]`,
  instalado en `.venv` (3.11.0), aclarado en CLAUDE.md.
- **Descubierto P9** (registrado, sin arreglar): `tools/setup_lfs.py` importa
  `DESIRED_LFS_CONFIG`, que no existe en `settings.py` → el tool está roto.
- Suite verificada en verde tras cada paso: **221/221**. Verificado también que `settings.py`
  funciona con y sin `settings_local.py`.

**Decisiones tomadas:**
1. **`interval` se queda en 10 ms** y se alinean las docs (README/CLAUDE.md decían 100 ms).
   Razón: la conducción/PID está afinada al ritmo real de 10 ms; cambiarlo sería un cambio
   de comportamiento, no limpieza (prohibido en Fase 0). Si se quiere 100 ms, será un cambio
   deliberado en Fase 2 (auditoría del hot-loop `on_ISP_MCI`).
2. **`rutas_grabadas.txt` sigue versionado** (datos del usuario, conviene sincronizarlos
   entre dispositivos). Migración a JSON pospuesta a cuando se toque `RouteManager`.
3. Los valores por máquina van en `config/settings_local.py` (gitignorado) con fallback a
   variables de entorno; la plantilla `settings_local.example.py` se versiona.

**Estado del repo:** rama `refactor/estabilizacion`, **Fase 0 completada**, suite 221/221.
Commits de la sesión: ver `git log` (limpieza + docs de cierre de fase).

**Próximo paso:** ver `ESTADO_ACTUAL.md` → Fase 1: infraestructura de fixtures sintéticos
y tests de caracterización de `navigation.py` / `traffic.py` / `physics.py`.

---

## S02 — 2026-07-01 — Entorno reproducible y primera suite verde (Fase 0)

**Qué se hizo:**
- Arranque según protocolo: en `refactor/estabilizacion`, `git pull` (al día), lectura de `docs/dev/`.
- Montado el entorno reproducible: `python -m venv .venv` (Python 3.14.6) + `pip install -e ".[dev]"`
  (pytest 9.1.1, `.venv` ya ignorado por `.gitignore`).
- Primera ejecución de la suite: **216/221 verdes**, 5 rojos en
  `tests/test_packet_base.py::TestValidateStringLengths` (padding de strings variables).
- Investigado a fondo (no se tocó código a ciegas): los **5 tests estaban mal, no el código**.
  Esperaban longitudes de `Msg` que **no** son múltiplo de 4, y uno incluso sin terminador null.
  El protocolo obliga a bloques múltiplo de 4 (`Size = bytes/4`), así que el código es correcto.
  Verificado ejecutando el `validate_string_lengths` real sobre cada caso.
- Corregidos los 5 tests para caracterizar el comportamiento real (expectativas + comentarios
  engañosos). Renombrado `test_empty_string_padded` → `test_empty_string_stays_empty`.
  Resultado: **`pytest` = 221/221 verde**.
- Registrado en `DIAGNOSTICO.md`: **P1 marcado RESUELTO**; añadido **P8** (caso borde de
  string vacío sin padding, decisión de diseño pendiente, riesgo bajo).

**Decisiones tomadas:**
1. Ante el conflicto test↔código, la fuente de verdad es el **protocolo LFS** (`Size = bytes/4`
   ⇒ `Msg` múltiplo de 4). Se corrigen los tests, no el código.
2. El comportamiento del string vacío (queda en 0 bytes, sin terminador) se **caracteriza tal
   cual** por ahora; si hay que cambiarlo, será un cambio de comportamiento deliberado (P8).

**Hallazgos clave:**
- La suite arranca en 0,2 s; base sólida para la red de seguridad de Fase 1.
- Los 5 tests rojos nunca se habían ejecutado (nacieron en rojo), no eran una regresión.

**Estado del repo:** rama `refactor/estabilizacion`. Cambio en `tests/test_packet_base.py`
(pendiente de commit al cerrar el hito, junto con las actualizaciones de `docs/dev/`).

**Próximo paso:** ver `ESTADO_ACTUAL.md` → seguir con la limpieza de bajo riesgo de Fase 0
(eliminar `utils_temp.py`, limpiar `settings.py`, anclar ruta de `rutas_grabadas.txt`).

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
5. **Sincronización por GitHub:** `git pull` al iniciar y `git push` al cerrar cada sesión
   (para continuar desde otro dispositivo). Push de la rama de refactor autorizado de forma
   permanente; merge/push a `main` sigue requiriendo permiso.

**Hallazgos clave:**
- Core sano; deuda concentrada en `ai_control`.
- Entorno no reproducible: paquete sin instalar y `pytest` ausente (Python sistema 3.14).
  221 tests sin poder ejecutarse.
- Lógica frágil (traffic/navigation/radar): la mayoría de commits recientes son fixes.
- `interval:10` en settings contradice los 100 ms documentados.

**Estado del repo:** partimos de `main` limpia (commit `131c966`). Creada la rama
`refactor/estabilizacion` y **commiteado** el sistema de contexto + enganche de `CLAUDE.md`
en **`52729c3`** (`chore(docs): sistema de contexto persistente y flujo de rama de refactor`).
Working tree limpio.

**Próximo paso:** ver `ESTADO_ACTUAL.md` → montar `.venv`, instalar deps, correr `pytest`.
