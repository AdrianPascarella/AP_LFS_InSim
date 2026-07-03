# 📜 Historial de sesiones

> Bitácora append-only. Una entrada por sesión, la más reciente arriba.
> Formato: fecha, qué se hizo, decisiones, commits.

---

## S07 — 2026-07-03 — Fase 2: P14 (config del paquete con defaults internos)

**Qué se hizo (segundo bloque, misma sesión) — P15, P17 y P20** (tras validar el
usuario P13/P14/P21 en LFS con `!test hcp` OK):

- **P15 — API pública con `__all__` en todos los módulos:**
  - El core dejó de importar la facade: client/app/sender/decoders/utils/mixin
    importan de `.packets`; `utils.py` toma `SND` de `insim_enums` (dependía de la
    fuga).
  - `insim_packet_class` → facade **deprecada** (DeprecationWarning al importar);
    re-exporta packets **y** enums (superficie del monolito original) para el código
    viejo (`ai_control` la usa aún).
  - `packets/insim.py`: el `from insim_enums import *` (la fuga que contaminaba todo
    `packets`) es ahora un import explícito de 68 enums. `packets/__init__` compone su
    `__all__` desde los submódulos + catálogos (`INSIM_PACKETS`, `OUTSIM_PACKETS`,
    `RECEIVE`, `SEND`, `ALLOWED_PACKETS`). Descubierto de paso: `OutSimPack2` es
    asignación de módulo (`make_dataclass`), no `class` — entró en el `__all__` de
    `outsim.py`.
  - `__all__` también en `insim_enums` (96 nombres; sin fugas de `IntEnum`/`IntFlag`),
    `utils` (21), `exceptions` (7, ahora todas exportadas también en `lfs_insim`),
    `config`, y docstring de API pública en `lfs_insim/__init__.py`.
  - **Reparados los que dependían de la fuga** (escaneo AST de nombres no resueltos,
    sin falsos positivos de comentarios/atributos): `test_insim/main.py` (TINY),
    `_cmds_request.py` (SMALL, TINY), `_cmds_send.py` (12 enums) y
    `tests/test_insim_handlers/test_lifecycle.py`; `test_packet_base.py` migrado a
    `lfs_insim.packets`.
- **P17:** `class INST` **duplicada** eliminada de `insim_enums.py` (dos definiciones
  idénticas, líneas 927 y 1287); CLAUDE.md corregido (decía que los constraints de
  versión "no se aplican todavía" — sí se aplican). `on_tick` configurable → Fase 3.
- **P20 — fail-fast del loader:** dependencia rota aborta la carga del dependiente
  (`InSimModuleError` con la cadena completa, `raise ... from`); eliminado el tragado.
  Tests nuevos: fail-fast simple y cadena transitiva (nieto←hijo←fantasma).
- **Tests:** `tests/test_api_publica.py` (17: `__all__` resuelve en 11 módulos, sin
  duplicados, sin fugas packets↔enums↔stdlib, facade avisa y conserva superficie).
  Suite **420/420**. Smoke: los 4 insims cargan (1 DeprecationWarning esperado de
  `ai_control`); `lfs-insim list` OK.
- **Validación del usuario (inicio del bloque):** P13/P14/P21 probados en LFS real —
  todo bien, incluido `!test hcp`.
- Pendiente del usuario: re-validar en LFS tras P15 (cambiaron imports de insims).

**Qué se hizo (primer bloque):**
- **`src/lfs_insim/config.py` (nuevo):** `DEFAULT_CONFIG` (defaults del framework:
  TCP/ISI/UDP/dispatch; sin valores por máquina como `user_name` o env) y
  `build_config(overrides)` (copia fusionada). Se mantiene **dict plano** en vez de
  dataclass para conservar la superficie `self.config.get(...)` de todos los insims
  (decisión: tipado fuerte puede venir con P15 si compensa).
- **Core sin CWD:** `InSimClient.__init__` e `InSimApp.__init__` usan `build_config`;
  eliminados los dos `from config.settings import get_config`. El core ya no depende
  de ningún archivo del proyecto.
- **Loader:** `InSimLoader(config=...)` — la guarda y la usa al crear el cliente
  perezoso; al instanciar cada app le pasa `config=self.client.config`, así **las apps
  heredan la config efectiva del cliente** (antes cada app releía el CWD por su
  cuenta). Con cliente inyectado, la config del loader se ignora (documentado).
- **CLI:** `_load_project_config()` — `config.settings.INSIM_CONFIG` del CWD si existe
  (ya aplica `settings_local.py` y env) > fallback env `LFS_ADMIN_PASS` > `None`
  (defaults del paquete). `get_loader()` la pasa al loader. El hack
  `sys.path.insert(0, os.getcwd())` se queda: los insims (p. ej. `RouteManager`)
  siguen importando `config.settings` legítimamente — P14 solo exige que el **core**
  no lo haga.
