# 📍 Estado actual

> Actualizado: **2026-07-10** — S26: **W2 (Fase 6) — `lfs-insim init` con perfiles**. Confirmado
> con el usuario: **cierre = `self.client.stop()`** (parada limpia nativa; `TINY.CLOSE` con la
> reconexión P12 activa solo reconectaría en vez de apagar) y **`--full` por defecto**. `init` gana
> flags mutuamente excluyentes `--full`/`--minimal` (registro extensible `_INIT_PROFILES`); `--full`
> = scaffold de bot real (cierre admin-guarded con `client.stop()`, permisos por UCID, `on_reconnect`,
> `TINY.NCN/NPL`), `--minimal` = template escueto de antes (byte-idéntico). Red primero (+10 tests:
> perfiles, mutua exclusión, y ambos templates compilan y `exec`→`InSimApp`). Suite **680**; ruff
> limpio; guías cuadradas. **W1+W5+W2 hechos → próximo W3 (refactor interno + radar).**
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**S26 (2026-07-10) — Fase 6 · W2: `lfs-insim init` con perfiles `--minimal`/`--full`
(implementado y verificado, NO requiere LFS):** segundo ítem de DX pre-publish. `init` ahora
acepta flags **mutuamente excluyentes** `--full`/`--minimal` (default **`--full`**, decidido con el
usuario). **Dos decisiones confirmadas (pregunta con recomendación, MODUS_OPERANDI §6):**
(1) **mecanismo de cierre = `self.client.stop()`** — parada limpia nativa del framework (cierra
hilos/sockets, sin reconexión) y reentrante-segura desde un handler (S09/S12); `TINY.CLOSE` se
descartó porque, con la auto-reconexión P12 activa por defecto, LFS cerraría el socket y el cliente
**reconectaría** en vez de apagarse. (2) **`--full` por defecto** — la experiencia por defecto debe
mostrar los patrones correctos; quien quiera lo escueto usa `--minimal`. **Implementación (`cli.py`):**
templates como **strings con centinelas** (`__CLASSNAME__`/`__MODNAME__`) rellenados por
`str.replace` (no f-strings → evita escapar `{{}}` en 90 líneas de código generado); **registro
extensible** `_INIT_PROFILES` (dict perfil→función de render) para admitir más perfiles en el futuro
sin tocar `cmd_init`. **`--minimal`** = el template de antes, **byte-idéntico**. **`--full`** trae el
esqueleto de un bot real: `set_isi_packet` con `ISF.LOCAL`; `TINY.NCN/NPL` en `on_connect`; tracking
de admin por NCN (`self.admins[UCID] = packet.Admin == AD_NOAD.ADMIN`) con `_is_admin(ucid)`
(**UCID 0 = host local, siempre admin**); comando **`cerrar` admin-guarded** que valida permisos y
llama `self.client.stop()`; y **`on_reconnect`** que resetea `self.admins` (los NCN entrantes lo
repueblan). **Red primero (`tests/test_cli.py`, +10 tests):** perfiles (default=full, minimal, full
explícito), **mutua exclusión** (`--minimal --full` → SystemExit), CamelCase + manifiesto, guard de
"ya existe", y —lo más valioso— **ambos templates `compile()` y `exec()`→ subclase de `InSimApp`**
(un scaffold roto es un fallo de DX serio). **Verificación:** suite **680/680** (670 + 10); `ruff
check .` + `format --check .` limpios; `lfs-insim list` OK; render de `--full` eyeballeado.
**3.9-safe** (`dict[int, bool]` es PEP 585, ya usado en `test_insim`; sin uniones PEP 604).
**Guías cuadradas (W5):** quickstart usa `--minimal` explícito + nota del `--full`; README, CLAUDE.md
y CHANGELOG (bullet en Añadido) actualizados. Solo CLI/tests/docs offline → **no requiere validación
en LFS**.

**S25 (2026-07-09) — Fase 6 · W5: sweep de API pública (jerarquía de excepciones; NO requiere
LFS):** repaso final de la API pública antes del primer publish (última ventana gratis). **Exports
de `lfs_insim`** (`__version__` + 10 nombres + excepciones) y **`DEFAULT_CONFIG`** (20 claves)
revisados y confirmados **sin cambios** (la guía `api-publica.md` los refleja uno a uno).
**Jerarquía de excepciones — hallazgo:** 2 de las 7 **no se lanzaban en ningún sitio** (ni core, ni
insims, ni tests — solo se asertaban como subclases): `InSimProtocolError` e `InSimCommandError`.
**Decisión (recomendación explícita, el usuario delegó): Opción 2 — quitar `InSimProtocolError`,
mantener `InSimCommandError`.** Razón: pre-publish no hay usuarios → quitar no es breaking real y
re-añadir una excepción **nunca** es breaking → recortar ahora lo injustificable. `InSimProtocolError`
es lo injustificable: el framework **estructuralmente no puede** lanzarla (P24: LFS no da feedback al
rechazar un ISI) y su caso de "paquete inválido" ya lo cubre `InSimPacketError`. `InSimCommandError`
se queda: tipo de error coherente del **sistema de comandos público** (`CMDManager`/`Command`, con
`.command_name`), punto de extensión para autores de módulos. De paso, **`exceptions.py` traducido a
inglés** (MODUS_OPERANDI §5: módulo público del core tocado en la pasada pre-publish) y docstring de
`InSimCommandError` aclarando que es para módulos. `CLAUDE.md:210` ya listaba exactamente las 5
subclases restantes → **correcto sin tocar**. **Regla de trabajo nueva** (a petición del usuario, en
`MODUS_OPERANDI §6`): al preguntar con opciones, **marcar siempre la recomendada** y por qué.
**Verificación:** suite **670/670** (671 − 1 test de subclase); `ruff check .` + `format --check .`
limpios (96 archivos); smoke de import OK; `lfs-insim list` carga los 4 insims. Solo API/tests/docs
offline → **no requiere validación en LFS**.

