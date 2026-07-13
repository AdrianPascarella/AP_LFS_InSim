# 📜 Historial de sesiones

> Bitácora append-only. Una entrada por sesión, la más reciente arriba.
> Formato: fecha, qué se hizo, decisiones, commits.

---

## S35 — 2026-07-13 — Validación en LFS: 3 bugs del radar con HUMANOS (stop-and-go) + nueva ley de seguimiento del ACC + semilla de la Fase 8

**Contexto:** continuación de S34. El usuario probó en LFS y reportó que la IA iba **"a saltos: ahora sí, o
no... aún no era"**, llegando a **pararse del todo y rearrancar**, en los TRES escenarios (recta, cruce y
ceda-el-paso) — siempre que hubiera alguien delante. Dato clave que dio al preguntarle: **solo lo había probado
con él mismo delante (un humano), no con otras IAs.**

**Método (lo que evitó tres arreglos equivocados).** Se midió antes de tocar. (1) Primera hipótesis —el ACC
oscila por sus umbrales dependientes de la propia velocidad— **REFUTADA**: simulando el lazo cerrado con el ACC
real, la velocidad pedida converge suave. (2) Segunda —a los humanos se les asigna un LatLink— **refutada para el
eje del carril** (0/5848 nodos del South City real). Solo entonces, leyendo el código con lupa, apareció la causa
real. Moraleja registrada: en este dominio, **medir antes de arreglar**.

**Bug 1 — se comparaban dos índices que NO significan lo mismo (commit `d6785a4`).** `_scan_lane_ahead` decide
"delante o detrás" con `idx_diff = other_node_index - mode.node_index`. Pero `mode.node_index` es el nodo
**OBJETIVO** de la IA, y `evaluate_dynamic_capture` lo adelanta al siguiente hasta `2.5 + v·0.3` m **antes** de
llegar (5 m a 30 km/h) → va sistemáticamente un nodo por delante de su posición. A otra **IA** se le lee su
`node_index` (misma regla → comparables), pero a un **HUMANO**, que no publica topología, se le asigna el nodo
**MÁS CERCANO**. Comparar "cercano" contra "objetivo" da `idx_diff = -1` a un humano que va físicamente
**delante** → se le toma por un coche de detrás y **se le pierde**. **Reproducido** en un test que camina 200
pasos con el humano 7 m por delante, manteniendo el índice con la MISMA secuencia que `navigation.py`
(antilag + captura): **60 de 200 pasos ciego**, en una ventana **periódica de ~3 m por cada nodo** (a 30 km/h:
~0,35 s de ceguera cada ~1,2 s). En el hueco la IA no ve a nadie → `velocidad_base` → gas; al recuperarlo → ACC →
freno. **Y con `speed_request = 0` la física aparca el coche** (freno de mano + motor OFF) → el tirón al
rearrancar. **Fix:** cada vehículo se compara contra MI índice medido con **su misma regla** (nuevo
`_my_closest_node_index`). Sin fudge factors.

**Bug 2 — la caché de humanos es COMPARTIDA por todas las IAs (mismo commit).** Guardaba el índice de nodo, que
solo vale para la geometría de **quien escaneó**. Una IA que iba por otra vía dejaba ahí un `-1`, y la IA que iba
justo detrás del humano lo leía como "va detrás" → lo perdía durante toda la ventana de caché (0,1 s). **Fix:** la
caché guarda solo la **vía** (independiente del escáner); el índice se calcula por escáner y solo para humanos que
van en su misma vía (un puñado) → coste despreciable.

**Bug 3 — a los humanos se les asignaba un LatLink como si fuera su vía (commit `87a1142`).** La fórmula del
radar dejaba que **cualquier** enlace más cercano desbancase a la vía. Pero un LatLink es la tira que **une** dos
carriles: nadie circula por ella, y como se graban conduciendo pegado al carril, corren casi **paralelos**.
**Medido sobre el South City real** (humano desplazado lateralmente dentro de su carril): a **1 m del eje** —o
sea, conduciendo normal— el **4,9%** de los puntos le asignaba un LatLink → invisible. **Hallazgo decisivo:**
`navigation.py:361` **ya lo hacía bien** (`... and ctx.link_type == "RoadLink"`) para localizar a la propia IA;
las **dos copias del radar se habían dejado la comprobación del tipo** → no es un cambio de diseño, es alinear el
radar con la regla canónica. Con el fix, la ceguera a 1 m baja a **0,5%** (lo que queda a 2-3 m es ambigüedad
física real: ir a caballo entre dos carriles). En `_scan_target_lane` el agujero era **peor**: es el escáner que
decide si el carril está libre para adelantar → un humano descentrado ahí era invisible y **la IA se le echaba
encima**.

**✅ VALIDADO en LFS por el usuario: "Desaparecieron todos los tirones. En todo lo que antes daba tirones ya no
los da".** Los 3 bugs eran **viejos** (nada que ver con el fix (3) de S34) y **solo afectaban a los humanos** —
por eso el tráfico IA-IA se veía bien y nunca se cazaron.

**Nueva ley de seguimiento del ACC (commit `35870bb`), a petición del usuario.** Pidió dos cosas: **(a)** hueco
mínimo entre coches un poco más grande y **(b)** que al ir bloqueado la IA **iguale** la velocidad del de delante
**en vez de reducirla** ("si no, terminan oscilando"). (a) → dos diales con nombre: `PARADA_ABSOLUTA_M` 5→**7 m**
(suelo duro) y `MIN_GAP_FLOOR_M` 5→**8 m** (suelo de la distancia de seguridad cuando el time-gap se queda corto:
marcha lenta y colas). El time-gap a velocidad (2 s) no se toca. (b) **obligaba a cambiar la FORMA de la ley, no
un número**: si la banda de seguimiento iguala, la vieja zona roja (que salta a 0 de golpe) queda debajo como un
**acantilado** y la IA volvería a oscilar ahí. Así que la rampa de frenado **baja a una franja de EMERGENCIA**
(por debajo de `critical`, que es donde reducir sí es legítimo) y la banda de seguimiento pasa a ser **igualación
pura**. La ley queda **CONTINUA en los tres bordes** (los escalones son justo lo que excita la oscilación).
**Verificado en lazo cerrado** con el ACC real (offline): siguiendo a 10/20 km/h y detrás de un coche parado
converge a un **punto fijo** — iguala exactamente la velocidad y el hueco se estabiliza (8 m en marcha lenta,
11,1 m a 20 km/h = time-gap). La caracterización del ACC (S19/S21) se **reescribió** a la ley nueva: es un cambio
de comportamiento **deliberado**. ⏳ Pendiente de validar en LFS.

**Incidencia (y su reparación, commit `cb9c3b3`).** Un `Get-Content | Set-Content -Encoding utf8` en PowerShell
5.1 leyó `test_traffic.py` como ANSI y lo reescribió **doble-codificado**: todos los acentos de los comentarios
quedaron en mojibake, y se coló en dos commits. Reparado y **verificado contra la última versión limpia** (el diff
de todo lo preexistente vuelve a ser cero). **Regla para el futuro: no usar `Get-Content | Set-Content` sobre
fuentes; editar con las herramientas de edición.**

**Rendimiento (falsa alarma que casi acaba mal).** La suite pasó de 43 s a 100 s → sospecha de regresión en el
hot-loop. Antes de matar los procesos "huérfanos" se comprobó qué eran: **eran el InSim del propio usuario**
(`lfs-insim run ai_control`, quemando un núcleo mientras probaba en LFS). No había regresión. **Además aparecían
DOS instancias** — si de verdad son dos clientes conectados, ambos mandarían órdenes a los mismos coches; avisado
al usuario.

**Cierre.** Suite **773/773**; ruff limpio; rama en sync. El usuario probó las **intersecciones**: *"funcionan,
pero son difíciles de crear y su funcionamiento es regular"*, y trae un **diseño propio** para rehacerlas →
**Fase 8 (nueva)** con la semilla de diseño y las preguntas abiertas. Se decidió **cerrar aquí** y arrancar el
rediseño en sesión nueva (falta que explique la parte de UI, toca el modelo de datos, y conviene hacerlo con el
feedback de LFS del ACC ya en la mano). Commits: `d6785a4`, `87a1142`, `cb9c3b3`, `35870bb` + docs.

---

## S34 — 2026-07-13 — Fase 7: fix (3) el radar pierde coches en la transición road↔roadlink → **FASE 7 COMPLETA (código)**

**Arranque:** protocolo de inicio. Ya en `refactor/estabilizacion`, árbol limpio (nada de mapas que proteger);
el `git pull` trajo TODO S33 desde el otro equipo (fixes (4)/(1)/(5), editor de prioridad de zonas, la primera
intersección `test1`). Handoff de S33: dos frentes — (A) validar en LFS lo acumulado (W4 ya desbloqueada) o
(B) implementar el fix (3), el último bug de conducción. **El usuario eligió (B)** (recomendado: es lo único
que se puede avanzar offline; la validación la hace él cuando juegue, y así llega a esa sesión con TODO junto).

**Diagnóstico (rastreado en el código, no en la descripción del bug).** `radar.py::_scan_lane_ahead` solo
aceptaba coches cuyo `current_id` fuera el nuestro (`same_segment`), con UNA excepción: `in_our_next_link`
(yendo por un Road, ve a los que ya entraron en su próximo RoadLink). La causa raíz de los dos choques es que
**la topología de la IA cambia ANTES que su posición**: `navigation.py:551` la mete en el RoadLink en cuanto
está a `TRIGGER_DIST_M` (**3,5 m**) de él, mucho antes de separarse físicamente de la vía. De ahí:
**(a)** dentro del enlace dejaba de ver al coche lento que aún tenía delante en la **vía que deja** (si se podía
seguir de frente, lo chocaba); **(b)** no veía a los que ya circulaban en la **vía de destino**.

**Fix — la cadena topológica del cruce (commit `3a628c3`).** `_lane_chain_ids` (función pura) ensancha
"mi carril, delante" a la cadena **`from_road → link → to_road`**, acotada por una **ventana de transición**
medida al **nodo de entrada** del enlace (`_LINK_TRANSITION_WINDOW_M = 25 m`, ajustable):
- **En un Road:** el próximo RoadLink **siempre** (= el `in_our_next_link` de antes, byte-equivalente) y, **solo
  dentro de la ventana**, su **vía de destino** → frena a tiempo por una cola al otro lado del cruce, en vez de
  descubrirla al meterse ya en él.
- **Dentro de un RoadLink:** la **vía de destino siempre** (estamos comprometidos: es nuestro carril) y, **solo
  dentro de la ventana**, la **vía que dejamos**.

**Por qué la ventana (decisión de diseño):** sin ella, con el lookahead real (`max(15, v·10)` ≈ **83 m a 30 km/h**)
la IA frenaría por coches de una **vía transversal** lejana que nunca va a seguir → **frenado fantasma en cada
cruce**, justo lo que el usuario está probando ahora con las intersecciones. Fuera de la ventana el match vuelve
a ser **estricto** (como antes). Los de la cadena se filtran por **producto escalar** (que estén delante), igual
que hacía `in_our_next_link`; su `node_index` NO es comparable (geometrías distintas).

**Guard: no adelantar dentro de un cruce (commit `8af862d`, decidido con el usuario).** Efecto secundario cazado
ANTES de tocar nada: `_scan_lane_ahead` no alimenta solo al ACC, también al **gatillo `IDLE→EVALUATING`** del FSM
(`orchestrator.py`), que **no comprobaba `current_type`**. Con más coches detectados, la IA se dispararía a
adelantar **dentro del enlace**, donde `_find_valid_overtake_lane` busca carril en los laterales de la vía que ya
dejó y con el `node_index` del enlace aplicado a los nodos del road (índice de **otra geometría**) → el fix pasaría
de evitar un choque a provocar una maniobra absurda. **Opción elegida (pregunta con recomendación, MODUS §6):**
guard = el adelantamiento **solo se ABRE en un Road**; dentro de un enlace se frena por el coche (ACC intacto) y
punto. Uno **ya en curso** no se toca (lo cierran sus estados del FSM). **Commit aparte a propósito**, para poder
revertirlo solo si en LFS resulta demasiado conservador.

**Red primero (MODUS §3) — 18 tests.** (1) Unitarios de los helpers puros (`_is_near_link_entry`,
`_lane_chain_ids`: 8). (2) Integración por `_scan_lane_ahead` (6): los **dos choques reportados**, el de detrás,
los **dos bordes de la ventana** (dentro detecta / fuera no → congela el "no frenar fantasma"). (3) **Red de
equivalencia del radar de S28 EXTENDIDA** al escáner **dentro de un RoadLink** (fuzz rejilla vs. barrido lineal,
40 semillas): la cadena admite muchos más candidatos → había que volver a demostrar que la **rejilla no pierde
ninguno**. (4) **Primera red sobre `_update_traffic_behavior`** (2): el orquestador se había dejado sin cubrir por
usar `time.time()`, pero en el gatillo el tiempo solo entra en comparaciones de cooldown con 0.0 → es determinista.
**Verificación en ROJO contra el comportamiento viejo** (no vale con que pase en verde): los 2 choques se
reproducen, el guard `non_empty ≥ 5` del fuzz cae a **0** (prueba de que el fuzz no es vacuo) y sin el guard el FSM
sale en `EVALUATING` dentro del enlace. Los que pasaban en rojo son justo los "**no** debe detectar" → la ventana
no rompe nada.

**De paso:** el docstring de `radar.py` decía que el índice espacial "aterrizará" aquí; llegó en S28.

**Verificación:** suite **767/767** (749 + 18); `ruff check .` + `format --check .` limpios (106 ficheros);
`lfs-insim list` OK (4 insims). Solo lógica del insim de ejemplo → **no toca la API pública**. Como es **conducta**,
⏳ **requiere validación en LFS**.

**Estado:** con esto la **Fase 7 queda COMPLETA en código** (5/5 fixes). Todo el trabajo restante del proyecto es
**validación en LFS** (W4 + los 5 fixes) → es el gate del merge. Commits: `3a628c3` (radar) + `8af862d` (guard).

---

## S33 — 2026-07-12 — Fase 7: fix (4) `is_closed` + fix (1) flip de enlace (red primero; ⏳ validar en LFS)

**Arranque:** protocolo de inicio. Ya en `refactor/estabilizacion`; `git pull` al día; árbol limpio (sin
mapas sin commitear que proteger). Próximo paso del handoff de S32: implementar los 3 bugs de conducción
freeroam de la Fase 7, offline y **red primero**, por impacto: (4) → (1) → (3). Se abordaron **(4) y (1)**;
**(3) queda para sesión nueva** (decisión con el usuario: es el más pesado, rinde mejor con contexto fresco).

**Fix (4) — no adelantar por vía cerrada (`is_closed`). Commit `d968abf`.** Auditoría de consumidores de
`is_closed`: el único hueco de **conducción** era `traffic/overtake.py::_find_valid_overtake_lane`, que NO
comprobaba `is_closed` → la IA podía meterse en un carril cerrado para adelantar. El resto ya estaba bien:
`_calculate_next_link` (Filtro A) y spawn/`get_location_context` filtran vía `ignore_closed_roads`; los 3
call-sites del radar **NO** filtran a propósito (deben *ver* coches en vías cerradas); la UI del editor
tampoco (correcto). **Fix:** helper centralizado `MapRecorder.is_road_usable(road_id)` (existe ∧ no cerrada),
aplicado en el hueco de overtake y en Filtro A (refactor **sin cambio de conducta**, cubierto por
`test_destino_cerrado_se_descarta`). **Red primero:** `test_carril_vecino_cerrado_no_se_usa` (rojo→verde;
hoy devolvía `('R2','R1<<>>R2')`, el carril cerrado). Suite 734/734.

**Fix (1) — `next_link` pegajoso (flip de intermitente en salidas juntas). Commit `1a8eaac`.**
**Diagnóstico:** conduciendo por `s2` hacia dos salidas RoadLink muy juntas, la IA comprometía `next_link`
a `_b` (intermitente encendido) y en el último momento saltaba a `_a`. Causa: al llegar al final de la vía
sin cruzar su enlace (`fin_de_geometria`, `navigation.py:669-672`), un re-plan **en la misma vía** re-tiraba
`random.choice` en `_calculate_next_link` → podía elegir la otra salida. La **asimetría** es geométrica
(`_is_link_reachable_ahead` evaluado desde el último segmento ve un enlace u otro según el sentido/orden de
nodos), **no** RHT/LHT: el intermitente de RoadLink sale de `link.indicators`, no de `_get_indicator_to_use`
(ese gobierna LatLinks) → la pista RHT/LHT del PLAN era un falso rastro para este caso.
**Decisión de diseño (pregunta con recomendación, MODUS §6):** el usuario eligió **"pegajosa-si-válida"**
(A) frente a "commit-on-blinker" (B): nuevo `_choose_link` conserva el enlace ya comprometido **solo si
sigue siendo una opción válida** (no re-tira el dado); si dejó de serlo, re-planifica como antes → solo
puede reducir flips espurios, **nunca deja sin salida** (B congelaría aun no siendo alcanzable → riesgo de
quedar mal encarada). `_plan_next_link` pasa `mode.next_link_id` como `committed_link_id` en el re-plan de
misma vía (rama `else`); el cruce de enlace (vía nueva) NO lo pasa (re-plan fresco). **Red primero:** 2
tests de pegajosidad en `_calculate_next_link` + 1 de wiring en `_plan_next_link` (el de wiring mostraba el
flip `R1->R2 ⇒ R1->R3`; rojo→verde). Suite 737/737.

**Verificación (fixes 4 y 1):** suite **737/737** (733 +1 +3); `ruff check` + `format --check` limpios en lo
tocado; `lfs-insim list` OK. Solo lógica del insim de ejemplo → **no tocan la API pública**. Como son
**conducta**, ⏳ **requieren validación en LFS**.

**Continuación de S33 (la sesión siguió; el usuario preguntó cómo asignar vías prioritarias a una zona).**

**Editor de reglas de prioridad de zonas en la UI (`a29fde3` → `5f9af3d`).** El usuario no podía asignar
prioritarias al crear una zona: el detalle de una Zona en Elementos solo exponía `zone_id`/`nodes`/`radius_m`;
las `priority_rules` solo se fijaban por chat (`!map set <zona> priority_rules add;A,B`). Se añadió un editor en
ese detalle. **Primera versión (`a29fde3`):** dos TypeIn (prioritaria/cede) + Anadir, con validación de que las
vías existan. **Tras feedback del usuario** ("que se seleccionen como al crear un RoadLink/LatLink") se rehízo
(`5f9af3d`): el botón "+ Anadir regla" abre una **sub-pantalla con el mismo picker de vías** — slots
"-> Prio"/"-> Cede", lista paginada, se elige de la lista (auto-avanza de slot), Confirmar/Cancelar; la lista de
reglas queda con su Quitar. Reutiliza `_ui_road_picker_*`, `_UI_CID_TI1/TI2` y `_cmd_set` (add/del) del recorder;
estado `_ui_zone_prio_adding` reseteado al abrir otro detalle o cambiar de pestaña. Se **usó la skill de proyecto
`ai-control-map-ui`** para orientarse. Red primero: `test_map_ui_zone_priority.py` (9 tests, reescritos a la UX
del picker). Solo UI del insim de ejemplo → no toca la API pública.

**Primera intersección del proyecto → W4 desbloqueada.** El usuario, en LFS, creó la primera zona con reglas.
Llegó por el árbol de trabajo dos veces (protección §1.2): `A13_MonumentServices` (`638698e`) y luego `test1`
(`12c29a4`: cápsula 2 nodos + `priority_rules` `HAVEN_LANE_S22_a/b` > `SOUTH_CITY_STATION_s2`). **W4 ya no está
bloqueada por `zones: 0`** — queda validarla en el juego.

**Duda de diseño resuelta (sin código):** ¿el privilegio/restricción de zona se mantiene mientras se recorre un
roadlink? **Sí para IAs:** al entrar a un roadlink, `navigation.py` cambia `current_id`/`current_type` pero NO
`current_road_id` (solo se actualiza a `to_road_id` en `fin_de_geometria`); y el ceda-el-paso se apoya en
`current_road_id` (`orchestrator.py:310`/`:366`). **Matiz:** un coche HUMANO se localiza geométricamente
(`get_location_context`), no por id conservado → aproximado. (Posible mejora futura.)

**Fix del ceda-el-paso tembloroso (`73bbae7`).** Probando `test1`, el usuario reportó que la IA "acelera a fondo
mientras mete el freno de mano repetidamente". **Diagnóstico:** al ceder, `speed_request=0` → la física
(`physics.py:107‑119`) lo trata como **aparcar** (`HANDBRAKE=MAX` + `IGNITION=OFF`), y `>0` dispara encendido +
gas a fondo; la decisión de ceder (`orchestrator.py`) **no tenía histéresis** y se soltaba al primer tick sin
prioritario → `speed_request` parpadeaba 0↔base y la física oscilaba a ~100 Hz. **Decisión (pregunta con
recomendación, MODUS §6):** el usuario eligió **histéresis** (sin tocar la física) frente a la opción B (que la
parada temporal no apague motor/freno de mano — toca TODAS las paradas, aparcada). **Fix:** predicado puro
`_should_keep_yielding(detected, hold_until, now)` + `mode._yield_hold_until` (renovado a `now + YIELD_HOLD_S=1.0s`
al detectar; sin detección se cede hasta que expira). Solo `orchestrator.py` + campo en `mode.py`. Red primero:
`TestShouldKeepYielding` (3). Suite **749/749**; ruff limpio.

**Cierre de S33:** docs de `docs/dev/` actualizados + commits pusheados (CI verde tras los fixes 4/1; el resto
son commits posteriores, mismo árbol). Todo ⏳ pendiente de validación en LFS (W4 + fixes de conducta + editor).
**Próximo:** validar en LFS (Frente A) y/o implementar el **fix (3)** (radar en transición road→roadlink, Frente B).

## S32 — 2026-07-12 — Herramienta "Link auto" en la UI de mapeo (petición del usuario, fuera de plan)

**Arranque:** protocolo de inicio. Ya en `refactor/estabilizacion`. **Mapa South City sin commitear**
(871 inserciones en `south_city.json` + su render, avance de mapeo del usuario) → **protegido** (§1.2):
respaldo fuera del repo + commit `data(ai_control)` `32a54d2` + push antes de nada. `git pull`: ya al día.
El usuario pidió **pausar el plan** (Fase 7) e implementar una herramienta que necesita **para mapear
cómodo**.

