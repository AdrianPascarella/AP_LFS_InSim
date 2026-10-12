# 🙋 Tus acciones — AP_LFS_InSim (lfs_insim)
> **1 pendiente** · bloquea W3.1 (la prueba en vivo, al final de W3), no lo siguiente · actualizado en S9
>
> Todo lo de aquí necesita tus manos o tu criterio: el agente no puede hacerlo o no puede
> comprobarlo. **Nunca editas este archivo**: cuéntale el resultado al agente y él cerrará la tarjeta.

## ⏳ Pendientes

### U5 — Reinstalar LFS limpio          ⏳ · bloquea: W3.1 · abierta en S9
**Tipo:** hacer          **Tiempo:** ~15 min
**Por qué:** la instalación actual tiene cosas que no puso el juego (por ejemplo,
`data/script/autoexec.lfs` con `/insim=29999`, que seguramente añadió un programa InSim que
instalaste). La prueba en vivo (W3.1) se hace sobre el juego tal como viene.
**Pasos:**
  1. Desinstalar LFS (`C:\LFS\UninstallLFS.exe`) e instalarlo de nuevo desde lfs.net en `C:\LFS`.
  2. Iniciar sesión con tu licencia si te lo pide.
  3. Si quieres, devolver tus setups y skins desde la copia:
     `C:\Users\pasca\proyectos\_archivo_AP_LFS_InSim\LFS_backup_2026-10-12` (carpetas `setups`,
     `skins` y `skins_dds`, que van dentro de `C:\LFS\data`).
**Resultado esperado:** LFS arranca normal desde `C:\LFS\LFS.exe`.
**Señales de fallo:** no arranca, pide algo raro o la ruta es otra.
**Si falla, dime:** qué ves y en qué ruta ha quedado instalado. Si sale bien, dime solo «hecho» y
qué versión de LFS es (se ve en la pantalla de inicio).

## ✅ Cerradas (recientes; el registro completo está en LOG.md)
- **U4** — `TextStart` como índice del `str`, arreglado en el paquete: sí, la recomendada (2026-10-12, S8).
- **U3** — Campo `Caption` en `IS_BTN`: sí, la recomendada (2026-10-12, S8).
- **U2** — Fusionar `dev` en `main`: sí (2026-10-12, S4). Avance rápido a `c97e62d`; `spec` lanzado a mano, en verde.
- **U1** — Licencia: MIT (2026-10-12, S2). `LICENSE` añadido y declarado en `pyproject.toml`.
