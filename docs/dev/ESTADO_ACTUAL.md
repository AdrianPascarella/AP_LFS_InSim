# 📍 Estado actual

> Actualizado: **2026-07-04** — sesión S17
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**Fases 1, 2, 3 y 4 COMPLETADAS.** FASE 4 (DX y packaging) cerrada en S17:
metadata (S14), subcomandos del CLI (S15), ruff+CI+mypy (S16), docs de usuario
(S17), CHANGELOG + semver (S17) y **PyPI preparado sin publicar** (S17). Suite
469/469 verde; ruff limpio; mypy limpio (core vigilado); wheel construye limpio
y `twine check` pasa. Sin validaciones pendientes en LFS
(tooling/packaging/docs no tocan runtime). **Rumbo decidido al cierre de S17:
seguir con FASE 5 (`ai_control`)**; el merge a `main` + publish a PyPI esperan a
que Fase 5 esté terminada y validada en LFS (ver "Fase activa").

**PyPI preparado sin publicar (último ítem de Fase 4, hecho en S17):** decisión
del usuario = preparar sí, disparar no hasta el merge. Build local validado
(`python -m build` → sdist + wheel `py3-none-any`; `twine check` PASSED); extra
`[publish]` (build+twine) para el ensayo local; workflow
`.github/workflows/publish.yml` con **Trusted Publishing (OIDC, sin tokens)** e
**inerte** — solo `workflow_dispatch`→TestPyPI y `release: published`→PyPI, y
solo operable desde `main`, así que no publica nada por sí solo. Runbook
completo en `docs/dev/PUBLICACION.md` (ensayo local en TestPyPI, configurar
trusted publishers, publish real post-merge). El upload real —incluido el ensayo
en TestPyPI— lo lanza el usuario con sus credenciales (Claude no las tiene).

**CHANGELOG + convención semver (último ítem de contenido de Fase 4, hecho en
S17):** `CHANGELOG.md` en formato Keep a Changelog (español, coherente con el
resto de docs) + sección de convención de versionado. Historial verificado con
git: la versión ha sido `0.2.0` desde el "Starting point" (2026-04-21), **nunca
hubo 0.1.0**, sin tags ni releases → el changelog documenta la 0.2.0 como
**primera versión en preparación** (sección `[Sin publicar]`, sin fecha hasta el
release real), recogiendo todo el refactor por categorías con los cambios que
rompen la API marcados. URL de Changelog en `[project.urls]` (apunta a
`blob/main`, correcto tras el merge) + enlace en el README. Tests de packaging
verdes (23/23). No requiere validación en LFS.

**Docs de usuario (penúltimo ítem de Fase 4, hecho en S17):** nueva carpeta
`docs/guia/` con 4 guías en español, verificadas contra el código:
`quickstart.md` (primer InSim en 5 min: instalar → settings_local → `/insim` →
`lfs-insim init` → `run` → probar en el chat), `modulos-y-deps.md` (manifiesto,
dependencias con constraints de versión y fail-fast, `get_insim`, estado
compartido vía `.extra`, comandos con CMDManager, mixins), `api-publica.md`
(exports de `lfs_insim`, superficie de `InSimApp`, TODAS las claves de
`DEFAULT_CONFIG` con sus defaults reales, las 7 excepciones, los 21 nombres de
`utils`) y `arquitectura.md` (composición/lifecycle/contrato de hilos/política
de errores/auto-reconexión P12+P24 — reemplaza la sección obsoleta del README).
**README reducido a landing page + enlaces** a las guías. La plantilla de
`lfs-insim init` revisada y al día (usa la API pública y CMDManager fluido; no
hubo que tocarla). Corregidas afirmaciones FALSAS del README viejo: la sección
Arquitectura describía el patrón "coup d'état"/Master/`modules[]`/
`insim_packet_io.py`, TODO eliminado en Fase 2; decía que los stubs `.pyi` se
generan por git hook (falso, el hook es un no-op); `insim_name` default es
`LFS-InSim`, no `InSimApp`; faltaba `InSimProtocolError` en la jerarquía.
De paso corregido **CLAUDE.md**: el loader instancia la PRIMERA subclase de
`InSimApp` del entry_point (matching por herencia, no por nombre CamelCase —
por eso `AIControl` funciona pese a que el CamelCase de `ai_control` sería
`AiControl`). Solo docs; cero cambios de runtime. **No requiere validación en LFS.**

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
✅ **Pusheado (tip `e40cfec`) y CI en VERDE** — confirmado por la API de GitHub
(run de `e40cfec` = success) y reproducido en Docker (Linux 3.9.25 → 467 passed,
2 skipped). El "exit 4" que se veía en Actions era el run VIEJO (`b0d0541`,
pre-fix), no el actual.

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