**Qué se hizo (red primero, MODUS §3):** nuevo botón **"Link auto"** en la pestaña **Grabar** de
`map_ui.py`, justo debajo de "RoadLink" (CID 118, idle reorganizado a filas T=21/31/41/52/63). Graba un
**RoadLink sin teclear origen ni destino**:

1. **Inicio** (`_map_ui_start_auto_link`): captura el road de ORIGEN de la vía más cercana al coche que se
   graba (`recording_plid`, humano o IA) vía `get_location_context`, siembra el nodo de origen, activa el
   autograbado y entra en fase `recording`. Guardas: mapa activo, telemetría legible, hay vías en el mapa.
2. **Finalizar** (`_map_ui_finalize_auto_link`): detecta el road DESTINO por la posición actual, cierra el
   trazado con un nodo en el destino, **congela** el autograbado y evalúa el nombre `origen[suf]->destino[suf]`.
3. **Confirmación** (nombre libre): pantalla con el nombre final + **Aprobar** / **Cancelar**.
4. **Conflicto** (el nombre ya existe): pantalla con **3 opciones** — (1) añadir **sufijo** a origen y/o
   destino y **Recomprobar** (re-evalúa; si sigue chocando, avisa), (2) **Sobrescribir** el existente
   (actualiza sus nodos), (3) **Cancelar**. Cancelar disponible en todas las pantallas.

**Decisiones de diseño:**
- **Nombre "Link auto"** en vez de "AUTOGRABAR": ya existe un toggle **"Auto"** (captura de nodos en
  movimiento) → "AUTOGRABAR" habría sido ambiguo. "Link auto" deja claro que es el enlace lo automático.
- **Estado del flujo en `current_recording["auto_phase"]`** (no en estado de UI): así **sobrevive a
  cerrar/reabrir el menú** (la grabación vive en el recorder, no en la sesión de menú) sin añadir estado
  que resetear en `_init_ui_state`.
- **Reutiliza `_cmd_rec_end`** del recorder para materializar el RoadLink (crear si `is_new`, actualizar
  nodos si sobrescribe) → cero duplicación de la lógica de guardado.
- El origen/destino se toman de `recording_plid` (el coche que se graba), no del UCID del menú.

**Red:** nuevo `tests/insims/ai_control/test_map_ui_auto_link.py` (**13 tests**) sobre la `AIControl` del
harness + `MapRecorder` real con `get_location_context` de verdad (roads A@(0,0) y F@(100,0); el coche se
mueve de A a F): botón dibujado bajo RoadLink, guard sin PLID, captura de origen, error sin vías, finalizar
→ confirm (nombre `A->F`), Aprobar crea el RoadLink, Cancelar no crea nada, finalizar con conflicto → las
3 opciones + campos de sufijo, sufijo libera el nombre (`A->Fb`), recomprobar sin sufijo sigue en conflicto,
sobrescribir reemplaza los nodos del mismo objeto, cancelar deja el link intacto, y el flujo sobrevive a
cambiar de pestaña.

**Verificación:** suite **723/723** (710 + 13); `ruff check` + `ruff format --check` limpios en lo tocado;
`lfs-insim list` OK. Solo lógica de UI del insim de ejemplo → **no toca la API pública** del framework.
Como es UI/conducta se validó en LFS: **✅ el usuario confirma que "funciona perfectamente"**. Commits:
`32a54d2` (mapa) + `b316ffb` (herramienta + tests + docs) + el de la validación.

**Extra S32 — primera skill de proyecto + paso prioritario de tooling.** El usuario preguntó si podía
autocrearme skills y si servirían para optimizar (menos tokens) los ajustes recurrentes de la UI de
ai_control. Tras explicar el modelo (una skill es un *playbook on-demand*, no una caché del código: recorta
la *orientación*, no el editar/verificar; mejor que CLAUDE.md porque solo se carga cuando es relevante), se
decidió **crearla ahora** (el mapa de `map_ui.py` estaba fresco en contexto → barato y preciso; diferirlo
obligaría a releer 3200+ líneas en frío). Creada **`ai-control-map-ui`** (`.claude/skills/ai-control-map-ui/
SKILL.md`): estructura de la UI (rangos de CID, patrón dibujar↔click, TypeIn, receta, harness de tests,
convenciones), redactada en **estructura/convenciones, no números de línea**. Para sincronizarla por git se
**des-ignoró `.claude/skills/`** en `.gitignore` (el resto de `.claude` sigue local). Se añadió al PLAN un
**paso prioritario** (§ "Tooling de trabajo — Skills"): evaluar qué otros flujos merecen skill (candidatas:
`cerrar-sesion`/`arrancar-sesion`) y ratificar la convención de gestión. Commit de cierre de S32 (skill +
`.gitignore` + docs).

**Extra S32 — 3 ajustes pequeños de UI en la pestaña Grabar (pedido del usuario; ⏳ requiere LFS).** Tras
validar "Link auto", el usuario pidió un lote de 4 cambios de UI; se hicieron los **3 pequeños** ahora y se
**aparcó el grande** (editor masivo) para su propia sesión (permiso explícito del usuario para repartir).
Con red primero (`test_map_ui_grabar_prefs.py`, 10 tests):
1. **Toggle "Trafico" movido de Mapa → Grabar** (CID 108): la norma por defecto de las nuevas vías se ajusta
   donde se graba. Fuera de `_map_ui_draw_tab_mapa`/`_map_ui_click_mapa`; entra en el idle de Grabar.
2. **Velocidad por defecto de grabado** (campo TypeIn CID 129 en Grabar): nuevo `default_speed_limit_kmh` en
   `MapRecorder` (default 30) que `_cmd_rec_end` aplica al crear un `RoadSegment` (antes 30 fijo); parseo en
   `on_ISP_BTT` (revierte si es inválido o ≤0).
3. **"Auto" pegajoso** (bug reportado: cancelar un road desmarcaba Auto): quitado `auto_recording_enabled =
   False` de `_cmd_rec_cancel` y de la rama sin-nodos de `_cmd_rec_end`. El **Link auto** dejó de apagar Auto
   al finalizar/commit; en su lugar la captura se **congela por fase** (gate nuevo en `update_recording`: si
   `current_recording["auto_phase"]` no es `None`/`"recording"`, no añade nodos) → la preferencia Auto queda
   intacta. Se actualizó el test de auto-link afectado (ahora verifica Auto=ON + congelación por fase).

**Decisión de reparto:** 3 pequeños ahora (cohesivos, en la zona Grabar/recorder que tenía fresca); el editor
**MASIVO** (buscador + multi-selección + aplicar-a-N sobre elementos) se aparca con **`TODO` en
`_map_ui_draw_tab_elementos`** + entrada en Ideas del PLAN (candidato a estrenar la skill `ai-control-map-ui`).
Suite **733/733** (723 + 10); ruff limpio; `lfs-insim list` OK. Solo UI del insim de ejemplo → **no toca la
API pública**. Como es UI/conducta, **⏳ pendiente de validar en LFS**. Se re-protegió el avance de mapeo de
la sesión (South City, 33k líneas) en `997769a`. Commit de cierre (UI + tests + docs).

---

## S31 — 2026-07-11 — Cierre de W3 (Fase 6): FSM revisado, código muerto fuera, `base.py` adelgazado (P4), docs de arquitectura

**Arranque:** protocolo de inicio. Ya en `refactor/estabilizacion` y en sync con `origin` (tip S30,
`e0de8e2`), no hizo falta pull. **Árbol limpio, sin mapas que proteger** (§1.2). El usuario pidió
**cerrar W3 tirando por el Frente A** (offline, sin LFS): revisar el FSM de adelantamiento, borrar el
código muerto, adelgazar `base.py` (P4) y actualizar los docs de arquitectura.

**Qué se hizo (todo con red / extracción segura, MODUS §3):**

1. **FSM de adelantamiento revisado** (`traffic/orchestrator.py` + `overtake.py`): estados
   IDLE→EVALUATING→OVERTAKING→RETURNING con cooldowns; estructura sólida, **sin cambios de conducta**.
   *Cleanup seguro:* `_finish_overtake` recibía un parámetro `name` que **no usaba** (resto de una
   eliminación de logs); el orquestador le pasaba `_n = ai.ai_name`, alias que **solo** alimentaba esas
   2 llamadas. Quitados el parámetro y el alias (el test `test_finish_overtake_...` ya llamaba sin `name`
   → red intacta). Pura estructura.

2. **Código muerto eliminado:** `is_target_ahead_and_in_lane` de `nav_modes/freeroam/geometry.py`
   (confirmado sin uso en producción por grep: solo la definición + sus 5 tests de caracterización +
   menciones en docs). Borrada la función y la clase `TestIsTargetAheadAndInLane` de `test_geometry.py`
   (el import `Any` se queda: lo usan otras 6 firmas). Suite **704→699**.

3. **Marcadores `[!] OPTIMIZACIÓN` de `radar.py`** (4: líneas 107/121/165/208) → comentarios normales
   (quitados el prefijo de atención `[!]` y la numeración secuencial, ya sin sentido; conservada la
   explicación útil). Solo comentarios.

4. **P4 — `base.py` adelgazado (honestidad del contrato):** `_MixinBase` declaraba 32 métodos como
   "cross-mixin", pero un **script de auditoría del grafo de llamadas** (`self.<m>` vs `def <m>` por
   fichero en todo `ai_control`) reveló que **12 son self-local** (solo se llaman dentro de su propio
   mixin): `_calculate_next_link`, `_cmd_add`, `_cmd_map_freeroam`, `_cmd_route_follow`,
   `_generate_random_pid`, `_get_available_overtake_distance`, `_get_coords_for_map`,
   `_get_radar_speed_limit`, `_get_raw_candidates`, `_is_link_reachable_ahead`, `_is_point_in_zone`,
   `_plan_next_link`. Su clase ya los ve → no pertenecen a un contrato *cross-mixin*. Fuera del contrato
   (quedan **20** genuinamente cruzados, cada uno anotado con quién lo llama); de rebote, los imports
   `Coordinates` y `PIDController` quedaban huérfanos (los usaban 2 métodos removidos) → fuera. Todo bajo
   `if TYPE_CHECKING:` → **cero runtime, cero test**; ruff limpio (habría cazado F401). **Matiz clave:**
   es honestidad del contrato, NO un desacople real — las 20 llamadas cruzadas siguen ahí. El **desacople
   profundo** (romper el "God object") es refactor arquitectónico de riesgo (el orquestador
   `_update_traffic_behavior` no tiene red) → queda **pendiente**, anotado en DIAGNOSTICO § P4.

5. **Docs de arquitectura:** CLAUDE.md — corregida la composición de `AIControl` (faltaba `_MapUIMixin`)
   + nota de la fachada `_TrafficMixin` sobre el paquete `traffic/` y del contrato `_MixinBase`; sección
   "ai_control nav system" ampliada (paquete `traffic/`, FSM de adelantamiento, rejilla del radar).
   DIAGNOSTICO § P4 revisado. El README ya delega la arquitectura a `docs/guia/` → sin cambios.

**Con esto W3 queda CERRADO** (los splits de `map_ui.py`/`map_recorder.py` estaban ya aplazados a
post-merge en S27). **Fase 6 (pre-publish) completa salvo W4** (validación en LFS del ceda-el-paso del
ACC, bloqueada por `zones: 0`).

**Verificación:** suite **699/699** (704 − 5 del código muerto); `ruff check` + `format --check` limpios
(103 ficheros); `lfs-insim list` OK; diff = 54 inserciones / 203 borrados (mayoría: código muerto +
contrato). Solo estructura/comentarios/docs del insim de ejemplo → **no toca la API pública ni requiere
validación en LFS**. **Commits:** `5bf394f` (código) + `788a791` (docs), pusheados; CI verde (incl. 3.9).

### Parte 2 — Herramienta "Apunta" en la UI de mapeo (2ª petición del usuario, no planeada)

**Petición:** una herramienta nueva en la pestaña **Info**, fija como los WA, que indique la **vía más
cercana a la que apunta la punta del coche** (distinta de la actual) y **a qué distancia** — muy útil para
mapear. Además, dejar marcado en el plan que lo próximo son los 3 fixes de la Fase 7 (que el usuario deberá
confirmar OBLIGATORIAMENTE en LFS).

**Diseño:** se integra como **6º tipo del overlay whereami** (`ahead`) en lugar de un overlay nuevo → reusa
toda la infra pineada de S30 (persiste entre pestañas, refresca en `on_tick`, se redibuja en reconexión, se
quita deseleccionando). Más DRY y consistente con lo pedido ("igual que los WA").

**Qué se hizo (red primero, MODUS §3):**

1. **Geometría pura `find_road_pointed_at`** (`nav_modes/freeroam/geometry.py`): **ray-cast 2D** desde la
   posición del coche en la dirección del morro; devuelve `(road_id, distancia)` del road cuyo segmento
   cruza el rayo MÁS CERCA, dentro de `max_dist`, excluyendo el road actual; `(None, inf)` si no toca nada.
   Test rayo-segmento estándar (u∈[0,1], t≥0, mínimo). **9 tests** (acierto directo, detrás, más-cercano de
   dos, exclusión de la actual, más allá de max_dist, road paralelo, vector nulo, rumbo diagonal, fuera de
   segmento), verdes ANTES de integrar.
2. **Rumbo del morro:** helper `_map_ui_forward_vector(ucid)` que saca el heading del coche
   (`player.telemetry.heading.angle_lfs`) y lo pasa a vector `(-sin, cos)` con la **misma fórmula que el
   orquestador de IA** → coherente con cómo el módulo entiende "hacia delante". Funciona parado (usa rumbo,
   no velocidad).
3. **Integración en `map_ui.py`:** nuevo tipo `"ahead"` en `_WA_TYPES`; toggle **"Apunta"** en Info (la fila
   pasa de 5 a 6 botones, ancho 30→26 para caber junto al TypeIn de intervalo); rama `"ahead"` en
   `_map_ui_compute_whereami` que excluye la vía actual (la más cercana a la posición, vía
   `get_closest_geometry`) y formatea `Apunta: <road> | <dist>m`; click handler extendido a CID 118;
   constante ajustable `_AHEAD_MAX_DIST_M = 300.0`.
4. **Red de integración:** +2 tests en `test_map_ui_whereami.py` (el toggle CID 118 activa el tipo `ahead` y
   dibuja su fila; el compute end-to-end, con telemetría+roads sintéticos del harness, reporta la vía
   apuntada y su distancia excluyendo la actual).

**Plan:** marcada la **Fase 7 como PRÓXIMO** en `PLAN.md` (implementar los 3 fixes offline con red primero;
el usuario los **confirma OBLIGATORIAMENTE en LFS** después) + la herramienta Apunta registrada como extra
S31 en Fase 5.

**Verificación:** suite **710/710** (699 + 9 + 2); `ruff check` + `format --check` limpios (103 ficheros);
`lfs-insim list` OK. Solo lógica de UI del insim de ejemplo → **no toca la API pública**; como es
UI/conducta, ✅ **validado en LFS por el usuario** ("funciona perfectamente"). **Commit:** el de la herramienta Apunta (S31).

---

## S30 — 2026-07-11 — Retoque de UI de `ai_control` (whereami → overlay fijo) + validación en LFS del fix 2 de S29

**Arranque:** protocolo de inicio. Ya en `refactor/estabilizacion` y en sync con `origin` (tip S29,
`bfea66e`), no hizo falta pull. **Árbol limpio, sin mapas que proteger** (§1.2). El usuario abrió la
sesión confirmando que **el fix de la última sesión funciona correctamente** → el **watchdog de fin de
vía → espectadores (fix 2 de S29) queda VALIDADO en LFS**. Pidió **no continuar el trabajo de
refactor** y hacer en su lugar un **retoque de UI** de `ai_control`.

**Petición del usuario:** en la pestaña **Info** hay toggles para mostrar el whereami (WA Road, WA
RLink, WA LLink, WA Zone, WA Regla). Los quería convertir en algo **fijo anclado a la mitad-derecha de
la pantalla**, que **siga apareciendo al cambiar de pestaña y aunque se cierre el menú**, y que la
**única forma de quitarlo sea deseleccionándolo** en el menú.

**Qué se hizo — overlay whereami "pineado" (CON RED PRIMERO):**

1. **Antes:** el whereami se dibujaba como panel dentro del contenido de la pestaña Info (`_WA_CID_BASE
   = 153`, CIDs 153-157), **dentro del rango de contenido** (108-165) que `_map_ui_clear_content` borra
   en cada redibujado → desaparecía al cambiar de pestaña y al cerrar el menú; y solo se refrescaba con
   `_ui_tab == "info"`.

2. **Ahora:** overlay fijo con **CIDs propios 166-171** (título "Ubicación" + 1 fila por tipo activo),
   **fuera del rango de contenido** → sobrevive a los redibujados de pestaña. Anclado a la
   mitad-derecha (`_WA_PIN_L=150`, `_WA_PIN_W=48`; centrado vertical en `_map_ui_pinned_whereami_top`,
   T≈100). Métodos nuevos: `_map_ui_redraw_pinned_whereami` (geometría completa, en cada toggle / cierre
   / reconexión), `_map_ui_refresh_pinned_whereami` (solo texto, en `on_tick`), `_map_ui_clear_pinned_
   whereami`, `_map_ui_active_whereami`. Se borró el viejo `_map_ui_draw_whereami_panels` y la constante
   `_WA_CID_BASE`.

3. **Persistencia:** estado nuevo **`_ui_whereami_ucid`** (dueño del overlay, independiente del
   `_ui_ucid` del menú). `_init_ui_state` **ya no resetea** el whereami (guard `hasattr` → se inicializa
   una sola vez) → persiste al reabrir el menú. `_map_ui_close` **redibuja** el overlay tras el
   `BFN.CLEAR`. `_map_ui_compute_whereami` usa `_ui_whereami_ucid` (no `_ui_ucid`, que es `None` con el
   menú cerrado). `on_tick` refresca el overlay **al margen del menú** (se reestructuró: el bloque del
   overlay corre siempre; el resto sigue exigiendo menú abierto). `on_reconnect` (app.py) lo redibuja
   (P12: LFS pierde los botones al caer la conexión). El toggle en `_map_ui_click_info` (CIDs 113-117)
   fija/suelta `_ui_whereami_ucid` y dibuja/borra el overlay; al quitar el último tipo se limpia.

4. **Red primero (MODUS §3):** `tests/insims/ai_control/test_map_ui_whereami.py` (**7 tests**) sobre la
   `AIControl` real del harness (client que captura los envíos): dibujo a la derecha con CIDs >165,
   persistencia entre pestañas (el DEL_BTN de contenido no abarca 166+), supervivencia al cierre
   (redibujado tras `BFN.CLEAR`), borrado al deseleccionar el último, refresco con el menú cerrado
   (solo texto, W=0/H=0), y que `compute` usa el UCID del overlay (nunca `None`) y persiste al reabrir.

**Decisiones de diseño:** (a) rango de CIDs 166-171, el primero libre por encima del techo de contenido
(165) y muy por debajo del límite de LFS; (b) el overlay es **single-user** como todo el resto de la UI
(`_ui_ucid` es un único campo) — no se aborda multi-usuario; (c) **UX conocida**: con el menú abierto en
Info y paneles desplegados, el overlay puede solaparse con la esquina inferior-derecha del menú (ambos
~L150+); con el menú cerrado —el caso de uso principal— queda limpio. Posición/tamaño en constantes por
si el usuario quiere afinar.

**Verificación:** suite **704/704** (697 + 7); `ruff check` + `format --check` limpios en lo tocado;
`lfs-insim list` OK. Solo lógica de UI del insim de ejemplo → **no toca la API pública**. **✅ VALIDADO
en LFS por el usuario: "funciona a la perfección".** **Commit:** el de cierre de S30 (código + tests +
docs).

---

## S29 — 2026-07-11 — Fase 7 (NUEVA): bugs de conducción freeroam + fix 2 (fin de vía → espectadores)

**Arranque:** protocolo de inicio. Ya en `refactor/estabilizacion` y en sync con `origin` (tip S28,
no hizo falta pull). El árbol traía **South City con 2 roads `is_closed:true→false`** sin commitear →
protegido según §1.2 (respaldo en scratchpad + commit `dcca07a` `data(ai_control): abre 2 roads en
South City` + push con el workaround de `gh` credential helper) ANTES de tocar nada.

**Petición del usuario:** conduciendo en LFS reportó **4 bugs del modo Freeroam** de `ai_control` y
pidió (a) resolver **uno ahora** (fin de vía → espectadores) y (b) **aparcar los otros 3 en el plan**,
delegándome el cuándo. Pidió opinión y cómo proceder.

**Decisión de rumbo:** los 4 son bugs de **conducción del insim de ejemplo** (el escaparate), **no
tocan la API pública** del framework → no bloquean la estabilidad de API de Fase 6. Como todos
necesitan **validación en LFS**, encajan con las sesiones de LFS de **W4** (mismo gate). Creada una
**Fase 7** dedicada en `PLAN.md` con el diagnóstico preciso de cada uno; el usuario decide el orden y
si van antes o después del merge (no urge para el release del framework).

**Fix 2 — fin de vía sin salida → espectadores (HECHO, red primero):**

1. **Diagnóstico:** una IA que llega a un fin de vía sin `next_link` se quedaba clavada a 0 km/h para
   siempre. Dos huecos: (a) el anti-stuck de `_update_freeroam_navigation` trata `speed_request<5`
   como parada **intencionada** y resetea su temporizador → nunca castiga la parada de fin de vía;
   (b) el único spec de fin de vía (en `fin_de_geometria`) solo saltaba en el tick exacto en que la
   IA **captura** el último nodo yendo a >1 km/h — si frenaba antes, no saltaba nunca.

2. **Solución:** watchdog dedicado en `navigation.py`. Predicado **puro** `_is_dead_end_stop(mode,
   speed_kmh)` → True solo si: velocidad <`DEAD_END_SPEED_KMH` (2 km/h), `mode.next_link_id` None,
   `overtake_state` no en OVERTAKING/RETURNING, y road actual no circular. Esto **distingue el
   callejón sin salida de la parada de tráfico legítima** (que conserva su `next_link` esperando para
   avanzar). Temporizador `mode._dead_end_since` (campo nuevo en `FreeroamMode.__post_init__`); si el
   estado persiste `DEAD_END_TIMEOUT_S` (4 s) → `_cmd_spec(plid)`. Se **centralizó el spec** en el
   watchdog y se quitó el inline de `fin_de_geometria` (con el watchdog, doble-spec-eaba → el 2º
   `_cmd_spec` mandaba un MSL de error porque el PLID ya no está en `ais`).

