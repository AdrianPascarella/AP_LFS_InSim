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

## Fase 3 — Robustez en runtime  ✅ COMPLETADA (S13, 2026-07-03)

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
- [x] Política de errores de handlers configurable (resiliente en prod, fail-fast en dev) —
      S13: clave `handler_errors` en `DEFAULT_CONFIG` ('log' default = comportamiento de
      siempre; 'raise' = fail-fast: el primer error de un handler o hook detiene el cliente
      y se re-lanza desde `start()` con su traceback — el worker aparca la excepción y el
      bucle principal la re-lanza). Excepción deliberada: los `on_disconnect` de `stop()`
      se aíslan SIEMPRE (el apagado debe completarse). Valor inválido →
      `InSimConfigurationError` al crear el cliente. De propina: los errores de lifecycle
      en modo 'log' ahora se loguean con traceback (`exc_info=True`). 8 tests nuevos
      (rojo primero). Suite 458/458
- [x] Decisión heredada de S07: ¿`on_tick` configurable? — S13: SÍ, clave `tick_interval`
      (segundos, default 0.1 = comportamiento histórico; mínimo 0.01, validado al crear el
      cliente con `InSimConfigurationError`). El tick de las apps queda DESACOPLADO del
      sondeo interno del bucle principal (fijo a ≤100 ms): un tick lento nunca retrasa la
      detección de caídas (P12) ni el fail-fast de `handler_errors`. Sin catch-up tras un
      stall (una reconexión no dispara una ráfaga de ticks debidos); documentado que no es
      un timer de precisión y que el trabajo de alta frecuencia va en handlers MCI/OutSim.
      5 tests nuevos (rojo primero). Suite 463/463

**Criterio de aceptación:** matar/levantar LFS con el InSim corriendo → se reconecta solo;
un handler lento no bloquea la recepción; suite verde. **Cumplido y validado en LFS**
(P12/P2 en S08–S10; apagado limpio y P24 en S12; los ítems de S13 no cambian defaults).

---

## Fase 4 — Experiencia de desarrollador (DX) y packaging  ✅ COMPLETADA (S17)

**Objetivo:** que un tercero pueda instalar, crear y publicar un InSim sin leer el código
fuente. (**P16**)

- [x] Arreglar metadata: `readme = "README.md"`, `license`, keywords/classifiers; eliminar
      `requirements.txt` redundante; una sola fuente de versión — S14: `readme` apuntaba a
      un `README` inexistente; licencia SPDX (`license = "MIT"` + `license-files`,
      build-system sube a setuptools>=77); versión única en `lfs_insim.__version__`
      (pyproject `dynamic`, contrato fijado con test contra la metadata instalada);
      keywords y classifiers (Python 3.9–3.14); URLs corregidas (apuntaban al repo
      antiguo `Aprendiendo-InSim-LFS`); descripción en inglés; `requirements.txt`
      eliminado. 2 tests nuevos (rojo primero); wheel construye limpio en aislamiento.
      Suite 465/465
- [x] `generate-stubs`/`update-all` → subcomandos del CLI (`lfs-insim stubs`,
      `lfs-insim update-all`) — S15: dos handlers en `cli.py` que llaman a
      `generate_stubs.main()` / `update_all.main()` (mismo comportamiento que
      los console-scripts: llamar a `main()` y devolver 0); los dos scripts
      globales fuera de `[project.scripts]` — `lfs-insim` es el único
      console-script. Git hook revisado: `.githooks/pre-commit` es un no-op
      deshabilitado por el usuario (no invocaba `generate-stubs`, nada que
      migrar); docs corregidas (CLAUDE/README apuntan a `lfs-insim stubs` y
      ya no afirman que el hook autogenera). 4 tests nuevos (`test_cli.py`,
      rojo primero) + reinstalación editable que elimina los `.exe` viejos.
      Suite 469/469
- [x] Adoptar **ruff** (lint + format) y **mypy** gradual (empezando por el core) — S16:
      ruff con line-length **88** y reglas conservadoras **E/F/I/W** (decidido con el
      usuario); `ruff format` en commit propio (79 archivos, cero comportamiento) +
      `.git-blame-ignore-revs`; lint con autofix seguro (137) + 5 fixes a mano e ignores
      acotados (E501 lo posee el formatter; per-file para star-imports intencionales,
      imports no-top y enums de una letra del protocolo). **mypy** gradual sobre el core:
      vigila los ~14 módulos limpios, backlog por módulo con `ignore_errors`
      (packets/loader/decoders/utils); `follow_imports=silent`, exclude de los `.pyi`,
      target 3.10. 2 errores type-only del core que los stubs enmascaraban, corregidos
      (`ISF(0)`; narrowing de `f.name`). ruff limpio, mypy limpio, suite 469/469
- [x] **CI** (GitHub Actions): pytest + ruff en push/PR a la rama de trabajo y main — S16:
      `.github/workflows/ci.yml` con jobs **lint** (ruff check + format --check, ruff
      pineado a `0.15.*`), **test** (pytest en matriz Python 3.9/3.11/3.13 en ubuntu +
      Windows 3.13) y **typecheck** (mypy, `continue-on-error` = no bloquea). Dispara en
      push/PR a `main` y `refactor/estabilizacion`; `MPLBACKEND=Agg`. **Nota:** la 1ª
      ejecución real se dispara con el push de cierre de S16 (primera validación en Linux)
