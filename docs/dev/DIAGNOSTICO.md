# 🩺 Diagnóstico del proyecto

> Escaneo inicial: **2026-07-01** (S01). Se actualiza cuando se descubre algo nuevo.
> Métrica base: 72 archivos Python, ~15.500 líneas. 221 tests. Git limpio en `main`.

## Veredicto

El **núcleo del framework** (`src/lfs_insim/`) está **sano y bien diseñado**. La deuda
—estructural y funcional— está **concentrada en `insims/ai_control/`**. No hay nada roto
de forma irrecuperable; el proyecto es una base sólida con un módulo que ha crecido sin
refactorizar.

---

## ✅ Lo que está bien (no tocar sin motivo)

- **Core del framework**: composición por MRO, patrón "coup d'état" del loader, *Active
  Packet Registry* (descarta tipos no manejados antes de decodificar). Diseño limpio en
  `insim_client.py`, `insim_app.py`, `insim_loader.py`.
- **Modelo de dominio** `users_management/um_class.py`: dataclasses con conversión de
  unidades LFS↔SI vía properties (`Coordinates.x_m`, `Speed.speed_kmh`, etc.). Muy correcto.
- **Documentación**: `README.md` y `CLAUDE.md` excelentes; `docs/tutorial/` con 72 fichas
  de paquetes; `docs/InSim.txt` como fuente de verdad del protocolo.
- **Intención arquitectónica de `ai_control`**: el contrato explícito de mixins en
  `base.py` (`_MixinBase`) es una buena idea (documenta qué ve `self`).
- **Suite de tests amplia**: 221 tests existentes (aunque hoy no corran, ver P1).

---

## 🔴 Problemas de severidad ALTA

### P1 — Entorno no reproducible; la suite no corre  ✅ RESUELTO (S02)
- `import lfs_insim` falla y `pytest` no está instalado en el Python del sistema (3.14).
- Hay **221 tests** que no se pueden ejecutar → inversión grande inutilizada; imposible
  refactorizar con seguridad sin ellos.
- **Acción:** venv + `pip install -e ".[dev]"` (Fase 0).
- **Resuelto (S02, 2026-07-01):** creado `.venv` (Python 3.14.6, ignorado por git),
  `pip install -e ".[dev]"` OK (pytest 9.1.1). Al correr por primera vez: **216/221 verdes**,
  5 rojos en `tests/test_packet_base.py::TestValidateStringLengths`. Investigado: **los tests
  estaban mal, no el código** (ver P8). Corregidos → **221/221 verde**.

### P2 — Lógica frágil en traffic / navigation / radar
- Los últimos ~15 commits son casi todos *fixes* de los mismos ficheros (radar, traffic,
  freeroam, overtake). Churn: `map_ui.py` ×36, `traffic.py` ×22, `navigation.py` ×12.
- Señal explícita de fragilidad: `traffic.py:655` — comentario "PARCHE DE SEGURIDAD
  MATEMÁTICO".
- Bucle caliente `AIControl.on_ISP_MCI` (`app.py:150`) ejecuta navegación + física +
  tráfico para **cada** coche, en el **hilo de IO**, a la frecuencia de MCI.
- **Acción:** tests de caracterización (Fase 1) → estabilizar causa raíz (Fase 2).

---

## 🟠 Problemas de severidad MEDIA

### P3 — Ficheros gigantes (violan responsabilidad única)
| Archivo | Líneas |
|---|---|
| `insims/ai_control/map_ui.py` | 1841 |
| `insims/ai_control/nav_modes/freeroam/map_recorder.py` | 1604 |
| `insims/ai_control/traffic.py` | 1084 |
| `insims/ai_control/navigation.py` | 683 |

(`insim_enums.py` 1314 y `packets/insim.py` 829 son grandes pero legítimos: son el
protocolo. No cuentan como deuda.)

