# 📍 Estado actual

> Actualizado: **2026-07-03** — sesión S07
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**Fase 1 COMPLETADA. Fase 2 en curso: P11, P13 y P14 hechos. Suite 402/402 verde.**

**P14 (config del paquete, hecho en S07):** defaults internos en
`src/lfs_insim/config.py` (`DEFAULT_CONFIG` + `build_config(overrides)`, dict plano —
se conserva la superficie `self.config.get(...)`). El core ya **no importa
`config.settings` del CWD**: `InSimClient.__init__` e `InSimApp.__init__` usan
`build_config`. El **CLI** carga la config del proyecto si existe
(`_load_project_config()`: `config.settings.INSIM_CONFIG` > env `LFS_ADMIN_PASS` >
defaults) y la pasa como `InSimLoader(config=...)` → cliente perezoso → las apps
heredan la config efectiva del cliente (antes cada app releía el CWD por su cuenta).
Con cliente inyectado, la config del loader se ignora. Smokes: `lfs-insim list` y
carga de `ai_control` OK dentro del proyecto (insim_name/prefix del proyecto llegan);
cliente/app/CLI funcionan desde un CWD **sin** `config/` (defaults del paquete).

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

**P21 arreglado (S06, adelantado de Fase 3):** validando P13 en vivo, el usuario pisó
P21 con `!test hcp` (el envío de REO/HCP/IPB-con-bans estaba roto desde siempre; el
aislamiento de errores contuvo el fallo). `_extract_values` aplana ya secuencias fijas
(con relleno de defaults) e items multi-valor; golden-bytes reales en
`TestGoldenSecuenciasFijas`.

**⚠️ Pendiente del usuario:** validar en LFS P13 **y ahora también P14** (la ruta de
config cambió: comprobar que ISI sale con el nombre/prefijo/admin del proyecto y que
los comandos con prefijo siguen respondiendo), incluyendo re-probar `!test hcp`
(debería resetear handicaps sin error en el log).

**Contexto del plan (S04):** framework a nivel profesional; romper insims aceptable.
P11–P21 en `DIAGNOSTICO.md`. Queda gordo: P12 (reconexión, Fase 3).

## Fase activa

**Fase 2 — Arquitectura del core** (composición y API); ver `PLAN.md`.
Hecho: P11, P13, P14 y decisión de idioma. Siguen: P15, P17/P20, migración/validación
de insims.

## ▶️ Próximo paso concreto (empezar AQUÍ la próxima sesión)

**P15**: definir la API pública — exports en `lfs_insim/__init__.py` (ya exporta
`DEFAULT_CONFIG`/`build_config` desde P14), `__all__` por módulo, deprecar la facade
`insim_packet_class`, eliminar los `import *` internos (`packets/insim.py` hace
`from insim_enums import *`). Leer antes `lfs_insim/__init__.py`,
`insim_packet_class.py`, `packets/__init__.py` y `packets/insim.py`. De paso caen
P17 (comentarios que mienten) y P20 (fail-fast del loader en dependencias rotas).

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
