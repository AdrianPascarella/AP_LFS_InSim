# 🙋 Tus acciones — AP_LFS_InSim (lfs_insim)
> **1 pendiente** · 1 bloquea (W5.5 y W5.6; no bloquea W5.4) · actualizado en S13
>
> Todo lo de aquí necesita tus manos o tu criterio: el agente no puede hacerlo o no puede
> comprobarlo. **Nunca editas este archivo**: cuéntale el resultado al agente y él cerrará la tarjeta.

## ⏳ Pendientes

### U6 — Cuentas y publicador en TestPyPI y PyPI          ⏳ · bloquea: W5.5 y W5.6 · abierta en S13
**Tipo:** hacer          **Tiempo:** ~15 min
**Por qué:** el workflow `publish.yml` (ya en `dev`) publica sin tokens, con Trusted Publishing; para
eso cada índice tiene que saber que ese workflow de ese repositorio puede publicar `lfs-insim`. Solo
tú puedes crear las cuentas y rellenar el formulario. Sin esto no se puede probar la instalación
(W5.5) ni publicar (W5.6).
**Pasos:**
  1. Cuenta en https://test.pypi.org y en https://pypi.org (son independientes; las dos piden
     verificar el correo y activar la verificación en dos pasos).
  2. En TestPyPI: *Your account → Publishing → Add a new pending publisher* (en la pestaña GitHub):
     - PyPI Project Name: `lfs-insim`
     - Owner: `AdrianPascarella`
     - Repository name: `AP_LFS_InSim`
     - Workflow name: `publish.yml`
     - Environment name: `testpypi`
  3. Lo mismo en PyPI con Environment name: `pypi`.
  4. (Opcional, recomendado) En GitHub: *Settings → Environments → New environment* `pypi`, con
     «Required reviewers» tú mismo: así publicar en PyPI pide un clic de confirmación. Si no los
     creas, GitHub los crea vacíos al primer uso.
**Resultado esperado:** en cada índice, `lfs-insim` aparece en «Pending publishers». El nombre aún no
queda reservado hasta la primera publicación.
**Señales de fallo:** que el nombre `lfs-insim` esté ocupado en el índice (el formulario avisa), o que
el formulario rechace el repositorio.
**Si falla, dime:** el mensaje exacto del formulario y en cuál de los dos índices ocurre.

## ✅ Cerradas (recientes; el registro completo está en LOG.md)
- **U5** — Reinstalar LFS limpio: lo hizo el agente a petición del usuario; 0.8C31 en `C:\LFS` (2026-10-12, S9).
- **U4** — `TextStart` como índice del `str`, arreglado en el paquete: sí, la recomendada (2026-10-12, S8).
- **U3** — Campo `Caption` en `IS_BTN`: sí, la recomendada (2026-10-12, S8).
- **U2** — Fusionar `dev` en `main`: sí (2026-10-12, S4). Avance rápido a `c97e62d`; `spec` lanzado a mano, en verde.
- **U1** — Licencia: MIT (2026-10-12, S2). `LICENSE` añadido y declarado en `pyproject.toml`.