- [x] Docs de usuario: quickstart "tu primer InSim en 5 min", guía de módulos y dependencias,
      referencia de la API pública; revisar plantilla de `lfs-insim init` — S17: nueva carpeta
      `docs/guia/` con 4 guías (quickstart, modulos-y-deps, api-publica, arquitectura), en
      español y verificadas contra el código; README reducido a landing page + enlaces. La
      plantilla de `lfs-insim init` revisada: al día (usa la API pública, CMDManager fluido).
      Corregidas afirmaciones FALSAS del README viejo (sección Arquitectura describía el
      "coup d'état"/Master/`modules[]`/`insim_packet_io.py` — todo eliminado en Fase 2; los
      stubs NO se generan por git hook; `insim_name` default es `LFS-InSim`, no `InSimApp`;
      faltaba `InSimProtocolError`). Corregido de paso CLAUDE.md: el loader instancia la
      PRIMERA subclase de `InSimApp` del entry_point, no casa por nombre CamelCase (por eso
      `AIControl` funciona). Sin cambios de runtime; suite intacta
- [x] CHANGELOG.md y convención de versionado (semver) — S17: `CHANGELOG.md` en
      formato Keep a Changelog (español, coherente con README/`docs/guia/`) +
      sección de convención semver. Historial verificado: la versión ha sido
      `0.2.0` desde el "Starting point" (nunca hubo 0.1.0, sin tags ni releases),
      así que el changelog documenta la 0.2.0 como **primera versión en
      preparación** (sección `[Sin publicar]`, sin fecha hasta el release),
      recogiendo todo el refactor por categorías (Añadido/Cambiado/Obsoleto/
      Eliminado/Corregido) con los cambios que rompen la API marcados. URL de
      Changelog añadida a `[project.urls]` de pyproject (apunta a `blob/main`, ok
      tras el merge) y enlace en el README. Tests de packaging verdes (23/23)
- [x] Publicación en PyPI — **PREPARADA (S17), publish real diferido a post-merge**
      (decidido con el usuario: preparar sí, disparar no hasta el merge a `main`).
      Hecho: build local validado (`python -m build` → sdist+wheel `py3-none-any`,
      `twine check` PASSED); extra `[publish]` (build+twine); workflow
      `.github/workflows/publish.yml` con Trusted Publishing (OIDC, sin tokens) e
      **inerte** (solo `workflow_dispatch`→TestPyPI y `release: published`→PyPI, y
      solo operable desde `main`); runbook `docs/dev/PUBLICACION.md` (ensayo local
      en TestPyPI, config de trusted publishers, publish real). El upload real
      (incluido el ensayo en TestPyPI) lo lanza el usuario con sus credenciales.

**Criterio de aceptación:** `pip install` desde el repo funciona fuera del proyecto;
CI verde; un desarrollador externo puede seguir el quickstart sin ayuda.
**CUMPLIDO:** wheel construye limpio y `twine check` pasa (S14/S17), CI verde
(S16), quickstart + guías (S17), PyPI preparado (S17). El publish real a PyPI se
dispara en/tras el merge a `main`.

---

## Fase 5 — ai_control: red de seguridad y estabilización (antiguo plan F1–F2)  ◀️ ACTIVA (S17)

> **Arranque acordado con el usuario (S17):** empezar por la RED DE SEGURIDAD
> (modus operandi §3 — `ai_control` no tiene tests y se toca lógica frágil):
> primero infra de fixtures (telemetría + grafo sintéticos, sin LFS), luego tests
> de caracterización de navigation/traffic/physics, y solo entonces el fix de
> reconexión (primer ítem de abajo). Ver ESTADO_ACTUAL § Próximo paso.

- [x] Hacer `ai_control` consciente de la reconexión (visto en S10): parar/pausar
      los bucles daemon en `on_disconnect` (morían con `InSimConnectionError` al enviar
      desconectados, o enloquecían tras la limpieza de memoria), resetear estado propio y
      ownership de AIs en `on_reconnect` — S20. Se descubrió que eran DOS bucles con el
      defecto (`_run_test_freeroam` + `_test`), no uno. Señal de parada compartida
      (`threading.Event`) + infra `_init_traffic_state` / `_start_traffic_loop` /
      `_stop_traffic_loops` en `_CommandsMixin`; overrides `AIControl.on_disconnect` /
      `on_reconnect` (este resetea target + cachés y NO reanuda el tráfico, para no arrastrar
      el UCID viejo); "Detener" de la UI ahora para de verdad. 6 tests en `test_reconexion.py`
      (rojo→verde). Suite 607/607. **Validado por el usuario en LFS (S20): "todo funciona
      perfectamente".**
- [x] Tests de caracterización de `navigation.py` (planificación de enlaces, nodo más cercano) —
      S18: `tests/insims/ai_control/test_navigation.py`, 31 tests (geometría pura:
      `_get_closest_node_index` / `_get_indicator_to_use` / `_is_link_reachable_ahead`;
      planificación: `_get_raw_candidates` / `_calculate_next_link` / `_plan_next_link`).
      Los grandes métodos de integración con tiempo/estado (`_update_freeroam_navigation`,
      `_get_radar_speed_limit`, `_update_route_navigation`) quedan sin cubrir a propósito
