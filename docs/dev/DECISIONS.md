# 🧠 Decisiones — AP_LFS_InSim (lfs_insim)
> Las decisiones vigentes, una entrada cada una, la más nueva al final. Solo se añade: una decisión que
> deja de valer nunca se borra; gana una línea `SUSTITUIDA (S<n>) por D<m>` y la entrada nueva dice
> qué cambió. Se lee por tema (busca con grep la línea «Toca» desde las rutas que vas a cambiar), nunca
> entero.
>
> **Una sola numeración `D<n>` en el proyecto.** D1–D6 nacieron en S2 en `API_DESIGN.md` y conservan
> su número; allí siguen los ejemplos y el detalle de cada decisión de la API, y sus precisiones
> menores (la firma de `InSim`, `every`, `request`, `say`, los comandos, `plain`, `watch`, `Arg`…)
> viven solo allí, por sección. Las entradas de aquí dicen qué está decidido y apuntan a ese detalle.
> Sembrado en S31 (UPGRADE a la plantilla v4) con las decisiones de S1–S30 que siguen en vigor; cada
> una cita la sesión del `LOG.md` en que se tomó.

### D1 — asyncio por dentro, `def` o `async def` por fuera   [VIGENTE]
- **Decisión:** `insim.run()` arranca el bucle de eventos; un manejador puede ser `def` (rápido, en el
  bucle) o `async def` (puede esperar). Quien tiene su propio bucle usa `await insim.connect()` /
  `async with insim:`.
- **Por qué:** la forma de FastAPI, que citó el usuario; quien no sabe `async` no lo ve, y sin hilos
  desaparecen la cola, los locks y el hilo de despacho del proyecto anterior.
- **Descartado:** hilos como en el proyecto anterior (de ahí venía mucha de su complejidad) · una API
  solo `async` (obliga a todos a aprenderlo para un «hola»).
- **Tomada:** S2 (2026-10-12; aprobada por el usuario). Detalle: `API_DESIGN.md` «Decisiones
  propuestas» y «Precisado al escribir `InSim`».
- **Toca:** `src/lfs_insim/_connection.py`, `_run.py`, `_events.py`, `_handlers.py`.

### D2 — Manejadores con decorador y el tipo del paquete   [VIGENTE]
- **Decisión:** los manejadores se registran con un decorador que lleva el tipo del paquete; un
  paquete admite varios manejadores y el error de uno se registra sin parar a los demás. La forma
  canónica es `@insim.on.IS_NPL` desde S15 (D20); `@insim.on(IS_NPL)` sigue valiendo.
- **Por qué:** el editor sabe qué paquete llega y autocompleta; mypy detecta un manejador mal tipado.
- **Descartado:** subclase con métodos `on_mso` (lo del proyecto anterior: un nombre mal escrito se
  ignora en silencio y no hay tipos) · cadenas como `"MSO"`.
- **Tomada:** S2 (2026-10-12; aprobada por el usuario). Detalle: `API_DESIGN.md`.
- **Toca:** `src/lfs_insim/_handlers.py`, `_events.py`, `received.py`.

### D3 — Los paquetes, con los nombres de la especificación   [VIGENTE]
- **Decisión:** `IS_MST(Msg=...)`, `packet.PLID`; enums y flags como clases con el prefijo de C
  (`TINY.NCN`, `ISF.MCI`); `Size`, `Type` y el relleno los pone la biblioteca. Lo pitónico va en la capa
  de arriba (`packet.text`, `roster.players`, `insim.say()`). Precisiones: texto como `str` sin los
  cambios de página y con los demás `^` (S7); `CName` y `IS_MAL.SkinID` como `str` (`"XFG"`,
  `"5A1FB3"`, `""`; S6); `IS_BTN.Caption` aparte e `IS_MSO.TextStart` como índice del `str` (S8, U3/U4).
- **Por qué:** quien lee `InSim.txt`, el foro o un ejemplo en C encuentra lo mismo, y la generación es
  mecánica (D11).
- **Descartado:** `snake_case` (`req_i`, `plid`): cada nombre necesitaría una traducción · constantes
  sueltas (`TINY_NCN`): cientos de nombres sin tipo · `CName` como `str` o `int` según el coche · texto
  en `bytes`.
- **Tomada:** S2; precisada en S4, S6, S7 y S8 (2026-10-12; todas por el usuario, con la recomendada
  por el agente). Detalle: `API_DESIGN.md` D3.