3. **Red primero (MODUS §3):** `TestIsDeadEndStop` en `test_navigation.py` (6 tests: fin de vía real,
   parada de tráfico con `next_link`, en movimiento, adelantando, vía circular, sin localizar). El
   orquestador `_update_freeroam_navigation` sigue sin red (usa `time.time()` y muta mucho estado, como
   los demás grandes orquestadores) → se testea el **predicado extraído**, y el cableado en el
   orquestador es mínimo y obvio. Constantes ajustables si en LFS conviene otro umbral/timeout.

**Otros 3 fixes → Fase 7 (diagnóstico en PLAN):** (1) **flip de enlace en salidas muy juntas** — el
intermitente marca un enlace y en el último momento se sobreescribe por el otro (asimétrico, solo un
lado); sospecha: `_calculate_next_link` (`random.choice`) se **re-planifica** en varios triggers y el
filtro `_is_link_reachable_ahead` cambia al avanzar → cambia la elección ya comprometida; arreglo:
hacerla **pegajosa**. (3) **radar en transición road→roadlink** — `traffic/radar.py::_scan_lane_ahead`
acota candidatos a `mode.current_id` (solo el link) → olvida a los de delante en el road que deja (los
choca) y no ve a los de dentro al entrar por un roadlink; arreglo: ampliar el match topológico a la
cadena current→next durante la transición. (4) **`is_closed` a medias** — **hueco cazado leyendo el
código**: `traffic/overtake.py::_find_valid_overtake_lane` NO comprueba `road_geom.is_closed` →
adelanta por carril cerrado; arreglo: auditar todos los consumidores y centralizar con
`_is_road_usable(road_id)`.

**Verificación:** suite **697/697** (691 + 6); `ruff check` + `format --check` limpios en lo tocado.
Solo lógica del insim de ejemplo → **no requiere validación en LFS para la corrección**, pero SÍ para
confirmar la conducta (pendiente). **Commits:** `dcca07a` (protección del mapa) + el de S29 (fix 2 +
Fase 7 + docs).

---

## S28 — 2026-07-11 — Fase 6 · W3: índice espacial de VEHÍCULOS para el radar

**Arranque:** protocolo de inicio. Ya en `refactor/estabilizacion`, pero el árbol traía **South City
sin commitear** (+5122/−1298 en `south_city.json` + render regenerado, **189 roads / 13.480 nodos**,
`zones: 0`). Protegido según §1.2 (instrucción permanente, autorizada sin preguntar) ANTES del pull:
respaldo fuera del repo (`~/backups/AP_LFS_InSim_maps/2026-07-11_S27/`) + JSON validado + commit
`data(ai_control)` + push. El `git pull` posterior trajo **S27 del otro equipo** (split de `traffic/`
+ P7); mi commit del mapa mergeó **limpio** (ortogonal). Baseline verificado tras el merge: **680/680**.

**Qué se hizo — índice espacial de vehículos para el radar (ex-6b de la auditoría S22, plegado en
W3), CON RED PRIMERO:** los 3 barridos de `traffic/radar.py` (`_scan_lane_ahead`, `_scan_target_lane`,
`_scan_return_lane_gap`) recorrían **todos** los vehículos por IA → O(N) por IA → **O(N²) global**.

1. **`SpatialHashGrid.ids_within(px,py,radius)` (nuevo, red primero):** consulta de **REGIÓN** —
   todos los ids de las celdas que solapan la caja `[px±r, py±r]`, superconjunto de los que distan
   ≤ r del centro (nunca falsos negativos). Complementa a `ring_ids` (vecino más cercano); el
   docstring de S23 ya la anticipaba ("reutilizable en el radar de vehículos"). +7 tests unitarios
   (dentro/fuera, radio 0, superconjunto por esquina de celda, borde, id repetido, vacío, radio<0),
   verificados en ROJO (AttributeError) antes de implementar.

2. **`_build_vehicle_grid` + `_iter_radar_candidates` (radar.py):** `_build_vehicle_grid` construye
   la rejilla **una vez por MCI** (la llama `on_ISP_MCI` antes del bucle de IAs → todas comparten la
   misma foto), indexando por PLID la posición 2D de cada vehículo con telemetría. **`players`/`ais`
   son disjuntos por PLID** (verificado en `users_management`: NPL mete en uno u otro con `return`) →
   índice PLID→(player,is_ai,other_ai) **1:1**. `_iter_radar_candidates(cx,cy,radio)` emite los
   candidatos: con rejilla, el vecindario (`ids_within`); **sin rejilla (None), itera TODOS** en el
   mismo orden que antes (el camino de referencia).

3. **Los 3 barridos:** cambia **SOLO la línea del `for`** → `_iter_radar_candidates(...)` con el radio
   = el culling propio de cada método (`max_dist+15` en los dos primeros, `max_dist*2` —3D— en el de
   retorno, holgado en 2D). **Todos los culls y filtros por-vehículo quedan intactos.** Como la
   rejilla es un SUPERCONJUNTO del culling y el barrido aplica su culling exacto → **salida
   bit-idéntica** (equivalencia por CONSTRUCCIÓN, no por reimplementar la matemática; mismo patrón
   que el índice de geometría de S23).

**Red de equivalencia (la caracterización del radar "como unidad" que exigía el plan):** clase
`TestRadarSpatialGridEquivalence` — fuzz de **40 semillas × 3 barridos** con mezcla aleatoria de IAs
(topología) y humanos alrededor del escáner, corriendo cada barrido DOS veces (sin rejilla =
referencia, con rejilla) y comparando **bit a bit**. Helper `_run_both` limpia las cachés de humanos
antes de cada corrida para que la rama de humano (`time.time()` + caché) sea determinista. + un test
de **candidato diagonal** (coche detectado en una celda distinta a la del escáner, que una consulta
de solo-celda-central perdería → discrimina el bug) + guardián anti-vacuo (`non_empty ≥ 5`). +4 tests.
**Ajuste del fuzz:** el primer intento casi no producía detecciones (posiciones y `node_index`
independientes) → correlacioné `node_index` con la `y` (como en producción) y mezclé vehículos cerca
(detecciones) y lejos (culling + celdas distantes).

**Benchmark (tick = todas las IAs barriendo, mapa 1000×1000 m):** `sin_grid` crece **cuadrático**,
`con_grid` **lineal** → **2,5× @N=24, 4,2× @N=48, 5,2× @N=64**, y creciendo con la densidad. **Celda
50 m**, elegida con sweep (meseta plana 40-80 m: por debajo penaliza el sondeo de celdas vacías; por
encima, más candidatos por celda al agruparse las IAs). Reset del grid en `on_reconnect` (P12).

**Decisión de diseño (fallback a None):** que el radar itere todos cuando `_vehicle_grid is None`
mata dos pájaros: (a) los 81 tests de S19 (que llaman los barridos directos, sin MCI) siguen verdes
sin tocar; (b) da el **camino de referencia** que el fuzz compara contra la rejilla, sin duplicar
código. En producción `on_ISP_MCI` siempre la construye antes de barrer.

**Verificación:** suite **691/691** (680 + 11: 7 grid + 4 equivalencia). `ruff check .` +
`ruff format --check .` limpios (repo entero, 102 ficheros). `lfs-insim list` carga los 4 insims.
3.9-safe (`dict[int, tuple]`/`set[int]` son PEP 585, `from __future__ import annotations`; sin
uniones PEP 604). Solo estructura + rejilla, **salida idéntica → no requiere validación en LFS**.

**Próximo:** cerrar W3 (último ítem de Fase 6) — **FSM de adelantamiento** (`traffic/overtake.py`) +
borrar `is_target_ahead_and_in_lane` (código muerto S24, con su test de `test_geometry.py`) + **P4**
(adelgazar `base.py`) + docs (README/CLAUDE con `traffic/` + rejilla). **W4** (validación LFS del
ceda-el-paso del ACC) sigue bloqueada por `zones: 0`. Sesión nueva recomendada (context-rot).

**Commits:** `8d757df` (mapa South City, protección de arranque), merge del pull, `acdba01`
(`perf(ai_control): índice espacial de vehículos para el radar`) + docs de cierre S28.

---

## S27 — 2026-07-10 — Fase 6 · W3 (1/2): split de `traffic.py` + P7 (nombres de estado)

**Arranque:** protocolo de inicio; ya en `refactor/estabilizacion`, árbol limpio (sin mapas que
proteger). `git pull` trajo S26 desde el otro equipo (tip `8c6c4b0`). Baseline verificado:
**680/680**. Próximo paso documentado: **W3**, último ítem de Fase 6.

**Hallazgo de arranque — el PLAN estaba desfasado:** los ficheros gordos habían crecido ~70% desde
que S23 escribió W3: `map_ui.py` 1841→**3161**, `map_recorder.py` 1604→**2520**, `traffic.py`
1084→**1348**. W3 tal cual eran varias sesiones.

**Decisión de alcance (pregunta con recomendación, MODUS_OPERANDI §6 — el usuario eligió la
recomendada): RECORTAR W3 pre-publish.** Entran `traffic.py` + radar + FSM + P4 + P7; **se aplazan
a post-merge** los splits de `map_ui.py` y `map_recorder.py`. Razón: son **tooling offline** de
edición de mapas — no son el framework publicado, no tocan el runtime de conducción ni la API
pública, y no tienen red de caracterización. Partir 5.700 líneas ahí no aporta nada al primer
release y retrasa el merge (que ya espera a W4). `traffic.py` sí entra: hospeda el radar (donde
aterriza el índice espacial) y tiene la red de los 81 tests de S19.

**Qué se hizo — 1) P3 (parte pre-publish): `traffic.py` → paquete `traffic/`.** Un módulo por
responsabilidad: `radar.py` (393), `orchestrator.py` (468), `overtake.py` (239), `zones.py` (80),
`cruise_control.py` (80), `paths.py` (51). `_TrafficMixin` pasa a ser una **fachada** que compone
los submixins, así que `app.py` y los tests no se enteran del reparto (los tests ya ejercitaban
`AIControl`, no el mixin). **Extracción segura de verdad** (MODUS_OPERANDI §3): los cuerpos se
movieron **por rango de líneas con un script**, nunca a mano; un script de análisis derivó primero
los spans y qué import usa cada método (de ahí que ruff pasara a la primera, sin F401/F821). La
prueba: snapshot antes/después con `inspect.getsource` → los **18 métodos conservan cuerpo y firma
BYTE-IDÉNTICOS**, `AIControl` los resuelve a la **misma función** y su superficie sigue teniendo
los **mismos 182 atributos**; el MRO linealiza (6 submixins nuevos). Cero líneas de código
perdidas (verificado: ninguna línea no-vacía fuera de los rangos asignados).

**2) P7 — nombres del modelo de estado (`behavior.py`).** El par "intención vs valor en uso"
(`target_speed_kmh_use`/`target_speed_kmh`, `target_point_use`/`target_point_m`) pasa al patrón
**petición → resuelto**: `speed_request`/`speed_resolved_kmh` y `point_request`/`point_resolved`.
Los `*_request` (heterogéneos: float o `AdaptiveSpeedConfig`; punto, tupla o PLID) los escriben
comandos y navegación; los `*_resolved` los calcula `physics.py` en cada MCI. 93 sustituciones en
9 ficheros, por **palabra completa** (`\btarget_speed_kmh\b` no casa dentro de
`target_speed_kmh_use`, porque `_` es carácter de palabra) → cero restos.

**Colisión cazada (lo interesante):** el rename tocó de más. `_estimate_overtake_distance` tenía un
**parámetro** llamado `target_speed_kmh` que **no es el campo**: es la velocidad del coche AL QUE se
adelanta. Renombrarlo a `speed_request` habría sido activamente engañoso. Se revirtió y se le puso
`target_vehicle_speed_kmh` (todas las llamadas son posicionales) — justo la ambigüedad que P7
denuncia. Auditados uno a uno los 93 sitios; el resto eran accesos `behavior.<campo>` o kwargs del
dataclass. De paso: `point_request` declara ya el `tuple[float, float]` que `physics.py` aceptaba
y la anotación se callaba; fuera el comentario residual `# En tu dataclass o clase AIBehavior:` y
el marcador `[!] NUEVO`. Los otros 20 marcadores `[!]` se limpian **zona a zona** (los de
`traffic/radar.py`, con el radar). Campos reordenados (petición antes que resuelto): `AIBehavior`
solo se construye con kwargs (`app.py`, `conftest.py`), así que el `__init__` posicional da igual.

**De propina:** `base.py` dice ahora en qué submódulo vive cada método cross-mixin de tráfico, y su
docstring de arquitectura estaba desfasado (le faltaba `_MapUIMixin`). Y el docstring de
`test_traffic.py` seguía diciendo que los tests **congelan** el "PARCHE DE SEGURIDAD MATEMÁTICO"
del ACC, cuando **S21 lo eliminó** y reescribió esos 2 tests — corregido (contradecía al propio
comentario de la línea 45 del fichero).

**Verificación:** suite **680/680** tras cada paso (el split no añade tests: es estructura pura;
la red existente es la prueba). `ruff check .` + `ruff format --check .` limpios (102 ficheros;
`physics.py` necesitó reformato tras el rename, por longitudes de línea). `lfs-insim list` carga
los 4 insims. **3.9-safe:** `tuple[float, float]` va dentro de anotación con
`from __future__ import annotations` (nunca se evalúa) y FA102 pasa. Solo estructura y nombres,
**cero cambios de comportamiento → no requiere validación en LFS**.

**Próximo:** cerrar W3 — **índice espacial de VEHÍCULOS para el radar** (ahora en
`traffic/radar.py`; caracterizar el radar como unidad ANTES, red primero; reutilizar el
`SpatialHashGrid` de S23 como grid dinámico) + revisar el **FSM de adelantamiento**
(`traffic/overtake.py`, y eliminar `is_target_ahead_and_in_lane`, código muerto desde S24) +
**P4** (adelgazar `base.py`). **W4** (validación LFS del ceda-el-paso del ACC) sigue bloqueada por
`zones: 0`.

**Commits:** `453d61b` (split de `traffic.py`), `69fb092` (P7) + docs de cierre S27.

---

## S26 — 2026-07-10 — Fase 6 · W2: `lfs-insim init` con perfiles `--minimal`/`--full`

**Arranque:** protocolo de inicio; ya en `refactor/estabilizacion`, árbol limpio, `git pull`
"Already up to date" (tip `9633ed3`). Baseline verificado: suite **670/670**. Próximo paso
documentado: **W2** — `lfs-insim init` más robusto, con dos decisiones marcadas para confirmar con
el usuario (mecanismo de cierre y perfil por defecto).

**Decisiones (pregunta con recomendación explícita, MODUS_OPERANDI §6 — el usuario eligió las dos
recomendadas):**
- **Mecanismo de cierre = `self.client.stop()`** (no `TINY.CLOSE`). Razón: `client.stop()` es la
  parada limpia nativa del framework (cierra hilos/sockets, dispara `on_disconnect`, sin
  reconexión) y es reentrante-segura desde un handler (S09/S12). `TINY.CLOSE` le pediría a LFS
  cerrar el socket, pero con la **auto-reconexión P12 activa por defecto** el cliente lo detectaría
  como caída y **reconectaría** en vez de apagarse → semántica equivocada para un comando de cierre.
- **`--full` por defecto.** El objetivo de W2 es que el scaffold por defecto muestre los patrones
  correctos; quien quiera lo escueto usa `--minimal`.

**Qué se hizo — W2 (`cli.py`), CON RED PRIMERO:**
- **Red primero (`tests/test_cli.py`, +10 tests):** escritos y verificados en ROJO (helpers y flags
  aún inexistentes → error de colección) antes de implementar. Cubren: default = `--full`,
  `--minimal`, `--full` explícito, **mutua exclusión** (`--minimal --full` → `SystemExit`), clase
  CamelCase + manifiesto, guard de "ya existe", y —lo más valioso para un generador— **ambos
  templates `compile()` y `exec()` → subclase de `InSimApp`** (un scaffold con un fallo de sintaxis
  o import roto es un fallo de DX serio; este test lo caza).
- **Implementación:** flags mutuamente excluyentes `--full`/`--minimal` en el subparser de `init`
  (`set_defaults(profile="full")`); **registro extensible `_INIT_PROFILES`** (dict perfil→función
  de render) para admitir más perfiles en el futuro sin tocar `cmd_init`. Templates como **strings
  con centinelas** `__CLASSNAME__`/`__MODNAME__` rellenados por `str.replace` (no f-strings: evita
  escapar `{{}}` en ~90 líneas de código generado, y deja el template legible como Python normal).
- **`--minimal`** = el template anterior, **byte-idéntico** (extracción segura del comportamiento
  de hoy). **`--full`** = esqueleto de bot real: `set_isi_packet` con `ISF.LOCAL`; `TINY.NCN/NPL`
  en `on_connect`; tracking de admin por NCN (`self.admins[UCID] = packet.Admin == AD_NOAD.ADMIN`,
  limpiado en `CNL`) con `_is_admin(ucid)` (**UCID 0 = host local → siempre admin**); comando
  **`cerrar` admin-guarded** (`is_mso_required=True` → valida `packet.UCID`, luego
  `self.client.stop()`); **`on_reconnect`** que resetea `self.admins` (los NCN entrantes lo
  repueblan tras reconectar).
- **Guías cuadradas (parte de W5):** `quickstart.md` ahora usa `--minimal` explícito (así el código
  incrustado sigue siendo exacto) + nota que explica el `--full` por defecto; `README.md`,
  `CLAUDE.md` (comando) y `CHANGELOG.md` (bullet en *Añadido*) actualizados.

**Verificación:** suite **680/680** (670 + 10); `ruff check .` + `ruff format --check .` limpios
(ruff pasó el `_MINIMAL_TEMPLATE` a `"""` y dejó el `_FULL_TEMPLATE` en `'''` porque contiene un
docstring `"""` — correcto); `lfs-insim list` carga los 4 insims; render de `--full` eyeballeado
(los `�` en consola son el codepage de PowerShell, no el archivo: se escribe UTF-8 y los tests de
`exec` pasan). **3.9-safe:** `dict[int, bool]` es PEP 585 (ya usado en `test_insim`), sin uniones
PEP 604; FA102 pasa (CI valida 3.9 en el push). Solo CLI/tests/docs offline → **no requiere
validación en LFS**.

**Próximo:** **W3** (último ítem de Fase 6) — refactor interno de ai_control (P3 partir
`map_ui`/`map_recorder`/`traffic`; P4 `base.py`; P7 nombres de `behavior.py`) + índice espacial de
VEHÍCULOS para el radar plegado en `traffic.py` (caracterizar el radar como unidad ANTES, red
primero) + revisar el FSM de adelantamiento. **W4** (validación LFS del ceda-el-paso del ACC) sigue
bloqueada por `zones: 0`.

**Commits:** (pendiente al cierre) `feat(cli): W2 - lfs-insim init con perfiles --minimal/--full` +
docs de cierre S26.

---

## S25 — 2026-07-09 — Fase 6 · W5: sweep de API pública (jerarquía de excepciones)

**Arranque:** protocolo de inicio; ya en `refactor/estabilizacion`, árbol limpio. `git pull` trajo
desde otro equipo el cierre de S23 (índice espacial de geometría) y S24 (split de `utils.py`) + el
mapa South City ampliado → tip `2722573`. Baseline verificado: **671/671**. Próximo paso
documentado: **W5** (repaso final de la API pública antes del primer publish).

**Qué se hizo — W5 (sweep de exports / config / excepciones):**
- **Exports de `lfs_insim`** (`__version__` + 10 nombres + excepciones) y **`DEFAULT_CONFIG`** (20
  claves): revisados uno a uno contra la guía `api-publica.md` → cuadran, **sin cambios**.
- **Jerarquía de excepciones — hallazgo:** grep en todo el repo → **2 de las 7 no se lanzaban en
  ningún sitio** (ni core, ni insims, ni tests; solo se asertaban como subclases):
  `InSimProtocolError` e `InSimCommandError`. Se planteó al usuario **con recomendación explícita**;
  el usuario delegó la elección.

**Decisión de diseño — Opción 2 (quitar `InSimProtocolError`, mantener `InSimCommandError`):**
pre-publish no hay usuarios → quitar no es breaking real (solo una línea de CHANGELOG en una versión
sin publicar) y **re-añadir una excepción nunca es breaking** → la asimetría favorece recortar ahora
lo injustificable y añadir luego si hace falta. `InSimProtocolError` es lo injustificable: el
framework **estructuralmente no puede** lanzarla (P24: LFS no da feedback al rechazar un ISI/
protocolo) y su caso de "paquete inválido" ya lo cubre `InSimPacketError`. `InSimCommandError` se
queda: tipo de error coherente del **sistema de comandos público** (`CMDManager`/`Command`, con
`.command_name`), punto de extensión legítimo para que los autores de módulos lo lancen desde sus
handlers (aunque el core no lo lance).

**Cambios aplicados:**
- `exceptions.py`: quitada la clase `InSimProtocolError` + de `__all__`. **Traducido a inglés** de
  paso (MODUS_OPERANDI §5: módulo público del core tocado en la pasada pre-publish) + docstring de
  `InSimCommandError` aclarando que es para módulos.
- `__init__.py`: quitado el import y el `__all__` de `InSimProtocolError`.
- `test_exceptions.py`: quitado el import + el test de subclase de Protocol (−1 test).
- `docs/guia/api-publica.md`: diagrama de jerarquía actualizado + nota sobre quién lanza qué.
- `CHANGELOG.md`: bullet en **Eliminado** con el porqué.
- `CLAUDE.md:210` ya listaba exactamente las 5 subclases restantes (omitía Protocol) → queda
  **correcto sin tocar**. Las otras 3 guías no referenciaban Protocol.

**Regla de trabajo nueva (a petición del usuario):** al plantear una pregunta con opciones, **marcar
SIEMPRE la recomendada** y por qué. Registrada en `MODUS_OPERANDI §6`. (Motivo: en la pregunta de
esta sesión describí "mantener las dos" como cero-riesgo pero no marqué explícitamente la recomendada.)

