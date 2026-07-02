# 📍 Estado actual

> Actualizado: **2026-07-02** — sesión S04
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**Protocolo actualizado a LFS 0.8C5** (suite **233/233 verde**): nuevo ISP_SET + ISF.SET,
NPL.Sp2→RIFlags (RIF/SAI), CCI.RETIRED, NLP_MAX_CARS=48, HOSTF nuevos. La spec completa
0.8C5 está restaurada en `docs/InSim.txt` (LFS ya solo distribuye un puntero; la fuente
es lfs.net/programmer/insim).

**Plan reorientado (decisión del usuario en S04):** llevar el **framework a nivel
profesional** (usable por otros desarrolladores, buenas prácticas); romper los insims
existentes es aceptable. Auditoría del core hecha → **P11–P20** en `DIAGNOSTICO.md`
(los gordos: P11 herencia invertida InSimApp→InSimClient + coup d'état, P12 sin
reconexión, P13 singletons globales, P14 core acoplado a `config/` del CWD).
`PLAN.md` reescrito: Fases 1–4 = core (red de seguridad → arquitectura → robustez → DX);
Fases 5–6 = ai_control (el plan antiguo).

## Fase activa

**Fase 1 — Red de seguridad del CORE** (ver `PLAN.md`). Sin empezar.

## ▶️ Próximo paso concreto (empezar AQUÍ la próxima sesión)

Arrancar la Fase 1 por los **golden-bytes de serialización** (tests que fijan los bytes
exactos que produce cada paquete enviable), porque son la red imprescindible antes de
tocar la ruta encode (P19) y la arquitectura (Fase 2). Después: golden-bytes de
decodificación y tests de dispatch/loader/packet_io con sockets falsos.

## Bloqueos / esperando

- Decisión pendiente del usuario (Fase 2): **idioma de la API pública del core**
  (recomendación: inglés en código/docstrings del core, español en docs/dev).
- Decisión pendiente (Fase 4): ¿publicar en PyPI?

## Notas para la próxima sesión

- Comando de tests: `.venv\Scripts\python.exe -m pytest -q`.
- La suite ahora incluye `tests/test_protocol_08c5.py` (12 tests del protocolo nuevo).
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py`
  y `pip install -e ".[dev]"`.
- Pendientes sin fase: P8, P9, migración de rutas a JSON (ver `PLAN.md` § Ideas).