- **Exports:** `DEFAULT_CONFIG` y `build_config` añadidos a `lfs_insim/__init__.py`.
- **Tests:** `tests/test_config.py` (8: defaults/copia/fusión + cliente, app e ISI
  funcionando con el paquete `config` **bloqueado** en `sys.modules`) y
  `TestConfigDelLoader` en `test_loader.py` (3: propagación al cliente perezoso y a
  las apps; cliente inyectado manda). Suite **402/402**.
- **Smokes:** `lfs-insim list` + carga de `ai_control` dentro del proyecto (llegan
  `insim_name`/`prefix` del proyecto); cliente, app y CLI desde un CWD sin `config/`
  funcionan con defaults.
- CLAUDE.md actualizado (bullet de Config; el viejo mencionaba `OUT_CONFIG`, que ya
  no existe).
- Pendiente del usuario: validar en LFS P13 + P14 (ISI con nombre/prefijo/admin del
  proyecto; comandos respondiendo; re-probar `!test hcp`).

---

## S06 — 2026-07-02 — Fase 1 COMPLETADA; P11 (composición), P13 (transporte) y P21

**Qué se hizo (cuarto bloque, misma sesión) — fix de P21, adelantado de Fase 3:**
- Validando P13 en vivo, el usuario pisó P21 con `!test hcp` (`struct.error: pack
  expected 68 items (got 5)` en el log; el aislamiento de `_execute_handler` contuvo
  el fallo y el cliente siguió vivo — P13 se comportó bien).
- Fix en `_extract_values`: rama nueva para secuencias de formato fijo (`repeat(...)`
  devuelve una lista de fmts por hueco) que aplana y **rellena con defaults** hasta la
  longitud fija (sub-structs → instancia por defecto; primitivos → 0); en listas
  variables, los items tuple/list (p. ej. IPs `'4B'`) se expanden con `extend`.
- `TestEnviosRotos` → `TestGoldenSecuenciasFijas` (5 golden-bytes reales de REO/HCP/
  IPB); REO y HCP reincorporados al test estructural. Suite **391/391**.
- Queda que el usuario re-pruebe `!test hcp` en LFS.

**Qué se hizo (tercer bloque, misma sesión) — Fase 2, P13** (tras validar el usuario
P11 en LFS):
- **`encode_packet` puro extraído** de `send_packet` (commit propio): una sola ruta de
  serialización sin socket; los golden-send ejercitan ahora la función real (los tests
  de P21 esperan `InSimPacketError`, el envoltorio real).
- **`insim_transport.py` (nuevo): `InSimTransport`** — sockets TCP/UDP, hilos
  receptores, stop event y lock de envío **por instancia**; entrega paquetes crudos al
  callback `on_raw`. Framing TCP idéntico al caracterizado en Fase 1.
- **`InSimClient` posee su transporte** (inyectable); barrera pre-decode + decode en
  `_on_raw_bytes`; `send(packet) = encode_packet + transport.send`.
- **Eliminados:** `insim_packet_io.py`, el `send_packet` global y los sockets/force_set/
  oso_opts (muerto) de `insim_state`, que queda como azúcar: **cliente por defecto**
  (primero creado), fallback del mixin para helpers sin `client` (Command, CMDManager,
  RouteManager, MapRecorder).
- **Tests:** `test_packet_io.py` → `test_transport.py` (32, incluido el **criterio de
  aceptación de Fase 2: dos clientes coexistiendo** con recepción y envío
  independientes); registry adaptado a `_on_raw_bytes`; `test_insim_state` adelgazado;
  fixtures de handlers registran la app en un cliente real con `client.send` parcheado;
  `conftest` con `fake_lfs_factory`. Suite **388/388** (el recuento baja por tests de
  sockets globales que ya no aplican). CLAUDE.md actualizado (transporte y estado global).
- Pendiente del usuario: validar P13 en LFS (la ruta interna de envío/recepción cambió).

**Qué se hizo (segundo bloque, misma sesión) — Fase 2, P11:**
- **Decisión de idioma resuelta con el usuario:** inglés en el core (identificadores,
  docstrings, errores/log del código nuevo); español en docs/dev, tests, insims y
  comunicación. Registrada en `MODUS_OPERANDI.md` § 5.
