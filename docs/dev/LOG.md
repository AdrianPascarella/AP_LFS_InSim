# 📓 Diario — AP_LFS_InSim (lfs_insim)
<!-- Solo se añade, lo más nuevo arriba. Una entrada por sesión. -->

## S20 — 2026-10-13 — W6 decidida y aparcada; W10 (plugins) esbozada antes

**Inicio:** `session_start_check` PASS (rama, identidad, pull, plantilla v3). Documentos y realidad coinciden
(último commit `ec5ccee`, árbol limpio). 1 acción del usuario pendiente, opcional (U11).

**W6, decidida con el usuario** (las dos recomendadas por el agente): la cámara libre vive **dentro de
streamer-project** (`tools/`, instala `lfs-insim` desde PyPI; *descartado* un repositorio propio: un proyecto
más con su protocolo, para un único usuario de la cámara); primera versión **repetición + plano guionizado**
(`IS_RIP`, `IS_SCC`, `IS_CPP`; *descartados* solo seguir en directo, que no cubre lo que pide streamer-project,
y todo desde el principio, por P4). Contexto: su W9 en streamer-project; en `C:\LFS\data\mpr` no hay
repeticiones (U36 de allí). Al ir a anotarlo, el usuario: «Pero aún no!!» y «Antes quiero que miremos otra
cosa». No se había cambiado nada.

**Plugins (W10), idea del usuario:** «Sigue sin cuadrarme la idea de que lo de Roster venga ya directo
incrustado sin más… sería mejor que sea un insim que ya trae la biblioteca y que se pueda cargar sin más
todas sus utilidades (como ya hacía el proyecto en su versión antigua)». Análisis del agente, con el código:
- `Roster` ya era opcional, pero **los comandos crean el suyo a escondidas** (`InSim._make_roster`): con un
  `Roster` propio hay dos y se pide todo dos veces → **P10**. Los flags del `IS_ISI` solo se fijan en
  `InSim(flags=)`, así que un módulo no puede declarar lo que necesita. Los `on_connect` arrancan a la vez.
- Del proyecto anterior (`insim_app.py`, `insim_loader.py`, `users_management`) se rescata la idea (módulos
  que declaran sus flags y comparten estado) y **se descarta el mecanismo** (manifiestos, carga por carpetas,
  `get_insim("nombre")` sin tipo, versiones entre módulos): fue parte de P4.
- El usuario: «Me encaja… que se pudiese utilizar Roster o AIControl o FreeCam de forma completamente
  independiente o que se puedan combinar en un solo insim compartiendo todo el estado… piensa en otras
  cosas». El agente añadió: peticiones iguales compartidas, `ready()`, flags e intervalo por plugin, opciones
  en `use()`, choques de comandos y de `ClickID`, `on_close`, arranque solo, kit de pruebas público.
- Preguntado si su idea era correcta, el agente: sí (patrón de los *Cogs* de discord.py, *blueprints* de
  Flask), con dos matices: la dependencia de `Roster` existe (los comandos la necesitan; se hace explícita) y
  del proyecto antiguo vale la idea, no el cargador.
- **Discrepancia resuelta:** el usuario propuso que los comandos vinieran dentro del plugin `Roster`. El
  agente recomendó **un plugin `Commands` propio que hace `use(Roster)`** (el registrador o la cámara quieren
  `Roster` sin comandos; `Roster` seguiría siendo solo «quién es quién»), sin atajo en `InSim`. Cambio
  incompatible (`@insim.on_command` desde 0.4.0), aceptable en 0.x. El usuario preguntó si eso duplicaría
  `Roster`: no, `use()` da una instancia por tipo; y crear uno directamente con otro ya en uso dará error.
  El usuario: «Sí, anótalo todo como W10».
- **Abierto:** si LFS acepta varios programas InSim en el mismo puerto (el agente cree que sí, sin comprobar)
  → W10.0.

**Decisiones:** W10 antes de W6, porque FreeCam será el primer plugin de fuera. Diseño en `API_DESIGN.md`
(«Plugins»), tareas W10.0–W10.10 en `PLAN.md`, P10 en `DIAGNOSIS.md`.
**Verificación:** sin cambios de código; solo documentación de trabajo. Control de cierre al final.

**Pregunta del usuario: ¿un plugin y un InSim son lo mismo?** El agente: en la jerga de LFS sí («un InSim» es
un programa); en la biblioteca, no: `InSim` es la conexión (la tubería) y un plugin es la lógica que se
engancha a ella; un programa = una conexión + uno o varios plugins (como `InSimClient` e `InSimApp` antes).

**W10.1 hecha** (el usuario: «Sigue con W10.0 y W10.1»; W10.0 espera a que diga si puede abrirse LFS).
- **Rojo primero:** `tests/test_plugins.py` (8 tests) falló entero antes del código; P10 reproducido: con
  `Roster(insim)` y un comando, `TINY_ISM` pedido dos veces.
- `insim.use(Tipo, **opciones)` (`_plugins.py`): una instancia por tipo y por `InSim`; sin opciones u otras
  iguales, la misma; otras distintas → `ValueError`. Los comandos usan `use(Roster)`.
- **Decisión del agente al escribirlo:** el primer intento llamaba a `insim._plugins` desde `Roster`, y el test
  existente `test_roster_uses_only_the_public_api` (S18) se puso en rojo con razón: `Roster` debe escribirse
  solo con la API pública, como un plugin de fuera. No se tocó el test; se añadió **`lfs_insim.Plugin`**, clase
  base pública cuyo `__init__` registra el plugin (crear un segundo directamente → `ValueError`). *Descartado:*
  `insim.adopt()` público. `use()` sigue aceptando cualquier clase. API pública nueva: `Plugin` y `use()`.
- Mutación «`Plugin` sin registrar»: 3 tests en rojo; restaurada. CHANGELOG «Unreleased». La guía sigue con
  `Roster(insim)`, que funciona: se reescribe en W10.8.
- **Verificación:** `verify` PASS (555 tests). Aviso: `_connection.py` **504 líneas** (límite 500): lo bajará
  W10.2, al sacar los comandos de `InSim`.

**Duda del usuario sobre herencia** (AIControl → AITraffic, AIDrift, combinados con `Roster`): el agente explicó
que heredar da dos copias de AIControl que se pisan los coches; para combinar, componer (AIControl como
servicio con `use()`). **Y sobre scripts como los ejemplos:** sin tocarlos se combinan con `run(a.insim,
b.insim)` (conexiones separadas, sin estado compartido); para compartir, el script dentro de una función
(un plugin puede ser una función). El usuario pidió el plan formal y lo aceptó: «Acepto el plan, procede».
Orden y criterios en `PLAN.md` (W10.11 nueva).

**W10.11 hecha:** `use()` acepta funciones (`Callable[..., T]`). Rojo: los dos tests nuevos pasaban en
ejecución pero mypy los rechazaba (`expected "type[Roster]"`); con la firma nueva, verdes. `verify` PASS.

**W10.2 hecha:** `Commands` es un plugin público (`from lfs_insim import Commands`;
`insim.use(Commands, prefix=None, guest_commands="local")`, que hace `use(Roster)` y se engancha a `IS_MSO`).
`InSim` pierde `on_command`, `command_group`, `guest_commands` y `_make_roster` (`_connection.py` 504 → 454).
- **Tests cambiados, por el cambio de API (no para que pasen):** los de comandos (`test_commands*.py`,
  `test_command_prefixes.py`, `test_guest.py`) migrados con un script del scratchpad: `commands =
  insim.use(Commands)` y `commands.on_command`; `guest_commands` pasa a `use(Commands, ...)`. Rojo antes del
  código (no podían importar `Commands`), más un test nuevo: `InSim` ya no tiene `on_command`.
- **Un test se reordenó con motivo:** la migración puso `use(Commands)` antes de `Roster(insim)` en el test de
  P10, y el `Roster` directo pasó a ser el segundo (el error diseñado). Se devolvió al orden original. **Trampa
  para usuarios:** `use(Commands)` y después `Roster(insim)` da ese error; la guía enseña `insim.use(Roster)`.
- Ejemplos, README, `getting-started.md`, `insim.md` y `roster-and-text.md` con la forma nueva; CHANGELOG
  «Breaking». `verify` PASS (558 tests), sin avisos de tamaño.

**W10.3 hecha:** dos `request()`/`request_all()` iguales a la vez → un solo `IS_TINY` (`Requests.shared`: una
tarea propia, `asyncio.shield`, cada `request_all` recibe su lista). Rojo primero: 3 de 4 tests nuevos.
- **Defecto de diseño encontrado por un test existente** (`test_starting_or_ending_multiplayer_asks_for_the_
  state_again`, en rojo con la primera versión): al llegar `IS_ISM`, `Roster` vuelve a preguntar, y se unía a la
  petición de `TINY_ISM` enviada antes del aviso → respuesta vieja. **Hipótesis comprobada** con una mutación:
  sin la regla nueva, ese test y uno nuevo fallan. **Regla:** solo se comparte si no ha llegado ningún paquete
  de LFS desde que se envió (contador en `Requests.deliver`). El test no se tocó.
- `verify` PASS (563 tests).

**W10.4 hecha:** `await roster.ready()` (un `asyncio.Event`): se pone al terminar el último `_refresh` sin
error de conexión, y se borra al empezar un `_refresh`, al desconectar y, de forma síncrona en `_before`, al
llegar `IS_ISM` sin `ReqI` o `TINY_MPE`. Rojo primero: 3 tests.
- **Un test nuevo mío estaba mal y se corrigió:** suponía la foto lista nada más llegar las conexiones, pero
  en un solo jugador `TINY_ISM` no tiene respuesta y se espera 1 s (documentado en `ready()`).
- **Dos mutaciones sobrevivieron al principio** (sin el borrado síncrono, sin el borrado al desconectar):
  los tests registraban siempre `Roster` antes que el plugin, y así el `_refresh` borra antes. Esos borrados
  importan cuando alguien se registra antes que `Roster`: dos tests nuevos con ese orden; con ellos, cada
  mutación da rojo.
- Guía (`roster-and-text.md`), CHANGELOG. `verify` PASS. `test_roster.py` tarda ~11 s (las esperas de 1 s).

**W10.5 hecha:** `insim.need(flags=..., interval_ms=...)` (nombre elegido por el agente: lo que un plugin
necesita de LFS; se puede cambiar antes de publicar). Suma flags al `IS_ISI`, guarda el intervalo más corto
distinto de 0, `ValueError` si es negativo, y avisa si la conexión ya está en marcha (cuenta desde la
siguiente, porque se reenvía `self._isi` al reconectar). Rojo primero: `tests/test_needs.py` (5 tests).
`verify` PASS (573 tests). La guía de plugins va en W10.8.

**W10.6 hecha:** dos plugins con el mismo comando y prefijo → `ValueError` que lo nombra (ya pasaba, porque
`Commands` es uno compartido: test de caracterización, verde desde el principio). `insim.reserve_click_ids(n)`
→ `range` consecutivo de los 240 `ClickID` (0–239, InSim.txt «BUTTONS»); al pasarse, `ValueError`. Rojo
primero: 3 tests. `verify` PASS (577 tests). **Hubo un fallo mío al documentar W10.5:** un script de ediciones
se cortó a medias y el commit salió igual (iba en otra línea, no encadenado); se completó en dos commits más.
Desde W10.6, el script va encadenado al commit con `&&`.

**W10.7 hecha:** `@insim.on_close`, al final de `_close`: después de `on_disconnect` y de cancelar los
manejadores, una sola vez, también sin haber conectado nunca y al cancelar la tarea (lo que hace Ctrl+C en
`run()`). Rojo primero: 2 de 4 tests (los otros dos, de caracterización: el de cancelación, escrito después
de implementar, y el del log). **El nombre del plugin en el log ya salía**: `Handlers._failed` usa el
`__qualname__` (`camera.<locals>.broken`); se fija con un test, sin código nuevo. `verify` PASS (581 tests).

**W10.0 hecha, en el LFS real** (el usuario: «Sí, abre LFS y haz W10.0»). LFS **ya estaba abierto** (lo abrió el
usuario después de la comprobación del inicio), como invitado en un servidor público («Always Ride Two», 46
conexiones): no se abrió otro ni se cerrará al final (§ Configuración: solo se cierra el que abre el agente).
InSim se activó con `lfs_screen.ps1` (`/insim=29999`; LFS se puso delante sin problema). Sonda de solo lectura
en el scratchpad (`probe_multi.py`), **sin enviar nada al chat**:
- Dos programas a la vez: los dos conectan y reciben **exactamente lo mismo** (47 `IS_NCN`, 8 `IS_MSO`, 20
  `IS_CSC`, 17 `IS_UCO`…, mismas respuestas a `TINY_VER`/`NCN`/`ISM`).
- Diez a la vez: **aceptó 8** y cerró el 9.º y el 10.º antes de contestar al `IS_ISI`.
- **P11:** el aviso de la biblioteca culpaba a la contraseña; ahora nombra también el límite. Rojo primero.
- `verify` PASS (581 tests). InSim queda escuchando en el 29999 del LFS del usuario.

**W10.9 hecha** (el usuario: «te doy mi sí»; se hizo antes que W10.8 para que la guía pueda contar cómo probar
un plugin). `tests/fake_lfs.py` → `src/lfs_insim/testing.py` con `git mv` (se conserva el historial; es un
traslado, no un borrado). `assert` → `RuntimeError`; docstrings para usuarios. Rojo primero: los tests, con el
import nuevo, no se podían recoger. Guía nueva `docs/testing.md`, cuyo ejemplo ejecuta `tests/test_testing.py`.
- **Dos errores del primer ejemplo, vistos al releerlo antes de probarlo:** esperaba `IS_MST` (la respuesta a
  este ordenador es `IS_MSL`) y usaba `async def test_...` (necesita pytest-asyncio, que no es dependencia).
- **Cicatriz nueva (§13):** `ruff format docs` formateó el Python de cuatro `.md` (`API_DESIGN.md`,
  `insim.md`, `units.md`, `roster-and-text.md`); restaurados desde git, porque sus únicos cambios eran de ruff.
- `verify` PASS (585 tests).

**W10.8 hecha:** guía `docs/plugins.md` (escribir un plugin, combinarlos, compartir, `ready()`, `need()`, botones,
`on_close`, opciones y clases, combinar o heredar con el ejemplo de IA del usuario, hasta 8 conexiones,
pruebas). `hello`, `who` y `buttons` pasan a ser funciones-plugin con `if __name__ == "__main__"`; `buttons` usa
`reserve_click_ids(2)` y borra solo sus botones (`BFN.DEL_BTN` con su rango, no `BFN.CLEAR`); `gauge` se queda
como script (mezcla OutGauge, que no es plugin de InSim). Nuevo `examples/together.py` (los tres en una
conexión; su test comprueba un solo `TINY_NCN`). README y `getting-started.md` con el primer programa como
plugin.
- **Tests cambiados, con motivo:** `test_examples.py`, por la forma nueva de los ejemplos (crean el `InSim` y
  hacen `use()`), y `test_docs.py`: ejecutaba todos los `import` de los bloques, y `plugins.md` importa módulos
  del lector (`hello`, `laps`); ahora solo los de `lfs_insim` y de la biblioteca estándar, que es lo que
  comprobaba (nombres de la biblioteca mal escritos).
- `DEL_BTN` no se ha visto en el LFS real (la pantalla es punto ciego; LFS está en un servidor público del
  usuario): va en U12, opcional. `verify` PASS (588 tests). **Pedido al usuario: U12.**

**Cierre de S20:** W10 hecha salvo W10.10 (publicar 0.6.0: pide permiso expreso; el agente recomienda U12
antes, por si cambian nombres). CI `verify` en verde en todos los commits de la sesión. 2 acciones del
usuario pendientes, ninguna bloquea: U12 y U11. LFS del usuario sigue abierto con InSim en el 29999 (no lo
abrió el agente).

## S19 — 2026-10-13 — W9: comandos como invitado en un servidor ajeno

**Inicio:** `session_start_check` PASS (rama, identidad, pull, plantilla v3). Documentos y realidad coinciden
(último commit `d0d97e5`, árbol limpio). 0 acciones del usuario pendientes. El usuario: «Sigamos tu
recomendación» → primero la prueba en real (W9.0) y después el diseño.

**W9.0, prueba en real como invitado** (LFS abierto por el usuario, dentro de su servidor «testing»; sonda en el
scratchpad, `probe_guest.py`; sin tocar `cfg.txt` ni cerrar LFS):
- `TINY_ISM` → `IS_ISM(Host=0, HName='testing')`. `TINY_NCN` sí responde: UCID 0 = anfitrión (`Flags=4`, remoto,
  `Admin=1`), UCID 1 = este ordenador (`AdrianPascarella`, `Flags=0`, `Admin=1`: el usuario es admin de ese
  servidor). `TINY_NCI`: sin respuesta por InSim.
- `hola`, `!who`, `.who` llegan los tres como `MSO.USER` (UserType 1), UCID 1, visibles para todos: el prefijo
  de `IS_ISI` no cuenta como invitado. `/o test` → `MSO.O` (3), `TextStart=0`, `Msg='test'`, UCID 1.
- `IS_MSL` vuelve como `IS_MSO` de sistema (UCID 0, UserType 0) y solo lo ve el usuario (confirmado por él).
  `IS_MTC` y `TINY_NCI`: el usuario vio en pantalla «IS_MTC - only for multiplayer hosts» y «TINY_NCI - only
  for multiplayer hosts» (solo él); por InSim no llega nada.
- Confirmado el problema: como invitado, cualquiera del servidor ejecutaba nuestros comandos, y `admin=True`
  dejaba pasar a los admins del servidor ajeno.

**Decisiones (usuario, S19; las cuatro recomendadas por el agente; detalle y descartes en `API_DESIGN.md`):**
como invitado, solo este ordenador usa los comandos (`InSim(guest_commands="everyone")` abre, `allow=` sigue
filtrando); `admin=True` = solo este ordenador; `reply()` a este ordenador por `IS_MSL` y a otro por el chat
público; `/o` cuenta como comando con el mismo prefijo.

**Hecho (W9.1–W9.5):**
- `Roster.guest` (de `IS_ISM.Host`; `TINY_MPE` lo apaga) y `Roster.local` (el UCID del `IS_NCN` sin marca de
  remoto; una conexión creada solo por su `IS_NPL` no cuenta). `_refresh` pide `TINY_ISM` a la vez que
  `NCN`/`NPL`; sin respuesta en 1 s → no es multijugador. Una respuesta a `TINY_ISM` (`ReqI` ≠ 0) no vuelve a
  pedir el estado (si no, bucle).