- [x] Tests de caracterización de `traffic.py` (radar / `_scan_lane_ahead`, ACC, overtake) —
      S19: `tests/insims/ai_control/test_traffic.py`, 81 tests (ACC de 3 zonas + parche,
      matemática de adelantamiento, geometría de zonas, `_find_valid_overtake_lane`, FSM
      `_trigger_return`/`_finish_overtake`, radar `_scan_lane_ahead`/`_scan_target_lane`/
      `_scan_return_lane_gap` con vehículos IA, guardián `_is_lane_safe_to_overtake`). El
      orquestador `_update_traffic_behavior` queda sin cubrir a propósito (tiempo + estado).
      Con esto la red de caracterización de Fase 5 está COMPLETA (física + nav + tráfico)
- [x] Tests de `physics.py` (volante/pedales/marchas) con telemetría sintética — hecho
      (otro equipo, sin documentar; llegó en el commit `9605dc6`):
      `tests/insims/ai_control/test_physics.py`, 20 tests (steering / pedals / gears /
      handle_steering)
- [x] Infra de fixtures: telemetría y grafo de calles sintéticos, sin conexión a LFS —
      telemetría + harness de la app (`tests/insims/ai_control/conftest.py`, otro equipo)
      + **grafo sintético** (`make_road` / `make_road_link` / `make_lateral_link` /
      `populate_graph`, puebla un MapRecorder real keyeado como producción; S18)
- [x] Revisar el "PARCHE DE SEGURIDAD MATEMÁTICO" (en `_apply_adaptive_cruise_control`) y
      sustituirlo por lógica correcta — S21: **Opción A** (confirmada con el usuario). Parche
      eliminado (ya no reescribe los `min`/`max` del llamador); suelo duro de parada explícito;
      `critical = max(5, min·0.5)` (se mantuvo el suelo por continuidad de la rampa —matiz sobre
      la letra de A, ver P25/HISTORIAL S21); ratios acotados a [0,1] y denominadores con ε →
      imposible el ZeroDivisionError; números mágicos → constantes con nombre. 2 tests del parche
      reescritos + 2 de robustez (rojo→verde). Suite 609/609; ruff limpio. **Pendiente validación
      en LFS.**
- [x] (extra S21, no planeado) Mejorar `map_renderer.py`: el render no escalaba y limitaba la
      edición de mapas grandes. Encuadre ajustado a los datos (`adjustable="box"`), grosores de
      línea proporcionales a la extensión (links más finos que los roads), roadlinks como línea
      cian fina continua (antes cruces X gruesas), leyenda multi-columna ordenada alfabéticamente
      con **cada columna de la altura del mapa** (filas por columna medidas sobre un render de
      sondeo + llenado columna-a-columna forzado) y paleta de roads sin colisión con los colores
      semánticos (rojo/gris/cian). Renders de south_city/south_drift_1 regenerados y validados
      visualmente. Tooling offline, sin LFS. Commits `5dd0740`, `9a9f4eb`.
- [x] (extra S30, no planeado) UI de `ai_control` (`map_ui.py`): el **whereami** de la pestaña Info
      (WA Road/RLink/LLink/Zone/Regla) pasa de panel dentro del menú a **overlay fijo anclado a la
      mitad-derecha** que persiste al cambiar de pestaña y con el menú cerrado; solo se quita
      deseleccionándolo. CIDs propios 166-171 (fuera del rango de contenido 108-165); estado
      `_ui_whereami_ucid` independiente del menú; `_map_ui_close`/`on_reconnect` lo redibujan;
      `on_tick` lo refresca al margen del menú. Red: `test_map_ui_whereami.py` (7 tests). Suite
      704/704; ruff limpio. ✅ validado en LFS por el usuario. Commit de cierre de S30.
- [x] (extra S31, no planeado) Herramienta **"Apunta"** en la pestaña Info (`map_ui.py`): overlay fijo
      (6º tipo del whereami, `ahead`) que indica la **vía más cercana a la que apunta el morro del coche**
      (distinta de la actual) y a qué distancia — útil para mapear. Geometría pura `find_road_pointed_at`
      (ray-cast 2D en `nav_modes/freeroam/geometry.py`; red de 9 tests) + rumbo del morro desde el heading
      LFS (misma fórmula que el orquestador); excluye la vía actual (la más cercana a la posición). Toggle
      CID 118, fila del overlay 172. Red: +2 tests de integración en `test_map_ui_whereami.py`. Suite 710;
      ruff limpio. ✅ **validado en LFS por el usuario** ("funciona perfectamente"). Commit de cierre de S31.
- [x] (extra S32, no planeado) Herramienta **"Link auto"** en la pestaña Grabar (`map_ui.py`): botón bajo
      "RoadLink" (CID 118) que graba un RoadLink **sin teclear origen ni destino**. El ORIGEN se captura de
      la vía más cercana al coche que se graba (`recording_plid`) al iniciar y el DESTINO al pulsar
      Finalizar (ambos vía `get_location_context`). Al finalizar, si `origen->destino` ya existe →
      pantalla de **conflicto** (añadir sufijo a origen/destino y recomprobar / sobrescribir / cancelar);
      si no → pantalla de **confirmación** con el nombre final (Aprobar / cancelar). El estado del flujo
      vive en `current_recording["auto_phase"]` (recording→confirm/conflict) para sobrevivir a
      cerrar/reabrir el menú. Reutiliza el commit del recorder (`_cmd_rec_end`). Red:
      `test_map_ui_auto_link.py` (13 tests: inicio/guard, confirm, conflicto+3 opciones, persistencia).
      Suite 723/723; ruff limpio. ✅ **validado en LFS por el usuario** ("funciona perfectamente"). Commit de cierre de S32.
