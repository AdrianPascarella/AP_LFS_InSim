# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-13 (S16): **W7 hecha entera salvo W7.7.** La biblioteca está validada en el LFS real
> y tiene la API de alto nivel (`@insim.on.IS_NPL`, `insim.send.IS_MST(...)`, `received` / `sent`,
> `await insim.request(...)`, `Roster`, `say()` / `command()`, `on_command`, `text.plain()`), cuatro
> ejemplos y `docs/packets.md` (tabla generada). U7 cerrada: el usuario vio las listas en su VS Code.
> La versión de `dev` es **0.2.0, sin publicar** (CHANGELOG listo).
> **▶️ SIGUIENTE (decide el usuario):** (a) publicar 0.2.0 (receta abajo; pide permiso expreso);
> (b) W7.7, subtipos de `IS_TINY` / `IS_SMALL` (`@insim.on.IS_TINY(TINY.MPE)`), que se decide con él;
> (c) abrir W8 (mejoras del proyecto anterior, `LEGADO.md`) o W6 (primera aplicación aparte).
> `lfs-insim 0.1.0` está publicado en PyPI. **Receta de una versión nueva:** versión y CHANGELOG en
> `dev`; `verify` en verde; avance rápido de `dev` a `main`; `gh release create vX.Y.Z --target main`
> (el tag debe ser `v<version>`); aprobar el entorno `pypi` (pedirlo cada vez). Una versión publicada
> no se puede resubir. `_connection.py` va por ~405 líneas y `_codec.py` pasa de 500 (aviso de
> `verify`): lo próximo que crezca, en un módulo propio. Ver `USER_ACTIONS.md`.

## Dónde estamos
Fase activa: **W7 — Dirección de los paquetes y atajos generados** (W7.1–W7.6 hechas; falta W7.7). W1–W5 están hechas enteras. Prueba en vivo: `tests/live_lfs.py` (cómo ejecutarla, en su docstring).

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
