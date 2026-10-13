# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-13 (S20): **W10 (plugins) esbozada y puesta antes de W6**, a petición del usuario; sin
> código todavía. En S19: **W9 hecha** (comandos como invitado, probados en el LFS real; prefijo propio por comando, W9.7;
> **publicado como 0.5.0**). Antes, en S18: **W7 y W8 hechas**. La biblioteca está validada en el LFS real
> y tiene la API de alto nivel (`@insim.on.IS_NPL`, `insim.send.IS_MST(...)`, `received` / `sent`,
> `await insim.request(...)`, `Roster`, `say()` / `command()`, `on_command`, `text.plain()`), cuatro
> ejemplos y `docs/packets.md` (tabla generada).
> **`lfs-insim 0.5.0` está publicado en PyPI** (S19, release `v0.5.0`): comandos como invitado y prefijo propio
> por comando (W9). Antes, 0.4.0 (S18: W8) y 0.3.0 y 0.2.0 (S16–S17).
> **▶️ SIGUIENTE: W10, plugins** (`insim.use(Roster)`, comandos como plugin propio, nada pedido dos veces,
> `ready()`, flags por plugin, `ClickID`). Plan aceptado en S20. **Hechas W10.1, W10.11, W10.2, W10.3, W10.4
> y W10.5** (`use()`, `Plugin`, funciones como plugins, `Commands` como plugin —cambio incompatible, sin
> publicar—, peticiones compartidas, `ready()`, `need()`). W10.6 y W10.7 hechas (`reserve_click_ids()`, `on_close`).
> Sigue **W10.8** (guía y ejemplos), que necesita antes **W10.0**:
> W10.0 (prueba en real) cuando el usuario deje abrir LFS, antes de W10.8.
> Tareas en `PLAN.md`; diseño en `API_DESIGN.md`
> («Plugins»); por qué, en `LOG.md` S20. **W6 espera a W10**; su alcance ya está decidido (en `PLAN.md`).
> **Receta de una versión nueva:** versión y CHANGELOG en
> `dev`; `verify` en verde; avance rápido de `dev` a `main`; `gh release create vX.Y.Z --target main`
> (el tag debe ser `v<version>`); aprobar el entorno `pypi` (pedirlo cada vez; con permiso, el agente lo aprueba
> por la API: `gh api -X POST .../actions/runs/<id>/pending_deployments -F "environment_ids[]=<id>" -f state=approved`,
> con `GH_TOKEN` de `AdrianPascarella`). Una versión publicada
> no se puede resubir. `_connection.py` va por 496 líneas (aviso de `verify` en 500): lo que crezca, en un
> módulo propio (los comandos de W8.2, en `_commands.py`). Ver `USER_ACTIONS.md`.

## Dónde estamos
Fase activa: **W10** (esbozada en S20; se detalla tarea a tarea). W6 detrás. W9 hecha y 0.5.0 publicado en S19.

- **Cómo se genera:** `.venv/Scripts/python scripts/generate_packets.py` lee
  `spec/cache/InSim.txt` y `spec/cache/OutSimPack.txt` (con `scripts/spec_parser.py`) y las
  excepciones de `scripts/spec_overrides.py`, y escribe en `src/lfs_insim/packets/` `_enums.py`,
  `_insim.py`, `_outsim.py`, `_outgauge.py` y `__init__.py`, que van en git y no se editan a mano.
  `--check` sale con 1 si no están al día. Los enums los construye `scripts/generate_enums.py`.
  El núcleo escrito a mano es `packets/_codec.py` (los codecs de campo) y `packets/_structure.py`
  (`Structure`, `InSimPacket`, `register`, `unpack_insim`; separado en W8.0).
- **Si la generación se para con un error**, es a propósito: algo de la especificación no está
  cubierto. Se añade la entrada que pide en `spec_overrides.py`, nunca se salta.
- `OutSimPack.txt` solo existe en este equipo (P3). Sin él, el generador salta `_outsim.py` y
  `__init__.py` y comprueba el resto: así funciona en el workflow `spec`.
- **OutSimPack2** se lee con `OutSimPack2.unpack(data, opciones OSO)`; las partes no enviadas son
  `None` (LOG S5).
- **Texto:** `packets/_text.py` (páginas de códigos; D3 precisada en S7). `CName` y
  `IS_MAL.SkinID` no son texto: tienen sus propios codecs (`CarName`, `SkinID`; P6).
- **Verificación:** `.venv/Scripts/python scripts/verify.py`; el CI (workflow `verify`) ejecuta lo
  mismo en cada push. Sin `spec/cache/` (como en el CI), los tests que comparan con la
  especificación y el paso `generated` se saltan; el workflow `spec` descarga InSim.txt y hace esa
  comprobación.
- **API:** `docs/dev/API_DESIGN.md` (D1–D6; D3 precisada en S4: `TINY.NCN`, texto como `str`).

El proyecto anterior está en la rama `refactor/estabilizacion` y en las etiquetas `archivo/*`. Se
consulta, no se copia.

## Lo que te espera
1 pendiente, opcional y sin bloquear nada: U11 (comando de otra persona como invitado) → `USER_ACTIONS.md`.

## Tests inestables (arreglados en S14)
`tests/test_every.py` fallaba a veces solo en el Windows del CI (3.12 y 3.13). Causa comprobada: en
Windows con Python anterior a 3.13, `time.monotonic()` avanza a saltos de ~15 ms, así que dos marcas
seguidas podían salir iguales. Los tests miden ahora con `time.perf_counter()` y margen de 2 ms. Si
vuelve a fallar en el CI, reabrir con el log delante.

## Restricciones ahora mismo
- En este equipo solo hay Python 3.14. Las demás versiones las comprueba el CI.
- El `python` de la terminal es el de streamer-project: aquí siempre `.venv/Scripts/python` (§13).
- `ruff format` y `ruff check --fix` solo sobre las rutas de `CHECKED_PATHS`, nunca sobre `scripts`
  entera (§13).
- El repositorio es público.
