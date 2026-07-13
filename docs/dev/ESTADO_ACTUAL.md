# 📍 Estado actual

> Actualizado: **2026-07-13** — S36 (**sesión META: no toca el proyecto**): se destiló el sistema de trabajo de
> este repo en un **protocolo agéntico portable** (`.meta/agentic-protocol/`): un **prompt maestro** agnóstico de
> harness + la misma cosa como **skill de Claude Code** (`/agentic-protocol`) con un **chequeo de cierre
> ejecutable**. Commits `a1c77a9` y `6fda6bc`, pusheados. **No se tocó nada del framework** → suite intacta
> (773/773 de S35), ruff limpio, árbol limpio y en sync.
> **▶️ PRÓXIMO (sesión nueva, decidido con el usuario): APLICAR ESE PROTOCOLO A ESTE PROYECTO** — es su prueba
> de fuego, y este repo tiene justo los dos fallos que dice curar: (1) **partir este `ESTADO_ACTUAL.md`**
> (1031 líneas) en un handoff de ≤120 líneas, volcando lo viejo a `HISTORIAL.md`; (2) montar la **cola de
> validación** con todo lo que hay ⏳ pendiente de probar en LFS (ley nueva del ACC de S35, W4, los 4 fixes de la
> Fase 7 + el guard) — hoy está disperso en prosa y nadie sabe qué está realmente probado; (3) instalar
> `close_check.py`. Detalle en `PLAN.md § Tooling de trabajo`.
> **Después: Fase 8 — REDISEÑO DE LAS INTERSECCIONES.** El usuario las probó: *"funcionan, pero son difíciles de
> crear y su funcionamiento es regular"*, y trae un **diseño propio** (línea de detención + tiempo en el RoadLink;
> zonas por tiempo en vez de por área). Semilla de diseño y preguntas abiertas en `PLAN.md § Fase 8`; falta que el
> usuario explique **cómo quiere mapearlo en la UI**.
>
> _(S35, contexto previo: **3 bugs VIEJOS del radar con HUMANOS** (el stop-and-go) — ✅ **VALIDADOS en LFS**
> ("desaparecieron todos los tirones") — y **nueva ley de seguimiento del ACC** (al ir bloqueado se IGUALA al de
> delante, no se reduce; hueco mínimo mayor), ⏳ **pendiente de validar**.)_
>
> _(S34, contexto previo: Fase 7 · fix (3) — el radar perdía coches en la transición road↔roadlink (`3a628c3`)
> + guard de no-adelantar-dentro-de-un-cruce (`8af862d`) → **Fase 7 completa en código, 5/5 fixes**.)_
> **Causa raíz del fix (3):** la topología de la IA cambia ANTES que su posición — `navigation.py:551` la mete
> en el RoadLink en cuanto está a `TRIGGER_DIST_M` (**3,5 m**) de él —, y `_scan_lane_ahead` solo aceptaba coches
> en `mode.current_id` → dentro del enlace dejaba de ver al lento que aún tenía delante en la **vía que deja** y
> no veía a los que ya circulaban en la **de destino**. **Fix:** `_lane_chain_ids` ensancha "mi carril, delante"
> a la cadena **`from_road → link → to_road`**, acotada por una **ventana de transición** (25 m desde el nodo de
> entrada del enlace) — la ventana es lo que evita el **frenado fantasma** por tráfico de una transversal (el
> lookahead real es ≈83 m a 30 km/h). **Guard (commit aparte, revertible solo):** el gatillo `IDLE→EVALUATING` del
> FSM no miraba `current_type` → con los coches nuevos la IA intentaría **adelantar dentro del cruce** → el
> adelantamiento **solo se ABRE en un Road**.
> **▶️ AHORA TODO EL TRABAJO QUE QUEDA ES VALIDACIÓN EN LFS** (W4 + los 4 fixes de conducta + el guard). No hay
> más trabajo offline que bloquee el merge. Árbol limpio y en sync con `origin`.
>
> _(S33, contexto previo: fix (4) `is_closed`, fix (1) flip de enlace, fix del ceda-el-paso tembloroso, editor de
> reglas de prioridad de zonas en la UI, y el usuario creó la PRIMERA intersección → W4 desbloqueada.)_
> **Fix (4) (`d968abf`):** `overtake.py::_find_valid_overtake_lane` no comprobaba `is_closed` → la IA adelantaba
> por carril cerrado. Helper centralizado `MapRecorder.is_road_usable` en overtake + Filtro A. **Fix (1)
> (`1a8eaac`):** flip de intermitente en salidas RoadLink muy juntas — un re-plan en la misma vía
> (`fin_de_geometria`) re-tiraba `random.choice`; fix **pegajosa-si-válida** (`_choose_link` + `committed_link_id`
> en `_plan_next_link`). **Editor de prioridad de zonas (`a29fde3`→`5f9af3d`):** el detalle de una Zona en
> Elementos ahora deja editar `priority_rules` (antes solo por `!map set`); tras feedback del usuario, el alta usa
> el **mismo picker de vías** que crear un RoadLink/LatLink (slots Prio/Cede + lista) en vez de teclear ids.
> **Fix ceda-el-paso tembloroso (`73bbae7`):** en la intersección la IA hacía "gas a fondo mientras metía el
> freno de mano repetidamente" — la decisión de ceder no tenía histéresis y parpadeaba; como `speed_request=0`
> dispara el aparcado (freno de mano + motor OFF) y `>0` el gas a fondo, oscilaba a ~100 Hz. Fix: histéresis
> `_should_keep_yielding` + `mode._yield_hold_until` (1 s tras la última detección). Solo `orchestrator.py`, no
> toca la física. **El usuario creó la primera intersección** (`test1` en South City: cápsula + `priority_rules`
> `HAVEN_LANE_S22_a/b` > `SOUTH_CITY_STATION_s2`; commit `12c29a4`) → **W4 ya NO está bloqueada por `zones: 0`**.
> Suite **749/749**; ruff limpio; no tocan la API pública. **Próximo:** (a) **validar en LFS** el ceda-el-paso
> (W4) + los fixes (4)/(1)/histéresis; (b) **fix (3)** — radar olvida coches en la transición road→roadlink
> (extender la red de equivalencia del radar de S28 + matching `current→next→to_road`). Árbol limpio y en sync
> con `origin` tras el cierre de S33.
> **Rama de trabajo: `refactor/estabilizacion`.** Todo el refactor ocurre aquí; `main`
> queda intacta hasta el merge final (cuando el proyecto esté estable). **Sync por GitHub:**
> `git pull` al arrancar y `git push` al cerrar (permite continuar desde otro dispositivo).

## Estado