**S24 (2026-07-09) — Fase 6 · W1: split de `utils.py` (implementado y verificado, NO requiere
LFS):** primer ítem pre-publish. Se sacó de `lfs_insim.utils` (la API PÚBLICA del framework) la
geometría/navegación **específica de la IA** y se movió a `ai_control`
(`nav_modes/freeroam/geometry.py`, que ya existía con los helpers 2D de zonas). **Se movieron 9
funciones:** `calc_target_heading`, `get_heading_diff`, `calc_deviation_angle`,
`calc_dist_point_to_segment_3d`, `get_closest_node_index`, `determine_smart_spawn_index`,
`apply_antilag_window`, `evaluate_dynamic_capture`, `is_target_ahead_and_in_lane`. **Se quedan en
el framework** (primitivas reutilizables): comandos (`separate_*`, `Command`/`CMDManager`),
`strip_lfs_colors`/`TextColors`, `PIDController`, conversiones `lfs_*` y **`calc_dist_3d`**.
**Red primero (MODUS_OPERANDI §3):** solo 3 de las 9 tenían test directo (en `test_utils.py`) →
nuevo `tests/insims/ai_control/test_geometry.py` (**44 tests**): las 3 movidas de `test_utils.py`
+ **29 de caracterización nueva** para las 6 sin cobertura. La red se escribió y verificó VERDE
contra la ubicación de origen (`lfs_insim.utils`) ANTES de mover, luego se giró el import al
destino → **extracción sin cambio de lógica** demostrada. **Quirk cazado por la red:**
`is_target_ahead_and_in_lane`, cuando el coche está delante pero **fuera de carril**, NO reporta la
distancia lateral real: devuelve `0.0` (solo la devuelve en detección peligrosa). **Imports
actualizados:** `physics.py`, `navigation.py`, `map_recorder.py`, `route/manager.py` (fuente; los 2
últimos y navigation ya importaban de `geometry.py` → sin aristas nuevas) + `test_geometry.py`;
`__all__` de `utils.py` recortado a `calc_dist_3d`. **W5 (parte ligada a W1):** `docs/guia/
api-publica.md` actualizada (geometría de IA fuera del framework) + entrada `[Rompe la API]` en
`CHANGELOG.md`. **Verificación:** suite **671** (642 baseline − 15 movidos de `test_utils` + 44 =
+29); `ruff check` + `format --check` limpios en lo tocado; `lfs-insim list` carga los 4 insims;
3.9-seguro por construcción (`from __future__ import annotations` en `geometry.py`, sin uniones
PEP604 en runtime; CI valida 3.9 en el push). **Hallazgo (para W3):** `is_target_ahead_and_in_lane`
es **código muerto** (no se llama en ningún sitio) — se migró igual por seguridad (con red),
candidata a eliminación al revisar el radar/FSM en W3.

**S23 (2026-07-08) — Fase 5: índice espacial de geometría para `get_location_context`
(fase (a) del ítem 6; implementado y verificado, NO requiere LFS):** atacado el hallazgo nº1 de
la auditoría S22. `get_location_context` buscaba el road más cercano con un barrido O(nodos
totales); en el south_city AMPLIADO (llegó por sync este arranque: **128 roads / 11.086 nodos**,
~8,5× lo que la auditoría asumió) eso son **~9,2 ms/consulta** (medido — confirma la
extrapolación de S22). Nuevo módulo genérico y testeable `nav_modes/freeroam/spatial_grid.py`
(`SpatialHashGrid`, hash grid uniforme 2D): cada segmento se registra en las celdas de su
bounding-box; una consulta expande anillos Chebyshev y **para en cuanto `best_dist < k·celda`**
(garantía: nada fuera de lo visto puede estar más cerca) o cuando el bloque cubre todas las
celdas ocupadas (→ barrido completo, fallback de siempre). **Fidelidad por construcción:** el
grid solo produce el CONJUNTO de road_ids candidatos; la respuesta la calcula el
`get_closest_geometry` existente sobre esos candidatos **en orden de dict** → distancia 3D y
desempate `<` estricto **idénticos** al barrido lineal. `road_node_idx` no se toca.
**Invalidación:** `self._road_index = None` en los **5 sitios discretos** de mutación de
`self.roads` (3×`clear` de nuevo/carga/borrado de mapa, commit de grabación, `del`); el toggle
`is_closed` NO invalida (geometría intacta; se filtra en caliente). La grabación NO muta roads en
vivo (usa el buffer `current_recording`, que se vuelca solo al commit) → el rebuild solo se paga
al conducir. **Celda = 20 m**, elegida con benchmark (las consultas caen SOBRE la vía → celda
pequeña = menos candidatos; retorno decreciente, 20 m = balance): **~13× (9,2 ms → 0,70
ms/consulta)**; build del índice ~13 ms una vez por mutación del mapa. **Red:**
`test_spatial_grid.py` (12 tests unitarios del grid) + `test_road_spatial_index.py` (**fuzz de
equivalencia**: 8 semillas × 200 puntos × 2 modos ≈ 3200 comparaciones bit-a-bit contra el
barrido lineal, dentro/fuera de vía y con cerradas, + casos borde: road de 1 nodo, sin nodos,
punto lejano, invalidación). Suite **642/642** (617 + 25); `ruff check` + `format --check`
limpios; 3.9-seguro por construcción (`from __future__ import annotations`, `typing.*`, FA102
pasa — CI valida 3.9 en el push; `.venv39` no está en este equipo). Solo tests/tooling offline →
**no requiere validación en LFS**. **Pendiente del ítem 6:** partición espacial de VEHÍCULOS para
el radar O(N²) (fase b — falta caracterizar el radar como unidad ANTES) y revisar el FSM de
adelantamiento.

**S23 (2026-07-08) — planificación de rumbo pre-publish (con el usuario, sin tocar código):** se
**re-secuencia** el plan. El refactor estructural de ai_control (antes post-merge) se ADELANTA a
antes de publicar, junto con la limpieza de la **API pública** (`utils.py`: sacar la
geometría/nav de ai_control del `utils` del framework) y un `lfs-insim init` más robusto (flag
`--minimal`/`--full`, con comando de cierre por defecto). Motivo: el split de `utils.py` cambia la
API PÚBLICA → hay que hacerlo ANTES del primer publish. El radar (ex-6b) se pliega en el refactor
de `traffic.py`. Todo pasa a la **Fase 6 re-secuenciada** (ver PLAN § Fase 6 y § Merge; Próximo
paso abajo). Todo en la rama; un solo merge cuando esté publish-ready + validado (W4), luego
publish. **Decisiones concretas:** `calc_dist_3d` y `PIDController` se QUEDAN en el framework; init
con flag min/full extensible; merge único al final. De paso, el usuario amplió el mapa South City
(→ 176 roads / 12.987 nodos, `cb4471a`; sigue `zones: 0`).