### P4 — Acoplamiento cruzado entre mixins
- `base.py` declara **~40 métodos cross-mixin** (líneas 87-125): cualquier mixin llama a
  métodos de cualquier otro vía `self`. Es un "God object" repartido en archivos; la
  modularidad es de fichero, no de responsabilidad. Refactor estructural = Fase 3.

---

## 🟡 Problemas de severidad BAJA (limpieza rápida — Fase 0)

### P5 — Config incoherente / insegura (`config/settings.py`)  ✅ RESUELTO (S03)
- `interval: 10` (línea 76) → LFS envía MCI/NLP a **100 Hz**, no a 100 ms como dicen
  README y CLAUDE.md. El hot-loop de IA corre 10× más rápido de lo documentado. **Decidir
  el valor correcto y alinear docs.**
- `admin_pass: 'abc'` (línea 74) y `LFS_DIR = 'C:/LFS'` (línea 59): valores locales
  hardcodeados en fichero versionado. Mover a config local / variable de entorno.
- `from lfs_insim.insim_enums import ISF` (línea 47): **import muerto** (sin usos) y además
  mal ubicado (en medio de definiciones de clase).
- **Resuelto (S03, 2026-07-02):** import de `ISF` eliminado. `admin_pass` y `LFS_DIR` se leen
  de env (`LFS_ADMIN_PASS`, `LFS_DIR`) con override en `config/settings_local.py` (gitignorado;
  plantilla en `settings_local.example.py`). **Decisión sobre `interval`: se mantiene `10`**
  (la conducción/PID está afinada a ese ritmo; cambiarlo sería un cambio de comportamiento,
  no limpieza) y se alinearon README/CLAUDE.md para documentar 10 ms. Si se quiere 100 ms,
  será un cambio deliberado en Fase 2 (auditoría del hot-loop).

### P6 — Basura y datos en el repo  ✅ RESUELTO (S03)
- `src/lfs_insim/utils_temp.py`: solo contiene `class DummyNode: pass`. **Eliminar** (o
  reubicar si algún test lo referencia — verificar antes).
- `rutas_grabadas.txt`: fichero de datos de **437 KB / 9916 líneas** versionado en la raíz.
  Se carga con `ast.literal_eval` (seguro) pero con **ruta relativa** dependiente del CWD
  (`nav_modes/route/manager.py:74,78,175`) → frágil según desde dónde se ejecute.
  Evaluar: sacarlo del repo, formato robusto (JSON) y ruta absoluta anclada al proyecto.
- **Resuelto (S03, 2026-07-02):** `utils_temp.py` eliminado (verificado sin usos). Ruta de
  rutas anclada a la raíz vía `RUTAS_FILE = BASE_DIR / 'rutas_grabadas.txt'` en `manager.py`.
  **Decisión: el fichero sigue versionado** (son datos del usuario que conviene sincronizar
  entre dispositivos; `ast.literal_eval` es seguro). Migrarlo a JSON queda como idea para
  cuando se toque `RouteManager` (no urgente).

### P7 — Nombres confusos y comentarios residuales
- `behavior.py`: `target_speed_kmh_use` vs `target_speed_kmh` y `target_point_use` vs
  `target_point_m` (líneas 37-40) — patrón "intención vs valor en uso" mal nombrado.
- Comentarios residuales dirigidos a uno mismo: `# En tu dataclass o clase AIBehavior:`
  (`behavior.py:49`), marcadores `[!] NUEVO` / `[!] OPTIMIZACIÓN`. Ruido a limpiar durante
  el refactor de cada zona (no en bloque).

### P8 — Caso borde: string variable vacío no recibe padding (`packets/base.py`)
- `validate_string_lengths` (`base.py:127`) hace el padding bajo `if new_val:`, así que un
  string vacío se queda en **0 bytes** (sin terminador null). 0 es múltiplo de 4, así que el
  paquete no queda malformado, pero **no está verificado** si LFS acepta un campo de texto
  variable de longitud 0 (p. ej. `ISP_MST` con `Msg=""`).