- Comandos: crean siempre su `Roster` (antes solo con `admin=True`); `Command.local`; como invitado, lo que no
  es local se ignora sin contestar salvo `guest_commands="everyone"`; `reply` elige `IS_MSL` / chat público /
  `IS_MTC` según invitado y local. `GuestCommands` en `_commands.py`; valor desconocido → `ValueError`.
- **Defecto encontrado y arreglado:** si la conexión se cerraba mientras `Roster` pedía `NCN`/`NPL`, el
  `ConnectionError` se registraba como error del manejador `on_connect`. Salió al hacer que los comandos tengan
  siempre `Roster` (`test_what_is_not_a_known_command_is_left_alone` en rojo por el log). Arreglo en su origen
  (`contextlib.suppress(ConnectionError)`: la siguiente conexión vuelve a pedir), no en el test. Test nuevo
  `test_closing_while_asking_is_not_an_error`.
- **Rojo primero:** `tests/test_guest.py` (12 tests) falló entero antes del código. Mutaciones, todas en rojo y
  restauradas: sin el `suppress`; sin la guarda de `ReqI`; sin la política de invitado; `admin` como invitado
  devolviendo `True`.
- Guía (`docs/insim.md` «As a guest», `docs/roster-and-text.md`), CHANGELOG «Unreleased», `API_DESIGN.md`.
- **Prueba en real (W9.5)**, con el permiso del usuario («procede»), teclea el agente con `lfs_screen.ps1`
  (`!` como `{!}` en SendKeys): `!who` → respuesta por `IS_MSL` («guest=True local=True: host,
  AdrianPascarella»), sin aviso de `IS_MTC`; `/o !who` → igual y sin salir en el chat; `!kick bob` (admin) →
  «(would kick bob)»; `!who ?` → la ayuda. Visto en las capturas y en el log. Sin probar: el comando de otra
  persona (no había nadie) → U11, opcional.
**Verificación:** `verify` PASS (542 tests). `_connection.py` 485 líneas (aviso en 500), `_commands.py` 328.
**Pedido al usuario:** U11 (opcional).

**W9.7, pedida por el usuario tras el cierre** («¿se podría que un comando o grupo inicie por un prefijo en
concreto?»). El agente explicó que no (un prefijo por `InSim`) y recomendó dejarlo en «Ideas»; el usuario: «Hazlo
como W9.7 antes de publicar». Diseño del agente (detalle y descartes en `API_DESIGN.md`): `prefix=` en
`on_command` y `command_group`, un carácter que no sea letra, dígito ni espacio; nombres únicos por prefijo;
`InSim()` sin prefijo vale si cada comando trae el suyo. Internamente, `_by_name`/`_groups` por prefijo y luego
por nombre; `_Entry` y `_Group` guardan su prefijo, así que ayuda, uso y negativas muestran el suyo.
**Rojo primero:** `tests/test_command_prefixes.py` (5 tests) falló entero antes del código. Un test estaba mal
(esperaba por `IS_MTC` la respuesta a la UCID 0, que va por `IS_MSL`); se cambió a otra UCID, y lo que
comprueba sigue igual. Sin prueba en real: es solo comparar texto, cubierto por los tests.
**Verificación:** `verify` PASS (547 tests). `_connection.py` va por **496 líneas** (aviso en 500).
Guía, CHANGELOG, `API_DESIGN.md`. **Trampa repetida:** un heredoc largo de Python se rompió en la terminal
(§13); se hizo con Edit.

**Publicado 0.5.0 (W9.6)** (el usuario: «Sí, publica 0.5.0»). Versión y CHANGELOG en `dev` (`6da7e6d`); `verify`
PASS; wheel y sdist construidos en un venv de herramientas en `%LOCALAPPDATA%\Temp\lfs_rel_050` (el scratchpad de
la sesión ya no estaba), `twine check` PASSED, instalado en un venv limpio. CI `verify` en verde (run 38439273928);
avance rápido de `dev` a `main` (`6da7e6d`); release `v0.5.0` (pre-release, notas del CHANGELOG) con `GH_TOKEN` de
`AdrianPascarella`; entorno `pypi` aprobado por el agente (§15); `publish` en verde (run 38439502735);
`pip install lfs-insim==0.5.0` en un venv limpio: 0.5.0, `prefix=`, `guest_commands`, `Roster.local` OK.
**Cierre de S19:** W9 cerrada y publicada; siguiente, W6. 1 acción opcional pendiente (U11).

## S18 — 2026-10-13 — W8.4: `insim.watch()` público

**Inicio:** `session_start_check` PASS (rama, identidad, pull, plantilla v3); `verify` PASS antes de tocar nada.
Documentos y realidad coinciden (último commit `050f5b6`, árbol limpio). 0 acciones del usuario pendientes.

**Decisión (usuario, S18; la recomendada por el agente):** W8.4 es un método aparte,
`insim.watch(before=f, after=g)`, y no un `order=` en `on`. **Por qué:** `order=` habría tocado `on`, `on.IS_X`,
los subtipos y sus sobrecargas de tipos, y habría dejado dos clases de manejador con reglas distintas (los
«before» solo `def`). Un observador de todos los paquetes es justo lo que necesita un estado como `Roster`.
Descartada también la opción de dejarla privada hasta W6.

**Hecho:** `watch()` en `_connection.py` sustituye a `_watch()`: `before` y/o `after` (al menos uno; si no,
`TypeError`), solo `def` (`async def` da `TypeError`: tienen que acabar antes de que pase nada más). Mismo orden
que antes: `before` → respuestas de `request()` → manejadores → primer paso de los `async` → `after`. Los
errores siguen `errors="log"/"raise"`. `Roster` usa ahora solo API pública: `watch()`, y el `_refresh` de
`IS_ISM` y `TINY.MPE` pasa a ser un manejador normal (`insim.on(IS_ISM)`, `insim.on(IS_TINY, TINY.MPE)`) en
vez de `insim._handlers.call` desde `_before` (ambos lanzan una tarea; el orden visto por los manejadores no
cambia). `InSimPacket` se exporta en `lfs_insim.packets` (por el generador) para anotar los observadores;
`test_packets.py` lo añade a las bases excluidas. Guía: «Your own state» en `docs/roster-and-text.md`;
CHANGELOG «Unreleased»; `API_DESIGN.md` al día.
**Rojo primero:** `tests/test_watch.py` (orden, solo uno de los dos, `TypeError`, `errors="raise"` y que
`state.py` no use nada privado de `insim`) falló entero antes del código; el último test se comprobó contra el
`state.py` anterior (encuentra `insim._watch` y `_insim._handlers`).
**Verificación:** `verify` PASS, 520 tests. `_connection.py` va por 479 líneas (aviso en 500).
**Visto de paso:** `HAND_WRITTEN` en `scripts/generate_packets.py` no lo usa nadie (código muerto); no se tocó.

**W8.5 hecha** (el usuario: «Sí, sigue con W8.5»). **W8 cerrada.**
- **P21 (`IS_REO`, `IS_HCP`, `IS_IPB`):** funcionaban; faltaba un test que los nombrara. `tests/test_fixed_lists.py`:
  bytes exactos según InSim.txt, ida y vuelta, envío al LFS falso y recepción desde él (los dos son «both
  ways»). Pasaron a la primera (el código ya era correcto), así que se mutó el codec `IPv4` (bytes al revés):
  2 tests en rojo; restaurado.
- **Encontrado:** una lista corta (`IS_REO(PLID=[5, 2, 9])`) da `PacketError: expected 48 items, got 3`. Claro
  pero incómodo; rellenar con ceros cambia la API → **U9** para el usuario, no se tocó.
- **P22 y P24 ya estaban fijados**, demostrado con mutaciones: limpiar el `Roster` *después* de pedir el estado
  pone en rojo 5 tests de `test_roster.py`; reiniciar siempre la espera (`if True:` en vez de
  `if self._accepted:`) pone en rojo `test_lfs_closing_at_once_is_reported_and_slows_down`. No se duplicaron;
  se añadió a cada test un comentario con la lección que fija.
- Sin cambios para el usuario: ni guía ni CHANGELOG.
**Verificación:** `verify` PASS (525 tests); CI `verify` en verde en `dev` (run 38424412941).
**Pedido al usuario:** U8 (permiso para probar en LFS real antes de 0.4.0) y U9 (decidir las listas cortas).

**U9 cerrada** (el usuario: «Sigamos tu recomendación»). Al aplicarla, el agente acotó la recomendación: solo
se rellenan con ceros las listas donde el cero significa «nada» (`IS_REO.PLID`, `IS_HCP.Info`); `Tyres` no (0 es
el neumático R1). `ZERO_FILLED` en `spec_overrides.py`; `Array(..., fill=)`; el generador se para si la entrada no
es una lista fija (comprobado). Pasarse de largo sigue siendo error. Tests en rojo antes; CHANGELOG.

**U8: prueba en LFS real** (el usuario: «Probemoslo, te doy permiso»). LFS ya estaba abierto por el usuario; no
se tocó `cfg.txt` ni se cerró LFS. Script en el scratchpad (`live_w8.py`, `probe.py`); comandos tecleados con
`lfs_screen.ps1` desde PowerShell.
- **Primera pasada: el usuario estaba como invitado en un servidor online** («testing»). Los comandos llegaron
  (UCID 1) con los argumentos convertidos, pero cada respuesta salió como «IS_MTC - only for multiplayer
  hosts»: desde un invitado LFS no acepta `IS_MTC`. Limitación de LFS, no de la biblioteca. `!aic` (admin)
  corrió para UCID 1: LFS lo marcaba admin de ese servidor (preguntado al usuario).
- **Segunda pasada, en la pantalla de inicio:** `!speed abc` → uso; `!speed ?` → uso y docstring; `!speed 80 Bob`
  → «Limit for Bob: 80 km/h»; `!aic` → la lista; `!aic start 3`; `!secret` → «You may not use !secret». Todo
  visto en la captura.
- **P9 encontrado** (1 error de orden en ~5400 `IS_MCI`): dos paquetes en la misma lectura TCP adelantaban el
  `before` del segundo al `after` del primero; con `Roster`, un UCID reutilizado en la misma lectura perdía la
  conexión nueva. Dos tests en rojo; arreglo: `await asyncio.sleep(0)` tras cada paquete en `_read`.
  `DIAGNOSIS.md` P9. Commit `d796189`.
- **Unidades (W8.3), con el usuario conduciendo en un jugador:** `speed_kmh` frente a la velocidad derivada de
  `x_m`/`y_m` entre `IS_MCI` seguidos: mediana 1,002 (936 muestras > 20 km/h, máx. 212 km/h). Escalas de
  velocidad y posición confirmadas. `watch()`: 0 errores de orden en 2399 `IS_MCI`.
- Sin probar en real: `IS_REO` / `IS_HCP` enviados (bytes cubiertos por tests). OutGauge no se comparó (habría
  que tocar `cfg.txt`); la derivada de posiciones es una comprobación independiente.
**Verificación:** `verify` PASS.

**U8 cerrada** (el usuario: «U8 cerrada, publica 0.4.0»).
**Publicado 0.4.0:** versión y CHANGELOG (con P9) en `dev`; `verify` PASS; wheel y sdist construidos en un venv de
herramientas del scratchpad, `twine check` PASSED, instalado en un venv limpio desde `site-packages`. CI `verify`
en verde (run 38433009468); avance rápido de `dev` a `main` (`cb118e6`); release `v0.4.0` (pre-release, notas del
CHANGELOG). `gh release create` con la cuenta activa (`Veloik-adrian`) falló por el permiso `workflow`; se hizo
con `GH_TOKEN` de `AdrianPascarella`, como dice la receta. Entorno `pypi` aprobado por el agente (§15); `publish`
en verde (run 38433230722); `pip install lfs-insim==0.4.0` en un venv limpio: 0.4.0, `watch`, `IS_REO` corto OK.

**Pregunta del usuario: comandos como invitado en un servidor ajeno** (prefijo distinto del del anfitrión,
visibles en el chat, solo para usuarios autorizados). Opinión del agente:
- **Ya funciona a medias:** los comandos se reconocen por el texto del `IS_MSO`, no por el prefijo de `IS_ISI` ni
  por `UserType`; en la primera pasada de U8, como invitado, `!speed 80 Bob` llegó y se ejecutó (UCID 1).
- **Falla:** (1) las respuestas: `reply()` usa `IS_MTC`, que LFS rechaza a un invitado; (2) `admin=True` mira si
  LFS marca al usuario como admin *del servidor*, que en un servidor ajeno no es «nosotros»; (3) como invitado
  llega el chat de todos: sin restricción, cualquiera que teclee el prefijo ejecuta el comando.
- **Propuesta (W9):** la biblioteca sabe si es anfitrión o invitado (`IS_ISM`/`TINY_ISM`, `Host`) y quién es «este
  ordenador» (`Command.local`); como invitado, por defecto solo responde a los comandos locales (seguro por
  defecto) y `allow=` abre a otros (p. ej. por nombre de usuario); `reply()` como invitado va por `IS_MSL` (solo lo
  ves tú) y no puede contestar en privado a otros (`say()` público, o aviso en el log). El prefijo ya puede ser
  cualquiera (`prefix="."`); separar el de `IS_ISI` del de los comandos solo haría falta para comandos visibles
  siendo anfitrión. **Hay que probarlo antes en real** (cómo se ve nuestra propia conexión como invitado, si
  `TINY_NCN` responde, qué UCID y flags llegan). Abierta U10 para decidir.
**U10 cerrada** (el usuario: «para la primera aplicación necesitaremos esto [...] continuaremos mejorando la
biblioteca [...] en la siguiente sesión»): W9 esbozada en `PLAN.md`, antes de W6; se detalla al empezar S19.
**Cierre de S18:** W8 cerrada, 0.4.0 en PyPI, P9 resuelto, 0 acciones pendientes.

## S17 — 2026-10-13 — Revisión de W7.7 y W7.8: solo los subtipos que LFS envía

**Inicio:** `session_start_check` PASS (rama, identidad, pull, plantilla v3); `verify` PASS (477) antes de tocar nada.
El usuario preguntó qué opinaba el agente de lo último (W7.7).

**Revisión de W7.7 (agente):** bien hecha, pero con dos fallos. (1) Aceptaba subtipos que LFS nunca envía:
`@insim.on.IS_TINY(TINY.NCN)` no daba error y el manejador no se llamaba nunca, el mismo fallo que W7.2
quitó para los paquetes. La propia guía y el test usaban `SMALL.STP`, que es una *instruction*. InSim.txt marca
la dirección de cada `TINY_` / `SMALL_`. (2) Había dos fuentes: `SUBTYPE_ENUMS` en el generador y `SUBTYPES`
a mano en `_events.py` (y `SubReceiver` recibía el enum sin usarlo). El agente propuso W7.8 antes de W8
y antes de publicar W7.7; el usuario: «Haz W7.8 primero».

**Hecho (W7.8):** `subtype_directions()` en `spec_directions.py` lee la marca de cada subtipo:
`info`, `report` (SMALL_VTA), `ping reply` → LFS; `both ways` y `keep alive` (TINY_NONE) → los dos;
`instruction`, `info request`, `ping request` → el programa; `SMALL_NONE` («not used») se salta; una marca
desconocida para la generación. El generador escribe `src/lfs_insim/_subtypes.py`: `ReceivedTINY` /
`ReceivedSMALL` (`Literal` con los miembros que envía LFS, para mypy) y `SUBTYPES` (enum y conjunto, para
ejecutar). `_shortcuts.py` declara `IS_TINY: SubReceiver[IS_TINY, ReceivedTINY]`; las sobrecargas de
`Receive.__call__` usan los `Literal`; `Receive._register` hace la comprobación y `Subtyped` lo llama sin
`# type: ignore`. `TypeError` claro: «LFS never sends IS_TINY with TINY.NCN: … LFS sends TINY.NONE, …».
`docs/packets.md` gana la sección «Subtypes» (generada); guía, CHANGELOG «Unreleased» y tests pasan a
`SMALL.VTA`. **Rojo primero:** `tests/test_subtypes.py` con los casos nuevos (ejecución, mypy y contraste con
la especificación) falló antes del código.
**Lo que cuesta:** mypy pide el miembro literal; una variable de tipo `TINY` (no `Final`) pasada a
`on.IS_TINY(...)` da error de tipos aunque valga. Aceptable: en un decorador casi siempre se escribe el miembro.
**Verificación:** `verify` PASS, 479 tests. Sin publicar (sigue en «Unreleased» con W7.7).
**Tropiezos:** (1) el agente metió por error un `git stash` en un comando; se deshizo al momento con
`git stash pop`, sin pérdida. (2) Otra vez barras invertidas en un script por Bash (§13): se pasó a Edit.

**W8 abierta** (el usuario: «Abre W8»). El agente propuso dividirla en W8.0–W8.5 (`PLAN.md`) y el usuario
eligió las cuatro recomendaciones: **botones (A4) fuera de W8**, en una fase propia con la aplicación
delante (diseñarlos a ciegas produjo el `map_ui.py` de 3.000 líneas); **argumentos de comando por
anotaciones de tipo** (no una lista en el decorador, que repite la firma); **permisos con `admin=True` y
`allow=función`** (no una lista de usuarios ni roles); **0.3.0 tras W8.1** (versiones pequeñas, no una grande
al final). W8.0 va primero: `_codec.py` ya pasa del aviso de tamaño y `_connection.py` va a crecer.

**W8.0 hecha (estructura, sin cambiar comportamiento; §5):** `packets/_codec.py` (525) se partió en `_codec.py`
(codecs de campo, 425) y `_structure.py` nuevo (`Structure`, `OptionalParts`, `InSimPacket`, `register`,
`unpack_insim`, `factory`; 108). **Movimiento demostrado:** un script comprobó que el texto de ambas partes es
idéntico al original (solo cambian docstring e importaciones). `Nested` anota `Structure` con un import bajo
`TYPE_CHECKING` (si no, el import sería circular). El generador importa las bases y `register` de `_structure`;
los generados solo cambian sus importaciones. **Red en rojo:** quitar el relleno de `InSimPacket.pack` hizo
fallar 2 tests; restaurado. `factory()` no lo usa el código, solo `test_codec.py`: se movió, no se borró
(borrarlo quitaría un test). `_connection.py` (407) no se parte: lo de W8.1 va en `_handlers.py`; partirlo a
ciegas sería trabajo sin motivo. `verify` PASS, 479 tests, sin aviso de tamaño.
**Tropiezo:** `git checkout` no restaura un archivo nuevo sin seguimiento; la copia previa a la mutación lo
salvó. Para pruebas de mutación en archivos nuevos, copia antes (o `git add` primero).