**S22 (2026-07-07) — Fase 5: auditoría del hot-loop `on_ISP_MCI`:** completada (informe con
mediciones reales en `docs/dev/AUDITORIA_HOTLOOP.md`). **Veredicto: el loop está SANO.** MCI
llega a ~100 Hz (paquetes de ≤8 coches; trabajo por coche), pero el trabajo caro NO corre a
100 Hz: el orquestador `_update_traffic_behavior` **auto-regula el radar** con una compuerta
(`_radar_interval = 0.1 + random(0..0.05)` → ~7–10 Hz por IA) y el jitter **desincroniza** a
las IAs; el contexto de humanos se cachea 0.1 s **compartido** entre todas las IAs. Medido:
radar `_scan_lane_ahead` ≈1.5 µs/vehículo (O(N) por IA → O(N²) global), física barata, `um`
≈1.2 µs/coche; el **peor tick** (16 IAs) ≈0.6 ms ≪ 10 ms → holgura cómoda hasta ~16–20 IAs.
Hallazgos de robustez/escalado (NO urgencias): (1) `get_location_context` es O(mapa entero),
~1 ms en mapa grande (≈south_city, 1300 nodos) — contenido hoy pero frágil; cura de fondo =
índice espacial; (2) radar O(N²); (3) `Coordinates.x_m/y_m/z_m` y `Speed.speed_kmh`
**recalculan la conversión en CADA acceso** (~28% del tiempo del radar en el profile) →
cachear a atributo plano, candidato a Fase 6. **Red primero:** nuevo `test_map_recorder.py`
(**8 tests**) que caracteriza `get_location_context` (road más cercano, enlace sobre
road_links ∪ lateral_links, desempate por orden, closed roads). **Limpieza menor aplicada:**
`get_location_context` ya no reconstruye `{**road_links, **lateral_links}` en cada llamada
(ahora `itertools.chain` — mismo orden, claves nunca colisionan) → elimina una allocation;
impacto de perf **despreciable** (~0.2 µs/llamada, medido) — el coste dominante son las
distancias sobre nodos, sin tocar. Suite **617/617** (609 + 8); ruff limpio. Solo
tests/tooling offline → **no requiere validación en LFS**. Commits: `b55a35f` (render, ver
S21) + los de S22.

**S21 (extra, 2026-07-07) — mejora del render del mapa (`map_renderer.py`), no planeada:** el
usuario avisó de que el renderer le estaba limitando para editar mapas grandes. Problemas del
render viejo (visibles en `south_city_rendered.png`): (1) la leyenda de UNA columna con ~65 roads
aplastaba el mapa hasta dejarlo diminuto (agravado por `adjustable="datalim"`, que expandía el
rango X de forma fantasma); (2) grosores de línea FIJOS en puntos → roads paralelos se solapaban
en un borrón; (3) roadlinks dibujados como cruces `X` gruesas cian que tapaban la vista.
**Solución (un solo archivo):** encuadre ajustado a los datos (`adjustable="box"` + xlim/ylim con
margen → el mapa llena el eje); **grosores proporcionales** a la extensión (`clamp(1300/span,
0.6, 3.0)`, links siempre más finos que los roads); **roadlinks = línea cian fina CONTINUA** (como
los laterales pero sólida); **leyenda multi-columna** (`ncol=ceil(n/30)`) y **ordenada
alfabéticamente**, fuente reducida; **paleta de roads que EXCLUYE** los colores semánticos
reservados (rojo=zonas, gris=laterales, cian=roadlinks); quitados los marcadores por-nodo.
Renders de `south_city` y `south_drift_1` regenerados y **validados visualmente con el usuario**.
Suite 609/609; ruff limpio. Es tooling offline (no toca runtime de conducción) → no requiere LFS.
Commit `5dd0740`. **Refinamiento posterior (a petición del usuario, commit `9a9f4eb`):** cada
columna de la leyenda baja **exactamente lo que baja el mapa** y solo entonces se abre la siguiente;
filas por columna **medidas** sobre un render de sondeo (no estimadas) y **llenado columna-a-columna
forzado** con entradas invisibles (matplotlib equilibra columnas por defecto). `south_city` → 2
columnas (la 1ª llena hasta el fondo), `south_drift_1` → 1 columna.

**S21 (2026-07-07) — Fase 5: sustitución del "PARCHE DE SEGURIDAD MATEMÁTICO" del ACC
(implementado, pendiente validación en LFS):** eliminado el parche de
`_apply_adaptive_cruise_control` (`traffic.py`) que **reescribía en silencio** los `min`/`max`
del modelo time-gap del llamador (los inflaba con constantes mágicas +2/+5 → la IA frenaba
antes/distinto de lo pedido). **Opción A** confirmada con el usuario (fix matemático localizado,
SIN tocar los `min`/`max` del llamador). Implementado: **suelo duro de parada explícito**
(`if dist ≤ 5: return 0`), `critical = max(5, min·0.5)` **con el suelo mantenido**, ratios
**acotados a [0,1]** y denominadores **blindados con ε** → imposible el ZeroDivisionError.
Números mágicos subidos a constantes con nombre (`PARADA_ABSOLUTA_M`, `CRITICAL_FRACTION`,
`ANTICREEP_KMH`, `EPSILON`). **Decisión de diseño (matiz sobre la letra de A en P25):** se mantiene
`critical = max(5, min·0.5)` en vez del `min·0.5` pelado que proponía el texto. Razón: con el
suelo la rampa naranja arranca **continua** desde 0 en el umbral rojo; sin él `critical` caería por
debajo del suelo de 5 m → **salto de velocidad discontinuo** en dist=5 m (justo donde entran los
`min≈5` reales a baja velocidad). Además así el cambio de conducta se **confina exactamente a la
franja rota** (`min<7` ∪ `max<min+5`): los 8 tests de setup limpio (min=10/20) quedan idénticos.
De paso se verificó que el div/0 que el parche decía tapar era en realidad **inalcanzable** (la
zona roja guarda el denominador naranja: naranja solo se evalúa si `critical < dist ≤ min` ⇒
`min > critical` ⇒ denom > 0) — el parche solo distorsionaba, no protegía. **Red primero:** los 2
tests del parche reescritos al comportamiento sin parche (rojo→verde: 15→34.44 y 46→50) + 2 tests
de robustez nuevos (min en el suelo y max==min no lanzan). Suite **609/609** (607 + 2). `ruff
check .` + `ruff format --check .` limpios; `lfs-insim list` OK. Los otros 2 call-sites del ACC
(overtake, intersección) se benefician igual. **PARCIALMENTE validado en LFS (S21):** el usuario
confirma que **el frenado/seguimiento funciona bien**. El **ceda el paso en intersección queda SIN
CONFIRMAR** — el usuario no tiene ninguna intersección creada todavía, así que no se ha podido
probar ese call-site. Reconfirmar cuando exista una intersección.

