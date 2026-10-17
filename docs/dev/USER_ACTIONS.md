# 🙋 Tus acciones — AP_LFS_InSim (lfs_insim)
> **1 pendiente** · 🚧 U15 bloquea W14.2 (publicar 0.9.1) · actualizado en S30
>
> Todo lo de aquí necesita tus manos o tu criterio: el agente no puede hacerlo o no puede
> comprobarlo. **Nunca editas este archivo**: cuéntale el resultado al agente y él cerrará la tarjeta.

## ⏳ Pendientes

### U15 — 🚧 ¿Publico 0.9.1 con el arreglo de W14, y arreglo también `every()` (W14.3)?          ⏳ · bloquea: W14.2 · abierta en S30
**Tipo:** decidir          **Tiempo:** ~1 min
**Por qué:** el arreglo de P12 está en `dev`, sin publicar; `lfs-ai-control` lo rodea mientras tanto. Publicar
necesita tu permiso. `every()` tiene el mismo defecto (P13) y entraría en la misma versión si lo apruebas.
**Pasos:**
  1. Dime una de estas: «publica 0.9.1» (solo W14.1), «arregla también every() y publica» (recomendada: un
     solo arreglo coherente para todo lo que se registra tarde), o «espera».
**Resultado esperado:** con permiso, 0.9.1 en PyPI y fijada en `lfs-ai-control`.
**Señales de fallo:** no aplica (es una decisión).
**Si falla, dime:** no aplica.

## ✅ Cerradas (recientes; el registro completo está en LOG.md)
- **U14** — Grupo P con otra persona: hecho con una segunda cuenta del usuario; 8 PASS en la segunda pasada (2026-10-17, S29).
- **U11** — Como invitado, los comandos de otra persona se ignoran: «Ahora sí, salió perfecto» (2026-10-17, S29).
- **U13** — Qué es «un plano»: «Me vale tal cual» → lista de pasos: ir a un instante, seguir a un coche con una vista (`IS_SCC`), cámara libre a una posición en N segundos (`IS_CPP`), esperar (2026-10-14, S23).
- **U12** — Probar si escribir y combinar plugins es cómodo: descartada por el usuario («No lo haré… ya iremos viendo si es cómodo o no a medida que avancemos») (2026-10-14, S21).
- **U10** — Comandos como invitado: W9 antes de W6, porque la primera aplicación los necesita; se detalla en la próxima sesión (2026-10-13, S18).
- **U8** — Probar W8.2–W8.4 en LFS real: cerrada por el usuario («U8 cerrada») con los resultados de S18 (comandos, unidades 1,002, `watch()`; P9 arreglado) (2026-10-13, S18).
- **U9** — Listas cortas en `IS_REO` / `IS_HCP`: «Sigamos tu recomendación» → se rellenan con ceros (2026-10-13, S18).
- **U7** — Probar `insim.on.` / `insim.send.` en VS Code: «va perfecto» (2026-10-13, S16).
- **U6** — Cuentas y publicador en TestPyPI y PyPI: hecha en S14 con el navegador (cuentas y 2FA, el usuario; formularios, el agente). `lfs-insim` figura en «Pending publishers» de ambos con `AdrianPascarella/AP_LFS_InSim`, `publish.yml` y entornos `testpypi` / `pypi`. ~~Falta (opcional) el entorno `pypi` en GitHub con revisor.~~ Creado en S14 (comprobado en S15).
- **U5** — Reinstalar LFS limpio: lo hizo el agente a petición del usuario; 0.8C31 en `C:\LFS` (2026-10-12, S9).
- **U4** — `TextStart` como índice del `str`, arreglado en el paquete: sí, la recomendada (2026-10-12, S8).
- **U3** — Campo `Caption` en `IS_BTN`: sí, la recomendada (2026-10-12, S8).
- **U2** — Fusionar `dev` en `main`: sí (2026-10-12, S4). Avance rápido a `c97e62d`; `spec` lanzado a mano, en verde.
- **U1** — Licencia: MIT (2026-10-12, S2). `LICENSE` añadido y declarado en `pyproject.toml`.
