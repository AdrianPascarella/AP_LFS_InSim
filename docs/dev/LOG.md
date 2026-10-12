# 📓 Diario — AP_LFS_InSim (lfs_insim)
<!-- Solo se añade, lo más nuevo arriba. Una entrada por sesión. -->

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
