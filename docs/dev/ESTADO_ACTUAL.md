# 📍 Estado actual

> Actualizado: **2026-07-02** — sesión S06
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**Fase 1 COMPLETADA (6/6), suite 387/387 verde.** El comportamiento del core está
congelado por tests:
- **Encode** (`test_golden_bytes_send.py`, 63): bytes exactos de los 27 paquetes enviables.
- **Decode** (`test_golden_bytes_decode.py`, 20): bytes según spec 0.8C5 → dataclass.
- **Dispatch** (`test_client_dispatch.py`, 14): orden master→módulos, aislamiento de
  errores, keep-alive reactivo, lifecycle, thread-pool.
- **Loader** (`test_loader.py`, 29): dependencias, coup d'état + aplanado, caché,
  rollback del master, fallos.
- **packet_io** (`test_packet_io.py`, 28): framing TCP (fragmentado/pegado/Size=0/cierre),
  bucle UDP, `stop_all_threads`, fallos de conexión e integración real por loopback.
- **Infra nueva:** fixture `fake_lfs` (`tests/conftest.py`) — servidor TCP loopback que
  reproduce trazas hacia el cliente y registra lo que este envía. Reutilizable en toda la suite.

**Contexto del plan (S04):** llevar el **framework a nivel profesional**; romper los
insims existentes es aceptable. Auditoría del core → **P11–P21** en `DIAGNOSTICO.md`
(los gordos: P11 herencia invertida + coup d'état, P12 sin reconexión, P13 singletons,
P14 core acoplado a `config/` del CWD). Fases 1–4 = core; Fases 5–6 = ai_control.

## Fase activa

**Fase 2 — Arquitectura del core** (composición y API); ver `PLAN.md`. **Rompe la API
de los insims** (aceptado por el usuario en S04).

## ▶️ Próximo paso concreto (empezar AQUÍ la próxima sesión)

1. **Resolver con el usuario el idioma de la API pública del core** (recomendación:
   inglés en código/docstrings del core, español en docs/dev) — condiciona todo el
   código nuevo de la fase.
2. Empezar **P11**: invertir la herencia — `InSimApp` deja de heredar de `InSimClient`;
   un cliente, N apps (`client.register(app)`); eliminar coup d'état y aplanado de
   `modules[]`. Leer antes `insim_client.py`, `insim_app.py` e `insim_loader.py`.

## Bloqueos / esperando

- Decisión pendiente del usuario (Fase 2): **idioma de la API pública del core**
  (recomendación: inglés en código/docstrings del core, español en docs/dev).
- Decisión pendiente (Fase 4): ¿publicar en PyPI?

## Notas para la próxima sesión

- Comando de tests: `.venv\Scripts\python.exe -m pytest -q`.
- Los tests de Fase 1 caracterizan el comportamiento VIEJO: al hacer P11/P13 muchos
  se romperán **a propósito**; adaptarlos deliberadamente es parte del trabajo (esa
  es su función: hacer visible cada cambio de comportamiento).
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py`
  y `pip install -e ".[dev]"`.
- Pendientes sin fase: P8, P9, migración de rutas a JSON (ver `PLAN.md` § Ideas).
