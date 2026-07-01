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

### P1 — Entorno no reproducible; la suite no corre
- `import lfs_insim` falla y `pytest` no está instalado en el Python del sistema (3.14).
- Hay **221 tests** que no se pueden ejecutar → inversión grande inutilizada; imposible
  refactorizar con seguridad sin ellos.
- **Acción:** venv + `pip install -e ".[dev]"` (Fase 0).

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

### P5 — Config incoherente / insegura (`config/settings.py`)
- `interval: 10` (línea 76) → LFS envía MCI/NLP a **100 Hz**, no a 100 ms como dicen
  README y CLAUDE.md. El hot-loop de IA corre 10× más rápido de lo documentado. **Decidir
  el valor correcto y alinear docs.**
- `admin_pass: 'abc'` (línea 74) y `LFS_DIR = 'C:/LFS'` (línea 59): valores locales
  hardcodeados en fichero versionado. Mover a config local / variable de entorno.
- `from lfs_insim.insim_enums import ISF` (línea 47): **import muerto** (sin usos) y además
  mal ubicado (en medio de definiciones de clase).

### P6 — Basura y datos en el repo
- `src/lfs_insim/utils_temp.py`: solo contiene `class DummyNode: pass`. **Eliminar** (o
  reubicar si algún test lo referencia — verificar antes).
- `rutas_grabadas.txt`: fichero de datos de **437 KB / 9916 líneas** versionado en la raíz.
  Se carga con `ast.literal_eval` (seguro) pero con **ruta relativa** dependiente del CWD
  (`nav_modes/route/manager.py:74,78,175`) → frágil según desde dónde se ejecute.
  Evaluar: sacarlo del repo, formato robusto (JSON) y ruta absoluta anclada al proyecto.

### P7 — Nombres confusos y comentarios residuales
- `behavior.py`: `target_speed_kmh_use` vs `target_speed_kmh` y `target_point_use` vs
  `target_point_m` (líneas 37-40) — patrón "intención vs valor en uso" mal nombrado.
- Comentarios residuales dirigidos a uno mismo: `# En tu dataclass o clase AIBehavior:`
  (`behavior.py:49`), marcadores `[!] NUEVO` / `[!] OPTIMIZACIÓN`. Ruido a limpiar durante
  el refactor de cada zona (no en bloque).

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
