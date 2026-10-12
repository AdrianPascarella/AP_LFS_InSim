# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-12 (S1) — Proyecto reiniciado desde cero: rama huérfana, protocolo de
> contexto nuevo y plan inicial. Todavía no hay código. Árbol limpio y subido al cerrar.
> **▶️ SIGUIENTE: W1.5 (diseño de la API pública con el usuario) y, en paralelo, W1.1–W1.2
> (esqueleto del paquete y comando de verificación).**

## Dónde estamos
Fase activa: **W1 — Cimientos** (abierta en S1). No hay nada hecho de W1 ni nada a medias.

Lo decidido hasta ahora (detalle y motivos en `LOG.md` S1):
- Biblioteca `lfs_insim` (`pip install lfs-insim`), Python ≥ 3.11, sin dependencias, en PyPI.
- Las aplicaciones van en proyectos aparte; aquí solo `examples/`.
- La especificación se descarga de lfs.net; en git solo su versión; los paquetes se generan.
- Código y documentación pública en inglés; documentación de trabajo en castellano.

El proyecto anterior está en la rama `refactor/estabilizacion` (que de momento es la rama por
defecto en GitHub) y en las etiquetas `archivo/*`. Se consulta, no se copia.

## Lo que te espera
**1 acción pendiente** (ninguna bloquea) → ver `USER_ACTIONS.md`. Empieza por **U1** (licencia).

## Restricciones ahora mismo
- No hay comando de verificación (P1): nada de código se da por terminado hasta W1.2.
- Este equipo solo tiene Python 3.14 (P5): las demás versiones, en el CI (W1.3).
- El repositorio es público.