**W8.1 hecha** (el usuario: «Procede entonces»). Diseño del agente dentro de lo acordado:
- **`errors="log" | "raise"`** en `InSim`, `OutSim` y `OutGauge` (`ValueError` con otro valor). Con `"raise"`, el
  primer error de un manejador (`def`, `async def`, `every`, comandos, `on_disconnect`) se registra, no corre
  ningún manejador más, se cierra (sin reconectar) y lo relanzan `wait_closed()`, la salida de `async with`
  y `run()`; `run(insim, gauge)` relanza el de cualquiera. Vive en `_handlers.py`: `Handlers(errors, fail)`,
  `call_and_wait()` (que ahora usa también `every`) y la base `StopsOnError` que comparten `InSim` y
  `_UDPSource` (al principio estaba duplicada en los dos; se extrajo antes de cerrar).
- **`@insim.on_disconnect`** (sin argumentos): una vez por cada `on_connect`, cuando la conexión ya no existe
  (no puede enviar), también al cerrar; uno `async def` se espera (si fuera tarea, `close()` lo cancelaría
  antes de empezar). Se llama en `_disconnect()`, el único sitio donde acaba una conexión.
- **`insim.reconnected`** (propiedad): `True` desde la segunda conexión. No se cambió la firma de `on_connect`
  (no rompe nada).
- **Colores:** `lfs_insim.text.Colour` (`StrEnum`: `BLACK`… `WHITE` = `^0`–`^7`, `DEFAULT` = `^8`) y
  `coloured(text, Colour.RED)` → `'^1text^8'` (`TypeError` si no es un `Colour`). `StrEnum` y no constantes
  sueltas para que el editor los liste. **Sin confirmar en la especificación:** InSim.txt no documenta los
  códigos de color; en el foro de lfs.net, una tabla de Scawen pone `^8` y `^9` como «reset» y otro
  desarrollador dice que `^9` además restaura la página de códigos. Se usa `^8` y **falta verlo en LFS real**
  antes de publicar; `^9` no se ofrece hasta saberlo.
- **Rojo primero:** `tests/test_lifecycle.py` (11 tests) falló entero antes del código (8 fallos y error de
  importación). Repetidos 15 veces junto a `test_insim`, `test_every` y `test_udp`: 15/15.
- Guía (`insim.md`, `roster-and-text.md`, `outsim-outgauge.md`, `getting-started.md`) y CHANGELOG **0.3.0**;
  `version = "0.3.0"` en `dev`, **sin publicar** (pide permiso). `verify` PASS, 490 tests. `_connection.py`: 439.

**Pruebas previas a 0.3.0 en LFS real** (el usuario: «Sí, abre LFS, comprueba los colores y publica»; sin tocar
`cfg.txt`). LFS 0.8C31 abierto por el agente (no había otro), InSim con `lfs_screen.ps1 -Keys "t" -Then
"/insim=29999{ENTER}"` desde PowerShell, puerto comprobado; cerrado al final con `/exit` por InSim.
- **El wheel, no el código fuente:** `build` y `twine` en un venv de herramientas del scratchpad (el `.venv` no
  tiene `build`); `twine check` PASSED; instalado en un venv limpio e importado desde `site-packages`.
- **Colores, vistos en una captura a resolución completa:** el texto sin código sale gris claro; tras `^8` (y tras
  `coloured()`) vuelve a ese gris; `^7` es blanco brillante, distinto. **`^8` = el color por defecto del mensaje:
  confirmado.** `^9` se ve igual que `^8` en el chat; lo de la página de códigos no se probó, así que no se ofrece.
- **Fallo encontrado y arreglado:** `on_disconnect` no se llamaba si `close()` se llamaba desde `on_connect`.
  Diagnóstico con trazas (sin tocar la biblioteca): ese `close()` cancelaba el supervisor, así que
  `wait_closed()` volvía antes de terminar el cierre; luego el `close()` de `async with` cancelaba las tareas de
  manejadores, entre ellas la que estaba a mitad del primer cierre, y la cancelación llegaba al lector dentro de
  `_disconnect()`, antes de `on_disconnect`. El test de W8.1 no lo vio porque cerraba solo por `async with`.
  **Arreglo:** el cierre corre una sola vez en su propia tarea (`StopsOnError._close`, protegida con `shield`);
  cada `close()` la espera; `wait_closed()` espera a que acabe; el que llama no se cancela (`keep`); un `close()`
  dentro de `on_disconnect` no espera (se esperaría a sí mismo). **Rojo primero:** dos tests nuevos (cerrar desde
  `on_connect`; cerrar desde `on_disconnect`, con LFS que se va y sin él) fallaron antes del arreglo. 492 tests;
  15/15 repeticiones de los de conexión. Con el wheel nuevo, en LFS real: `connect` y `disconnect`.
- **`errors="raise"` en vivo:** un manejador de `IS_VER` que falla → `run()` relanza «bug on purpose (LFS 0.8C31)».

**Publicado 0.3.0:** CI `verify` en verde en los 8 trabajos (3.11–3.14, Windows y Ubuntu); avance rápido de `dev` a
`main` (`ea4edc0`); release `v0.3.0` (pre-release, notas del CHANGELOG); `publish` se paró en el entorno `pypi`.
El usuario preguntó qué tenía que aprobar y, tras la explicación, dijo «Hazlo tú directamente»: el agente lo
aprobó por la API (`pending_deployments`, `state=approved`, con la cuenta `AdrianPascarella`, revisora del
entorno). `publish` en verde; instalado desde PyPI en un venv limpio: 0.3.0, `coloured`, `on_disconnect`,
`reconnected` y el rechazo de `TINY.NCN`; PyPI lista 0.3.0, 0.2.0 y 0.1.0.
**Tropiezo de comunicación:** el agente lanzó una espera de hasta 10 minutos sin decir antes qué tenía que hacer el
usuario en GitHub; el usuario la cortó. Al pedir una aprobación, explicar primero dónde y qué pulsar.
**Instrucción permanente (§15):** preguntado si «Hazlo tú directamente» valía siempre: «Vale siempre, guárdalo».
Escrita en `PROTOCOL.md` §15: con permiso para publicar, el agente aprueba él mismo el entorno `pypi`.

**W8.2 hecha** (el usuario: «sigue con W8.2»). Diseño del agente dentro de lo decidido al abrir W8:
- **Argumentos = parámetros tras el `Command`**, convertidos por su anotación (`str`, sin anotación también;
  `int`, `float`); con valor por defecto, opcional; `*resto`, las palabras que quedan. Otro tipo, un parámetro
  solo por nombre sin valor por defecto, o ningún parámetro: `TypeError` al registrar. Una función de solo el
  `Command` (o `print`, `list.append`) funciona como antes: cualquier palabra, sin comprobar.
- **Palabras que no encajan:** se contesta solo a quien lo escribió («!speed: kmh must be a whole number, not
  'abc'. Use: !speed <kmh> [who]», «… is missing», «too many words») y la función no se llama; no es un error
  del programa (no se registra ni cuenta para `errors="raise"`). **`!speed ?`** → uso y primera línea del
  docstring (el de un builtin no se usa).
- **Permisos:** `admin=True` deja al host (UCID 0) y a quien LFS marca `Admin` en `IS_NCN`; para saberlo,
  `Commands` crea un `Roster` interno la primera vez que hace falta (otro `Roster` del usuario pide lo mismo dos
  veces: inofensivo). Sin datos aún, se niega (lo seguro). `allow=función(Command) -> bool`; si falla, cuenta
  como error de manejador y se niega. Respuestas: «!kick is only for admins», «You may not use !boost».
- **Grupos:** `insim.command_group("aic", admin=, allow=)` → `CommandGroup.on_command("start")`; `command.name`
  es «aic start»; los límites del grupo y del comando se suman. `!aic` (o `!aic ?`) lista los comandos; con uno
  que no existe, lo dice y los lista (el grupo es nuestro, así que sí se contesta).
- Todo en `_commands.py` (297 líneas); `_dispatch` solo llama a `Commands.handle`. `_connection.py`: 462.
- **Rojo primero:** `tests/test_commands_typed.py` (10 tests) falló antes del código (9 de 10). Un test estaba mal
  (suponía que un comando `async` acaba antes que uno `def`): se corrigió para no depender del orden, dicho aquí.
  `verify` PASS, 502 tests; 10/10 repeticiones. Guía (`insim.md`) y CHANGELOG «Unreleased». **Sin probar en LFS
  real** (teclear `!speed abc` en el chat): antes de publicar 0.4.0. Los administradores remotos solo se pueden
  ver en un servidor con otra persona: punto ciego.

**W8.3 hecha** (el usuario: «Sí, sigue con W8.3»). **Solo las escalas que InSim.txt da** (§15, Scawen manda):
`CompCar` y `Vec` (65536 = 1 m; Speed 32768 = 100 m/s; Direction/Heading 32768 = 180°; AngVel 16384 = 360°/s,
y la NOTE 3, 8192 = 180°/s, dice lo mismo), `CarContact`/`CarContOBJ` (16 = 1 m; Speed en m/s; ángulos byte,
128 = 180°), `SpClose` de `IS_CON`/`IS_OBH` (12 bits bajos, 10 = 1 m/s) y `OutGaugePack.Speed` (m/s). **Fuera**,
por no tener escala en la especificación: H/P/R de `IS_CPP` y `ObjectInfo` del autocross (su escala está en el
formato de archivo de layout, no en InSim.txt).
- `lfs_insim.units`: funciones puras de ida y vuelta (`to_metres`/`from_metres`, `speed_to_mps`/`mps_to_speed`,
  `angle_to_degrees`/`degrees_to_angle` con vuelta a 0–65535, `angvel_to_degrees`/`degrees_to_angvel`,
  `mps_to_kmh`, `kmh_to_mps`, `mps_to_mph`, `mph_to_mps`; 1 mph = 0,44704 m/s exacto).
- Propiedades de solo lectura por `EXTRAS` (`CompCarUnits`, `ContactUnits`, `ClosingSpeed`, `GaugeUnits` en
  `_extras.py`); `Vec` las lleva directamente (es escrita a mano) y además `Vec.from_metres()` para enviar.
  Nombres: `x_m`, `speed_mps`, `speed_kmh`, `speed_mph`, `direction_deg`, `heading_deg`, `angvel_dps`,
  `closing_speed_mps`. Los campos siguen siendo los números de LFS (lo que se envía).
- **Rojo primero:** `tests/test_units.py` (11) falló al importar antes del código. `verify` PASS, 515 tests.
  Página nueva `docs/units.md` (enlazada en `docs/README.md`) y CHANGELOG «Unreleased». **Sin probar en LFS real**
  (comparar `CompCar.speed_kmh` con `OutGaugePack.speed_kmh` con un coche en pista): antes de 0.4.0.

## S16 — 2026-10-13 — W7.6: equivalencia, tabla de direcciones, guía en forma canónica y 0.2.0

**Inicio:** identidad git correcta (`AdrianPascarella`, gmail); `verify` PASS antes de tocar nada.
**U7 cerrada:** el usuario probó `insim.on.` / `insim.send.` en su VS Code: «va perfecto».

**Hecho:** (1) `tests/test_equivalence.py` (128 tests): para cada uno de los 70 paquetes, la clase es la
misma en `packets`, `received` y `sent` según su dirección, `on.X` / `send.X` existen solo si toca,
`on.X(h)`, `on(X)(h)` y `on(received.X)(h)` registran lo mismo; OutSim/OutGauge solo en `received`.
(2) `docs/packets.md`, tabla generada por `generate_packets.py` (`emit_table` en `spec_directions.py`),
enlazada desde `docs/README.md`; los `.md` no pasan por ruff. (3) README, guía y los cuatro ejemplos
pasados a `@insim.on.IS_X` / `insim.send.IS_X(...)` con `received.IS_X`; `insim.send(a, b)` se queda
donde se envían varios. (4) `CHANGELOG.md` 0.2.0 y `version = "0.2.0"`.
**Verificación:** `verify` PASS, 474 tests. **Sin publicar:** subir 0.2.0 a PyPI (merge a `main`, release,
aprobar entorno `pypi`) exige permiso expreso del usuario.
**Pruebas previas a publicar 0.2.0 (S16, con permiso del usuario para abrir LFS, manejarlo y tocar `cfg.txt`):**
- **El wheel, no el código fuente:** `build` → `lfs_insim-0.2.0` (wheel y sdist); `twine check` PASSED;
  instalado en un venv limpio (Python 3.14), con `py.typed`, `received`, `sent`, `_events` y
  `_shortcuts` dentro. Un script de usuario con `@insim.on.IS_VER`, `insim.send.IS_MST(...)` y
  `insim.send(sent.IS_TINY(...))` contra un LFS falso por TCP: OK; `mypy --strict` sobre él: sin errores.
- **LFS 0.8C31 real, con el wheel:** `live_lfs.py` con InSim, OutGauge (853) y `OutSimPack2` (853, Opts
  `1ff`): 0 paquetes ilegibles, 0 reescritos distintos, 0 avisos. `hello.py` («Hello from Python»),
  `who.py` (lista a los AI), `buttons.py` (clic → «Clicked 1 times», cuadro de texto con título → «You
  typed: prueba 0.2.0», `!hide` los quita) y `gauge.py` («0 km/h at 722 rpm (4 in the race)»): todos
  vistos en la captura.
- **Tropiezos:** (1) `/insim=29999` tecleado desde Git Bash llegó a LFS como `C:/Program Files/Git/insim=29999`
  (la cicatriz de §13 ya existía: no usar Bash para teclear comandos de LFS; PowerShell, y comprobar el
  puerto antes de seguir). (2) El usuario rechazó una ejecución a medias y quedó un `python` suelto
  ocupando los puertos UDP: se paró. (3) OutSim no mandaba nada mientras el usuario miraba a los AI:
  solo manda la física del coche que conduces tú (OutGauge sí, del que se ve).
- **`cfg.txt`:** copia en `_archivo_AP_LFS_InSim\cfg_backup_2026-10-13_S16_prerelease.txt`; restaurado
  idéntico a la copia (byte a byte, CRLF). LFS cerrado por InSim (`/exit`).

**Publicado (el usuario: «Publica»):** CI en verde; avance rápido de `dev` a `main`; release `v0.2.0` (pre-release);
entorno `pypi` aprobado; `publish` en verde; PyPI lista 0.1.0 y 0.2.0, e instalado desde PyPI en un venv limpio
devuelve 0.2.0 con `on.` y `send.`.

**W7.7 hecha (decidida con el usuario antes de escribir):** `@insim.on.IS_TINY(TINY.MPE)` y
`@insim.on.IS_SMALL(SMALL.STP, SMALL.RTP)`, solo al recibir (enviar ya se lee bien); `on.IS_TINY` sin
paréntesis sigue recibiendo todos; `on(IS_TINY, TINY.MPE)` es la forma larga. Sin LFS real (acordado:
la lógica no toca bytes). **Rojo primero:** 3 tests de `tests/test_subtypes.py` fallaron antes del
código. Implementación: `Handlers` guarda `(manejador, subtipos)` y salta los que no tocan
(`_handlers.py`); `Receive.__call__` con sobrecargas y `SubReceiver` / `Subtyped` en `_events.py`; el
generador emite `SubReceiver(IS_TINY, TINY)` (`SUBTYPE_ENUMS`). Tropiezos: las sobrecargas
`*subtypes` se solapaban con la genérica (mypy `overload-overlap`): ahora piden al menos un subtipo;
las barras invertidas en un script en línea otra vez (usar Edit). `verify` PASS, 477 tests. **Sin
publicar** (CHANGELOG «Unreleased»; la versión sigue en 0.2.0).

**Cierre de S16:** el usuario eligió abrir **W8** en la próxima sesión (el agente había recomendado W6 antes,
para que una aplicación real ordenara W8; el usuario prefirió W8 y se respeta). Nada pendiente de él
(`USER_ACTIONS.md` vacío). `main` = release `v0.2.0`; `dev` va por delante con W7.7 y la documentación.

**Tropiezo:** un `sed` con `&` estropeó `spec_directions.py`; restaurado con git y reaplicado. Las
barras invertidas en la entrada de Bash se pierden: para ellas, usar Edit.

## S15 — 2026-10-13 — Auditoría de S13–S14, W7 rehecha y W7.1

**Inicio:** el control de inicio falló en la identidad: el repo no tenía identidad local en este
equipo (el segundo, ver PROTOCOL «Máquinas») y salía `apascarella@tensolutions.es`. Corregida en local.
**16 commits de S13–S14 ya subidos** con ese correo (14 en `main`, que es de donde sale `v0.1.0`).

**Auditoría pedida por el usuario** (S13–S14 se hicieron con Sonnet 5.5, primera vez que lo usaba).
Comprobado, no solo leído: `verify` en verde; CI verde en todos los commits salvo el fallo de tiempos ya
diagnosticado; `publish.yml` correcto; PyPI con wheel y sdist 0.1.0; release `v0.1.0` (pre-release, en
`58a71ae`; `main` va un commit de documentación por delante); entorno `pypi` con revisor obligatorio; cada
afirmación de README y `docs/` contrastada con la API real; afirmaciones de `LEGADO.md` comprobadas (la
dirección en el `enum` ISP, ningún test nombra `IS_REO`/`IS_HCP`/`IS_IPB`, la espera solo se reinicia
con `IS_VER`). **Diagnóstico de `test_every` reproducido** en Python 3.12 de este equipo, 25
ejecuciones de cada versión: los tests antiguos fallaron 4/25 y los nuevos 0/25.
Defectos encontrados: (1) no se ejecutó el control de inicio (§3.2) → los 16 commits; (2) en
`test_a_slow_call_does_not_cause_a_burst` el margen bajó de 0,01 s a 0,002 s sin anotarlo (§5). Se acepta
por un motivo que **se registra aquí**: tras una llamada lenta, `repeat()` espera `seconds` medidos con
`loop.time()`, cuyo reloj en Windows anterior a 3.13 va a saltos de ~15 ms, y asyncio adelanta los
temporizadores hasta su resolución, así que el hueco real puede bajar de 10 ms sin que haya ráfaga;
una ráfaga se vería como microsegundos, que 2 ms sigue detectando; (3) `bd05b30` borró del LOG la única
nota del arreglo de `every` (§1); (4) no se anotó el equipo nuevo (§16); (5) U6 decía que faltaba el
entorno `pypi`, ya creado; (6) el `.venv` se creó sin `--group dev` (salió ruff 0.17.0, dentro del
rango, por suerte). Sin confirmar: que el merge a `main` y la aprobación del despliegue tuvieran permiso
(el LOG de S14 lo dice; preguntado al usuario).

