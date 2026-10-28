# 🗺️ Arquitectura — AP_LFS_InSim (lfs_insim)
> Lo que es cierto ahora: qué existe, dónde vive, cómo se verifica y qué decisión explica cada
> frontera. Se reescribe en el sitio en el cierre que lo cambia (PROTOCOL §4); nunca es un diario. Por
> estructura y convenciones, nunca por números de línea. Tope ~200 líneas: el detalle va a una guía
> (§14). Escrito en S31 (UPGRADE a la plantilla v4) a partir del repositorio tal como está (0.9.0
> publicada; W14.1 en `dev`, sin publicar).

## Qué es
Una biblioteca de Python (`pip install lfs-insim`, `import lfs_insim`) para los protocolos InSim
(TCP), OutSim y OutGauge (UDP) de Live for Speed. Python ≥ 3.11, sin dependencias (D8, D9). No es un
framework: las aplicaciones viven en otros repositorios (D7).

## Componentes
- **Paquetes generados** — una dataclass por paquete de la especificación, con sus nombres (D3) ·
  `src/lfs_insim/packets/` `_enums.py`, `_insim.py`, `_outsim.py`, `_outgauge.py`, `__init__.py` ·
  generados, en git, nunca a mano (D11). Su primera línea los marca como generados.
- **Núcleo de los paquetes, a mano** — los codecs de campo (`packets/_codec.py`), las clases base,
  el registro y `unpack_insim` (`packets/_structure.py`), el texto de LFS ↔ `str` (`packets/_text.py`),
  los tipos vector (`_types.py`), la dirección de cada paquete (`_directions.py`, D19) y añadidos a
  lo generado (`_extras.py`).
- **Generador** — `scripts/generate_packets.py` lee `spec/cache/InSim.txt` y `OutSimPack.txt` con
  `scripts/spec_parser.py`, aplica `scripts/spec_overrides.py` (excepciones, nombres, notas vistas en
  LFS) y `scripts/spec_directions.py`; los enums los hace `scripts/generate_enums.py`. `--check` dice si
  lo generado está al día. Si se para, falta una excepción: se añade, nunca se salta (D11).
- **Especificación** — `scripts/fetch_spec.py` descarga lfs.net a `spec/cache/` (ignorada) y compara
  con `spec/checked.json`, que es lo único en git; `--accept` registra una versión nueva (D10).
- **Conexión InSim** — `_connection.py` (`InSim`: TCP, el saludo `IS_ISI`, `connect`/`close`,
  `on_connect`/`on_disconnect`, `watch`, `every`), `_stream.py` (cortar el flujo TCP en paquetes),
  `_handlers.py` (manejadores por tipo, compartidos con UDP), `_events.py` + `_shortcuts.py` +
  `_subtypes.py` (`insim.on` / `insim.send` con un atributo por paquete, D2, D20), `_asking.py` +
  `_requests.py` (`request`, `request_all`, `instruct`), `_run.py` (`run()` para varios a la vez, D1).
- **UDP** — `_udp.py`: `OutSim` y `OutGauge`, con la misma forma que `InSim` (D5).
- **Plugins** — `_plugins.py` (`insim.use()`, `Plugin`, D22); `state.py` (`Roster`, quién es quién,
  opcional, D4); `_commands.py` (`Commands`, `Command`, `Arg`: comandos de chat, también como invitado,
  D21).
- **Ayudantes públicos** — `received.py` / `sent.py` (los paquetes por dirección, D19), `text.py`
  (`plain()`, `strip_colours()`), `units.py` (unidades de LFS y comunes), `testing.py` (`FakeLFS`, un
  LFS falso para probar programas y plugins sin el juego).
- **Superficie pública** — lo que exporta `src/lfs_insim/__init__.py` y los módulos sin `_` (D6).

