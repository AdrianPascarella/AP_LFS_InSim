# 🙋 Tus acciones — AP_LFS_InSim (lfs_insim)
> **1 pendiente** · 0 bloquean · orden recomendado: U2 · actualizado en S3
>
> Todo lo de aquí necesita tus manos o tu criterio: el agente no puede hacerlo o no puede
> comprobarlo. **Nunca editas este archivo**: cuéntale el resultado al agente y él cerrará la tarjeta.

## ⏳ Pendientes

### U2 — ¿Fusiono `dev` en `main` ahora que W1 está cerrada?          ⏳ · bloquea: nada · abierta en S3
**Tipo:** decidir          **Tiempo:** ~1 min
**Por qué:** GitHub solo ejecuta los workflows programados desde la rama por defecto (`main`), que
hoy está vacía. Hasta que `main` reciba W1, el aviso semanal de que lfs.net ha cambiado la
especificación no funciona (el CI de cada push sí). Tocar `main` necesita tu permiso.
**Recomendación del agente:** sí. W1 es un hito completo y en verde (8 combinaciones de CI), y
`main` mostraría en GitHub un proyecto con licencia, README y CI en vez de estar vacía.
**Pasos:**
  1. Dime «sí, fusiona» (o «espera a W2», o lo que prefieras).
**Resultado esperado:** el agente fusiona `dev` en `main` con un merge normal, sin force-push, sube
`main` y comprueba que el workflow `spec` aparece y pasa al lanzarlo a mano.
**Señales de fallo:** —
**Si falla, dime:** —

## ✅ Cerradas (recientes; el registro completo está en LOG.md)
- **U1** — Licencia: MIT (2026-10-12, S2). `LICENSE` añadido y declarado en `pyproject.toml`.
