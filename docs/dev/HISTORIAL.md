# 📜 Historial de sesiones

> Bitácora append-only. Una entrada por sesión, la más reciente arriba.
> Formato: fecha, qué se hizo, decisiones, commits.

---

## S46 — 2026-07-17 — Fase 8: 8.6.5 (UI de mapeo) hecho; suite verde otra vez (914)

**Arranque limpio:** árbol limpio, ya en la rama, `git pull` sin novedades, 0 fichas U pendientes,
nada que proteger. Se leyó la skill `ai-control-map-ui` antes de abrir `map_ui.py` (manda el
handoff) y el contrato entero de `PLAN.md § 8.6`.

**Dos huecos del diseño → dos preguntas por selector, ANTES de escribir código** (el handoff lo
exigía: "si aparece algo que el diseño no previó, parar y preguntar"). Las dos recomendadas se
aceptaron:

1. **`[Auto]`: ¿cuánto retrocede?** El diseño decía "justo antes del primer cruce real" sin decir
   cuánto, y el punto de conflicto cae en el **eje** de la road que cruzas (parar ahí = morro en
   mitad del carril). → **dial nuevo `yield_auto_setback_m` = 5.0**, no constante, para afinarlo
   en LFS sin tocar código. El retroceso va **por el trazado** (`auto_yield_point`): en un link en
   L dobla la esquina; en línea recta el punto se habría salido del link.
2. **La tabla de la zona: "auto-poblada" Y "borrable" se contradicen.** → se repuebla **solo** al
   grabar el polígono y con **[Re-detectar]**; `autodetect_zone_roads` conserva el `YieldType` de
   las que sobreviven. Si se repoblara al dibujar, los falsos cruces borrados volverían al salir
   y entrar del detalle.

**Lo que se hizo (red primero en cada pieza):**

- **Geometría (7 tests):** `auto_yield_point` + `_point_at_arc_2d` / `_project_on_segment_2d` en
  `yielding.py`. El cruce se **proyecta** antes de medir (viene del eje de otra road, no cae
  exacto sobre el link). Link más corto que el retroceso ⇒ primer nodo.
- **Backend del recorder:** `_cmd_set` (`yield_type` con validación del vocabulario + tabla
  `roads` con `set;Via,TIPO` / `del;Via` / `clear`; fuera `yield_line`, `priority_rules`,
  `yield_zone_id`) · `_cmd_rec_end` (zona ⇒ **≥3 puntos** + auto-poblado, con el mensaje diciendo
  que los puntos se descartan) · `_cmd_check` al modelo nuevo (polígono, tabla, tipo-sin-punto,
  punto-huérfano, "ninguna vía es NONE") · `!map info` (tabla y punto) · `autodetect_zone_roads`.
- **UI del link (24 tests):** toggle + `[+ Marcar punto]` + `[Auto]` + `[Borrar]` + T con float
  efectivo y `[Usar default]`. **Murieron** el grabador por fases (`type="yield_line"`,
  `auto_phase`), la pantalla `ask_t` y el picker de zonas: −266 líneas netas en ese bloque.
- **UI de la zona (24 tests):** polígono (reusa el grabador normal `type="zone"`) + T + tabla con
  toggle por road, `[X]` y `[Re-detectar]`. **Murió** el editor de `priority_rules`: −102 líneas.
  Fichero de tests renombrado `test_map_ui_zone_priority.py` → `test_map_ui_zone_yield.py`
  ("priority" es vocabulario muerto).
- **Reparto de CIDs** documentado y sin solapes: zona **134-151**, link **152-160** (nunca
  coexisten: un detalle es de un tipo o del otro). 134-139 eran de la pestaña Info y se reutilizan
  por la convención del módulo (el contenido se borra al cambiar de pestaña).

**El bug que el grep destapó y la suite NO:** `map_ui.py::_map_ui_compute_whereami` seguía leyendo
`ctx.zone_radius`, borrado del modelo en S45 ⇒ **AttributeError en cuanto pineabas el overlay de
zona**. Ningún test lo cubría. Se arregló (`zone_inside`, nuevo en `LocationContext`, que solo es
True dentro de un polígono de verdad) **y se le escribió red**: 4 tests nuevos, incluido
`!map whereami zone` por su camino real. Esa era exactamente la clase de trampa que el aviso
"puede petar con AttributeError" del handoff anunciaba.

**Dos tests míos estaban mal, no el código** (se corrigieron los tests, y ambos documentan ahora
una decisión real): (a) `[Auto]` en un link que no cruza nada **sí** coloca punto — el de unión con
la `to_road` es un punto de conflicto más (S45), así que para antes de la **incorporación**; el
caso sin punto es el link colgado (su `to_road` no existe). (b) un `rec_end` inválido **descarta**
los puntos: es el contrato de `_cmd_rec_end` para todos los tipos desde antes del 8.6 (un `finally`
limpia `current_recording`; el test viejo se llamaba literalmente `..._descarta`). No se tocó —
solo se hizo explícito en el mensaje; si molesta en LFS, es su propio bloque.

**Verificación:** `ruff check` + `ruff format` limpios · **pytest 914 pasan / 0 fallan** (los 9
rojos que S45 dejó a propósito han caído: eran el trabajo a medias, como estaba escrito) ·
`lfs-insim list` carga los 4 InSims · `close_check.py` → PASS.

**Consecuencia:** se **levanta la restricción de S45**: ya se puede mapear en LFS. Sale la ficha
**U9** (validar la herramienta rediseñada). No bloquea el 8.6.6 (el render no toca la UI), pero
conviene hacerla pronto: el 8.6.7 se apoya en poder grabar el polígono.

**Commits:** el de esta sesión (geometría + backend + las dos UIs + skill + docs).

---

## S45 — 2026-07-17 — Fase 8: 8.6 a medias (modelo + geometría + conducta del link); UI y render fuera

**Arranque limpio:** árbol limpio, ya en la rama, `git pull` sin novedades, 0 fichas U pendientes.
Nada que proteger (ningún mapa sin commitear, por una vez).

**Se implementó el diseño S44 de abajo arriba, red de tests primero en cada sub-bloque:**

1. **8.6.1 Modelo** — `YieldType` (`NONE|YIELD|STOP`) como **str-enum** (para que el JSON del mapa
   se lea a ojo: `"YIELD"`, no un `2`). `RoadLink` = `yield_type` + `yield_point` (un punto) +
   `yield_time_s`. `IntersectionZone` = polígono + `yield_time_s` + `roads: Dict[str, YieldType]`.
   **Borrados** `yield_line`, `yield_zone_id`, `radius_m`, `priority_rules`. 13 tests
   (`test_map_persistencia.py`, rehecho).