**Verificación:** suite **670/670** (671 − 1); `ruff check .` + `ruff format --check .` limpios (96
archivos); smoke de import OK (`InSimProtocolError` fuera; `InSimError` + 5 subclases presentes;
`InSimCommandError` sigue siendo subclase); `lfs-insim list` carga los 4 insims. 3.9-seguro (solo
`__all__`/docstrings; CI valida 3.9 en el push). Solo API/tests/docs offline → **no requiere
validación en LFS**.

**Próximo:** **W2** — `lfs-insim init` con flag `--minimal`/`--full`. Al implementar, confirmar con
el usuario el mecanismo de cierre (`TINY.CLOSE` vs `client.stop()`) y si `--full` es el default.
**W4** (validación LFS del ceda-el-paso del ACC) sigue bloqueada por `zones: 0`.

**Commits:** (pendiente al cierre) `refactor(core): W5 - quita InSimProtocolError de la API pública`
+ docs de cierre S25.

---

## S24 — 2026-07-09 — Fase 6 · W1: split de `utils.py` (geometría de IA fuera del framework)

**Arranque:** protocolo de inicio; ya en `refactor/estabilizacion`, árbol limpio (sin mapas
pendientes que proteger). `git pull` "Already up to date" (tip `7936cca`, cierre S23). Próximo paso
documentado: Fase 6 · W1 (lo más irreversible, toca la API pública). Baseline verificado: suite
**642/642**, sin `utils.pyi` que regenerar.

**Qué se hizo — W1 (split de `utils.py`), CON RED PRIMERO (MODUS_OPERANDI §3):** se sacó de
`lfs_insim.utils` (API PÚBLICA del framework) la geometría/navegación **específica de la IA** y se
movió a `insims/ai_control/nav_modes/freeroam/geometry.py` (que ya existía con los helpers 2D de
zonas). **9 funciones movidas:** `calc_target_heading`, `get_heading_diff`, `calc_deviation_angle`,
`calc_dist_point_to_segment_3d`, `get_closest_node_index`, `determine_smart_spawn_index`,
`apply_antilag_window`, `evaluate_dynamic_capture`, `is_target_ahead_and_in_lane`. **Se quedan** en
el framework (primitivas reutilizables): comandos (`separate_*`, `Command`/`CMDManager`),
`strip_lfs_colors`/`TextColors`, `PIDController`, conversiones `lfs_*` y **`calc_dist_3d`** (decidido
en S23).

**Secuencia de extracción segura (dos fases):**
1. **Red primero.** Auditada la cobertura: solo 3 de las 9 tenían test directo (`get_heading_diff`,
   `calc_deviation_angle`, `calc_dist_point_to_segment_3d`, en `test_utils.py`); las otras 6 sin
   test (los grandes orquestadores que las usan están sin cubrir a propósito desde S18/S19). Nuevo
   `tests/insims/ai_control/test_geometry.py` (**44 tests**): las 3 movidas de `test_utils.py` + **29
   de caracterización nueva** para las 6, importando **desde el origen** (`lfs_insim.utils`) y
   verificado VERDE contra el código actual. Las 3 clases se retiraron de `test_utils.py` (dejando
   ahí lo genérico: `calc_dist_3d`, conversiones, PID, colores).
2. **El move.** Funciones copiadas **verbatim** a `geometry.py` (que ahora importa `calc_dist_3d` de
   `lfs_insim.utils` + `Any`); truncado de `utils.py` con script determinista (corta desde
   `def calc_target_heading` a EOF, conserva `calc_dist_3d` bajo `# CALCULOS`); `__all__` recortado.
   Imports actualizados en `physics.py`, `navigation.py`, `map_recorder.py`, `route/manager.py`
   (los 3 últimos ya importaban de `geometry.py` → sin aristas de import nuevas) + el import de
   `test_geometry.py` girado al destino. Sin ciclo: `geometry.py` solo depende de `math`, `typing`
   y `lfs_insim.utils` (no importa nada de ai_control).

**Quirk cazado por la red (caracterización, NO bug corregido):** `is_target_ahead_and_in_lane`,
cuando el coche está delante pero **fuera de carril** (lateral ≥ umbral), NO devuelve la distancia
lateral real — devuelve `0.0`. Solo reporta el lateral en detección peligrosa. Un test lo asertaba
mal (esperaba 5.0); corregido al comportamiento real y documentado el matiz.

**Hallazgo:** `is_target_ahead_and_in_lane` es **código muerto** — no se llama en ningún sitio del
repo. Se migró igual (con red) por seguridad de la extracción; candidata a **eliminación en W3** al
revisar el radar/FSM de adelantamiento. Señalado al usuario.

**W5 (parte ligada a W1, HECHA):** `docs/guia/api-publica.md` actualizada (la geometría de IA ya no
es API pública; en `utils` solo queda `calc_dist_3d`) + entrada **`[Rompe la API]`** en
`CHANGELOG.md`. Las otras 3 guías solo usan helpers que se quedan → sin cambios. **Pendiente de W5:**
el sweep final de exports de `lfs_insim` + `DEFAULT_CONFIG` + jerarquía de excepciones (próxima
sesión, antes de W2).

**Verificación:** suite **671** (642 baseline − 15 movidos de `test_utils` + 44 en `test_geometry` =
+29); `ruff check` + `ruff format --check` limpios en los 8 archivos tocados; `lfs-insim list` carga
los 4 insims. 3.9-seguro por construcción (`from __future__ import annotations` en `geometry.py`, sin
uniones PEP604 en runtime; `.venv39` no está en este equipo → lo valida el CI en el push). Solo
tests/refactor offline → **no requiere validación en LFS**.

**Decisión de diseño:** destino `nav_modes/freeroam/geometry.py` (lo fijaba el plan). Aunque estas
funciones las usan también `route/manager.py` y `physics.py` (fuera de freeroam), la ubicación es
**interna** (no API pública) → reversible sin coste post-publish; se siguió el plan sin bloquear.

**Próximo:** **W5 sweep** (exports/config/excepciones) → **W2** (`init` con `--minimal/--full`) →
**W3** (refactor interno + radar). **W4** (validación LFS del ceda-el-paso del ACC) sigue bloqueada
por `zones: 0`.

**Commits:** (pendiente al cierre) `refactor(ai_control): W1 - mover geometría de IA de utils a
geometry.py` (código + red + docs de API) + docs de cierre S24.

---

## S23 — 2026-07-08 — Fase 5: índice espacial de geometría (`get_location_context`)

**Arranque:** protocolo de inicio; ya en `refactor/estabilizacion`, árbol limpio (sin mapas
pendientes que proteger). `git pull` trajo **`9852f87 data(ai_control): amplia mapa freeroam de
South City`** desde otro equipo (nuevo `south_city.json` + render; solo datos, sin código). El
usuario pidió arrancar la **fase (a)** del ítem 6 (índice espacial para `get_location_context`).

**Contexto nuevo detectado al inspeccionar el mapa ampliado:** south_city ahora **128 roads /
11.086 nodos** (~8,5× lo que la auditoría S22 asumió, ~1.300) → el barrido O(nodos) de
`get_location_context` está en **~9,2 ms/consulta** (medido; confirma la extrapolación de S22).
Además, `zones: 0` → **sigue sin haber ninguna intersección**, así que la validación en LFS del
ceda-el-paso del ACC (pendiente de S21) **sigue bloqueada** (nada nuevo que probar).

**Qué se hizo (fase (a), geometría):**
- Nuevo módulo genérico y testeable `nav_modes/freeroam/spatial_grid.py` — `SpatialHashGrid`
  (hash grid uniforme 2D): `insert_point`/`insert_segment` (registra en las celdas del
  bounding-box del segmento), `ring_ids(px,py,k)` (marco Chebyshev de radio k) y
  `block_covers_all` (para terminar la expansión). Documentada la garantía de corrección (celda a
  Chebyshev m dista ≥ (m-1)·celda → parada segura cuando `best_dist < k·celda`).
- `map_recorder.py`: `_get_road_index` (build perezoso), `_get_closest_road` (expande anillos,
  reúne road_ids candidatos y delega en el `get_closest_geometry` existente **en orden de dict**),
  y wiring en el paso 1 de `get_location_context`. `road_node_idx` sin tocar.
- **Invalidación:** `_invalidate_road_index()` (pone el índice a `None`) en los **5 sitios
  discretos** de mutación de `self.roads`: 3×`clear` (nuevo/carga/borrado de mapa), commit de
  grabación de road (1296/1298), `del` (2350). Descubierto al auditar: la grabación **NO** muta
  roads en vivo (usa el buffer `current_recording`, que se vuelca solo al commit) y **no hay
  edición de nodos in-place** → el conjunto de mutaciones es pequeño y frío. El toggle `is_closed`
  NO invalida (geometría intacta; la consulta filtra las cerradas en caliente).

**Decisiones de diseño:**
1. **Fidelidad por construcción, no por reimplementación:** el grid solo acota el CONJUNTO de
   candidatos; la distancia 3D y el desempate `<` estricto los sigue calculando el
   `get_closest_geometry` de siempre, recorriendo `self.roads` en orden de dict → resultado
   **bit-idéntico** al barrido lineal (probado con fuzz). Se evitó así el riesgo de duplicar la
   matemática/desempate.
2. **Celda 20 m** (no 40 m como sugería la nota de S22). El "40 m para reutilizar en el radar" se
   debilita: la fase (b) usará un grid de vehículos **dinámico** (otra vida), no el estático. Como
   las consultas caen SOBRE la vía, celda pequeña = menos candidatos; benchmark: 30→20→10 m ≈
   11×→13×→18×, retorno decreciente + celdas pequeñas encarecen build/memoria y penalizan puntos
   lejanos → **20 m = balance (~13×, 9,2 ms → 0,70 ms/consulta)**.
3. **Solo geometría de ROADS** (no links/zonas): los roads son el 99% del coste (11.086 nodos vs
   55 links / 0 zonas); indexar solo roads captura ~todo el win y deja intacto el test de
   desempate de links (queda verde trivialmente). No mezclar comportamiento y estructura.

**Red (caracterización + equivalencia):** `test_spatial_grid.py` (12 unitarios del grid) +
`test_road_spatial_index.py` (**fuzz**: 8 semillas × 200 puntos × 2 modos ≈ 3200 comparaciones
bit-a-bit contra el barrido lineal, dentro/fuera de vía y con cerradas; + bordes: road de 1 nodo,
sin nodos, punto lejano, invalidación tras mutar). La red previa `test_map_recorder.py` (8) se
verificó VERDE antes de tocar y sigue verde.

**Verificación:** suite **642/642** (617 + 25). `ruff check` + `ruff format --check` limpios en
lo tocado. 3.9-seguro por construcción (`from __future__ import annotations`, `typing.*`, regla
FA102 pasa; `.venv39` no está en este equipo → lo valida el CI en el push). Solo tests/tooling
offline → **no requiere validación en LFS**.

**Planificación de rumbo pre-publish (misma sesión, con el usuario — SIN tocar código):** tras
cerrar el índice de geometría, se **re-secuenció** el plan. El refactor estructural de ai_control
(antes post-merge) se ADELANTA a antes de publicar, junto con: **(W1) split de `utils.py`** — sacar
la geometría/nav específica de ai_control del `utils` público del framework, porque es un cambio de
**API pública** y la única ventana limpia es antes del primer publish; **(W5)** repaso final de API
+ CHANGELOG; **(W2) `lfs-insim init` más robusto** con flag `--minimal`/`--full` (comando de cierre
por defecto, validación de permisos, `on_reconnect`, `TINY.NCN/NPL`); **(W3)** refactor interno
(P3/P4/P7) + el radar ex-6b **plegado** en el refactor de `traffic.py` (no urgente por auditoría, y
traffic.py se toca igual) + revisar FSM de adelantamiento. **Decisiones concretas:** `calc_dist_3d`
y `PIDController` se QUEDAN en el framework; init con flag min/full **extensible** a más perfiles;
**todo en la rama**, un solo merge a `main` cuando esté publish-ready + validado (W4), luego
publish. Detalle en PLAN § Fase 6 / § Merge y ESTADO § Próximo paso. De paso se **instaló y
autenticó `gh`** en este equipo (ZIP portable en `%LOCALAPPDATA%\Programs\gh`, reutilizando la
credencial de git no fue posible —token caduco—, login interactivo del usuario); sirvió para
verificar que el CI de S23 salió VERDE, incluido el job de **Python 3.9** (no había `.venv39` en
este equipo).

**Protección de mapas (incidente de mitad de sesión, instrucción permanente):** el usuario avisó de
cambios en el mapa sin commitear. Backup fuera del repo + validación de integridad del JSON + commit
`cb4471a data(ai_control): amplía mapa freeroam de South City` + push. South City creció a **176
roads / 12.987 nodos** (antes 128/11.086); sigue `zones: 0` → **W4 sigue bloqueada**.

**Commits:** `8771bc1` (índice espacial de geometría + red), `506bb51` (docs S23), `cb4471a` (mapa
South City ampliado) + el de este cierre (docs de planificación).

---

## S22 — 2026-07-07 — Fase 5: auditoría del hot-loop `on_ISP_MCI`

**Arranque:** protocolo de inicio; ya en `refactor/estabilizacion`, `git pull` "Already up to
date" (tip `0ff46fb`, cierre S21). Próximo paso documentado: auditar el hot-loop `on_ISP_MCI`.

**Incidente de arranque (mapas):** el usuario avisó de cambios sin commitear del render. Había
en el working tree `map_renderer.py` + `south_drift_1_rendered.png` + `test_rendered.png`
(continuación de S21: la leyenda de 1 columna ahora se **reparte** con `labelspacing` hasta el
alto del mapa cuando cabe holgada). Protegido según instrucción permanente: commit + push
(`b55a35f`). *(El `git status` de arranque los daba como limpios; aparecieron/afloraron
durante la sesión — commiteados igualmente para no perderlos.)*

**Qué se hizo — auditoría (análisis + medición real, sin LFS):** benchmark scratchpad con las
factorías del conftest. Resultados en `docs/dev/AUDITORIA_HOTLOOP.md`. **Veredicto: el loop
está SANO.** Puntos:
- **Frecuencia:** MCI ~100 Hz (paquetes ≤8 coches; trabajo por coche). Dos handlers por MCI
  (`um` → `ai_control`). Pero el trabajo caro NO va a 100 Hz: `_update_traffic_behavior`
  **auto-regula el radar** (`_radar_interval = 0.1 + random(0..0.05)` → ~7–10 Hz/IA) con jitter
  que **desincroniza** a las IAs; la nav por tick solo hace tracking topológico incremental.
- **Coste medido:** `um.on_ISP_MCI` ≈1.2 µs/coche; física barata; radar `_scan_lane_ahead`
  ≈1.5 µs/vehículo (O(N) por IA → **O(N²)** global); `get_location_context` **56 µs (50 nodos)
  → ~1.0 ms (1300 nodos ≈ south_city)**. Peor tick (16 IAs) ≈0.6 ms ≪ 10 ms → holgura hasta
  ~16–20 IAs. La caché de contexto de humanos (`_radar_human_cache`) vive en la app y es
  **compartida** entre IAs (un humano se localiza 1 vez/0.1 s en total).
- **Hallazgos (robustez/escalado, NO urgencias):** (1) `get_location_context` O(mapa entero),
  frágil si algo lo llama por-tick — cura de fondo = índice espacial; (2) radar O(N²); (3)
  `Coordinates.x_m/y_m/z_m` y `Speed.speed_kmh` **recalculan la conversión en cada acceso**
  (~28% del tiempo del radar en el profile) → cachear a atributo plano, candidato a Fase 6.

**Red primero + limpieza:** nuevo `tests/insims/ai_control/test_map_recorder.py` (**8 tests**)
que caracteriza `get_location_context` (road más cercano, `road_node_idx`, enlace sobre
`road_links` ∪ `lateral_links`, **desempate por orden de iteración**, `ignore_closed_roads`,
mapa vacío). Verificado VERDE contra el código actual ANTES de tocar. Luego, cambio menor
blindado por esa red: `get_location_context` deja de reconstruir el dict fusionado
`{**road_links, **lateral_links}` en cada llamada → `itertools.chain(road_links.items(),
lateral_links.items())` (mismo orden —las claves `'A->B'` vs `'A<<>>B'` nunca colisionan— y
mismo desempate con `<` estricto). **Medido aislado: ahorro ~0.2 µs/llamada → despreciable**
(el coste dominante son las distancias sobre nodos, sin tocar); se mantiene por limpieza
(elimina una allocation), no por perf.

**Decisión de diseño:** el fix de fondo (índice espacial para geometría + radar) NO se hizo en
esta sesión: es cambio de estructura + comportamiento potencial → va en el siguiente ítem del
plan ("consolidar radar/geometría"), a diseñar con el usuario y con más caracterización (falta
el radar como unidad). La auditoría concluye que no hay urgencia de rendimiento.

**Verificación:** suite **617/617** (609 + 8). `ruff check` + `ruff format --check` limpios en
los archivos tocados. Solo tests/tooling offline → **no requiere validación en LFS**.

**Commits:** `b55a35f` (render, protección de mapas) + el de la auditoría (red + limpieza +
docs de cierre).

---

## S21 — 2026-07-07 — Fase 5: sustitución del "PARCHE DE SEGURIDAD MATEMÁTICO" del ACC

**Arranque:** protocolo de inicio; ya en `refactor/estabilizacion`, `git pull` "Already up to
date" (tip `ffc5c7d`, cierre S20 = diagnóstico P25). Repo limpio, sin mapas freeroam sin
commitear que proteger. Próximo paso documentado: revisar/sustituir el PARCHE del ACC.

**Decisión con el usuario:** confirmada la **Opción A** del diagnóstico P25 (fix matemático
localizado, SIN mover los `min`/`max` del llamador), frente a B (A + config) y C (modelo
cinemático de frenado).

**Qué se hizo — `_apply_adaptive_cruise_control` (`traffic.py`), CON LA RED PUESTA (red primero):**
eliminado el "PARCHE DE SEGURIDAD MATEMÁTICO" que **reescribía en silencio** los `min`/`max` del
modelo time-gap del llamador (`min = max(critical+2, min)`; `max = max(min+5, max)`), inflándolos
con constantes mágicas → la IA frenaba antes/distinto de lo pedido.

- **Suelo duro de parada explícito** (`if closest_dist_m <= 5: return 0.0`), separado de la
  matemática de zonas.
- `critical = max(5, min·0.5)` (**se mantiene el suelo**), ratios de naranja y amarilla
  **acotados a [0,1]** y ambos denominadores **blindados con ε** → imposible el ZeroDivisionError
  para cualquier input.
- Números mágicos → **constantes con nombre**: `PARADA_ABSOLUTA_M`, `CRITICAL_FRACTION`,
  `ANTICREEP_KMH`, `EPSILON`.

**Decisión de diseño (matiz sobre la letra de A):** el texto de A proponía `critical = min·0.5`
pelado (sin suelo). Se mantuvo `max(5, min·0.5)` porque: (1) **continuidad** — con el suelo la
rampa naranja arranca de 0 justo en el umbral rojo; sin él `critical < 5` produce un **salto de
velocidad discontinuo** en dist=5 m, justo donde entran los `min≈5` reales a baja velocidad;
(2) **cambio mínimo** — así la conducta solo cambia en la franja que el parche distorsionaba
(`min<7` ∪ `max<min+5`), dejando idénticos los 8 tests de setup limpio (min=10/20). De paso se
comprobó que el **div/0 que el parche decía tapar era inalcanzable**: la zona roja guarda el
denominador naranja (naranja solo se evalúa con `critical < dist ≤ min` ⇒ `min > critical` ⇒
denom > 0). El parche solo distorsionaba, no protegía.

**Red primero:** los 2 tests que congelaban el parche (`test_parche_empuja_*`) reescritos al
comportamiento sin parche (rojo→verde: 15→34.44 y 46→50), renombrados a
`test_min_pequeno_no_se_reescribe_cae_en_amarilla` / `test_max_menor_que_min_no_se_reescribe`;
+ 2 tests de robustez nuevos (`test_min_en_el_suelo_no_lanza`, `test_max_igual_a_min_no_lanza`).
Verificado ROJO antes del fix (4 fallos por el parche) y VERDE después.

**Verificación:** suite **609/609** (607 + 2). `ruff check .` + `ruff format --check .` limpios
en todo el repo (el formatter reajustó una línea larga del ratio, cero comportamiento).
`lfs-insim list` OK. Los otros 2 call-sites del ACC (overtake `:468`, intersección `:645`) se
benefician igual.

**PARCIALMENTE validado en LFS (S21):** el usuario confirma que el **frenado/seguimiento funciona
bien**. El **ceda el paso en intersección queda SIN CONFIRMAR**: no tiene ninguna intersección
creada, así que ese call-site (`traffic.py:645`) no se ha podido probar. Reconfirmar cuando exista.

**Mejora extra (no planeada) — render del mapa (`map_renderer.py`):** a mitad de sesión el usuario
pidió arreglar el renderer, que le limitaba para editar mapas grandes. Problemas del render viejo
(patentes en `south_city_rendered.png`, ~65 roads): (1) leyenda de UNA columna que aplastaba el
mapa hasta dejarlo diminuto, agravado por `set_aspect(adjustable="datalim")` que expandía el rango
X de forma fantasma; (2) grosores FIJOS en puntos → roads paralelos solapados en un borrón; (3)
roadlinks como cruces `X` gruesas cian tapando la vista. Solución en un solo archivo:

- **Encuadre a los datos:** `adjustable="box"` + `xlim/ylim` con margen calculado sobre los bounds
  reales → el mapa llena el eje (se acabó el agrandado fantasma del eje X).
- **Grosores proporcionales** a la extensión: `road_lw = clamp(1300/span, 0.6, 3.0)`,
  `link_lw = 0.55·road_lw` (los links SIEMPRE más finos que los roads, para que se vean menos).
- **RoadLinks = línea cian fina CONTINUA** (como los laterales pero sólida), conservando su cian.
- **Leyenda multi-columna** (`ncol = ceil(n/30)`) y **ordenada alfabéticamente**, fuente 7 → su
  alto ≈ el del mapa y aprovecha el espacio. Al ordenar, los carriles `X_a`/`X_b` quedan contiguos.
- **Paleta de roads que EXCLUYE** rojo (zonas), gris (laterales) y cian (roadlinks) para no
  confundir un road con esos elementos semánticos. Quitados los marcadores por-nodo (ensuciaban).

Renders de `south_city` y `south_drift_1` regenerados y **validados visualmente con el usuario**.
Tooling offline (no toca el runtime de conducción) → no requiere validación en LFS.