- **Toca:** `src/lfs_insim/packets/`, `scripts/generate_*.py`, `scripts/spec_overrides.py`,
  `packets/_text.py`, `packets/_codec.py`.

### D4 — Estado de conexiones y jugadores, en la biblioteca y opcional (`Roster`)   [VIGENTE]
- **Decisión:** `lfs_insim.state.Roster`, opcional: quien no lo crea no paga nada. Desde S20 es un
  plugin más (D22).
- **Por qué:** casi todas las aplicaciones lo necesitan y es fácil hacerlo mal (reconexiones, cambios
  de nombre, IA sin conexión propia).
- **Descartado:** dejarlo a cada aplicación (cada una lo haría mal a su manera).
- **Tomada:** S2 (2026-10-12; aprobada por el usuario; resolvía la discrepancia del agente en S1).
- **Toca:** `src/lfs_insim/state.py`.

### D5 — OutSim y OutGauge, con la misma forma que InSim   [VIGENTE]
- **Decisión:** `OutGauge(port=...)`, `@gauge.on...`, y `run(...)` para varios a la vez. OutSimPack2 se
  lee con `OutSimPack2.unpack(data, opciones OSO)` y las partes no enviadas son `None` (S5).
- **Por qué:** son protocolos UDP independientes y muchos programas solo usan uno; los bytes de
  OutSimPack2 no dicen qué partes llevan.
- **Descartado:** meterlos dentro de `InSim` (como el proyecto anterior) · deducir las opciones de
  OutSim por el tamaño (ambiguo) · valores por defecto en vez de `None` (no se distingue «no enviado»
  de «cero»).
- **Tomada:** S2 (propuesta sin objeción); OutSimPack2 en S5 (2026-10-12).
- **Toca:** `src/lfs_insim/_udp.py`, `_run.py`, `packets/_outsim.py`, `packets/_outgauge.py`.

### D6 — Una superficie pública pequeña   [VIGENTE]
- **Decisión:** lo público es lo que se exporta sin `_` (`InSim`, `OutSim`, `OutGauge`, `run`,
  `lfs_insim.packets`, `lfs_insim.state`, `received`, `sent`, `text`, `units`, `testing`, `Plugin`,
  `Commands`, `Command` y `Arg`); todo lo que lleva `_` puede cambiar sin aviso. Cada
  ampliación se anota en `API_DESIGN.md` como «amplía D6».
- **Por qué:** P4 (el proyecto anterior perdió el control creciendo); una API pequeña se revisa entera.
- **Descartado:** exponer los módulos internos.
- **Tomada:** S2 (2026-10-12; propuesta sin objeción).
- **Toca:** `src/lfs_insim/__init__.py`, cualquier nombre público nuevo.

### D7 — Biblioteca, no framework; las aplicaciones van aparte   [VIGENTE]
- **Decisión:** `lfs_insim` se usa como cualquier biblioteca (`import lfs_insim`). Las aplicaciones
  (cámara libre, control de IA, registrador, gestión de usuarios, botones) viven en sus propios
  proyectos e instalan la biblioteca desde PyPI; aquí solo hay ejemplos cortos (`examples/`) y sus
  requisitos, como texto, en `PLAN.md` «Aplicaciones aparte». La cámara libre vive en
  streamer-project (S20) y el control de IA en `AdrianPascarella/lfs-ai-control` (S26); lo que les
  falte entra aquí como tarea.
- **Por qué:** el usuario: «como una librería más de python… como se haría un import matplotlib o un
  import FastAPI»; que las aplicaciones se escriban con comodidad es la prueba de que la biblioteca
  funciona.
- **Descartado:** repetir el framework del proyecto anterior (módulos, cargador, CLI) · aplicaciones
  dentro de este repositorio · un repositorio propio para la cámara libre (S20).
- **Tomada:** S1 (2026-10-12; el usuario); ubicaciones en S20 y S26.
- **Toca:** `examples/`, `PLAN.md` «Aplicaciones aparte», cualquier propuesta de meter una aplicación aquí.

### D8 — Nombre `lfs_insim` (`pip install lfs-insim`)   [VIGENTE]
- **Decisión:** el paquete se importa como `lfs_insim` y se publica como `lfs-insim`.
- **Por qué:** minúsculas, como manda la convención de Python; libre en PyPI.
- **Descartado:** `AP_LFS_InSim` (contra la convención) · `ap_lfs_insim` · `insim` (demasiado genérico).
- **Tomada:** S1 (2026-10-12).
- **Toca:** `pyproject.toml`, `src/lfs_insim/`.

