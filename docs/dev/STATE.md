# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-12 (S12): **W3 hecha entera.** W3.1 validó la biblioteca en el LFS real:
> InSim (menú y carrera con IA y coche mod), OutGauge, OutSim y `OutSimPack2`, sin un solo fallo
> de lectura. Encontró y arregló un error: `OutGaugePack.Car` lleva el SkinID de un mod. El agente
> maneja LFS sin el usuario con `tests/lfs_screen.ps1` (PROTOCOL §13). `cfg.txt` está restaurado:
> para repetir OutSim/OutGauge en vivo hay que pedir permiso de nuevo. Tests en verde.
> **W4 detallada con el usuario en S12** (7 tareas en `PLAN.md`; decisiones en `API_DESIGN.md`).
> W4.1 hecha: `IS_MSO.text`, con un mecanismo para añadir propiedades escritas a mano a los
> paquetes generados (`packets/_extras.py` + `spec_overrides.EXTRAS`). W4.2 hecha:
> `await insim.request(IS_STA)` y `request_all(IS_NPL)` (`_requests.py`). W4.3 hecha: `Roster`
> en `lfs_insim.state` (decisiones en `API_DESIGN.md`). W4.4 hecha: `insim.say()` e
> `insim.command()`. W4.5 hecha: `@insim.on_command("hello")` (`_commands.py`; el nombre
> cambió por un choque con `insim.command()`, falta que el usuario lo vea).
> W4.6 hecha: `examples/` (`hello`, `who`, `gauge`, `buttons`), probados en `test_examples.py`.
> W4.7 hecha: los cuatro, bien en el LFS real; `say(to=0)` pasó a `IS_MSL` (LFS rechaza `IS_MTC`
> en un jugador). `cfg.txt` restaurado.
> **▶️ SIGUIENTE: W4.8 — `lfs_insim.text.plain()`** (propuesta en `PLAN.md`, que el usuario
> confirme el nombre), y con ella W4 queda cerrada. `_connection.py` va por ~405 líneas.

## Dónde estamos
Fase activa: **W4 — La API de alto nivel y los ejemplos**, detallada en S12 (`PLAN.md`). W2 y W3
están hechas enteras. Prueba en vivo: `tests/live_lfs.py` (cómo ejecutarla, en su docstring).

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
