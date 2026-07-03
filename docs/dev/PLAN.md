# 🗺️ Plan de trabajo — AP_LFS_InSim

> Plan por fases. Cada fase tiene criterios de aceptación. Se marca lo completado con `[x]`.
> Referencias `Pn` remiten a los problemas de `DIAGNOSTICO.md`.
> **Rama de trabajo:** todo ocurre en `refactor/estabilizacion`; merge a `main` solo cuando
> el proyecto esté estable (ver "Merge a `main`" al final).
>
> **Reorientación (S04, 2026-07-02):** el usuario fijó como objetivo llevar el **framework**
> a nivel profesional (usable felizmente por otros desarrolladores, buenas prácticas).
> Romper los insims existentes es aceptable. El plan antiguo de `ai_control` (caracterizar →
> estabilizar → trocear) se conserva como Fases 5–6, después del core.

---

## Fase 0 — Cimientos  ✅ COMPLETADA (S03, 2026-07-02)

**Objetivo:** entorno reproducible, suite corriendo y deuda de bajo riesgo eliminada.

- [x] Crear `.venv` e instalar `pip install -e ".[dev]"` (**P1**) — S02, Python 3.14.6 + pytest 9.1.1
- [x] Ejecutar `pytest`; registrar cuántos de los 221 tests pasan (**P1**) — S02, 216/221 en el primer run
- [x] Dejar los tests en verde — S02, corregidos 5 tests de padding erróneos → **221/221** (ver P8)
- [x] Eliminar `src/lfs_insim/utils_temp.py` (**P6**) — S03, sin usos
- [x] Limpiar `config/settings.py` (**P5**) — S03: env + `settings_local.py`; `interval` se queda en 10
- [x] Anclar la ruta de `rutas_grabadas.txt` (**P6**) — S03: `RUTAS_FILE = BASE_DIR / ...`; sigue versionado
- [x] (descubierto) Declarar dependencia `matplotlib` de `ai_control` (**P10**) — S03

**Extra S04:** protocolo actualizado a **LFS 0.8C5** (ISP_SET, ISF_SET, RIFlags/RIF/SAI,
CCI_RETIRED, NLP_MAX_CARS=48, HOSTF nuevos) con 12 tests; spec completa restaurada en
`docs/InSim.txt`; suite **233/233**.

---

## Fase 1 — Red de seguridad del CORE  ✅ COMPLETADA (S06, 2026-07-02)

**Objetivo:** congelar el comportamiento del core antes de refactorizarlo (P11–P14 lo van
a remover todo). Sin LFS: sockets falsos y bytes de oro.

- [x] **Golden-bytes de serialización**: para cada paquete enviable, test que fija los bytes
      exactos que produce `prepare()+pack` (captura el layout binario actual) (**P19**) —
      S05: `tests/test_golden_bytes_send.py` (63 tests, los 27 enviables); descubierto **P21**
      (envío de REO/HCP/IPB-con-bans roto, caracterizado con `pytest.raises`)
- [x] **Golden-bytes de decodificación**: bytes reales (capturados de LFS o construidos según
      spec) → dataclass esperado, para los paquetes info más usados (STA, NCN, NPL, MCI,
      MSO, VER...) (**P19**) — S05: `tests/test_golden_bytes_decode.py` (20 tests: VER/STA/
      NCN/CNL/MSO/NPL/MCI/NLP-con-padding/CON/OBH/HLV/BTC/BTT + enrutado de decode_packet)
- [x] Tests del **dispatch** de `InSimClient`: registro de handlers activos, orden
      master→módulos, aislamiento de errores por handler — S05:
      `tests/test_client_dispatch.py` (14 tests: orden, aislamiento, keep-alive reactivo,
      lifecycle, ruta thread-pool; el registro activo ya estaba en
      `test_active_packet_registry.py`)
- [x] Tests del **loader**: carga con dependencias, coup d'état actual (caracterizar),
      fallos (módulo inexistente, sin clase InSimApp, versión insuficiente) (**P20**) —
      S05: `tests/test_loader.py` (29 tests con InSims sintéticos en tmp_path; caracterizado
      el tragado de dependencias rotas de P20 y el requisito no documentado de `__init__.py`)