2. **8.6.2 Geometría** — `segment_intersection_2d` en `geometry.py` (genérica) y, en
   `traffic/yielding.py`, `link_conflict_points` + `derive_yield_line` + `roads_touching_polygon`.
   27 tests nuevos (`test_yielding_geometria.py`).
3. **8.6.3 Conducta del link** — `_yield_threat_detected` reescrito contra los puntos de conflicto;
   **la rama de zona murió**. `_stop_pending` (orquestador) implementa el `STOP`. 40 tests.

**Decisiones tomadas (con su porqué):**

- **Los campos muertos se borran YA (8.6), no en el 8.7.** El PLAN se contradecía: el diseño S44
  dice "mueren" y el punto 8.7 —escrito en S43, antes del diseño— reclamaba su retirada. Se
  resolvió a favor del 8.6: el end state es idéntico, la convivencia ya se descartó en S38, el
  loader filtra claves desconocidas (así que `south_city.json` carga igual) y `test1` ya estaba
  inerte ⇒ no se pierde nada en el juego. **No se paró a preguntar** porque no es una variante del
  diseño, solo el orden de los estados intermedios.
- **`has_yield` exige tipo Y punto** (un toggle sin punto no tiene línea que derivar ⇒ no cede).
- **La `from_road` no aporta punto de conflicto** y **el punto de unión con la `to_road` se añade a
  mano**: el trazado ACABA en la `to_road`, no la atraviesa, así que su cruce es un caso degenerado
  que la intersección de segmentos no garantiza. El diseño ya lo llamaba "uno más".
- **Caché de puntos de conflicto** (`get_link_conflict_points`, perezosa, clave
  `(link_id, tol. Z)`): cruzar un link contra 223 roads no cabe en el hot loop (AUDITORIA_HOTLOOP).
  La invalidan `_invalidate_road_index()` y `_invalidate_link_conflicts()` (nueva, en el rec_end de
  links).
- **El 8.6.4 (conducta de la zona) se mueve DESPUÉS de la UI y pasa a 8.6.7**: sin grabador de
  polígonos no hay forma de probarla en LFS (`test1` es una cápsula de 2 nodos, inerte).
- **Cierre a medias, pactado con el usuario por selector** (opción "cerrar y abrir sesión nueva"):
  quedaba UI + render, `map_ui.py` es grande y tiene skill propia, y el contexto de la sesión ya
  iba largo. Se prefirió handoff limpio a arriesgar context-rot justo en la parte que ya fue
  "funciona, a mejorar" (U8).

**La prueba de que el rediseño hace lo que promete:** la clase `TestVigiladosDeLaZona` (que
verificaba que una zona referenciada AMPLIABA la vigilancia a un tercer ramal, R3) se convirtió en
`TestVigiladosPorGeometria`: **el mismo escenario pasa sin zona ninguna**, porque el trazado del
link cruza R3 en ~(5, 97.3) y la geometría lo detecta sola. Es exactamente la promesa del diseño
("esto es lo que hace innecesaria la zona"), ahora en un test. Se añadió también el caso del puente
(R3 elevada 10 m ⇒ no se vigila, por la tolerancia en Z).

**Verificación:** `ruff check` limpio; **pytest 888 pasan / 9 fallan**. Los 9 son de la UI vieja
(`test_map_ui_link_yield.py`, `test_map_ui_zone_priority.py`), que edita campos ya borrados: es el
trabajo a medias, no una regresión, y caen con el 8.6.5. **CI rojo esperado** en esta rama hasta
entonces. `close_check.py` → PASS.

**Consecuencia asumida y avisada:** hasta el 8.6.5, **mapear en LFS puede petar** (`map_ui.py` y
restos de `map_recorder.py` tocan campos borrados). Conducir es seguro: la conducta está migrada
entera.

**Commits:** el de esta sesión (modelo + geometría + conducta + docs).

---

## S44 — 2026-07-17 — Diseño del 8.6 CERRADO Y APROBADO (sin código) + protección del remapeo S22

**Arranque:** `git status` traía otra vez mapas sin commitear (remapeo de la zona S22, tocado esa
misma mañana). Protegido según MODUS §1.2 sin preguntar: backup fuera del repo → commit `0140815`
→ push. Contenido: **+5 road_links** (Vermilion/Victory/Commercial/Kenton), **−5** (los de
Arcade↔Commercial), 2 modificados (total sigue en 374); **+3 lateral_links** (40 → **43**); roads
(223) y zones (1) intactos. Eso tumbó `test_map_persistencia::test_south_city_carga_intacto` — es
**caracterización**, así que se re-basó el conteo (como en S42 con `c7fc2b2`). Suite **855/855**.

**Sesión de diseño puro**, la que S43 dejó apalabrada. Todo decidido con el usuario por selector.
El resultado **se apartó mucho de lo que S43 recomendaba**, y merece la pena registrar el camino
porque el valor está en los descartes:

1. **Matriz N×N → rango → nada.** Se propuso sustituir la matriz de pares del usuario por un
   **rango por vía** (N toggles en vez de N²; se pierden prioridades circulares, que no existen en
   carreteras). Aprobado. Más tarde el propio rango se disolvió: el vocabulario acabó siendo el
   **mismo `NONE|YIELD|STOP`** del link, con lo que "rango" desapareció como concepto.
2. **El modelo híbrido de S43 (zona = quién cede a quién sobre los links) se descartó entero.** El
   usuario aclaró el malentendido de fondo: **las zonas no tienen nada que ver con los links**. Una
   zona resuelve el caso que el link NO puede resolver — **coches que van de recto**, cada uno por
   su road, donde las roads se cortan sin que medie ningún link: nadie toma un enlace y chocan en
   mitad del cruce. Claude había entendido lo contrario y **retiró su recomendación**.
3. **De ahí sale el principio rector: DOS MECANISMOS ORTOGONALES**, que no se referencian jamás
   (link = el que maniobra; zona = el que cruza recto). **`yield_zone_id` se borra.**
4. **El link vigila todas las roads que su trazado pisa** (idea del usuario), con tolerancia en Z
   para no confundir un puente. Eso le da solo lo que antes le daba el `yield_zone_id`.
5. **`yield_line` polilínea → `yield_point`, un solo punto** (el punto implica la línea,
   perpendicular a la tangente). Simplifica datos, UI (se acaba el grabador por fases del 8.4) y
   el auto: **Auto** coloca el punto justo antes del primer cruce real.