**Refinamiento de la leyenda (petición del usuario tras ver el primer resultado):** que **cada
columna baje EXACTAMENTE lo que baja el mapa** y solo entonces se abra la siguiente (antes el
corte era fijo, `max_rows=30`, dejando columnas más cortas que el mapa). Ahora el nº de filas por
columna se **mide sobre un render de sondeo** (alto del recuadro del mapa ÷ alto de una entrada de
leyenda; ratio independiente del dpi) en vez de estimarse. Como matplotlib **equilibra** las
columnas por su cuenta, se **fuerza el llenado columna-a-columna** rellenando la última con
entradas invisibles (`Line2D(color="none")`, label `" "`) hasta `ncol·filas_por_columna`. Resultado
validado: `south_city` → 2 columnas (la 1ª llena hasta el fondo del mapa, la 2ª con el resto
arriba); `south_drift_1` → 1 columna (sus ~22 entradas caben en el alto). Commit `9a9f4eb`.

**Commits:** `fix(ai_control): sustituir el PARCHE del ACC por matemática robusta` (código + tests),
`docs(dev): S21 - ...` (docs de cierre), `docs(dev): S21 - validación parcial del fix del ACC en
LFS`, y `5dd0740 feat(ai_control): mejorar el render del mapa (leyenda, grosores, roadlinks)`.

---

## S20 — 2026-07-06 — Fase 5: fix de reconexión de `ai_control`

**Arranque:** protocolo de inicio; ya en `refactor/estabilizacion`, `git pull` "Already up
to date" (tip `3b6db5d`, cierre S19). Repo limpio al arrancar. **Incidente de mapas (a
mitad de sesión):** el usuario avisó de cambios manuales en el mapa freeroam de South City
sin commitear → protegidos según protocolo permanente ANTES de seguir: respaldo fuera del
repo (`C:\Users\Adrian\backups\AP_LFS_InSim_maps\2026-07-06_S20`) + commit `2b2bc85`
(`data(ai_control): ampliar el mapa freeroam de South City`, +21251/-325 en `south_city.json`
+ render) + push. **Solo se commitearon los 2 ficheros de mapa** (`git add` selectivo); el
refactor en curso NO se arrastró.

**Qué se hizo — `ai_control` consciente de la reconexión (P12), CON LA RED PUESTA
(test primero):** el punto de entrada verificado en S19 se confirmó y se amplió: había
**DOS** bucles daemon persistentes con el mismo defecto, no uno: `_run_test_freeroam`
(gestor freeroam) **y `_test`** (cargador masivo de rutas, lanzado por `_test_routes`). Ambos
eran `while True` con `time.sleep` que morían con `InSimConnectionError` al enviar sobre un
socket caído (traceback a stderr, S10) e ignoraban toda señal de parada (el flag
`_is_freeroam_loop_running` no se consultaba en el bucle → ni "Detener" en la UI los paraba).

- **Señal de parada compartida** (`threading.Event`) que ambos bucles consultan en cada
  espera (`stop.wait(t)` en vez de `time.sleep(t)`, y `while not stop.is_set()`), envuelto en
  `try/except InSimConnectionError` para cortar limpio si el socket cae mid-envío. Infra nueva
  en `_CommandsMixin`: `_init_traffic_state` (llamado desde `AIControl.__init__`),
  `_start_traffic_loop` (lanza + rastrea el hilo, deja la señal en verde) y
  `_stop_traffic_loops` (set + join corto de todos los hilos, idempotente, no hace join a sí
  mismo). `_test_routes`/`_test_freeroam` pasan a usar `_start_traffic_loop`.
- **`AIControl.on_disconnect`** (override nuevo): `_stop_traffic_loops()` → los bucles paran
  limpiamente al perder la conexión.
- **`AIControl.on_reconnect`** (override nuevo): `_stop_traffic_loops()` + `_target_freeroam_count
  = 0` + limpia las cachés de radar por PLID (`_radar_human_cache` / `_target_lane_human_cache`).
  **Decisión de diseño:** NO se reanuda el tráfico automático — reanudarlo arrastraría el UCID
  viejo capturado por el hilo → "La AI X no es una de tus AI's". El usuario lo reinicia si quiere.
- **De propina (mismo root cause):** la UI "Detener" (`map_ui.py`, cid 116) ahora llama a
  `_stop_traffic_loops()` → **para de verdad** (antes solo ponía el flag a False, que el bucle
  no miraba). Stub cross-mixin de `_stop_traffic_loops` en `base.py`. Import muerto `time`
  eliminado de `commands.py`.

**Red primero:** `tests/insims/ai_control/test_reconexion.py`, **6 tests** escritos en ROJO
(fallaban por falta de la API nueva) y luego en verde: on_disconnect para el freeroam, para el
cargador de rutas, corte limpio ante `InSimConnectionError` (sin propagar, flag a False por el
`finally`), on_reconnect resetea estado, on_reconnect no deja vivo un gestor con el UCID viejo,
y la parada es pronta (< 2 s, no espera el sleep de 5 s).

**Verificación:** suite **607/607** (601 + 6). `ruff check .` + `ruff format --check .` limpios.
`lfs-insim list` OK (los 4 InSims cargan). **✅ VALIDADO por el usuario en LFS: "todo funciona
perfectamente"** (se probó: matar/levantar LFS con el gestor corriendo → parada limpia sin
traceback y sin recrear IAs solo; "Detener" de la pestaña Run para de verdad; `.route test`
también para al caer la conexión).

**Próximo:** revisar/sustituir el "PARCHE DE SEGURIDAD MATEMÁTICO" (ya congelado por tests) y
auditar el hot-loop `on_ISP_MCI`.

**Commits:** `2b2bc85` (mapa, protección), `fix(ai_control): reconexión — parar los bucles de
tráfico daemon` (código + 6 tests) y el commit de docs de cierre.

---

## S19 — 2026-07-06 — Fase 5: caracterización de `traffic.py`

**Arranque:** protocolo de inicio; ya en `refactor/estabilizacion`, `git pull` "Already up
to date" (tip `7137949`, cierre S18). Repo limpio, sin mapas freeroam sin commitear que
proteger. Próximo paso documentado: caracterizar `traffic.py`.

**Qué se hizo — red de seguridad de `traffic.py`** (`tests/insims/ai_control/test_traffic.py`,
**81 tests**, escritos por bloques y verificados en verde en cada uno). Reutiliza los
fixtures de `conftest.py` (grafo + telemetría sintéticos). Cubre la lógica DETERMINISTA:

- **ACC de 3 zonas** `_apply_adaptive_cruise_control` (roja/naranja/amarilla/fuera de rango),
  **incluido su "PARCHE DE SEGURIDAD MATEMÁTICO"** (dos tests fijan cómo empuja `min_dist` y
  `max_dist` hacia arriba). Se CONGELA el comportamiento actual; la sustitución sigue
  pendiente en PLAN §Fase 5.
- **Matemática de adelantamiento:** `_estimate_overtake_distance` (delta ≤ 0.1 m/s → `inf`),
  `_get_relative_dist_to_cover` (lógica de convoy + **ordena su lista de entrada in-place**,
  documentado), `_calc_path_length` (2D, ignora Z; índice negativo → longitud completa),
  `_get_lookahead_point` (adelante/reverse/lista vacía).
- **Geometría de zonas:** `_get_zone_centroid`, `_is_point_in_zone`, `_get_dist_to_zone_edge`
  con los 4 casos por nº de nodos (vacía / círculo / cápsula / polígono), y
  `_is_priority_vehicle_active_at_zone` (dentro / lejos-para-su-velocidad / cerca-apuntando /
  cerca-alejándose). Helper local `_zone` + heading LFS 0=+Y (Norte), 32768=-Y (Sur).
- **Selección de carril** `_find_valid_overtake_lane` (RHT→izquierda, LHT→derecha, vía
  `_get_indicator_to_use` de navigation) y **helpers del FSM** `_trigger_return` /
  `_finish_overtake` (mutaciones de estado del `mode`).
- **Radar:** `_scan_lane_ahead` (14 tests: mismo segmento, índice detrás, empate de distancia
  al nodo con desempate por PLID, producto cruzado para índices cercanos y su bypass para
  índices lejanos, `max_dist`, orden, coche en el próximo RoadLink), `_scan_target_lane` y
  `_scan_return_lane_gap` (separa delante/detrás). Y el guardián `_get_available_overtake_distance`
  / `_is_lane_safe_to_overtake` (salida, límite físico, tráfico mismo sentido y contrario).

**Decisión de diseño (clave):** el radar se ejercita **solo con vehículos IA**. La rama de IA
lee la topología directa de `extra['aic'].active_mode` (determinista); la de humanos usa
`time.time()` + `get_location_context`. Usar IAs evita el no-determinismo temporal y aísla
la lógica de filtrado, que es lo valioso. Detalle de fixtures aprendido: un "otro" AI sin
`active_mode` (o con `extra['aic']` ausente) NO es detectable — cae en la rama de humano; por
eso los helpers de radar (`_place_ai`) siempre adjuntan un `FreeroamMode` con `current_id` /
`current_road_id` según el escáner.

**Sin cubrir a propósito:** el orquestador `_update_traffic_behavior` (Sense-Think-Act con
`time.time()` y mutación masiva de estado), mismo criterio que los métodos gordos de
`navigation.py`. Con esto, la **red de caracterización de Fase 5 queda COMPLETA** (física +
navegación + tráfico).

**Verificación:** suite **601/601** (520 + 81). `ruff check .` y `ruff format --check .`
limpios en todo el repo (el archivo nuevo se pasó por `ruff format`). mypy no aplica (solo
tests). **No requiere validación en LFS:** cero cambios de runtime.

**Próximo:** el **fix de reconexión de `ai_control`** (ítem de S10), ahora ya CON LA RED
PUESTA; después, revisar el "PARCHE" (ya congelado) y auditar el hot-loop `on_ISP_MCI`.

**Commits:** `test(ai_control): caracterización de traffic.py (81 tests)` + el commit de
docs de cierre de esta sesión.

---

## S18 — 2026-07-06 — Fase 5: caracterización de `navigation.py` + fixture de grafo

**Arranque:** `git pull` al iniciar trajo un bloque grande desde el otro equipo. Por un
lado, el **cierre completo de Fases 1-4** (S14-S17: metadata del paquete, subcomandos del
CLI, ruff+CI+mypy, `docs/guia/`, CHANGELOG, PyPI preparado sin publicar). Por otro,
**trabajo de Fase 5 sin documentar** en el commit `9605dc6 "mapas (ignorar)"`, que mezcló
mapas freeroam con tests: la infra de fixtures sin LFS (`conftest.py`) y la caracterización
de `physics.py` (`test_physics.py`, 20 tests). Repo limpio; sin mapas sin commitear que
proteger. Suite de partida **489/489**.

**Reconciliación de contexto (con el usuario):** los `.md` decían "Fase 5 sin arrancar",
falso. Actualizados PLAN/ESTADO para reflejar que fixtures (parcial) + física ya estaban.
Decisión de rumbo: seguir el orden acordado de Fase 5 (red de seguridad primero) → como
física ya estaba, el siguiente eslabón es `navigation.py`.

**Qué se hizo — red de seguridad de `navigation.py`:**
- **Fixture de grafo sintético** añadido a `conftest.py` (lo que el docstring prometía y
  física no necesitó): factorías `make_road` / `make_road_link` / `make_lateral_link` +
  `populate_graph`, que pueblan un `MapRecorder` REAL con RoadSegment/RoadLink/LateralLink
  **keyeados IGUAL que producción** (roads por `road_id`; links por su propiedad `.link_id`,
  p. ej. `"R1->R2"`, `"R1<<>>R3"` — verificado en `map_recorder.py`). Coordenadas en metros
  reutilizando `make_coords` (exacto: 1 m = 65536 units).
- **`test_navigation.py`** — 31 tests de caracterización de la lógica DETERMINISTA:
  - Geometría pura: `_get_closest_node_index` (nodo más cercano; 2D, empate→índice menor,
    lista vacía→(0, inf)), `_get_indicator_to_use` (producto cruzado→LEFT/RIGHT/OFF, con el
    signo ACTUAL congelado), `_is_link_reachable_ahead` (alcance espacial + culling).
  - Planificación de enlaces: `_get_raw_candidates` (RoadLinks salientes + LatLinks según
    `allow_*`, excluye `made_to_overtake`), `_calculate_next_link` (filtros de destino
    abierto/alcanzable + clasificación válida/retorno) y `_plan_next_link`.
  - El único no-determinismo (`random.choice` cuando hay varias válidas) se congela
    parcheando `navigation.random` y asertando el CONJUNTO de candidatos.
  - Los grandes métodos de integración con tiempo/estado (`_update_freeroam_navigation`,
    `_get_radar_speed_limit`, `_update_route_navigation`) quedan SIN cubrir a propósito
    (usan `time.time()` y mutan mucho estado).

**Hallazgo caracterizado (NO es bug):** `_is_link_reachable_ahead` (usado por
`_calculate_next_link`, `max_dist=8`) hace un culling rápido de radio ~38 m medido desde el
nodo de INICIO de cada segmento → con vías de nodos muy separados un enlace alcanzable se
descartaría. Las vías reales se graban con nodos densos, así que en producción no ocurre; los
tests de planificación usan vías a 10 m (helper `_straight_y`) y lo dejan documentado. El
primer intento de tests (nodos a 50 m) lo cazó en rojo → confirma que la red funciona.

**Fix de higiene (CI):** `test_physics.py` traía un import muerto (`AIInputVal as AIV`, F401)
que dejaba el `ruff check` del CI en rojo en el tip. Eliminado. Llegó con `9605dc6`.

**Verificación:** suite **520/520** (489 + 31). `ruff check .` y `ruff format --check .`
limpios en TODO el repo (hubo que instalar **ruff 0.15.20** en `.venv`, que no lo tenía —
el pin del proyecto es `>=0.15,<0.16`). mypy no aplica (solo se tocan tests).

**No requiere validación en LFS:** solo tests + docs; cero cambios de runtime.

**Próximo:** seguir la red de seguridad con `traffic.py` (radar/`_scan_lane_ahead`, ACC, FSM
de adelantamiento), reutilizando el fixture de grafo; luego el fix de reconexión de
`ai_control` (ítem de S10), ya CON LA RED PUESTA.

**Commits:** `818c832` (tests navigation + fixture de grafo), `1efc962` (fix F401 en
test_physics) y el commit de docs de cierre de esta sesión.

---

## S17 — 2026-07-04 — Fase 4 COMPLETADA: docs de usuario + CHANGELOG + PyPI preparado

**Arranque:** repo limpio y sincronizado (HEAD `8398cde`, cierre S16); CI en
verde. Sin mapas freeroam sin commitear que proteger. No se corrió la suite (el
trabajo es solo documentación; cero cambios de runtime).

**Decisión de estructura (con el usuario):** **README slim + `docs/guia/`** (frente
a un README único ampliado). El README queda como landing page con enlaces; el
grueso va a páginas separadas.

**Qué se hizo (penúltimo ítem de Fase 4 — docs de usuario):** 4 guías nuevas en
`docs/guia/`, todas en español y **verificadas leyendo el código fuente** (no
copiando el README viejo, que estaba obsoleto):

- **`quickstart.md`** — "tu primer InSim en 5 min": instalar → copiar
  `settings_local.example.py` y poner `admin_pass` → `/insim 29999` en LFS →
  `lfs-insim init` → módulo generado (idéntico a la plantilla real) → `run` →
  `!<modulo> hola` en el chat. Con la nota del `admin_pass` (pista de ISI
  rechazado).
- **`modulos-y-deps.md`** — anatomía del módulo, manifiesto `insim.json` (tabla
  de campos), **cómo el loader localiza la clase** (primera subclase de
  `InSimApp`, no por nombre), dependencias (`insim_dependencies` con constraints
  de versión, orden de carga = orden de dispatch, `get_insim`, fail-fast P20),
  estado compartido vía `.extra`, comandos con CMDManager (args tipados,
  `is_mso_required`), mixins con el truco `TYPE_CHECKING`.
- **`api-publica.md`** — puntos de import; exports de `lfs_insim`; superficie de
  `InSimApp` (atributos de clase/instancia, hooks, métodos); **TODAS las claves
  de `DEFAULT_CONFIG` con sus defaults reales** (tablas por grupo); las **7**
  excepciones; los **21** nombres de `utils` agrupados; paquetes y enums.
- **`arquitectura.md`** — composición (un cliente, N apps), tabla de objetos del
  core, ciclo de vida del paquete (IO → cola → worker), contrato de hilos (P2),
  política de errores de handlers, envío siempre-TCP, auto-reconexión (P12 +
  provisional P24), config en dos capas. **Reemplaza la sección obsoleta del
  README.**

**README reducido a landing page** + tabla de enlaces a las 4 guías (arriba del
todo), CLI, módulos incluidos, telemetría OutSim (compacta, sin guía dedicada),
protocolo y tests. Enlaces internos verificados (archivos + anclas GitHub).

**Erratas del README viejo corregidas (eran FALSAS, no solo incompletas):**
- Sección Arquitectura describía el patrón **"coup d'état" / Master / `modules[]`
  / `insim_packet_io.py`** — TODO eliminado en Fase 2 (composición P11, transporte
  P13). Verificado en el código: `self.apps`, `insim_transport.py`, sin master.
- Afirmaba que los stubs `.pyi` **se generan por git hook en cada commit** —
  falso (el hook es un no-op deshabilitado desde S15). Se quita la sección; la
  regeneración es `lfs-insim stubs` (ya en la sección CLI).
- `insim_name` default documentado como `"InSimApp"`; el real es `"LFS-InSim"`.
- Jerarquía de excepciones incompleta (faltaba `InSimProtocolError`; son 7).
- "LFS v0.7F" → "0.7F o superior (probado en 0.8C)".
- Recuento de tutoriales 72 → 73 (`recibir/` pasó de 42 a 43).

**Corregido de paso CLAUDE.md** (§ insim.json manifest schema): decía que el
loader "looks for a class whose name matches the module's name in CamelCase
(ai_control → AiControl)". La regla REAL (leída en `insim_loader.py:244-263`) es
que instancia la **primera subclase de `InSimApp`** que encuentra en el
entry_point — el nombre no la localiza (por eso `AIControl` funciona). Corregido
a la descripción por herencia + "una sola clase InSimApp por entry point".

**La plantilla de `lfs-insim init` revisada:** al día. Genera un `main.py` que ya
usa la API pública (`from lfs_insim import InSimApp`, `.packets`, `.insim_enums`,
`.utils`) y CMDManager fluido con `.submit()`. No hubo que tocarla.

**No requiere validación en LFS:** solo documentación (`.md`), cero cambios de
runtime. Suite heredada 469/469 intacta.

**Segundo bloque (misma sesión) — CHANGELOG.md + convención semver (último ítem
de contenido de Fase 4):** `CHANGELOG.md` en formato Keep a Changelog (español,
coherente con README y `docs/guia/`) + sección de convención de versionado.

- **Historial de versiones verificado con git antes de escribir** (para no
  inventar): la versión ha sido `0.2.0` desde el "Starting point" (`775636c`,
  2026-04-21); `git log -S'0.1.0'` no devuelve nada (**nunca hubo 0.1.0**);
  `git tag -l` vacío (sin releases). → El changelog documenta la 0.2.0 como
  **primera versión en preparación**: sección `## [Sin publicar] — v0.2.0 en
  preparación` (sin fecha hasta el release real; al cortarla pasa a
  `[0.2.0] - fecha`), recogiendo todo el refactor por categorías
  (Añadido/Cambiado/Obsoleto/Eliminado/Corregido), con los cambios que **rompen
  la API** marcados (composición, dispatch, etc.).
- **Convención semver** documentada: 0.x puede romper en MINOR; fuente única de
  versión en `lfs_insim.__version__` + recordatorio de reinstalar editable tras
  un bump (el test de S14 lo exige).
- **`pyproject.toml`:** URL `Changelog` en `[project.urls]` (apunta a
  `blob/main/CHANGELOG.md` — correcto porque el publish a PyPI es post-merge).
  Enlace al CHANGELOG en el README.
- **Verificado:** tests de packaging/CLI (`test_cli.py` + `test_api_publica.py`)
  **23/23** tras tocar pyproject (el contrato de `[project.scripts]` y el de
  versión única siguen verdes).

**Tercer bloque (misma sesión) — PyPI preparado sin publicar (último ítem de
Fase 4; el usuario eligió "preparar sí, disparar no"):**

- **Build local validado (seguro, no sube nada):** `python -m build` produce
  `lfs_insim-0.2.0.tar.gz` (sdist) y `lfs_insim-0.2.0-py3-none-any.whl` (wheel
  puro); **`twine check` PASSED** en ambos. Inspeccionado el contenido: el wheel
  lleva el paquete completo + stubs `.pyi` + LICENSE + METADATA; el sdist lleva
  src/tests/README/LICENSE/pyproject. Artefactos borrados tras validar (`dist/`
  está gitignorado).
- **Extra `[publish]`** en pyproject (`build`, `twine`) para el ensayo local
  reproducible (`pip install -e ".[publish]"`).
- **Workflow `.github/workflows/publish.yml`** con **Trusted Publishing (OIDC, sin
  tokens)**, deliberadamente **inerte**: solo `workflow_dispatch`→TestPyPI y
  `release: published`→PyPI, y —como GitHub solo ofrece estos disparadores desde
  la rama por defecto— **no operable hasta el merge a `main`**. Jobs: build (con
  `twine check`) + testpypi/pypi condicionados por evento, con environments
  `testpypi`/`pypi`.
- **Runbook `docs/dev/PUBLICACION.md`** (+ fila en `00_INDEX.md`): ensayo local en
  TestPyPI (comandos exactos, necesita cuenta+token del usuario), configurar
  trusted publishers en (Test)PyPI, publish real post-merge (GitHub Release →
  PyPI), recordatorios semver. URL `Changelog` ya estaba en `[project.urls]`.
- **Lo que NO hago yo:** el upload real —incluido el ensayo en TestPyPI— lo lanza
  el usuario con sus credenciales (acción pública; Claude no las tiene). Dejo los
  comandos listos en la doc.

**FASE 4 COMPLETADA.** Fases 1-4 hechas: core estabilizado, documentado y
empaquetado. Cero cambios de runtime en toda la sesión S17 (solo docs, packaging
y CI). Suite heredada 469/469 intacta; tests de packaging/CLI 23/23.

