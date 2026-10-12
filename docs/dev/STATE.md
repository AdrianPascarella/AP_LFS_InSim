# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-12 (S5): **W2.1–W2.7 hechas: InSim, OutSim y OutGauge se generan** desde la
> especificación, y `verify.py` y el workflow `spec` comprueban que el código generado está al día.
> Tests y CI en verde. Árbol limpio y subido al cerrar.
> **▶️ SIGUIENTE: W2.8**: segunda opinión. Un script de un solo uso compara formatos y tamaños con
> el proyecto anterior (rama `refactor/estabilizacion`), y las diferencias se revisan y se anotan
> en `LOG.md`. Incluye comprobar si `CName` lleva un SkinID binario en los mods. Después, W2.9.

## Dónde estamos
Fase activa: **W2 — El protocolo, generado desde la especificación**, detallada con el usuario en
S4 (`PLAN.md`). Hechas W2.1–W2.7.

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
- **Texto:** `packets/_text.py` usa cp1252 de forma provisional hasta W2.9.
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