**Fase 5 — `ai_control`** (decidido con el usuario al cierre de S17). Fases 1-4
(el core) COMPLETADAS: el framework está estabilizado, documentado y empaquetado.

**Decisión de rumbo (S17):** continuar con **Fase 5** ahora. `ai_control` es una
insim de ejemplo **sobre** el framework (el escaparate que demuestra para qué
sirve), no el framework en sí — por eso se pule antes de publicar, para un primer
release cohesionado (no hay prisa; el nombre PyPI está libre). **Criterio de
merge acordado:** mergear a `main` cuando **Fase 5 esté terminada + validada en
LFS**; **NO se espera a Fase 6** (refactor estructural de ai_control — cosmético,
no cambia comportamiento; puede hacerse ya en `main` tras el merge). El publish a
PyPI se dispara tras el merge (el framework en sí ya es publicable hoy).

## ▶️ Próximo paso concreto (empezar AQUÍ la próxima sesión)

**Decisión tomada al cierre de S17: seguir con Fase 5 — `ai_control`.** El merge a
`main` + publish esperan a que Fase 5 esté terminada y validada en LFS (Fase 6 va
DESPUÉS del merge; ver "Fase activa" y PLAN § Merge). Empezar AQUÍ:

1. **Arrancar Fase 5 por la RED DE SEGURIDAD** (modus operandi §3: caracterizar
   ANTES de tocar lógica frágil). Clave: **`ai_control` no tiene tests** — es la
   parte del proyecto sin cubrir, y toca traffic/navigation/física (frágil).
   Orden acordado con el usuario:
   1. **Infra de fixtures sin LFS:** telemetría sintética + grafo de calles
      sintético, para poder ejercitar navigation/traffic/physics en tests.
   2. **Tests de caracterización** de esa lógica frágil que congelen el
      comportamiento ACTUAL (red de seguridad).
   3. **Fix de reconexión** (el ítem concreto de S10, con test primero): hacer
      `ai_control` consciente de la reconexión — parar/pausar el hilo daemon
      `_run_test_freeroam` en `on_disconnect` (hoy muere con `InSimConnectionError`
      al enviar desconectado) y resetear estado propio + ownership de IAs en
      `on_reconnect` (hoy ve "0 coches" tras la limpieza de memoria y crea/arranca
      IAs con ownership desincronizado → "La AI X no es una de tus AI's").
   (Antes de tocar: releer PLAN § Fase 5 y, del análisis de S10, la entrada de
   HISTORIAL de S10. Nota: `gh` CLI / `.venv39` / Docker siguen disponibles.)
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

- **PyPI: decidido y PREPARADO (S17), publish real pendiente del merge.** El
  usuario eligió "preparar sí, disparar no". Ya hecho: build validado, extra
  `[publish]`, workflow inerte con Trusted Publishing, runbook
  `docs/dev/PUBLICACION.md`. El nombre `lfs-insim` está LIBRE (S14). Queda, cuando
  el usuario quiera: (1) opcional, **ensayo en TestPyPI** en local (lo lanza el
  usuario con su token); (2) tras el merge a `main`, el **publish real** creando
  un GitHub Release. Acción pública e irreversible (versión liberada no se
  reutiliza, nombre reclamado): por eso va después del merge.
- **Decisión de rumbo abierta (S17):** merge a `main` (+ publish) vs. abrir Fase 5
  (`ai_control`). Ver Próximo paso. La autoriza el usuario.

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