**Rumbo decidido con el usuario (cierre de S17): seguir con FASE 5 (`ai_control`).**
Matices acordados: (1) el framework/core (Fases 1-4) ya es publicable, pero
`ai_control` es el escaparate y se pule antes para un primer release cohesionado
(sin prisa); (2) **el merge a `main` se hará cuando Fase 5 esté terminada +
validada en LFS — NO se espera a Fase 6** (refactor estructural de ai_control,
cosmético, va después del merge en `main`); (3) el publish a PyPI se dispara tras
el merge. **Arranque de Fase 5 acordado:** red de seguridad primero (fixtures
sintéticos + tests de caracterización de navigation/traffic/physics), luego el fix
de reconexión de ai_control. Registrado en ESTADO_ACTUAL § Fase activa / § Próximo
paso y en PLAN § Fase 5 / § Merge.

**Próxima sesión:** arrancar Fase 5 por la red de seguridad (ver ESTADO_ACTUAL
§ Próximo paso).

---

## S16 — 2026-07-04 — Fase 4: ruff (format+lint) + CI + mypy gradual

**Arranque:** repo limpio y sincronizado (HEAD `f3b4a6b`, cierre S15); suite
heredada 469/469 antes de tocar. Sin mapas freeroam sin commitear que proteger.

**Decisiones al arrancar (con el usuario):** line-length **88** (mi
recomendación; medí el core: 95,8% de las líneas ya ≤79 y solo 105 superan 88
→ pasada de format barata) y reglas de lint **conservadoras E, F, I, W** (se
ampliará con UP/B/C4/SIM en pasadas futuras).

**Qué se hizo (el bloque grande de Fase 4, en 6 commits):**

- **ruff format** (`a3bea56`, commit propio): pasada mecánica sobre 79 archivos
  (comillas dobles, línea en blanco tras docstrings, envoltura de firmas/llamadas
  largas, comas finales). Cero comportamiento — los 469 tests son la red. Config
  de ruff en commit aparte (`4ec9db1`); `.git-blame-ignore-revs` con el hash del
  format (`5564530`) para que `git blame` no apunte al reformateo masivo (GitHub
  lo usa solo; en local `git config blame.ignoreRevsFile .git-blame-ignore-revs`).
- **ruff lint** (`c5a736b`): 793 hallazgos. Autofix seguro (137): orden de
  imports (I001), imports sin usar (F401, incluido un `import math` duplicado en
  utils y un `insim_enums`/`field` muertos), f-strings sin placeholder (F541). A
  mano (5): dead vars `parts`/`fake` (F841), bare-except → Exception (E722), loop
  var `l`→`ln` (E741), noqa E402 en el import diferido de generate_stubs (va tras
  `sys.path.insert`). Ignores acotados: **E501** (el formatter es el dueño del
  ancho); per-file para los star-imports intencionales (insims + packets/__init__
  + packets/maps, guiados por __all__), imports no-top (E402) y nombres de una
  letra del protocolo (insim_enums I/O) o de código insim pendiente de refactor.
- **CI** (`838edac`): `.github/workflows/ci.yml` con jobs **lint** (ruff check +
  format --check, ruff pineado a `0.15.*`) y **test** (pytest en matriz Python
  3.9/3.11/3.13 en ubuntu + Windows 3.13 para paridad con el equipo). Dispara en
  push/PR a `main` y a la rama de refactor; `MPLBACKEND=Agg` (runner headless);
  concurrency cancela runs en vuelo. El extra `[dev]` pinea ruff al mismo
  `0.15.*` (local == CI).
- **mypy gradual** (`8a64881`): mypy sobre `src/lfs_insim` vigilando los ~14
  módulos ya limpios (client, transport, app, config, cli, sender, mixin, state,
  exceptions...). Backlog explícito (`ignore_errors` por módulo) para los de
  fricción: packets (dataclasses de protocolo con `field(metadata=)` +
  star-imports), insim_loader (importlib `ModuleSpec | None` + kwargs inyectados)
  y decoders/utils (2 errores puntuales cada uno). Config:
  `ignore_missing_imports`, `follow_imports=silent` (no reporta `config.settings`
  del CLI), exclude de los `.pyi`, target 3.10 (mypy 2.x no acepta 3.9; el
  runtime 3.9 lo cubre pytest). Job de CI `typecheck` con `continue-on-error`
  (NO bloquea el merge).

**Dos errores reales del core que los stubs `.pyi` enmascaraban** (aflorados al
excluir los `.pyi` de mypy), corregidos, type-only y cubiertos por los tests:
`insim_app` (`self.isi.Flags = ISF(0)` en vez de `0`: int → ISF) e `insim_client`
(narrowing de `f.name`, que typeshed tipa `str | None`, en el join de OSO).

**Hallazgo registrado (amplía P9):** `configuration.py` (`LFSConfigManager`)
está **huérfano** — su único consumidor es el `tools/setup_lfs.py` roto.
Decidir recuperar/eliminar en bloque. Backlog de tipado gradual (quitar los
overrides módulo a módulo) apuntado en PLAN.

**No requiere validación en LFS:** solo tooling/packaging + 2 fixes type-only.
Estado local al cierre: **ruff limpio, mypy limpio (24 ficheros), suite
469/469**.

**El primer run del CI cazó 2 incompatibilidades reales con Python 3.9**
(commit `a077f41`, `fix(py39)`), invisibles en local (3.14). Se instaló un
Python 3.9.13 real (`winget`, venv `.venv39`) para reproducir y verificar:

1. **Union PEP 604 (`X | Y`) en anotaciones evaluadas en runtime:** el `|`
   sobre tipos solo existe desde 3.10 (`TypeError` al importar en 3.9).
   Convertidas a `Union`/`Optional` (estilo ya usado en el core):
   `packets/base.py` (`repeat`), `packets/insim.py` (`ISP_CIM.SubMode`) y
   `um_class.py` (`User.plid`, `Player.telemetry`).
2. **Campo self-shadow `HLVC: HLVC` en `ISP_HLV`:** el campo se llama igual
   que su enum; en 3.9 la anotación sin comillas resuelve al `Field` ya
   asignado (orden de evaluación) y el autogenerado de `__doc__` de
   `dataclasses` recursa al hacer su `repr`. Convertido a forward-ref con
   comillas (`HLVC: "HLVC"`) — produce el MISMO stub y no evalúa la anotación.
   Único caso en el repo (escaneado con regex-backref en Python, ripgrep no los
   soporta).

**Guardas para que no recurra:** regla ruff **FA102** (PEP 604 sin
`from __future__ import annotations`) — lo habría cazado en lint; y la matriz
de CI ya incluye 3.9. **Verificado en 3.9.13 real:** 467 passed, 2 skipped
(los 2 skips = test de packaging con `tomllib`, stdlib solo desde 3.11). Sin
regresión en 3.14 (469); ruff limpio con FA102; stub `.pyi` sin cambios.
`.gitignore`: `.venv/` → `.venv*/` (para el venv `.venv39`).

**Cierre confirmado:** el push (`a077f41` + docs) necesitó varios intentos (Git
Credential Manager pedía reauth interactiva; los push los lanza el usuario),
pero se completó — origin en `e40cfec`. **CI en VERDE** en ese commit,
confirmado por la API de GitHub (run `e40cfec` = success) y **reproducido en
Docker (Linux 3.9.25 → 467 passed, 2 skipped)**, idéntico al runner. El "exit 4"
que aparecía en Actions era el run VIEJO (`b0d0541`, pre-fix), no el actual.
Herramientas nuevas de esta sesión para verificar en Linux/3.9 sin depender del
CI: venv `.venv39` (Python 3.9.13) y `docker run python:3.9` con el repo montado.

---

## S15 — 2026-07-03 — Fase 4: subcomandos del CLI (fin de los scripts globales)

**Arranque:** repo limpio y sincronizado (HEAD `459bc4c`, cierre S14); suite
heredada 465/465 antes de tocar. Sin mapas freeroam sin commitear que proteger.

**Qué se hizo (segundo ítem de Fase 4 — CLI):** los entry points sueltos
`generate-stubs` y `update-all` se instalaban como **comandos GLOBALES en el
PATH** de cualquiera que hiciera `pip install` (nombres genéricos que invaden
el entorno ajeno — lo contrario del objetivo de Fase 4). Plegados en
subcomandos de `lfs-insim`:

- **`cli.py`**: dos handlers nuevos (`cmd_stubs`, `cmd_update_all`) con import
  perezoso del módulo (`from . import generate_stubs` / `update_all`) que
  llaman a su `main()` y devuelven 0 — replican EXACTAMENTE lo que hacían los
  console-scripts (`... :main`, cuyo return `None` daba exit 0 y cuyas
  excepciones/`sys.exit` propagaban). Dos subparsers nuevos (`stubs`,
  `update-all`); docstring del módulo y epilog actualizados.
- **`pyproject.toml`**: `generate-stubs` y `update-all` fuera de
  `[project.scripts]` — **`lfs-insim` es el único console-script** (comentario
  explicando el porqué).
- **Git hook revisado (sub-tarea del ítem):** el `.githooks/pre-commit` es un
  **no-op deshabilitado por el usuario** (`exit 0`, con comentario propio) y
  `scripts/install-git-hooks.*` solo fija `core.hooksPath` → **ningún hook
  invocaba `generate-stubs`**: nada que migrar. Decisión: NO reactivarlo (lo
  deshabilitó el usuario a propósito); solo dejar registrado que, si se
  reactiva, debe llamar a `lfs-insim stubs` / `python -m lfs_insim.generate_stubs`.
- **Docs corregidas:** CLAUDE.md y README.md apuntaban la regeneración de
  stubs a `python src/lfs_insim/generate_stubs.py` y afirmaban que el hook
  "genera stubs en cada commit" (falso) → ahora `lfs-insim stubs` /
  `lfs-insim update-all` y comentario honesto sobre el hook deshabilitado.
  Nota de resolución parcial de P16 en DIAGNOSTICO (metadata S14 + scripts S15;
  quedan ruff/mypy/CI/CHANGELOG).

- **4 tests nuevos, rojo primero** (`tests/test_cli.py`, primer test del CLI):
  despacho de `stubs`→`generate_stubs.main()` y `update-all`→`update_all.main()`
  (monkeypatch del `main()`), y contrato de packaging leyendo `pyproject.toml`
  con `tomllib` — `lfs-insim` es el único `[project.scripts]`. Suite **469/469**.
- **Verificado a mano (smoke real, sin mocks):** `lfs-insim --help` lista los
  subcomandos; `lfs-insim stubs` regenera de verdad y el `.pyi` versionado
  **no cambió** (estaba al día); reinstalación editable (`pip install -e ".[dev]"`)
  **borra los `.exe` viejos** (`generate-stubs.exe`, `update-all.exe`) y deja
  solo `lfs-insim.exe`, ya con los subcomandos.

**No requiere validación en LFS:** solo tooling de desarrollo/packaging, cero
cambios de runtime (los 465 tests previos pasan intactos).

**Decisión de diseño:** los subcomandos llaman a `main()` y devuelven 0 en vez
de envolver el manejo de errores — replican el contrato exacto de los
console-scripts que sustituyen (`generate_stubs.main()` autoaborta con
`sys.exit(1)`; `update_all.main()` re-lanza tras loguear con `exc_info`), sin
inventar comportamiento nuevo. Import perezoso para no cargar `lfs_insim.packets`
(que `generate_stubs` importa a nivel de módulo) en cada arranque del CLI.

---

## S14 — 2026-07-03 — Fase 4 arrancada: metadata del paquete saneada

**Arranque:** repo limpio y sincronizado (HEAD `3b75b2e`, post-cierre S13);
suite heredada 463/463 antes de tocar.

**Qué se hizo (primer ítem de Fase 4 — metadata):**

- `readme = "README"` apuntaba a un archivo INEXISTENTE (existe `README.md`)
  → corregido; el wheel ahora embebe la descripción larga.
- **Licencia declarada** como expresión SPDX: `license = "MIT"` +
  `license-files = ["LICENSE"]` (el archivo MIT ya existía pero el paquete no
  lo declaraba). Exige subir el build-system a `setuptools>=77` (antes >=61).
- **Fuente única de versión:** `__version__ = "0.2.0"` en
  `src/lfs_insim/__init__.py` (exportada en `__all__`); pyproject pasa a
  `dynamic = ["version"]` con `attr = "lfs_insim.__version__"`. El contrato
  queda fijado con test: la metadata instalada coincide con `__version__`
  (si falla tras un bump → reinstalar editable, el propio test lo dice).
- `requirements.txt` eliminado — solo decía "no hay dependencias" (y mentía
  con el Python mínimo: 3.10+ vs el 3.9+ real); nada lo referenciaba salvo
  los docs de dev.
- **URLs corregidas:** Homepage apuntaba al repo ANTIGUO
  (`Aprendiendo-InSim-LFS`) → `AP_LFS_InSim`; añadidos Repository e Issues.
- Descripción en inglés (metadata de cara a PyPI, coherente con la decisión
  S06 de core en inglés); keywords y classifiers completados (Python
  3.9–3.14, `3 :: Only`).
- **2 tests nuevos, rojo primero** (`TestVersionUnica` en
  `test_api_publica.py`). Suite **465/465**. Verificado: reinstalación
  editable OK, `lfs-insim list` OK, y **el wheel construye limpio en
  aislamiento** (`pip wheel . --no-deps` con build isolation — valida la
  metadata SPDX con setuptools 77 real).

**No requiere validación en LFS** (solo packaging; cero cambios de runtime).

**Decisión de secuencia (S14, acordada con el usuario):** orden de Fase 4 =
**CLI → ruff + CI → docs → CHANGELOG**. El ítem del CLI va primero por un
wart concreto hallado al leer el paquete: `generate-stubs` y `update-all`
se instalan como **comandos GLOBALES en el PATH** de quien haga
`pip install` (nombres genéricos que invaden el entorno ajeno) → plegarlos
en `lfs-insim`. Luego ruff ANTES de escribir más código (format = diff de
pura forma, cubierto por los 465 tests) y CI encima.

**PyPI (verificado en S14):** el nombre `lfs-insim` está LIBRE
(`pypi.org/pypi/lfs-insim/json` → 404). Decisión: **preparar sí, publicar
no todavía** — ensayar en TestPyPI cuando llegue CI y dejar workflow listo;
el publish real a PyPI, tras el merge a `main` (acción pública e
irreversible). Sin prisa por reservar el nombre. Detalle en
ESTADO_ACTUAL § Bloqueos.

---

## S13 — 2026-07-03 — Fase 3 COMPLETADA: `handler_errors` + `tick_interval`

**Arranque:** repo limpio y sincronizado (HEAD `f2995e5`, cierre S12); suite
heredada 450/450 antes de tocar.

**Qué se hizo (último ítem de Fase 3):** hasta hoy `_execute_handler` tragaba
y logueaba SIEMPRE los errores de las apps — resiliente en producción, pero
en desarrollo un bug en un handler pasaba desapercibido entre los logs.

- **Clave nueva `handler_errors` en `DEFAULT_CONFIG`** ('log' | 'raise'):
  - `'log'` (default): comportamiento de siempre — el error se aísla, se
    loguea con traceback y el dispatch continúa. Nadie nota el cambio.
  - `'raise'` (fail-fast, para desarrollo): el primer error de un handler
    `on_ISP_*` o de un hook de lifecycle detiene el cliente. Plomería: el
    handler re-lanza → el worker aparca la excepción en `_handler_error`,
    loguea CRITICAL y sale (lo pendiente en cola se descarta a propósito);
    el bucle principal de `start()` la ve en ≤100 ms y la re-lanza en el
    hilo principal → `start()` muere con el traceback ORIGINAL del handler
    (las excepciones conservan el traceback del hilo del worker) y `stop()`
    limpia en el finally.
  - Valor inválido → `InSimConfigurationError` al crear el cliente (la
    validación de la política es en sí fail-fast).
- **Excepción deliberada:** los `on_disconnect` despachados desde `stop()`
  se aíslan SIEMPRE (`_dispatch_lifecycle(..., isolate=True)`) — el apagado
  debe completarse y todas las apps deben recibir su on_disconnect aunque
  una explote, también en modo 'raise'.
- **De propina:** los errores de lifecycle en modo 'log' ahora se loguean
  con `exc_info=True` (antes salían sin traceback — inservibles para
  depurar).
- Contrato documentado en CLAUDE.md (§ Handler error policy), docstring del
  módulo y `config.py`; `insim_client.pyi` actualizado a mano (el generador
  solo produce `insim_app.pyi`).
- **8 tests nuevos, rojo primero** (`TestPoliticaDeErroresDeHandlers` en
  `test_client_dispatch.py` + default en `test_config.py`), incluida la
  integración completa contra FakeLFS: keep-alive → handler explota →
  `start()` propaga ValueError y el cliente queda parado. Suite **458/458**.

**No requiere validación en LFS:** el default no cambia ningún
comportamiento (los 450 tests previos pasan intactos) y el modo 'raise' es
una herramienta de desarrollo cubierta por la integración con FakeLFS.

**Remate de S13 — `tick_interval` (decisión heredada de S07, resuelta con
el usuario):** SÍ es configurable, pero desacoplando el tick de las apps
del sondeo interno del bucle principal — el `time.sleep(0.1)` viejo
controlaba a la vez la cadencia de `on_tick`, la detección de caídas (P12)
y el fail-fast de S13; configurarlo sin desacoplar habría sido un footgun.

- Clave `tick_interval` (segundos, default 0.1 = comportamiento histórico;
  mínimo 0.01, validado al crear el cliente con `InSimConfigurationError`,
  como `handler_errors`).
- El bucle principal sondea SIEMPRE a `min(0.1, tick_interval)` para
  `_connection_lost` y `_handler_error`, y despacha `on_tick` solo cuando
  vence el intervalo (acumulador con `time.monotonic()`; el primer tick
  sale inmediato, como siempre). Sin catch-up tras un stall: una
  reconexión larga no dispara una ráfaga de ticks debidos.
- Documentado (CLAUDE.md, docstring del cliente, `config.py`): no es un
  timer de precisión (~15 ms de resolución en Windows); el trabajo de alta
  frecuencia va en handlers MCI/OutSim; cadencias por app → contadores
  módulo sobre el tick del cliente.
- **5 tests nuevos, rojo primero** (`TestTickInterval`): intervalo lento
  respetado (huecos ≥ intervalo), tick rápido (12 ticks en < 0.9 s, contra
  ≥ 1.1 s de la cadencia vieja), y la guardia clave — con
  `tick_interval=5.0` la caída se detecta y reconecta en < 2 s.
  Suite **463/463**.

**FASE 3 COMPLETADA.** Sus ítems de runtime están validados en LFS
(S08–S12); los dos de S13 no cambian defaults (la cadencia efectiva sigue
siendo ~100 ms). Próxima: **Fase 4 — DX y packaging** (metadata, CLI,
ruff/mypy, CI, docs de usuario, CHANGELOG; decisión pendiente: PyPI).

**Post-cierre:** el usuario mapeó South City en el juego (grafo freeroam +
render actualizados). Protegido según la instrucción permanente: respaldo
en `C:\Users\pasca\backups\AP_LFS_InSim_maps\2026-07-03_S13` + commit
`74be94b` pusheado.

---

## S12 — 2026-07-03 — Fase 3: apagado limpio y determinista (carrera de `close()` + stop() atómico)

**Arranque en dispositivo nuevo:** no había `.venv` — creado (Python 3.14.3),
`pip install -e ".[dev]"`, `settings_local.py` copiado del example y git hooks
instalados (`install-git-hooks.ps1`). La suite heredada pasó 438/438 antes de tocar.

**Qué se hizo:**

- **Apagado limpio (ítem de Fase 3, resuelto):** la carrera de S11 en
  `InSimTransport.close()` se reprodujo primero EN ROJO con dos tests
  (socket falso que despierta con retardo tras el cierre — la ventana exacta
  del jitter del SO; y `close()` llamado desde el propio hilo receptor, que
  con el código viejo re-armaba el bucle y seguía leyendo: 3 recv en vez de 1).
- **Fix (más robusto que el join propuesto en S11):** cada bucle receptor
  **captura su evento de stop al arrancar**, y `close()` lo deja puesto para
  siempre y lo **REEMPLAZA** por uno nuevo (nunca `clear()`), además de hacer
  join (timeout 2 s) de los receptores antes de volver. Consecuencias:
  un receptor que despierte tarde ya no puede confundir un cierre deliberado
  con una caída (ni log de error falso ni `on_connection_lost` espurio);
  `close()` es determinista (al volver, los hilos han salido); y es seguro
  llamarlo desde el propio receptor (no se hace join a sí mismo — el bucle
  sale por su evento capturado). El transporte sigue siendo reutilizable
  (test de reconexión tras close por loopback).
- **`InSimClient.stop()` atómico (de propina, mismo ítem):** el check-and-set
  de `running` no era atómico — dos stops simultáneos (handler + Ctrl+C)
  podían despachar `on_disconnect` dos veces. Lock SOLO alrededor del flip
  del flag: la reentrada desde un hook `on_disconnect` retorna al instante
  sin deadlock (2 tests: 8 stops con barrera → un solo apagado; reentrante).
- Suite **443/443** (438 + 3 transporte + 2 stop); smoke `lfs-insim list` OK;
  stubs sin cambios. Commit `7ee9f38`.

**Incidente en vivo (misma sesión) → P24 resuelto:** al intentar conectar,
LFS mostró "InSim - TCP excess : 127.0.0.1". Forense del log + sondas ISI
contra el LFS vivo (0.8C17): el LFS de este equipo tiene `Game Admin abc`
y el `settings_local.py` recién copiado del example llevaba `admin_pass: ''`
→ LFS aceptaba el TCP y tiraba la conexión ~10 ms tras el ISI (sin enviar
un solo byte). El defecto del framework: `_reconnect` daba cada ciclo por
bueno (TCP + ISI enviados, nada confirma la aceptación) y reseteaba el
backoff → **tormenta de ~10 conexiones/s** (~250 en 25 s); el "TCP excess"
era LFS quejándose del aluvión y el mensaje del rechazo real (password)
quedó enterrado. Sonda con `Admin='abc'` → VIVA con IS_VER de vuelta
(confirmación al 100%). **Fixes:** (1) `admin_pass: 'abc'` en el
settings_local de este equipo; (2) **P24 en el core** — reconexión
provisional: si la sesión muere antes de `reconnect_stable_time` (config
nueva, default 10 s), el siguiente `_reconnect` retoma la racha (espera el
delay acumulado ANTES de reintentar, sigue escalando, y la racha cuenta
para `reconnect_max_attempts`, que antes no agotaba nunca). 3 tests nuevos
(`TestReconexionProvisional`, en rojo primero). Suite **446/446**.
Verificado en vivo: `test_insim` conectado y estable 8 s contra el LFS del
usuario. Commit `759f224`.