- Descubierto en S02 al corregir los tests de `TestValidateStringLengths`: esos 5 tests
  codificaban una fórmula de padding equivocada (esperaban longitudes NO múltiplo de 4, uno
  incluso sin terminador null) y **nunca se habían ejecutado**. El código es correcto según
  el protocolo (`Size = bytes/4` obliga a bloques múltiplo de 4). Tests corregidos para
  caracterizar el comportamiento real; el caso vacío queda documentado en el propio test.
- **Acción:** decisión pendiente — confirmar contra `docs/InSim.txt` si el vacío debe
  rellenarse a 4 bytes (`"\x00\x00\x00\x00"`) o dejarse en 0. Riesgo bajo; no urgente.

### P9 — `tools/setup_lfs.py` roto: importa un símbolo inexistente
- `tools/setup_lfs.py:15` hace `from config.settings import LFS_DIR, DESIRED_LFS_CONFIG`,
  pero **`DESIRED_LFS_CONFIG` no existe** en `settings.py` → el tool muere al arrancar
  (descubierto en S03 al limpiar settings). Probablemente se borró/renombró en algún refactor.
- **Acción:** decidir si el tool se recupera (definir `DESIRED_LFS_CONFIG` con los valores
  de cfg.txt deseados: puerto InSim, OutSim, etc.) o se elimina. No bloquea nada.

### P10 — matplotlib: dependencia externa sin declarar  ✅ RESUELTO (S03)
- `map_renderer.py:4` importa `matplotlib`, pero ni `insim.json` ni `pyproject.toml` lo
  declaraban, y README/CLAUDE.md afirmaban "sin dependencias externas". Cualquier import de
  `ai_control` (y por tanto los tests de caracterización de Fase 1) fallaba en un venv limpio.
- **Resuelto (S03, 2026-07-02):** declarado en `insim.json` (`python_dependencies`), añadido
  al extra `[dev]` de `pyproject.toml`, instalado en `.venv` (3.11.0) y aclarado en CLAUDE.md
  (el core sigue siendo stdlib puro; la dependencia es solo de `ai_control`).

---

## 🏗️ Auditoría del core para nivel profesional (S04, 2026-07-02)

> Objetivo declarado por el usuario: que **otros desarrolladores puedan usar el framework
> felizmente** y que siga buenas prácticas. Romper los insims existentes es aceptable.
> Los P1–P10 siguen aplicando; estos son adicionales, centrados en `src/lfs_insim/`.

### P11 — Arquitectura invertida: `InSimApp` hereda de `InSimClient` (ALTA, diseño) ✅ RESUELTO (S06)
- Cada módulo **ES** un cliente completo (config, `isi`, `modules[]`, executor...). Solo uno
  ejerce; el resto queda vestigial. El patrón "coup d'état" del loader y los
  `set/reset/force_set_insim_client` existen únicamente para compensar esta herencia.
- Consecuencias: imposible razonar sobre "quién es el cliente"; `InSimApp.__init__` tiene
  efectos globales (registra al primero que se instancia); el aplanado de `modules[]` en el
  loader es frágil.
- **Acción:** invertir a **composición**: un `InSimClient` (conexión + dispatch) y N
  `InSimApp` registradas en él (`client.register(app)`). El loader construye el cliente y
  registra las apps en orden de dependencias. Adiós golpe de estado.
- **Resolución (S06):** `InSimApp(PacketSenderMixin)` ya no hereda de `InSimClient`;
  `client.register(app)` + cliente único perezoso en el loader (o inyectado con
  `InSimLoader(client=...)`); `modules[]`→`apps`. Cambio de comportamiento deliberado:
  el orden de dispatch pasa a ser el de dependencias (antes el dependiente-master recibía
  ANTES que sus dependencias — bug latente). Los 3 insims cargan sin cambios; queda la
  validación en LFS por el usuario.