**S36 (2026-07-13) — META: protocolo agéntico portable (`.meta/agentic-protocol/`). No toca el proyecto.**
A petición del usuario, sesión **ajena al framework**: destilar *cómo se trabaja aquí* en algo que pueda darse a
**cualquier IA agéntica en cualquier proyecto**. Diagnóstico del sistema actual: funciona porque cura los **tres
fallos estructurales** de un agente — **amnesia** (el contexto vive en archivos versionados), **ceguera** (el
`MODUS §4` declara "no puedo ejecutar LFS" → el humano es el oráculo de verificación) y **temeridad** (red de
caracterización antes de tocar lógica frágil). Y cuatro agujeros detectados **en nuestro propio sistema**, que el
protocolo corrige: (1) el handoff **no tiene tope** y se ha vuelto un segundo historial (1031 líneas, se lee
entera **cada sesión**); (2) lo ⏳ pendiente de validar en LFS **está disperso en prosa** → no hay cola; (3) el
"hecho" no es comprobable por máquina; (4) no está escrito **qué NO se lee al arrancar** (esta misma sesión gastó
40k tokens leyendo medio `ESTADO_ACTUAL.md`). **Entregado:** `AGENTIC_PROTOCOL.md` (maestro agnóstico: instalador
ejecutado por la IA — idioma → auditoría → entrevista → generación → enganche → entrega de las frases; reglas;
plantillas) y `skill/agentic-protocol/` (skill de Claude Code, ya instalada en `~/.claude/skills/` de este
equipo). **Principio rector nuevo (del usuario):** los archivos de contexto tienen **un solo escritor, la IA** —
el humano **nunca los edita**, solo habla y los lee para auditar. **Único capaz de verificar de verdad:**
`close_check.py` (árbol limpio, todo pusheado, tope de `STATE.md`, próximo paso y cola de validación presentes) —
probado contra este repo, y **falló señalando exactamente lo que denuncia** (1031 > 120 líneas; sin cola de
validación). **No requiere validación en LFS** (no toca código).

**S36 (cont.) — lo que la propia sesión enseñó, y la regla que salió de ahí.** Al usuario se le escaparon cinco
huecos del documento y **los cazó él** (preguntando: *"¿cómo arranca cada sesión?"*, *"¿se lo lee entero?"*,
*"¿dónde se acumulan las instrucciones fijas?"*); un barrido final destapó tres más. **No fue context-rot ni falta
de modelo** (el barrido los encontró en dos minutos con el mismo modelo y contexto, solo cambiando de modo): es la
**asimetría entre escribir y revisar** — los fallos eran **ausencias**, y una ausencia es invisible desde dentro
porque el hueco está relleno en la cabeza del autor. **Cura, una sola regla (`§6`):** para entregables que ningún
comando puede verificar, "hecho" = **recorrerlos simulando su uso** (no releerlos) + **un lector que no sepa lo
que querías decir** + **si el mismo contenido vive en dos sitios, comprobarlo con un comando**. De ahí sale
**`parity_check.py`**: la duplicación maestro↔skill ya se había separado sola (numeración distinta según el
vehículo) y al automatizar la comprobación aparecieron **3 derivas más** invisibles a ojo → **17 secciones
idénticas, 4 divergencias declaradas**. Commits `a1c77a9`, `6fda6bc`, `9f30739`, `439ca35` + el de cierre.

**S35 (2026-07-13) — 3 bugs VIEJOS del radar con HUMANOS (el stop-and-go). ✅ VALIDADO en LFS.** Probando lo de
S34, el usuario reportó que la IA iba **"a saltos: ahora sí, o no... aún no era"**, hasta **pararse del todo y
rearrancar**, en los TRES escenarios (recta, cruce, ceda-el-paso) — siempre con alguien delante. Pista clave al
preguntarle: **solo lo había probado con él mismo (un humano) delante, no con otras IAs**. **Se midió antes de
tocar**, y eso evitó dos arreglos equivocados: la hipótesis "el ACC oscila" quedó **refutada** simulando el lazo
cerrado con el ACC real (converge suave), y la de "se le asigna un LatLink" quedó refutada **por el eje del
carril** (0/5848 nodos del mapa real). La causa apareció leyendo el código: **(1)** `_scan_lane_ahead` comparaba
`other_node_index` contra `mode.node_index`, que **no significan lo mismo** — el de la IA es el nodo **objetivo**
(la captura dinámica lo adelanta hasta 5 m antes de llegar) y al humano se le asigna el **más cercano** →
`idx_diff = -1` a alguien que va **delante** → se le toma por un coche de detrás y **se le pierde**. Reproducido:
**60 de 200 pasos ciego**, en ventanas **periódicas de ~3 m por nodo** (~0,35 s de ceguera cada ~1,2 s a
30 km/h) → sin nadie delante → `velocidad_base` → gas; al recuperarlo → ACC → freno; y con `speed_request=0` la
física **aparca** (freno de mano + motor OFF) → el tirón. **(2)** La **caché de humanos es compartida** entre
todas las IAs y guardaba un índice de nodo válido solo para **quien escaneó** → una IA en otra vía dejaba un `-1`
y la de detrás del humano lo leía como "va detrás". **(3)** Al humano se le asignaba **cualquier enlace más
cercano, incluido un LatLink** (la tira que une dos carriles, por la que nadie circula y que corre casi paralela):
medido en South City, **a 1 m del eje —conduciendo normal— el 4,9% de los puntos** lo hacía invisible (con el fix,
**0,5%**). Lo revelador: **`navigation.py:361` ya lo hacía bien** (solo un RoadLink puede desbancar a la vía); las
dos copias del radar **se habían dejado la comprobación del tipo** → no es rediseño, es alinear el radar con la
regla canónica. En `_scan_target_lane` era peor: decide si el carril está libre para adelantar → un humano
descentrado era invisible y **la IA se le echaba encima**. Los tres bugs son **viejos** (nada que ver con el fix
(3) de S34) y **solo afectan a humanos** — por eso el tráfico IA-IA se veía bien. Commits `d6785a4` y `87a1142`.