**S20 (2026-07-06) — Fase 5: fix de reconexión de `ai_control` (implementado, pendiente
validación en LFS):** `ai_control` ya es consciente de la reconexión (P12). Se confirmó que
había **DOS** bucles daemon con el mismo defecto (no uno): `_run_test_freeroam` y `_test`
(cargador de rutas). Ambos eran `while True` con `time.sleep` que morían con
`InSimConnectionError` al enviar desconectados e ignoraban toda señal de parada. Solución:
**señal de parada compartida** (`threading.Event` que ambos consultan vía `stop.wait(t)`),
infra en `_CommandsMixin` (`_init_traffic_state` / `_start_traffic_loop` / `_stop_traffic_loops`),
y overrides nuevos en `AIControl`: **`on_disconnect`** para los bucles limpiamente y
**`on_reconnect`** los para + resetea `_target_freeroam_count` y las cachés de radar por PLID
**sin reanudar el tráfico** (evita arrastrar el UCID viejo → "La AI X no es una de tus AI's").
De propina, la UI "Detener" ahora para de verdad (antes el flag no se miraba). Red primero:
`test_reconexion.py`, **6 tests** (rojo→verde). Suite **607/607**; ruff limpio; `lfs-insim list`
OK. **✅ VALIDADO por el usuario en LFS (S20): "todo funciona perfectamente".** Commits:
`2b2bc85` (protección del mapa South City, incidente de mitad de sesión), `047d8f1`
(`fix(ai_control): reconexión…`, código + tests) y docs de cierre.

**S19 (2026-07-06) — Fase 5: caracterización de `traffic.py`:** completada la red de
seguridad de `traffic.py` en `tests/insims/ai_control/test_traffic.py` (**81 tests**),
reutilizando los fixtures de grafo/telemetría de `conftest.py`. Congela la lógica
DETERMINISTA: el **ACC de 3 zonas** `_apply_adaptive_cruise_control` **incluido su "PARCHE
DE SEGURIDAD MATEMÁTICO"** (congelado, NO corregido — la sustitución sigue pendiente en
PLAN §Fase 5); la matemática de adelantamiento (`_estimate_overtake_distance`,
`_get_relative_dist_to_cover` —ojo: **ordena su lista de entrada in-place**—,
`_calc_path_length`, `_get_lookahead_point`); la **geometría de zonas** de intersección
(`_get_zone_centroid` / `_is_point_in_zone` / `_get_dist_to_zone_edge` /
`_is_priority_vehicle_active_at_zone`, con los 4 casos círculo/cápsula/polígono/vacío); la
**selección de carril RHT/LHT** (`_find_valid_overtake_lane`); los **helpers del FSM**
(`_trigger_return` / `_finish_overtake`); el **radar** (`_scan_lane_ahead` /
`_scan_target_lane` / `_scan_return_lane_gap`) y el **guardián de adelantamiento**
(`_get_available_overtake_distance` / `_is_lane_safe_to_overtake`). Decisión de diseño
clave: el radar se ejercita **solo con vehículos IA** (leen topología directa de
`extra['aic'].active_mode`, determinista) para EVITAR la rama de humanos, que usa
`time.time()` + `get_location_context`. El gran orquestador `_update_traffic_behavior`
queda SIN cubrir a propósito (usa `time.time()` y muta muchísimo estado del `mode`, mismo
criterio que los métodos gordos de `navigation.py`). Suite **601/601** (520 + 81); `ruff
check .` + `ruff format --check .` limpios en TODO el repo. Solo tests: **no requiere
validación en LFS**. Próximo: **fix de reconexión de `ai_control`** (ítem de S10), ya CON
LA RED PUESTA.

**S18 (2026-07-06) — reconciliación de contexto:** el `git pull` de arranque trajo, además
del cierre completo de Fases 1-4, **trabajo de Fase 5 sin documentar** (commit
`9605dc6 "mapas (ignorar)"` del otro equipo, que mezcló mapas freeroam con tests): la infra
de fixtures sin LFS (`tests/insims/ai_control/conftest.py`) y la **caracterización de
`physics.py`** (`test_physics.py`, 20 tests). **S18 completó la infra de fixtures (grafo
sintético) y caracterizó `navigation.py`** (`test_navigation.py`, 31 tests). Suite **520/520**;
`ruff check .` + `ruff format --check .` limpios (se instaló ruff 0.15.20 en `.venv`, que no
lo tenía); de paso se quitó un import muerto (F401) en `test_physics.py` que dejaba el CI en
rojo. Próximo: caracterizar `traffic.py` (ver Próximo paso).

**Fases 1, 2, 3 y 4 COMPLETADAS.** FASE 4 (DX y packaging) cerrada en S17:
metadata (S14), subcomandos del CLI (S15), ruff+CI+mypy (S16), docs de usuario
(S17), CHANGELOG + semver (S17) y **PyPI preparado sin publicar** (S17). Suite
469/469 verde; ruff limpio; mypy limpio (core vigilado); wheel construye limpio
y `twine check` pasa. Sin validaciones pendientes en LFS
(tooling/packaging/docs no tocan runtime). **Rumbo decidido al cierre de S17:
seguir con FASE 5 (`ai_control`)**; el merge a `main` + publish a PyPI esperan a
que Fase 5 esté terminada y validada en LFS (ver "Fase activa").

**PyPI preparado sin publicar (último ítem de Fase 4, hecho en S17):** decisión
del usuario = preparar sí, disparar no hasta el merge. Build local validado
(`python -m build` → sdist + wheel `py3-none-any`; `twine check` PASSED); extra
`[publish]` (build+twine) para el ensayo local; workflow
`.github/workflows/publish.yml` con **Trusted Publishing (OIDC, sin tokens)** e
**inerte** — solo `workflow_dispatch`→TestPyPI y `release: published`→PyPI, y
solo operable desde `main`, así que no publica nada por sí solo. Runbook
completo en `docs/dev/PUBLICACION.md` (ensayo local en TestPyPI, configurar
trusted publishers, publish real post-merge). El upload real —incluido el ensayo
en TestPyPI— lo lanza el usuario con sus credenciales (Claude no las tiene).

**CHANGELOG + convención semver (último ítem de contenido de Fase 4, hecho en
S17):** `CHANGELOG.md` en formato Keep a Changelog (español, coherente con el
resto de docs) + sección de convención de versionado. Historial verificado con
git: la versión ha sido `0.2.0` desde el "Starting point" (2026-04-21), **nunca
hubo 0.1.0**, sin tags ni releases → el changelog documenta la 0.2.0 como
**primera versión en preparación** (sección `[Sin publicar]`, sin fecha hasta el
release real), recogiendo todo el refactor por categorías con los cambios que
rompen la API marcados. URL de Changelog en `[project.urls]` (apunta a
`blob/main`, correcto tras el merge) + enlace en el README. Tests de packaging
verdes (23/23). No requiere validación en LFS.