**Correo:** el usuario eligió `.mailmap` (recomendado) en vez de reescribir el historial, que obligaba a
force-push en `main` y a mover `v0.1.0`, ya publicada. Commit `1aa1ab7`. GitHub no usa `.mailmap` en su web.

**W7 rehecha con el usuario.** El agente desaconsejó los ~95 métodos `on_IS_XXX` / `send_IS_XXX`:
llenan `insim.` (al teclear `insim.s` saldrían 30 `send_IS_…` delante de `say`), no ahorran el import
(el tipo del argumento de un `def` no se deduce del decorador), `send_IS_X` repite el constructor, tres
formas por cosa, y quitarlos después rompe código ajeno, mientras que añadirlos después no. El usuario
aclaró que lo que echaba de menos del anterior era **ver la lista**. Propuesta del agente, aceptada:
colgar la lista de `on` y `send` (`@insim.on.IS_NPL`, `insim.send.IS_MST(...)`), sin tocar el espacio
de nombres de `insim`; se mantienen `on(IS_X)` y `send(a, b)`; `received.IS_X` es la misma clase, así que
no cuenta como forma aparte. Prototipo comprobado con mypy estricto: `send.IS_MST` toma la firma del
constructor (`ParamSpec`, revelada como `def (Msg: str =, ReqI: int =)`) y salen los cuatro errores
esperados (tipo de campo, campo inexistente, `send.IS_NPL`, manejador de otro paquete). Pylance está
instalado aquí; cómo lo ve el editor es punto ciego (comodidad de la API), para cuando W7.4 esté hecha.
Pregunta del usuario: ¿puede el manejador tener el tipo sin importar el paquete? En un `def`, no: Python
no deduce el tipo del argumento a partir del decorador (ni mypy ni Pyright). La guía enseñará
`from lfs_insim import received` y `packet: received.IS_NPL`: un solo import, con la lista también al
anotar.

**W7.1 hecha:** `scripts/spec_directions.py` (`packet_directions(spec)`) lee la dirección del comentario
de cada `ISP_` y para con `SpecError` si falta o es otra palabra; el generador comprueba que cada `IS_`
tiene dirección y al revés. Resultado: 70 paquetes, 43 `info`, 16 `instruction` y 11 `both ways`
(`AXM`, `BFN`, `CPP`, `IPB`, `MAL`, `PLH`, `REO`, `RIP`, `SMALL`, `SSH`, `TINY`). `REO` («info or
instruction») sale `both ways`: cuenta lo de antes de los dos puntos. Los archivos generados no cambian.
`tests/test_spec_directions.py` (6 tests); vistos en **rojo** con la expresión rota (3 fallaron).
Verificación: `verify` PASS, 331 tests, ninguno saltado (aquí están la especificación y `OutSimPack.txt`).

**Documentos:** `PLAN.md` (W7 rehecha, lo antiguo tachado), `PROTOCOL.md` (segundo equipo y una
cicatriz nueva en §13), `STATE.md` (decía «W5 sin empezar», desfasado) y la línea de U6.

**El usuario confirmó** que en S14 dio permiso para el merge a `main` y para aprobar el despliegue en
PyPI: la auditoría queda sin dudas abiertas.

**Mapas freeroam de `ai_control`:** el usuario no quiere perderlos («me costó mucho tiempo hacerlos»)
por si se reutilizan. Comprobado que están en GitHub: rama `refactor/estabilizacion` (4 mapas y sus
renders; `south_city.json` de 3,2 MB, último cambio `e1240d5`) y etiqueta
`archivo/fix/radar-false-positive-behind`, con otra versión, anterior, de `south_city.json` (241 KB).
Copia extra fuera del repo con `git archive`, de la carpeta `freeroam/` entera (el código define el
formato, que no está documentado aparte), comprobada con `git hash-object`: 27 de 27 archivos idénticos.
Anotado en PROTOCOL («Lo que nunca se debe perder») y en PLAN (requisito de la aplicación de control de
IA). La memoria del agente ya no habla de commits de mapas en este repo, que ya no los tiene.

**W7.2 hecha** (el usuario dijo «Procede»): `src/lfs_insim/packets/_directions.py`, escrito a mano y
aparte porque `_codec.py` ya pasa de 500 líneas, con `InfoPacket`, `InstructionPacket` y
`BothWaysPacket` (este hereda de los dos) y el texto de los errores. El nombre `BothWaysPacket`, no el
`BothWays` del plan, es por coherencia con los otros dos. El generador da a cada `IS_` la base de su dirección
y añade al docstring «(info: LFS sends it)», «(instruction: your program sends it)» o «(both ways: …)».
Las tres clases se exportan desde `lfs_insim.packets`. En `_connection.py`, el `TypeVar` de `on()`,
`request()` y `request_all()` pasa a `bound=InfoPacket`, y `send()` recibe `InstructionPacket`; los
dos comprueban también en ejecución, con un `TypeError` que dice quién envía el paquete (`send()` lo
comprueba antes de mirar la conexión). **Cambio de API pública:** `send()` de un paquete info y `on()`
de una instrucción ya fallan (CHANGELOG en W7.6).
Tests: `tests/test_directions.py` (bases contra la especificación, docstrings, errores en ejecución y un
test que lanza mypy estricto sobre un fragmento y espera error justo en `on(IS_MST)` y `send(IS_NPL())`).
Vistos en **rojo** con el `_connection.py` anterior (3 de 6 fallaron). **Tests cambiados (§5), con motivo:** `test_packets.py`
recorre lo que exporta `lfs_insim.packets` y tomaba las tres bases por paquetes (sin `_TYPE` ni
`_LAYOUT`); se excluyen de esa enumeración, igual que ya se excluía `Structure`, sin tocar ninguna
comprobación. `tests/live_lfs.py`: la lista de enviados pasa a `list[InstructionPacket]` (mypy).
Verificación: `verify` PASS, 337 tests. CI de W7.2 (`f926efe`): `verify` y `spec` en verde.

**W7.3 hecha:** `src/lfs_insim/received.py` y `sent.py`, **generados** (`emit_direction_module` en
`scripts/spec_directions.py`, para no acercar `generate_packets.py` a 500 líneas) con cada nombre
escrito: calculados al importar, el editor no vería la lista, que es el objetivo de W7. Solo
necesitan `InSim.txt`, así que el CI los comprueba. `received` tiene 54 paquetes (info + both ways) y `sent` 27
(instruction + both ways). Se exportan desde `lfs_insim` para que `lfs_insim.received` funcione tras
`import lfs_insim`. OutSim y OutGauge entran en `received` en W7.5. Tests en `test_directions.py`:
mismas clases (no copias), completos según la base, los `both ways` en los dos, `received.IS_MST` no
existe. Visto en **rojo** quitando `IS_TINY` de `received.py` a mano (el test y `--check` lo detectan).
Verificación: `verify` PASS, 339 tests.

**W7.4 hecha:** `insim.on` e `insim.send` dejan de ser métodos y son atributos de instancia
(`On` / `Send`), invocables como antes. Lógica a mano en `src/lfs_insim/_events.py`: `Receive` y
`Transmit` (bases invocables, con la comprobación de dirección que W7.2 puso en `_connection.py`) y
los descriptores `Receiver` (devuelve el decorador tipado para ese paquete) y `Sender` (copia con
`ParamSpec` la firma del constructor; la función devuelta lleva el nombre y la ayuda del paquete).
Atributos generados en `src/lfs_insim/_shortcuts.py` (`emit_shortcuts` en `spec_directions.py`): 54
en `On` y 27 en `Send`, cada uno con la descripción de la especificación como docstring de atributo
(Pylance la enseña). `_connection.py` queda con `_write()` (la conexión) y pasa a 407 líneas; `P` se
importa de `_events`. **Cambio de API pública:** `insim.on` / `insim.send` ya no son métodos (llamarlos
funciona igual). Tests: `tests/test_shortcuts.py`, de extremo a extremo con el LFS falso (las formas
llegan a LFS y al manejador) y mypy estricto sobre un fragmento: errores justo en el manejador de otro
paquete (mypy lo marca en la línea del decorador), `on.IS_MST`, `Msg=3`, un campo inexistente y
`send.IS_NPL`, y `send.IS_MST` revelado como `def (*, ReqI: int =, Msg: str =)`. Visto en **rojo**
haciendo que `send.IS_XXX` construyera sin enviar. Dos expectativas mías estaban mal y se corrigieron
(el test, no el código): la línea del error del decorador, y esperar `IS_VER` con `lfs.wait_for()`,
que solo ve lo que envía el programa. Verificación: `verify` PASS, 343 tests. Pyright no está
instalado como herramienta (instalarlo pide permiso); cómo lo ve Pylance → **U7** abierta (validar,
bloquea W7.6). Tropiezo con la cicatriz de los heredocs (§13) al escribir U7: el script no llegó a
ejecutarse y se hizo con Edit.

**W7.5 hecha:** `gauge.on` y `outsim.on` son objetos (`GaugeOn`, `OutSimOn` en `_udp.py`), invocables
como antes y con una propiedad por paquete: `@gauge.on.OutGaugePack`, `@outsim.on.OutSimPack` y
`.OutSimPack2`. **Escritos a mano, no generados** (el plan decía generar): son tres atributos fijos,
y propiedades tipadas evitan los descriptores genéricos. Los paquetes se nombran como `_p.X` dentro de
esas clases para que una propiedad no tape a la clase del mismo nombre. `received` incluye
`OutGaugePack`, `OutSimPack` y `OutSimPack2` (constante `UDP_PACKETS` en `spec_directions.py`, que el
generador comprueba contra las especificaciones disponibles); como sus clases ya están en
`lfs_insim.packets`, `received.py` sigue sin necesitar `OutSimPack.txt` y el CI lo comprueba entero.
`insim.on(received.OutGaugePack)` da un error que lleva a `@gauge.on.OutGaugePack`. **Tests
cambiados (§5), con motivo:** los de W7.3/W7.4 comparaban `received` solo con los paquetes InSim; ahora
cuentan los tres de UDP (en `test_shortcuts.py`, `insim.on.` se compara con los `IS_` de `received`).
Tests nuevos en `test_udp.py` y en el fragmento de mypy (manejador de otro paquete y `gauge.on.IS_NPL`).
Visto en **rojo** cambiando el nombre de la propiedad `OutGaugePack`. Verificación: `verify` PASS, 344 tests.

## S14 — 2026-10-13 — U6 por el navegador

**Hecho:** Chrome conectó (en S13 no). Con el usuario haciendo cuentas, verificación de correo y 2FA
(el agente no puede: PROHIBIDO por seguridad del navegador), el agente rellenó y envió, con
confirmación previa, el *pending publisher* de `lfs-insim` en TestPyPI (entorno `testpypi`) y en PyPI
(entorno `pypi`): `AdrianPascarella/AP_LFS_InSim`, `publish.yml`. Comprobado releyendo ambas páginas.
**U6 cerrada.**

**W5.5 hecha:** `dev` fusionado en `main` (avance rápido, con permiso) porque `workflow_dispatch` exige
el workflow en la rama por defecto; entorno `pypi` creado en GitHub con el usuario de revisor. Lanzado
`publish.yml` (run 38371844831): `build` y `testpypi` en verde, `pypi` omitido. Instalado
`lfs-insim==0.1.0` desde TestPyPI en un venv limpio (Python 3.14, Windows): importa, y `hello.py` arranca
y espera a LFS con el mensaje esperado. **No probado:** con LFS en vivo desde el paquete instalado ni en
otro equipo (punto ciego sigue abierto). Los índices no permiten resubir 0.1.0 con otro contenido.

**Prueba en vivo del paquete instalado (S14):** abierto LFS (permiso de S9), Un Jugador en Blackwood
(la primera vez genera la ruta de la IA, ~3 min), `/insim=29999`, `examples/hello.py` ejecutado con el
`lfs-insim 0.1.0` de TestPyPI en el venv limpio: imprimió `Connected to LFS 0.8C31, InSim 10` y, al
escribir `!hello` en el chat, LFS mostró «Hello from Python». LFS cerrado con `/exit`. Una vez la
protección de `lfs_screen.ps1` saltó (el usuario usaba otra ventana): no se envió nada y se esperó.
Sigue sin probarse en otro equipo.

**W5.6 hecha:** `main` al día con `dev`; `gh release create v0.1.0` (pre-release, alpha); el workflow
`publish.yml` (run 38373393060) construyó y esperó al revisor del entorno `pypi`. **El usuario pidió
que el agente aprobara el despliegue** («Hazlo tú mismo»): aprobado con
`gh api .../pending_deployments`. Publicado `lfs-insim 0.1.0` en PyPI; `pip install lfs-insim==0.1.0`
en un venv limpio importa bien. **W5 completa.** Las versiones futuras: receta en STATE.

**Legado:** a petición del usuario («no me acaba de gustar» algo respecto al anterior), explicada la
biblioteca de cero y revisada a fondo `origin/refactor/estabilizacion`. Resultado: `docs/dev/LEGADO.md`
(propuestas sin decidir: comandos con tipos/ayuda/permisos, `on_disconnect`, ayudante de botones,
unidades, modo `errors="raise"`, colores; y tres comprobaciones de tests). El usuario aprobó «prácticamente todo»; sus reparos llevaron a W7.

**Decisiones (usuario):** la pega era no saber qué paquetes se reciben, se envían o van en ambos sentidos
(el anterior lo tenía en `docs/tutorial/` y en los `.pyi`). Se comprobó que la especificación ya marca la
dirección (`enum` ISP). Acordado: clases base por dirección, módulos `received`/`sent`, y métodos
`on_IS_XXX` / `send_IS_XXX` generados, con todas las formas válidas y `on_IS_XXX` canónica; también
OutSim y OutGauge. Los plugins: `Roster` ya lo es; sin cargador. Apuntado como **W7** y **W8** en `PLAN.md`
y en `LEGADO.md` §5. No se tocó código.

**Pendiente:** abrir W7 (o elegir otra fase).

## S13 — 2026-10-13 — W5 detallada

**Inicio:** la sesión arrancó en `main`; el usuario pidió cambiar a `dev` (hecho, pull al día).

**Decisiones del usuario:** documentación en `README.md` + `docs/` en Markdown (sin MkDocs/Sphinx
por ahora); publicación con Trusted Publishing desde GitHub Actions; estado Alpha para 0.1.0.

**Hecho:** W5 detallada en `PLAN.md` (W5.1–W5.6). Aún no se ha tocado código. Anticipada la tarjeta
U6 (cuentas y publicador en TestPyPI/PyPI), que se abre al llegar a W5.4.

**W5.1 hecha:** README real (alpha, instalación, primer programa, tabla de qué usar para qué).
`tests/test_readme.py` comprueba que su ejemplo es `examples/hello.py`. En este equipo no había
`.venv`: creado con `pip install -e . ruff mypy pytest`; `verify.py` en verde (310 tests).
Aviso que ya existía: `packets/_codec.py` tiene 525 líneas (límite 500).

**W5.2 hecha:** guía en `docs/` (índice, empezar, InSim, Roster y texto, OutSim/OutGauge), en
inglés, enlazada desde el README. `tests/test_docs.py` comprueba que los bloques de código son
Python válido con `import` que existen, y que no hay enlaces ni anclas rotos; el código no se
ejecuta (necesitaría LFS). Se quitó una línea de `cfg.txt` (`OutGauge Delay`) que no se podía
respaldar con nada del repositorio. Lo que **no** está comprobado en el LFS real: los fragmentos
nuevos de la guía que no vienen de `examples/` (solo se comprobó que compilan).

**W5.3 hecha:** `pyproject.toml` en 0.1.0 y Alpha, `CHANGELOG.md`. `python -m build` y
`twine check` en verde (wheel y sdist). El wheel lleva `py.typed` y la licencia; se instaló en un
venv limpio (fuera del repositorio): `import lfs_insim` da 0.1.0 y `examples/hello.py` carga. El
sdist llevaba `CLAUDE.md`, `docs/dev` y `.github`: excluidos en `[tool.hatch.build.targets.sdist]`.
Nada subido a ningún índice.

**W5.4 hecha (escrita, no ejecutada):** `.github/workflows/publish.yml`. Job `build` (comprueba que
el tag sea `v<versión>` en los releases, construye, `twine check`, sube `dist`); job `testpypi`
(lanzamiento manual, entorno `testpypi`, `skip-existing`); job `pypi` (al publicar un release,
entorno `pypi`). Ambos con `id-token: write` y `pypa/gh-action-pypi-publish@release/v1`, sin tokens.
El YAML se comprobó con un parser; no hay forma de probarlo sin las cuentas. Abierta la tarjeta
**U6** (cuentas y publicador en los dos índices), que bloquea W5.5 y W5.6.

**Intento de hacer U6 desde el navegador (a petición del usuario):** no hay herramientas de
Chrome en la sesión (ni `mcp__claude-in-chrome__*` ni el navegador integrado). El usuario ejecutó
`/chrome` (sin salida visible) y `claude -chrome` (error: la opción es `--chrome`, con dos
guiones). Reintentado dos veces, sin herramientas. Pendiente para la siguiente sesión: arrancar con
`claude --chrome --continue` (Chrome abierto y extensión instalada) y comprobar `/chrome`. Aun
conectado, la creación de cuentas, el correo y el 2FA los hace el usuario; el agente solo rellena
los formularios del «pending publisher» con la sesión ya iniciada. Si no conecta, U6 sigue siendo
manual. Nada se ha hecho en TestPyPI ni PyPI.

**CI:** dos fallos intermitentes en Windows, en tests distintos de `tests/test_every.py` (de tiempos); ambos pasaron al relanzar (el primero ya; el segundo, ver STATE). Sin relación con W5. Anotado en STATE como «Tests inestables», sin arreglar.

