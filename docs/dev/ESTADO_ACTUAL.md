# 📍 Estado actual

> Actualizado: **2026-07-02** — sesión S06
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**Fase 1 COMPLETADA. Fase 2 en curso: P11 hecho. Suite 391/391 verde.**

**P11 (composición) resuelto:** `InSimApp(PacketSenderMixin)` ya no hereda de
`InSimClient`. Un cliente, N apps: `client.register(app)`; el loader crea el cliente
de forma perezosa (`loader.client`, inyectable) y registra las apps en **orden de
dependencias**. Sin coup d'état ni aplanado de `modules[]` (ahora `apps`). Cambio
deliberado: el orden de dispatch pasa a ser dependencias→dependientes (antes era el
inverso, un bug latente). Core reescrito en **inglés** (decisión S06). Los 3 insims
cargan sin cambios (superficie de `InSimApp` conservada); smoke tests hechos:
`ai_control` se registra tras `users_management`, CLI `list` funciona.

**✅ P11 validado por el usuario en LFS** (mismo día): los insims corren
correctamente en vivo con la nueva arquitectura.

**Contexto del plan (S04):** framework a nivel profesional; romper insims aceptable.
P11–P21 en `DIAGNOSTICO.md`. Quedan gordos: P12 (reconexión), P13 (singletons),
P14 (config del CWD).

## Fase activa

**Fase 2 — Arquitectura del core** (composición y API); ver `PLAN.md`.
Hecho: P11 + decisión de idioma. Siguen: P13, P14, P15, P17/P20, migración/validación
de insims.

## ▶️ Próximo paso concreto (empezar AQUÍ la próxima sesión)

**P13**: encapsular la conexión — objeto transporte TCP/UDP inyectado en el cliente;
eliminar los singletons de `insim_state` (cliente y sockets globales); `send` viaja por
el cliente (`app.client.send`), no por globals. Criterio: dos clientes pueden coexistir
en un proceso (test). Leer antes `insim_state.py`, `insim_packet_io.py`,
`insim_packet_sender.py` y `packet_sender_mixin.py`.

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