**Docs de usuario (penúltimo ítem de Fase 4, hecho en S17):** nueva carpeta
`docs/guia/` con 4 guías en español, verificadas contra el código:
`quickstart.md` (primer InSim en 5 min: instalar → settings_local → `/insim` →
`lfs-insim init` → `run` → probar en el chat), `modulos-y-deps.md` (manifiesto,
dependencias con constraints de versión y fail-fast, `get_insim`, estado
compartido vía `.extra`, comandos con CMDManager, mixins), `api-publica.md`
(exports de `lfs_insim`, superficie de `InSimApp`, TODAS las claves de
`DEFAULT_CONFIG` con sus defaults reales, las 7 excepciones, los 21 nombres de
`utils`) y `arquitectura.md` (composición/lifecycle/contrato de hilos/política
de errores/auto-reconexión P12+P24 — reemplaza la sección obsoleta del README).
**README reducido a landing page + enlaces** a las guías. La plantilla de
`lfs-insim init` revisada y al día (usa la API pública y CMDManager fluido; no
hubo que tocarla). Corregidas afirmaciones FALSAS del README viejo: la sección
Arquitectura describía el patrón "coup d'état"/Master/`modules[]`/
`insim_packet_io.py`, TODO eliminado en Fase 2; decía que los stubs `.pyi` se
generan por git hook (falso, el hook es un no-op); `insim_name` default es
`LFS-InSim`, no `InSimApp`; faltaba `InSimProtocolError` en la jerarquía.
De paso corregido **CLAUDE.md**: el loader instancia la PRIMERA subclase de
`InSimApp` del entry_point (matching por herencia, no por nombre CamelCase —
por eso `AIControl` funciona pese a que el CamelCase de `ai_control` sería
`AiControl`). Solo docs; cero cambios de runtime. **No requiere validación en LFS.**

**ruff + CI + mypy (bloque grande de Fase 4, hecho en S16):** adoptado
**ruff** (lint+format, **line-length 88**, reglas conservadoras **E, F, I,
W**; decidido con el usuario). `ruff format` en commit propio (`a3bea56`, 79
archivos, cero comportamiento) con `.git-blame-ignore-revs` para que blame no
apunte al reformateo; lint (`c5a736b`) con autofix seguro + 5 fixes a mano e
ignores acotados (E501 lo posee el formatter; per-file para star-imports
intencionales, imports no-top y enums de una letra del protocolo). **CI**
(`838edac`, `.github/workflows/ci.yml`): jobs lint (ruff) y test (pytest en
matriz Python 3.9/3.11/3.13 + Windows), dispara en push/PR a main y a la rama
de refactor. **mypy gradual** (`8a64881`): vigila los ~14 módulos limpios del
core; backlog por módulo (`ignore_errors`) para packets/loader/decoders/utils;
job de CI `typecheck` con `continue-on-error` (NO bloquea). De paso, 2 errores
type-only del core que los stubs enmascaraban, corregidos (`ISF(0)`; narrowing
de `f.name`). **No requiere validación en LFS.**

**El primer run del CI cazó 2 incompatibilidades reales con Python 3.9**
(`fix(py39)`, commit `a077f41`), ya arregladas y verificadas en un Python
3.9.13 real (venv `.venv39`): union PEP 604 (`X | Y`) en anotaciones runtime
→ `Union`/`Optional` (base.py, insim.py, um_class.py); y el campo self-shadow
`HLVC: HLVC` en ISP_HLV (recursión del `repr` de dataclasses en 3.9) →
forward-ref `"HLVC"`. Guardas: regla ruff **FA102** + la matriz de CI ya
incluye 3.9. Suite 3.9: 467 passed, 2 skipped; 3.14 sigue en 469.
✅ **Pusheado (tip `e40cfec`) y CI en VERDE** — confirmado por la API de GitHub
(run de `e40cfec` = success) y reproducido en Docker (Linux 3.9.25 → 467 passed,
2 skipped). El "exit 4" que se veía en Actions era el run VIEJO (`b0d0541`,
pre-fix), no el actual.

**Subcomandos del CLI (segundo ítem de Fase 4, hecho en S15):** los antiguos
entry points `generate-stubs` y `update-all` se instalaban como comandos
GLOBALES en el PATH de quien hiciera `pip install` (nombres genéricos que
invaden el entorno ajeno) → plegados en `lfs-insim stubs` y
`lfs-insim update-all`. Dos handlers en `cli.py` (`cmd_stubs`/`cmd_update_all`,
import perezoso) que llaman a `generate_stubs.main()` / `update_all.main()` —
mismo comportamiento que los console-scripts (llamar a `main()`, devolver 0).
Los dos scripts fuera de `[project.scripts]`: **`lfs-insim` es el único
console-script**. Git hook revisado: `.githooks/pre-commit` es un no-op
deshabilitado por el usuario (NO invocaba `generate-stubs` — nada que
migrar); docs corregidas (CLAUDE/README apuntan a `lfs-insim stubs` y ya no
afirman que el hook autogenera stubs). 4 tests nuevos (`tests/test_cli.py`,
rojo primero): despacho de ambos subcomandos + contrato de que `lfs-insim`
es el único script. Verificado además a mano: reinstalación editable
(`pip install -e ".[dev]"`) **elimina los `.exe` viejos** y deja solo
`lfs-insim.exe` con los subcomandos. Suite 469/469. **No requiere validación
en LFS.**

**Metadata del paquete (primer ítem de Fase 4, hecho en S14):**
`readme = "README.md"` (antes apuntaba a un `README` inexistente); licencia
SPDX `license = "MIT"` + `license-files` (build-system sube a
setuptools>=77); **fuente única de versión** en `lfs_insim.__version__`
(pyproject `dynamic = ["version"]`; contrato fijado con test contra la
metadata instalada — si falla tras un bump, reinstalar editable);
`requirements.txt` eliminado; URLs corregidas (Homepage apuntaba al repo
antiguo `Aprendiendo-InSim-LFS`); descripción en inglés + keywords +
classifiers (Python 3.9–3.14). 2 tests nuevos (rojo primero,
`TestVersionUnica`); wheel construye limpio en aislamiento
(`pip wheel . --no-deps`).

