# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-14 (S23), equipo principal: **W6.3 hecha** — `FreeCam` en streamer-project
> (`tools/freecam`, su W9.1), probada en real con `freecam_prueba.mpr`: cargar, ir a un instante, seguir a un
> piloto con una vista (`IS_SCC`), cámara libre a una posición y movimiento suave (`IS_CPP`), esperar; `where`
> escribe los pasos de donde está la cámara. Plano = U13 («me vale tal cual»). **W6.10 hecha:** `connect()` no
> llamaba a `on_connect`/`on_disconnect` (con `connect()`, `roster.ready()` no volvía nunca); arreglado en
> `dev`. **Avisos rojos de LFS** («sending to one but ReqI is not set», 5 cada vez): el usuario sospechó de un
> `ReqI` sin poner; investigado: salen al **saltar hacia atrás** en una MPR, también con un cliente mínimo de
> socket propio (`IS_ISI` + `IS_RIP` con `ReqI`), no hacia delante; no los causa la biblioteca (LOG S23).
> **▶️ SIGUIENTE: W6.4** — publicar **0.7.0** (con permiso del usuario; CHANGELOG «Unreleased» ya tiene W6.1,
> W6.5–W6.10) y después, en streamer-project, fijar `lfs-insim==0.7.0` (hoy su `.venv` tiene la de `dev`
> instalada desde la carpeta). W6 se cierra con eso. Antes, en S22: W6.5–W6.9 (enums de comentarios,
> `unpack_insim` pública, `request.IS_X()` / `request_all.IS_X()` / `instruct.IS_X(...)`). La biblioteca tiene
> la API de alto nivel (`@insim.on.IS_NPL`, `insim.send.IS_MST(...)`, `received` / `sent`, `request` /
> `request_all` / `instruct`, `say()` / `command()`, `text.plain()`), plugins (`insim.use()`, `Plugin`,
> `Commands`, `Roster`, `insim.need()`, `reserve_click_ids()`, `on_close`) y `lfs_insim.testing.FakeLFS`.
> LFS acepta hasta 8 programas InSim a la vez (W10.0). Tareas en `PLAN.md` (W6); por qué, en `LOG.md` S21–S23.
> **Receta de una versión nueva:** versión y CHANGELOG en
> `dev`; `verify` en verde; avance rápido de `dev` a `main`; `gh release create vX.Y.Z --target main`
> (el tag debe ser `v<version>`); aprobar el entorno `pypi` (pedirlo cada vez; con permiso, el agente lo aprueba
> por la API: `gh api -X POST .../actions/runs/<id>/pending_deployments -F "environment_ids[]=<id>" -f state=approved`,
> con `GH_TOKEN` de `AdrianPascarella`). Una versión publicada
> no se puede resubir. `_connection.py` va por 454 líneas (aviso de `verify` en 500): lo que crezca, en un
> módulo propio (los comandos, en `_commands.py`; las peticiones, en `_asking.py`). Ver `USER_ACTIONS.md`.

## Dónde estamos
Fase activa: **W6** (todo hecho menos W6.4, publicar 0.7.0). W10 hecha y publicada como 0.6.0 en S21.

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
1 pendiente → `USER_ACTIONS.md`: U11 (opcional: comando de otra persona como invitado). U13 cerrada en S23. Además,
el permiso para publicar 0.7.0 (W6.4), que se pide en el chat.

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