- [x] Auditar el hot-loop `on_ISP_MCI` (coste por tick, frecuencia real) — con el dispatch
      ya fuera del hilo IO (Fase 3) — S22: informe en `docs/dev/AUDITORIA_HOTLOOP.md` con
      mediciones reales. **Veredicto: el loop está SANO** (radar auto-regulado a ~7–10 Hz/IA
      con jitter + caché compartida de humanos → peor tick ≈0.6 ms ≪ 10 ms hasta ~16–20 IAs).
      Hallazgos de robustez/escalado (no urgencias): `get_location_context` es O(mapa) ~1 ms en
      mapa grande (índice espacial pendiente); radar O(N²); `Coordinates.x_m/y_m/z_m` recalcula
      la conversión en cada acceso (~28% del radar, candidato a Fase 6). De paso, red nueva
      `test_map_recorder.py` (8 tests, caracteriza `get_location_context`) + limpieza menor:
      `get_location_context` ya no reconstruye el dict fusionado de enlaces (`itertools.chain`;
      perf despreciable, pero elimina una allocation). Suite 617/617.
- [x] (6a) Índice espacial de GEOMETRÍA para `get_location_context` — S23: ataca el hallazgo 1
      de la auditoría (barrido O(nodos) → ~9,2 ms/consulta en south_city ampliado, 128 roads /
      11.086 nodos). Nuevo `nav_modes/freeroam/spatial_grid.py` (`SpatialHashGrid`, hash grid 2D
      genérico) + `_get_closest_road` en `map_recorder.py`. **Fidelidad por construcción**: el
      grid solo acota candidatos y delega en el `get_closest_geometry` existente en orden de dict
      → distancia 3D y desempate `<` idénticos al barrido lineal. Invalidación en los 5 sitios de
      mutación de `self.roads`; celda 20 m (~13×, medido). `test_spatial_grid.py` (12) +
      `test_road_spatial_index.py` (fuzz de equivalencia + bordes). Suite 642/642; ruff limpio.
      Solo tests offline → no requiere LFS.
- [→] (6b) Partición espacial de VEHÍCULOS para el radar O(N²) + FSM de adelantamiento —
      **REUBICADO a Fase 6 · W3 (S23):** se pliega en el refactor de `traffic.py` (la auditoría lo
      dio no urgente y traffic.py se toca igual → evita trabajo doble). Caracterizar el radar como
      unidad primero; reutiliza el `SpatialHashGrid` de 6a (grid dinámico aparte). Ver Fase 6.

**Criterio de aceptación:** lógica de P2 congelada por tests; sin parches ad-hoc; el usuario
valida en LFS. **Estado:** cumplido salvo la validación en LFS del ceda-el-paso del ACC (S21) =
**W4** (bloqueada: el mapa aún tiene `zones: 0`, ninguna intersección creada). Es el gate del merge.

---

## Fase 6 — Pre-publish: refactor de ai_control + endurecimiento de API + DX del init  ◀️ ACTIVA (re-secuenciada S23)

> **Re-secuenciación (S23, 2026-07-08, decidida con el usuario):** el refactor estructural de
> ai_control (antes post-merge) se ADELANTA a **antes de publicar**, junto a una limpieza de la
> **API pública del framework** (`utils.py`) y un scaffold `init` más robusto. Motivo clave: mover
> funciones de `lfs_insim.utils` es un **cambio de API pública**; una vez en PyPI rompería a
> usuarios reales → la única ventana limpia es ANTES del primer publish. La antigua opción 6b
> (índice espacial de vehículos para el radar) se **pliega** en el refactor de `traffic.py` (W3) en
> vez de hacerse suelta (auditoría: no urgente; traffic.py se toca igual → evita trabajo doble).
> **Separar SIEMPRE** lo que toca API pública (W1/W5, pre-publish OBLIGATORIO) de lo interno/
> cosmético (W3, flexible) para no dejar que el scope creep retrase el release.
>
> **Orden propuesto:** W4 (usuario, en paralelo — gate del merge) → **W1 + W5** (API) → **W2**
> (init) → **W3** (refactor interno + radar). **Todo en la rama** `refactor/estabilizacion`; un
> solo merge a `main` cuando esté publish-ready + validado, y luego publish (ver § Merge).

### W1 · Split de `utils.py` — sacar la geometría/navegación de ai_control del `utils` público
**(pre-publish OBLIGATORIO: cambia la API publicada)**
- [x] Mover a ai_control (tiene `nav_modes/freeroam/geometry.py`) el bloque específico:
      `calc_target_heading`, `get_heading_diff`, `calc_deviation_angle`,
      `calc_dist_point_to_segment_3d`, `get_closest_node_index`, `determine_smart_spawn_index`,
      `apply_antilag_window`, `evaluate_dynamic_capture`, `is_target_ahead_and_in_lane`.
      **Se quedan** (framework genérico): `separate_message`/`separate_command_args`,
      `strip_lfs_colors`, `TextColors`, `Command`/`CMDManager`, conversiones `lfs_*`, y —decidido
      S23— **`calc_dist_3d`** (geometría 3D genérica) y **`PIDController`** (primitiva reutilizable).
      Es **extracción segura**: verificar cobertura de tests de lo que migra ANTES de moverlo,
      actualizar imports (ai_control + `test_utils.py`), `__all__` y las guías. — **S24:** hecho.
      Red primero (`tests/insims/ai_control/test_geometry.py`, 44 tests: 15 movidos de `test_utils` +
      29 de caracterización nueva) verificada VERDE contra el origen antes de mover, luego import
      girado al destino → extracción sin cambio de lógica. Imports actualizados en `physics.py`,
      `navigation.py`, `map_recorder.py`, `route/manager.py` + `test_geometry.py`; `__all__` de
      `utils.py` recortado a `calc_dist_3d`. Suite 671; ruff limpio; `lfs-insim list` OK. Quirk
      caracterizado: `is_target_ahead_and_in_lane` fuera de carril devuelve lateral=0.0; además es
      **código muerto** (sin uso) → candidata a eliminar en W3.