- **P11 — inversión a composición** (los 3 archivos reescritos en inglés):
  - `insim_app.py`: `InSimApp(PacketSenderMixin)` — ya no hereda de `InSimClient`.
    Conserva: config, logger, `isi` (solo contribución de Flags), `outsim_opts`,
    dependencias, `get_insim`, hooks. Nuevo atributo `self.client` (lo asigna
    `register`). Eliminado `_resolve_dependencies` (código muerto, parte de P17).
  - `insim_client.py`: gana `register(app)` (idempotente, asigna `app.client`);
    `modules[]` → `apps`. Dispatch, agregación de flags ISI/OSO, keep-alive y
    lifecycle intactos.
  - `insim_loader.py`: **sin coup d'état** — cliente único perezoso (`loader.client`,
    propiedad) o inyectado (`InSimLoader(client=...)`); `load()` registra cada app en
    el cliente en orden de dependencias. Conservado: caché, checks de versión, tragado
    P20, envoltura de errores (mensajes ahora en inglés). Sin rollback (ya no hay trono).
  - `cli.py`: `cmd_run` arranca `loader.client.start()` en vez de la app.
- **Cambio de comportamiento deliberado:** el orden de dispatch pasa a ser el de
  dependencias (users_management procesa ANTES que ai_control). El orden antiguo
  (master-dependiente primero) era un bug latente: el consumidor leía estado no
  actualizado.
- **Tests adaptados:** `test_loader.py` (31: registro en cliente en orden de deps,
  cliente perezoso/inyectable, fallo no ensucia el cliente), `test_client_dispatch.py`
  (16: + TestRegister), `test_active_packet_registry.py` (`apps`). Suite **391/391**.
- **Smoke tests reales:** `test_insim`, `users_management` y `ai_control` cargan SIN
  cambios (la superficie de `InSimApp` se conservó); `ai_control` queda registrado tras
  `users_management`; `lfs-insim list` OK. CLAUDE.md actualizado (sección arquitectura).

**Qué se hizo (primer bloque) — cierre de Fase 1:**
- **Tests de packet_io** (`tests/test_packet_io.py`, 28 tests), sin LFS real:
  - `_tcp_listen_loop` con socket guionizado: reensamblado del flujo TCP (paquete
    completo, dos pegados, fragmentado en dos y byte a byte, pegado+fragmento del
    siguiente, ráfaga de 10); byte **Size=0** se descarta de uno en uno (resincronización
    byte a byte); cierre (recv vacío corta el bucle; **un resto incompleto en el buffer
    se pierde en silencio**); excepción en recv termina el hilo sin propagar (sin
    reconexión — P12); STOP_EVENT previo impide leer.
  - `_udp_listen_loop`: un datagrama = un paquete (sin reensamblado), datagrama vacío
    se ignora sin cortar, excepción termina el bucle.
  - `stop_all_threads`: cierra y resetea ambos sockets, traga errores de cierre y deja
    STOP_EVENT limpio.
  - `connect_tcp_lfs`/`connect_udp_lfs`: puerto cerrado/ocupado → `InSimConnectionError`.
  - **Integración real por loopback** (7 tests, con `fake_lfs`): conectar registra el
    socket y arranca el hilo receptor; trazas completas y fragmentadas llegan
    decodificadas al cliente; el FakeLFS registra lo que envía el cliente; la caída de
    LFS termina el hilo receptor (y NO se reconecta — P12); `stop_all_threads` lo
    termina y resetea; UDP end-to-end con datagrama real.
- **Fixture "LFS falso"** (`tests/conftest.py`, nuevo): clase `FakeLFS` — servidor TCP
  loopback que acepta una conexión, reproduce trazas de bytes hacia el cliente y
  registra lo recibido — expuesta como fixture `fake_lfs` para toda la suite.

**Decisiones tomadas:**
1. Los tests de packet_io congelan el comportamiento actual, incluidas las carencias
   ya registradas (P12 sin reconexión, pérdida silenciosa del resto del buffer al cerrar).
2. **Idioma de la API pública del core (pendiente desde S04): inglés en el core** —
   identificadores, docstrings y mensajes de error/log del código nuevo/refactorizado;
   español en docs/dev, tests, insims, commits y comunicación. Porqué: comunidad LFS
   internacional y eventual PyPI. El código viejo se traduce al tocarlo, sin pasadas
   masivas. Registrado en `MODUS_OPERANDI.md` § 5 y `PLAN.md` Fase 2.

**Estado del repo:** rama `refactor/estabilizacion`, suite **388/388 verde**.
**Fase 1: COMPLETADA. Fase 2: P11 (✅ validado en LFS por el usuario) y P13 hechos.**

**Próximo paso:** ver `ESTADO_ACTUAL.md` → P14 (config del paquete con defaults
internos; el core deja de importar `config.settings` del CWD). Pendiente del
usuario: validar P13 en LFS.