**S35 — Nueva ley de seguimiento del ACC (⏳ validar en LFS).** A petición del usuario: **(a)** hueco mínimo un
poco mayor y **(b)** que al ir bloqueado la IA **iguale** la velocidad del de delante **en vez de reducirla** ("si
no, terminan oscilando"). (a) → dos diales con nombre: `PARADA_ABSOLUTA_M` 5→**7 m** (suelo duro) y
`MIN_GAP_FLOOR_M` 5→**8 m** (suelo de la distancia de seguridad cuando el time-gap se queda corto: marcha lenta y
colas); el time-gap a velocidad (2 s) no se toca. (b) **obligaba a cambiar la forma de la ley, no un número**: con
la banda de seguimiento igualando, la vieja zona roja (0 de golpe) quedaba debajo como un **acantilado** → habría
vuelto a oscilar ahí. La rampa de frenado **baja a una franja de EMERGENCIA** (bajo `critical`, donde reducir sí
es legítimo) y el seguimiento pasa a ser **igualación pura** → ley **CONTINUA en los tres bordes**. Verificado en
**lazo cerrado** (offline, ACC real): converge a un **punto fijo**, iguala exactamente la velocidad y el hueco se
estabiliza (8 m en marcha lenta; 11,1 m a 20 km/h). La caracterización del ACC (S19/S21) se **reescribió**: cambio
de comportamiento **deliberado**. Commit `35870bb`.

**S35 — dos avisos operativos.** (1) Un `Get-Content | Set-Content` de PowerShell **corrompió la codificación**
de `test_traffic.py` (mojibake en todos los acentos) y se coló en 2 commits; reparado y verificado contra la
versión limpia (`cb9c3b3`). **No usar `Get-Content | Set-Content` sobre fuentes.** (2) La suite pasó de 43 s a
100 s: NO era regresión, era **el InSim del propio usuario** comiendo un núcleo. Aparecían **dos** procesos
`lfs-insim run ai_control` a la vez → si son dos clientes conectados, ambos mandan órdenes a los mismos coches.

**S34 (2026-07-13) — Fase 7 · fix (3): el radar perdía coches en la transición road↔roadlink. FASE 7
COMPLETA EN CÓDIGO (⏳ validar en LFS).** Último bug de conducción del handoff de S29. **Diagnóstico
(rastreado en el código):** `radar.py::_scan_lane_ahead` solo aceptaba coches cuyo `current_id` fuera el
nuestro (`same_segment`), con una única excepción (`in_our_next_link`: yendo por un Road, ve a los que ya
entraron en su próximo RoadLink). La causa raíz es que **la topología de la IA cambia ANTES que su posición**:
`navigation.py:551` la mete en el RoadLink en cuanto está a `TRIGGER_DIST_M` (**3,5 m**) de él, mucho antes de
separarse físicamente de la vía → (a) dentro del enlace dejaba de ver al coche lento que aún tenía delante en
la **vía que deja** (si se podía seguir de frente, lo chocaba) y (b) no veía a los que ya circulaban en la
**vía de destino**. **Fix (`3a628c3`):** función pura `_lane_chain_ids` que ensancha "mi carril, delante" a la
cadena **`from_road → link → to_road`**, acotada por una **ventana de transición** medida al **nodo de entrada**
del enlace (`_LINK_TRANSITION_WINDOW_M` = 25 m, ajustable): en un **Road**, el próximo RoadLink **siempre**
(= el `in_our_next_link` de antes) y —solo en la ventana— su **vía de destino**; dentro de un **RoadLink**, la
**vía de destino siempre** (estamos comprometidos: es nuestro carril) y —solo en la ventana— la **vía que
dejamos**. **Por qué la ventana (decisión de diseño):** sin ella, con el lookahead real (`max(15, v·10)` ≈ **83 m
a 30 km/h**) la IA frenaría por coches de una **transversal** que nunca va a seguir → **frenado fantasma en cada
cruce**; fuera de la ventana el match vuelve a ser estricto, como antes. **Guard, commit aparte (`8af862d`,
decidido con el usuario):** `_scan_lane_ahead` no alimenta solo al ACC sino también al **gatillo `IDLE→EVALUATING`**
del FSM, que **no comprobaba `current_type`** → con los coches nuevos la IA se dispararía a **adelantar dentro del
enlace** (donde `_find_valid_overtake_lane` busca carril en los laterales de la vía que ya dejó, con el
`node_index` del enlace aplicado a los nodos del road) → el fix pasaría de evitar un choque a provocar una maniobra
absurda. **El adelantamiento solo se ABRE en un Road**; uno ya en curso no se toca. Va **aparte para poder
revertirlo solo** si en LFS resulta demasiado conservador. **Red primero (18 tests):** helpers puros (8);
integración de los **2 choques reportados** + los **bordes de la ventana** (6); la **red de equivalencia del radar
de S28 EXTENDIDA** al escáner dentro de un RoadLink (fuzz rejilla vs. barrido lineal — la cadena admite muchos más
candidatos); y la **primera red sobre `_update_traffic_behavior`** (2: el gatillo es determinista, el tiempo solo
entra en cooldowns con 0.0). **Verificada en ROJO** contra el código viejo: los 2 choques se reproducen, el guard
`non_empty ≥ 5` del fuzz cae a **0** (el fuzz no es vacuo) y sin el guard el FSM sale en `EVALUATING` dentro del
enlace. Suite **767/767**; ruff limpio; `lfs-insim list` OK. **No toca la API pública.**

**S33 cont. (2026-07-13) — Fix del ceda-el-paso tembloroso (histéresis del yield; ⏳ validar en LFS).**
Probando la primera intersección, el usuario reportó que la IA entraba en "acelerar a fondo mientras mete el
freno de mano repetidamente". **Diagnóstico (rastreado en el código):** al ceder, `velocidad_final` baja a 0 →
`behavior.speed_request = 0.0` (`orchestrator.py:490`); la física (`physics.py:107‑119`) trata `speed_request==0`
como **aparcar** → `HANDBRAKE=MAX` + `IGNITION=OFF`; y `>0` dispara encendido + gas a fondo desde parado. La
decisión de ceder (`orchestrator.py`) **no tenía histéresis** y se soltaba al primer tick sin prioritario
detectado → el `speed_request` parpadeaba 0↔base y con él la física oscilaba entre aparcar y acelerar a ~100 Hz.
**Fix (opción elegida por el usuario: histéresis, sin tocar la física):** predicado puro
`_should_keep_yielding(detected, hold_until, now)` + `mode._yield_hold_until`; detectar un prioritario renueva el
hold (`YIELD_HOLD_S=1.0 s`) y sin detección se sigue cediendo hasta que expira → un dropout de 1 tick ya no
suelta el freno. Descartada (opción B, para más adelante): que la parada temporal NO apague motor/freno de mano
(toca la física de TODAS las paradas → más validación). Red primero: `TestShouldKeepYielding` (3). Commit
`73bbae7`. Suite **749/749**.

**S33 cont. (2026-07-12/13) — Editor de reglas de prioridad de zonas en la UI + primera intersección (W4).**
A raíz de que el usuario no podía asignar vías prioritarias al crear una zona (la UI solo exponía `zone_id`/
`nodes`/`radius_m`; las `priority_rules` solo se fijaban por `!map set <zona> priority_rules add;A,B`), se añadió
un **editor de `priority_rules` en el detalle de una Zona** (pestaña Elementos). Primera versión (`a29fde3`) con
dos TypeIn; **tras feedback del usuario** se rehízo (`5f9af3d`) para que el alta use el **mismo picker de vías**
que crear un RoadLink/LatLink: botón "+ Anadir regla" → sub-pantalla con slots "-> Prio"/"-> Cede" + lista
paginada de vías (elegir de la lista elimina typos → validación = "dos vías distintas"), + la lista de reglas con
su Quitar. Reutiliza el picker (`_ui_road_picker_*`, `_UI_CID_TI1/TI2`) y `_cmd_set` (add/del) del recorder. Red
primero: `test_map_ui_zone_priority.py` (9 tests). Se usó la skill `ai-control-map-ui`. **El usuario creó la
PRIMERA intersección del proyecto** (`test1` en South City: cápsula 2 nodos + reglas `HAVEN_LANE_S22_a/b` >
`SOUTH_CITY_STATION_s2`; protegida en `12c29a4`, antes hubo `A13_MonumentServices` en `638698e`) → **W4 ya NO
está bloqueada por `zones: 0`.** Solo UI del insim de ejemplo → no toca la API pública.

**S33 (2026-07-12) — Fase 7: fix (4) `is_closed` + fix (1) flip de enlace (red primero; ⏳ validar en LFS).**
Se retomó la Fase 7 (3 bugs de conducción freeroam del handoff de S31/S32) y se abordaron **(4) y (1)** por
impacto; **(3) queda para sesión nueva** (el más pesado; decisión con el usuario). **Fix (4) — no adelantar
por vía cerrada (commit `d968abf`):** el único hueco de conducción de `is_closed` era
`traffic/overtake.py::_find_valid_overtake_lane`, que no lo comprobaba → la IA se metía en un carril cerrado
para adelantar. Auditados todos los consumidores (Filtro A de `_calculate_next_link` y spawn/`get_location_context`
ya filtran vía `ignore_closed_roads`; los 3 call-sites del radar y la UI del editor NO filtran a propósito).
Fix: helper centralizado `MapRecorder.is_road_usable(road_id)` (existe ∧ no cerrada) en overtake y en Filtro A
(refactor sin cambio de conducta, cubierto por `test_destino_cerrado_se_descarta`). Red primero:
`test_carril_vecino_cerrado_no_se_usa` (rojo→verde). Suite **734/734**. **Fix (1) — `next_link` pegajoso
(commit `1a8eaac`):** en dos salidas RoadLink muy juntas, la IA comprometía `next_link` (con intermitente) y en
el último momento saltaba a la otra. Causa: al llegar al final de la vía sin cruzar su enlace (`fin_de_geometria`),
un re-plan **en la misma vía** re-tiraba `random.choice` en `_calculate_next_link`; la asimetría es geométrica
(`_is_link_reachable_ahead` desde el último segmento), **no** RHT/LHT (el intermitente de RoadLink sale de
`link.indicators`, no de `_get_indicator_to_use`, que gobierna LatLinks). **Decisión de diseño (pregunta con
recomendación, MODUS §6):** el usuario eligió **"pegajosa-si-válida"** (conservar el enlace comprometido solo si
sigue siendo opción válida; nunca dejar sin salida) frente a "commit-on-blinker" (congelar aun no siendo
alcanzable → riesgo). Fix: `_choose_link` + `committed_link_id`; `_plan_next_link` lo pasa en el re-plan de misma
vía (rama `else`), no en el cruce a vía nueva. Red primero: 2 tests de pegajosidad + 1 de wiring (el de wiring
mostraba el flip `R1->R2 ⇒ R1->R3`; rojo→verde). Suite **737/737**. Ambos: `ruff` limpio, `lfs-insim list` OK,
**no tocan la API pública**; como son conducta, **⏳ requieren validación en LFS** (se acumulan con W4 y el fix (3)).

**S32 (2026-07-12) — Herramienta "Link auto" en la UI de mapeo (petición del usuario, fuera de plan;
⏳ requiere validación en LFS).** A petición del usuario, se **pausó la Fase 7** para añadir una utilidad
de mapeo. Nuevo botón **"Link auto"** en la pestaña **Grabar** de `map_ui.py`, justo debajo de "RoadLink"
(CID 118; el panel idle se reorganizó a filas T=21/31/41/52/63 para hacerle sitio). Graba un **RoadLink
sin teclear origen ni destino**: (1) al pulsarlo, `_map_ui_start_auto_link` captura el road de ORIGEN de
la vía más cercana al coche que se graba (`recording_plid`, humano o IA) con `get_location_context`,
siembra el nodo de origen, activa el autograbado y entra en fase `recording`; (2) al **Finalizar**,
`_map_ui_finalize_auto_link` detecta el road DESTINO por la posición actual, cierra el trazado con un nodo
en el destino, **congela** el autograbado y evalúa el nombre `origen[suf]->destino[suf]`; (3) si el nombre
está **libre** → pantalla de **confirmación** (nombre final + Aprobar / Cancelar); (4) si **ya existe** →
pantalla de **conflicto** con **3 opciones**: añadir **sufijo** a origen y/o destino y **Recomprobar**
(re-evalúa; si sigue chocando, avisa), **Sobrescribir** el existente (actualiza sus nodos) o **Cancelar**.
Cancelar está en todas las pantallas. **Decisiones:** nombre "Link auto" (no "AUTOGRABAR", que chocaría
con el toggle "Auto" de captura de nodos); el estado del flujo vive en `current_recording["auto_phase"]`
(recording→confirm/conflict) para **sobrevivir a cerrar/reabrir el menú** sin estado nuevo que resetear;
reutiliza `_cmd_rec_end` del recorder para materializar el RoadLink (crear o sobrescribir nodos). **Red
primero (MODUS §3):** `tests/insims/ai_control/test_map_ui_auto_link.py` (**13 tests**) sobre la `AIControl`
del harness + `MapRecorder` real con `get_location_context` de verdad (roads A@(0,0)/F@(100,0), coche que
se mueve de A a F). Suite **723/723** (710 + 13); `ruff check` + `ruff format --check` limpios en lo tocado;
`lfs-insim list` OK. Solo lógica de UI del insim de ejemplo → **no toca la API pública**. **Arranque
(protección de mapas §1.2):** South City sin commitear (871 inserciones en `south_city.json` + render) →
respaldo + commit `data(ai_control)` `32a54d2` + push antes de nada.

**S32 (2026-07-12) — 3 ajustes de UI en la pestaña Grabar (pedido del usuario; ⏳ requiere validación en
LFS).** Tres cambios pequeños y cohesivos, con red primero (`test_map_ui_grabar_prefs.py`, 10 tests):
(1) **toggle "Trafico" movido de Mapa a Grabar** (CID 108): la norma por defecto de las nuevas vías se
ajusta ahora donde se graba (fuera de `_map_ui_draw_tab_mapa`/`_map_ui_click_mapa`, entra en el idle de
Grabar). (2) **Campo "Vel. grabar (km/h)"** (TypeIn CID 129) en Grabar: fija
`MapRecorder.default_speed_limit_kmh` (nuevo, default 30), que `_cmd_rec_end` aplica al crear un `RoadSegment`
(antes siempre 30 fijo); parseo en `on_ISP_BTT` (revierte si es inválido/≤0). (3) **"Auto" pegajoso**: el
usuario reportó que **cancelar un road desmarcaba Auto** — se quitó el `auto_recording_enabled = False` de
`_cmd_rec_cancel` y de la rama sin-nodos de `_cmd_rec_end` (es una preferencia del usuario, no debe apagarse).
El **Link auto** dejó de apagar Auto al finalizar/commit: la captura se **congela por fase** (gate nuevo en
`update_recording`: si `current_recording["auto_phase"]` no es `None`/`"recording"`, no añade nodos), así la
preferencia Auto se mantiene intacta. Suite **733/733** (723 + 10); ruff limpio; `lfs-insim list` OK. Solo UI
del insim de ejemplo → **no toca la API pública**. **Aparcado (su propia sesión):** editor **MASIVO** de
elementos (buscador + multi-selección + aplicar-a-N) → `TODO` en `_map_ui_draw_tab_elementos` + Ideas del PLAN.

**S32 (2026-07-12) — primera skill de proyecto + paso prioritario de tooling (con el usuario).** A raíz de
que los ajustes de UI de ai_control son un pedido recurrente (coste de *orientación* alto: `map_ui.py` tiene
3200+ líneas), se creó la skill de proyecto **`ai-control-map-ui`** (`.claude/skills/ai-control-map-ui/
SKILL.md`): un playbook con la estructura estable de la UI (rangos de CID 108–165 contenido / 166+
persistente, patrón `_map_ui_draw_tab_*` ↔ `_map_ui_click_*`, TypeIn vía `_ui_input_buffer`, receta para
añadir botón/pantalla, harness de tests `ai_control`, convenciones). Escrita en **estructura/convenciones, no
números de línea** (para que no envejezca). Una skill on-demand es mejor vehículo que CLAUDE.md (que se carga
siempre) para conocimiento solo-a-veces-relevante. Para **sincronizarla por git** entre dispositivos se
des-ignoró `.claude/skills/` en `.gitignore` (el resto de `.claude` sigue local). **Nuevo paso prioritario en
PLAN** (§ "Tooling de trabajo — Skills"): evaluar qué otros flujos merecen skill (candidatas: cierre/arranque
de sesión) y ratificar la convención de gestión. **Se usará/probará la skill** en el próximo ajuste de UI.

**S31 (2026-07-11) — Fase 6 · cierre de W3 (Frente A, offline; NO requiere LFS).** Último bloque de W3.
(1) **FSM de adelantamiento revisado** (`traffic/orchestrator.py` + `overtake.py`):
IDLE→EVALUATING→OVERTAKING→RETURNING con cooldowns, estructura sólida, sin tocar la conducta. Cleanup
seguro: `_finish_overtake` tenía un parámetro `name` sin usar (resto de logs eliminados) y el orquestador
le pasaba `_n = ai.ai_name`, alias que solo alimentaba esas 2 llamadas → fuera ambos (el test ya llamaba
sin `name`). (2) **Código muerto borrado:** `is_target_ahead_and_in_lane` (`geometry.py`) — confirmado sin
uso en producción por grep — y su clase `TestIsTargetAheadAndInLane` (`test_geometry.py`, 5 tests). (3) Los
**4 marcadores `[!] OPTIMIZACIÓN`** de `radar.py` → comentarios normales (fuera el prefijo `[!]` y la
numeración). (4) **P4 — `base.py` adelgazado:** un script de auditoría del grafo de llamadas
(`self.<m>` vs `def <m>` por fichero) probó que **12 de los 32** métodos del contrato `_MixinBase` son
**self-local** (solo se llaman dentro de su propio mixin) → fuera del contrato *cross-mixin* (quedan **20**
genuinos, anotados con quién los llama); imports `Coordinates`/`PIDController` huérfanos, fuera. Todo bajo
`TYPE_CHECKING` → cero runtime/test. **Honestidad del contrato, NO desacople real:** las 20 llamadas
cruzadas siguen; el desacople profundo del "God object" es arquitectónico (orquestador sin red) → PENDIENTE
(DIAGNOSTICO § P4). (5) **Docs:** CLAUDE.md (composición real con `_MapUIMixin`, fachada `_TrafficMixin`
sobre `traffic/`, contrato `_MixinBase`, FSM, rejilla del radar) + DIAGNOSTICO § P4. **W3 CERRADO** (los
splits de `map_ui`/`map_recorder` ya estaban aplazados a post-merge, S27) → **Fase 6 completa salvo W4**
(LFS, bloqueada por `zones: 0`). Suite **699/699** (704−5); ruff limpio; `lfs-insim list` OK. **No toca la
API pública.** Commits de W3: `5bf394f` (código) + `788a791` (docs), pusheados, CI verde.

**S31 (2026-07-11) — Herramienta "Apunta" en la UI de mapeo (2ª petición, no planeada; requiere LFS
para validar).** A petición del usuario, nueva utilidad en la pestaña **Info** de `ai_control` como **6º
tipo del overlay whereami** (`ahead`, toggle "Apunta"): indica la **vía más cercana a la que apunta el
morro del coche** —distinta de la que estás pisando— y **a qué distancia**, para ayudar a mapear.
**Cómo:** geometría pura **`find_road_pointed_at`** (ray-cast 2D en `nav_modes/freeroam/geometry.py`) que
lanza un rayo desde la posición en la dirección del morro y devuelve el road cuyo segmento cruza más cerca
(excluyendo el actual = el más cercano a la posición) + su distancia; el rumbo del morro se saca del
heading LFS con la MISMA fórmula que el orquestador de IA (`(-sin, cos)`). Reutiliza TODO el overlay
pineado de S30 (persiste entre pestañas, refresca en `on_tick`, se redibuja en reconexión); toggle CID
118, fila del overlay 172; la fila de toggles de Info pasa de 5 a 6 (ancho 30→26 para caber). **Red
primero (MODUS §3):** `find_road_pointed_at` con 9 tests (acierto/detrás/más-cercano/exclusión/max-dist/
paralelo/vector-nulo/diagonal/fuera-de-segmento) + 2 de integración en `test_map_ui_whereami.py` (toggle
CID 118 → tipo `ahead`; compute end-to-end reporta la vía apuntada y su distancia, excluyendo la actual).
Suite **710/710** (699 + 9 + 2); ruff limpio; `lfs-insim list` OK. Solo lógica de UI del insim de ejemplo
→ **no toca la API pública**; como es conducta/UI, ✅ **validado en LFS por el usuario** ("funciona
perfectamente"). Commit: el de la herramienta Apunta (S31).

**S30 (2026-07-11) — retoque de UI de `ai_control` (whereami → overlay fijo; fuera del plan) +
validación en LFS del fix 2 de S29.** Sesión corta a petición del usuario, **sin continuar el trabajo
de refactor**. (1) **Fix 2 de S29 VALIDADO en LFS:** el usuario confirmó de entrada que el watchdog de
fin de vía → espectadores "funciona correctamente" → ya no está pendiente de validación (la Fase 7
sigue sin abordar y sus 3 bugs sí requieren LFS). (2) **Overlay whereami pineado:** el whereami de la
pestaña **Info** (WA Road/RLink/LLink/Zone/Regla) era un panel dentro del menú (CIDs 153-157, en el
rango de contenido que se limpia en cada redibujado) → ahora es un **overlay fijo anclado a la
mitad-derecha** de la pantalla que **persiste al cambiar de pestaña y con el menú cerrado**, y **solo
se quita deseleccionándolo** en Info (al quitar el último se borra). **Cómo:** CIDs propios
**166-171** (título "Ubicación" + 1 fila por tipo activo) **fuera del rango de contenido** (108-165);
estado nuevo **`_ui_whereami_ucid`** (dueño del overlay, independiente del `_ui_ucid` del menú, que
pasa a `None` al cerrar); el whereami **ya no se resetea al reabrir** el menú (`_init_ui_state` lo
inicializa una sola vez, con guard `hasattr`); `_map_ui_close` **redibuja** el overlay tras el
`BFN.CLEAR`; `_map_ui_compute_whereami` usa **el UCID del overlay** (no el del menú); `on_tick`
refresca (solo texto) **aunque el menú esté cerrado**; y `on_reconnect` (app.py) lo **redibuja** (P12:
LFS pierde los botones al caer la conexión). Posición/tamaño en constantes ajustables (`_WA_PIN_L=150`,
`_WA_PIN_W=48`, `_WA_PIN_ROW_STEP=8`; centrado vertical en `_map_ui_pinned_whereami_top`, T≈100).
**Red primero (MODUS §3):** `test_map_ui_whereami.py` (**7 tests** sobre la `AIControl` del harness que
captura envíos: dibujo a la derecha con CIDs >165, persistencia entre pestañas/cierre/reapertura,
borrado al deseleccionar, refresco con menú cerrado, UCID correcto). Suite **704/704** (697+7); `ruff
check`+`format` limpios; `lfs-insim list` OK. **Validado en LFS por el usuario** ("funciona a la
perfección"). Solo lógica de UI del insim de ejemplo → **no toca la API pública** del framework.
**Nota de UX conocida:** con el menú abierto en Info y paneles desplegados, el overlay puede solaparse
con la esquina inferior-derecha del menú (ambos ~L150+); con el menú cerrado —el caso principal— queda
limpio. **Commit:** el de cierre de S30.

**S29 (2026-07-11) — Fase 7 (NUEVA): bugs de conducción freeroam + fix 2 (fin de vía → espectadores;
implementado y verificado, ✅ VALIDADO en LFS en S30).** El usuario, conduciendo en LFS, reportó 4
bugs del modo Freeroam de `ai_control` y pidió resolver **uno ahora** y aparcar el resto en el plan
(delegando el cuándo). **Fix 2 (hecho):** una IA que llegaba a un fin de vía sin `next_link` se
quedaba clavada a 0 km/h para siempre — el anti-stuck de `_update_freeroam_navigation` trata
`speed_request<5` como parada *intencionada* y nunca la castiga, y el único spec de fin de vía saltaba
solo en el tick exacto de captura del último nodo (frágil). **Watchdog nuevo** en `navigation.py`:
predicado puro **`_is_dead_end_stop(mode, speed_kmh)`** (True solo si parada real <`DEAD_END_SPEED_KMH`
2 km/h, `next_link_id` None, road no circular y sin adelantamiento en curso → distingue el callejón
del semáforo/tráfico, que SÍ conserva `next_link`) + temporizador `mode._dead_end_since`; si persiste
`DEAD_END_TIMEOUT_S` (4 s) → `_cmd_spec`. Se **centralizó el spec** en el watchdog (quitado el inline
de `fin_de_geometria` que, con el watchdog, doble-spec-eaba y mandaba un MSL de error). **Red primero
(MODUS §3):** `TestIsDeadEndStop` (6 tests: fin de vía, parada de tráfico con `next_link`, en
movimiento, adelantando, circular, sin localizar). Constantes ajustables (2 km/h / 4 s). Suite **697**
(691+6); `ruff check`+`format` limpios. Solo lógica del insim de ejemplo → **no toca la API pública**;
como es conducta, **requiere validación en LFS**. **Otros 3 fixes → nueva Fase 7 (con diagnóstico
preciso):** (1) flip de enlace en salidas muy juntas (el intermitente se sobreescribe; asimétrico) —
`_calculate_next_link` re-planifica y cambia la elección comprometida; (3) el radar
(`traffic/radar.py`) olvida a los coches de delante al pasar road→roadlink (los choca) y no ve a los
de dentro al entrar por un roadlink; (4) `is_closed` a medias — **hueco cazado**: `overtake.py::
_find_valid_overtake_lane` NO comprueba `is_closed` (adelanta por carril cerrado) → auditar todos los
consumidores. **Arranque (protección de mapas §1.2):** South City con 2 roads `is_closed:true→false`
sin commitear → respaldo + commit `dcca07a` + push antes de nada.

**S28 (2026-07-11) — Fase 6 · W3: índice espacial de VEHÍCULOS para el radar (implementado y
verificado, NO requiere LFS).** Ataca el hallazgo O(N²) de la auditoría S22 (ex-6b, plegado en W3).
Los 3 barridos del radar (`traffic/radar.py`: `_scan_lane_ahead`, `_scan_target_lane`,
`_scan_return_lane_gap`) recorrían **todos** los vehículos por IA (O(N) por IA → **O(N²) global**).
Ahora consultan una **rejilla dinámica** (`SpatialHashGrid`, reutilizado de S23 como grid separado
del estático de geometría) que se construye **una vez por MCI** en `on_ISP_MCI` (`_build_vehicle_grid`),
indexando por PLID la posición 2D de cada vehículo con telemetría (`players`/`ais` son disjuntos por
PLID → índice 1:1). **Extracción segura (MODUS_OPERANDI §3):** en cada barrido cambia SOLO la línea
del `for` → `_iter_radar_candidates(cx, cy, radio)`; el radio = el mismo culling de cada método
(`max_dist+15` en los dos primeros, `max_dist*2` en el de retorno) y **todos los culls/filtros
por-vehículo quedan intactos**. La rejilla devuelve un **SUPERCONJUNTO** de los vehículos dentro del
círculo (la caja `ids_within` lo contiene) y el barrido aplica su culling exacto → **salida
bit-idéntica**. **Sin rejilla** (`_vehicle_grid=None`, p. ej. un barrido llamado directo en un test)
**cae a iterar todos** en el mismo orden que antes → camino de referencia. **Nuevo en el grid:**
`SpatialHashGrid.ids_within(px,py,radius)` — consulta de **REGIÓN** (todos los ids de las celdas que
solapan la caja del radio), complementaria a `ring_ids` (vecino más cercano); +7 tests unitarios.
**Red de equivalencia (la caracterización del radar "como unidad" que pedía el plan):** fuzz de 40
semillas × 3 barridos con mezcla aleatoria de IAs+humanos, comparando bit a bit el barrido CON
rejilla vs. SIN (referencia); + un test de "candidato diagonal" (coche detectado en una celda
distinta a la del escáner, que una consulta de solo-celda-central perdería). +4 tests. **Diseño
clave:** la equivalencia por CONSTRUCCIÓN (superconjunto + filtros intactos), no por reimplementar
la matemática — mismo patrón que el índice de geometría de S23. **Benchmark (tick = todas las IAs
barriendo, mapa 1000×1000):** `sin_grid` crece cuadrático, `con_grid` lineal → **2,5× @N=24, 4,2×
@N=48, 5,2× @N=64**, creciendo con la densidad. **Celda 50 m** (sweep: meseta plana 40-80 m; por
debajo penaliza el sondeo de celdas vacías, por encima infla candidatos al agruparse las IAs).
Reset del grid en `on_reconnect` (P12). **Verificación:** suite **691/691** (680 + 11); `ruff check`
+ `format --check` limpios (repo entero); `lfs-insim list` OK; 3.9-safe (`dict[int, tuple]` PEP 585,
`from __future__ import annotations`). Solo estructura + rejilla, salida idéntica → **no requiere
validación en LFS**. **Pendiente de W3:** FSM de adelantamiento (`traffic/overtake.py`) + borrar
`is_target_ahead_and_in_lane` (código muerto S24) + **P4** (adelgazar `base.py`) + docs. **Arranque
(protección de mapas §1.2):** South City sin commitear (189 roads/13.480 nodos, `zones: 0`) →
respaldo + commit `data(ai_control)` + push ANTES del pull, que trajo S27 del otro equipo (mergeó
limpio, ortogonal).

**S27 (2026-07-10) — Fase 6 · W3 (1/2): split de `traffic.py` + P7 (implementado y verificado, NO
requiere LFS).** Al medir los ficheros al arrancar, el PLAN estaba **desfasado**: habían crecido
~70% desde S23 (`map_ui` 1841→**3161**, `map_recorder` 1604→**2520**, `traffic` 1084→**1348**).
**Decisión de alcance (recomendación explícita, el usuario la eligió): recortar W3 pre-publish** →
entran `traffic.py` + radar + FSM + P4 + P7; **`map_ui.py` y `map_recorder.py` se aplazan a
post-merge** (son tooling **offline** de edición de mapas: no son el framework publicado, no tocan
el runtime de conducción ni la API pública, y no tienen red de caracterización → partirlos no
aporta nada al release y retrasa el merge, que ya espera a W4). **(1) P3 parcial — paquete
`traffic/`:** un módulo por responsabilidad — `radar.py` (393), `orchestrator.py` (468),
`overtake.py` (239), `zones.py` (80), `cruise_control.py` (80), `paths.py` (51); `_TrafficMixin`
queda como **fachada** que compone los submixins (los tests ya ejercitaban `AIControl`, así que el
reparto les es transparente). **Extracción segura de verdad:** los cuerpos se movieron **por rango
de líneas con un script** (nunca a mano) y se demostró con snapshot `inspect.getsource`
antes/después: **cuerpo y firma byte-idénticos** en los 18 métodos, `AIControl` resuelve a la
**misma función**, superficie intacta (**182 atributos**), cero líneas perdidas. Prepara el terreno:
el índice espacial aterriza en `radar.py` y el FSM a revisar vive en `overtake.py`. **(2) P7 —
nombres de `behavior.py`:** `target_speed_kmh_use`/`target_speed_kmh` y `target_point_use`/
`target_point_m` → **`speed_request`/`speed_resolved_kmh`** y **`point_request`/`point_resolved`**
(los `*_request` los escriben comandos y navegación; los `*_resolved` los calcula `physics.py` en
cada MCI). 93 sustituciones en 9 ficheros por **palabra completa**, cero restos. **Colisión cazada:**
`_estimate_overtake_distance` tenía un *parámetro* homónimo `target_speed_kmh` que **no es el campo**
(es la velocidad del coche adelantado) → revertido y renombrado a `target_vehicle_speed_kmh`; era
justo la ambigüedad que P7 denuncia. De paso: `point_request` ya declara el `tuple[float, float]`
que `physics.py` aceptaba; fuera los comentarios residuales de `behavior.py` (el resto de marcadores
`[!]`, zona a zona); `base.py` dice en qué submódulo vive cada método de tráfico y su docstring de
arquitectura ya incluye `_MapUIMixin`; y el docstring de `test_traffic.py` decía que los tests
**congelan** el "PARCHE DE SEGURIDAD MATEMÁTICO" del ACC, cuando **S21 lo eliminó** — corregido.
**Verificación:** suite **680/680** tras cada paso (el split es estructura pura: la red existente
ES la prueba); `ruff check .` + `format --check .` limpios (102 ficheros); `lfs-insim list` OK;
3.9-safe. Solo estructura y nombres → **no requiere validación en LFS**.

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
perfiles) y W3 (refactor interno + radar) HECHOS** (S24/S25/S26/S27/S28/**S31**). **W3 CERRADO en S31**
(FSM revisado, código muerto fuera, `base.py` adelgazado por P4, docs de arquitectura). **Fase 6 completa
salvo W4** (LFS). **Fase 7 COMPLETA EN CÓDIGO (S34): los 5 fixes de conducción están hechos.**

**FASE ACTIVA REAL (S35): Fase 8 — rediseño de las intersecciones.** Al validar en LFS, el usuario dio por
buenos los fixes del stop-and-go, pero las **intersecciones "funcionan, pero son difíciles de crear y su
funcionamiento es regular"** → no se dan por buenas, y **W4 no se cierra con el modelo actual**. Trae un diseño
propio; la semilla y las preguntas abiertas están en **`PLAN.md § Fase 8`**. El merge espera a que las
intersecciones estén rehechas y validadas.

**Recorte de W3 (S27, con el usuario):** los splits de `map_ui.py` (3161) y `map_recorder.py`
(2520) **salen del pre-publish** y pasan a post-merge (ver PLAN § Ideas). Son tooling offline,
sin red de tests, y no tocan ni la API pública ni el runtime de conducción → no deben retrasar
el merge/publish.

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
(init) → ~~W3~~ ✅ (refactor interno + radar; **CERRADO en S31**). Todo en la rama; un solo merge a
`main` cuando esté publish-ready + validado, luego publish. Detalle en PLAN § Fase 6.

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

**✅ W3 CERRADO (S27 + S28 + S31)** — S27: **split de `traffic.py`** en el paquete `traffic/` (fachada
`_TrafficMixin` + 6 submixins; extracción segura byte-idéntica) + **P7** (`speed_request`/
`speed_resolved_kmh`, `point_request`/`point_resolved`). S28: rejilla del radar (abajo). **S31: FSM de
adelantamiento revisado, código muerto `is_target_ahead_and_in_lane` borrado, 4 marcadores
`[!] OPTIMIZACIÓN` de `radar.py` limpiados, `base.py` adelgazado por P4 (contrato `_MixinBase` 32→20,
honestidad del contrato — desacople profundo pendiente) y docs de arquitectura (CLAUDE.md/DIAGNOSTICO).**
**Recortado el alcance** (S27): `map_ui.py` y `map_recorder.py` salen a post-merge.

**✅ RADAR HECHO (S28)** — índice espacial de VEHÍCULOS: rejilla dinámica (`SpatialHashGrid`)
construida 1×/MCI; los 3 barridos consultan el vecindario (`_iter_radar_candidates`) en vez de los N
vehículos → O(N²)→~O(N) (benchmark 2,5×@24, 5×@64). Extracción segura (solo cambia el `for`; salida
bit-idéntica) + red de equivalencia (fuzz grid vs. lineal) + `ids_within` en el grid. Suite 691.

**✅ FIX 2 HECHO (S29)** — fin de vía sin salida → espectadores. Watchdog en `navigation.py`
(`_is_dead_end_stop` puro + `mode._dead_end_since`, 4 s → `_cmd_spec`); red `TestIsDeadEndStop` (6).
Suite 697. **Pendiente validación en LFS.** Los otros 3 bugs de conducción → **Fase 7** (ver PLAN).

**▶️ EMPEZAR AQUÍ: Fase 8 — rediseño de las intersecciones. Es una sesión de DISEÑO primero, no de código.**
Leer **`PLAN.md § Fase 8`**: lleva la propuesta del usuario (línea de detención + tiempo colgados del RoadLink;
zonas por tiempo en vez de por área), por qué es mejor que el modelo actual, y las **preguntas abiertas** que hay
que cerrar ANTES de tocar código (a qué coches se vigila, si hacen falta los dos mecanismos, compatibilidad del
JSON del mapa con el South City actual, y qué pasa con las `priority_rules` de hoy). **Falta que el usuario
explique cómo quiere mapearlo en la UI** — preguntárselo al arrancar; usar la skill `ai-control-map-ui`.

**Pendiente de validar en LFS (acumulado; el usuario lo mira cuando juegue):**
- **Ley de seguimiento nueva del ACC (S35)** — que la IA **iguale** al de delante sin descolgarse ni oscilar, y
  que el **hueco** (7 m suelo duro / 8 m en cola) se note bien. Diales: `PARADA_ABSOLUTA_M` (cruise_control) y
  `MIN_GAP_FLOOR_M` (orchestrator).
- **Fix (3) + guard (S34)** — que no choque en los cruces: (a) al entrar en un enlace sigue frenando por el lento
  que se quedó de frente en la vía que deja; (b) ve a los que ya circulan en la vía de destino; (c) **no** frena
  por fantasmas lejos del cruce; (d) **no adelanta dentro de un cruce** (si resulta demasiado conservador, el
  commit `8af862d` se revierte **solo**, sin tocar el radar). Dial: `_LINK_TRANSITION_WINDOW_M` (25 m, radar.py).
- **Fix (4) y fix (1) (S33)** — no adelantar por vías cerradas; el intermitente no hace flip en salidas juntas.
- **Ceda-el-paso (W4)** — *"funciona, pero regular"*: **no se da por bueno**; es lo que motiva la Fase 8. No
  perder tiempo afinando el modelo viejo.
- *(✅ ya validados: los 3 bugs del radar con humanos (S35, "desaparecieron todos los tirones"), Apunta (S31) y
  fin de vía → espectadores (S29).)*

**Backlog offline (opcional, si no hay LFS a mano; no bloquea el merge):**
1. **Desacople profundo de `base.py` (resto de P4):** reducir las 20 llamadas cross-mixin reales / romper
   el "God object". Es refactor arquitectónico de riesgo y el orquestador `_update_traffic_behavior` **casi no
   tiene red** (S34 le puso la primera: 2 tests del gatillo de adelantamiento; el resto del método sigue
   descubierto) → caracterizar más antes de tocarlo. Ver DIAGNOSTICO § P4.
2. **Tipado gradual** (quitar overrides de `[tool.mypy]` módulo a módulo al tocar cada uno): `packets`
   (dataclasses de protocolo), `insim_loader` (fricción con `importlib`: `ModuleSpec | None` sin
   None-check + kwargs inyectados en InSimApp — merece None-checks reales, no `type: ignore`),
   `insim_packet_decoders`/`utils` (2 errores puntuales cada uno). No urge; mypy no bloquea.
3. **Idea DX de Fase 4:** el connect inicial fallido imprime un traceback feo (`exc_info=True` +
   re-raise) — valorar mensaje limpio y/o `connect_retry` para arrancar el insim antes que LFS. (La pista
   de ISI rechazado ya está hecha; el fallback de cfg.txt está en PLAN § Ideas.)
4. **Post-merge:** partir `map_ui.py` (3161) y `map_recorder.py` (2520) — resto de P3, con red primero
   (PLAN § Ideas).

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
- **W4 (ceda-el-paso): PROBADA en LFS (S35) y NO superada.** El usuario creó la intersección `test1` y la
  condujo: *"funcionan, pero son difíciles de crear y su funcionamiento es regular"*. **No se cierra el gate
  afinando el modelo actual** — el problema es el modelo de datos (reglas de prioridad globales por pares en vez
  de reglas locales colgadas de la maniobra). Se rehace en la **Fase 8**; el merge espera a eso.

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