### W5 · Repaso final de API pública + CHANGELOG  **(pre-publish; va con W1)**
- [x] Última pasada por exports de `lfs_insim`, claves de `DEFAULT_CONFIG` y jerarquía de
      excepciones (última oportunidad de cambiarlos gratis, sin usuarios). Cuadrar las 4 guías de
      `docs/guia/` tras W1/W2 y anotar los breaking changes en `CHANGELOG.md`.
      — **S24 (parte ligada a W1):** `docs/guia/api-publica.md` refleja que la geometría de IA salió
      del framework; entrada `[Rompe la API]` en `CHANGELOG.md`. — **S25 (sweep, HECHO):** exports de
      `lfs_insim` y `DEFAULT_CONFIG` (20 claves) confirmados sin cambios; jerarquía de excepciones
      recortada — **quitada `InSimProtocolError`** (el framework no puede detectarla, P24; solapa con
      `InSimPacketError`; nunca se lanzaba), **mantenida `InSimCommandError`** (tipo de error del
      sistema de comandos, para módulos). `exceptions.py` traducido a inglés (MODUS_OPERANDI §5).
      Suite 670; ruff limpio. Bullet en `CHANGELOG.md` (Eliminado).

### W2 · `lfs-insim init` más robusto, con flag `--minimal`/`--full`  **(pre-publish recomendado, DX)**
- [x] `--minimal` = el template escueto de hoy (un comando "hola"). `--full` (default a decidir)
      trae por defecto lo necesario: **comando de cierre** guardado por admin/UCID, patrón de
      validación de permisos, `on_reconnect` (P12) y petición de estado inicial (`TINY.NCN/NPL`).
      Diseñado para **admitir más perfiles en el futuro** (no solo min/full). Confirmar el
      mecanismo del close al implementar (`TINY.CLOSE` a LFS vs `client.stop()`).
      — **S26 (hecho):** dos decisiones confirmadas con el usuario → **cierre = `self.client.stop()`**
      (parada limpia nativa; `TINY.CLOSE` con la reconexión P12 activa solo reconectaría) y
      **`--full` por defecto**. Implementado en `cli.py`: flags mutuamente excluyentes
      `--full`/`--minimal` + registro extensible `_INIT_PROFILES` (dict perfil→render) para
      admitir más perfiles sin tocar `cmd_init`. Templates como strings con centinelas
      (`__CLASSNAME__`/`__MODNAME__`) + `str.replace` (no f-strings, evita el infierno de `{{}}`).
      `--minimal` = byte-idéntico al template anterior. `--full` trae: `set_isi_packet` con
      `ISF.LOCAL`, `TINY.NCN/NPL` en `on_connect`, tracking de admin por NCN
      (`packet.Admin == AD_NOAD.ADMIN`) + `_is_admin(ucid)` (UCID 0 = host local siempre admin),
      comando `cerrar` admin-guarded que llama `self.client.stop()`, y `on_reconnect` que resetea
      `self.admins`. Red primero (`test_cli.py`, +10 tests: perfiles, mutua exclusión, CamelCase/
      manifiesto, y **ambos templates compilan y `exec` → subclase de `InSimApp`**). Suite **680**;
      ruff limpio. Guías cuadradas (quickstart usa `--minimal` explícito + nota del `--full`;
      README/CLAUDE.md/CHANGELOG). 3.9-safe (`dict[int, bool]` es PEP 585; sin uniones PEP 604).

### W3 · Refactor estructural de ai_control (interno, flexible) + radar + FSM  (antiguo Fase 6)

> **Recorte de alcance (S27, decidido con el usuario):** al medir en S27, los ficheros gordos
> habían crecido ~70% sobre lo que asumió S23 (`map_ui` 1841→**3161**, `map_recorder`
> 1604→**2520**, `traffic` 1084→**1348**). Se **aplazan a post-merge** los splits de `map_ui.py`
> y `map_recorder.py`: son **tooling offline** de edición de mapas (no son el framework
> publicado, no tocan el runtime de conducción ni la API pública, y no tienen red de
> caracterización), así que partirlos no aporta nada al primer release y retrasa el merge —que
> además ya está esperando a W4. Pre-publish se queda `traffic.py` (hospeda el radar y tiene la
> red de los 81 tests de S19), P4 y P7.

