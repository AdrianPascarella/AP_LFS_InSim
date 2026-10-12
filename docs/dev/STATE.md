# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-12 (S4): **W2 a medias: los paquetes de InSim ya se generan** desde la
> especificación (W2.1–W2.4), con tests y CI en verde. `main` ya tiene W1 (U2). Árbol limpio y
> subido al cerrar.
> **▶️ SIGUIENTE: W2.5** — generar OutSim (OutSimPack y OutSimPack2 según sus opciones OSO_) y
> OutGauge (OutGaugePack), con el `ID` final opcional (`_c.Optional`), en sus propios módulos.
> Después, completar W2.6 (sus tests de ida y vuelta) y seguir con W2.7 → W2.9.

## Dónde estamos
Fase activa: **W2 — El protocolo, generado desde la especificación**, detallada con el usuario en
S4 (`PLAN.md`). Hechas W2.1–W2.4. **W2.6, a medias:** los tests de InSim están; faltan los de
OutSim/OutGauge, que llegan con W2.5.

- **Cómo se genera:** `.venv/Scripts/python scripts/generate_packets.py` lee `spec/cache/InSim.txt`
  (con `scripts/spec_parser.py`) y las excepciones de `scripts/spec_overrides.py`, y escribe
  `src/lfs_insim/packets/_enums.py`, `_insim.py` y `__init__.py`, que van en git y no se editan a
  mano. `--check` sale con 1 si no están al día (base de W2.7). El núcleo escrito a mano es
  `packets/_codec.py`.
- **Si la generación se para con un error**, es a propósito: algo de la especificación no está
  cubierto. Se añade la entrada que pide en `spec_overrides.py`, nunca se salta.
- `OutSimPack` y `OutGaugePack` están en `NOT_INSIM` (no se generan todavía). OutSimPack2 se lee
  de `spec/cache/OutSimPack.txt`, que solo existe en este equipo (P3).
- **Texto:** `packets/_text.py` usa cp1252 de forma provisional hasta W2.9.
- **Verificación:** `.venv/Scripts/python scripts/verify.py`; el CI (workflow `verify`) ejecuta lo
  mismo en cada push. Sin `spec/cache/` (como en el CI), los tests que comparan con la
  especificación se saltan.
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