**`tick_interval` (cierre de Fase 3, hecho en S13):** la cadencia de
`on_tick` es configurable (segundos, default 0.1 = comportamiento
histórico; mínimo 0.01, valor inválido → `InSimConfigurationError` al
crear el cliente). Clave del diseño: el tick queda DESACOPLADO del sondeo
interno del bucle principal, que sigue fijo a ≤100 ms para
`_connection_lost` y `_handler_error` — un tick lento nunca retrasa la
reconexión (P12) ni el fail-fast. Sin catch-up tras un stall. No es un
timer de precisión; alta frecuencia → handlers MCI/OutSim. 5 tests
(`TestTickInterval`), rojo primero.

**Política de errores de handlers (último ítem de Fase 3, hecho en S13):**
clave `handler_errors` en `DEFAULT_CONFIG` — `'log'` (default) aísla y
loguea con traceback como siempre; `'raise'` (fail-fast, desarrollo) hace
que el primer error de un handler `on_ISP_*` o hook de lifecycle detenga el
cliente: el worker aparca la excepción en `_handler_error` y sale, y el
bucle principal de `start()` la re-lanza con el traceback original.
Excepción deliberada: los `on_disconnect` de `stop()` se aíslan SIEMPRE
(el apagado se completa y todas las apps se enteran). Valor inválido →
`InSimConfigurationError` al crear el cliente. De propina: los errores de
lifecycle en modo 'log' ahora llevan `exc_info=True`. 8 tests nuevos (rojo
primero), incluida integración con FakeLFS. No requiere validación en LFS
(el default no cambia nada). Documentado en CLAUDE.md § Handler error policy.

**Pista de diagnóstico de ISI rechazado (hecho al cierre de S12):** LFS no
da feedback en el socket al rechazar un ISI — solo cierra. El cliente marca
la sesión como "hablada" al primer byte recibido (`_session_received_data`,
reseteado antes de cada ISI) y, si una sesión muere antes de
`reconnect_stable_time` sin haber recibido NADA, `_handle_connection_lost`
loguea la pista ("ISI likely rejected — check admin_pass / InSim version").
El fallback de leer `Game Admin` desde cfg.txt quedó SOLO como idea a
futuro (PLAN § Ideas + comentario en `config/settings.py`). Commit `3f2e2b3`.

**P24 (tormenta de reconexión, hecho en S12 — incidente EN VIVO):** al
intentar conectar desde el dispositivo nuevo, LFS rechazaba el ISI
(`Game Admin abc` en cfg.txt vs `admin_pass: ''` del settings_local recién
copiado del example) y `_reconnect`, que da por buena una reconexión con
solo enviar el ISI, reseteaba el backoff en cada ciclo → ~10 conexiones/s
durante 25 s hasta el "InSim - TCP excess : 127.0.0.1" de LFS. Diagnóstico
confirmado con sondas ISI contra el LFS vivo (0.8C17). Fix: reconexión
**provisional** — si la sesión muere antes de `reconnect_stable_time`
(config nueva, 10 s), el siguiente ciclo retoma la racha (espera previa +
escalado + cuenta para `max_attempts`). El settings_local de este equipo ya
lleva la password. Detalles en DIAGNOSTICO § P24. Commit `759f224`.

**Apagado limpio (ítem de Fase 3, hecho en S12):** resuelta la carrera de
`InSimTransport.close()` detectada en S11 — cada bucle receptor **captura su
evento de stop al arrancar** y `close()` lo deja puesto y lo **REEMPLAZA**
por uno nuevo (nunca `clear()`), además de esperar (join, timeout 2 s) a los
receptores antes de volver. Un receptor que despierte tarde por el socket
cerrado ya no puede disparar `on_connection_lost` espurio tras un cierre
deliberado; `close()` es seguro incluso desde el propio hilo receptor y el
transporte sigue siendo reutilizable. De propina: `InSimClient.stop()` con
check-and-set atómico de `running` (lock solo en el flip del flag) — stops
concurrentes ejecutan el apagado UNA vez y la reentrada desde `on_disconnect`
no se bloquea. La carrera se reprodujo EN ROJO antes del fix (2 tests);
5 tests nuevos en total. Commit `7ee9f38`.

**P18 (envío UDP, hecho en S11):** eliminado el parámetro `use_udp` de
`transport.send` — el envío es **siempre TCP** (LFS solo recibe InSim por TCP;
el socket UDP es solo de bajada: OutSim/OutGauge, NLP/MCI). Documentado en el
docstring del transporte y CLAUDE.md; contrato fijado con test. Commit `844feed`.

**P19 (una sola ruta de serialización, hecho en S11):**
`validate_string_lengths()` (prepare) es la única autoridad del layout de
strings — gana el truncado de los fijos `'Ns'` a N-1 (null final garantizado;
antes vivía en `_extract_values`); `_extract_values()` ya solo codifica a
latin-1 y `struct.pack` rellena los fijos. El decoder ya **no hace `.strip()`**
(corta en el primer null; los espacios significativos se conservan). Dos
cambios deliberados de comportamiento reflejados en los goldens: string fijo
con `len == N` pierde 1 char por el null (antes salía SIN terminador, contra
la spec) y los strings decodificados conservan espacios previos al null.
**Validado por el usuario en LFS (cierre de S11):** pasada normal OK — nada
dependía de los strings recortados del decoder. Commit `720315a`.

**Validación de P2-core en LFS (S10):** el usuario probó conexión + AIs rodando,
cierre abrupto del juego, reapertura del puerto y arranque con el juego cerrado.
El framework se comportó bien en todo (detección de caída en 33–40 ms, backoff,
restauración de sesión, keep-alive bajo tráfico, Ctrl+C limpio en pleno backoff).
Los comportamientos "raros" eran de `ai_control` (no es consciente de la
reconexión: su hilo `_run_test_freeroam` muere al enviar desconectado o enloquece
tras la limpieza de memoria) → apuntado como ítem de Fase 5. Del análisis del log
salieron y se arreglaron en S10: **P22** (orden de `_restore_session` invertido:
ISI → on_reconnect → TINY.NCN/NPL, con test del orden causal) y **P23**
(QuickEdit de la consola Windows congelaba el proceso entero sin dejar traza:
ahora el handler `file` va antes que `console`, `lfs-insim run` desactiva
QuickEdit al arrancar, y el bucle de reconexión deja traza si se abandona).