### D9 — Python 3.11 o superior y ninguna dependencia en tiempo de ejecución   [VIGENTE]
- **Decisión:** `requires-python = ">=3.11"`, `dependencies = []`. Las herramientas de desarrollo van en
  `[dependency-groups]` (`pip install --group dev`), no en un extra (S2).
- **Por qué:** 3.11 es la más antigua con soporte (3.9 ya no lo tiene, 3.10 lo perdía); sin
  dependencias se instala en cualquier sitio. Un grupo no aparece como opción de instalación para los
  usuarios.
- **Descartado:** soportar 3.9/3.10 · las herramientas de desarrollo como extra.
- **Tomada:** S1 y S2 (2026-10-12).
- **Toca:** `pyproject.toml`, cualquier `import` de terceros en `src/`.

### D10 — La especificación se descarga de lfs.net; no se copia en el repositorio   [VIGENTE]
- **Decisión:** `scripts/fetch_spec.py` descarga `InSim.txt` de https://www.lfs.net/programmer/insim a
  `spec/cache/` (ignorada por git); en git solo queda la versión comprobada (`spec/checked.json`, con la
  huella del texto extraído y normalizado). OutSimPack2 se lee de `C:\LFS\docs\OutSimPack.txt` y
  tampoco se sube (S5). La biblioteca nunca descarga nada al usarse.
- **Por qué:** el usuario: «no quiero que esté puesta harcodeada en el proyecto, quiero que la coja de
  la página de lfs.net»; una copia fija se queda desfasada (P2). La huella del texto, no del HTML,
  evita falsos avisos por cambios de la web.
- **Descartado:** copiar la especificación al repositorio · que la biblioteca la descargue en uso
  (dependería de internet) · subir `OutSimPack.txt` para el CI.
- **Tomada:** S1 (el usuario); forma concreta en S3 y S5 (2026-10-12).
- **Toca:** `scripts/fetch_spec.py`, `spec/`, `.github/workflows/spec.yml`.

### D11 — Los paquetes se generan desde la especificación   [VIGENTE]
- **Decisión:** `scripts/generate_packets.py` (con `spec_parser.py`, `generate_enums.py` y las
  excepciones de `spec_overrides.py`) escribe `src/lfs_insim/packets/` `_enums.py`, `_insim.py`,
  `_outsim.py`, `_outgauge.py` y `__init__.py`; el resultado va en git y no se edita a mano. Si la
  generación se para, es a propósito: se añade la excepción que pide, nunca se salta. Sin
  `OutSimPack.txt` comprueba lo que sale solo de `InSim.txt`.
- **Por qué:** mecánico y verificable contra la fuente; en git porque generar al construir exigiría
  red y LFS (para OutSimPack2), y porque el CI comprueba que está al día (`--check`).
- **Descartado:** escribir los paquetes a mano (lo del proyecto anterior) · generar al construir.
- **Tomada:** S1 (aceptado por el usuario); código generado en git en S4; sin `OutSimPack.txt` en S5
  (2026-10-12).
- **Toca:** `scripts/generate_*.py`, `scripts/spec_*.py`, `src/lfs_insim/packets/` (lo generado).

### D12 — Ramas: se trabaja en `dev`; `main` protegida; el proyecto anterior solo se consulta   [VIGENTE]
- **Decisión:** `dev` y `main` nacieron como rama huérfana en S1; `main` solo recibe merges con
  permiso (avance rápido desde `dev`) y es la rama por defecto en GitHub. El proyecto anterior vive en
  `refactor/estabilizacion` y en las etiquetas `archivo/*`, que nunca se borran.
- **Por qué:** empezar sin 45 MB de historial y sin el control perdido (P4), sin destruir nada.
- **Descartado:** seguir sobre la rama antigua · borrar las ramas antiguas sin etiqueta.
- **Tomada:** S1 (2026-10-12; el usuario).
- **Toca:** cualquier operación de git sobre `main`, `refactor/estabilizacion` o `archivo/*`.

### D13 — Lo público en inglés; la documentación de trabajo, en castellano   [VIGENTE]
- **Decisión:** identificadores, comentarios, docstrings, README, `docs/` y ejemplos en inglés;
  `docs/dev`, el chat y los commits en castellano.
- **Por qué:** la comunidad de LFS es internacional y los docstrings son lo que enseña el editor.
- **Descartado:** todo en castellano.
- **Tomada:** S1 (2026-10-12; el usuario).
- **Toca:** todo el código, `README.md`, `docs/`, `examples/`.