- [x] Tests de **packet_io** con socket falso: reensamblado TCP (paquetes fragmentados /
      pegados), byte Size=0, cierre de conexión — S06: `tests/test_packet_io.py` (28 tests:
      framing TCP con socket guionizado, Size=0 con resincronización byte a byte, cierre y
      errores de recv, bucle UDP, stop_all_threads, fallos de conexión, integración loopback)
- [x] Infra: fixture de "LFS falso" (servidor TCP loopback que reproduce trazas) reutilizable —
      S06: clase `FakeLFS` + fixture `fake_lfs` en `tests/conftest.py`, usada por los 6 tests
      de integración TCP de packet_io

**Criterio de aceptación:** el comportamiento actual del core queda descrito por tests que
fallarían ante una regresión; base para refactorizar con confianza.

---

## Fase 2 — Arquitectura del core (composición y API)  ✅ COMPLETADA (S08, 2026-07-03)

**Objetivo:** eliminar los defectos estructurales de raíz. **Rompe la API de los insims**
(aceptado por el usuario en S04).

- [x] **P11**: invertir la herencia — `InSimApp` deja de heredar de `InSimClient`.
      Un cliente, N apps: `client.register(app)`; el loader construye el cliente y registra
      las apps en orden de dependencias. Eliminar coup d'état y aplanado de `modules[]` —
      S06: `InSimApp(PacketSenderMixin)`, `modules[]`→`apps`, cliente perezoso/inyectable
      en el loader, `_resolve_dependencies` muerto eliminado (parte de P17). El orden de
      dispatch pasa a ser el de dependencias (cambio deliberado; antes era el inverso).
      Core reescrito en inglés. Suite 391/391
- [x] **P13**: encapsular la conexión (objeto transporte TCP/UDP inyectado); eliminar los
      singletons de `insim_state`; `send` viaja por el cliente, no por globals — S06:
      `InSimTransport` por instancia; `encode_packet` puro extraído (adelanta parte de P19);
      `insim_state` reducido a "cliente por defecto" (azúcar del mixin); test de dos
      clientes coexistiendo. Suite 388/388
- [x] **P14**: config del paquete con defaults internos (`InSimConfig` o similar); el CLI
      carga config de proyecto/env; el core no importa `config.settings` del CWD —
      S07: `lfs_insim/config.py` (`DEFAULT_CONFIG` + `build_config`, dict plano para
      conservar `self.config.get(...)`); CLI con `_load_project_config()`; el loader
      propaga la config al cliente perezoso y las apps heredan la del cliente.
      Suite 402/402
- [x] **P15**: definir API pública — exports en `lfs_insim/__init__.py`, `__all__` por
      módulo, deprecar `insim_packet_class` (facade), eliminar `import *` internos —
      S07: `__all__` en 11 módulos; facade con DeprecationWarning (re-exporta
      packets+enums); `packets` ya no re-exporta enums; el core no usa la facade.
      Tests en `test_api_publica.py`. Suite 420/420
- [x] **P17/P20 (de paso)**: borrar `_resolve_dependencies` muerto, alinear comentarios,
      fail-fast en el loader — S06/S07: `_resolve_dependencies` (S06); `INST` duplicado
      eliminado, CLAUDE.md alineado (constraints SÍ se aplican), fail-fast con cadena
      de dependencias en el mensaje (S07). `on_tick` configurable → Fase 3
- [x] Migrar `users_management`, `ai_control` y `test_insim` a la nueva API — S06: tras
      P11 los 3 cargan sin cambios; S07: tras P15, `test_insim`/`prueba_botones`
      actualizados (enums explícitos); S08: `ai_control` migrado (10 imports, 9
      archivos; `users_management` ya estaba); smoke sin facade + suite 420/420;
      **validado por el usuario en LFS (S08)** — todo correcto
- [x] Decisión de diseño: idioma de la API pública del core — S06, decidido con el usuario:
      **inglés en el core** (identificadores, docstrings y errores del código nuevo/refactorizado);
      español en docs/dev, tests, insims y comunicación. El código viejo se traduce al tocarlo

