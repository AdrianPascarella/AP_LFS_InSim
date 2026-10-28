# AP_LFS_InSim (lfs_insim)

## Contexto de trabajo persistente — LÉELO PRIMERO

Este proyecto guarda su contexto en archivos, no en la sesión de chat. **Al empezar CUALQUIER sesión,
antes de tocar nada:** cambia a la rama `dev`, haz pull y lee `docs/dev/STATE.md` (dónde se quedó el
trabajo y cuál es el siguiente paso); después, `docs/dev/USER_ACTIONS.md`, la última entrada de
`docs/dev/LOG.md` y la fase activa de `docs/dev/PLAN.md`. Las reglas completas están en
`docs/dev/PROTOCOL.md` y son obligatorias. **Al cerrar la sesión o al llegar a un hito:** actualiza
`STATE.md`, añade una entrada a `LOG.md`, marca lo hecho en `PLAN.md`, ejecuta el control de cierre
(`python scripts/close_check.py --context-dir docs/dev`), haz commit y push.

**Hilos sin sesión (una rutina de la nube, un job del CI, `claude -p`, un subagente):** trabaja en
`dev`, nunca en la rama por defecto salvo que te lo digan; antes de cambiar nada lee
`docs/dev/STATE.md` y, para el tema que tocas, `docs/dev/DECISIONS.md` y `docs/dev/ARCHITECTURE.md`;
el comando de verificación está declarado en `factory.json` y tiene que pasar; nunca hagas merge a
`main` ni reescribas la historia de los archivos de contexto.

## Qué es este repositorio

`lfs_insim`: una biblioteca de Python para el protocolo InSim de Live for Speed (InSim, OutSim,
OutGauge), que se instala con `pip install lfs-insim` y se usa con `import lfs_insim`. Python ≥ 3.11,
sin dependencias externas. Las aplicaciones que la usan viven en otros proyectos; aquí solo hay
ejemplos cortos. Todo lo que leen los usuarios de la biblioteca va en inglés; la documentación de
trabajo (`docs/dev`), en castellano.

El proyecto anterior, empezado de nuevo en S1, está en la rama `refactor/estabilizacion` y en las
etiquetas `archivo/*`: solo se consulta, y nunca se borra.