### D14 — Una sola verificación: `scripts/verify.py`   [VIGENTE]
- **Decisión:** `verify.py` comprueba el entorno, lint, formato, tipos (mypy estricto), tests y que lo
  generado está al día; está declarado en `factory.json` (S31). Avisa sin fallar de los archivos de más
  de 500 líneas, salvo los generados (S4). `ruff` está fijado a `>=0.17,<0.18` (S5).
- **Por qué:** un único comando que puede fallar es lo que hace terminado algo (§6); el aviso de
  tamaño vigila P4 sin bloquear; ruff cambia el formato en sus versiones menores y pondría en rojo lo
  generado sin cambios nuestros.
- **Descartado:** el tamaño como fallo (se endurece si hace falta) · ruff sin fijar.
- **Tomada:** S2; ajustes en S4 y S5 (2026-10-12).
- **Toca:** `scripts/verify.py`, `pyproject.toml`, `factory.json`.

### D15 — El CI: `verify` en 3.11–3.14, Linux y Windows; lfs.net fuera de `verify`   [VIGENTE]
- **Decisión:** el workflow `verify` ejecuta `verify.py` en cada push a `dev`/`main` y en cada pull
  request, en Python 3.11–3.14 sobre Ubuntu y Windows. La comparación con lfs.net es un test `network`
  que se salta por defecto y que ejecuta el workflow `spec` (cada lunes desde `main` y en cada push que
  cambie la especificación).
- **Por qué:** este equipo no tiene todas las versiones (P5); Windows es donde corre LFS; la verificación
  local no debe depender de la red (lfs.net no siempre responde, §13).
- **Descartado:** solo Linux · meter la descarga de lfs.net en `verify.py`.
- **Tomada:** S3 (2026-10-12).
- **Toca:** `.github/workflows/verify.yml`, `.github/workflows/spec.yml`, los tests `network`.

### D16 — Licencia MIT   [VIGENTE]
- **Decisión:** MIT (`LICENSE`, declarada en `pyproject.toml`).
- **Por qué:** la recomendación del agente para una biblioteca pública de la comunidad; el usuario la eligió.
- **Descartado:** las demás opciones de U1.
- **Tomada:** S2 (2026-10-12; el usuario, U1).
- **Toca:** `LICENSE`, `pyproject.toml`.

### D17 — Las pruebas con el LFS real las hace el agente; el LFS falso, para el CI   [VIGENTE]
- **Decisión:** el agente abre LFS, se conecta y comprueba lo que se ve como paquetes (con los permisos
  de la Configuración); el usuario solo valida lo que se ve en pantalla. La batería en vivo vive en
  `tests/live/` (un script por grupo de `COVERAGE.md`, lo común en `harness.py`, fuera de pytest) y monta
  la carrera con comandos, no con clics (S24). `lfs_insim.testing.FakeLFS` cubre el CI y los casos raros.
- **Por qué:** propuesta del usuario (S9): «prefiero yo quedar fuera»; los comandos no dependen de la
  resolución ni de la ventana.
- **Descartado:** que cada prueba real fuera una tarjeta del usuario · ampliar el único `live_lfs.py` ·
  montar la carrera con clics en coordenadas.
- **Tomada:** S9 (2026-10-12; el usuario); forma de la batería en S24 (2026-10-14).
- **Toca:** `tests/live/`, `tests/lfs_screen.ps1`, `docs/dev/COVERAGE.md`, `src/lfs_insim/testing.py`.

### D18 — Documentación pública en Markdown y publicación con Trusted Publishing   [VIGENTE]
- **Decisión:** `README.md` y `docs/` en Markdown (comprobados por `tests/test_readme.py` y
  `tests/test_docs.py`), sin generador de sitios. Se publica en PyPI con Trusted Publishing desde
  GitHub Actions (`publish.yml`, entorno `pypi`), al crear una release `v<versión>` sobre `main`; estado
  Alpha. Publicar siempre necesita permiso (Configuración; §15 S17 para aprobar el entorno).
- **Por qué:** lo más simple que se puede comprobar con un test; sin tokens guardados.
- **Descartado:** MkDocs o Sphinx «por ahora» · subir con un token de API.
- **Tomada:** S13 (2026-10-13; el usuario).
- **Toca:** `README.md`, `docs/`, `.github/workflows/publish.yml`, `CHANGELOG.md`.

