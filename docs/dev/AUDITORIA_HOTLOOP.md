# 🔬 Auditoría del hot-loop `on_ISP_MCI` (Fase 5)

> Hecha en S22 (2026-07-07). Mediciones reales con `.venv` (Python 3.14) sobre datos
> sintéticos (fixtures de `tests/insims/ai_control/conftest.py`), sin LFS. El script de
> benchmark es scratchpad (no versionado); los métodos medidos se pueden re-ejercitar con
> las factorías del conftest.

## Objetivo

Entender **coste por tick** y **frecuencia real** del bucle que conduce a las IAs, con el
dispatch ya fuera del hilo de IO (Fase 3), para decidir si hace falta optimizar antes de
seguir con "consolidar radar/geometría" y el FSM de adelantamiento.

## Frecuencia real

- LFS envía **MCI a `interval` = 10 ms → ~100 Hz**, en paquetes de **≤8 coches** (con >8
  coches manda varios MCI por intervalo, pero el trabajo es **por coche**, no por paquete;
  partir en paquetes no cambia el coste total).
- Por cada MCI corren **dos** handlers en orden de dependencia: primero
  `users_management.on_ISP_MCI` (vuelca telemetría), luego `ai_control.on_ISP_MCI` (conduce).
- **Clave:** el trabajo caro NO corre a 100 Hz. El orquestador `_update_traffic_behavior`
  **auto-regula su radar** con una compuerta (`traffic.py:294`):
  `_radar_interval = 0.1 + random.uniform(0, 0.05)` → **~7–10 Hz por IA**, y el jitter
  aleatorio **desincroniza** a las IAs para que no escaneen todas en el mismo tick. La
  navegación por tick solo hace *tracking* topológico incremental (barato); NO re-localiza
  desde cero (`get_location_context` solo se llama al "despertar" de cada IA).

## Coste por tick (medido)

| Componente | Coste | Escala |
|---|---|---|
| `um.on_ISP_MCI` (construir `Telemetry`) | ~1.2 µs/coche | O(coches), lineal |
| Física (`_handle_steering` + `_handle_pedals_and_gears`) | pocos µs/IA | O(1) |
| Nav freeroam por tick (tracking topológico) | pocos µs/IA | O(nodos del road actual, ~10–20) |
| **Radar `_scan_lane_ahead`** | **~1.5 µs/vehículo escaneado** | **O(N) por IA → O(N²) global** |
| **`get_location_context`** | **56 µs (50 nodos) → 1001 µs (1300 nodos)** | **O(nodos del mapa entero)** |

Radar por IA que escanea: N=8 → 14 µs, N=16 → 26 µs, N=32 → 50 µs.
`get_location_context`: 50 nodos → 56 µs; 200 → 167 µs; 600 → 473 µs; **1300 (≈south_city)
→ ~1.0 ms**.

## Presupuesto

Con compuerta + jitter + caché compartida de contexto de humanos
(`_radar_human_cache`, en la app, no por IA → un humano se localiza 1 vez cada 0.1 s en
total), el **peor tick** (todas las IAs escaneando a la vez, cosa que el jitter rompe):
16 IAs × 26 µs ≈ 420 µs + base ≈ 160 µs ≈ **0.6 ms ≪ 10 ms**.

**Conclusión: el hot-loop NO tiene problema de rendimiento hoy.** Hay holgura cómoda hasta
~16–20 IAs. El diseño actual (throttle del radar + jitter + caché compartida) ya está bien
pensado para el caso común. Los hallazgos de abajo son de **robustez y escalado futuro**, no
urgencias.

## Hallazgos (por relación coste/beneficio)

1. **`get_location_context` = O(mapa entero), ~1 ms en mapa grande.** Hoy está *contenido*
   (solo en el "despertar" de cada IA y para humanos, cacheado 0.1 s y compartido), pero es
   **frágil**: cualquier ruta que lo llame por-tick por-IA revienta el presupuesto. El coste
   real está en el cálculo de distancias sobre TODOS los nodos del mapa → la única cura de
   fondo es un **índice espacial** (grid/celdas). Esto es el "consolidar radar/geometría" del
   plan. **[S22] Cambio menor ya aplicado:** se dejó de reconstruir el dict fusionado
   `{**road_links, **lateral_links}` en cada llamada (ahora `itertools.chain`) — limpieza
   correcta (elimina una allocation), pero de impacto **despreciable** (~0.2 µs/llamada); el
   coste dominante (distancias sobre nodos) sigue intacto.

2. **Radar O(N²).** ~1.5 µs/vehículo por IA que escanea. Bien hasta ~16–20 IAs; degrada más
   allá. Un índice espacial lo bajaría a ~O(N·k). Mismo trabajo que el hallazgo 1
   (consolidar radar/geometría con caracterización primero).

3. **`Coordinates.x_m/y_m/z_m` (y `Speed.speed_kmh`) recalculan la conversión LFS→humano en
   CADA acceso** (`um_class.py:27`, propiedad que llama a `lfs_pos_to_meters` = una división).
   En el profile del radar, esas propiedades + `lfs_pos_to_meters` suman **~5.6 M llamadas** y
   **~28 % del tiempo del radar**. Son valores inmutables tras construir la telemetría →
   cachearlos a atributo plano (calcular 1 vez) es un win transversal. Toca `users_management`
   (usado en todas partes) → refactor que preserva comportamiento, **necesita red puesta**.
   Candidato natural a **Fase 6** (que ya toca `um` y nombres).

## Recomendación de rumbo

El loop está sano; no hay que optimizar por urgencia. El siguiente ítem del plan
("consolidar radar/geometría en unidad testeable") es el que ataca de raíz los hallazgos 1 y
2 (índice espacial) y debe hacerse **con caracterización primero** (la red de
`test_map_recorder.py`, S22, ya cubre `get_location_context`). El hallazgo 3 encaja mejor en
Fase 6.
