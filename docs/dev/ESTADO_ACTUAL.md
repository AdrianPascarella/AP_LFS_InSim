# 📍 Estado actual

> Actualizado: **2026-07-02** — sesión S03
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**Fase 0 (Cimientos) COMPLETADA.** Suite **221/221 verde**. Limpieza de bajo riesgo hecha:
`utils_temp.py` eliminado; `settings.py` sin import muerto ni secretos (env +
`config/settings_local.py` gitignorado, plantilla en `settings_local.example.py`);
`interval` se queda en **10 ms** (decisión: no cambiar comportamiento; docs alineadas);
ruta de `rutas_grabadas.txt` anclada a la raíz del proyecto (sigue versionado).
Extra: `matplotlib` declarado como dependencia de `ai_control` e instalado en `.venv` (P10).

## Fase activa

**Fase 1 — Red de seguridad (tests de caracterización)** (ver `PLAN.md`). Sin empezar.

## ▶️ Próximo paso concreto (empezar AQUÍ la próxima sesión)

Arrancar la Fase 1, empezando por la **infraestructura de fixtures** (telemetría y grafo de
calles sintéticos, sin conexión a LFS), porque los demás puntos dependen de ella. Luego, en
orden: caracterizar `navigation.py`, `traffic.py` y `physics.py`.

Antes de escribir tests: leer `insims/ai_control/nav_modes/freeroam/graph.py` y
`navigation.py` para entender el modelo (RoadLink / LateralLink / Road).

## Bloqueos / esperando

Ninguno.

## Notas para la próxima sesión

- Comando de tests: `.venv\Scripts\python.exe -m pytest -q`.
- **En otro dispositivo:** copiar `config/settings_local.example.py` → `config/settings_local.py`
  con los valores locales (admin_pass, user_name, LFS_DIR); el venv necesita
  `pip install -e ".[dev]"` (ahora incluye matplotlib).
- Pendientes sin fase: P8 (padding string vacío) y P9 (`tools/setup_lfs.py` roto) —
  ver `PLAN.md` § Ideas.
