# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-13 (S16): **W7 hecha entera salvo W7.7.** La biblioteca está validada en el LFS real
> y tiene la API de alto nivel (`@insim.on.IS_NPL`, `insim.send.IS_MST(...)`, `received` / `sent`,
> `await insim.request(...)`, `Roster`, `say()` / `command()`, `on_command`, `text.plain()`), cuatro
> ejemplos y `docs/packets.md` (tabla generada). U7 cerrada: el usuario vio las listas en su VS Code.
> **`lfs-insim 0.2.0` está publicado en PyPI** (S16, release `v0.2.0`).
> **W7 está hecha entera** (W7.7, S16: `@insim.on.IS_TINY(TINY.MPE)`, en `dev` sin publicar: CHANGELOG «Unreleased»).
> **▶️ SIGUIENTE: abrir W8** (mejoras del proyecto anterior; lista y orden propuesto en `LEGADO.md` §4; se detalla con el
> usuario al abrirla, no antes). El usuario eligió W8 antes que W6 (el agente recomendó W6 primero para que la
> aplicación real decidiera el orden de W8; queda como alternativa). W7.7 y el CHANGELOG «Unreleased» esperan a la
> siguiente versión: se publican con lo próximo que se añada.
> **Receta de una versión nueva:** versión y CHANGELOG en
> `dev`; `verify` en verde; avance rápido de `dev` a `main`; `gh release create vX.Y.Z --target main`
> (el tag debe ser `v<version>`); aprobar el entorno `pypi` (pedirlo cada vez). Una versión publicada
> no se puede resubir. `_connection.py` va por ~405 líneas y `_codec.py` pasa de 500 (aviso de
> `verify`): lo próximo que crezca, en un módulo propio. Ver `USER_ACTIONS.md`.

## Dónde estamos
Fase activa: ninguna (W7 hecha entera en S16); la siguiente sesión abre **W8**.

- **Cómo se genera:** `.venv/Scripts/python scripts/generate_packets.py` lee
  `spec/cache/InSim.txt` y `spec/cache/OutSimPack.txt` (con `scripts/spec_parser.py`) y las
  excepciones de `scripts/spec_overrides.py`, y escribe en `src/lfs_insim/packets/` `_enums.py`,
  `_insim.py`, `_outsim.py`, `_outgauge.py` y `__init__.py`, que van en git y no se editan a mano.
  `--check` sale con 1 si no están al día. Los enums los construye `scripts/generate_enums.py`.
  El núcleo escrito a mano es `packets/_codec.py`.
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
Ninguna acción pendiente (U7 cerrada en S16) → `USER_ACTIONS.md`.

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
