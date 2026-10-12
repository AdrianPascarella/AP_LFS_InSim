# 📓 Diario — AP_LFS_InSim (lfs_insim)
<!-- Solo se añade, lo más nuevo arriba. Una entrada por sesión. -->

## S5 — 2026-10-12 — OutSim y OutGauge generados (W2.5) y W2.6 completa

**Hecho:**
- **W2.5:** el generador escribe además `_outsim.py` (`OutSimPack` de InSim.txt; `OutSimMain`,
  `OutSimInputs`, `OutSimWheel` y `OutSimPack2` de OutSimPack.txt) y `_outgauge.py`
  (`OutGaugePack`). El enum `OSO` va a `_enums.py` con los demás; `OG`, `DL` y `DLF` ya estaban.
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
- **Un único `_enums.py`** para InSim, OutSim y OutGauge; el generador rechaza un nombre de clase
  repetido entre los dos archivos.
- **El generador necesita ahora también `OutSimPack.txt`.** Afecta a W2.7: el workflow `spec`
  solo descarga InSim.txt (P3), así que allí no se podrá regenerar todo. Se decide en W2.7.

**Verificación:** `.venv/Scripts/python scripts/verify.py` → PASS (environment, lint, format,
types, tests: 144 passed, 1 deselected). `generate_packets.py --check` → al día.

**Commits:** W2.5 + W2.6 (`048fcca`) y el de cierre.

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