---

## S05 — 2026-07-02 — Fase 1: golden-bytes + tests de dispatch y loader (4/6 ítems)

**Qué se hizo (segundo bloque, misma sesión):**
- **Tests de dispatch de `InSimClient`** (`tests/test_client_dispatch.py`, 14 tests):
  orden de entrega master→módulos, aislamiento de errores por handler (uno que explota
  no corta a los demás), keep-alive reactivo (TINY.NONE se contesta con TINY.NONE),
  `_dispatch_lifecycle` (orden, aislamiento, módulos sin hook) y enrutado según
  `use_thread_pool` (inline vs executor.submit).
- **Tests del loader** (`tests/test_loader.py`, 29 tests) con InSims sintéticos generados
  en `tmp_path` (insim.json + app.py, sin sockets): carga simple, entry point `__init__.py`,
  caché, discover; **coup d'état caracterizado** (dependencia degradada a módulo, cadena de
  3 aplanada a `[n1, n0]`, master anterior limpiado); fallos (inexistente, sin entry point,
  sin clase InSimApp → error envuelto, rollback del trono tras fallo, versión insuficiente);
  **P20 caracterizado**: una dependencia rota se loguea y se SIGUE (el dependiente carga
  igualmente y `get_insim` devuelve None). Helpers `_parse_version`/`_check_version`
  parametrizados.
- **Hallazgo (ampliación de P20 en `DIAGNOSTICO.md`):** un InSim **sin `__init__.py`**
  (con entry point aparte) muere con error críptico — `spec_from_file_location(name, None)`
  devuelve None. Requisito no documentado; caracterizado en `test_sin_init_py_falla`.

**Qué se hizo (primer bloque):**
- Arranque según protocolo: rama al día, working tree limpio, suite base 233/233.
- **Golden-bytes de serialización** (`tests/test_golden_bytes_send.py`, 63 tests): fija los
  bytes exactos que produce la ruta real de encode de `send_packet()` (prepare →
  get_struct_string → `_extract_values` → struct.pack) para los **27 paquetes enviables**,
  con casos representativos (strings fijos/variables, truncado, padding a bloque de 4,
  sub-structs, listas variables, límite de 20 inputs en AIC...). Los bytes esperados se
  generaron con el código actual y se contrastaron contra la spec 0.8C5 (tamaños, Size,
  Type, offsets). Incluye test estructural parametrizado (Size=bytes/4, Type correcto).
- **Descubierto P21** (registrado en `DIAGNOSTICO.md`): el envío de **ISP_REO, ISP_HCP e
  ISP_IPB con bans está roto** — `_extract_values` no aplana listas de formato fijo
  (`repeat(...)`) ni tuplas anidadas y `struct.pack` recibe menos valores de los exigidos.
  Nadie los usa hoy, por eso no se había notado. Caracterizado con `pytest.raises`
  (`TestEnviosRotos`); se arreglará al unificar la serialización (P19, Fase 3).
- **Golden-bytes de decodificación** (`tests/test_golden_bytes_decode.py`, 20 tests): bytes
  construidos a mano según la spec → dataclass esperado para VER, TINY, SMALL, STA, NCN,
  CNL, MSO, BTC, BTT, NPL, MCI (2 CompCar), NLP (con padding a múltiplo de 4), CON, OBH,
  HLV, más el enrutado de `decode_packet` (vacío/tipo desconocido/Size incoherente → None)
  y un roundtrip encode→decode. Pasaron a la primera: el layout del código es fiel a la spec.
- Caracterizados de paso tres comportamientos actuales del decoder (documentados en el
  docstring del test): `.strip()` come espacios finales significativos (P19), las listas
  fijas se decodifican como `list` aunque el dataclass declare `tuple`, y los enums llegan
  como int crudo.

**Decisiones tomadas:**
1. Los golden-bytes **congelan el comportamiento actual** (incluso el discutible, como el
   string variable vacío de 0 bytes — P8 — o el strip del decoder): cambiarlo será un acto
   deliberado que actualice el test correspondiente, no un efecto colateral de un refactor.
2. P21 se caracteriza como excepción, no se arregla ahora (Fase 1 no cambia comportamiento);
   el arreglo va con P19 en Fase 3.

**Estado del repo:** rama `refactor/estabilizacion`, suite **359/359 verde**
(233 + 63 golden-send + 20 golden-decode + 14 dispatch + 29 loader).
Fase 1: **4/6 ítems completados**.

**Próximo paso:** ver `ESTADO_ACTUAL.md` → terminar Fase 1: packet_io con socket falso
(reensamblado TCP fragmentado/pegado, Size=0, cierre) + fixture "LFS falso".

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