**P2-core (dispatch fuera del hilo de IO, hecho en S09):** los hilos de IO del
transporte ya NO ejecutan handlers — decodifican, contestan el keep-alive en el
acto (para que una cola ocupada nunca retrase el ping a LFS) y encolan; un
**worker dedicado** (`InSim_Dispatch_Worker`, arrancado en `start()`) despacha
`on_ISP_*` en orden FIFO estricto. Un handler lento ya no bloquea la recepción.
`stop()` cierra el transporte y mete un centinela al FINAL de la cola: lo
pendiente se despacha antes de que el worker salga (join con timeout 2 s,
protegido contra `stop()` llamado desde un handler). `use_thread_pool` y
`max_workers` RETIRADOS de config y cliente (orden no garantizado, sin usuarios).
Contrato de threading documentado (CLAUDE.md + docstring de `insim_client.py`):
handlers en el worker (FIFO); hooks de ciclo de vida en el hilo principal; sin
garantía de orden entre ambos; `send()` thread-safe. `insim_client.pyi`
reescrito (estaba desfasado desde Fase 2). Detectado de paso **P22** (carrera
menor en `_restore_session`, ver DIAGNOSTICO).

**P12 (reconexión, hecho en S08):** el transporte avisa con `on_connection_lost`
cuando el bucle receptor TCP muere sin `close()`; el bucle principal de `start()`
(el que antes quedaba zombie) detecta el evento en ≤100 ms, despacha `on_disconnect`
(desde el hilo principal, como on_connect/on_tick), reintenta con backoff exponencial
(claves `reconnect*` en `DEFAULT_CONFIG`: delay 1 s, factor 2, tope 30 s,
`max_attempts 0` = infinito), reenvía el ISI agregado, re-solicita `TINY.NCN/NPL`
y despacha `on_reconnect` (hook nuevo en cliente y apps). `reconnect: False` o
intentos agotados → `stop()` limpio. `users_management.on_reconnect` limpia su
memoria (los NCN/NPL entrantes la repueblan). `on_tick` se pausa mientras reconecta.

**Migración de insims (hecha en S08):** `ai_control` ya no importa la facade
deprecada — los 10 imports de `insim_packet_class` (9 archivos) pasaron a
`lfs_insim.packets` (ISP_*, `AIInputVal`) y `lfs_insim.insim_enums` (CS, CSVAL,
SND). `users_management` ya estaba migrado (usa `packets`/`insim_enums` directos;
sus enums llegan vía `um_class.py`). Smoke: los 4 insims cargan con
DeprecationWarning-como-error (nadie importa la facade); `lfs-insim list` OK.
Commit `0292a01`.

**P15 (API pública, hecho en S07):** `__all__` en todos los módulos públicos
(`lfs_insim`, `packets/*`, `insim_enums`, `utils`, `exceptions`, `config`). Puntos de
import recomendados: `lfs_insim` (core+config+excepciones), `lfs_insim.packets`
(paquetes; **ya no re-exporta enums**), `lfs_insim.insim_enums`, `lfs_insim.utils`.
`insim_packet_class` queda como facade **deprecada** (DeprecationWarning) que
re-exporta packets+enums como el monolito original — el core ya no la usa;
`ai_control` sí (migración pendiente). El único `import *` interno que contaminaba
(`packets/insim.py` ← enums) es ahora import explícito.

**P20 (fail-fast del loader, hecho en S07):** una dependencia rota aborta la carga
del dependiente con la cadena completa en el mensaje (antes se tragaba y `get_insim`
devolvía `None` mucho después). **P17:** `class INST` duplicada eliminada de
`insim_enums.py`; comentario falso de CLAUDE.md corregido (los constraints de versión
SÍ se aplican). Decisión de si `on_tick` debe ser configurable → Fase 3.

**P14 (config del paquete, hecho en S07):** defaults internos en
`src/lfs_insim/config.py` (`DEFAULT_CONFIG` + `build_config(overrides)`, dict plano).
El core no importa `config.settings` del CWD; el CLI carga la config del proyecto
(`_load_project_config()`) y el loader la propaga (las apps heredan la config
efectiva del cliente).

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

**Validación en LFS (S08):** el usuario probó el estado post-migración (Fase 2
cerrada) y también P12 — la reconexión funcionó al matar/levantar LFS con el
InSim corriendo. **P2-core validado en S10** (ver "Estado").

**Contexto del plan (S04):** framework a nivel profesional; romper insims aceptable.
P11–P21 en `DIAGNOSTICO.md`. Queda gordo: P12 (reconexión, Fase 3).

## Fase activa

**Fase 6 — Pre-publish: refactor de ai_control + API + init** (re-secuenciada con el usuario en
S23). Fases 1-4 (core) COMPLETADAS. **Fase 5 (ai_control: red + estabilización) COMPLETA salvo la
validación en LFS del ceda-el-paso del ACC (W4)**, hoy bloqueada porque ningún mapa tiene
intersección (`zones: 0`). **Fase 6: W1 (split `utils.py`), W5 (sweep de API) y W2 (`init` con
perfiles) HECHOS** (S24/S25/S26); **falta W3** (refactor interno + radar).

**Decisión de rumbo (S23):** adelantar el refactor de ai_control a **ANTES de publicar**, junto
con la limpieza de la API pública (`utils.py`) y un `init` más robusto. Motivo clave: mover
funciones de `lfs_insim.utils` cambia la **API PÚBLICA** del paquete → la única ventana limpia es
antes del primer publish (después rompería usuarios reales). El radar (ex-6b) se **pliega** en el
refactor de `traffic.py` (no urgente por la auditoría, y traffic.py se toca igual). Se separa
SIEMPRE lo que toca API pública (pre-publish obligatorio) de lo interno/cosmético (flexible), para
no dejar que el scope creep retrase el release. **Todo en la rama**; un solo merge a `main` cuando
esté publish-ready + validado, luego publish. Ver PLAN § Fase 6 y § Merge.

**Esto sustituye la decisión de S17** (que mergeaba tras Fase 5 y dejaba Fase 6 para después del
merge). `ai_control` es la insim de ejemplo **sobre** el framework (el escaparate); se pule antes
de publicar para un primer release cohesionado y con la API pública ya estable.

## ▶️ Próximo paso concreto (empezar AQUÍ la próxima sesión)

**Rumbo re-decidido en S23 (planificación con el usuario): Fase 6 pre-publish** — refactor de
ai_control + limpieza de la API pública (`utils.py`) + `init` más robusto. Fase 5 está COMPLETA
salvo **W4** (validación en LFS del ceda-el-paso del ACC, hoy bloqueada por `zones: 0`). Orden
acordado: **W4** (tú, en LFS, en paralelo — gate del merge) → ~~W1~~ ✅ → ~~W5~~ ✅ → ~~W2~~ ✅
(init) → **W3** (refactor interno + radar). Todo en la rama; un solo merge a `main` cuando esté
publish-ready + validado, luego publish. Detalle en PLAN § Fase 6.