**Siguiente:** U6 (por el navegador o a mano); después W5.5.

## S12 — 2026-10-12 — Primera prueba con el LFS real (W3.1, primera pasada)

**Inicio:** según el protocolo; control de inicio en verde, 0 acciones del usuario pendientes.

**Decisión del usuario:** InSim lo activó él esta vez, escribiendo `/insim=29999` en LFS (opción 1
de 3). Para el futuro: «mejor la 2 y/o la 3 (prefiero yo quedar fuera)», es decir, el agente
controlando la pantalla o con `autoexec.lfs` (con permiso, porque está en `C:\LFS`). Anotado en
`PLAN.md` (W3.1).

**Hecho:** `tests/live_lfs.py`, sin el prefijo `test_` para que pytest no lo recoja. Envuelve
`unpack_insim` de `_stream` para guardar los bytes de cada paquete; pide con `IS_TINY` (cada
`ReqI` distinto, para saber qué petición tuvo respuesta) VER, PING, SST, GTM, SCP, ISM, NCN, NPL,
RES, NLP, MCI, REO, RST, AXI, RIP, NCI, ALC, AXM, SLC, MAL, PLH, IPB y LCL; envía `IS_MSL`, `IS_MSX`,
`IS_MST` (con acentos, `€` y griego) y un `IS_BTN` con `Caption`; lo borra con `IS_BFN` y, con
`--exit`, cierra LFS con `/exit`. El informe va a `tests/live_reports/` (en `.gitignore`: lleva
nombres de jugadores). Ensayado antes contra el `FakeLFS`.

**Resultado con LFS 0.8C31 en el menú (un jugador, sin carrera):** conectó; 0 paquetes ilegibles; 0
reescritos con otro contenido. Respondieron VER, PING (`TINY_REPLY`), SST (`IS_STA`), GTM, SCP
(`IS_CPP`), ISM, NCN, REO, RIP, ALC, AXM, MAL, PLH y LCL. Sin respuesta, lo esperable sin carrera,
sin servidor o sin layout: NPL, RES, NLP, MCI, RST, AXI, NCI, SLC e IPB. Los tres mensajes
volvieron como `IS_MSO` con el texto exacto (`TextStart` 21 = índice en el `str`, bien).
LFS se cerró con `/exit`.

**Diagnóstico (§8):** la primera versión exigía los mismos bytes al reescribir, y dos `IS_MSO`
fallaban. No era un error de la biblioteca: LFS pone `^L` delante del texto del chat y rellena con
más ceros; la biblioteca quita los cambios de página al leer y no los repite si no hacen falta
(D3, S7). El criterio pasó a ser «mismo contenido al leer lo reescrito», y las diferencias de bytes
quedan en el informe como información. Comprobado con los bytes reales guardados. También se vio
que LFS quita los colores del chat en `IS_MSO` si no se pide `ISF.MSO_COLS`.

**Tropiezo propio:** un comando con dos heredocs mal encadenados abrió el `python` de
streamer-project en modo interactivo, sin ejecutar nada (§13 otra vez). Se paró la tarea y se rehizo
con Edit.

**Verificación:** `verify.py` → PASS (255 passed, 1 deselected); aviso de tamaño de `_codec.py`
igual que antes.

**Commits:** `276aa2d` (script) y el cierre de este hito.

**Segunda pasada (el usuario: «continuemos»), sin el usuario:**
- **Activar InSim y manejar LFS desde el agente.** No hay herramientas de control de pantalla en la
  sesión. Funcionó lo siguiente: `WScript.Shell.AppActivate` + `SendKeys` (`t`, `/insim=29999`,
  Enter), y clics con `SetCursorPos`/`mouse_event` de `user32` desde PowerShell, con capturas de
  pantalla a media resolución (`CopyFromScreen`) para ver dónde está. El script de clic y captura
  está en el scratchpad de la sesión, no en el repositorio. Pantalla de 1920×1080: Un Jugador
  (1736, 506), OK del circuito (356, 1038), GO (1786, 1038). Los botones InSim (200×200 unidades)
  caen en x = 420 + L·5,4, y = T·5,4.
- **Tropiezo:** Git Bash convierte `/help` en `C:/Program Files/Git/help` al pasarlo como
  argumento. Solo salió basura en el chat local. Hace falta `MSYS_NO_PATHCONV=1`.
- **Montar la carrera:** en el menú, `/ai` contesta «Circuito no disponible»; en la pantalla de Un
  Jugador sí añade IA (`IS_NPL` con `PType=2`). El coche elegido era un mod (`SLX180 TYPEX~008`):
  LFS generó la trayectoria de la IA para él al pulsar GO (lo escribe el propio LFS en `C:\LFS`).
- **Resultados:** carrera de 3 vueltas en BL1 con 2 IA, todo en verde. Llegaron, entre otros,
  `IS_MCI` ×361, NLP, NPL, RST, SPX, LAP, CON, HLV, FLG, FIN, RES, CIM y AXI. **`CName` = `35D799`**,
  el mismo SkinID que muestra LFS (P6 validado). El botón con `TypeIn` abrió el cuadro «Type
  something» (`Caption`, U3) y devolvió `IS_BTT` con «hola mañana»; un segundo botón sin `TypeIn`
  (añadido al script) devolvió `IS_BTC`. NCI, SLC e IPB: LFS dice «only for multiplayer hosts».
  Solo `TINY_RES` no respondió, ni siquiera durante la carrera. Pendiente de mirar.
- Script: se añadieron `ISF.MCI | HLV | OBH` y el segundo botón; `IS_BFN` con `BFN.CLEAR` al final.
- **OutSim/OutGauge:** no hay comando en `C:\LFS\docs\Commands.txt`; hace falta `cfg.txt`
  (`OutGauge Mode/Port`, `OutSim Mode/Port/Opts`, líneas 204–214, ahora todo a 0). Se pide permiso.

**Tercera pasada: OutSim y OutGauge.** El usuario dio permiso para los cinco cambios de `cfg.txt`
y para guardar en el repo el script de pantalla («me gusta tu propuesta. Procede»).
- **`tests/lfs_screen.ps1`**: teclas (`-Keys`, `-Then`), clic (`-X`, `-Y`) y captura en
  `tests/live_reports/screen.png`. Con él se abrió LFS, se activó InSim y se montó la carrera sin
  el usuario. `live_lfs.py` escucha además `--outgauge`, `--outsim` y `--outsim-opts` (subclases que
  pasan cada datagrama por el mismo registro) y guarda en el informe 20 paquetes de cada tipo como
  máximo.
- **`cfg.txt`:** copia en `_archivo_AP_LFS_InSim\cfg_backup_2026-10-12_S12.txt`; cambios con LFS
  cerrado. **Tropiezo:** el primer `sed -i` pasó el archivo entero de CRLF a LF. Se vio con `diff`,
  se rehízo desde la copia con Python en binario y se comprobó con `od -c` (cicatriz nueva en §13).
  Al final, las cinco líneas vuelven a 0. Al salir, LFS cambió por su cuenta `Setup Name` y
  `Setup Index`, que se dejan.
- **Resultados** (carrera en BL1, unos 20 s): OutGauge (puerto 30001) y OutSim clásico (Opts 0,
  puerto 30002), 2055 de cada uno; después `OutSimPack2` con Opts `1ff`, 2056. Todos leídos y
  reescritos sin fallos; las partes opcionales de `OutSimPack2` tienen valores con sentido
  (ruedas, entradas, `EngineAngVel`…).
- **Error encontrado (§8):** `OutGaugePack.Car` salía `'™×5'`, que son los bytes `99 D7 35 00`: el
  SkinID `35D799` leído como texto cp1252. La comprobación automática no podía verlo, porque leer
  ese texto y volver a escribirlo no pierde nada; lo encontró mirar los valores. Test nuevo con esos
  bytes (en rojo antes) y arreglo en `spec_overrides.CAR_NAMES` (`"Car"` usa el códec `CarName`),
  regenerado. En la pasada siguiente, `Car` = `'35D799'`.
- **`TINY_RES` sin respuesta:** es lo correcto. LFS solo envía `IS_RES` de quien ya terminó, y el
  script lo pide al empezar; al acabar la carrera llegaron `IS_RES` solos.
- **W3.1 y W3 hechas.** Siguiente: detallar W4 con el usuario.

**Verificación:** `verify.py` → PASS (256 passed, 1 deselected).

**Commits:** `60997bb` (arreglo de `Car`), `e3208e7` (OutSim/OutGauge en la prueba y
`lfs_screen.ps1`) y el cierre.

**W4 detallada con el usuario** («Empecemos»). El agente propuso 5 bloques y preguntó cuatro
decisiones de forma; el usuario eligió en las cuatro la opción recomendada:
- **`Roster`: identidad y estado**, sin posición ni velocidad (*descartado:* guardar lo último del
  `IS_MCI`).
- **`@insim.command`** para los comandos de chat (cierra la pregunta abierta de S2).
- **Botones: solo un ejemplo**, sin ayudante hasta que una aplicación lo pida.
- **`await insim.request(...)`**, que también usará el `Roster`.

Quedan 7 tareas en `PLAN.md` (W4.1 `IS_MSO.text`, W4.2 `request`, W4.3 `Roster`, W4.4 `say` y
`command`, W4.5 `@insim.command`, W4.6 `examples/`, W4.7 los ejemplos en el LFS real) y las
decisiones en `API_DESIGN.md`. Una propuesta del agente queda para confirmar al escribir el
`Roster`: actualizarlo antes que los manejadores del usuario cuando alguien llega y después cuando
se va.

**W4.1 — `IS_MSO.text`** (el usuario: «sigamos tus recomendaciones. Procedamos»).
- `src/lfs_insim/packets/_extras.py` con `MSOText.text` (`Msg[TextStart:]`), y
  `spec_overrides.EXTRAS = {"IS_MSO": "MSOText"}`. El generador la pone como base de `IS_MSO`,
  importa `_extras as _x` solo si hace falta y falla si `EXTRAS` nombra un paquete que no existe.
  Decisión y lo descartado, en `API_DESIGN.md` («Precisado al escribir `IS_MSO.text`»).
- **Red:** 4 tests en `tests/test_text.py` (mensaje de usuario con `^L` y griego como los reales de
  S12, de prefijo, del sistema, y que `text` no es un campo), en rojo antes del código. Bytes
  hechos a mano, sin el nombre del usuario, porque el repositorio es público. Tres mutaciones
  (`Msg` entero, un carácter de más, la parte de antes), las tres en rojo; restaurado sin restos.
- **Tropiezos:** otra vez las barras invertidas en un heredoc (§13): el parche del generador falló
  antes de escribir nada y se rehízo con Edit. mypy encontró un nombre (`bases`) reutilizado con
  otro tipo en la misma función.
- **Verificación:** `verify.py` → PASS (260 passed, 1 deselected).
- **Commit:** `e809b0b`.

**W4.2 — `await insim.request(...)`.**
- **Forma** (propuesta del agente; el usuario había delegado: «sigamos tus recomendaciones»): se
  pide por el tipo de la respuesta. `request(IS_STA)` devuelve un paquete y `request_all(IS_NPL)`
  una lista; usar la que no toca da un `TypeError` que dice cuál usar. Lo descartado, en
  `API_DESIGN.md` («Precisado al escribir `request`»).
- `src/lfs_insim/_requests.py`: tablas `SINGLE` y `MULTI` (con el campo contador: `Total`, `NumP`,
  `NumRes`) y `Requests`, que reparte `ReqI` del 2 al 255, entrega cada respuesta a su petición y,
  al cortarse la conexión, falla las pendientes con `ConnectionError`. `InSim._dispatch` entrega
  antes de llamar a los manejadores, que también reciben la respuesta.
- `tests/fake_lfs.py`: `replies[TINY.X]` = paquetes con los que contesta, con el `ReqI` de la
  petición.
- **Red:** `tests/test_request.py`, 12 tests, todos en rojo antes del código. Siete mutaciones
  (empezar en `ReqI` 1, no liberar el `ReqI`, aceptar cualquier tipo, no fallar al desconectar,
  ignorar el contador, no entregar, quitar las respuestas a los manejadores), todas en rojo.
- Los contadores coinciden con lo visto en el LFS real en S12 (3 `IS_NPL` con `NumP` 3, 1 `IS_NCN`
  con `Total` 1). La prueba con el juego queda para W4.7.
- **Verificación:** `verify.py` → PASS (272 passed, 1 deselected).
- **Commit:** `abf109e`.

**W4.3 — `Roster`** (`src/lfs_insim/state.py`, público como `lfs_insim.state`, D6).
- Antes de escribir se leyó en InSim.txt cómo se comporta cada paquete: `IS_NPL` con un PLID que
  ya existe significa que sale de boxes; `NumP` 0 es una solicitud para unirse; `IS_PLP` lo deja en
  la lista; `TINY_CLR`, `TINY_MPE`, `IS_ISM`.
- **Orden** (la propuesta de S12, que el usuario aceptó al decir «sigamos tus recomendaciones»):
  nuevo `InSim._watch(antes, después)`. «Después» va con `call_soon`, para que también un
  manejador `async` encuentre al que se va hasta su primer `await` (sus tareas se programan antes).
  Detalle y lo demás, en `API_DESIGN.md` («Precisado al escribir el `Roster`»).
- **Red:** `tests/test_roster.py`, 12 tests (estado inicial, conexiones, boxes, solicitud de
  unión, cambio de nombre, toma de coche, `TINY_CLR`, conexión desconocida, reconexión,
  `IS_ISM`/`TINY_MPE`, orden respecto a los manejadores, identificadores desconocidos). Pasaron a la
  primera, así que se pasaron 13 mutaciones (orden de antes y después, solicitud de unión, nombre
  de la IA, boxes, olvidar al pedir de nuevo, `IS_ISM`/`TINY_MPE`, `IS_CNL`, `IS_TOC`, `remote`,
  `is_ai`, `TINY_CLR`, `IS_PLP`): las 13, en rojo.
- mypy y ruff pidieron dos retoques de forma (un nombre reutilizado con otro tipo y un `if`
  anidado); el código de `IS_CNL` cambió de forma después de las mutaciones, sin cambiar lo que
  hace, y sus tests siguen en verde.
- **Verificación:** `verify.py` → PASS (284 passed, 1 deselected).
- **Commit:** `c52a919`.

**W4.4 — `insim.say()` e `insim.command()`** (en `_connection.py`).
- Límites leídos en InSim.txt: `IS_MST` 63 bytes y vale para comandos; `IS_MSX` 95, «not for
  commands»; `IS_MTC` 127, solo si LFS es el anfitrión. El códec ya cuenta los bytes después de
  codificar y da un error claro («the limit is 63»), así que `say` prueba `IS_MST` y, si no cabe,
  `IS_MSX`.
- Decisiones (en `API_DESIGN.md`, «Precisado al escribir `say` y `command`»): `say("/...")` y
  `command("sin barra")` son un `ValueError` que dice cuál usar; lo demasiado largo falla antes de
  mirar la conexión.
- **Red:** `tests/test_say.py`, 8 tests (con cirílico y japonés para los límites), en rojo antes
  del código. Seis mutaciones (siempre `IS_MSX`, nunca `IS_MSX`, ignorar `to`, dejar pasar
  comandos en `say`, `command` sin barra, no comprobar antes), todas en rojo.
- **Verificación:** `verify.py` → PASS (292 passed, 1 deselected).
- **Commit:** `d24580c`.

**W4.5 — comandos de chat** (`src/lfs_insim/_commands.py`; `Command` exportado en `lfs_insim`).
- **Choque de nombres que creó el agente al planificar:** `insim.command("/restart")` (W4.4) y
  `@insim.command("hello")` (W4.5) no pueden ser el mismo método. Se eligió
  `@insim.on_command("hello")`, como `on` y `on_connect`. Falta que el usuario lo vea.
- La función recibe un `Command` (`name`, `args`, `ucid`, `plid`, `packet` y `reply()` por
  `IS_MTC`). Decisiones en `API_DESIGN.md` («Precisado al escribir los comandos de chat»). Cuenta
  cualquier mensaje de usuario que empiece por el prefijo; cómo llega lo que escribe el anfitrión,
  en W4.7.
- **Red:** `tests/test_commands.py`, 7 tests, en rojo antes del código. De 11 mutaciones, dos
  seguían en verde y cada una señalaba un hueco real: ningún test escribía un comando con otro
  prefijo (`?hello`), y el test de «sin prefijo» pasaba por casualidad porque otro mensaje de error
  también contiene «prefix». Se añadió el caso y se precisó el texto esperado; las 11, en rojo.
- **Verificación:** `verify.py` → PASS (299 passed, 1 deselected).
- **Commit:** `fc8d0fb`.

**W4.6 — `examples/`.**
- `hello.py` (`!hello` y `IS_VER`), `who.py` (`Roster`, `IS_NPL`/`IS_PLL` y `!who`),
  `gauge.py` (`@insim.every(2)` con `await insim.request(IS_STA)`, OutGauge y `run(insim, gauge)`,
  con `IS_MSL` en pantalla) y `buttons.py` (`IS_BTN` tal cual, `IS_BTC`, `IS_BTT`, `!buttons` y
  `!hide`). El ejemplo 3 del diseño (IA) quedó como `gauge.py`: controlar la IA con `IS_AIC` es una
  aplicación entera (la de «Aplicaciones aparte»).
- `tests/test_examples.py`: carga cada ejemplo sin ejecutar su `__main__`, lo conecta al LFS
  falso y comprueba lo que hace (respuestas por `IS_MTC`, lo impreso, el `IS_MSL` con la velocidad
  de un datagrama OutGauge enviado a mano, los botones). Un test comprueba que no hay ejemplos sin
  probar. `verify.py` pasa ahora lint, formato y tipos también por `examples/`.
- Escribir `buttons.py` fue llevadero, pero se nota lo que haría un ayudante (repartir `ClickID`,
  el estado en globales, reenviar para actualizar): anotado en «Ideas», como se decidió.
- `API_DESIGN.md` apunta a `examples/` como la referencia viva.
- **Verificación:** `verify.py` → PASS (304 passed, 1 deselected).
- **Commit:** `5487d6b`.