### D19 — La dirección de cada paquete sale de la especificación   [VIGENTE]
- **Decisión:** cada paquete se marca `info` / `instruction` / `both ways` según el `enum` ISP de
  `InSim.txt`; de ahí salen las clases base por dirección y los módulos `received` / `sent`, y lo que no
  corresponde no existe (`on.IS_MST`, `send.IS_NPL`).
- **Por qué:** lo que se echaba de menos del proyecto anterior era saber qué se recibe y qué se envía;
  la especificación ya lo dice.
- **Descartado:** mantener la lista a mano (`.pyi` y tutoriales del proyecto anterior).
- **Tomada:** S14 (2026-10-13; el usuario).
- **Toca:** `scripts/spec_directions.py`, `src/lfs_insim/received.py`, `sent.py`, `packets/_directions.py`.

### D20 — Atajos `on.IS_X` y `send.IS_X`, una sola forma canónica   [VIGENTE]
- **Decisión:** la lista de paquetes cuelga de `on` y de `send`: `@insim.on.IS_NPL` y
  `insim.send.IS_MST(Msg=...)` son las canónicas; `@insim.on(IS_NPL)` e `insim.send(IS_MST(...))`
  siguen valiendo. `send.IS_X` copia la firma del constructor. La guía enseña solo la canónica; sin más
  variantes.
- **Por qué:** lo que se echaba de menos era **ver la lista** en el editor.
- **Descartado:** ~95 métodos sueltos `on_IS_XXX` / `send_IS_XXX` en `insim` (decidido en S14 y rehecho
  en S15) · abreviaturas o nombres como cadena.
- **Tomada:** S15 (2026-10-13; el usuario). Detalle: `PLAN.md` W7.
- **Toca:** `src/lfs_insim/_shortcuts.py`, `_handlers.py`, `docs/`, `examples/`.

### D21 — Como invitado en un servidor ajeno, los comandos son solo de este ordenador   [VIGENTE]
- **Decisión:** como invitado, solo este ordenador usa los comandos (`guest_commands="everyone"`
  abre); `admin=True` es solo este ordenador; `reply()` contesta por `IS_MSL` a este ordenador y por el
  chat público a otro; `/o` cuenta como comando.
- **Por qué:** en un servidor ajeno nadie más debe poder mandar a tu programa.
- **Descartado:** ver `API_DESIGN.md` «Comandos como invitado».
- **Tomada:** S19 (2026-10-13; el usuario, las cuatro recomendadas). Validado en real en S29 (U11).
- **Toca:** `src/lfs_insim/_commands.py`, `state.py` (`guest`, `local`).

### D22 — Plugins: `insim.use()`, `Plugin` y `Commands` aparte de `Roster`; sin cargador   [VIGENTE]
- **Decisión:** `insim.use(Tipo, **opciones)` da una instancia por tipo y por `InSim`; `lfs_insim.Plugin`
  es la base pública; `Commands` es un plugin propio que hace `use(Roster)`. Un plugin se escribe solo
  con la API pública, como uno de fuera.
- **Por qué:** idea del usuario: usar `Roster`, el control de IA o la cámara solos o combinados en un
  solo InSim compartiendo el estado (como los *Cogs* de discord.py o los *blueprints* de Flask).
- **Descartado:** el cargador del proyecto anterior (manifiestos, carga por carpetas,
  `get_insim("nombre")` sin tipo, fue parte de P4) · los comandos dentro de `Roster` · `insim.adopt()`
  público.
- **Tomada:** S20 (2026-10-13; idea del usuario, diseño del agente aceptado). P10. Detalle:
  `API_DESIGN.md` «Plugins».
- **Toca:** `src/lfs_insim/_plugins.py`, `_commands.py`, `state.py`, `docs/plugins.md`.
### D23 — Un `on_connect` registrado con la conexión abierta se llama al momento   [VIGENTE]
- **Decisión:** `on_connect` registrado con la conexión ya abierta se llama al momento (y su
  `on_disconnect` después); así cualquier complemento hecho tarde, como un `Roster`, queda listo.
- **Por qué:** arregla de una vez a todos los complementos hechos tarde, y es lo que ya prometía el
  docstring («after every connection»).
- **Descartado:** arreglar solo el `Roster` (los demás seguirían fallando en silencio) · un error al
  crearlo tarde (no arregla nada).
- **Tomada:** S30 (2026-10-18; el usuario, la recomendada). P12. `every()` tiene el mismo defecto (P13,
  W14.3, sin decidir).
- **Toca:** `src/lfs_insim/_connection.py` (`on_connect`, `connect`), `state.py`.