- [x] **P3 (parte pre-publish): partir `traffic.py`** (1348) — **S27**: paquete `traffic/` con un
      módulo por responsabilidad: `radar.py` (393), `orchestrator.py` (468), `overtake.py` (239),
      `zones.py` (80), `cruise_control.py` (80), `paths.py` (51). `_TrafficMixin` pasa a ser una
      **fachada** que compone los submixins → `app.py` y los tests no cambian. **Extracción
      segura**: los cuerpos se movieron por rango de líneas y se verificó con un snapshot
      antes/después que los 18 métodos conservan **cuerpo y firma byte-idénticos**, que
      `AIControl` los resuelve a la misma función y que su superficie sigue teniendo los mismos
      182 atributos. Suite 680; ruff limpio.
- [ ] ~~Dividir `map_ui.py` / `map_recorder.py`~~ → **aplazado a post-merge** (ver recorte arriba)
- [x] Reducir superficie cross-mixin de `base.py` (**P4**) — **S31**: auditado el grafo de
      llamadas real, el contrato `_MixinBase` se recorta de 32 firmas a las **20** genuinamente
      cross-mixin (fuera las **12 self-local**, que solo se llaman dentro de su propio mixin),
      cada una anotada con quién la llama; imports `Coordinates`/`PIDController` huérfanos fuera.
      Es **honestidad del contrato** (hints `TYPE_CHECKING`, cero runtime). El **desacople
      profundo** (reducir esas 20 llamadas / romper el "God object") queda **pendiente**: es
      arquitectónico y el orquestador `_update_traffic_behavior` no tiene red (ver DIAGNOSTICO § P4).
- [x] Limpiar nombres del modelo de estado (`behavior.py`, **P7**) — **S27**: el par "intención vs
      valor en uso" pasa al patrón **petición → resuelto**: `speed_request`/`speed_resolved_kmh` y
      `point_request`/`point_resolved` (93 sustituciones en 9 ficheros, por palabra completa).
      Cazada una **colisión**: `_estimate_overtake_distance` tenía un *parámetro* homónimo
      `target_speed_kmh` que no es el campo (es la velocidad del coche adelantado) →
      `target_vehicle_speed_kmh`. Limpiados los comentarios residuales de `behavior.py`; el resto
      de marcadores `[!]`, zona a zona. Suite 680.
- [x] Índice espacial de VEHÍCULOS para el radar O(N²) (ex-6b), en `traffic/radar.py` — **S28**:
      rejilla dinámica (`SpatialHashGrid`, aparte de la estática de geometría) construida 1×/MCI en
      `on_ISP_MCI`; los 3 barridos consultan el vecindario (`_iter_radar_candidates`) en vez de los N
      vehículos. **Extracción segura**: cambia solo la línea del `for`, culls/filtros intactos → la
      rejilla es un SUPERCONJUNTO del culling → salida **bit-idéntica**. Nuevo `SpatialHashGrid.
      ids_within` (consulta de región). **Red de equivalencia** (fuzz grid vs. barrido lineal, 40
      semillas × 3 barridos, IAs+humanos, bit-idéntico) + 7 unitarios del grid. Benchmark
      **O(N²)→~O(N)** (2,5×@24, 5,2×@64; celda 50 m). Suite 691; ruff limpio.
- [x] Revisar el FSM de adelantamiento (`overtake_state`, en `traffic/overtake.py`) y **eliminar
      `is_target_ahead_and_in_lane`** de `nav_modes/freeroam/geometry.py` (código muerto, S24; con su
      test de `test_geometry.py`). Limpiar los marcadores `[!] OPTIMIZACIÓN` que queden en `radar.py`.
      — **S31:** FSM revisado (IDLE→EVALUATING→OVERTAKING→RETURNING con cooldowns; estructura sólida).
      Borrada la función muerta + sus 5 tests (704→699). Los 4 marcadores `[!] OPTIMIZACIÓN` de
      `radar.py` → comentarios normales. De paso, quitado el parámetro `name` muerto de `_finish_overtake`
      (y el alias `_n = ai.ai_name` que solo lo alimentaba, resto de una eliminación de logs previa).
      Solo estructura/comentarios; suite verde, ruff limpio.
- [x] Actualizar README/CLAUDE.md con la arquitectura final (paquete `traffic/`, rejilla del radar);
      revisión final del diagnóstico — **S31:** CLAUDE.md actualizado (composición real con `_MapUIMixin`,
      fachada `_TrafficMixin` sobre el paquete `traffic/`, contrato `_MixinBase`, FSM de adelantamiento y
      rejilla del radar); diagnóstico P4 revisado. El README ya delega la arquitectura a `docs/guia/`
      (su fila de `ai_control` es correcta a alto nivel) → sin cambios.

**Criterio de aceptación:** API pública limpia y estable (W1/W5); `init --full/--minimal`
funcionando (W2); `traffic/` partido, `base.py` adelgazado, nombres de estado claros y radar con
red (W3 — `map_ui`/`map_recorder` quedan para post-merge, ver recorte S27); suite verde + CI
verde; el usuario valida en LFS. **Red primero** en todo lo que toque lógica frágil (los grandes
orquestadores con `time.time()` siguen sin red → cubrir antes de tocarlos).

---

## 🧩 Tooling de trabajo — Skills de Claude Code  ⭐ PRIORITARIO (S32)

> **Iniciado en S32:** se creó la primera skill de proyecto, **`ai-control-map-ui`**
> (`.claude/skills/ai-control-map-ui/SKILL.md`), un playbook para tocar la UI de mapeo de
> `map_ui.py` sin re-explorar 3000+ líneas — ahorra tokens de *orientación* y da consistencia
> (rangos de CID, patrón dibujar↔click, harness de tests). Para que se **sincronice entre
> dispositivos** se des-ignoró `.claude/skills/` en `.gitignore` (el resto de `.claude` sigue
> local). Motivación (con el usuario): los ajustes de UI de ai_control son un pedido recurrente
> y de coste de orientación alto → candidato ideal a skill on-demand.

