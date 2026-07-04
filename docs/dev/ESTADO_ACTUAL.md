# 📍 Estado actual

> Actualizado: **2026-07-04** — sesión S16
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**Fases 1, 2 y 3 COMPLETADAS. FASE 4 ACTIVA (DX y packaging): metadata
(S14), subcomandos del CLI (S15) y el bloque ruff+CI+mypy (S16) hechos.
Suite 469/469 verde; ruff limpio; mypy limpio (core vigilado). Sin
validaciones pendientes en LFS (tooling/packaging no tocan runtime).
Queda de Fase 4: docs de usuario + CHANGELOG.**

**ruff + CI + mypy (bloque grande de Fase 4, hecho en S16):** adoptado
**ruff** (lint+format, **line-length 88**, reglas conservadoras **E, F, I,
W**; decidido con el usuario). `ruff format` en commit propio (`a3bea56`, 79
archivos, cero comportamiento) con `.git-blame-ignore-revs` para que blame no
apunte al reformateo; lint (`c5a736b`) con autofix seguro + 5 fixes a mano e
ignores acotados (E501 lo posee el formatter; per-file para star-imports
intencionales, imports no-top y enums de una letra del protocolo). **CI**
(`838edac`, `.github/workflows/ci.yml`): jobs lint (ruff) y test (pytest en
matriz Python 3.9/3.11/3.13 + Windows), dispara en push/PR a main y a la rama
de refactor. **mypy gradual** (`8a64881`): vigila los ~14 módulos limpios del
core; backlog por módulo (`ignore_errors`) para packets/loader/decoders/utils;
job de CI `typecheck` con `continue-on-error` (NO bloquea). De paso, 2 errores
type-only del core que los stubs enmascaraban, corregidos (`ISF(0)`; narrowing
de `f.name`). **No requiere validación en LFS.**

**El primer run del CI cazó 2 incompatibilidades reales con Python 3.9**
(`fix(py39)`, commit `a077f41`), ya arregladas y verificadas en un Python
3.9.13 real (venv `.venv39`): union PEP 604 (`X | Y`) en anotaciones runtime
→ `Union`/`Optional` (base.py, insim.py, um_class.py); y el campo self-shadow
`HLVC: HLVC` en ISP_HLV (recursión del `repr` de dataclasses en 3.9) →
forward-ref `"HLVC"`. Guardas: regla ruff **FA102** + la matriz de CI ya
incluye 3.9. Suite 3.9: 467 passed, 2 skipped; 3.14 sigue en 469.
⚠️ **El push de `a077f41` quedó SIN HACER** (Git Credential Manager pedía
reauth interactiva que Claude no puede dar) — hay que pushear y confirmar el
CI en verde.

**Subcomandos del CLI (segundo ítem de Fase 4, hecho en S15):** los antiguos
entry points `generate-stubs` y `update-all` se instalaban como comandos
GLOBALES en el PATH de quien hiciera `pip install` (nombres genéricos que
invaden el entorno ajeno) → plegados en `lfs-insim stubs` y
`lfs-insim update-all`. Dos handlers en `cli.py` (`cmd_stubs`/`cmd_update_all`,
import perezoso) que llaman a `generate_stubs.main()` / `update_all.main()` —
mismo comportamiento que los console-scripts (llamar a `main()`, devolver 0).
Los dos scripts fuera de `[project.scripts]`: **`lfs-insim` es el único
console-script**. Git hook revisado: `.githooks/pre-commit` es un no-op
deshabilitado por el usuario (NO invocaba `generate-stubs` — nada que
migrar); docs corregidas (CLAUDE/README apuntan a `lfs-insim stubs` y ya no
afirman que el hook autogenera stubs). 4 tests nuevos (`tests/test_cli.py`,
rojo primero): despacho de ambos subcomandos + contrato de que `lfs-insim`
es el único script. Verificado además a mano: reinstalación editable
(`pip install -e ".[dev]"`) **elimina los `.exe` viejos** y deja solo
`lfs-insim.exe` con los subcomandos. Suite 469/469. **No requiere validación
en LFS.**