**Validación del usuario (cierre de S12):** probado en LFS tras los fixes —
"todo funciona correctamente" (conexión normal con la password puesta y
apagado limpio). **S12 termina sin validaciones pendientes.**

**Remate de S12 — pista de diagnóstico de ISI rechazado (decidido con el
usuario tras valorar leer la password del cfg.txt):** LFS no da feedback en
el socket al rechazar un ISI — solo cierra. Ahora el cliente marca la
sesión como "hablada" al primer byte recibido y, si muere antes de
`reconnect_stable_time` sin haber recibido NADA, loguea la pista explícita
("ISI likely rejected — check admin_pass / InSim version") — el mensaje que
faltó en el diagnóstico del incidente. El **fallback de leer `Game Admin`
desde cfg.txt se descartó como código** (solo localhost; cfg.txt se escribe
al SALIR de LFS; y rompería P14 si viviera en el core) y quedó apuntado
como idea a futuro en PLAN § Ideas + comentario en `config/settings.py`
(capa de proyecto, si algún día se hace). 4 tests
(`TestPistaDeIsiRechazado`). Suite **450/450**. Commit `3f2e2b3`.

**Próxima sesión:** política de errores de handlers configurable
(resiliente en prod, fail-fast en dev); decisión de `on_tick` configurable.

---

## S11 — 2026-07-03 — Fase 3: P18 (envío UDP eliminado) + P19 (una sola ruta de serialización)

**Qué se hizo:**

- **P18 (resuelto, eliminado):** fuera el parámetro `use_udp` de
  `InSimTransport.send` — el envío es **siempre TCP** (LFS solo recibe InSim
  por TCP; el socket UDP es solo de bajada: OutSim/OutGauge, NLP/MCI).
  Documentado (docstring del transporte + CLAUDE.md) y fijado con test nuevo
  en `test_transport.py` (sin TCP, `send` falla aunque haya socket UDP).
  Nadie pasaba `use_udp`; el único llamador es `client.send`. Commit `844feed`.
- **P19 (resuelto):** una sola autoridad para el layout de strings.
  - Encode: `validate_string_lengths()` (prepare) fija truncado y padding de
    TODOS los strings — gana el truncado de los fijos `'Ns'` a N-1 (el null
    final siempre cabe; antes vivía en `_extract_values` recortando bytes);
    `_extract_values()` ya solo codifica a latin-1 (`struct.pack` rellena los
    fijos; los variables resuelven su fmt de `len(val)`). Desaparece el
    recálculo "por seguridad" del padding (las tres capas se pisaban y el
    truncado de `struct.pack` disimulaba la discrepancia).
  - Decode: eliminado el `.strip()` (2 sitios) — se corta en el primer null y
    se conservan los espacios significativos.
  - **Dos cambios deliberados de comportamiento**, actualizados en los goldens:
    string fijo con `len == N` pierde 1 char por el null terminator (antes
    salía SIN terminador, contra la spec; golden nuevo del caso) y los strings
    decodificados conservan los espacios previos al null (los parsers de
    comandos hacen su propio strip → sin impacto esperado). Commit `720315a`.
- De paso: hallada (sin arreglar) una **carrera en `InSimTransport.close()`**
  — `_stop.clear()` sin join de los receptores puede disparar
  `_notify_connection_lost()` espurio tras un cierre deliberado. Registrada
  como punto de entrada del ítem "apagado limpio" en ESTADO_ACTUAL.
- Suite **438/438** (436 + test P18 + golden P19); smoke `lfs-insim list` OK.

**Validación del usuario (cierre de sesión):** probado en LFS el estado
post-P18/P19 — todo OK (nada dependía de los strings recortados del decoder).
**S11 termina sin validaciones pendientes.**

**Próxima sesión:** apagado limpio y determinista (carrera de `close()`),
política de errores de handlers, decisión de `on_tick` configurable.

---

## S10 — 2026-07-03 — Validación de P2-core en LFS + P22 resuelto + P23 (QuickEdit)

**Validación del usuario (P2-core), con análisis forense del log:**

- Secuencia probada: conexión + AIs rodando (~68 min), cierre abrupto del juego,
  reapertura del puerto, cierre del puerto, arranque del insim con el juego cerrado.
- **El framework se comportó bien en todo:** detección de caída en 33–40 ms,
  backoff correcto, restauración de sesión (ISI + NCN/NPL + limpieza/repoblación
  de users_management), keep-alive contestado bajo tráfico, Ctrl+C limpio en
  pleno backoff (adiós zombie), fail-fast diseñado al arrancar sin LFS.
- **Los comportamientos "raros" eran de `ai_control`** (no es consciente de la
  reconexión): su hilo `_run_test_freeroam` (bucle infinito en hilo daemon,
  `commands.py:389`) murió con `InSimConnectionError` al enviar desconectado
  (traceback a stderr, invisible en el log) en la 1ª caída; en la 2ª sobrevivió
  de casualidad y, tras la limpieza de memoria del on_reconnect, vio "0 coches"
  y se puso a crear/arrancar IAs con ownership desincronizado ("La AI X no es
  una de tus AI's"). Apuntado como ítem nuevo de Fase 5 en PLAN.md.
- **Misterio resuelto (P23):** tras la 1ª caída el proceso quedó mudo (ni intento
  4 ni shutdown). Causa: consola Windows en modo selección (QuickEdit) — bloquea
  stdout, y con `handlers: ['console', 'file']` el logger se congela ANTES de
  escribir al archivo. El insim estaba paralizado, no muerto; encaja con el
  relato del usuario ("me conecté sin problemas pero no se ejecutó nada").

**Fixes aplicados (S10):**

- **P23 (mitigación):** `file` antes que `console` en `LOGGING_CONFIG` (el
  archivo siempre recibe el registro aunque la consola esté congelada);
  `lfs-insim run` desactiva QuickEdit al arrancar (`_disable_console_quick_edit`,
  ctypes, best effort, solo win32); `_reconnect` deja traza explícita
  ("Reconnection abandoned") cuando sale por parada del cliente.
- **P22 (resuelto):** `_restore_session` invertido — ISI → `on_reconnect`
  (limpieza de estado) → `TINY.NCN/NPL` — para que las respuestas nunca corran
  contra la limpieza. La carrera se había visto EN VIVO en el log de las
  13:33:55. Test nuevo del orden causal en `test_reconexion.py`.
- Suite **436/436**; smoke `lfs-insim list` + ruta de error de `run` OK.

**Decisión:** robustez de `ai_control` ante reconexiones → Fase 5 (no mezclar
con el core). Idea DX apuntada: traceback feo del connect inicial fallido y
posible `connect_retry` (ver ESTADO_ACTUAL § Próximo paso).

**Próxima sesión:** P18 (envío UDP: recomendación eliminar) y P19 (una sola
ruta de serialización).

---

## S09 — 2026-07-03 — Fase 3: P2-core (dispatch fuera del hilo de IO)

**Arranque de sesión:** había mapeo de South City sin commitear (+5.605 líneas
en `south_city.json` + render); por instrucción permanente del usuario se
protegió ANTES del `git pull`: backup fuera del repo + commit `7cb7562` + push.
La regla quedó registrada en `MODUS_OPERANDI.md` § 1 paso 2 (commit `edc4c09`).

**Qué se hizo — P2-core (cola + worker de dispatch):**

- **Cliente:** los hilos de IO ya no ejecutan handlers. `on_packet_received`
  (llamado por el transporte) contesta el keep-alive `TINY.NONE` en el acto
  —una cola ocupada nunca retrasa el ping a LFS— y encola el paquete;
  el worker dedicado `InSim_Dispatch_Worker` (hilo daemon, arrancado en
  `start()` antes de conectar) saca de la cola y llama a `_dispatch_packet`
  en orden FIFO estricto. Bucle del worker con guarda propia: nada lo mata.
- **Apagado:** `stop()` cierra el transporte (deja de entrar) y mete un
  centinela `_DISPATCH_STOP` al FINAL de la cola → lo pendiente se despacha
  antes de salir; `join` con timeout 2 s y protección contra `stop()` llamado
  desde el propio worker (un handler puede parar el cliente sin deadlock).
- **Retirado `use_thread_pool`/`max_workers`** (cliente + `DEFAULT_CONFIG` +
  tests): dispatch por pool no garantizaba orden y no tenía usuarios.
- **Contrato de threading documentado** (CLAUDE.md § Packet lifecycle +
  docstring de `insim_client.py`): handlers `on_ISP_*` en el worker, FIFO, de
  uno en uno (un handler lento no bloquea la recepción pero retrasa a los que
  vienen detrás); hooks de ciclo de vida en el hilo principal; sin garantía de
  orden entre ambos mundos; `send()` thread-safe desde cualquier hilo.
- **Tests:** 6 nuevos en `test_client_dispatch.py` (`TestColaYWorkerDeDispatch`):
  la recepción solo encola; FIFO end-to-end; handler bloqueado no frena
  `on_packet_received` ni el keep-alive (criterio de Fase 3); `stop()` vacía lo
  pendiente; el worker sobrevive a un handler que explota; arranque idempotente.
  Retirados los 2 del thread pool. Suite **435/435**; `lfs-insim list` OK.
- **Limpieza:** `insim_client.pyi` reescrito — estaba desfasado desde Fase 2
  (aún declaraba `register_module`, `modules[]`, `on_first`...); el generador
  de stubs solo cubre `insim_app.pyi`, este va a mano.
- **Descubierto P22 (BAJA, preexistente):** en `_restore_session` los
  `TINY.NCN/NPL` se piden ANTES de despachar `on_reconnect`; una respuesta muy
  rápida podría procesarse antes del `_clear_all_memory()` y perderse. Fix
  propuesto (invertir orden) registrado en DIAGNOSTICO; no se tocó para no
  mezclar cambios de comportamiento con P2.

**Pendiente de validar en LFS (usuario):** funcionamiento normal de
`ai_control` + una reconexión. No debería notarse ningún cambio.

**Próxima sesión:** P18 (envío UDP: recomendación eliminar), luego P19
(una ruta de serialización) + P22 de paso.

---

## S08 — 2026-07-03 — Fase 2 cerrada + Fase 3: P12 (reconexión automática)

**Qué se hizo (segundo bloque, misma sesión) — P12, reconexión automática:**

- **Transporte:** callback nuevo `on_connection_lost` — se dispara desde el hilo
  receptor moribundo cuando el bucle TCP termina sin `close()` (recv vacío o
  excepción); un cierre deliberado (`close()` pone `_stop` antes) NO lo dispara.
  `connect_tcp` ahora cierra un socket previo muerto antes de reconectar.
- **Cliente (diseño: reconexión desde el bucle principal):** el callback solo
  marca un `threading.Event`; el bucle de `start()` — exactamente el que antes
  quedaba zombie (P12) — lo detecta en ≤100 ms y llama a
  `_handle_connection_lost()`: `on_disconnect` a apps y cliente **desde el hilo
  principal** (consistente con on_connect/on_tick, sin hilos extra ni carreras),
  y `_reconnect()` con backoff exponencial. Al reconectar: reenvía `self.isi`
  (ya agregado), re-solicita `TINY.NCN/NPL` (los trackers se repueblan solos por
  sus handlers) y despacha `on_reconnect` (hook nuevo, vacío por defecto en
  `InSimClient` y `InSimApp`). Nuevo atributo `client.connected`; `stop()` ya no
  duplica `on_disconnect` si la caída ya lo despachó. Con `reconnect: False` o
  `reconnect_max_attempts` agotados → `stop()` limpio (adiós proceso zombie).
  `on_tick` se pausa mientras se reconecta.
- **Config:** claves nuevas en `DEFAULT_CONFIG`: `reconnect` (True),
  `reconnect_delay` (1.0 s), `reconnect_backoff` (2.0), `reconnect_max_delay`
  (30 s), `reconnect_max_attempts` (0 = infinito).
- **users_management:** `on_reconnect` limpia la memoria (`_clear_all_memory`)
  para no arrastrar estado de antes de la caída; los NCN/NPL la repueblan.
- **Tests:** `tests/test_reconexion.py` (11): callback del transporte (avisa en
  recv vacío/excepción, no con stop, errores aislados) e integración real del
  cliente con `start()` en un hilo contra FakeLFS (caída → on_disconnect →
  reconexión → ISI+NCN/NPL → on_reconnect, en orden y a todas las apps; dos
  caídas seguidas; `reconnect: False` detiene el cliente sin zombie;
  `max_attempts` exacto; `stop()` durante el backoff sale limpio). Los tests de
  política de reintentos parchean `connect_tcp` (el connect real a puerto
  cerrado tarda segundos en Windows). **FakeLFS acepta ahora conexiones
  sucesivas** (`espera_conexiones(n)`, contador `conexiones`).
- **Docs:** CLAUDE.md (hook `on_reconnect` + sección de auto-reconexión),
  DIAGNOSTICO.md (P12 resuelto), PLAN.md (casilla P12 de Fase 3).
- Suite **431/431**; smoke de carga de insims y CLI OK.

**Validación del usuario (cierre de sesión):** P12 probado en LFS real —
matar/levantar LFS con el InSim corriendo → reconectó solo, prueba exitosa.
S08 termina sin validaciones pendientes. Próxima sesión: **P2-core** (sacar el
dispatch del hilo de IO: cola + worker; ver "Próximo paso" en ESTADO_ACTUAL).

---

## S08 (primer bloque) — 2026-07-03 — Fase 2: migración de insims fuera de la facade deprecada

**Qué se hizo:**
- **`ai_control` migrado a la API pública (P15):** los 10 imports de
  `insim_packet_class` en 9 archivos (`app.py`, `commands.py` ×2, `physics.py`,
  `traffic.py`, `navigation.py`, `nav_modes/route/manager.py`,
  `nav_modes/freeroam/{graph,map_recorder,mode}.py`) pasan a los puntos
  recomendados: ISP_* y `AIInputVal` desde `lfs_insim.packets`; `CS`, `CSVAL` y
  `SND` desde `lfs_insim.insim_enums`. Cambio mecánico, sin tocar lógica.
- **`users_management` no necesitaba cambios:** ya importaba
  `lfs_insim.packets`/`lfs_insim.insim_enums`; `main.py` recibe los enums vía
  `from um_class import *` (um_class hace `from insim_enums import *`).
- **Verificación:** smoke que carga los 4 insims con el DeprecationWarning de la
  facade elevado a error y comprueba que `insim_packet_class` no entra en
  `sys.modules` — OK. `lfs-insim list` OK. Suite **420/420**.
- Con esto la facade deprecada queda sin consumidores dentro del repo (solo la
  cubren los tests de compatibilidad de `test_api_publica.py`).

**Commits:** `0292a01` refactor(insims): migrar ai_control fuera de la facade
deprecada (cierre P15).

**Validación del usuario (misma sesión):** probado en LFS el estado
post-migración — todo funcionó correctamente. **FASE 2 CERRADA.** Se abre
**Fase 3** (robustez en runtime); próximo: P12 (reconexión automática),
empezando por tests con `FakeLFS` que simulen caída/vuelta del servidor.

---

## S07 — 2026-07-03 — Fase 2: P14 (config del paquete con defaults internos)

**Qué se hizo (segundo bloque, misma sesión) — P15, P17 y P20** (tras validar el
usuario P13/P14/P21 en LFS con `!test hcp` OK):

- **P15 — API pública con `__all__` en todos los módulos:**
  - El core dejó de importar la facade: client/app/sender/decoders/utils/mixin
    importan de `.packets`; `utils.py` toma `SND` de `insim_enums` (dependía de la
    fuga).
  - `insim_packet_class` → facade **deprecada** (DeprecationWarning al importar);
    re-exporta packets **y** enums (superficie del monolito original) para el código
    viejo (`ai_control` la usa aún).
  - `packets/insim.py`: el `from insim_enums import *` (la fuga que contaminaba todo
    `packets`) es ahora un import explícito de 68 enums. `packets/__init__` compone su
    `__all__` desde los submódulos + catálogos (`INSIM_PACKETS`, `OUTSIM_PACKETS`,
    `RECEIVE`, `SEND`, `ALLOWED_PACKETS`). Descubierto de paso: `OutSimPack2` es
    asignación de módulo (`make_dataclass`), no `class` — entró en el `__all__` de
    `outsim.py`.
  - `__all__` también en `insim_enums` (96 nombres; sin fugas de `IntEnum`/`IntFlag`),
    `utils` (21), `exceptions` (7, ahora todas exportadas también en `lfs_insim`),
    `config`, y docstring de API pública en `lfs_insim/__init__.py`.
  - **Reparados los que dependían de la fuga** (escaneo AST de nombres no resueltos,
    sin falsos positivos de comentarios/atributos): `test_insim/main.py` (TINY),
    `_cmds_request.py` (SMALL, TINY), `_cmds_send.py` (12 enums) y
    `tests/test_insim_handlers/test_lifecycle.py`; `test_packet_base.py` migrado a
    `lfs_insim.packets`.
- **P17:** `class INST` **duplicada** eliminada de `insim_enums.py` (dos definiciones
  idénticas, líneas 927 y 1287); CLAUDE.md corregido (decía que los constraints de
  versión "no se aplican todavía" — sí se aplican). `on_tick` configurable → Fase 3.
- **P20 — fail-fast del loader:** dependencia rota aborta la carga del dependiente
  (`InSimModuleError` con la cadena completa, `raise ... from`); eliminado el tragado.
  Tests nuevos: fail-fast simple y cadena transitiva (nieto←hijo←fantasma).
- **Tests:** `tests/test_api_publica.py` (17: `__all__` resuelve en 11 módulos, sin
  duplicados, sin fugas packets↔enums↔stdlib, facade avisa y conserva superficie).
  Suite **420/420**. Smoke: los 4 insims cargan (1 DeprecationWarning esperado de
  `ai_control`); `lfs-insim list` OK.
- **Validación del usuario (inicio del bloque):** P13/P14/P21 probados en LFS real —
  todo bien, incluido `!test hcp`.
- **Cierre de sesión:** el usuario validó en LFS también el estado post-P15
  (`!test` OK) — S07 termina sin validaciones pendientes. Próxima sesión: migrar
  `ai_control`/`users_management` fuera de la facade deprecada y cerrar Fase 2.

**Qué se hizo (primer bloque):**
- **`src/lfs_insim/config.py` (nuevo):** `DEFAULT_CONFIG` (defaults del framework:
  TCP/ISI/UDP/dispatch; sin valores por máquina como `user_name` o env) y
  `build_config(overrides)` (copia fusionada). Se mantiene **dict plano** en vez de
  dataclass para conservar la superficie `self.config.get(...)` de todos los insims
  (decisión: tipado fuerte puede venir con P15 si compensa).
- **Core sin CWD:** `InSimClient.__init__` e `InSimApp.__init__` usan `build_config`;
  eliminados los dos `from config.settings import get_config`. El core ya no depende
  de ningún archivo del proyecto.
- **Loader:** `InSimLoader(config=...)` — la guarda y la usa al crear el cliente
  perezoso; al instanciar cada app le pasa `config=self.client.config`, así **las apps
  heredan la config efectiva del cliente** (antes cada app releía el CWD por su
  cuenta). Con cliente inyectado, la config del loader se ignora (documentado).
- **CLI:** `_load_project_config()` — `config.settings.INSIM_CONFIG` del CWD si existe
  (ya aplica `settings_local.py` y env) > fallback env `LFS_ADMIN_PASS` > `None`
  (defaults del paquete). `get_loader()` la pasa al loader. El hack
  `sys.path.insert(0, os.getcwd())` se queda: los insims (p. ej. `RouteManager`)
  siguen importando `config.settings` legítimamente — P14 solo exige que el **core**
  no lo haga.
- **Exports:** `DEFAULT_CONFIG` y `build_config` añadidos a `lfs_insim/__init__.py`.
- **Tests:** `tests/test_config.py` (8: defaults/copia/fusión + cliente, app e ISI
  funcionando con el paquete `config` **bloqueado** en `sys.modules`) y
  `TestConfigDelLoader` en `test_loader.py` (3: propagación al cliente perezoso y a
  las apps; cliente inyectado manda). Suite **402/402**.
- **Smokes:** `lfs-insim list` + carga de `ai_control` dentro del proyecto (llegan
  `insim_name`/`prefix` del proyecto); cliente, app y CLI desde un CWD sin `config/`
  funcionan con defaults.
- CLAUDE.md actualizado (bullet de Config; el viejo mencionaba `OUT_CONFIG`, que ya
  no existe).
- Pendiente del usuario: validar en LFS P13 + P14 (ISI con nombre/prefijo/admin del
  proyecto; comandos respondiendo; re-probar `!test hcp`).

---

## S06 — 2026-07-02 — Fase 1 COMPLETADA; P11 (composición), P13 (transporte) y P21

**Qué se hizo (cuarto bloque, misma sesión) — fix de P21, adelantado de Fase 3:**
- Validando P13 en vivo, el usuario pisó P21 con `!test hcp` (`struct.error: pack
  expected 68 items (got 5)` en el log; el aislamiento de `_execute_handler` contuvo
  el fallo y el cliente siguió vivo — P13 se comportó bien).
- Fix en `_extract_values`: rama nueva para secuencias de formato fijo (`repeat(...)`
  devuelve una lista de fmts por hueco) que aplana y **rellena con defaults** hasta la
  longitud fija (sub-structs → instancia por defecto; primitivos → 0); en listas
  variables, los items tuple/list (p. ej. IPs `'4B'`) se expanden con `extend`.
- `TestEnviosRotos` → `TestGoldenSecuenciasFijas` (5 golden-bytes reales de REO/HCP/
  IPB); REO y HCP reincorporados al test estructural. Suite **391/391**.
- Queda que el usuario re-pruebe `!test hcp` en LFS.

**Qué se hizo (tercer bloque, misma sesión) — Fase 2, P13** (tras validar el usuario
P11 en LFS):
- **`encode_packet` puro extraído** de `send_packet` (commit propio): una sola ruta de
  serialización sin socket; los golden-send ejercitan ahora la función real (los tests
  de P21 esperan `InSimPacketError`, el envoltorio real).
- **`insim_transport.py` (nuevo): `InSimTransport`** — sockets TCP/UDP, hilos
  receptores, stop event y lock de envío **por instancia**; entrega paquetes crudos al
  callback `on_raw`. Framing TCP idéntico al caracterizado en Fase 1.
- **`InSimClient` posee su transporte** (inyectable); barrera pre-decode + decode en
  `_on_raw_bytes`; `send(packet) = encode_packet + transport.send`.
- **Eliminados:** `insim_packet_io.py`, el `send_packet` global y los sockets/force_set/
  oso_opts (muerto) de `insim_state`, que queda como azúcar: **cliente por defecto**
  (primero creado), fallback del mixin para helpers sin `client` (Command, CMDManager,
  RouteManager, MapRecorder).
- **Tests:** `test_packet_io.py` → `test_transport.py` (32, incluido el **criterio de
  aceptación de Fase 2: dos clientes coexistiendo** con recepción y envío
  independientes); registry adaptado a `_on_raw_bytes`; `test_insim_state` adelgazado;
  fixtures de handlers registran la app en un cliente real con `client.send` parcheado;
  `conftest` con `fake_lfs_factory`. Suite **388/388** (el recuento baja por tests de
  sockets globales que ya no aplican). CLAUDE.md actualizado (transporte y estado global).
- Pendiente del usuario: validar P13 en LFS (la ruta interna de envío/recepción cambió).

**Qué se hizo (segundo bloque, misma sesión) — Fase 2, P11:**
- **Decisión de idioma resuelta con el usuario:** inglés en el core (identificadores,
  docstrings, errores/log del código nuevo); español en docs/dev, tests, insims y
  comunicación. Registrada en `MODUS_OPERANDI.md` § 5.
- **P11 — inversión a composición** (los 3 archivos reescritos en inglés):
  - `insim_app.py`: `InSimApp(PacketSenderMixin)` — ya no hereda de `InSimClient`.
    Conserva: config, logger, `isi` (solo contribución de Flags), `outsim_opts`,
    dependencias, `get_insim`, hooks. Nuevo atributo `self.client` (lo asigna
    `register`). Eliminado `_resolve_dependencies` (código muerto, parte de P17).
  - `insim_client.py`: gana `register(app)` (idempotente, asigna `app.client`);
    `modules[]` → `apps`. Dispatch, agregación de flags ISI/OSO, keep-alive y
    lifecycle intactos.
  - `insim_loader.py`: **sin coup d'état** — cliente único perezoso (`loader.client`,
    propiedad) o inyectado (`InSimLoader(client=...)`); `load()` registra cada app en
    el cliente en orden de dependencias. Conservado: caché, checks de versión, tragado
    P20, envoltura de errores (mensajes ahora en inglés). Sin rollback (ya no hay trono).
  - `cli.py`: `cmd_run` arranca `loader.client.start()` en vez de la app.