- [ ] **Evaluar el catálogo de skills del proyecto (qué merece skill y qué no).** Candidatas
      detectadas: (a) protocolo de **cierre de sesión** (`cerrar-sesion`: actualizar docs + commit
      + push con el workaround de `gh`) — cómodo, ahorro marginal; (b) protocolo de **arranque**
      (`arrancar-sesion`: proteger mapas §1.2 + `pull` + leer `docs/dev/`); (c) otras zonas de
      re-exploración cara (¿`traffic/`? ¿navegación freeroam?). **Criterio:** una skill vale para
      conocimiento **procedimental y solo-a-veces-relevante** (mejor que CLAUDE.md, que se carga
      SIEMPRE); mantenerla en **estructura/convenciones, NO números de línea** (envejecen). Coste:
      mantenimiento si el código se mueve.
- [ ] **Definir cómo gestionarlas (convención).** Propuesta de partida (a ratificar/afinar al
      evaluar a/b/c): skills de proyecto en `.claude/skills/<nombre>/SKILL.md` versionadas por git
      (ya des-ignoradas); una skill por flujo repetible; `description` afinada para que se dispare
      sola cuando toca; revisarlas si el código al que apuntan cambia mucho.

---

## Fase 7 — Robustez de conducción freeroam (ai_control)  ◀️ PRÓXIMO (S31)

> **▶️ PRÓXIMO TRABAJO (S31, decidido con el usuario):** los **3 fixes pendientes de abajo son el
> siguiente trabajo a abordar**. Se implementan **con red primero** (offline, extrayendo un predicado
> puro testeable por fix, como en el fix 2). Una vez implementados, **el usuario los debe confirmar
> OBLIGATORIAMENTE en LFS** (son conducta): sin esa validación no se dan por buenos. Encajan con la
> sesión de LFS de **W4** (mismo gate del merge). Orden sugerido por impacto: (4) `is_closed`, (1) flip
> de enlace, (3) radar en transición.
>
> **Origen (S29, 2026-07-11):** el usuario, conduciendo en LFS, reportó 4 bugs de comportamiento
> del modo Freeroam. Uno (fin de vía → espectadores) se pidió y **se resolvió en el acto**; los
> otros tres se aparcan aquí para abordarlos cuando sea más oportuno (delegado a Claude). Son bugs
> de **conducción** del insim de ejemplo (el escaparate), NO tocan la API pública del framework →
> no bloquean la estabilidad de la API (Fase 6). Como todos necesitan **validación en LFS**, encajan
> con las sesiones de LFS de **W4** (mismo gate). **Red primero** (MODUS §3): son los grandes
> orquestadores con `time.time()`, que siguen sin red — extraer un predicado puro testeable por fix
> y probarlo antes de tocar el orquestador (patrón usado en el fix de fin de vía).

- [x] **(2) Fin de vía sin salida → espectadores** — **S29 (HECHO).** Una IA que llegaba a un fin
      de vía sin `next_link` se quedaba clavada a 0 km/h: el anti-stuck de `_update_freeroam_navigation`
      trata `speed_request<5` como parada *intencionada* y nunca la castiga, y el spec inline del
      `fin_de_geometria` solo saltaba en el tick exacto de captura del último nodo (frágil).
      **Watchdog nuevo** en `navigation.py`: predicado puro `_is_dead_end_stop(mode, speed_kmh)`
      (parada real < `DEAD_END_SPEED_KMH` 2 km/h, sin `next_link`, no circular, sin adelantamiento en
      curso — distingue el callejón del semáforo/tráfico legítimo, que SÍ conserva su `next_link`) +
      temporizador `mode._dead_end_since`; si sigue así `DEAD_END_TIMEOUT_S` (4 s) → `_cmd_spec`. Se
      centralizó el spec en el watchdog (quitado el inline duplicado que enviaba un MSL de error al
      re-spec). Red primero: `TestIsDeadEndStop` (6 tests) en `test_navigation.py`. Suite 697; ruff
      limpio. **✅ VALIDADO en LFS por el usuario (S30): "funciona correctamente".**
- [ ] **(1) Flip de enlace en salidas muy juntas (intermitente se sobreescribe).** Reportado: yendo
      por `SOUTH_CITY_STATION_s2` con intención de tomar `HAVEN_LINE_S22_b` (lo marca el intermitente),
      en el último momento cambia a `HAVEN_LINE_S22_a` (se ve el intermitente cambiar). **Asimétrico:**
      solo pasa hacia un lado; el sentido contrario casi nunca falla. Sospecha: `_calculate_next_link`
      (`navigation.py`) elige con `random.choice` y el `next_link_id` **se re-planifica** en varios
      triggers (localización, transición RoadLink/LatLink, recálculo de `fin_de_geometria`); al avanzar,
      el filtro `_is_link_reachable_ahead` deja de ver un enlace y ve el otro → el re-plan **cambia la
      elección ya comprometida** (y el intermitente con ella). Arreglo probable: hacer la elección
      **pegajosa** (no re-planificar el `next_link` mientras siga siendo alcanzable / una vez encendido
      el intermitente comprometerse a ese enlace). Investigar la asimetría RHT/LHT en `_get_indicator_to_use`
      y la geometría del culling. **Red primero.**