6. **`radius_m`: rehabilitado y vuelto a matar en la misma sesión.** Al decir el usuario "para antes
   de entrar en la zona", Claude dedujo que el borde volvía a hacer falta ⇒ propuso recuperar el
   círculo/radio. El usuario corrigió: **no hay radio aparte**, el único umbral es el **tiempo** al
   **borde más cercano**, y la zona es un **polígono grabado** (**≥3 puntos**, sin máximo). Claude
   se retractó. `radius_m` y `priority_rules` **se borran**.
7. **`STOP` como toggle explícito** (petición del usuario, nombres en inglés): parada real (v≈0),
   ~1 s de espera y luego evalúa como `YIELD`. La declaración deja de ser implícita ("tiene línea").

**Decisiones registradas:** diseño completo en `PLAN.md § Fase 8, bloque 8.6`, con su sección
**"Qué cambió respecto a lo previsto"** para que nadie relea S43 como vigente. **Limitación aceptada
y escrita:** con dos niveles, **dos roads `YIELD` que se cruzan en la misma zona no se ceden entre
sí**; si aparece en LFS, la salida es el rango numérico. **Config nuevo:** `yield_line_width_m`,
`yield_stop_hold_s`, `yield_z_tolerance_m`.

**Consecuencia asumida:** el 8.6 **invalida parte del 8.4 (UI) y del 8.5 (render)** — cambia el
modelo de datos que ambos pintan. Es el precio de rediseñar tras el veredicto de U8, no una
regresión.

**Verificación:** sin código de producción → `pytest` **855/855** (el único cambio de test es el
re-baseo del conteo). `close_check.py` → PASS.

**Commits:** `0140815` (mapa S22 + re-baseo del conteo) + el commit de docs de esta entrada.

---

## S43 — 2026-07-15 — Validación U3–U7/U8 + re-plan: rediseño de la cesión (diseño pendiente)

**Contexto:** el usuario hizo sus deberes de `ACCIONES_USUARIO` y trajo veredictos + feedback de
mejora. Sesión de **validación + re-plan, sin código** (a petición suya: opinar, planear y dejar
el diseño para una sesión nueva).

**Veredictos (fichas cerradas → cola a 0):**
- **U3** (ley del ACC), **U4** (radar en transición road↔roadlink), **U5** (guard: no adelantar
  en cruce), **U6** (no adelantar por vía cerrada), **U7** (intermitente sin flip): **todos OK**.
  → **Fase 7 queda validada y cerrada.**
- **U8** (UI de mapeo del 8.4): **"funciona, a mejorar"** — el flujo va bien, pero con pegas y
  peticiones (como fue W4). Se cierra con veredicto; las mejoras pasan al bloque de rediseño.

**Feedback del usuario sobre la cesión (los 4 frentes del rediseño 8.6):**
1. **`yield_time_s`**: el TypeIn muestra el texto literal `"default (4)"` cuando el valor es
   `None` — debería ser un float.