**Metadata del paquete (primer ítem de Fase 4, hecho en S14):**
`readme = "README.md"` (antes apuntaba a un `README` inexistente); licencia
SPDX `license = "MIT"` + `license-files` (build-system sube a
setuptools>=77); **fuente única de versión** en `lfs_insim.__version__`
(pyproject `dynamic = ["version"]`; contrato fijado con test contra la
metadata instalada — si falla tras un bump, reinstalar editable);
`requirements.txt` eliminado; URLs corregidas (Homepage apuntaba al repo
antiguo `Aprendiendo-InSim-LFS`); descripción en inglés + keywords +
classifiers (Python 3.9–3.14). 2 tests nuevos (rojo primero,
`TestVersionUnica`); wheel construye limpio en aislamiento
(`pip wheel . --no-deps`).

**`tick_interval` (cierre de Fase 3, hecho en S13):** la cadencia de
`on_tick` es configurable (segundos, default 0.1 = comportamiento
histórico; mínimo 0.01, valor inválido → `InSimConfigurationError` al
crear el cliente). Clave del diseño: el tick queda DESACOPLADO del sondeo
interno del bucle principal, que sigue fijo a ≤100 ms para
`_connection_lost` y `_handler_error` — un tick lento nunca retrasa la
reconexión (P12) ni el fail-fast. Sin catch-up tras un stall. No es un
timer de precisión; alta frecuencia → handlers MCI/OutSim. 5 tests
(`TestTickInterval`), rojo primero.

**Política de errores de handlers (último ítem de Fase 3, hecho en S13):**
clave `handler_errors` en `DEFAULT_CONFIG` — `'log'` (default) aísla y
loguea con traceback como siempre; `'raise'` (fail-fast, desarrollo) hace
que el primer error de un handler `on_ISP_*` o hook de lifecycle detenga el
cliente: el worker aparca la excepción en `_handler_error` y sale, y el
bucle principal de `start()` la re-lanza con el traceback original.
Excepción deliberada: los `on_disconnect` de `stop()` se aíslan SIEMPRE
(el apagado se completa y todas las apps se enteran). Valor inválido →
`InSimConfigurationError` al crear el cliente. De propina: los errores de
lifecycle en modo 'log' ahora llevan `exc_info=True`. 8 tests nuevos (rojo
primero), incluida integración con FakeLFS. No requiere validación en LFS
(el default no cambia nada). Documentado en CLAUDE.md § Handler error policy.

**Pista de diagnóstico de ISI rechazado (hecho al cierre de S12):** LFS no
da feedback en el socket al rechazar un ISI — solo cierra. El cliente marca
la sesión como "hablada" al primer byte recibido (`_session_received_data`,
reseteado antes de cada ISI) y, si una sesión muere antes de
`reconnect_stable_time` sin haber recibido NADA, `_handle_connection_lost`
loguea la pista ("ISI likely rejected — check admin_pass / InSim version").
El fallback de leer `Game Admin` desde cfg.txt quedó SOLO como idea a
futuro (PLAN § Ideas + comentario en `config/settings.py`). Commit `3f2e2b3`.

**P24 (tormenta de reconexión, hecho en S12 — incidente EN VIVO):** al
intentar conectar desde el dispositivo nuevo, LFS rechazaba el ISI
(`Game Admin abc` en cfg.txt vs `admin_pass: ''` del settings_local recién
copiado del example) y `_reconnect`, que da por buena una reconexión con
solo enviar el ISI, reseteaba el backoff en cada ciclo → ~10 conexiones/s
durante 25 s hasta el "InSim - TCP excess : 127.0.0.1" de LFS. Diagnóstico
confirmado con sondas ISI contra el LFS vivo (0.8C17). Fix: reconexión
**provisional** — si la sesión muere antes de `reconnect_stable_time`
(config nueva, 10 s), el siguiente ciclo retoma la racha (espera previa +
escalado + cuenta para `max_attempts`). El settings_local de este equipo ya
lleva la password. Detalles en DIAGNOSTICO § P24. Commit `759f224`.

**Apagado limpio (ítem de Fase 3, hecho en S12):** resuelta la carrera de
`InSimTransport.close()` detectada en S11 — cada bucle receptor **captura su
evento de stop al arrancar** y `close()` lo deja puesto y lo **REEMPLAZA**
por uno nuevo (nunca `clear()`), además de esperar (join, timeout 2 s) a los
receptores antes de volver. Un receptor que despierte tarde por el socket
cerrado ya no puede disparar `on_connection_lost` espurio tras un cierre
deliberado; `close()` es seguro incluso desde el propio hilo receptor y el
transporte sigue siendo reutilizable. De propina: `InSimClient.stop()` con
check-and-set atómico de `running` (lock solo en el flip del flag) — stops
concurrentes ejecutan el apagado UNA vez y la reentrada desde `on_disconnect`
no se bloquea. La carrera se reprodujo EN ROJO antes del fix (2 tests);
5 tests nuevos en total. Commit `7ee9f38`.

