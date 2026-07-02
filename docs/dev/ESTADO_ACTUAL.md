# 📍 Estado actual

> Actualizado: **2026-07-02** — sesión S06
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**Fase 1 COMPLETADA. Fase 2 en curso: P11 y P13 hechos. Suite 388/388 verde.**

**P11 (composición, ✅ validado por el usuario en LFS):** `InSimApp(PacketSenderMixin)`
ya no hereda de `InSimClient`; `client.register(app)`; loader con cliente perezoso e
inyectable; dispatch en orden de dependencias. Core en **inglés** (decisión S06).

**P13 (transporte, hecho en S06 tras validar P11):** `InSimTransport` posee sockets
TCP/UDP, hilos receptores, stop y lock **por instancia**; el cliente lo posee
(inyectable) y hace barrera+decode en `_on_raw_bytes`; `client.send = encode_packet
(puro) + transport.send`. `insim_packet_io.py` y el `send_packet` global eliminados.
`insim_state` queda como azúcar: "cliente por defecto" para helpers del mixin
(Command/CMDManager/RouteManager). **Dos clientes coexisten en un proceso** (test de
aceptación en `test_transport.py`). Smoke: `ai_control` carga, CLI OK.

**⚠️ Pendiente del usuario:** validar P13 en LFS (`lfs-insim run test_insim` /
`ai_control`) — el envío/recepción cambió de ruta interna (no bloquea seguir).

**Contexto del plan (S04):** framework a nivel profesional; romper insims aceptable.
P11–P21 en `DIAGNOSTICO.md`. Quedan gordos: P12 (reconexión, Fase 3) y P14 (config
del CWD).

## Fase activa

**Fase 2 — Arquitectura del core** (composición y API); ver `PLAN.md`.
Hecho: P11, P13 y decisión de idioma. Siguen: P14, P15, P17/P20, migración/validación
de insims.

## ▶️ Próximo paso concreto (empezar AQUÍ la próxima sesión)

**P14**: config del paquete con defaults internos (`InSimConfig` o similar) — el core
deja de importar `config.settings` del CWD (hoy lo hacen `InSimClient.__init__` e
`InSimApp.__init__`); el CLI carga la config de proyecto/env si existe. Leer antes
`config/settings.py`, `cli.py` y los dos `__init__` citados.

## Bloqueos / esperando

- Decisión pendiente (Fase 4): ¿publicar en PyPI?

## Notas para la próxima sesión

- Comando de tests: `.venv\Scripts\python.exe -m pytest -q`.
- Idioma (decisión S06): código nuevo del core en **inglés**; docs/dev, tests e insims
  en español. Ver `MODUS_OPERANDI.md` § 5.
- Los golden-bytes y tests de packet_io de Fase 1 siguen válidos; los de loader y
  dispatch ya están adaptados a la nueva API (registro en cliente).
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py`
  y `pip install -e ".[dev]"`.
- Pendientes sin fase: P8, P9, migración de rutas a JSON (ver `PLAN.md` § Ideas).