## Fronteras (lo que no se hace a propósito, y dónde está la línea)
- Ninguna aplicación dentro del repositorio; `examples/` solo tiene ejemplos cortos — D7.
- Ninguna dependencia en tiempo de ejecución — D9.
- La especificación no se copia: ni `InSim.txt` ni `OutSimPack.txt` van en git — D10.
- Lo generado no se edita a mano; lo escrito a mano se añade en `_extras.py`, `_codec.py` o en las
  excepciones del generador — D11.
- Nada de cargador de módulos, manifiestos ni CLI del proyecto anterior — D22, D7.
- La biblioteca no descarga nada al usarse; solo en desarrollo — D10.
- El proyecto anterior (`refactor/estabilizacion`, `archivo/*`) se consulta, no se copia — D12.

## Convenciones
- Lo público en inglés (código, docstrings, `README.md`, `docs/`, `examples/`); `docs/dev`, en
  castellano — D13.
- Nombres de la especificación (`IS_MST`, `PLID`, `TINY.NCN`), no `snake_case` — D3.
- Formas canónicas `@insim.on.IS_X` e `insim.send.IS_X(...)`; la guía enseña solo esas — D20.
- Cada ampliación de la API pública se anota en `docs/dev/API_DESIGN.md` («amplía D6») y en
  `CHANGELOG.md` («Unreleased» hasta publicar).
- Aviso a partir de 500 líneas por archivo `.py` (salvo lo generado): lo que crezca en
  `_connection.py` o `generate_packets.py`, a un módulo propio — D14, P4.
- `ruff format` solo sobre las rutas de `CHECKED_PATHS` de `verify.py`, nunca sobre `scripts` o
  `docs` enteras (PROTOCOL §13).
- Los scripts del protocolo (`scripts/close_check.py`, `session_start_check.py`, `ctx_log_last.py`,
  `ctx_plan_active.py`) vienen de la plantilla y no son código del proyecto: no se formatean ni se
  editan aquí.

## Cómo se verifica
- `.venv/Scripts/python scripts/verify.py` (declarado en `factory.json`) — detecta un intérprete o un
  `lfs_insim` equivocados, lint y sintaxis posterior a 3.11, formato, tipos (mypy estricto), tests que
  fallan y paquetes generados desfasados — D14.
- CI: workflow `verify` (3.11–3.14, Ubuntu y Windows, cada push a `dev`/`main` y cada pull request);
  workflow `spec` (lfs.net frente a `spec/checked.json`, cada lunes desde `main`) — D15.
- `tests/`: pytest contra `FakeLFS`; los tests `network` se saltan por defecto (`pytest -m network`).
  `tests/test_readme.py` y `tests/test_docs.py` comprueban la documentación pública.
- `tests/live/`: batería en el LFS real, por grupos (`group_a.py` … `group_p.py`, `aic_values.py`,
  `probe.py`; lo común en `harness.py`), fuera de pytest; el estado por paquete en
  `docs/dev/COVERAGE.md`. `tests/lfs_screen.ps1` maneja la ventana de LFS — D17.
- Lo que valida el usuario (lo que se ve en pantalla, la comodidad de la API): punto ciego, PROTOCOL
  Configuración.
- Publicación: `publish.yml` con Trusted Publishing al crear la release `v<versión>` en `main` — D18.

## Dónde vive el estado
- Archivos de contexto: `docs/dev/` (`STATE`, `USER_ACTIONS`, `LOG`, `PLAN`, `DIAGNOSIS`, `DECISIONS`,
  este archivo, `PROTOCOL`), más `API_DESIGN.md` (detalle de la API), `COVERAGE.md` (qué se ha visto
  funcionar en el LFS real) y `LEGADO.md` (qué rescatar del proyecto anterior).
- `factory.json` (raíz): el comando de verificación y las rutas protegidas, como dato.
- `spec/checked.json`: la versión de la especificación comprobada; `spec/cache/` es local.
- `tests/live_reports/`: informes de las pruebas en vivo (ignorados por git).
- Lo que nunca se debe perder (la rama `refactor/estabilizacion`, las etiquetas `archivo/*`, los mapas
  freeroam y las copias fuera del repositorio): PROTOCOL, Configuración.