**P18 (envío UDP, hecho en S11):** eliminado el parámetro `use_udp` de
`transport.send` — el envío es **siempre TCP** (LFS solo recibe InSim por TCP;
el socket UDP es solo de bajada: OutSim/OutGauge, NLP/MCI). Documentado en el
docstring del transporte y CLAUDE.md; contrato fijado con test. Commit `844feed`.

**P19 (una sola ruta de serialización, hecho en S11):**
`validate_string_lengths()` (prepare) es la única autoridad del layout de
strings — gana el truncado de los fijos `'Ns'` a N-1 (null final garantizado;
antes vivía en `_extract_values`); `_extract_values()` ya solo codifica a
latin-1 y `struct.pack` rellena los fijos. El decoder ya **no hace `.strip()`**
(corta en el primer null; los espacios significativos se conservan). Dos
cambios deliberados de comportamiento reflejados en los goldens: string fijo
con `len == N` pierde 1 char por el null (antes salía SIN terminador, contra
la spec) y los strings decodificados conservan espacios previos al null.
**Validado por el usuario en LFS (cierre de S11):** pasada normal OK — nada
dependía de los strings recortados del decoder. Commit `720315a`.

**Validación de P2-core en LFS (S10):** el usuario probó conexión + AIs rodando,
cierre abrupto del juego, reapertura del puerto y arranque con el juego cerrado.
El framework se comportó bien en todo (detección de caída en 33–40 ms, backoff,
restauración de sesión, keep-alive bajo tráfico, Ctrl+C limpio en pleno backoff).
Los comportamientos "raros" eran de `ai_control` (no es consciente de la
reconexión: su hilo `_run_test_freeroam` muere al enviar desconectado o enloquece
tras la limpieza de memoria) → apuntado como ítem de Fase 5. Del análisis del log
salieron y se arreglaron en S10: **P22** (orden de `_restore_session` invertido:
ISI → on_reconnect → TINY.NCN/NPL, con test del orden causal) y **P23**
(QuickEdit de la consola Windows congelaba el proceso entero sin dejar traza:
ahora el handler `file` va antes que `console`, `lfs-insim run` desactiva
QuickEdit al arrancar, y el bucle de reconexión deja traza si se abandona).

**P2-core (dispatch fuera del hilo de IO, hecho en S09):** los hilos de IO del
transporte ya NO ejecutan handlers — decodifican, contestan el keep-alive en el
acto (para que una cola ocupada nunca retrase el ping a LFS) y encolan; un
**worker dedicado** (`InSim_Dispatch_Worker`, arrancado en `start()`) despacha
`on_ISP_*` en orden FIFO estricto. Un handler lento ya no bloquea la recepción.
`stop()` cierra el transporte y mete un centinela al FINAL de la cola: lo
pendiente se despacha antes de que el worker salga (join con timeout 2 s,
protegido contra `stop()` llamado desde un handler). `use_thread_pool` y
`max_workers` RETIRADOS de config y cliente (orden no garantizado, sin usuarios).
Contrato de threading documentado (CLAUDE.md + docstring de `insim_client.py`):
handlers en el worker (FIFO); hooks de ciclo de vida en el hilo principal; sin
garantía de orden entre ambos; `send()` thread-safe. `insim_client.pyi`
reescrito (estaba desfasado desde Fase 2). Detectado de paso **P22** (carrera
menor en `_restore_session`, ver DIAGNOSTICO).

**P12 (reconexión, hecho en S08):** el transporte avisa con `on_connection_lost`
cuando el bucle receptor TCP muere sin `close()`; el bucle principal de `start()`
(el que antes quedaba zombie) detecta el evento en ≤100 ms, despacha `on_disconnect`
(desde el hilo principal, como on_connect/on_tick), reintenta con backoff exponencial
(claves `reconnect*` en `DEFAULT_CONFIG`: delay 1 s, factor 2, tope 30 s,
`max_attempts 0` = infinito), reenvía el ISI agregado, re-solicita `TINY.NCN/NPL`
y despacha `on_reconnect` (hook nuevo en cliente y apps). `reconnect: False` o
intentos agotados → `stop()` limpio. `users_management.on_reconnect` limpia su
memoria (los NCN/NPL entrantes la repueblan). `on_tick` se pausa mientras reconecta.

