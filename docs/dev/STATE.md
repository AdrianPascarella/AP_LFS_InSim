# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-14 (S22): **W6.7, W6.5, W6.6 y W6.8 hechas** en `dev` (equipo secundario), sin publicar. W6.6/W6.8:
> `PTYPE`, `NCNF`, `SCHF`, `HCPF` (bits leídos del comentario del campo por el generador: `BIT_COMMENTS`). W6.5:
> `lfs_insim.packets.unpack_insim(data)` es pública (lee un paquete cualquiera de sus bytes). W6.7: `await
> insim.request.IS_STA()`, `await insim.request_all.IS_NPL()` y `await insim.instruct.IS_RIP(...)` (el editor
> lista lo que cabe en cada uno; `request(IS_X)` y `request_all(IS_X)` siguen). Sustituye `request(IS_RIP(...))`
> de W6.1. Encadenar (`request.IS_A().IS_B()`) descartado: `asyncio.gather`. Antes, en S21: W10 (plugins)
> publicada como `lfs-insim 0.6.0`. La biblioteca está validada en el LFS real y tiene la API de alto nivel
> (`@insim.on.IS_NPL`, `insim.send.IS_MST(...)`, `received` / `sent`, `request` / `request_all` / `instruct`,
> `say()` / `command()`, `text.plain()`) y plugins: `insim.use()`, `lfs_insim.Plugin`, `Commands` como plugin,
> peticiones compartidas, `roster.ready()`, `insim.need()`, `insim.reserve_click_ids()`, `@insim.on_close` y
> `lfs_insim.testing.FakeLFS`.
> LFS acepta hasta 8 programas InSim a la vez (W10.0).
> **▶️ SIGUIENTE: W6.3** — `FreeCam` en streamer-project (W9.1 de allí): repetición + plano guionizado; necesita
> el equipo principal (LFS y streamer-project). FreeCam usará `instruct.IS_RIP(...)` (`request(IS_RIP(...))` ya no existe).
> En el secundario: W6.9 (valores en comentarios, «0 = off / 1 = weak»), propuesta sin decidir (`LEGADO.md` §7).
> **Pregunta abierta al usuario (fin de S21), lo primero de la próxima sesión:** qué es «un plano». Propuesta del agente, sin respuesta todavía: un archivo pequeño con una lista de pasos: ir a un instante de la repetición; seguir a un coche con una vista del juego (`IS_SCC`); cámara libre de A a B en N segundos, con posición y hacia dónde mira (`IS_CPP`, LFS suaviza); esperar N segundos. Más adelante, planos generados desde los eventos del registrador. Con eso se graban tomas concretas con OBS. La
> repetición `freecam_prueba.mpr` está cargada en el LFS del usuario y hay permiso para usarlo. **W6.2 hecha** en
> S21: el registrador de streamer-project usa `lfs_insim` 0.6.0 (mismos eventos que antes). W6.1 (con la forma de W6.7) en `dev`,
> probada en real en S21, sin publicar. Propuesta sin decidir: W6.9. Tareas en `PLAN.md` (W6); por qué, en `LOG.md` S21.
> **Receta de una versión nueva:** versión y CHANGELOG en
> `dev`; `verify` en verde; avance rápido de `dev` a `main`; `gh release create vX.Y.Z --target main`
> (el tag debe ser `v<version>`); aprobar el entorno `pypi` (pedirlo cada vez; con permiso, el agente lo aprueba
> por la API: `gh api -X POST .../actions/runs/<id>/pending_deployments -F "environment_ids[]=<id>" -f state=approved`,
> con `GH_TOKEN` de `AdrianPascarella`). Una versión publicada
> no se puede resubir. `_connection.py` va por 452 líneas (aviso de `verify` en 500): lo que crezca, en un
> módulo propio (los comandos, en `_commands.py`; las peticiones, en `_asking.py`). Ver `USER_ACTIONS.md`.

## Dónde estamos
Fase activa: **W6** (en curso: W6.1, W6.2, W6.5–W6.8 hechas; siguiente, W6.3, la cámara libre). W10 hecha y publicada como 0.6.0 en S21.

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
U12 descartada por el usuario en S21.

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