2. **`yield_zone_id`**: no entiende qué es ni para qué sirve. (Hoy: "vigila ADEMÁS el punto de
   conflicto de esta zona", sin prioridades — `traffic/zones.py`.)
3. **Auto-`yield_line`**: con tanto mapeo, quiere un botón que cree la línea de detención sola
   (no perfecta, pero que sirva en la mayoría).
4. **Zonas con tabla auto + toggle**: en vez de añadir a mano, al crear una zona detectar los
   roads que la cruzan y ofrecer una matriz *toggle* de prioridades; poder borrar roads (falsos
   cruces a distinta altura: puentes) sin ignorar del todo la Z (pendientes).

**Análisis de Claude (opinión, no diseño cerrado):**
- (1) y (3) son cambios acotados y claros. (2) y (4) **reabren el modelo de la Fase 8**: el punto
  4 **revive parcialmente las `priority_rules`** que S38 retiró (decisiones 2 y 7), pero
  auto-pobladas — que era donde estaba el dolor real, no en el concepto.
- Modelo híbrido propuesto (a aprobar): **`yield_line` = DÓNDE paras** (geometría, auto/manual);
  **tabla de zona = QUIÉN cede a QUIÉN** (auto + toggle); así **`yield_zone_id` cobra sentido**
  ("qué tabla gobierna este link"). Retos a resolver en el diseño: auto-detección de cruces XY +
  chequeo de Z; UI de la matriz N×N en botones de LFS; y cómo convive con el "quien tiene
  `yield_line` cede" actual.

**Decisiones de proceso:**
- **8.6 pasa a ser "Rediseño de la UX/modelo de cesión"**, con flujo **DISEÑAR → APROBAR →
  EJECUTAR** (no tocar código hasta aprobar, como S38). Migración y validación se posponen a
  **8.7/8.8** (antes 8.6/8.7): migrar `test1` con la UI actual, que va a cambiar, sería trabajo
  tirado. Frentes + recomendaciones capturados en `PLAN.md § Fase 8, bloque 8.6`.
- **Sesión nueva para el diseño**: esta jornada ya trae arranque + 8.5 completo + validación;
  el diseño de (4) merece cabeza fresca. Lo siguiente, literal, es **planear → diseñar → aprobar**
  el rediseño; ejecutar vendría en la sesión posterior si se aprueba.

**Verificación:** sin código → `pytest` sigue en **855/855** (S42). `close_check.py` → PASS.

**Commits:** el commit de docs de esta entrada (veredictos + re-plan; ACCIONES/PLAN/ESTADO/HISTORIAL).

---

## S42 — 2026-07-15 — Fase 8: bloque 8.5 (render de la cesión) + protección de mapa al arrancar

**Arranque:** `git status` mostraba mapas sin commitear (nuevo mapeo de `south_city`: vías
`COMMERCIAL_LANE_S22…` + su render). Protegidos según protocolo (MODUS §1.2): backup fuera del
repo → commit `4cfc95e` → **rebase** sobre los 3 commits de S41 subidos desde el otro equipo
(no tocaban el mapa: cero conflictos) → push. Los `.md` en disco eran S40; tras el pull se
trabajó sobre S41.

**Hecho (código) — bloque 8.5, en el orden del MODUS §3 (estructura → comportamiento):**
- **Seam puro y testeable**: se extrajo `_draw_elements(ax, data, road_lw, link_lw)` (dibuja
  roads/zonas/lateral/road_links/cesión sobre un axes y devuelve los bounds; sin figura, límites,
  leyenda ni IO) y `_road_bounds(data)` (pre-pase de span). `generate_map_image` queda como
  orquestador (carga → span → seam → límites/leyenda/guardado). **Verificado byte-idéntico**:
  md5 del render de `south_city` idéntico antes y después de la extracción, y también idéntico al
  PNG commiteado (misma versión de matplotlib en los dos equipos).
- **Dibujo de la cesión** (red en rojo primero): color reservado nuevo `YIELDLINE_COLOR = "m"`
  (magenta) añadido a la convención; cada `yield_line` no vacía de un RoadLink se pinta como
  línea de detención (magenta grueso + marcadores en los extremos, `zorder` alto) rotulada con su
  **T** en el centro; las **zonas** rotulan su T en la etiqueta (`_fmt_yield_t`: `None`⇒`def`,
  valor⇒`<n>s`). Los links sin cesión y las zonas no dibujables no pintan nada.
- **17 tests nuevos** (`test_map_renderer.py`): 10 de caracterización del dibujo actual (verdes
  antes de tocar) + 7 de cesión (nacidos en rojo). Afirman sobre los artistas de matplotlib
  (`ax.lines`/`ax.patches`/`ax.texts`) sin generar PNGs. Verificado visualmente además con un
  render de demostración de datos sintéticos (magenta legible, T y zona correctas).
- **`test_map_persistencia.py`**: re-basados los conteos de `south_city` (222/328/28 → **223/374/40**)
  como consecuencia del nuevo mapeo del arranque. Es una caracterización sobre datos vivos: se
  re-basa cuando el usuario amplía el mapa.

**Decisiones (con su porqué):**
- **Seam extraído ANTES de añadir comportamiento** (MODUS §3): permite caracterizar el render
  actual con tests y probar byte-identidad; el dibujo de cesión se apila encima sobre terreno
  verde. *Rechazado:* testear `generate_map_image` de una pieza (escribe un PNG a ruta fija junto
  al módulo; solo se podría afirmar "existe el fichero").
- **Magenta reservado, no un color de la paleta**: la `yield_line` es semántica (dónde paras para
  ceder), como zona/lateral/roadlink; debe tener color propio y los roads deben excluirlo.
- **La parte "en Elementos" del diseño (decisión 9) NO añade lienzo nuevo**: el overlay whereami
  es texto (road/link/zona más cercanos), no geometría; el detalle del RoadLink ya muestra la
  cesión textualmente desde el 8.4. El 8.5 es el render PNG.
- **No se regeneran los 3 PNG commiteados**: ningún mapa actual tiene `yield_line` ni zona
  dibujable, así que el código nuevo dibuja idéntico al viejo (comprobado). Regenerar solo metería
  ruido binario. Las líneas de cesión aparecerán en el render cuando el 8.6 migre `test1`.

**Verificación:** `test_map_renderer.py` 10 verdes (caracterización) + 7 rojos (cesión) →
implementación → **17/17**; suite completa **855/855**. `ruff check` + `ruff format` limpios.

**Pendiente de validación:** ninguna ficha nueva (el 8.5 es offline y testeado; su resultado
visible se verá cuando existan `yield_line`, es decir con el 8.6). Sigue abierta **U8** (UI del
8.4), que ahora **bloquea el 8.6** (el próximo paso).

**Commits:** `4cfc95e` (protección del mapa) · re-base de conteos (`test_map_persistencia`) ·
`feat(ai_control): 8.5 render de la cesión` · el commit de docs de esta entrada.

---

## S41 — 2026-07-15 — Fase 8: bloque 8.4 (UI de mapeo de la cesión) + veredictos U1/U2

**Contexto:** el 8.4 estaba bloqueado en blando por U1/U2 (pestaña Grabar sin validar desde S32).
Se aplicó el mecanismo de S40 tal cual: parar antes de escribir código y preguntar con el
selector. **El usuario validó en el momento** → el bloqueo se levantó y el 8.4 se hizo entero.

**Veredictos del usuario (fichas cerradas):**
- **U1 ("Link auto")** — *"Validado, funciona perfectamente."* ✅
- **U2 (ajustes de la pestaña Grabar)** — *"Funciona todo perfectamente."* ✅ (toggle Tráfico,
  Vel. grabar respetada, Auto pegajoso al cancelar.)

**Hecho (código) — bloque 8.4, red en rojo primero (29 tests, `test_map_ui_link_yield.py`):**
- **Sección "Cesion (ceda el paso)"** en el detalle de un RoadLink (Elementos, CIDs 152-159):
  sin línea → "Este giro no cede." + `+ Grabar linea`; con línea → nº de puntos, `Regrabar`,
  `Quitar` (limpia línea+T+zona), TypeIn de `yield_time_s` en el propio detalle (acepta número
  positivo o `default`/`none` ⇒ None; inválido revierte) y fila de `yield_zone_id` que abre el
  **picker de zonas** (misma mecánica que el picker de vías: lista paginada + `Ninguna` +
  `Cancelar`).
- **Grabador de la línea de detención**: sub-pantalla a contenido completo. El estado vive en
  `map_recorder.current_recording` (`type="yield_line"`, `link_id`, `auto_phase`) — el patrón de
  "Link auto": sobrevive a cerrar/reabrir el menú y reutiliza el freeze de `update_recording`
  (solo captura en fase `"recording"`). **Nace SIEMPRE en manual** aunque el toggle Auto general
  esté activo (diseño S38 punto 8, congelado en test). El toggle Auto del grabador exige coche
  (si no hay `recording_plid` toma el del usuario que clica) y va en lockstep con la preferencia
  global a partir del primer toggle. `Terminar` exige ≥2 puntos y pasa a fase `"ask_t"`: pide
  **T** con TypeIn (default visible) y `Guardar` comete línea (+T) vía `_cmd_rec_end`; `< Volver`
  regresa al grabador sin perder puntos; `Cancelar` descarta sin tocar el link.
- **Backend (`map_recorder.py`)**: rama `yield_line` en `_cmd_rec_end` (exige ≥2 puntos y que el
  link siga existiendo); `_cmd_set` gana `yield_time_s` (float > 0 o `none`/`default` ⇒ None) y
  `yield_zone_id` (con aviso si la zona no existe); `yield_line` **bloqueada** a la edición
  manual (se graba, como `nodes`). La pestaña Grabar tolera la grabación `yield_line` activa
  (su `Finalizar`/`Cancelar` funcionan; su indicador Auto y el del header muestran el estado
  EFECTIVO — fase+global — no solo el flag global).
- **Skill `ai-control-map-ui` actualizada** con el ejemplo nuevo (sección por tipo en el detalle
  + sub-pantallas con fase en `current_recording`).

**Decisiones (con su porqué):**
- **El estado del grabador vive en `current_recording`, no en la UI**: es lo que ya hace "Link
  auto" y regala gratis el freeze de la captura, la supervivencia al cierre del menú y la
  visibilidad en el header/pestaña Grabar. *Rechazado:* estado paralelo en `_ui_*` (habría
  duplicado la máquina de captura).
- **"Nace manual" se implementa con la fase, no apagando el toggle global**: la preferencia
  pegajosa del usuario (U2) no se toca al abrir el grabador; solo el primer toggle explícito
  la mueve (lockstep a partir de ahí).
- **`Guardar` comete por `_cmd_rec_end` + `_cmd_set`** (un único punto de materialización y la
  validación de T reutilizada), no asignando a pelo desde la UI.
- La retirada del editor de `priority_rules` de zonas **se queda en el 8.6** como estaba
  planificado (hoy sigue operativo pero inerte para la conducta desde el 8.3).

**Verificación:** red del 8.4 en rojo primero (28 de 29 fallando; 1 pasó de rebote porque el
descarte por tipo desconocido ya limpiaba la grabación) → **29/29 en verde** → suite completa
**838/838**. `ruff check` + `ruff format --check` limpios. `lfs_insim.cli list` carga los 4
insims.

**Pendiente de validación:** ficha **U8** (flujo completo de la UI en LFS, ~10 min). El **8.6
queda bloqueado en blando por U8** (migrar `test1` usa esta herramienta); el **8.5 (render) no
está bloqueado** y es el próximo paso.

**Commits:** `feat(ai_control): 8.4 - UI de mapeo de la cesion (...)` + el commit de docs de esta
entrada.

---

## S40 — 2026-07-14 — Protocolo: `ACCIONES_USUARIO.md` + bloqueo blando (meta; no toca el proyecto)

**Contexto:** primera cicatriz del uso real del protocolo. El usuario: *"cuando tengo que hacer algo
a mano, aunque quede apuntado no me queda del todo claro dónde mirarlo ni cuántas cosas tengo que
hacer"*. **Fase 8 aparcada** durante la sesión (§12: petición no planificada, legítima); se retoma en
el 8.4.

**Diagnóstico (el hueco era mayor que el síntoma):** la cola de validación tenía tres defectos.
(1) Era **una línea por ítem**: decía qué se había tocado, no qué tenía que hacer el usuario, ni
cómo, ni con qué mapa, ni qué contar si fallaba. (2) **Solo cubría el punto ciego** (validar en LFS):
lo demás que se le pedía —mapear, correr un comando, decidir un dial, aportar un dato— no tenía sitio
y moría en el chat. (3) **Competía por el tope de 120 líneas** del handoff (ocupaba ~35 de 120), que
era precisamente lo que impedía dar detalle. El síntoma del usuario era el efecto de (3) sobre (1).

**Hecho — las tres capas, en paridad:**
- **`ACCIONES_USUARIO.md`** (canónico: `USER_ACTIONS.md`): ficha por acción con ID estable **`U<n>`**
  —cuarta familia junto a `P`/`W`/`S`— con tipo, por qué, **pasos copiables**, resultado esperado,
  señales de fallo y qué contar si falla. Cabecera con contadores. Migrada la cola actual: **7 fichas
  (U1–U7)**; las cerradas históricas quedan como una línea en la sección ✅.
- **El handoff deja un puntero, no una copia** (§6: contenido duplicado diverge). 91 → 75 líneas.
- **Bloqueo blando** (§7 reescrito): el bloqueo **se declara en la ficha**; una tarea que toca el
  **mismo subsistema** que una ficha sin validar está bloqueada por defecto; se para **antes** de
  escribir código; el usuario puede saltárselo y el **override se registra** sin volver a sacarlo.
  Recordatorios en 4 momentos (arranque, choque, cola >4, cierre).
- **`close_check.py` reescrito**: verifica existencia, contadores = fichas reales, ninguna pendiente
  sin pasos ni campos, y que el handoff apunte al archivo. WARN si hay bloqueantes o la cola pasa de 4.
- **Proyecto**: `MODUS_OPERANDI §8` (mecanismo completo) + §1/§2/§4 tocados, `00_INDEX`, enganche de
  `CLAUDE.md`. **Portable + skill**: §2/§3/§4/§7/§15 + plantillas; `parity_check.py` verde.

**Decisiones (con su porqué):**
- **Un solo archivo, sin historial aparte.** El registro completo de un veredicto ya vive en este
  `HISTORIAL.md`; un tercer sitio con lo mismo se desincroniza (§6). Las cerradas se colapsan a una
  línea con tope. *Rechazado:* `ACCIONES_LOG.md` separado.
- **Bloqueo blando, no duro.** Un bloqueo que me auto-impongo y que se quita con una frase acaba
  siendo una frase que el usuario dice siempre, y el mecanismo muere. Parar-y-preguntar **una vez**,
  con el motivo, se respeta; insistir cada turno es ruido que enseña a ignorarme.
- **Regla del mismo subsistema.** Es el único caso donde seguir sin validar no es subóptimo sino que
  **destruye información**: apilar un cambio sobre otro sin validar deja dos sospechosos y el
  veredicto del usuario deja de ser interpretable. Aplicada ya: **U1/U2 bloquean el 8.4** (vuelve a
  tocar la pestaña Grabar, con dos cambios de S32 aún sin validar).
- **Marcadores independientes del idioma** en el formato de ficha (`### U<n>`, `🚧`, `- [x] U<n>`):
  es lo que permite que `close_check.py` cuente y valide en un proyecto en cualquier idioma.

**Bug encontrado de paso (y arreglado):** la skill instalada en `~/.claude/skills/agentic-protocol/`
tenía **las reglas viejas en la raíz** (`references/protocol.md`, 11 KB vs 15,7 KB) y una copia
anidada al día en `agentic-protocol/agentic-protocol/`. Causa: el `Copy-Item -Recurse <carpeta>
-Destination $dst` del README **anida** en vez de sobrescribir cuando `$dst` ya existe — solo
funcionaba la primera vez. Claude cargaba la versión equivocada y **nada lo delataba**. Reinstalada
(hashes verificados contra el repo) y comando del README corregido a `<carpeta>\*` + nota de cicatriz.

**Verificación:** `close_check.py` → PASS (2 WARN, ambos ciertos y deseados: U1/U2 bloqueantes
abiertas y cola de 7 > 4). `parity_check.py` → IN PARITY. `ruff check` + `ruff format` limpios.
No se tocó código del framework: `pytest` sigue en 809/809 (S39).

**Commits:** `ea5f027` (protocolo portable + skill) y el commit de esta misma entrada (la
instantiación en el proyecto: `ACCIONES_USUARIO.md`, `MODUS_OPERANDI §8`, `00_INDEX`, `CLAUDE.md`,
`scripts/close_check.py`).

---

## S39 — 2026-07-14 — Fase 8: bloque 8.3 (conducta de cesión) + retirada del modelo viejo de la conducta

**Contexto:** el orquestador casi no tenía red (2 tests, S34), así que el bloque se hizo en el orden
del MODUS §3: caracterizar → red en rojo → implementar → retirar.

**Hecho (código):**
- **Caracterización del marco** (`test_orchestrator.py`, 8 tests EN VERDE antes de tocar): asignación
  final (`speed_request = min(velocidad_segura, base)`, `point_request` también en el camino de caché),
  compuerta del radar (`_cached_target_speed`, sin rescaneo dentro del intervalo), reglas especiales
  (el override rige en el SIGUIENTE scan: la base se calcula al principio de la pasada y la
  activación/desactivación ocurre al final — asimetría congelada a propósito). El modelo viejo de
  cesión NO se caracterizó: esta misma sesión lo retiraba.
- **8.3 Conducta** (21 tests verificados EN ROJO primero): el orquestador detecta el link con cesión
  (el `RoadLink` actual o el `next_link_id` comprometido, si `has_yield`), y si la línea está a menos
  de `max(15, v·5s)` y `_yield_threat_detected` ve tráfico, frena con el ACC contra un **coche parado
  fantasma colocado `PARADA_ABSOLUTA_M` más allá de la línea** (el morro para EN la línea, no un radio
  arbitrario antes; la constante se promocionó a nivel de módulo en `cruise_control.py`). **Punto de
  compromiso:** `has_crossed_line` ⇒ no se frena dentro del cruce. Histéresis del fix (5) reutilizada
  tal cual (`_should_keep_yielding` + `_yield_hold_until`).
- **`_yield_threat_detected`** (en `zones.py`, reescrito): compone los predicados de `yielding.py`.
  Vigila (1) el `to_road` hacia el punto de unión — arco hacia delante por la vía / velocidad; parado
  ⇒ ∞; pasado el punto (arco `None`) o a contramano (`is_heading_towards`) excluidos — y (2) la zona
  referenciada (punto de conflicto + T) **excluyendo a los que van detrás de la IA** (si contaran, tus
  seguidores te dejarían clavado en la línea). T: `yield_time_s` del link/zona, `None` ⇒ config
  `yield_time_s` (default `DEFAULT_YIELD_TIME_S` = 4 s).
- **Decisiones de detalle:** el nodo de los vehículos vigilados se recalcula por posición
  (`_get_closest_node_index`), NO se usa su `node_index` — es el nodo objetivo (va uno por delante,
  lección S35) y cerca del punto de unión ese sesgo diría "ya pasó" justo al llegar; los humanos se
  localizan con `get_location_context(find_links=False)` como en el modelo viejo; se itera sobre todos
  los vehículos sin rejilla (solo corre acercándose a un link con cesión, a cadencia de radar).
- **Retirada:** el bloque viejo del orquestador (zona-área + `priority_rules`) sustituido; los 4
  helpers de `zones.py` (`_is_point_in_zone`, `_get_dist_to_zone_edge`, `_get_zone_centroid`,
  `_is_priority_vehicle_active_at_zone`) y sus 15 tests eliminados; contrato de `base.py` actualizado;
  `mode.yield_zone_id` → `yield_link_id` (map_ui solo lee `yield_active`, intacto).

**⚠️ Consecuencia en el juego:** hasta que exista UI (8.4) o migración (8.6), NINGÚN cruce cede: los
mapas no tienen `yield_line` y la zona `test1` quedó inerte en conducta. Dos ítems de la cola de
validación (S33: temblor del fix (5) y editor de `priority_rules`) pasan a "cerradas" por obsoletos —
la histéresis se valida con la cesión nueva en 8.7 y el editor se retira en 8.4/8.6.

**Verificación:** red nueva verificada EN ROJO (19 fallos por piezas ausentes) antes de implementar;
suite **809/809** (824 tras implementar − 15 del modelo viejo); ruff check + format limpios;
`lfs-insim list` carga los 4 insims.

**Commits:** `feat(ai_control)` conducta de cesión (red primero) · `refactor(ai_control)` retirada del
modelo viejo · `docs(dev)` cierre.

---

## S38 — 2026-07-13 — Fase 8: diseño cerrado con el usuario + bloques 8.1 (modelo de datos) y 8.2 (predicados puros)

**Contexto:** la sesión de DISEÑO que pedía el PLAN. Novedad de método: el usuario pidió que las preguntas
se le hagan con el **selector interactivo de opciones** siempre que sea posible — instrucción añadida a
`MODUS §6` y usada durante toda la sesión (3 tandas de preguntas; aceptó todas las recomendadas salvo el
destino del modelo viejo).

**Diseño (decidido por selector; detalle en `PLAN § Fase 8`):** la cesión cuelga del **RoadLink** (línea de
detención grabada por puntos + T con default global y override + **zona opcional por referencia explícita**);
**quién cede = quien tiene línea** (la zona no decide prioridades, solo amplía qué se vigila — desaparecen
las tablas de pares); **zona nueva = punto de conflicto + T** (sin radio); se vigila el `to_road` acercándose
al punto de unión y a los que ya cruzan (parado ⇒ ∞ ⇒ se ignora; pasado/detrás excluidos), con **punto de
compromiso** al cruzar la línea. **Modelo viejo: migrar y retirar YA** (decisión del usuario, contra la
convivencia recomendada; barato — la única zona real es `test1`, 2 pares). UI: el campo cesión nace vacío,
su editor abre un **grabador de puntos** (default SIEMPRE manual aunque el "Auto" general esté activo) y
pide T al terminar; visualización en render + Elementos.

**Hecho (código):**
- **8.1 Modelo de datos:** `yield_line`/`yield_time_s`/`yield_zone_id` + `has_yield` en `RoadLink`
  (⚠️ `time` ya existía y es otra cosa); `yield_time_s` en `IntersectionZone` (área+pares marcados legacy
  hasta 8.3/8.6). Extracción de costuras en `map_recorder.py`: `_serialize_map_data` / `_load_map_from_data`
  / `_json_map_default` / `_graph_item_from_json` — este último compartido por carga y merge (elimina el
  bucle de reconstrucción duplicado). Red nueva `test_map_persistencia.py` (5): South City
  (222/328/28 + `test1`) carga INTACTO, round-trip de cesión, defaults en mapas viejos.
- **8.2 Predicados puros:** `traffic/yielding.py` — `time_to_point_s` (**parado ⇒ inf**, cambio deliberado
  frente al suelo de 0.5 m/s del modelo viejo), `forward_arc_dist_m` (lineal: `None` si ya pasó; circular:
  envuelve por el cierre), `has_crossed_line` (compromiso estricto; cuerda 1º→último), `is_heading_towards`
  (misma convención LFS que `zones.py`), `DEFAULT_YIELD_TIME_S = 4.0`. Red `test_yielding.py` (17).

**Verificación:** ambas redes verificadas **EN ROJO** antes de implementar; suite **795/795** (34 s);
ruff limpio; `lfs-insim list` carga los 4 insims. El 8.3 (orquestador, casi sin red) se dejó a propósito
para una sesión fresca.

**Commits:** `docs(dev)` diseño+MODUS · `feat(ai_control)` 8.1 · `feat(ai_control)` 8.2 · `docs(dev)` cierre.

---

## S37 — 2026-07-13 — Aplicación del protocolo agéntico a ESTE repo (handoff, cola, close_check, presupuesto)

**Contexto:** la prueba de fuego del protocolo destilado en S36, decidida con el usuario: este repo tenía
justo los fallos que el protocolo denuncia (handoff sin tope, cola de validación dispersa en prosa, cierre
no comprobable por máquina, sin presupuesto de lectura).

**Hecho:**
- **Handoff partido:** `ESTADO_ACTUAL.md` pasó de **1073 líneas a ~90** (tope 120). Todo el contenido
  anterior se volcó **ÍNTEGRO y byte-idéntico** (verificado con `cmp` sobre la concatenación) al
  **Anexo (S37)** al final de este archivo. Nada se perdió; el handoff vivo queda en: dónde estamos,
  cola de validación, bloqueos y notas operativas.
- **Cola de validación en LFS** montada en el handoff, con casillas que **solo cierra el usuario**:
  ley nueva del ACC (S35), fix (3) + guard (S34), fixes (4)/(1)/(5) (S33), herramientas de mapeo de
  S32/S33; W4 marcada como probada-y-NO-superada (→ Fase 8) y los ya validados como referencia.
- **`scripts/close_check.py` instalado** (copia del canónico de `.meta/`, con el default del handoff
  adaptado a `ESTADO_ACTUAL.md`) y **enganchado al MODUS §2** como último paso del cierre: árbol limpio,
  todo pusheado, tope del handoff, próximo paso y cola presentes.
- **Presupuesto de lectura** escrito en `MODUS §1` (+ puntero en `00_INDEX.md`): qué se lee entero
  (handoff, MODUS), qué en parte (última entrada de HISTORIAL, fase activa del PLAN) y qué **NO** se lee
  al arrancar (resto de HISTORIAL y su anexo, DIAGNOSTICO, auditorías, guías, `.meta/`).
- **Backlog offline** del handoff viejo (desacople P4, tipado gradual, DX del connect, splits post-merge)
  reubicado en `PLAN § Ideas` para que no viva solo en el anexo.

**Decisiones:** el volcado va a un **anexo al final de HISTORIAL** (verbatim, marcado como no-lectura de
arranque) en vez de repartirse por entradas: garantiza "sin perder nada", es verificable con un comando y
no reescribe la bitácora. En la cola, W4 no figura como pendiente sino como **no superada** (el usuario ya
dio su veredicto; lo pendiente es la Fase 8, no re-probar el modelo viejo).

**Verificación:** suite **773/773** en este equipo tras el pull (36 s) — no se tocó código del framework;
`close_check.py` en **PASS** al cierre (salida pegada en el chat de la sesión). La revisión adversarial del
protocolo queda pendiente A PROPÓSITO para después de usarlo unas sesiones (PLAN § Tooling).

**Commits:** `chore(dev)` (script) + `docs(dev)` (split + cola, presupuesto, cierre).

---

## S36 — 2026-07-13 — META: protocolo agéntico portable (prompt maestro + skill). No toca el proyecto

**Contexto:** el usuario pidió una sesión **ajena al framework**: resumir por qué este proyecto funciona bien con
IAs agénticas y destilarlo en un **prompt maestro configurable** aplicable a cualquier proyecto con cualquier IA.
Se arrancó igualmente con el protocolo de inicio (rama, `pull`, lectura de `docs/dev/`) y **no se tocó ni una
línea del framework**.

**Diagnóstico del sistema actual (lo que se entregó como análisis).** Funciona porque cura los **tres fallos
estructurales** de un agente: **amnesia** → el contexto vive en archivos versionados (`docs/dev/`, sincronizados
por GitHub); **ceguera** → `MODUS §4` declara "no puedo ejecutar LFS", así que el humano es el **oráculo de
verificación** y los cambios se entregan con nota de "qué probar" y marca ⏳/✅; **temeridad** → red de
caracterización antes de tocar lógica frágil, extracción segura, medir antes de arreglar. Piezas secundarias que
valen más de lo que parecen: **IDs estables** (`Pn`/`Wn`/`Sn`), la regla de **marcar siempre la opción
recomendada**, y la lista de **trampas del entorno** (mojibake de `Get-Content|Set-Content`, mirar qué es un
proceso antes de matarlo).

**Cuatro agujeros hallados en NUESTRO propio sistema** (y corregidos en el protocolo): (1) el handoff **no tiene
tope** y se ha convertido en un segundo historial — `ESTADO_ACTUAL.md` son **1031 líneas** que se leen **cada
sesión**, con el próximo paso enterrado; (2) lo **pendiente de validar en LFS está en prosa**, disperso → nadie
sabe qué está realmente probado; (3) el "hecho" **no es comprobable por máquina**; (4) **no está escrito qué NO se
lee al arrancar** — esta misma sesión gastó ~40k tokens leyendo medio `ESTADO_ACTUAL.md` porque nada decía dónde
parar.

**Entregado (`.meta/agentic-protocol/`, carpeta deliberadamente ajena al proyecto):**
- **`AGENTIC_PROTOCOL.md`** — el maestro, **agnóstico de harness**. Tres capas: **instalador** (que ejecuta la
  IA: idioma → auditoría del repo → modo FRESH/ADOPT/UPGRADE → entrevista → generación → enganche → entrega de
  las frases), **reglas** (§0–§15) y **plantillas**. Reglas nuevas respecto a lo que ya hacíamos: tope duro del
  handoff, **cola de validación** que solo cierra el usuario, definición de "hecho" con salida real pegada,
  prohibición de debilitar tests, verificar la red **en ROJO**, cambio arriesgado en **commit aparte**, y
  **presupuesto de lectura por sesión** (qué se lee entero, qué en parte y qué **no** se lee).
- **`skill/agentic-protocol/`** — lo mismo como **skill de Claude Code** (`/agentic-protocol`), con revelación
  progresiva (`references/` se leen solo al escribir los archivos) y **`scripts/close_check.py`**: el chequeo de
  cierre **ejecutable** (árbol limpio, todo pusheado, tope de `STATE.md`, próximo paso y cola presentes).
  Instalada en `~/.claude/skills/` de este equipo.

**Decisiones (con su porqué):**
- **Protocolo en inglés, idioma de trabajo como parámetro** (`working_language`). Razón: robustez con modelos
  pequeños, ~20% menos tokens por sesión y vocabulario nativo del oficio; el agente igualmente habla, commitea y
  documenta en español. Es el mismo patrón que ya usa el repo (core en inglés, docs en español).
- **Un solo escritor: la IA** (corrección del usuario a la v1, que era una plantilla para rellenar a mano). El
  humano **nunca edita** los archivos generados: responde en el chat y los lee para auditar. Contrapartida que se
  fijó como regla: los archivos deben quedar **legibles por un humano** (su idioma, prosa) — si no, se pierde la
  única supervisión que tiene.
- **Skill = solo instalación** (no `/arranca` ni `/cierra`): el arranque y el cierre viven en el enganche del
  `CLAUDE.md`, una sola fuente de verdad que además funciona desde otra IA o desde una máquina sin la skill.
- **Con script de chequeo** frente a solo prosa: una regla que un script verifica deja de ser una promesa. Es la
  única capacidad que el `.md` portable no puede dar.

**Verificación:** `close_check.py` probado contra este repo — y **falló señalando justo lo que denuncia**
(`STATE.md cap: 1031 > 120`, `validation queue: no checklist items`). Probado también el camino de error. Salida
forzada a ASCII porque la consola de Windows destrozaba los guiones largos. **No se ejecutó `pytest`: no se tocó
código** (suite intacta de S35, 773/773).

**Aviso operativo:** `Copy-Item -Recurse` con destino una carpeta que **ya existe** **aplana** la estructura
(copia el contenido, no la carpeta) — pasó al instalar la skill; hay que pasar `-Destination` con la ruta final
completa. Corregido también en el comando documentado.

**Lección de método (la más valiosa de la sesión).** Al usuario se le escaparon **cinco** huecos del
documento y **los cinco los cazó él**, casi todos preguntando: *"¿cómo arranca cada sesión?"*, *"¿la IA se lo
lee entero cada vez?"*, *"¿dónde se acumulan las instrucciones fijas?"*. Al pedir un barrido final aparecieron
tres más (paridad rota entre las dos copias, `DIAGNOSIS` que no se mantenía sola, nadie asignaba el `S<n>`).
**Diagnóstico honesto:** no es context-rot (los fallos conceptuales ocurrieron con el contexto fresco) ni falta
de modelo (el barrido los encontró en dos minutos con **el mismo modelo y el mismo contexto**, solo cambiando de
modo). Es una **asimetría estructural entre escribir y revisar**: al producir se optimiza por coherencia, y todos
los fallos eran **ausencias**, no contradicciones — y una ausencia es invisible desde dentro porque *el hueco está
relleno en la cabeza del autor*. Ironía registrada: se escribió un documento sobre verificación **sin verificar el
documento**. **Cura (una regla, no una por incidente):** `§6` gana la definición de "hecho" para entregables que
**ningún comando puede verificar** — (a) **recorrerlo simulando su uso**, no releerlo (instalación → sesión 1 →
sesión 5 → llega una norma permanente → aparece un defecto → cierre → otra máquina); (b) **un lector que no sepa
lo que querías decir** (sesión fresca, subagente, el usuario); (c) **si el mismo contenido vive en dos sitios, se
separará** → derivar uno del otro o comprobarlo con un comando. Descartado a propósito: meterlo en las cicatrices
(`§13` es para daño del toolchain, no fallos de proceso) y añadir una regla por cada agujero (un protocolo que
engorda una regla por incidente deja de leerse).

**`parity_check.py` (`.meta/agentic-protocol/scripts/`).** La duplicación maestro↔skill es deliberada (dos
vehículos) pero se separó sola: el maestro tenía "Keeping the system alive" fuera de las reglas y la skill como
`§16` → el protocolo instanciado salía con **numeración distinta según por dónde entrases**. Lo cacé con una
comparación a mano; eso es una buena intención, no un sistema. Ahora es un comando: exige **mismas secciones** en
ambas copias y que **toda divergencia de cuerpo esté DECLARADA** con su motivo (`KNOWN_DIFFS`); una no declarada
es fallo. Al ejecutarlo aparecieron **3 derivas más** que yo no había visto a ojo (§0, §10, §16: palabras
cambiadas y una frase perdida) → alineadas. Estado: **17 secciones idénticas, 4 divergencias declaradas**.

**Commits:** `a1c77a9` (protocolo + skill), `6fda6bc` (presupuesto de lectura), `9f30739` (instrucciones
permanentes + tabla de enrutado), `439ca35` (paridad de numeración + `DIAGNOSIS` y `S<n>`), y el de cierre
(regla `§6` de entregables no ejecutables + `parity_check.py`). Todos pusheados.

**Próximo (decidido con el usuario): sesión nueva para APLICAR el protocolo a este proyecto** — partir
`ESTADO_ACTUAL.md` en handoff ≤120 líneas + volcado a `HISTORIAL.md`, montar la **cola de validación** con lo ⏳
pendiente en LFS, e instalar `close_check.py`. Es su prueba de fuego.

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

---

# 📦 Anexo (S37) — handoff histórico volcado de `ESTADO_ACTUAL.md`

> **Qué es esto:** en S37 se aplicó el protocolo agéntico al repo y `ESTADO_ACTUAL.md` (que había
> crecido hasta 1073 líneas y se leía entero en cada arranque) se partió: el handoff vivo quedó en
> ≤120 líneas y **todo su contenido anterior se volcó aquí ÍNTEGRO y sin editar** (tal y como quedó
> al cierre de S36). Es material de consulta, NO lectura de arranque. Las entradas por sesión de
> arriba siguen siendo la bitácora canónica; este anexo aporta además el encuadre que el handoff
> llevaba acumulado (fase activa, próximo paso, bloqueos y notas, como estaban en cada momento).

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
