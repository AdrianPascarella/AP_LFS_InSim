# 📍 Estado — AP_LFS_InSim (lfs_insim)
> Actualizado: 2026-10-12 (S3): **W1 cerrada.** Hay CI en GitHub (Python 3.11–3.14, Linux y
> Windows, en verde) y un script que descarga la especificación y avisa si cambia. Árbol limpio y
> subido al cerrar.
> **▶️ SIGUIENTE: detallar W2 con el usuario** (generar los paquetes de InSim, OutSim y OutGauge a
> partir de `spec/cache/`): qué se genera, cómo es el generador, si el código generado va en git
> (P3) y cómo se prueba. Antes, si el usuario contesta U2, fusionar en `main`.

## Dónde estamos
Fase cerrada: **W1 — Cimientos** (W1.1–W1.5). La siguiente, **W2**, solo está esbozada en
`PLAN.md`: se detalla con el usuario al abrirla. No hay nada a medias.

- **Verificación:** `.venv/Scripts/python scripts/verify.py`. El CI (workflow `verify`) ejecuta lo
  mismo en cada push (lo que detecta, en la Configuración de `PROTOCOL.md`).
- **Especificación:** `.venv/Scripts/python scripts/fetch_spec.py` deja el texto en `spec/cache/`
  (ignorado por git) y lo compara con `spec/checked.json` (0.8C27, INSIM_VERSION 10). W2 genera a
  partir de `spec/cache/InSim.txt` y `spec/cache/OutSimPack.txt`.
- **API:** `docs/dev/API_DESIGN.md` es la referencia (D1–D6). El código de W2–W4 se escribe para
  que sus ejemplos funcionen tal cual.
- Lo decidido en S1 sigue vigente (`LOG.md` S1): biblioteca sin dependencias, Python ≥ 3.11,
  especificación descargada, aplicaciones aparte y lo público en inglés.

El proyecto anterior está en la rama `refactor/estabilizacion` y en las etiquetas `archivo/*`. Se
consulta, no se copia.

## Lo que te espera
**1 acción pendiente, que no bloquea** → ver `USER_ACTIONS.md` (U2: decidir si `dev` se fusiona ya
en `main`).

## Restricciones ahora mismo
- En este equipo solo hay Python 3.14. Las demás versiones las comprueba el CI.
- El `python` de la terminal es el de streamer-project: aquí siempre `.venv/Scripts/python` (§13).
- El aviso semanal de cambios en lfs.net (workflow `spec`) no funciona hasta que `main` tenga W1
  (U2).
- El repositorio es público.
