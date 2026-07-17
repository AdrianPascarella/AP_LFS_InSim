---
name: ai-control-map-ui
description: Playbook para modificar la UI de botones de mapeo de ai_control (insims/ai_control/map_ui.py) — añadir o cambiar botones, toggles, campos de texto y pantallas en las pestañas del menú `.map ui` (Mapa/Grabar/Info/Elementos/Debug/Run). Úsala siempre que el usuario pida un ajuste de esa interfaz. Da el mapa del código y la receta para no re-explorar 3000+ líneas.
---

# UI de mapeo de ai_control (`map_ui.py`)

Guía para tocar la interfaz de botones del `map_recorder`. Contiene la **estructura
estable** y la **receta**; NO números de línea (envejecen). Para el detalle real,
`grep` por los nombres de función que se citan y lee esa función antes de editar.

## Dónde vive

- **UI:** `insims/ai_control/map_ui.py` → clase `_MapUIMixin` (mixin de `AIControl`).
  Se activa en el juego con `.map ui`.
- **Datos/lógica del mapa:** `insims/ai_control/nav_modes/freeroam/map_recorder.py`
  (`MapRecorder`): guarda `roads` / `road_links` / `lateral_links` / `zones` /
  `special_rules`; comandos `_cmd_rec_*` (grabación), `get_location_context(px,py,pz,...)`
  (vía/enlace/zona más cercanos a unas coords), `current_recording` (grabación en curso).
- **Tests:** `tests/insims/ai_control/test_map_ui_*.py`.

## Modelo de la UI (cómo se dibuja)

- Menú por pestañas: `self._ui_tab` ∈ {`mapa`, `grabar`, `info`, `elementos`, `debug`, `run`}.
- `.map ui` → `_map_ui_open` → dibuja header + tabs + `_map_ui_redraw_content`.
- **`_map_ui_redraw_content`**: limpia el área de contenido (`_map_ui_clear_content`)
  y llama al `_map_ui_draw_tab_<tab>` de la pestaña activa.
- Cada pestaña tiene **dos** métodos emparejados:
  - `_map_ui_draw_tab_<nombre>` → dibuja (envía los BTN).
  - `_map_ui_click_<nombre>` → procesa los clicks de esa pestaña.
- Un botón se dibuja con:
  `self.send_ISP_BTN(ReqI=1, UCID=u, ClickID=<cid>, BStyle=<ISB_STYLE...>, L, T, W, H, Text=...)`
  - **Rejilla de pantalla 0–200** en L (izq), T (arriba), W (ancho), H (alto).
  - Estilos en `ISB_STYLE` (combinables con `|`): `OK` (verde), `CANCEL` (rojo),
    `DARK`, `SELECTED`, `CLICK` (clicable), `LEFT`, `TITLE`, `LIGHT`.
- **Campo de texto (TypeIn):** un BTN con `TypeIn=TYPEIN_FLAGS.INIT_WITH_TEXT | <maxlen>`.
  Lo que el usuario escribe llega por `on_ISP_BTT` y se guarda en
  `self._ui_input_buffer[ClickID]`. Se lee de ahí en el click de "confirmar".

## Rangos de ClickID (CLAVE para no pisar nada)

- **98–107**: header y pestañas (reservado; ver constantes `_UI_CID_*` y `_TAB_LAYOUT`).
- **108–165**: **área de contenido**. `_map_ui_clear_content` hace
  `BFN.DEL_BTN` de 108 a 165 en CADA redibujado → aquí van los botones normales de
  cada pantalla. Los CIDs se **reutilizan** entre pestañas (se borran al cambiar).
  - 130–133 son los TypeIn/label designados: `_UI_CID_TI1=130`, `_UI_CID_TI2=131`,
    `_UI_CID_TI3=132`, `_UI_CID_LBL_CONF=133`.
  - En el **detalle de Elementos** el área está repartida así: filas de campos
    estándar 111–126, sección de **zona** 134–151 y sección de **link** 152–160.
    Las dos últimas nunca coexisten (un detalle es de un tipo o de otro).
- **166+**: **overlays que PERSISTEN** al cambiar de pestaña y al cerrar el menú
  (no los borra el clear de contenido). Ej.: overlay "whereami" pineado (166–171).
  Usa este rango solo si el elemento debe sobrevivir fuera de la sesión de menú.

## Flujo de eventos (clicks)

- `on_ISP_BTC` → `_map_ui_handle_click(cid)` → despacha: close / save / cambio de
  pestaña, o `_map_ui_click_<tab>` de la pestaña activa.
- Un handler típico: mira `cid`, muta estado (`self._ui_*` o `self.map_recorder.*`),
  y llama `self._map_ui_redraw_content()` (y `_map_ui_update_header()` si cambió el
  header, p. ej. el estado de grabación).
- **Estado de UI:** se inicializa en `_init_ui_state()` (se resetea al abrir el menú).
  Lo que deba sobrevivir a cerrar/reabrir el menú usa guard `hasattr` (ver el overlay
  whereami) **o** se guarda fuera de la UI (ver "Link auto" abajo).

## Receta: añadir un botón / toggle / pantalla

1. Elegir CID(s) libres: **108–165** (normal, se limpia) o **166+** (si debe persistir).
   Comprueba que no choquen con los que ya usa esa pantalla.
2. Dibujarlo en el `_map_ui_draw_tab_<x>` (o en una sub-función de dibujo) correspondiente.
3. Cablear el click en `_map_ui_click_<x>` (o en su intercept de sub-fase).
4. Si es un **mini-flujo con varias pantallas** (confirmación, conflicto...), guarda la
   fase en un estado que **sobreviva a reabrir el menú**. Patrón bueno: meterla en
   `map_recorder.current_recording[...]` (así vive con la grabación, no con el menú),
   como hace "Link auto" con `current_recording["auto_phase"]`.
