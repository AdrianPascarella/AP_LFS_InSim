# 📓 Diario — AP_LFS_InSim (lfs_insim)
<!-- Solo se añade, lo más nuevo arriba. Una entrada por sesión. -->

## S13 — 2026-10-13 — W5 detallada

**Inicio:** la sesión arrancó en `main`; el usuario pidió cambiar a `dev` (hecho, pull al día).

**Decisiones del usuario:** documentación en `README.md` + `docs/` en Markdown (sin MkDocs/Sphinx
por ahora); publicación con Trusted Publishing desde GitHub Actions; estado Alpha para 0.1.0.

**Hecho:** W5 detallada en `PLAN.md` (W5.1–W5.6). Aún no se ha tocado código. Anticipada la tarjeta
U6 (cuentas y publicador en TestPyPI/PyPI), que se abre al llegar a W5.4.

**Siguiente:** W5.1, README real.

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