- **Cambio de comportamiento deliberado:** el orden de dispatch pasa a ser el de
  dependencias (users_management procesa ANTES que ai_control). El orden antiguo
  (master-dependiente primero) era un bug latente: el consumidor leía estado no
  actualizado.
- **Tests adaptados:** `test_loader.py` (31: registro en cliente en orden de deps,
  cliente perezoso/inyectable, fallo no ensucia el cliente), `test_client_dispatch.py`
  (16: + TestRegister), `test_active_packet_registry.py` (`apps`). Suite **391/391**.
- **Smoke tests reales:** `test_insim`, `users_management` y `ai_control` cargan SIN
  cambios (la superficie de `InSimApp` se conservó); `ai_control` queda registrado tras
  `users_management`; `lfs-insim list` OK. CLAUDE.md actualizado (sección arquitectura).

**Qué se hizo (primer bloque) — cierre de Fase 1:**
- **Tests de packet_io** (`tests/test_packet_io.py`, 28 tests), sin LFS real:
  - `_tcp_listen_loop` con socket guionizado: reensamblado del flujo TCP (paquete
    completo, dos pegados, fragmentado en dos y byte a byte, pegado+fragmento del
    siguiente, ráfaga de 10); byte **Size=0** se descarta de uno en uno (resincronización
    byte a byte); cierre (recv vacío corta el bucle; **un resto incompleto en el buffer
    se pierde en silencio**); excepción en recv termina el hilo sin propagar (sin
    reconexión — P12); STOP_EVENT previo impide leer.
  - `_udp_listen_loop`: un datagrama = un paquete (sin reensamblado), datagrama vacío
    se ignora sin cortar, excepción termina el bucle.
  - `stop_all_threads`: cierra y resetea ambos sockets, traga errores de cierre y deja
    STOP_EVENT limpio.
  - `connect_tcp_lfs`/`connect_udp_lfs`: puerto cerrado/ocupado → `InSimConnectionError`.
  - **Integración real por loopback** (7 tests, con `fake_lfs`): conectar registra el
    socket y arranca el hilo receptor; trazas completas y fragmentadas llegan
    decodificadas al cliente; el FakeLFS registra lo que envía el cliente; la caída de
    LFS termina el hilo receptor (y NO se reconecta — P12); `stop_all_threads` lo
    termina y resetea; UDP end-to-end con datagrama real.
- **Fixture "LFS falso"** (`tests/conftest.py`, nuevo): clase `FakeLFS` — servidor TCP
  loopback que acepta una conexión, reproduce trazas de bytes hacia el cliente y
  registra lo recibido — expuesta como fixture `fake_lfs` para toda la suite.

**Decisiones tomadas:**
1. Los tests de packet_io congelan el comportamiento actual, incluidas las carencias
   ya registradas (P12 sin reconexión, pérdida silenciosa del resto del buffer al cerrar).
2. **Idioma de la API pública del core (pendiente desde S04): inglés en el core** —
   identificadores, docstrings y mensajes de error/log del código nuevo/refactorizado;
   español en docs/dev, tests, insims, commits y comunicación. Porqué: comunidad LFS
   internacional y eventual PyPI. El código viejo se traduce al tocarlo, sin pasadas
   masivas. Registrado en `MODUS_OPERANDI.md` § 5 y `PLAN.md` Fase 2.

**Estado del repo:** rama `refactor/estabilizacion`, suite **388/388 verde**.
**Fase 1: COMPLETADA. Fase 2: P11 (✅ validado en LFS por el usuario) y P13 hechos.**

**Próximo paso:** ver `ESTADO_ACTUAL.md` → P14 (config del paquete con defaults
internos; el core deja de importar `config.settings` del CWD). Pendiente del
usuario: validar P13 en LFS.

---

## S05 — 2026-07-02 — Fase 1: golden-bytes + tests de dispatch y loader (4/6 ítems)

**Qué se hizo (segundo bloque, misma sesión):**
- **Tests de dispatch de `InSimClient`** (`tests/test_client_dispatch.py`, 14 tests):
  orden de entrega master→módulos, aislamiento de errores por handler (uno que explota
  no corta a los demás), keep-alive reactivo (TINY.NONE se contesta con TINY.NONE),
  `_dispatch_lifecycle` (orden, aislamiento, módulos sin hook) y enrutado según
  `use_thread_pool` (inline vs executor.submit).
- **Tests del loader** (`tests/test_loader.py`, 29 tests) con InSims sintéticos generados
  en `tmp_path` (insim.json + app.py, sin sockets): carga simple, entry point `__init__.py`,
  caché, discover; **coup d'état caracterizado** (dependencia degradada a módulo, cadena de
  3 aplanada a `[n1, n0]`, master anterior limpiado); fallos (inexistente, sin entry point,
  sin clase InSimApp → error envuelto, rollback del trono tras fallo, versión insuficiente);
  **P20 caracterizado**: una dependencia rota se loguea y se SIGUE (el dependiente carga
  igualmente y `get_insim` devuelve None). Helpers `_parse_version`/`_check_version`
  parametrizados.
- **Hallazgo (ampliación de P20 en `DIAGNOSTICO.md`):** un InSim **sin `__init__.py`**
  (con entry point aparte) muere con error críptico — `spec_from_file_location(name, None)`
  devuelve None. Requisito no documentado; caracterizado en `test_sin_init_py_falla`.

**Qué se hizo (primer bloque):**
- Arranque según protocolo: rama al día, working tree limpio, suite base 233/233.
- **Golden-bytes de serialización** (`tests/test_golden_bytes_send.py`, 63 tests): fija los
  bytes exactos que produce la ruta real de encode de `send_packet()` (prepare →
  get_struct_string → `_extract_values` → struct.pack) para los **27 paquetes enviables**,
  con casos representativos (strings fijos/variables, truncado, padding a bloque de 4,
  sub-structs, listas variables, límite de 20 inputs en AIC...). Los bytes esperados se
  generaron con el código actual y se contrastaron contra la spec 0.8C5 (tamaños, Size,
  Type, offsets). Incluye test estructural parametrizado (Size=bytes/4, Type correcto).
- **Descubierto P21** (registrado en `DIAGNOSTICO.md`): el envío de **ISP_REO, ISP_HCP e
  ISP_IPB con bans está roto** — `_extract_values` no aplana listas de formato fijo
  (`repeat(...)`) ni tuplas anidadas y `struct.pack` recibe menos valores de los exigidos.
  Nadie los usa hoy, por eso no se había notado. Caracterizado con `pytest.raises`
  (`TestEnviosRotos`); se arreglará al unificar la serialización (P19, Fase 3).
- **Golden-bytes de decodificación** (`tests/test_golden_bytes_decode.py`, 20 tests): bytes
  construidos a mano según la spec → dataclass esperado para VER, TINY, SMALL, STA, NCN,
  CNL, MSO, BTC, BTT, NPL, MCI (2 CompCar), NLP (con padding a múltiplo de 4), CON, OBH,
  HLV, más el enrutado de `decode_packet` (vacío/tipo desconocido/Size incoherente → None)
  y un roundtrip encode→decode. Pasaron a la primera: el layout del código es fiel a la spec.
- Caracterizados de paso tres comportamientos actuales del decoder (documentados en el
  docstring del test): `.strip()` come espacios finales significativos (P19), las listas
  fijas se decodifican como `list` aunque el dataclass declare `tuple`, y los enums llegan
  como int crudo.

**Decisiones tomadas:**
1. Los golden-bytes **congelan el comportamiento actual** (incluso el discutible, como el
   string variable vacío de 0 bytes — P8 — o el strip del decoder): cambiarlo será un acto
   deliberado que actualice el test correspondiente, no un efecto colateral de un refactor.
2. P21 se caracteriza como excepción, no se arregla ahora (Fase 1 no cambia comportamiento);
   el arreglo va con P19 en Fase 3.

**Estado del repo:** rama `refactor/estabilizacion`, suite **359/359 verde**
(233 + 63 golden-send + 20 golden-decode + 14 dispatch + 29 loader).
Fase 1: **4/6 ítems completados**.

**Próximo paso:** ver `ESTADO_ACTUAL.md` → terminar Fase 1: packet_io con socket falso
(reensamblado TCP fragmentado/pegado, Size=0, cierre) + fixture "LFS falso".

---

## S04 — 2026-07-02 — Protocolo 0.8C5 + auditoría del core y plan profesional

**Qué se hizo:**
- El usuario reemplazó `docs/InSim.txt` por el nuevo de LFS, que resultó ser **solo un
  puntero de 6 líneas** a lfs.net/programmer. Se recuperó la spec completa **0.8C5** de
  `lfs.net/programmer/insim` (extraída del HTML) y se restauró como `docs/InSim.txt`.
- Diff spec vieja (0.8A) vs nueva (0.8C5): cambios acotados. **Framework actualizado**:
  - `ISP.SET=70` + dataclass `ISP_SET` (136 bytes, `Setup[120]` crudo) + registro en
    `INSIM_PACKETS` + stub `.pyi` regenerado.
  - `ISF.SET` (bit 12); `ISP_NPL.Sp2` → `RIFlags` + enums `RIF`/`SAI` + `RIF_SAI_SHIFTS`;
    `CCI.RETIRED`; `NLP_MAX_CARS` 40→48; `HOSTF` +6 valores (SHOW_FUEL..NO_FLOOD).
  - 12 tests nuevos (`tests/test_protocol_08c5.py`), incluida decodificación real de un
    IS_SET de 136 bytes. Suite: **233/233 verde**.
  - Fichas del tutorial actualizadas (nueva `ISP_SET.md`; ISI/MCI/NLP/NPL/SLC).
- **Nueva directiva del usuario:** revisar el framework, identificar problemas de diseño y
  hacer un plan para llevarlo a **nivel profesional** (usable por otros desarrolladores).
  Romper los insims existentes es aceptable.
- **Auditoría del core completa** (client, app, loader, io, sender, state, cli, packets):
  registrados **P11–P20** en `DIAGNOSTICO.md`. Los graves: P11 (InSimApp hereda de
  InSimClient; el "coup d'état" compensa esa herencia), P12 (sin reconexión: proceso
  zombie si LFS se cae), P13 (sockets/cliente como singletons de módulo), P14 (el core
  importa `config.settings` del CWD; `sys.path` hack en cli.py). Otros: API pública
  indefinida (P15), packaging/tooling (P16: `readme="README"` roto, sin CI/lint/mypy),
  código muerto (`_resolve_dependencies`, P17), envío UDP roto (P18), serialización
  duplicada (P19), loader traga errores (P20).
- **`PLAN.md` reescrito**: F1 red de seguridad del core (golden-bytes + sockets falsos) →
  F2 arquitectura (composición, sin globals, config del paquete, API pública) → F3
  robustez (reconexión, dispatch fuera del hilo IO) → F4 DX/packaging (ruff, mypy, CI,
  docs, PyPI opcional) → F5–F6 ai_control (el plan antiguo).
- Corregido de paso CLAUDE.md: `on_tick` corre a ~100 ms fijos (sleep hardcodeado),
  no cada `interval` ms (P17).

**Decisiones tomadas:**
1. La spec del protocolo se mantiene **versionada y completa** en `docs/InSim.txt` aunque
   LFS ya no la distribuya (fuente de verdad offline).
2. El core primero, `ai_control` después: no tiene sentido trocear `ai_control` sobre una
   API que va a cambiar (F2 rompe la herencia InSimApp→InSimClient).
3. `Setup[120]` de ISP_SET se modela como `list[int]` (`('B', 120)`), no como string
   (el decoder de strings corrompería datos binarios).

**Pendiente de decisión del usuario:** idioma de la API pública del core (recomendación:
inglés) y publicación en PyPI (Fase 4).

**Estado del repo:** rama `refactor/estabilizacion`, suite 233/233. Commits: spec 0.8C5,
soporte de protocolo, fichas del tutorial, auditoría + plan (docs/dev).

**Próximo paso:** ver `ESTADO_ACTUAL.md` → Fase 1: golden-bytes de serialización.

---

## S03 — 2026-07-02 — Cierre de Fase 0: limpieza de bajo riesgo

**Qué se hizo:**
- Arranque según protocolo: rama al día con origin, working tree limpio, docs leídas.
- **Eliminado `src/lfs_insim/utils_temp.py`** (P6): verificado con grep que nadie lo importaba.
- **Limpiado `config/settings.py`** (P5): import muerto de `ISF` fuera; `admin_pass` y
  `LFS_DIR` ahora se leen de env (`LFS_ADMIN_PASS`, `LFS_DIR`) con override local en
  `config/settings_local.py` (gitignorado; plantilla versionada `settings_local.example.py`;
  creado el local con los valores que estaban hardcodeados para no cambiar nada en esta máquina).
- **Anclada la ruta de `rutas_grabadas.txt`** (P6): `RUTAS_FILE = BASE_DIR / 'rutas_grabadas.txt'`
  en `nav_modes/route/manager.py` (antes ruta relativa al CWD). `import os` muerto eliminado.
- **Descubierto y resuelto P10**: `map_renderer.py` importa `matplotlib` sin declararlo en
  ningún sitio → cualquier import de `ai_control` fallaba en el venv (habría bloqueado la
  Fase 1). Declarado en `insim.json` (`python_dependencies`), añadido al extra `[dev]`,
  instalado en `.venv` (3.11.0), aclarado en CLAUDE.md.
- **Descubierto P9** (registrado, sin arreglar): `tools/setup_lfs.py` importa
  `DESIRED_LFS_CONFIG`, que no existe en `settings.py` → el tool está roto.
- Suite verificada en verde tras cada paso: **221/221**. Verificado también que `settings.py`
  funciona con y sin `settings_local.py`.

**Decisiones tomadas:**
1. **`interval` se queda en 10 ms** y se alinean las docs (README/CLAUDE.md decían 100 ms).
   Razón: la conducción/PID está afinada al ritmo real de 10 ms; cambiarlo sería un cambio
   de comportamiento, no limpieza (prohibido en Fase 0). Si se quiere 100 ms, será un cambio
   deliberado en Fase 2 (auditoría del hot-loop `on_ISP_MCI`).
2. **`rutas_grabadas.txt` sigue versionado** (datos del usuario, conviene sincronizarlos
   entre dispositivos). Migración a JSON pospuesta a cuando se toque `RouteManager`.
3. Los valores por máquina van en `config/settings_local.py` (gitignorado) con fallback a
   variables de entorno; la plantilla `settings_local.example.py` se versiona.

**Estado del repo:** rama `refactor/estabilizacion`, **Fase 0 completada**, suite 221/221.
Commits de la sesión: ver `git log` (limpieza + docs de cierre de fase).

**Próximo paso:** ver `ESTADO_ACTUAL.md` → Fase 1: infraestructura de fixtures sintéticos
y tests de caracterización de `navigation.py` / `traffic.py` / `physics.py`.

---

## S02 — 2026-07-01 — Entorno reproducible y primera suite verde (Fase 0)

**Qué se hizo:**
- Arranque según protocolo: en `refactor/estabilizacion`, `git pull` (al día), lectura de `docs/dev/`.
- Montado el entorno reproducible: `python -m venv .venv` (Python 3.14.6) + `pip install -e ".[dev]"`
  (pytest 9.1.1, `.venv` ya ignorado por `.gitignore`).
- Primera ejecución de la suite: **216/221 verdes**, 5 rojos en
  `tests/test_packet_base.py::TestValidateStringLengths` (padding de strings variables).
- Investigado a fondo (no se tocó código a ciegas): los **5 tests estaban mal, no el código**.
  Esperaban longitudes de `Msg` que **no** son múltiplo de 4, y uno incluso sin terminador null.
  El protocolo obliga a bloques múltiplo de 4 (`Size = bytes/4`), así que el código es correcto.
  Verificado ejecutando el `validate_string_lengths` real sobre cada caso.
- Corregidos los 5 tests para caracterizar el comportamiento real (expectativas + comentarios
  engañosos). Renombrado `test_empty_string_padded` → `test_empty_string_stays_empty`.
  Resultado: **`pytest` = 221/221 verde**.
- Registrado en `DIAGNOSTICO.md`: **P1 marcado RESUELTO**; añadido **P8** (caso borde de
  string vacío sin padding, decisión de diseño pendiente, riesgo bajo).

**Decisiones tomadas:**
1. Ante el conflicto test↔código, la fuente de verdad es el **protocolo LFS** (`Size = bytes/4`
   ⇒ `Msg` múltiplo de 4). Se corrigen los tests, no el código.
2. El comportamiento del string vacío (queda en 0 bytes, sin terminador) se **caracteriza tal
   cual** por ahora; si hay que cambiarlo, será un cambio de comportamiento deliberado (P8).

**Hallazgos clave:**
- La suite arranca en 0,2 s; base sólida para la red de seguridad de Fase 1.
- Los 5 tests rojos nunca se habían ejecutado (nacieron en rojo), no eran una regresión.

**Estado del repo:** rama `refactor/estabilizacion`. Cambio en `tests/test_packet_base.py`
(pendiente de commit al cerrar el hito, junto con las actualizaciones de `docs/dev/`).

**Próximo paso:** ver `ESTADO_ACTUAL.md` → seguir con la limpieza de bajo riesgo de Fase 0
(eliminar `utils_temp.py`, limpiar `settings.py`, anclar ruta de `rutas_grabadas.txt`).

---

## S01 — 2026-07-01 — Escaneo inicial y creación del sistema de contexto

**Qué se hizo:**
- Escaneo general del proyecto (estructura, core, `ai_control`, config, tests, git).
- Diagnóstico completo volcado en `DIAGNOSTICO.md` (7 problemas P1–P7 + inventario de lo sano).
- Plan por fases (0–4) en `PLAN.md`.
- Creado el sistema de contexto persistente en `docs/dev/`: `00_INDEX`, `MODUS_OPERANDI`,
  `ESTADO_ACTUAL`, `DIAGNOSTICO`, `PLAN`, `HISTORIAL`.
- Enganchado el arranque automático en `CLAUDE.md` (leer `docs/dev/` al iniciar sesión).
- Creada la rama **`refactor/estabilizacion`** para todo el trabajo de refactor; `main`
  queda intacta hasta el merge final.

**Decisiones tomadas (con el usuario):**
1. El contexto de trabajo se **versiona** en `docs/dev/` (no en `.claude/` local).
2. Se empieza por la **Fase 0 (Cimientos)**.
3. Red de seguridad para refactorizar = **tests de caracterización primero**.
4. Todo el refactor va en la rama **`refactor/estabilizacion`**; **merge a `main` solo
   cuando esté todo estable** (suite verde + validación en LFS).
5. **Sincronización por GitHub:** `git pull` al iniciar y `git push` al cerrar cada sesión
   (para continuar desde otro dispositivo). Push de la rama de refactor autorizado de forma
   permanente; merge/push a `main` sigue requiriendo permiso.

**Hallazgos clave:**
- Core sano; deuda concentrada en `ai_control`.
- Entorno no reproducible: paquete sin instalar y `pytest` ausente (Python sistema 3.14).
  221 tests sin poder ejecutarse.
- Lógica frágil (traffic/navigation/radar): la mayoría de commits recientes son fixes.
- `interval:10` en settings contradice los 100 ms documentados.

**Estado del repo:** partimos de `main` limpia (commit `131c966`). Creada la rama
`refactor/estabilizacion` y **commiteado** el sistema de contexto + enganche de `CLAUDE.md`
en **`52729c3`** (`chore(docs): sistema de contexto persistente y flujo de rama de refactor`).
Working tree limpio.

**Próximo paso:** ver `ESTADO_ACTUAL.md` → montar `.venv`, instalar deps, correr `pytest`.
