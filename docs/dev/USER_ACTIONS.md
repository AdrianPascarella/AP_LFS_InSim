# 🙋 Tus acciones — AP_LFS_InSim (lfs_insim)
> **1 pendiente** (U7, validar en tu editor; bloquea W7.6) · actualizado en S15
>
> Todo lo de aquí necesita tus manos o tu criterio: el agente no puede hacerlo o no puede
> comprobarlo. **Nunca editas este archivo**: cuéntale el resultado al agente y él cerrará la tarjeta.

## ⏳ Pendientes

### U7 — Probar `insim.on.` e `insim.send.` en tu VS Code          ⏳ · bloquea: W7.6 (la guía enseña esta forma) · abierta en S15
**Tipo:** validar          **Tiempo:** ~10 min
**Por qué:** W7 existe para que veas la lista de paquetes al escribir. mypy ya lo comprueba, pero
cómo lo enseña Pylance (la lista, la ayuda, los subrayados) solo lo puedes ver tú.
**Pasos:**
  1. En VS Code, abre `C:\Users\Adrian\Projects\AP_LFS_InSim` (rama `dev`, con W7.4 o posterior) y
     elige como intérprete `.venv\Scripts\python.exe` (Ctrl+Shift+P → «Python: Select Interpreter»).
  2. Crea un archivo de prueba en la raíz (por ejemplo `prueba_w7.py`; no lo subas) con:
     ```python
     from lfs_insim import InSim, received
     insim = InSim()
     ```
  3. Escribe `insim.on.` y mira la lista; luego `insim.send.` y mira la lista.
  4. Escribe `insim.send.IS_MST(` y mira qué campos te propone; pasa el ratón por encima de `IS_MST`.
  5. Escribe `@insim.on.IS_NPL` y debajo `def f(packet: received.` y mira la lista.
  6. Opcional: pon `"python.analysis.typeCheckingMode": "standard"` en los ajustes y prueba
     `insim.on.IS_MST` y `insim.send.IS_MST(Msg=3)`: deberían salir subrayados.
**Resultado esperado:** en 3, `on.` lista solo lo que envía LFS (54, con `IS_NPL` y sin `IS_MST`) y
`send.` solo lo que envías tú (27, con `IS_MST` y sin `IS_NPL`); en 4, los campos (`Msg`, `ReqI`) y la
ayuda del paquete; en 5, la lista de `received`; en 6, los subrayados.
**Señales de fallo:** la lista mezcla direcciones o sale vacía; `send.IS_MST(` no propone campos
(solo `*args, **kwargs`); no se ve ayuda al pasar el ratón; ningún subrayado ni en modo `standard`.
**Si falla, dime:** en qué paso, qué ves (una captura vale) y tu versión de Pylance. Y lo más
importante: si te resulta cómodo así o lo cambiarías.

## ✅ Cerradas (recientes; el registro completo está en LOG.md)
- **U6** — Cuentas y publicador en TestPyPI y PyPI: hecha en S14 con el navegador (cuentas y 2FA, el usuario; formularios, el agente). `lfs-insim` figura en «Pending publishers» de ambos con `AdrianPascarella/AP_LFS_InSim`, `publish.yml` y entornos `testpypi` / `pypi`. ~~Falta (opcional) el entorno `pypi` en GitHub con revisor.~~ Creado en S14 (comprobado en S15).
- **U5** — Reinstalar LFS limpio: lo hizo el agente a petición del usuario; 0.8C31 en `C:\LFS` (2026-10-12, S9).
- **U4** — `TextStart` como índice del `str`, arreglado en el paquete: sí, la recomendada (2026-10-12, S8).
- **U3** — Campo `Caption` en `IS_BTN`: sí, la recomendada (2026-10-12, S8).
- **U2** — Fusionar `dev` en `main`: sí (2026-10-12, S4). Avance rápido a `c97e62d`; `spec` lanzado a mano, en verde.
- **U1** — Licencia: MIT (2026-10-12, S2). `LICENSE` añadido y declarado en `pyproject.toml`.
