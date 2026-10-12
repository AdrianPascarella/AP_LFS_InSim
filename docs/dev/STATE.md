# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-12 (S11): **W3.7 hecha** — `lfs_insim.OutSim` y `OutGauge` (`_udp.py`)
> escuchan UDP con `@x.on(...)` como `InSim`, y `lfs_insim.run(insim, gauge)` (`_run.py`) arranca
> varias fuentes a la vez. Los manejadores de las tres viven en `_handlers.Handlers`. Hechas en
> S9–S10: W3.2–W3.6 (`InSim` conecta, keep-alive, reconexión, `@insim.on_connect`). Decisiones de
> API en `API_DESIGN.md`. El agente puede abrir LFS 0.8C31 (`C:\LFS`, limpio; InSim **no**
> activado). Tests en verde.
> **▶️ SIGUIENTE: W3.8 — `@insim.every(segundos)`** (`def` o `async def`; un error no lo para).
> Después, W3.1 (prueba en vivo con el LFS real), que cierra W3.

## Dónde estamos
Fase activa: **W3 — La conexión**, detallada en S9 (`PLAN.md`). W2 está hecha entera.

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
**0 acciones pendientes** → `USER_ACTIONS.md`.

## Restricciones ahora mismo
- En este equipo solo hay Python 3.14. Las demás versiones las comprueba el CI.
- El `python` de la terminal es el de streamer-project: aquí siempre `.venv/Scripts/python` (§13).
- `ruff format` y `ruff check --fix` solo sobre las rutas de `CHECKED_PATHS`, nunca sobre `scripts`
  entera (§13).
- El repositorio es público.