**W4.7 — los ejemplos en el LFS real.**
- **Incidente (el más serio de la sesión):** con el usuario usando Chrome, Windows no dejó traer LFS
  al frente y las teclas del agente (`t`, `/insim=29999`, Enter, `t`, `!hello`, Enter) fueron a
  YouTube. El agente se paró, se lo contó al usuario y protegió `tests/lfs_screen.ps1`: comprueba
  que la ventana de delante es LFS y, si no, sale con 2 sin enviar nada (commit `0f4008e`; reglas
  en PROTOCOL §13). Segundo error propio: probó esa protección con un clic real en (5, 5); esa vez
  LFS sí estaba delante y el clic cayó en su menú, sin efecto. El usuario dijo «Procede», que se
  tomó como sí a seguir y a cambiar `cfg.txt` para `gauge.py`.
- **Resultados**, cada uno visto en la captura: `hello.py` contesta «Hello from Python»;
  `who.py` imprime quién entra en pista (con el SkinID del mod) y quién sale (`/spec` → `IS_PLL`,
  aún encontrado en el `Roster`), y `!who` lista los tres; `buttons.py` cuenta los clics («Clicked
  2 times»), el cuadro de texto muestra su título y contesta «You typed: hola mañana», y `!hide` los
  quita; `gauge.py` muestra cada 2 s «148 km/h at 5771 rpm (2 in the race)».
- **Encontrado con el LFS real:** LFS rechaza `IS_MTC` en un jugador («IS_MTC - only for
  multiplayer hosts»), así que `command.reply()` no llegaba. Arreglo: `say(texto, to=0)` va como
  `IS_MSL` (UCID 0 es siempre este equipo). Test nuevo en rojo antes del cambio; los tests de los
  ejemplos se ajustaron (commit `6618f3b`). También: los comandos que escribe el propio anfitrión se
  detectan bien.
- **Pendiente (W4.8):** `who.py` imprime `^h773 A.Pascarella`: `strip_colours()` no convierte los
  caracteres escapados de LFS. Propuesta en `PLAN.md`.
- `cfg.txt`: copia en `_archivo_AP_LFS_InSim\cfg_backup_2026-10-13_S12_gauge.txt`; `OutGauge Mode`
  y `Port` cambiados con LFS cerrado y restaurados después (idéntico a la copia, CRLF comprobado).
  LFS se cerró con `/exit` por InSim.
- Tropiezo menor: `Start-Process` partió un texto con espacios en varios argumentos; el script
  falló al leer los parámetros sin enviar nada. Se repitió con el texto entre comillas.
- **Verificación:** `verify.py` → PASS (305 passed, 1 deselected).

**W4.8 — `lfs_insim.text.plain()`** (el usuario: «Todo perfecto, confirmo», que confirma
también el nombre `@insim.on_command`).
- La tabla de escapados no está en InSim.txt ni en `C:\LFS\docs`; una búsqueda web no la dio. Se
  leyó en el código de InSim.NET (`LfsUnicodeEncoding.cs`, con `gh api`): 11 códigos, coherentes
  con el `^h773` → `#773` visto en W4.7. Origen anotado en el código y en `API_DESIGN.md`.
- **Red:** 7 casos en `tests/test_text.py` (el nombre real, todos los escapados, `^^1`, `^^^1x`,
  colores, código desconocido y `^` suelto, griego), en rojo antes del código. `who.py` imprime con
  `plain()` y su test usa un nombre con `^h`.
- **W4 hecha entera.** Siguiente: detallar W5 con el usuario.
- **Verificación:** `verify.py` → PASS (312 passed, 1 deselected).

## S11 — 2026-10-12 — `OutSim`, `OutGauge` y `run()` (W3.7)

**Inicio:** según el protocolo; control de inicio en verde, documentos de acuerdo con git, 0
acciones del usuario pendientes.

**Hecho, en dos commits (§5: estructura y comportamiento por separado):**
1. **Solo estructura:** el registro de manejadores de `InSim` (llamar a cada uno, aislar sus
   errores, seguir y cancelar las tareas `async`) pasa a `src/lfs_insim/_handlers.py` (`Handlers`)
   para compartirlo. Los 233 tests, en verde sin tocarlos.
2. **`src/lfs_insim/_udp.py`**: `OutGauge(port, host)` y `OutSim(port, host, *, options)`, con
   `@x.on(...)`, `async with`, `close()`, `wait_closed()` y `run()`. **`src/lfs_insim/_run.py`**:
   `run(*fuentes)`, que arranca varias en un bucle (un `Protocol` con `__aenter__`, `__aexit__` y
   `wait_closed`: no importa las clases, así no hay importaciones circulares). Exportados en
   `lfs_insim`: `OutSim`, `OutGauge`, `run`.

**Decisiones** (de API, en `API_DESIGN.md`, «Precisado al escribir `OutSim` y `OutGauge`», con lo
descartado): `options` copia «OutSim Opts» de `cfg.txt` (0 → `OutSimPack`, otro → `OutSimPack2`,
como dice InSim.txt); registrar un manejador del paquete que nunca llegará es un `TypeError`; un
datagrama ilegible se salta con un solo aviso hasta que llegue uno bueno; `run()` vuelve cuando se
cierra **cualquiera** de las fuentes y cierra las demás. `InSim.run()` no se tocó (no usa `run()`
de `_run.py`; se podría unificar, pero no aporta nada ahora).

**Diagnóstico (§8):** de 12 mutaciones, una seguía en verde: quitar la comprobación de tamaño. Los
datagramas malos del test fallaban ya por cortos; la comprobación existe para los **largos** (un
`OutGaugePack` con 8 bytes de más se leería en silencio con un `ID` inventado). Se añadió ese caso
al test y la mutación pasó a rojo. Las 12, en rojo al final; el código restaurado se comprobó sin
restos.

**Red:** `tests/test_udp.py`, 11 tests con datagramas locales en puertos libres (`port=0`; nunca
el 30000, §13) y el `FakeLFS` para `run(insim, gauge)`, que corre en un hilo con límite de tiempo.

**Verificación:** `.venv/Scripts/python scripts/verify.py` → PASS (244 passed, 1 deselected). Sigue
el aviso previo de tamaño de `_codec.py` (525 líneas), sin cambios.

**Commits:** `e22054a` (extracción) y `213511f` (W3.7). CI en verde.

**W3.8 — `@insim.every(segundos)`** (el usuario: «sigue»). El bucle está en
`Handlers.repeat` (`_handlers.py`) y `InSim` lo arranca y lo para (`_start_ticks`, `_stop_ticks`).
Decisiones en `API_DESIGN.md` («Precisado al escribir `@insim.every`»): solo mientras hay conexión
y desde el `IS_VER`, sin solaparse, y saltando las vueltas perdidas en vez de recuperarlas en
ráfaga.
- **Diagnóstico (§8):** el test «cerrar desde dentro» acabó en `RecursionError`. Causa raíz: el
  ritmo llamaba a `close()`, que esperaba a la tarea lectora; esta, al desconectar, cancelaba el
  ritmo, y la cancelación volvía por el `gather` que la esperaba, en un ciclo. Arreglo: `close()`
  para primero los ritmos, salvo el que la llama, que termina solo porque su conexión ya no existe
  (cada ritmo comprueba que sigue en **su** conexión, la del `writer` con la que empezó).
- **Red:** `tests/test_every.py`, 11 tests; 9 en rojo antes del código. De 10 mutaciones, dos
  seguían en verde y cada una señalaba un hueco real: un segundo `IS_VER` (pedido con `TINY_VER`)
  duplicaba el ritmo, y sin pararlos al desconectar, una llamada `async` que esperaba seguía viva
  sin conexión. Dos tests nuevos y las 10, en rojo.
- Tropiezo propio: preparé el script de mutaciones con un heredoc de Python con `\n` (la cicatriz
  de §13 otra vez) y además con un prefijo de shell mal escrito; el comando falló y se ejecutó la
  copia vieja, sin daño (restaura en `finally`). Se rehízo con Write.
- **Verificación:** `verify.py` → PASS (255 passed, 1 deselected).
- **Commit:** `d690f47`.

## S10 — 2026-10-12 — `InSim` básico (W3.4)

**Hecho:** `src/lfs_insim/_connection.py`, clase `InSim`, exportada en `lfs_insim` (primera pieza
de la API pública). Conecta por TCP, envía `IS_ISI` (`ReqI=1`, `InSimVer` 10), parte lo recibido
con `PacketStream` (W3.2) y llama a los manejadores de `@insim.on(Tipo)`: los `def` al momento,
los `async def` como tareas. Un error en un manejador se registra (logger `lfs_insim`, con su
nombre y traza) y no para a los demás ni a los paquetes siguientes. `Size` 0 cierra la conexión
con un error en el registro. `run()` bloquea hasta que LFS cierra o se pulsa Ctrl+C; sin
reconexión todavía (W3.6) y sin keep-alive (W3.5).

**Decisiones** (de API, en `API_DESIGN.md`, «Precisado al escribir `InSim`»): firma de `InSim`;
`send()` normal que lanza `ConnectionError` sin conexión (*descartado:* descartar en silencio);
`connect`/`close`/`wait_closed`/`connected` para quien tiene su propio bucle; **al cerrar se
cancelan los manejadores `async` que siguen esperando** (*descartado:* esperarlos). La constante
`INSIM_VERSION = 10` va escrita a mano en `_connection.py`: el generador no emite constantes.

**Diagnóstico (§8):** con la mutación «solo el primer manejador», los tests se colgaban en vez de
fallar. Causa raíz: `close()` esperaba a los manejadores `async`, y uno esperaba un evento que
nunca llegaba, así que `close()` (y el Ctrl+C) no volvía nunca. Test nuevo
(`test_closing_cancels_async_handlers_that_are_still_waiting`), visto en rojo, y arreglo: `close()`
los cancela.

**Red:** `tests/test_insim.py`, 12 tests contra el `FakeLFS`, más uno de `run()` con el LFS falso
en otro hilo. Mutaciones de `_connection.py` (7): todas en rojo al final. «Errores `async` sin
registrar» seguía en verde porque asyncio también escribe el error en el registro («Task exception
was never retrieved»); el test se hizo más estricto (exige el aviso de `lfs_insim` con el nombre del
manejador) y entonces sí falla. *Corrección de un test (§5), con su motivo:* era demasiado laxo.
- Tropiezo propio: en la prueba del cuelgue, la copia de seguridad de `_connection.py` fue a
  `$TMPDIR` y la restauración buscó en el scratchpad; se restauró a mano desde `$TMPDIR` y se
  comprobó que no quedaba la mutación (archivo sin seguimiento en git: `git diff` no lo habría
  visto).

**Verificación:** `.venv/Scripts/python scripts/verify.py` → PASS (220 passed, 1 deselected).

**Commits:** uno. CI de GitHub en verde.

**W3.5 — mantener viva la conexión** (en `_connection.py`):
- Un `IS_TINY` con `SubT` `TINY_NONE` y `ReqI` 0 se contesta igual, como pide InSim.txt; los
  manejadores lo siguen recibiendo.
- Sin datos durante `SILENCE_TIMEOUT` (70 s, lo mismo que espera LFS) la conexión se da por muerta,
  con un aviso en el registro. El tiempo es el atributo interno `_silence_timeout`, que los tests
  acortan. *Descartado:* un parámetro público (D6: la superficie, pequeña; nadie lo ha pedido).
- `close()` envía `TINY_CLOSE` si sigue conectado; si LFS ya se fue, no envía nada.
- **Red:** 5 tests nuevos en `tests/test_insim.py`; 3 en rojo antes del código (los otros dos
  vigilan que el cambio no rompa nada: datos que mantienen viva la conexión, cerrar tras irse LFS).
  4 mutaciones, todas en rojo. El script de mutaciones se escribió primero con un heredoc y las
  barras invertidas lo rompieron (la cicatriz de §13, otra vez): se rehízo con Write.
- **Verificación:** `verify.py` → PASS (225 passed, 1 deselected). CI en verde.

**W3.6 — reconexión** (en `_connection.py`): `async with insim:` y `run()` arrancan un supervisor
(`_keep_connected`) que conecta, llama a `@insim.on_connect`, espera a que la conexión se corte y
vuelve a intentarlo con `RETRY_DELAYS` (1, 2, 4, 8, 10 s; el último se repite). `connect()` queda
como un solo intento. `close()` para el supervisor antes de despedirse. Los manejadores de paquetes
y de `on_connect` comparten `_call` (errores aislados, `async` como tareas). Decisiones de API en
`API_DESIGN.md` («Reconexión»), con lo descartado.
- **Cambio de un test (§5), con su motivo:** `test_run_blocks_until_lfs_closes_the_connection`
  describía el comportamiento que W3.6 cambia a propósito (`run()` terminaba al cerrar LFS; ahora
  reconecta, como ya decía el ejemplo 1 de `API_DESIGN.md`). Sustituido por
  `test_run_reconnects_and_returns_when_closed`, que corre `run()` en un hilo con límite de tiempo:
  un `run()` que no vuelve falla en vez de colgar la ejecución de tests (y el CI).
- **`FakeLFS`:** `start()`/`stop()` en el mismo puerto, para parar y volver a arrancar LFS. Y un
  defecto suyo: `stop()` podía colgarse si un programa se conectaba justo entonces
  (`server.wait_closed()` espera a todas las conexiones aceptadas). Ahora deja de aceptar antes de
  cortar y rechaza las conexiones que lleguen durante el cierre.
- **Diagnóstico (§8):** las mutaciones dejaron ver tres cosas. (1) «Avisar en cada intento» seguía
  en verde: en Windows un intento rechazado tarda ~2 s, así que en el test solo fallaba uno; el
  test nuevo simula intentos fallidos instantáneos (`monkeypatch` de `asyncio.open_connection`).
  (2) Con «`on_connect` nunca se llama», `run()` no volvía y la ejecución se colgaba: de ahí el
  hilo con límite. (3) «`close()` sin `supervisor.cancel()`» colgaba por la propia mutación: dejaba
  la espera al supervisor, que reconecta para siempre (hipótesis «el falso se cuelga al pararse»:
  cierta, pero no era esto; refutada con un script que volcaba las tareas pendientes). La mutación
  realista (olvidar el supervisor sin pararlo) la detecta el test ampliado de salir de
  `async with`, que exige que no haya más conexiones después de cerrar.
- `test_waits_for_lfs_to_start` esperaba un tiempo fijo y fallaba en Windows por los ~2 s de un
  intento rechazado: ahora espera a ver el aviso.
- **Red:** 8 tests nuevos de reconexión; 7 en rojo antes del código. 5 mutaciones, todas en rojo.
- **Verificación:** `verify.py` → PASS (233 passed, 1 deselected).

## S9 — 2026-10-12 — W3 detallada con el usuario; pruebas con el LFS real; copia de setups y skins

**Hecho:**
- **W3 detallada** en `PLAN.md`: W3.2 (partir el flujo TCP), W3.3 (LFS falso), W3.4 (`InSim`
  básico), W3.5 (mantener viva la conexión), W3.6 (reconexión), W3.7 (OutSim/OutGauge y `run`),
  W3.8 (`every`), y W3.1 (prueba en vivo) al final.
- **Copia de los setups y las skins de LFS** (`setups`, `skins` y `skins_dds` de `C:\LFS\data`;
  49, 3 y 108 archivos) en `C:\Users\pasca\proyectos\_archivo_AP_LFS_InSim\LFS_backup_2026-10-12`,
  comprobada con `diff -rq` (idéntica). La pidió el usuario antes de reinstalar LFS.
- `PROTOCOL.md`: la copia pasa a «lo que nunca se debe perder»; permisos nuevos para abrir y cerrar
  LFS; el punto ciego se precisa.

**Decisiones (el usuario eligió las recomendadas):**
- `@insim.every()` va en W3 (W3.8): es parte del bucle de eventos. *Descartado:* llevarlo a W4.
- InSim por UDP, a «Ideas». El usuario cree que debería ser configurable, con TCP por defecto y
  `MCI`/`NLP` por UDP, pero prefiere pensarlo con calma. *Descartado por ahora:* solo `MCI`/`NLP`
  por UDP, o todo InSim por UDP.
- El relay de InSim, a «Ideas»: ninguna aplicación de la lista lo usa.
- **Pruebas con el LFS real** (propuesta del usuario): el agente puede abrir LFS y conectarse, así
  que comprueba él mismo lo que se ve como paquetes, y W3.1 deja de ser una tarjeta del usuario.
  El LFS falso se queda para el CI (no tiene LFS) y para los casos raros. Permisos acordados: abrir
  `LFS.exe` y cerrarlo con `/exit` por InSim, solo si no había otro abierto y sin matar el proceso;
  cambiar `cfg.txt`, solo con permiso y cambio a cambio.
- El usuario reinstala LFS (U5) porque la instalación tiene cosas que no son del juego:
  `data/script/autoexec.lfs` con `/insim=29999`, que cree que puso un programa InSim que instaló.

**Verificación:** solo documentación; no hay código que verificar.

**Commits:** uno, con todo lo anterior.

**Después del commit — reinstalación de LFS (U5, la hizo el agente a petición del usuario):**
- Descargado `LFS_S3_8C31_setup.exe` (1,74 GB) desde lfs.net con la sesión del usuario en Chrome.
  Era la misma versión instalada (0.8C31, la «nueva gráfica» en prueba pública). El instalador no
  está firmado (LFS nunca lo ha hecho); es NSIS.
- `UninstallLFS.exe /S` salió con 0 sin borrar ningún archivo. Se movió todo `C:\LFS` a
  `C:\LFS_old_2026-10-12` para no borrar nada; el usuario borró después esa carpeta él mismo.
- Instalado con `/S /D=C:\LFS`. El instalador deja las texturas y los circuitos en
  `C:\LFS\inst_tmp\*.7z` y es **`LFS.exe` quien los descomprime al abrirse la primera vez** (~75 s).
- En el juego limpio, `data/script/autoexec.lfs` solo tiene comentarios: el `/insim=29999` lo
  había puesto otro programa (en el registro hay una aplicación «LFS SpeedMonitor Core»; no se ha
  tocado). InSim no escucha hasta que se active.
- Un `du` sobre `C:\LFS` lanzado por el agente siguió en segundo plano tras su tiempo límite y
  bloqueó la carpeta (Windows negó el renombrado) → cicatriz en §13.
- A petición del usuario, setups y skins devueltos desde la copia sin sobrescribir nada. Solo
  chocaba `setups/FBM_RACE_blackwood.set`, distinto del que trae el juego; se dejó el del juego a
  la espera de que el usuario decida. **Decidió no cambiarlo:** se queda el del juego.