**Criterio de aceptación:** cero estado global obligatorio; dos clientes pueden coexistir en
un proceso (test); los 3 insims corren con la nueva API; tests de Fase 1 adaptados y verdes.

---

## Fase 3 — Robustez en runtime  ◀️ ACTIVA

**Objetivo:** comportamiento profesional ante fallos y carga.

- [x] **P12**: reconexión automática con backoff configurable; `on_disconnect`/`on_reconnect`;
      reenvío de ISI y re-solicitud de estado al reconectar — S08: `on_connection_lost`
      en el transporte + detección/reconexión en el bucle principal de `start()`
      (hooks desde el hilo principal; claves `reconnect*` en `DEFAULT_CONFIG`;
      sin zombie al desactivarla o agotar intentos); `users_management.on_reconnect`
      limpia memoria; 11 tests en `test_reconexion.py`; FakeLFS multi-conexión.
      Suite 431/431. **Validado por el usuario en LFS (S08)**: matar/levantar LFS
      con el InSim corriendo → reconecta solo
- [x] **P2 (parte core)**: sacar el dispatch del hilo de IO (cola + worker dedicado);
      documentar el contrato de threading para autores de módulos; revisar/retirar
      `use_thread_pool` (orden no garantizado) — S09: el receptor decodifica, contesta
      el keep-alive en el acto y encola; worker `InSim_Dispatch_Worker` despacha en FIFO;
      `stop()` vacía lo pendiente antes de salir (centinela al final de la cola);
      `use_thread_pool`/`max_workers` retirados; contrato de threading documentado en
      CLAUDE.md y en el docstring de `insim_client.py`; 6 tests nuevos en
      `test_client_dispatch.py`. Suite 435/435
- [x] **P18**: eliminar o implementar bien el envío UDP — S11: **eliminado** el parámetro
      `use_udp` de `transport.send`; el envío es siempre TCP (LFS solo recibe InSim por
      TCP; UDP es solo de bajada). Documentado (docstring + CLAUDE.md) y fijado con test
- [x] **P19**: una sola ruta de serialización (prepare→pack) apoyada en los golden-bytes;
      revisar `.strip()` del decoder (espacios significativos) — S11: `validate_string_lengths`
      es la única autoridad del layout de strings (incluido el truncado de los fijos 'Ns'
      a N-1 con null garantizado); `_extract_values` solo codifica; `.strip()` eliminado
      del decoder (los espacios antes del null se conservan). Goldens actualizados
      (2 cambios deliberados) + 1 golden nuevo del caso borde len == N.
      **Validado por el usuario en LFS (S11)**
- [x] Apagado limpio y determinista (STOP_EVENT compartido/carreras en `stop_all_threads`) —
      S12: `InSimTransport.close()` espera (join) a los receptores y REEMPLAZA el evento de
      stop en vez de limpiarlo (cada bucle captura el evento de SU conexión → imposible el
      `on_connection_lost` espurio tras un cierre deliberado, incluso llamando a close()
      desde el propio receptor); `InSimClient.stop()` con check-and-set atómico de `running`
      (un solo apagado ante stops concurrentes; reentrada desde on_disconnect sin deadlock).
      5 tests nuevos (carrera reproducida en rojo primero). Suite 443/443.
      **Validado por el usuario en LFS (S12)**