5. **Reutiliza la lógica del recorder** (`_cmd_rec_*`, `get_location_context`) en vez de
   reimplementar guardado/geometría.

## Convenciones OBLIGATORIAS del proyecto

- **Red primero** (MODUS_OPERANDI §3): escribe el test ANTES o junto al cambio, en
  `tests/insims/ai_control/test_map_ui_*.py`, sobre el fixture **`ai_control`**
  (harness con `CapturingClient`: los envíos quedan en `app.client.sent`).
  - Helper típico: `_btns(app)` = `[p for p in app.client.sent if type(p).__name__ == "ISP_BTN"]`.
  - Estado mínimo: `app.map_recorder.active_map_name = "test"`, `app._init_ui_state()`,
    `app._ui_ucid = <ucid>`, `app._ui_tab = "<tab>"`.
  - Poblar el grafo con `populate_graph` + `make_road` / `make_road_link` / `make_lateral_link`;
    telemetría con `make_player` / `make_telemetry` (fixtures de `conftest.py`).
  - Si el flujo llama a `map_recorder.send` (p. ej. `_cmd_rec_end`, `_cmd_rec_cancel`),
    fija `app.map_recorder.client = app.client` en el setup del test.
- **Texto de botones en ASCII** (sin acentos ni ñ; ej.: "Anadir", "Trafico"). Los
  mensajes de chat (`send_ISP_MSL`) SÍ admiten acentos (latin-1). Colores: `TextColors`.
- Esto es UI del **insim de ejemplo** → **NO toca la API pública** del framework
  (`src/lfs_insim/`). No cambies el core por un ajuste de UI.
- **Verificar** (venv del proyecto):
  - `./.venv/Scripts/python.exe -m pytest tests/insims/ai_control/test_map_ui_<x>.py -q`
  - `./.venv/Scripts/python.exe -m ruff check <archivos>` + `ruff format --check <archivos>`
  - `./.venv/Scripts/python.exe -m lfs_insim.cli list` (carga los 4 insims)
- **Validación en LFS:** los cambios de UI/conducta los prueba **el usuario en el juego**
  (Claude no puede ejecutar LFS). Entrega el cambio + una nota de "qué probar".

## Ejemplos vivos a imitar (grep para leerlos)

- **"Apunta"** — toggle en la pestaña Info que reporta la vía a la que apunta el morro.
  Geometría pura `find_road_pointed_at` (en `nav_modes/freeroam/geometry.py`) + overlay
  pineado. Tests en `test_map_ui_whereami.py`.
- **"Link auto"** — mini-flujo en la pestaña Grabar (botón CID 118) que graba un RoadLink
  con origen/destino auto-detectados, con pantallas de confirmación y de conflicto. Grep
  `_map_ui_draw_auto_link` / `_map_ui_start_auto_link`. Tests en `test_map_ui_auto_link.py`.
  Buen patrón de "estado del flujo en `current_recording`" y de reutilizar `_cmd_rec_end`.
- **Cesión, los DOS mecanismos (Fase 8, rediseño S44 · bloque 8.6.5)** — dos
  secciones extra en el detalle de Elementos, **sin ninguna sub-pantalla**: cada
  una se dibuja solo para su tipo, así que sus rangos de CID no se pisan.
  - **RoadLink** (el que hace la maniobra), CIDs **152-160**: toggle
    `NONE|YIELD|STOP` + `[+ Marcar punto]` (UN punto, un clic, del coche del que
    clica) + `[Auto]` (geometría pura: retrocede `yield_auto_setback_m` desde el
    primer punto de conflicto — no necesita coche en pista) + `[Borrar]` + T.
    Grep `_map_ui_draw_link_yield`. Tests en `test_map_ui_link_yield.py`.
  - **Zona** (el que cruza de recto), CIDs **134-151**: grabador del polígono
    (reusa el grabador normal `type="zone"`, el de la pestaña Grabar) + T +
    tabla de vías auto-poblada con un toggle por road, su `[X]` y
    `[Re-detectar]`. Grep `_map_ui_draw_zone_yield`. Tests en
    `test_map_ui_zone_yield.py`.
  - **Los dos son ORTOGONALES: no se referencian jamás.** El link no nombra
    zonas y la zona no nombra links. Confundirlos fue lo que hundió la UI del
    8.4 (veredicto U8) — si vas a "conectarlos", para y relee `PLAN.md § 8.6`.
  - **Patrón de la fila de T** (`_map_ui_draw_yield_t_row`, compartida): enseña
    el **float efectivo**, nunca `None`, y ofrece `[Usar default]` solo si hay
    valor propio del que volver. `_map_ui_yield_apply_t` valida el TypeIn.
  - **Patrón de la tabla auto-poblada**: `_map_ui_draw_zone_roads_rows` **NO**
    puebla — solo pinta. Se repuebla al grabar el polígono y con
    `[Re-detectar]` (`map_recorder.autodetect_zone_roads`, que conserva los
    tipos ya puestos). Si poblaras al dibujar, lo que el usuario borra
    reaparecería al salir y entrar.

  > ⚠️ **Muerto en el 8.6.5, no lo resucites:** el grabador por fases de la
  > `yield_line` (`current_recording` con `type="yield_line"` y `auto_phase`
  > manual/recording/ask_t), el picker de zonas del link (`yield_zone_id`) y el
  > editor de pares `priority_rules` de la zona. El punto del link es **uno** y
  > la línea se **deriva** de él (`derive_yield_line`).