**✅ W1 HECHO (S24)** — split de `utils.py`: las 9 funciones de geometría/nav de la IA movidas a
`ai_control/nav_modes/freeroam/geometry.py`; en el framework quedan comandos, colores,
`PIDController`, conversiones `lfs_*` y `calc_dist_3d`. Red `test_geometry.py` (44 tests, red
primero). Suite 671. Hecha también la parte de W5 ligada a W1 (guía `api-publica.md` + entrada
`[Rompe la API]` en `CHANGELOG.md`).

**✅ W5 HECHO (S25)** — sweep de API pública: exports de `lfs_insim` y `DEFAULT_CONFIG` (20 claves)
confirmados sin cambios; jerarquía de excepciones **recortada** — quitada `InSimProtocolError` (el
framework no puede detectarla, P24; solapa con `InSimPacketError`; nunca se lanzaba), mantenida
`InSimCommandError` (tipo de error del sistema de comandos, para módulos). `exceptions.py` traducido
a inglés (MODUS_OPERANDI §5). Guía `api-publica.md` + `CHANGELOG.md` cuadrados. Suite 670.

**✅ W2 HECHO (S26)** — `lfs-insim init` con perfiles. Confirmado con el usuario: **cierre =
`self.client.stop()`** (`TINY.CLOSE` con reconexión P12 activa solo reconectaría) y **`--full` por
defecto**. `cli.py`: flags mutuamente excluyentes `--full`/`--minimal` + registro extensible
`_INIT_PROFILES` (perfil→render); templates como strings con centinelas + `str.replace`. `--minimal`
= template de antes (byte-idéntico); `--full` = bot real (cierre admin-guarded con `client.stop()`,
`_is_admin` + tracking de admin por NCN, `on_reconnect`, `TINY.NCN/NPL`). Red `test_cli.py` (+10
tests, incl. ambos templates `compile`+`exec`→`InSimApp`). Suite 680; ruff limpio; guías/README/
CLAUDE/CHANGELOG cuadrados.

**Empezar AQUÍ la próxima sesión — W3 (refactor interno + radar), último ítem de Fase 6:**

1. **W3 (resto de Fase 6):**
   - **W3** — refactor interno (P3 partir `map_ui`/`map_recorder`/`traffic`; P4 `base.py`; P7
     nombres de `behavior.py`) + índice espacial de VEHÍCULOS para el radar **plegado en
     `traffic.py`** (caracterizar el radar como unidad ANTES; reutiliza el `SpatialHashGrid` de
     S23, grid dinámico aparte) + revisar el FSM de adelantamiento (`overtake_state`).
2. Backlog de **tipado gradual** (ir quitando overrides de `[tool.mypy]` en
   pyproject, módulo a módulo, cuando se toque cada uno): los módulos
   `packets` (dataclasses de protocolo), `insim_loader` (fricción con
   `importlib`: `ModuleSpec | None` sin None-check + kwargs inyectados en
   InSimApp — merece None-checks reales, no `type: ignore`), y
   `insim_packet_decoders`/`utils` (2 errores puntuales cada uno). No urge;
   mypy no bloquea.
3. Idea DX de Fase 4 ya apuntada: el connect inicial fallido imprime un
   traceback feo (`exc_info=True` + re-raise) — valorar mensaje limpio y/o
   `connect_retry` para arrancar el insim antes que LFS. (La pista de ISI
   rechazado ya está hecha; el fallback de cfg.txt está en PLAN § Ideas.)

## Bloqueos / esperando

- **PyPI: decidido y PREPARADO (S17), publish real pendiente del merge.** El
  usuario eligió "preparar sí, disparar no". Ya hecho: build validado, extra
  `[publish]`, workflow inerte con Trusted Publishing, runbook
  `docs/dev/PUBLICACION.md`. El nombre `lfs-insim` está LIBRE (S14). Queda, cuando
  el usuario quiera: (1) opcional, **ensayo en TestPyPI** en local (lo lanza el
  usuario con su token); (2) tras el merge a `main`, el **publish real** creando
  un GitHub Release. Acción pública e irreversible (versión liberada no se
  reutiliza, nombre reclamado): por eso va después del merge.
- **Rumbo: RE-DECIDIDO (S23).** El refactor de ai_control + limpieza de API (`utils.py`) + init
  robusto se hacen **antes** del merge/publish (Fase 6 re-secuenciada; ver Fase activa y PLAN).
  Todo en la rama; un solo merge a `main` cuando esté publish-ready + validado, luego publish. No
  es un bloqueo: es el plan de trabajo.
- **W4 (validación en LFS del ceda-el-paso del ACC, S21): BLOQUEADA.** Necesita una **intersección**
  creada y ningún mapa tiene (`zones: 0`, incluido el South City ampliado). Es el gate del merge:
  cuando el usuario cree una intersección y valide el ceda-el-paso (+ smoke test), se desbloquea.

## Notas para la próxima sesión

- Comando de tests: `.venv\Scripts\python.exe -m pytest -q`.
- **Tests en Python 3.9** (mínimo soportado; el CI y S16 cazaron bugs solo-3.9): **según
  equipo** — donde exista `.venv39` (Python 3.9.13, gitignorado): `$env:MPLBACKEND='Agg';
  .venv39\Scripts\python.exe -m pytest -q` (2 skips esperados: `tomllib` es 3.11+). **En este
  equipo NO hay `.venv39`** → verificar 3.9 vía CI con `gh` (instalado y autenticado aquí, S23):
  `gh run list --branch refactor/estabilizacion` / `gh run view <id>`.
- Tooling nuevo (S16): `python -m ruff check` y `python -m ruff format` (lint+format),
  `python -m mypy` (tipos del core; lee `[tool.mypy]` de pyproject). Config toda en
  `pyproject.toml`. El commit de formato masivo (`a3bea56`) está en
  `.git-blame-ignore-revs`; para que `git blame` local lo salte:
  `git config blame.ignoreRevsFile .git-blame-ignore-revs`.
- Idioma (decisión S06): código nuevo del core en **inglés**; docs/dev, tests e insims
  en español. Ver `MODUS_OPERANDI.md` § 5.
- Los golden-bytes y tests de packet_io de Fase 1 siguen válidos; los de loader y
  dispatch ya están adaptados a la nueva API (registro en cliente).
- En otro dispositivo: copiar `config/settings_local.example.py` → `settings_local.py`
  y `pip install -e ".[dev]"`.
- Pendientes sin fase: P8, P9, migración de rutas a JSON (ver `PLAN.md` § Ideas).
