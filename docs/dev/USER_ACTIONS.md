# 🙋 Tus acciones — AP_LFS_InSim (lfs_insim)
> **2 pendientes (U13 bloquea W6.3)** · actualizado en S22 · U13 lo primero de la próxima sesión; U11 cuando haya
> alguien más en tu servidor
>
> Todo lo de aquí necesita tus manos o tu criterio: el agente no puede hacerlo o no puede
> comprobarlo. **Nunca editas este archivo**: cuéntale el resultado al agente y él cerrará la tarjeta.

## ⏳ Pendientes

### U13 — Decir qué es «un plano» de la cámara libre          ⏳ · bloquea: W6.3 · abierta en S21 (tarjeta en S22)
**Tipo:** decidir          **Tiempo:** ~5 min, sin el LFS delante
**Por qué:** `FreeCam` (W6.3) graba «planos guionizados» sobre una repetición, y el agente no puede elegir por ti
qué tiene que poder describir uno: de eso depende el formato del archivo y lo que se programa.
**Pasos:**
  1. Lee la propuesta del agente: un archivo pequeño con una lista de pasos que se ejecutan en orden:
     ir a un instante de la repetición; seguir a un coche con una vista del juego (`IS_SCC`); cámara libre de A a B
     en N segundos, con posición y hacia dónde mira (`IS_CPP`, LFS suaviza); esperar N segundos. Más adelante,
     planos generados a partir de los eventos del registrador. Con eso grabas tomas concretas con OBS.
  2. Di si te vale tal cual, qué le quitarías o añadirías, o qué tenías tú en mente.
**Resultado esperado:** una respuesta con la que el agente pueda escribir el formato del plano.
**Señales de fallo:** —
**Si falla, dime:** —

### U11 — Probar que, como invitado, los comandos de otra persona se ignoran          ⏳ · bloquea: nada · abierta en S19
**Tipo:** validar          **Tiempo:** ~5 min, con una segunda persona en tu servidor «testing»
**Por qué:** en S19 se probó en real todo lo de este ordenador, pero no había nadie más. Los tests con el LFS
falso lo cubren; esto confirma en el juego que un desconocido no puede usar tus comandos.
**Pasos:**
  1. Con tu LFS como invitado en el servidor y otra persona conectada, pídeme que arranque el programa de prueba
     (o arranca un programa tuyo con `InSim(prefix="!")` y un comando).
  2. Que la otra persona escriba `!who` y `!kick bob`.
  3. Escribe tú `!who`.
**Resultado esperado:** a la otra persona no le contesta nada ni se ejecuta nada; a ti sí te contesta (solo a ti).
**Señales de fallo:** la otra persona recibe una respuesta, o el log muestra su comando ejecutado.
**Si falla, dime:** qué escribió, qué vio cada uno y, si puedes, si su conexión salía como remota.

## ✅ Cerradas (recientes; el registro completo está en LOG.md)
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