- [ ] **(3) El radar olvida a los coches al pasar de road a roadlink.** Al transicionar road→roadlink,
      `traffic/radar.py::_scan_lane_ahead` acota los candidatos a la geometría de `mode.current_id` (solo
      el link) → olvida a los coches que aún tenía delante en el road que deja (si se podía seguir de
      frente y el de delante iba más lento, lo choca). Además, al **entrar** a un road por un roadlink no
      ve a los que ya circulan dentro (les corta el paso). Arreglo probable: durante la ventana de
      aproximación/transición, ampliar el match topológico de "delante en mi carril" a la **cadena
      current→next**: road actual + su roadlink saliente (`next_link`) + el `to_road` del link, para que
      detecte a los de las salidas y a los de dentro del road destino. **Red primero** (extender la red
      de equivalencia del radar de S28).
- [ ] **(4) Road cerrado = inexistente en TODOS los casos.** Hoy `is_closed` se respeta a medias:
      `_calculate_next_link` salta el road destino cerrado (Filtro A, `navigation.py`) y el spawn localiza
      con `ignore_closed_roads=True`. **Hueco encontrado:** `traffic/overtake.py::_find_valid_overtake_lane`
      NO comprueba `road_geom.is_closed` → la IA puede adelantar metiéndose en un carril cerrado. **Auditar
      TODOS los consumidores** (spawn / `get_location_context` en todos sus call-sites, selección de carril
      de adelantamiento, barridos del radar, navegación por LatLink) y centralizar con un helper
      `_is_road_usable(road_id)` (existe y no cerrado) aplicado de forma consistente. **Red primero.**

**Criterio de aceptación:** las 4 conductas corregidas y **validadas por el usuario en LFS**; red de
caracterización en cada fix antes de tocar el orquestador; suite + CI verdes. No tocan la API pública.

---

## 🔀 Merge a `main`

Todo el refactor vive en la rama **`refactor/estabilizacion`**. `main` permanece intacta
hasta el merge.

**Momento del merge — RE-DECIDIDO con el usuario (S23):** se mantiene **TODO en la rama** hasta
que esté **publish-ready** (Fase 5 + Fase 6 completas + validado en LFS) y entonces se hace **un
solo merge** a `main`, seguido del publish. Esto sustituye la decisión de S17 (que mergeaba tras
Fase 5 y dejaba Fase 6 para después): ahora Fase 6 (refactor + limpieza de API + init) va **antes**
del merge/publish, porque el split de `utils.py` es un cambio de **API pública** que post-publish
rompería a usuarios. Mantener todo en la rama deja `main` impoluta hasta el release y evita un
estado intermedio medio-refactorizado en `main`.

**Criterio para mergear a `main`:**
- Fases 5 y 6 (pre-publish) completadas.
- `pytest` verde desde `.venv` + **CI verde** (verificable con `gh run list`, ver memoria del equipo).
- El usuario ha **validado el comportamiento en LFS**, incluida la validación pendiente del
  ceda-el-paso del ACC (**W4**, Fase 5 — hoy bloqueada por `zones: 0`).

**Publish a PyPI:** tras el merge a `main` (runbook en `docs/dev/PUBLICACION.md`). El framework en
sí es publicable hoy; se adelanta el refactor + limpieza de API para un primer release cohesionado
y con la **API pública ya estable**. El merge y el publish los decide y autoriza el usuario; tras
el merge se continúa desde `main`.

## Ideas / pendientes sin fase asignada

- **Post-merge (aplazado en S27): partir `map_ui.py` (3161) y `map_recorder.py` (2520)** —
  resto de P3. Es tooling offline de edición de mapas: no toca el runtime de conducción ni la
  API pública, y **no tiene red de caracterización** → escribirla antes de partir
  (MODUS_OPERANDI §3). Se sacó de pre-publish para no retrasar el merge.
- **P9**: decidir qué hacer con `tools/setup_lfs.py` (roto: importa `DESIRED_LFS_CONFIG`,
  que no existe en `settings.py`) — recuperarlo o eliminarlo. **En bloque con
  `src/lfs_insim/configuration.py`** (`LFSConfigManager`), que quedó **huérfano** (S16):
  su único consumidor es ese tool roto. Reutilizable para el fallback de `admin_pass`
  desde cfg.txt (idea de abajo).
- **Fallback opcional de `admin_pass` desde cfg.txt** (idea S12, tras el incidente del
  ISI rechazado): que `config/settings.py` (capa de proyecto — NUNCA el core, P14) lea
  `Game Admin` de `{LFS_DIR}/cfg.txt` solo si `admin_pass` está vacío y `tcp_host` es
  local, dejando en el log de dónde salió. Limitaciones conocidas: solo localhost, y
  LFS escribe cfg.txt al SALIR (en caliente puede estar desactualizado). La pista de
  diagnóstico del cliente ("ISI likely rejected") ya cubre el 90 % del dolor; esto
  sería solo comodidad. Encaja con la decisión pendiente de P9 (setup_lfs.py).
- Migrar `rutas_grabadas.txt` a JSON cuando se toque `RouteManager` (ver P6).
- **P8**: confirmar contra `docs/InSim.txt` el caso de string variable vacío sin padding.
- `interval` a 100 ms como cambio deliberado, si se quiere, al auditar el hot-loop (Fase 5).
