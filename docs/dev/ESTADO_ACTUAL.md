# 📍 Estado actual

> Actualizado: **2026-07-02** — sesión S05
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**Fase 1 al 67 % (4 de 6 ítems), suite 359/359 verde.** Congelado por tests:
- **Encode** (`test_golden_bytes_send.py`, 63): bytes exactos de los 27 paquetes enviables.
- **Decode** (`test_golden_bytes_decode.py`, 20): bytes según spec 0.8C5 → dataclass.
- **Dispatch** (`test_client_dispatch.py`, 14): orden master→módulos, aislamiento de
  errores, keep-alive reactivo, lifecycle, thread-pool.
- **Loader** (`test_loader.py`, 29): dependencias, coup d'état + aplanado, caché,
  rollback del master, fallos.

Hallazgos nuevos registrados en `DIAGNOSTICO.md`: **P21** (enviar ISP_REO/ISP_HCP/
ISP_IPB-con-bans falla siempre: `_extract_values` no aplana listas fijas) y ampliación
de **P20** (un InSim sin `__init__.py` muere con error críptico).

**Contexto del plan (S04):** llevar el **framework a nivel profesional**; romper los
insims existentes es aceptable. Auditoría del core → **P11–P21** en `DIAGNOSTICO.md`
(los gordos: P11 herencia invertida + coup d'état, P12 sin reconexión, P13 singletons,
P14 core acoplado a `config/` del CWD). Fases 1–4 = core; Fases 5–6 = ai_control.

## Fase activa

**Fase 1 — Red de seguridad del CORE** (ver `PLAN.md`). Quedan 2 ítems: packet_io
con socket falso y la fixture de "LFS falso".

## ▶️ Próximo paso concreto (empezar AQUÍ la próxima sesión)

Terminar la Fase 1: tests de **packet_io** con socket falso — reensamblado TCP
(paquetes fragmentados y pegados), byte Size=0, cierre de conexión — y la fixture
reutilizable de **"LFS falso"** (servidor TCP loopback que reproduce trazas).
Leer `src/lfs_insim/insim_packet_io.py` antes de empezar.

## Bloqueos / esperando

- Decisión pendiente del usuario (Fase 2): **idioma de la API pública del core**
  (recomendación: inglés en código/docstrings del core, español en docs/dev).
- Decisión pendiente (Fase 4): ¿publicar en PyPI?

## Notas para la próxima sesión

- Comando de tests: `.venv\Scripts\python.exe -m pytest -q`.
- Golden-bytes en `tests/test_golden_bytes_send.py` y `tests/test_golden_bytes_decode.py`;
  el helper `encode()` de los tests replica la ruta real de `send_packet` sin socket.
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py`
  y `pip install -e ".[dev]"`.
- Pendientes sin fase: P8, P9, migración de rutas a JSON (ver `PLAN.md` § Ideas).
