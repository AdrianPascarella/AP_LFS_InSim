# 📍 Estado actual

> Actualizado: **2026-07-02** — sesión S05
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**Golden-bytes de Fase 1 hechos** (suite **316/316 verde**): la ruta de encode
(`prepare→pack`, 63 tests sobre los 27 paquetes enviables) y la de decode
(`decode_packet`, 20 tests con bytes construidos según spec 0.8C5) quedan congeladas
byte a byte. Descubierto y registrado **P21**: enviar ISP_REO, ISP_HCP o ISP_IPB con
bans **falla siempre** (`_extract_values` no aplana listas de formato fijo); queda
caracterizado con `pytest.raises` hasta que se arregle en P19/Fase 3.

**Contexto del plan (S04):** llevar el **framework a nivel profesional**; romper los
insims existentes es aceptable. Auditoría del core → **P11–P21** en `DIAGNOSTICO.md`
(los gordos: P11 herencia invertida + coup d'état, P12 sin reconexión, P13 singletons,
P14 core acoplado a `config/` del CWD). Fases 1–4 = core; Fases 5–6 = ai_control.

## Fase activa

**Fase 1 — Red de seguridad del CORE** (ver `PLAN.md`). 2 de 6 ítems completados
(golden-bytes de serialización y de decodificación).

## ▶️ Próximo paso concreto (empezar AQUÍ la próxima sesión)

Seguir la Fase 1 con los tests de **dispatch de `InSimClient`** (registro de handlers
activos, orden master→módulos, aislamiento de errores por handler) y del **loader**
(dependencias, coup d'état, fallos). Después: **packet_io** con socket falso
(reensamblado TCP fragmentado/pegado, Size=0, cierre) y la fixture de "LFS falso".

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