**Migración de insims (hecha en S08):** `ai_control` ya no importa la facade
deprecada — los 10 imports de `insim_packet_class` (9 archivos) pasaron a
`lfs_insim.packets` (ISP_*, `AIInputVal`) y `lfs_insim.insim_enums` (CS, CSVAL,
SND). `users_management` ya estaba migrado (usa `packets`/`insim_enums` directos;
sus enums llegan vía `um_class.py`). Smoke: los 4 insims cargan con
DeprecationWarning-como-error (nadie importa la facade); `lfs-insim list` OK.
Commit `0292a01`.

**P15 (API pública, hecho en S07):** `__all__` en todos los módulos públicos
(`lfs_insim`, `packets/*`, `insim_enums`, `utils`, `exceptions`, `config`). Puntos de
import recomendados: `lfs_insim` (core+config+excepciones), `lfs_insim.packets`
(paquetes; **ya no re-exporta enums**), `lfs_insim.insim_enums`, `lfs_insim.utils`.
`insim_packet_class` queda como facade **deprecada** (DeprecationWarning) que
re-exporta packets+enums como el monolito original — el core ya no la usa;
`ai_control` sí (migración pendiente). El único `import *` interno que contaminaba
(`packets/insim.py` ← enums) es ahora import explícito.

**P20 (fail-fast del loader, hecho en S07):** una dependencia rota aborta la carga
del dependiente con la cadena completa en el mensaje (antes se tragaba y `get_insim`
devolvía `None` mucho después). **P17:** `class INST` duplicada eliminada de
`insim_enums.py`; comentario falso de CLAUDE.md corregido (los constraints de versión
SÍ se aplican). Decisión de si `on_tick` debe ser configurable → Fase 3.

**P14 (config del paquete, hecho en S07):** defaults internos en
`src/lfs_insim/config.py` (`DEFAULT_CONFIG` + `build_config(overrides)`, dict plano).
El core no importa `config.settings` del CWD; el CLI carga la config del proyecto
(`_load_project_config()`) y el loader la propaga (las apps heredan la config
efectiva del cliente).

**P11 (composición, ✅ validado por el usuario en LFS):** `InSimApp(PacketSenderMixin)`
ya no hereda de `InSimClient`; `client.register(app)`; loader con cliente perezoso e
inyectable; dispatch en orden de dependencias. Core en **inglés** (decisión S06).

**P13 (transporte, hecho en S06 tras validar P11):** `InSimTransport` posee sockets
TCP/UDP, hilos receptores, stop y lock **por instancia**; el cliente lo posee
(inyectable) y hace barrera+decode en `_on_raw_bytes`; `client.send = encode_packet
(puro) + transport.send`. `insim_packet_io.py` y el `send_packet` global eliminados.
`insim_state` queda como azúcar: "cliente por defecto" para helpers del mixin
(Command/CMDManager/RouteManager). **Dos clientes coexisten en un proceso** (test de
aceptación en `test_transport.py`). Smoke: `ai_control` carga, CLI OK.

**Validación en LFS (S08):** el usuario probó el estado post-migración (Fase 2
cerrada) y también P12 — la reconexión funcionó al matar/levantar LFS con el
InSim corriendo. **P2-core validado en S10** (ver "Estado").

**Contexto del plan (S04):** framework a nivel profesional; romper insims aceptable.
P11–P21 en `DIAGNOSTICO.md`. Queda gordo: P12 (reconexión, Fase 3).

## Fase activa

**Fase 4 — Experiencia de desarrollador (DX) y packaging**; ver `PLAN.md`.
Fase 3 quedó COMPLETADA en S13 (último ítem: `tick_interval`; la decisión
"¿on_tick configurable?" se resolvió con el usuario: SÍ, desacoplado del
sondeo interno).

## ▶️ Próximo paso concreto (empezar AQUÍ la próxima sesión)