**W3.2 — partir el flujo TCP en paquetes:** `src/lfs_insim/_stream.py`, clase interna
`PacketStream` con `feed(bytes) -> list[InSimPacket]`. Usa el `unpack_insim()` que ya había en
`_codec.py`. Un paquete que no se puede leer (tipo desconocido, bytes que no encajan) se registra
con `logging` (logger `lfs_insim`, nombrando el paquete: `IS_VER (type 2, 4 bytes)`) y se salta;
un error inesperado de un codec, igual, pero con su traza.
- *Decisión (corrige el plan, dicha al usuario antes de escribir):* el plan decía que un tamaño
  imposible se salta, pero el único imposible es `Size` 0, y entonces no se sabe dónde empieza el
  paquete siguiente. `feed` lanza `PacketError` y la conexión (W3.4/W3.6) se rehace.
  *Descartado:* buscar el siguiente paquete válido byte a byte (adivinaría, y un falso positivo
  entrega basura como si fuera un paquete).
- **Red:** `tests/test_stream.py`, 10 tests (un paquete, varios, partido, byte a byte, tipo
  desconocido, mal formado, `Size` 0). En rojo antes del código; el del mensaje del registro, en
  rojo también con la primera versión (decía «type 2» sin nombre).
- **Verificación:** `.venv/Scripts/python scripts/verify.py` → PASS (198 passed, 1 deselected).
  Aviso previo, sin cambio: `_codec.py` tiene 525 líneas (límite 500).

**W3.3 — el LFS falso:** `tests/fake_lfs.py`, clase `FakeLFS` (`async with FakeLFS() as lfs`,
puerto libre en 127.0.0.1). Hace solo lo que dice InSim.txt: `IS_VER` tras un `IS_ISI` con `ReqI`;
`TINY_VER` → `IS_VER`, `TINY_PING` → `TINY_REPLY`; `TINY_CLOSE` cierra; `keepalive` y `timeout`
configurables (LFS: 30 s y 70 s). Apunta lo recibido (`received`, `wait_for`), y tiene `send`,
`send_raw` (bytes rotos) y `drop` (LFS que se cae).
- *Suposición, no está en InSim.txt:* una contraseña de administrador equivocada cierra la
  conexión sin respuesta. Se comprueba en el LFS real en W3.1.
- Sin dependencias nuevas: los tests usan `asyncio.run` (*descartado:* `pytest-asyncio`, que no
  hace falta para esto).
- **Red:** `tests/test_fake_lfs.py`, 10 tests con un cliente TCP mínimo. Pasaron a la primera, así
  que se comprobaron con 7 mutaciones del falso (ping sin `ReqI`, sin comprobar la contraseña,
  `TINY_CLOSE` ignorado, `IS_VER` sin `ReqI`, sin keep-alive, sin timeout, `wait_for` que repite):
  las 7 en rojo.
- **Verificación:** `verify.py` → PASS (208 passed, 1 deselected).

## S8 — 2026-10-12 — `IS_BTN.Caption` (W2.10), `IS_MSO.TextStart` (W2.11): W2 cerrada

**Hecho:**
- **W2.10 (P7):** `IS_BTN` tiene un campo `Caption`. Si no está vacío, se envía
  `0 + Caption + 0 + Text`, como dice InSim.txt; al leer, un texto que empieza por cero se separa
  en los dos. Excepción `CAPTIONS` en `spec_overrides.py`; codecs `TailText(caption=)` y
  `FilledIn` (un campo sin bytes propios, que lee otro codec).
- **W2.11 (P8):** `IS_MSO.TextStart` es un índice en `Msg`. Al leer se decodifica el trozo anterior
  y se cuenta; al enviar se codifica y, si el codificador añade un cambio de página justo ahí, se
  apunta después (Scawen, post 460437: «excluding the codepage»). Excepción `TEXT_STARTS`; el
  generador se para si un campo dice «first character» y no está en ella. Codec `TextOffset`.

**Decisiones:** U3 y U4: el usuario eligió las opciones recomendadas. `Caption` como campo aparte
(*descartado:* que cada uno ponga los ceros dentro de `Text`); `TextStart` arreglado en el paquete
(*descartado:* dejarlo en bytes y resolverlo en W4). Anotado en `API_DESIGN.md` (D3).

**Red:** 6 tests nuevos en `tests/test_text.py`, con el ejemplo de InSim.txt (`ABC`/`DEFG`) y un
nombre con un carácter japonés y `^L` añadidos por LFS; 5 fallan con el código de S7.

**Verificación:** `.venv/Scripts/python scripts/verify.py` → PASS (188 passed, 1 deselected).

**Commits:** W2.10, W2.11 y cierre, en uno.

## S7 — 2026-10-12 — Texto de LFS ↔ `str` (W2.9)

**Hecho:**
- **`packets/_text.py`**: lee y escribe las 10 páginas de códigos de InSim.txt. Al leer quita
  `^L`, `^E`…; al escribir añade un cambio solo cuando la página actual no tiene el carácter
  (primero las de un byte, para que el cirílico sea `^C` y no `^J`). Lo que no está en ninguna
  página pasa a `?`. En las páginas de dos bytes recorre carácter a carácter: el segundo byte puede
  ser `^` (0x5E). `^8` vuelve a la página original y `^:` a Latin-1, y los dos se quedan en el `str`.
- **`IS_MSO`**: el texto empieza en la página de `MSOData & 0x0f`. Excepción nueva
  `TEXT_CODE_PAGES` en `spec_overrides.py`; el generador se para si un campo dice «code page» y no
  está en ella. `TailText` acepta `code_page=`.
- **`lfs_insim.text.strip_colours()`** (público).
- **Fuentes** (regla de §15, leídas en Chrome con la sesión del usuario): Scawen, hilo «Any urgent
  InSim requests?», post 460437 (2007): «^9 original colour, ^8 original colour and code page, ^:
  original colour and Latin-1»; notas de 0.8C27, post 2177567 (2026): página del mensaje en
  `IS_MSO`, y sin `ISF_MSO_COLS` el `^8` se convierte en `^L`, `^E`… Los escapes `^v`, `^d`… no
  tienen fuente de Scawen (solo otras bibliotecas); como se dejan tal cual, no dependemos de ellos.
- **Encontrado:** P7 (`IS_BTN` con título) y P8 (`TextStart`), como W2.10 y W2.11. Sus
  decisiones, como U3 y U4 en `USER_ACTIONS.md`.

**Decisiones:** en el `str` se quitan los cambios de página y se dejan los demás `^` (el usuario
aceptó la propuesta). *Por qué:* son un detalle de la codificación; convertir `^^` en `^` y dejar
`^1` haría ambiguo `"^1"`. *Descartado:* el texto limpio con los colores aparte.

**Red:** 22 tests nuevos (`tests/test_text.py`); 11 fallan con el `_text.py` anterior. Mutaciones:
sin los bytes iniciales de dos bytes falla el test del 0x5E; sin `TEXT_CODE_PAGES` el generador se
para. Que funcione en el LFS real es punto ciego (W3.1).

**Verificación:** `.venv/Scripts/python scripts/verify.py` → PASS (183 passed, 1 deselected).

**Commits:** W2.9 y cierre, en uno.

## S6 — 2026-10-12 — Segunda opinión frente al proyecto anterior (W2.8) y `CName` de los mods (P6)

**Hecho:**
- **W2.8:** un script de un solo uso (en el scratchpad de la sesión, no en el repositorio) vuelca
  la disposición byte a byte de cada clase del proyecto anterior (`refactor/estabilizacion`,
  extraído con `git archive`) y del nuevo, y las compara: tamaño fijo, tipo de cada byte, cola
  variable y nombres de campo. **70 de 85 clases idénticas.** Las diferencias, revisadas una a una
  contra InSim.txt:
  - **Errores del proyecto anterior, bien en el nuevo:** `IS_CSC` llevaba `UCID` donde la
    especificación dice `PLID`; `IS_LAP` e `IS_SPX` tenían `PLIP`; `IS_ISM` tenía `Hname` e
    `IS_RES` tenía `Cname`, `Pname` y `Uname`; `IS_SET` era de tamaño variable, pero mide 136 fijos
    (`Setup[120]`); `OutGaugePack` no tenía el `ID` final opcional (92 frente a 96).
  - **Cambios a propósito:** `IS_MSO` tiene `MSOData` donde antes había `Zero` (0.8C27, W2.9);
    `OutSimPack2` usa `Magic` en lugar de `L`, `F`, `S`, `T` (S5); las colas variables tienen ahora
    el máximo de la especificación (MCI 16, NLP 48, PLH 48, AXM 60, MAL 120, IPB 120), que antes no
    se limitaba; `IS_IPB.BanIPs` son `IPv4Address` en lugar de 4 bytes.
  - Solo en el anterior: `IS_NONE` (un marcador, no un paquete) y `Vec`/`Vector`, que en el nuevo
    están en `_types.py`, fuera del volcado. Coinciden byte a byte dentro de OutSimPack.
- **`CName` de los mods (P6):** InSim.txt solo dice «skin prefix», y ni la documentación local de
  LFS ni el proyecto anterior lo resuelven. La fuente es el hilo «New InSim packet size byte and
  mod info» del foro de lfs.net. Primero se leyó solo el extracto del buscador, porque el foro pide
  sesión; después el usuario inició sesión y se leyó en Chrome el post de Scawen y su respuesta a
  una pregunta. Para un mod, `CName` es el SkinID como entero de 32 bits con el byte alto a cero,
  en orden de bytes de Intel, y su valor en hexadecimal es el ID del mod. Su ejemplo (`_A3` = mod
  `33415F`; `XRZ` = coche oficial, quizá futuro) está en los tests. Un coche oficial se reconoce porque sus
  tres primeros bytes son letras o cifras ASCII. Con el código de S5, los SkinID 0x8D0A90, 0x100081
  y 0x5A0012 se perdían al ir y volver. Arreglado con los codecs `CarName` y `SkinID` en `_codec`,
  y las excepciones `CAR_NAMES` y `SKIN_IDS` en `spec_overrides.py`. El generador se para si un
  campo dice «skin prefix» o «SkinID» y no está en ellas. La docstring de `CName` explica las tres
  formas.

**Decisiones:**
- **`CName` es un `str`: `"XFG"` (oficial), `"5A1FB3"` (mod) o `""` (sin coche).** El usuario
  eligió la opción recomendada. *Por qué:* siempre el mismo tipo; es como LFS y lfs.net enseñan el
  ID de un mod, y no hay ambigüedad (3 caracteres frente a 6). Al empaquetar se aceptan minúsculas
  y se rechaza un SkinID cuyos bytes parecerían un coche oficial (`5A5A5A` → `ZZZ`): LFS nunca los
  emite, y se volvería a leer como otro coche. *Descartado:* `str` o `int` según el coche (obliga a
  usar `isinstance`) y los bytes crudos.
- **`IS_MAL.SkinID` es una lista de `str` con el mismo formato**, para que funcione
  `npl.CName in mal.SkinID`. El usuario eligió la opción recomendada. *Descartado:* dejarlo `int`,
  como dice la especificación, porque cada aplicación tendría que convertir.
- Ambas quedan en `API_DESIGN.md` (D3, precisión de S6). **Cambia la API pública** de `IS_SLC`,
  `IS_NPL`, `IS_RES`, `IS_SET` e `IS_MAL`; no se ha publicado nada, así que no rompe a nadie.

**Red:** los tests nuevos se vieron en rojo antes del arreglo. Después se comprobaron con dos
mutaciones: sin `CName` en `CAR_NAMES`, el generador se para; sin el control de ambigüedad, falla
`test_car_name_rejects_what_is_neither[5A5A5A]`. Que funcione con un mod en el LFS real es punto
ciego: se añade a W3.1.

**Verificación:** `.venv/Scripts/python scripts/verify.py` → PASS (environment, lint, format,
types, tests: 159 passed, 1 deselected; generated).

**Commits:** W2.8 + P6 y cierre, en uno.

## S5 — 2026-10-12 — OutSim y OutGauge generados (W2.5), W2.6 completa y control del código generado (W2.7)

**Hecho:**
- **W2.5:** el generador escribe además `_outsim.py` (`OutSimPack` de InSim.txt; `OutSimMain`,
  `OutSimInputs`, `OutSimWheel` y `OutSimPack2` de OutSimPack.txt) y `_outgauge.py`
  (`OutGaugePack`). `OG`, `DL` y `DLF` ya estaban en `_enums.py`; el enum `OSO` se define en
  `_outsim.py` (ver W2.7).
  - Núcleo (`_codec`): `Options` (las opciones, campo sin bytes), `When` (parte presente solo si
    una opción está activa), `Magic` (bytes fijos comprobados al leer) y la clase base
    `OptionalParts`, cuyo `unpack(data, options)` exige las opciones y el tamaño exacto.
  - Excepciones nuevas en `spec_overrides.py`: `MODULES` (sustituye a `NOT_INSIM`),
    `OPTIONAL_TAIL` (el `ID` final de OutSim y OutGauge), `MAGIC` (`"LFST"`), `OPTIONS_FIELD` y la
    docstring de `OSO`. Las condiciones `// if (OSOpts & OSO_x)` no son excepciones: salen de la
    especificación (el lector ya las guardaba desde W2.1).
  - El generador se para si un campo dice «optional - only if» y no está en `OPTIONAL_TAIL`
    (comprobado quitando la entrada de OutGaugePack).
- **W2.6 completa:** tamaños (OutSim 64/68, OutGauge 92/96, `OutSimWheel` 40 por «10 ints»,
  OutSimPack2 280 con todo, como dice OutSimPack.txt, y cada parte por separado), ida y vuelta de
  todas las clases, bytes hechos a mano de los tres paquetes y errores (sin opciones, opciones de
  más o de menos, `LFST` incorrecto, valores que no casan con las opciones). Visto en rojo
  quitando un relleno de la parte DRIVE y desactivando la comprobación de `When`.
- **W2.7:** `verify.py` tiene el paso `generated` (`generate_packets.py --check`; se salta sin
  `spec/cache/`, como en el CI). El workflow `spec` descarga la especificación y hace la misma
  comprobación; se lanza también al cambiar el lector, las excepciones, el generador o los
  paquetes. Visto en rojo editando a mano `_insim.py`, en modo completo y sin `OutSimPack.txt`; en
  GitHub, `spec` en verde ejecutando el paso, con `_outsim.py` y `__init__.py` saltados.
- La parte de enums del generador pasa a `scripts/generate_enums.py`: `generate_packets.py` había
  llegado a 504 líneas (aviso de P4).

**Decisiones:**
- **OutSimPack2 lleva sus opciones en un campo `OSOpts`** (el nombre de los comentarios de la
  especificación), que no viaja en los bytes, y **se lee con `OutSimPack2.unpack(data, opciones)`**.
  Las partes no enviadas son `None`. *Por qué:* los bytes no dicen qué partes llevan (la cabecera
  `LFST` también es opcional) y adivinarlas por el tamaño es ambiguo. Al empaquetar se exige que
  cada valor esté exactamente cuando su opción está activa. *Descartado:* deducir las opciones de
  los campos rellenos (la cabecera no tiene campos) y valores por defecto en vez de `None` (no se
  distinguiría «no enviado» de «cero»). La capa `OutSim(...)` de W4 recibirá las opciones una vez.
- **`L`, `F`, `S`, `T` son una sola marca fija** (`Magic`), no cuatro campos: siempre valen
  «LFST» y se comprueban al leer.
- **Sin `OutSimPack.txt`, el generador comprueba lo que sale solo de InSim.txt** (`_enums.py`,
  `_insim.py`, `_outgauge.py`) y dice qué se salta (`_outsim.py`, `__init__.py`). Era la
  recomendación del agente, y el usuario dijo «procede». *Por qué:* el CI no tiene OutSimPack.txt
  (P3), y así comprueba igualmente casi todo el código generado. *Descartado:* subir OutSimPack.txt
  al repositorio, porque el usuario no quiere la especificación copiada (S1).
- **`OSO` se define en `_outsim.py`, no en `_enums.py`.** Al principio iba con los demás enums,
  pero así `_enums.py` depende solo de InSim.txt y se comprueba en el CI. `OSO` sale de
  OutSimPack.txt y solo lo usa OutSimPack2. Se importa igual: `from lfs_insim.packets import OSO`.
  El generador rechaza un nombre de clase repetido entre los dos archivos.

**Problemas del agente:** volvió a usar un heredoc con `\` para parchear el generador (cicatriz de
§13, ya escrita) y el archivo quedó roto. Se restauró desde git y se rehízo con Edit, sin pérdidas.

**`ruff` fijado a `>=0.17,<0.18`** en el grupo `dev` de `pyproject.toml`. Lo recomendó el agente y
el usuario dijo «haz lo que recomendaste». *Por qué:* el código generado pasa por `ruff format`, y
una versión nueva podría poner en rojo `spec` y `verify` sin ningún cambio nuestro. Se fija la
versión menor, porque ruff cambia el estilo de formato en las versiones menores. *Para subirla:*
cambiar el límite, regenerar y revisar el diff.

**Verificación:** `.venv/Scripts/python scripts/verify.py` → PASS (environment, lint, format,
types, tests: 144 passed, 1 deselected; generated). En GitHub, `verify` y `spec` en verde.

**Commits:** W2.5 + W2.6 (`048fcca`), cierre parcial (`913c608`), W2.7 (`5873c14`), cierre (`99e1f1b`), `ruff` fijado y el de cierre.

## S4 — 2026-10-12 — U2 (dev en main), W2 detallada y paquetes de InSim generados (W2.1–W2.4)

**Hecho:**
- **U2 cerrada:** el usuario dijo «sí, sigamos tu recomendación». `main` avanzó en modo rápido de
  `563a891` a `c97e62d` (era antecesor directo de `dev`: sin merge commit ni force-push). En `main`,
  `verify` y `spec` en verde tras el push, y `spec` también lanzado a mano (workflow_dispatch).
- **W2 detallada** en `PLAN.md` (W2.1–W2.9) a partir de un inventario de la especificación: 81
  structs, 30 enums, 125 `#define`, 16 constantes y 3 listas de valores que solo aparecen en
  comentarios (CS_, HOSTF_, AXO_).
