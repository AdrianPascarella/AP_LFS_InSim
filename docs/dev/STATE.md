# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-13 (S14): W5.1–W5.3 hechas; **W3 y W4 hechas enteras (S12).** La biblioteca está validada en el
> LFS real (InSim, OutGauge, OutSim y `OutSimPack2`; `tests/live_lfs.py`), y tiene la API de alto
> nivel: `IS_MSO.text`, `await insim.request(IS_X)` / `request_all`, `Roster` (`lfs_insim.state`),
> `insim.say()` / `command()`, `@insim.on_command("hello")`, `lfs_insim.text.plain()` y cuatro
> ejemplos en `examples/`, probados en cada push y comprobados en el LFS real. Decisiones en
> `API_DESIGN.md`. El agente maneja LFS con `tests/lfs_screen.ps1`, que no envía nada si LFS no
> está delante (PROTOCOL §13). `cfg.txt` está restaurado: OutSim/OutGauge en vivo pide permiso.
> **▶️ SIGUIENTE: W7** (dirección de los paquetes y atajos generados: `@insim.on_IS_NPL`,
> `insim.send_IS_MST(...)`, `received`/`sent`; detallada en `PLAN.md`, decidida con el usuario en S14).
> Después W8 (mejoras del proyecto anterior, `LEGADO.md`) y W6 (primera aplicación aparte).
> `lfs-insim 0.1.0` está **publicado en PyPI** (S14, release `v0.1.0`). **Receta de una versión nueva:**
> subir `version` en `pyproject.toml` y añadir la sección a `CHANGELOG.md` en `dev`; `verify` en verde;
> avance rápido de `dev` a `main`; `gh release create vX.Y.Z --target main` (el tag debe ser `v<version>`);
> aprobar el entorno `pypi` (el usuario lo autorizó en S14 para 0.1.0; pedirlo cada vez). Una versión
> publicada no se puede resubir. `_connection.py` va por ~405 líneas: lo próximo que crezca, en un
> módulo propio. Ver `USER_ACTIONS.md`.

## Dónde estamos
Fase siguiente: **W5 — Publicación**, detallada y sin empezar. W2, W3 y W4 están hechas enteras. Prueba en vivo: `tests/live_lfs.py` (cómo ejecutarla, en su docstring).

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
Ninguna acción pendiente (U6 cerrada en S14) → `USER_ACTIONS.md`.

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