- [x] **P24** (extra S12, incidente en vivo): un ISI rechazado por LFS (admin password)
      reseteaba el backoff en cada ciclo → tormenta de ~10 conexiones/s ("InSim - TCP
      excess"). Fix: reconexión **provisional** — sesión que muere antes de
      `reconnect_stable_time` (10 s) retoma la racha (espera previa + escalado + cuenta
      para `max_attempts`). 3 tests (`TestReconexionProvisional`). Suite 446/446.
      **Validado por el usuario en LFS (S12)**
- [ ] Política de errores de handlers configurable (resiliente en prod, fail-fast en dev)

**Criterio de aceptación:** matar/levantar LFS con el InSim corriendo → se reconecta solo;
un handler lento no bloquea la recepción; suite verde.

---

## Fase 4 — Experiencia de desarrollador (DX) y packaging

**Objetivo:** que un tercero pueda instalar, crear y publicar un InSim sin leer el código
fuente. (**P16**)

- [ ] Arreglar metadata: `readme = "README.md"`, `license`, keywords/classifiers; eliminar
      `requirements.txt` redundante; una sola fuente de versión
- [ ] `generate-stubs`/`update-all` → subcomandos del CLI (`lfs-insim stubs`, ...)
- [ ] Adoptar **ruff** (lint + format) y **mypy** gradual (empezando por el core)
- [ ] **CI** (GitHub Actions): pytest + ruff en push/PR a la rama de trabajo y main
- [ ] Docs de usuario: quickstart "tu primer InSim en 5 min", guía de módulos y dependencias,
      referencia de la API pública; revisar plantilla de `lfs-insim init`
- [ ] CHANGELOG.md y convención de versionado (semver)
- [ ] (Opcional, decidir con el usuario) publicación en PyPI

**Criterio de aceptación:** `pip install` desde el repo funciona fuera del proyecto;
CI verde; un desarrollador externo puede seguir el quickstart sin ayuda.

---

## Fase 5 — ai_control: red de seguridad y estabilización (antiguo plan F1–F2)

- [ ] Hacer `ai_control` consciente de la reconexión (visto en S10): parar/pausar
      `_run_test_freeroam` en `on_disconnect` (hoy el hilo muere con `InSimConnectionError`
      al enviar desconectado, o enloquece tras la limpieza de memoria), resetear
      estado propio y ownership de AIs en `on_reconnect`
- [ ] Tests de caracterización de `navigation.py` (planificación de enlaces, nodo más cercano)
- [ ] Tests de caracterización de `traffic.py` (radar / `_scan_lane_ahead`, ACC, overtake)
- [ ] Tests de `physics.py` (volante/pedales/marchas) con telemetría sintética
- [ ] Infra de fixtures: telemetría y grafo de calles sintéticos, sin conexión a LFS
- [ ] Revisar el "PARCHE DE SEGURIDAD MATEMÁTICO" (`traffic.py:655`) y sustituirlo por lógica correcta
- [ ] Auditar el hot-loop `on_ISP_MCI` (coste por tick, frecuencia real) — con el dispatch
      ya fuera del hilo IO (Fase 3)
- [ ] Consolidar radar/geometría en unidad testeable; revisar FSM de adelantamiento

**Criterio de aceptación:** lógica de P2 congelada por tests; sin parches ad-hoc; el usuario
valida en LFS.

---

## Fase 6 — ai_control: refactor estructural y consolidación (antiguo plan F3–F4)

- [ ] Dividir `map_ui.py` (1841), `map_recorder.py` (1604), `traffic.py` (1084) (**P3**)
- [ ] Reducir superficie cross-mixin de `base.py` (**P4**)
- [ ] Limpiar nombres del modelo de estado (`behavior.py`, **P7**)
- [ ] Actualizar README/CLAUDE.md con la arquitectura final; revisión final del diagnóstico

---

## 🔀 Merge a `main`

Todo el refactor vive en la rama **`refactor/estabilizacion`**. `main` permanece intacta
hasta el merge. **Criterio para mergear a `main` ("estable"):**

- Las fases del plan acordadas están completadas.
- `pytest` en **verde** desde `.venv` (+ CI verde cuando exista, Fase 4).
- El usuario ha **validado el comportamiento en LFS** (no hay regresiones funcionales).

El merge lo decide y autoriza el usuario. Tras el merge, se continúa desde `main`.

## Ideas / pendientes sin fase asignada

- **P9**: decidir qué hacer con `tools/setup_lfs.py` (roto: importa `DESIRED_LFS_CONFIG`,
  que no existe en `settings.py`) — recuperarlo o eliminarlo.
- Migrar `rutas_grabadas.txt` a JSON cuando se toque `RouteManager` (ver P6).
- **P8**: confirmar contra `docs/InSim.txt` el caso de string variable vacío sin padding.
- `interval` a 100 ms como cambio deliberado, si se quiere, al auditar el hot-loop (Fase 5).