### P12 — Sin reconexión ni gestión de caída de LFS (ALTA, funcional)
- Si LFS cierra el TCP, el hilo receptor muere y `start()` sigue en
  `while running: sleep(0.1)` para siempre: **proceso zombie** sin conexión, sin aviso a los
  módulos y sin reintento. El docstring de `insim_packet_io.py` dice "mantiene la
  reconexión", pero **no hay ninguna lógica de reconexión**.
- **Acción:** detectar desconexión → notificar (`on_disconnect`) → reintentos con backoff
  (configurable) → re-enviar ISI y re-solicitar estado (`TINY_NCN/NPL`) → `on_reconnect`.

### P13 — Estado global de módulo: sockets y cliente como singletons (ALTA, diseño) ✅ RESUELTO (S06)
- `insim_state.py` guarda sockets y cliente en variables globales; `send_packet()` los lee.
  Impide 2 conexiones en un proceso (LFS admite 8 programas InSim), obliga a los tests a
  hacer `reset_*()` en cada setup/teardown y esconde el ciclo de vida de la conexión.
- **Acción:** encapsular en un objeto conexión/transporte inyectado en el cliente; las apps
  envían a través de su cliente. `insim_state` desaparece o queda como azúcar opcional.
- **Resolución (S06):** `InSimTransport` (nuevo) posee sockets/hilos/stop/lock por
  instancia; el cliente lo posee (inyectable) y hace barrera+decode en `_on_raw_bytes`;
  `client.send = encode_packet + transport.send` (`insim_packet_io.py` y el `send_packet`
  global eliminados). `insim_state` queda como azúcar: solo el "cliente por defecto"
  (fallback del mixin para Command/CMDManager/RouteManager sin `client`). Test de
  aceptación: dos clientes coexisten en un proceso con recepción y envío independientes.

### P14 — El core importa `config.settings` del CWD (MEDIA, packaging)
- `InSimClient.__init__` hace `from config.settings import get_config` y `cli.py` hace
  `sys.path.insert(0, os.getcwd())` para que funcione. Un paquete instalable **no puede
  depender de un `config/` del directorio del proyecto**: rompe fuera del repo y en tests.
- **Acción:** defaults internos en el paquete (`lfs_insim/config.py` o dataclass
  `InSimConfig`); el CLI (no el core) carga la config de proyecto/env si existe.

### P15 — API pública indefinida (MEDIA, DX)
- `lfs_insim/__init__.py` exporta 9 nombres, pero los tutoriales/insims importan de
  `lfs_insim.packets`, `insim_enums`, `utils`, `insim_packet_class` (facade duplicado de
  `packets`)... `packets/insim.py` hace `from insim_enums import *` (contamina), casi ningún
  módulo define `__all__`.
- **Acción:** definir la superficie pública (un solo punto de import recomendado), `__all__`
  en módulos, deprecar `insim_packet_class`, y documentar qué es API y qué es interno (`_`).

### P16 — Packaging y tooling incompletos (MEDIA, DX)
- `pyproject.toml`: `readme = "README"` (el fichero es `README.md` → metadata rota),
  sin `license`, `requirements.txt` redundante con `pyproject`, y `generate-stubs` /
  `update-all` expuestos como comandos globales (deberían ser subcomandos: `lfs-insim stubs`).
- No hay: linter/formatter (ruff), mypy, CI (GitHub Actions), pre-commit portable
  (hay hook bash casero), CHANGELOG, ni versión única (0.2.0 en pyproject vs 1.0.0 en
  manifests).
- **Acción:** arreglar metadata, adoptar ruff + mypy gradual, CI con pytest en push/PR,
  CHANGELOG y política de versiones.

