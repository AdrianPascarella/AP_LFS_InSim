# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-14 (S23), equipo principal: **W6 cerrada y `lfs-insim` 0.7.0 publicada** (W6.4, con
> permiso). 0.7.0 trae W6.1 y W6.5–W6.10: `request.IS_X()` / `request_all.IS_X()` / `instruct.IS_RIP(...)`,
> `unpack_insim` pública, enums de comentarios (`PTYPE`, `NCNF`, `SCHF`, `PLHF`, `RACING`, `WIND`, `OFFON`, `ACR`,
> `ISM`, `FLG`, `HLVC`, `REPLAY`) y `connect()` que llama a `on_connect`/`on_disconnect` (W6.10). **W6.3 hecha:**
> `FreeCam` en streamer-project (`tools/freecam`, su W9.1), probada en real, con 0.7.0 de PyPI fijada allí.
> **Avisos rojos de LFS** («sending to one but ReqI is not set»): salen al saltar hacia atrás en una MPR, también
> con un cliente mínimo propio; no los causa la biblioteca (LOG S23).
> **▶️ SIGUIENTE: decidir con el usuario la próxima fase.** No queda ninguna tarea abierta en `PLAN.md`. Candidatas
> (sección «Ideas» y «Aplicaciones aparte»): la siguiente aplicación (control de IA, botones), el ayudante de
> botones, InSim por UDP, o lo que pida FreeCam al crecer (planos desde los eventos del registrador). La
> biblioteca tiene la API de alto nivel (`@insim.on.IS_NPL`, `insim.send.IS_MST(...)`, `received` / `sent`,
> `request` / `request_all` / `instruct`, `say()` / `command()`, `text.plain()`), plugins (`insim.use()`,
> `Plugin`, `Commands`, `Roster`, `insim.need()`, `reserve_click_ids()`, `on_close`) y
> `lfs_insim.testing.FakeLFS`. LFS acepta hasta 8 programas InSim a la vez (W10.0).
> **Receta de una versión nueva:** versión y CHANGELOG en
> `dev`; `verify` en verde; avance rápido de `dev` a `main`; `gh release create vX.Y.Z --target main`
> (el tag debe ser `v<version>`); aprobar el entorno `pypi` (pedirlo cada vez; con permiso, el agente lo aprueba
> por la API: `gh api -X POST .../actions/runs/<id>/pending_deployments -F "environment_ids[]=<id>" -f state=approved`,
> con `GH_TOKEN` de `AdrianPascarella`). Una versión publicada
> no se puede resubir. `_connection.py` va por 454 líneas (aviso de `verify` en 500): lo que crezca, en un
> módulo propio (los comandos, en `_commands.py`; las peticiones, en `_asking.py`). Ver `USER_ACTIONS.md`.

## Dónde estamos
Fase activa: **ninguna** — W6 cerrada en S23 y publicada como 0.7.0; la siguiente se decide con el usuario.

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
1 pendiente → `USER_ACTIONS.md`: U11 (opcional: comando de otra persona como invitado). U13 cerrada en S23. 

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