Orden de Fase 4 acordado con el usuario (S14): **CLI → ruff + CI → docs →
CHANGELOG**; PyPI se prepara pero NO se dispara hasta el merge a `main`.
CLI (S15) y ruff+CI+mypy (S16) HECHOS (ver "Estado").

0. **PRIMERO al arrancar: `git push`** — el commit `a077f41` (`fix(py39)`) y
   el cierre de docs de S16 **quedaron sin pushear** (Git Credential Manager
   pedía reauth interactiva que Claude no puede dar; los push los lanza el
   usuario con `! git push origin refactor/estabilizacion`). Luego **verificar
   el CI en verde** en GitHub Actions (alta confianza: la suite ya pasa en un
   Python 3.9.13 real en local, lo mismo que corre el CI). El primer run de
   S16 ya cazó 2 incompatibilidades de 3.9, ya arregladas (ver "Estado"). Si
   quedara algo, arreglarlo antes de seguir. Valorar instalar `gh` CLI (y
   `gh auth login`) para que Claude pueda mirar el CI por sí mismo.
1. **Siguiente ítem — docs de usuario:** quickstart "tu primer InSim en 5
   min", guía de módulos/dependencias, referencia de la API pública; revisar
   la plantilla de `lfs-insim init`. Luego **CHANGELOG.md** + convención
   semver. Con eso se cierra la Fase 4 (salvo la decisión de PyPI).
2. Backlog de **tipado gradual** (ir quitando overrides de `[tool.mypy]` en
   pyproject, módulo a módulo, cuando se toque cada uno): los módulos
   `packets` (dataclasses de protocolo), `insim_loader` (fricción con
   `importlib`: `ModuleSpec | None` sin None-check + kwargs inyectados en
   InSimApp — merece None-checks reales, no `type: ignore`), y
   `insim_packet_decoders`/`utils` (2 errores puntuales cada uno). No urge;
   mypy no bloquea.
3. Idea DX de Fase 4 ya apuntada: el connect inicial fallido imprime un
   traceback feo (`exc_info=True` + re-raise) — valorar mensaje limpio y/o
   `connect_retry` para arrancar el insim antes que LFS. (La pista de ISI
   rechazado ya está hecha; el fallback de cfg.txt está en PLAN § Ideas.)

## Bloqueos / esperando

- Decisión pendiente (Fase 4): ¿publicar en PyPI? Recomendación S14:
  **preparar sí, disparar no todavía.** El nombre `lfs-insim` está LIBRE
  (verificado en S14: `pypi.org/pypi/lfs-insim/json` → 404). Plan: cuando
  llegue CI, ensayar contra **TestPyPI** y dejar un workflow de publicación
  listo; el `pip install` real a PyPI queda para DESPUÉS del merge a `main`
  (acción de cara al público y difícilmente reversible: versión liberada no
  se reutiliza, nombre reclamado). Sin urgencia por reservar el nombre (nicho
  + PyPI desaconseja el squatting). La metadata ya quedó lista para ello (S14).

## Notas para la próxima sesión

- Comando de tests: `.venv\Scripts\python.exe -m pytest -q`.
- **Tests en Python 3.9** (mínimo soportado; el CI y S16 cazaron bugs solo-3.9):
  venv `.venv39` ya creado (Python 3.9.13, gitignorado). Correr con
  `$env:MPLBACKEND='Agg'; .venv39\Scripts\python.exe -m pytest -q`. Reproduce el
  job de CI de 3.9 sin esperar a GitHub. (2 skips esperados: `tomllib` es 3.11+.)
- Tooling nuevo (S16): `python -m ruff check` y `python -m ruff format` (lint+format),
  `python -m mypy` (tipos del core; lee `[tool.mypy]` de pyproject). Config toda en
  `pyproject.toml`. El commit de formato masivo (`a3bea56`) está en
  `.git-blame-ignore-revs`; para que `git blame` local lo salte:
  `git config blame.ignoreRevsFile .git-blame-ignore-revs`.
- Idioma (decisión S06): código nuevo del core en **inglés**; docs/dev, tests e insims
  en español. Ver `MODUS_OPERANDI.md` § 5.
- Los golden-bytes y tests de packet_io de Fase 1 siguen válidos; los de loader y
  dispatch ya están adaptados a la nueva API (registro en cliente).
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py`
  y `pip install -e ".[dev]"`.
- Pendientes sin fase: P8, P9, migración de rutas a JSON (ver `PLAN.md` § Ideas).