### P17 — Código muerto y comentarios que mienten (BAJA)
- `InSimApp._resolve_dependencies()` **no lo llama nadie** (el docstring dice "llamado
  automáticamente por el Loader"); `get_insim()` funciona por el fallback a
  `loader._instances`.
- `start()` comenta "Keep-Alive reactivo (ver on_ISP_TINY abajo)" pero vive en
  `on_packet_received`. CLAUDE.md decía que `on_tick` corre cada `interval` ms: en realidad
  es **fijo a 100 ms** (`time.sleep(0.1)` hardcodeado), independiente de `interval`.
- **Acción:** borrar lo muerto, alinear comentarios, y decidir si `on_tick` debe ser
  configurable.

### P18 — Envío por UDP roto (BAJA, funcional)
- `send_packet(use_udp=True)` usa el socket UDP que está `bind()` para **escuchar**, sin
  `connect()` ni destino: `sendall()` fallaría. Nadie lo usa hoy.
- **Acción:** eliminarlo o implementarlo bien (socket de envío con destino) cuando se
  encapsule el transporte (P13).

### P19 — Duplicación en el camino de serialización (BAJA)
- `_extract_values()` recalcula el padding de strings que ya hizo
  `validate_string_lengths()` ("por seguridad"): dos fuentes de verdad para el mismo layout.
  El decoder además hace `.strip()` a los strings, que puede comer espacios significativos.
- **Acción:** una sola ruta encode (prepare → pack) con tests golden-bytes; revisar `.strip()`.

### P20 — Loader: errores tragados y versiones a mano (BAJA)
- `load()` captura el fallo de carga de una dependencia, lo loguea y **sigue** (el error real
  aflora después, lejos de la causa). `_parse_version/_check_version` reinventan
  `packaging.version` con soporte parcial.
- **Acción:** fail-fast con excepción encadenada; si se quieren constraints serios, usar
  `packaging` (o documentar el subset soportado).
- (S05) Además: si el paquete del InSim **no tiene `__init__.py`** y el entry point es otro
  archivo, `spec_from_file_location(name, None)` devuelve `None` y la carga muere con un
  error críptico (`'NoneType' object has no attribute 'loader'`). Documentar el requisito
  o dar un mensaje claro. Caracterizado en `tests/test_loader.py::test_sin_init_py_falla`.

### P21 — Envío de ISP_REO / ISP_HCP / ISP_IPB-con-bans roto (MEDIA, funcional) — descubierto en S05
- `_extract_values()` (insim_packet_sender.py) solo aplana listas cuando el `fmt` es una
  **tupla variable** `(fmt, límite)`. Con listas de formato **fijo** (`repeat('B', 48)` en
  `ISP_REO.PLID`, `repeat(CarHCP, 32)` en `ISP_HCP.Info`) y con tuplas anidadas
  (`ISP_IPB.BanIPs`, fmt `('4B', None)`) el valor llega a `struct.pack` sin aplanar →
  `struct.error: pack expected N items (got M)`. **Enviar IS_REO, IS_HCP o IS_IPB con
  bans falla siempre.** Nadie los usa hoy (por eso no se había notado).
- Caracterizado en `tests/test_golden_bytes_send.py::TestEnviosRotos`.
- **Acción:** arreglar al unificar la ruta de serialización (P19, Fase 3); entonces
  sustituir los tests de excepción por golden-bytes reales.

---

## Mapa de zonas de `ai_control` (para orientarse)

- `app.py` — clase `AIControl`, hot-loop `on_ISP_MCI`, gestión de `AIBehavior`.
- `behavior.py` — estado por IA (`AIBehavior`), `GearMode`, config de velocidad adaptativa.
- `commands.py` — registro de comandos de chat (`_CommandsMixin`).
- `navigation.py` — planificación de ruta y de enlaces del grafo (`_NavigationMixin`).
- `physics.py` — volante, pedales, marchas (`_PhysicsMixin`).
- `traffic.py` — radar, ACC (adaptive cruise), adelantamientos, zonas de intersección (`_TrafficMixin`).
- `map_ui.py` — UI de botones en LFS (tabs Info/Debug/Run, grabación) (`_MapUIMixin`).
- `nav_modes/route/` — `RouteMode` + `RouteManager` (waypoints grabados).
- `nav_modes/freeroam/` — `FreeroamMode`, `graph.py` (RoadLink/LateralLink/Road),
  `map_recorder.py`, `map_renderer.py`, `geometry.py`.
