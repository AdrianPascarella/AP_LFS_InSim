# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-12 (S2): ya existen el paquete vacío instalable, el comando de verificación
> (visto en rojo y en verde) y la licencia MIT, y el usuario aprobó el diseño de la API. Árbol
> limpio y subido al cerrar.
> **▶️ SIGUIENTE: W1.3 (CI en GitHub Actions, Python 3.11–3.14) y W1.4 (script de la
> especificación). Ninguna de las dos depende de la otra.**

## Dónde estamos
Fase activa: **W1 — Cimientos**. Hechas: W1.1, W1.2 y W1.5. Quedan W1.3 y W1.4, sin nada a medias.

- **Verificación:** `.venv/Scripts/python scripts/verify.py` (qué detecta, en la Configuración de
  `PROTOCOL.md`). Hay que pasarla antes de dar cualquier cambio por terminado.
- **API:** `docs/dev/API_DESIGN.md` es la referencia. D1–D4 están aprobadas: asyncio por dentro
  con manejadores `def` o `async def`, `@insim.on(IS_X)`, nombres de la especificación y `Roster`
  opcional. D5 y D6 se aceptaron sin objeción. El código de W2–W4 se escribe para que sus
  ejemplos funcionen tal cual.
- Lo decidido en S1 sigue vigente (`LOG.md` S1): biblioteca sin dependencias, Python ≥ 3.11,
  especificación descargada, aplicaciones aparte y lo público en inglés.

El proyecto anterior está en la rama `refactor/estabilizacion` y en las etiquetas `archivo/*`. Se
consulta, no se copia.

## Lo que te espera
**0 acciones pendientes** → ver `USER_ACTIONS.md`.

## Restricciones ahora mismo
- En este equipo solo hay Python 3.14 (P5). Las demás versiones las comprobará el CI (W1.3), que
  todavía no existe.
- El `python` de la terminal es el de streamer-project: aquí siempre `.venv/Scripts/python` (§13).
- El repositorio es público.
