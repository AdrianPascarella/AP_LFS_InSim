# 🙋 Tus acciones — AP_LFS_InSim (lfs_insim)
> **2 pendientes** · actualizado en S18 · 🚧 U8 bloquea 0.4.0 · orden: U9 (decidir, 1 min), luego U8
>
> Todo lo de aquí necesita tus manos o tu criterio: el agente no puede hacerlo o no puede
> comprobarlo. **Nunca editas este archivo**: cuéntale el resultado al agente y él cerrará la tarjeta.

## ⏳ Pendientes

### U8 — 🚧 Permiso para abrir LFS y probar W8.2–W8.4          ⏳ · bloquea: publicar 0.4.0 · abierta en S18
**Tipo:** validar          **Tiempo:** ~10 min (lo conduce el agente; tú solo das permiso y miras)
**Por qué:** W8.2 (comandos con tipos), W8.3 (unidades) y W8.4 (`watch()`) solo se han probado contra el LFS
falso. Una versión publicada no se puede resubir.
**Pasos:**
  1. Decirle al agente «abre LFS» (o abrirlo tú en `C:\LFS` con `/insim 29999`).
  2. El agente teclea `!speed abc`, `!speed ?` y un grupo de comandos, y compara `CompCar.speed_kmh` con
     OutGauge con un coche en pista.
**Resultado esperado:** `!speed abc` contesta con el uso; `!speed ?` con la ayuda; las dos velocidades
coinciden (±1 km/h).
**Señales de fallo:** sin respuesta en el chat de LFS, o velocidades que no coinciden.
**Si falla, dime:** lo que veas en el chat de LFS; el agente guarda el informe en `tests/live_reports`.

### U9 — Listas cortas en `IS_REO` / `IS_HCP`          ⏳ · bloquea: nada · abierta en S18
**Tipo:** decidir          **Tiempo:** ~1 min
**Por qué:** hoy `IS_REO(NumP=3, PLID=[5, 2, 9])` da `PacketError: expected 48 items, got 3`; hay que escribir
los 45 ceros a mano (y las 32 entradas de `IS_HCP`). Es claro, pero incómodo.
**Pasos:**
  1. Elegir: **(a, recomendada)** rellenar con ceros al enviar las listas de longitud fija que InSim.txt
     declara así (sobra lo que falta; pasarse de largo sigue siendo error); **(b)** dejarlo como está.
**Resultado esperado:** con (a), `IS_REO(NumP=3, PLID=[5, 2, 9])` se envía bien.
**Señales de fallo:** no aplica (es una decisión).
**Si falla, dime:** no aplica.

## ✅ Cerradas (recientes; el registro completo está en LOG.md)
- **U7** — Probar `insim.on.` / `insim.send.` en VS Code: «va perfecto» (2026-10-13, S16).
- **U6** — Cuentas y publicador en TestPyPI y PyPI: hecha en S14 con el navegador (cuentas y 2FA, el usuario; formularios, el agente). `lfs-insim` figura en «Pending publishers» de ambos con `AdrianPascarella/AP_LFS_InSim`, `publish.yml` y entornos `testpypi` / `pypi`. ~~Falta (opcional) el entorno `pypi` en GitHub con revisor.~~ Creado en S14 (comprobado en S15).
- **U5** — Reinstalar LFS limpio: lo hizo el agente a petición del usuario; 0.8C31 en `C:\LFS` (2026-10-12, S9).
- **U4** — `TextStart` como índice del `str`, arreglado en el paquete: sí, la recomendada (2026-10-12, S8).
- **U3** — Campo `Caption` en `IS_BTN`: sí, la recomendada (2026-10-12, S8).
- **U2** — Fusionar `dev` en `main`: sí (2026-10-12, S4). Avance rápido a `c97e62d`; `spec` lanzado a mano, en verde.
- **U1** — Licencia: MIT (2026-10-12, S2). `LICENSE` añadido y declarado en `pyproject.toml`.