- **W2.1:** `scripts/spec_parser.py`. Lee los dos archivos enteros y falla, con el número de línea,
  ante cualquier construcción desconocida. Visto en rojo estropeando la numeración de los enums y el
  control de tipos.
- **W2.3:** `src/lfs_insim/packets/_codec.py` (escrito a mano). Incluye `Size` ÷4 y `Type`
  automáticos, relleno, texto fijo y al final del paquete, arrays fijos, contados o que llenan el
  paquete, un final opcional, `unpack_insim()` y `PacketError`. Además, `_types.py` (`Vec`, `Vector`)
  y `_text.py` (cp1252 provisional). Visto en rojo estropeando el relleno a 4 bytes y el cálculo de
  `Size`.
- **W2.2 y W2.4:** `scripts/spec_overrides.py` y `scripts/generate_packets.py`, que escriben
  `_enums.py` (51 clases), `_insim.py` (81 structs) y `__init__.py`. El generador pidió por sí solo
  las excepciones que faltaban (`PENALTY_30`, `JRR_2`…, `OCO_1`…), y así se comprobó que no deja
  pasar nada en silencio.
- **W2.6 (InSim):** `tests/test_packets.py` cubre:
  - ida y vuelta de todas las clases, con valores por defecto y con valores distintos en cada
    campo;
  - que cada valor de `ISP` tiene su clase;
  - los tamaños de 76 structs contra los comentarios de la especificación (fijos, rangos, fórmulas
    `4 + NumC * 28` y «in 28 bytes»), con la lista de las 5 que no declaran tamaño;
  - bytes hechos a mano de `IS_TINY` (keepalive), `IS_ISI`, `IS_MST` e `IS_MCI`.

  Visto en rojo cambiando `CompCar.Heading` de `H` a `I` y un relleno de `IS_NPL`.

**Decisiones:**
- **Enums y flags como clases (`TINY.NCN`)**, el código generado en git (cierra la decisión
  pendiente de P3) y el texto como `str` con la codificación de LFS en W2. Las tres, aprobadas por
  el usuario tal como las recomendó el agente. D3 se precisó en `API_DESIGN.md`. *Descartado:*
  constantes sueltas (`TINY_NCN`), que son cientos de nombres sin tipo; generar al construir, que
  exigiría red y LFS para OutSimPack2; y usar `bytes` en W2, con lo que el Ejemplo 1 no funcionaría
  hasta W4.
- **Los campos que usan un enum siguen siendo `int`**, para no inflar W2. Se enlazarán en W4 si una
  aplicación lo pide.
- **Los `#define` se agrupan por bloques seguidos y se separan por prefijo**, porque un mismo
  bloque mezcla LCS/LCL, PIF/RIF e INST/ISB. Cuando dos grupos tienen el mismo prefijo (ISB, PMO,
  OCO), uno se renombra en las excepciones: `ISB_CLICK`, `PMOF`, `OCO_INDEX`.
- **Un grupo es `IntFlag` si todos sus valores son bits o combinaciones de ellos; si no, es
  `IntEnum`.** Los enums de C son siempre `IntEnum`. PSE y DL guardan la posición del bit, tal como
  la especificación.
- **Los codecs se usan en el código generado como `_c.Text`, `_c.Scalar`…**, porque el campo
  `Text` de `IS_BTT` tapaba la clase `Text` dentro del cuerpo de la clase (mypy: «str not
  callable»).
- **El registro de tipos para `unpack_insim()` es explícito (`register(...)`) y rechaza un `Type`
  duplicado.** Con el registro automático, las clases de prueba de `test_codec.py`, que tenían los
  mismos `Type` que las reales, las sustituían: 5 tests fallaron solo en la ejecución completa.
- **El aviso de tamaño (P4) no cuenta los archivos generados.** Su tamaño viene de la
  especificación, no de una decisión de diseño. `_enums.py` (E741 por `MSO.O`) es la única
  excepción de lint.
- `Plate[8]` se trata como texto sin cero final, porque así lo dice la especificación (NO ZERO AT
  END). Los campos con «last byte» reservan el último byte para el cero. Queda pendiente para W2.8:
  comprobar si `CName` lleva un SkinID binario en los mods.

**Problemas del agente:**
- `ruff format scripts` reformateó los scripts del protocolo y entraron en el commit `bdec24f`. Se
  restauraron en `4163c05`, y quedó como cicatriz nueva en §13.
- Volvió a aparecer la trampa de las barras invertidas en heredocs (§13); se amplió la cicatriz.

**Verificación:** `.venv/Scripts/python scripts/verify.py` → PASS (environment, lint, format, types,
tests: 131 passed, 1 deselected). `generate_packets.py --check` → al día. GitHub: `verify` en verde
en los 5 pushes de `dev`, y `verify` y `spec` en verde en `main`.

**Commits:** plan de W2 y U2 (`0f09a8b`), W2.1 (`d4b2d07`), W2.3 (`0930b67`), W2.2+W2.4
(`bdec24f`), restauración de los scripts del protocolo (`4163c05`) y el de cierre.

## S3 — 2026-10-12 — CI en GitHub Actions y script de la especificación: W1 cerrada

**Hecho:**
- **W1.3:** `.github/workflows/verify.yml` ejecuta `scripts/verify.py` en Python 3.11, 3.12, 3.13 y
  3.14, en `ubuntu-latest` y `windows-latest`, en cada push a `dev`/`main` y en cada pull request.
  Las 8 combinaciones, en verde. La primera ejecución avisó de que `checkout@v4` y
  `setup-python@v5` usan Node 20, que está obsoleto. Se subieron a v5/v6, y en la segunda el aviso
  ya no aparece.
- **W1.4:** `scripts/fetch_spec.py` descarga https://www.lfs.net/programmer/insim, extrae el único
  bloque `<pre>` (con las entidades HTML convertidas y saltos de línea LF) y lo guarda en
  `spec/cache/InSim.txt`. También lee `C:\LFS\docs\OutSimPack.txt`, si existe, y lo copia a
  `spec/cache/`. La versión comprobada queda en `spec/checked.json`, en git: 0.8C27,
  INSIM_VERSION 10 y la huella SHA-256 de cada texto. Sale con 0 si coincide, 1 si ha cambiado y
  2 si no puede leer una fuente; en ese último caso no toca la copia anterior. `--accept`
  registra lo descargado.
  Tests sin red para la extracción, más un test con el marcador `network`, que se salta por defecto
  y compara lfs.net con `checked.json`. El workflow `spec.yml` lo ejecuta cada lunes y en cada push
  que cambie el script, `checked.json` o el propio workflow.
- **Comprobación de la extracción:** comparada con el `docs/InSim.txt` del proyecto anterior, solo
  difieren 40 líneas, que son las de 0.8C27 señaladas en P2. No queda ninguna entidad HTML.
- **Visto en rojo:** con una huella falseada en `checked.json`, el script salió con 1 y el test de
  red falló. Con una URL que no existe salió con 2 y la copia de `spec/cache/` quedó idéntica
  (misma SHA-256). Restaurado, todo volvió a verde.
- **LOG.md reordenado:** S2 se había añadido al final, aunque la regla es poner lo más nuevo arriba,
  así que `ctx_log_last.py` devolvía S1. Se puso S3 arriba y S2 delante de S1, sin cambiar ninguna
  línea (comprobado comparando las líneas antes y después).

**Decisiones:**
- **Windows en el CI**, aunque W1.3 solo pedía versiones de Python, porque es donde corre LFS y donde
  la usará casi todo el mundo. No cuesta nada.
- **La huella es del texto extraído y normalizado, no del HTML**, para que un cambio en la cabecera
  o el menú de la web no dé un falso aviso.
- **El aviso de lfs.net no forma parte de `verify.py`**, porque lfs.net no siempre responde (§13) y
  la verificación local no debe depender de la red. Va en un test `network` que se salta por
  defecto, y lo ejecuta un workflow propio.
- **El workflow programado solo funciona desde `main`** (es una limitación de GitHub). Se añadió el
  disparador por push, que de paso demostró que lfs.net responde a los servidores de GitHub
  (ejecución `spec` en `400ee65`, en verde). Para activar el aviso semanal hay que fusionar en
  `main`, y eso queda como **U2** (decidir).
- **El CI no se ha visto en rojo a propósito.** No tiene pasos propios: falla si y solo si
  `verify.py` sale con un código distinto de 0, y eso ya se vio en S2. Comprobarlo exigiría crear y
  borrar una rama con un fallo, y borrar ramas necesita permiso. Se informó al usuario.

**Verificación:** `.venv/Scripts/python scripts/verify.py` → PASS (environment, lint, format, types y
tests: 10 passed, 1 deselected). `pytest -m network` → 1 passed. GitHub: `verify` en verde (8/8) en los
cuatro pushes de la sesión, y `spec` en verde en `400ee65`.

**Commits:** CI (W1.3), acciones con Node 24, script de la especificación (W1.4), disparador por
push del workflow `spec` y el de cierre.

## S2 — 2026-10-12 — Paquete vacío, comando de verificación, licencia y diseño de la API

**Hecho:**
- **U1 cerrada:** el usuario eligió **MIT**, la recomendación del agente. Se añadieron `LICENSE`
  (Copyright 2026 Adrian Pascarella), la declaración en `pyproject.toml` y una línea en el README.
- **W1.1:** `pyproject.toml` (`lfs-insim` 0.0.0, Python ≥ 3.11, sin dependencias, construido con
  hatchling), `src/lfs_insim/` con `__version__` y `py.typed`, y un `.venv` propio con Python 3.14.
- **W1.2:** `scripts/verify.py`. **Visto en rojo:** con un archivo temporal que tenía un import sin
  usar, un `type X = int` (Python 3.12), un retorno mal tipado, una función sin anotar y mal
  formateada, un test que fallaba y un archivo de 600 líneas, fallaron lint, formato, tipos y tests
  por esos motivos, y saltó el aviso de tamaño. La sintaxis de 3.12 la detectaron tanto ruff como
  mypy (P5). Con el `python` de streamer-project falló el control de entorno. Después de retirar
  los defectos y borrar `__pycache__`, todo volvió a verde.
- **W1.5:** `docs/dev/API_DESIGN.md`, con tres ejemplos de uso y las decisiones D1–D6. Antes se
  revisó cómo se escribía una aplicación en el proyecto anterior (subclase de `InSimApp` con
  métodos `on_<paquete>` e hilos), para contrastar.

**Decisiones:**
- **D1 — asyncio por dentro, `def` o `async def` por fuera, `insim.run()`** (aprobada). El porqué:
  es la forma de FastAPI, que citó el usuario; quien no sabe `async` no lo ve, y sin hilos
  desaparecen la cola, los locks y el hilo de despacho del proyecto anterior. Se descartaron los
  hilos y una API solo `async`.
- **D2 — `@insim.on(IS_MSO)`** (aprobada), porque da tipos y autocompletado. Se descartó la
  subclase con `on_mso`, que ignora en silencio un nombre mal escrito.
- **D3 — Los nombres de la especificación** (`IS_MST(Msg=...)`, `packet.PLID`) (aprobada), para
  que coincidan con `InSim.txt` y el foro. Lo pitónico va en la capa alta. Se descartó `snake_case`.
- **D4 — `Roster`, estado opcional dentro de la biblioteca** (aprobada). Cierra la discrepancia
  que quedó abierta en S1.
- **D5 (OutSim y OutGauge con la misma forma y `run(...)` para varios) y D6 (superficie pública
  pequeña):** propuestas sin objeción.
- **Dependencias de desarrollo en `[dependency-groups]`** (PEP 735, `pip install --group dev`) y
  no en un extra: así no aparecen como opción de instalación para los usuarios de la biblioteca.
- **Aviso de tamaño a partir de 500 líneas, sin fallar**, como pedía W1.2. Si hace falta más mano
  dura, se convierte en fallo.
- **Trampa nueva (§13):** el `python` de la terminal es el `.venv` de streamer-project.

**Verificación:** `.venv/Scripts/python scripts/verify.py` → PASS (environment, lint, format,
types y tests: 2 passed). P1 queda resuelto.

**Commits:** `bfc3095` (esqueleto, verificación y licencia) y el de cierre, con los documentos y
`API_DESIGN.md`.

## S1 — 2026-10-12 — Reinicio desde cero: rama huérfana, protocolo nuevo (modo FRESH) y plan inicial
**Contexto.** La sesión se abrió desde streamer-project (su S14), que necesita esta biblioteca para
la cámara libre. El usuario contó la historia del repositorio: lo empezó a mano, fue añadiendo IA y
avanzó mucho más rápido, pero «más pronto que tarde perdí el hilo y el control». Decidió empezarlo
de cero en el mismo repositorio, en una rama nueva, «cogiendo lo único que sea realmente útil», y
borrar todo el contexto antiguo (el protocolo antiguo fue el origen de la skill agentic-protocol).

**Hecho:**
- **Revisión del proyecto anterior** (`refactor/estabilizacion`, 358 commits del 21/04 al 05/09,
  46 sesiones, 914 tests en verde). Capas: el protocolo (paquetes y enums, ~3.000 líneas, lo más
  valioso), la especificación (`docs/InSim.txt`, desfasada: P2), el núcleo (conexión, reconexión,
  cargador de módulos, CLI, ~3.500 líneas: valen las ideas, no el código) y las aplicaciones
  (`ai_control` y otras, ~14.000 líneas más unas 150.000 de mapas JSON: donde se perdió el control,
  P4).
- **Ramas.** Se dejó una etiqueta `archivo/<rama>` en cada una (subidas a GitHub) y se borraron, en
  local y en GitHub, `main`, `fix/radar-false-positive-behind` (con 4 commits únicos del editor de
  mapas, recuperables desde su etiqueta), `feat/map-ui-refinements`, `feat/prueba-botones-completo`,
  `feat/overtake-refactor`, `fix/ai-test-remove-oldest-own-ai`, `fix/ai-control-stability` y
  `docs/update-readme`. Antes, `refactor/estabilizacion` pasó a ser la rama por defecto en GitHub.
- **Identidad y credenciales locales:** el repo tenía en local el correo de Veloik (un commit
  antiguo salió con él). Ahora `AdrianPascarella <pascarellaadrian@gmail.com>` y el ayudante de
  credenciales con el token de `AdrianPascarella`, como en streamer-project.
- **Rama huérfana `main`** y limpieza de la carpeta: se borraron las cachés, `.venv` (254 MB),
  `.venv39` (217 MB) y `logs/` (17 MB). `config/settings_local.py` se movió a
  `C:\Users\pasca\proyectos\_archivo_AP_LFS_InSim\` (puede tener la contraseña de administrador).
- **Especificación.** Se comprobó que https://www.lfs.net/programmer/insim publica el `InSim.txt`
  entero dentro de un `<pre>` (3.203 líneas, versión 0.8C27) y que la copia antigua tenía 41 líneas
  de diferencia. OutSim y OutGauge clásicos están en esa página; OutSimPack2 solo en
  `C:\LFS\docs\OutSimPack.txt` (idéntico a la copia antigua).
- **Protocolo instalado en modo FRESH** (plantilla v3): `docs/dev` completo, scripts de inicio y
  cierre y `CLAUDE.md` con el arranque. Basado en la versión en castellano de streamer-project, con
  la configuración de este proyecto. Ningún código.

**Decisiones:**
- **Biblioteca primero, no framework** → el usuario quiere que se use «como una librería más de
  python, que se pueda hacer un import… como se haría un import matplotlib o un import FastAPI». Lo
  de framework (módulos, dependencias, CLI) solo si una aplicación real lo pide. Se descartó repetir
  el framework del proyecto anterior.
- **Nombre `lfs_insim`** (`pip install lfs-insim`) → minúsculas como manda la convención de Python;
  libre en PyPI el 12/10. Se descartaron `import AP_LFS_InSim` (contra la convención),
  `ap_lfs_insim` e `insim` (demasiado genérico).
- **Python ≥ 3.11** → todas las versiones con soporte; 3.9 ya no lo tiene y 3.10 lo pierde este mes.
- **Las aplicaciones (cámara libre, control de IA, gestión de usuarios, registrador) van aparte** →
  idea del usuario: crearlas con comodidad es la comprobación de que la biblioteca funciona. El
  agente estuvo de acuerdo y añadió `examples/` y un LFS falso para los tests. **Discrepancia del
  agente:** la gestión de usuarios (UCID ↔ PLID ↔ nombre) la necesitan casi todas las aplicaciones,
  así que propone que esté en la biblioteca como algo opcional. Queda para W1.5.
- **Especificación descargada, no copiada** → petición del usuario: «no quiero que esté puesta
  harcodeada en el proyecto, quiero que la coja de la página de lfs.net». El agente añadió que la
  biblioteca nunca la descargue al usarse (dependería de internet), solo en desarrollo, y que en
  git quede la versión comprobada. El usuario aceptó además **generar los paquetes** a partir de
  ella en vez de escribirlos a mano.
- **Rama huérfana** → arranca sin los 45 MB de historial, que sigue en `refactor/estabilizacion`.
- **Ramas borradas con etiquetas de archivo** → recuperables si algún día hacen falta.
- **Todo lo público en inglés** (código, docstrings, README, ejemplos); la documentación de trabajo,
  en castellano.
- **Punto ciego**: el LFS real, la comodidad de la API y la instalación en otro equipo. El usuario:
  «Iniciemos siendo precavidos y ya después iremos afinando».
- **Lo que nunca se pierde**: el archivo del proyecto anterior (rama y etiquetas).
- **Instrucción permanente** (§15): decirle siempre cuando algo se puede hacer mejor.

**Después de instalar:** el usuario dio permiso y `main` pasó a ser la rama por defecto en GitHub.
Pidió dejar indicadas las aplicaciones de prueba («las que necesitamos aquí y las que ya
estaban»), pero insistió: «en la biblioteca solo esté lo que será de la biblioteca y no se mezcle
con los insims que vamos a crear aparte». Se acordó: **una lista de requisitos, solo texto**, en
`PLAN.md` («Aplicaciones aparte»: gestión de usuarios, registrador, cámara libre, botones y control
de IA, con los paquetes que usaban o usan), y **la prueba en vivo del protocolo como test de la
biblioteca** (W3.1), que sustituye al `test_insim` antiguo y no es un InSim para el usuario.

**Verificación:** no hay comando de verificación (P1, W1.2). Control de cierre al final.

**Commits:** instalación del protocolo en `main` (primer commit de la rama huérfana); `dev` sale de
ahí.
