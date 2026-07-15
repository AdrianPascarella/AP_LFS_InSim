# 🙋 Tus acciones — AP_LFS_InSim

> **6 pendientes** · ninguna bloquea el próximo paso (el 8.5 no toca la pestaña Grabar ni la
> conducción) · orden recomendado: U8 → ronda de conducción (U3 → U4 → U5 → U6 → U7) —
> U8 primero porque el 8.6 mapeará `test1` con esa herramienta · actualizado en S41
>
> Todo lo que hay aquí necesita tus manos o tu criterio: Claude no puede hacerlo, o no puede
> comprobarlo (no puede ejecutar LFS). **Tú nunca editas este archivo**: me dices cómo ha ido y
> yo cierro la ficha. Reglas del mecanismo: `MODUS_OPERANDI.md §8`.

## ⏳ Pendientes

### U8 — UI de mapeo de la cesión (bloque 8.4)   ⏳ · bloquea: el 8.6 en blando (migrar `test1` usa esta herramienta) · abierta en S41

**Tipo:** validar en LFS · **Tiempo:** ~10 min
**Por qué:** es la herramienta con la que se van a mapear TODAS las `yield_line` (8.6 migra
`test1` con ella, y el 8.7 valida la conducta sobre líneas grabadas así). Si graba mal, todo lo
de después queda contaminado.
**Pasos:**
  1. `.venv\Scripts\lfs-insim.exe run ai_control`, entra en LFS y carga un mapa (`.map ui` → Mapa).
  2. Pestaña **Elementos** → filtro **RoadLinks** → clica un link. Abajo debe verse la sección
     **"Cesion (ceda el paso)"** con "Este giro no cede." y el botón **"+ Grabar linea"**.
  3. Activa el **Auto general** en Grabar (para probar el default manual) y vuelve al detalle.
  4. Pulsa **"+ Grabar linea"**: el grabador debe abrirse con **"Auto: OFF"** (SIEMPRE nace
     manual). Coloca el morro DONDE debe parar la IA y pulsa **"+ Anadir punto"** en 2+
     posiciones a lo ancho del carril.
  5. Pulsa **"Terminar"**: debe pedirte **T** (campo con "default (4)"). Escribe un valor o
     déjalo y pulsa **"Guardar"**.
  6. De vuelta en el detalle: "Linea: N puntos", la fila de T y la de zona. Prueba el campo
     **yield_zone_id** (picker con las zonas del mapa, "Ninguna", "Cancelar") y **"Quitar"**.
  7. Extra: en el grabador, prueba el toggle **"Auto"** conduciendo (debe capturar puntos solo
     con él en ON) y **"Cancelar"** (no debe tocar el link).
**Resultado esperado:** el flujo completo sin teclear ningún id; la línea queda grabada donde
paraste el coche; T y zona editables desde el detalle; "Quitar" limpia los tres campos.
**Señales de fallo:** el grabador nace con Auto ON, "Terminar" no pide T, los puntos no se
añaden (mensaje de telemetría), el picker no lista las zonas, o "Quitar" deja restos.
**Si falla, dime:** en qué paso y qué muestra el chat de LFS. La lógica está en
`map_ui.py` (grep `_map_ui_draw_link_yield`) y la rama `yield_line` de `_cmd_rec_end`
(`map_recorder.py`).

### U3 — Ley nueva de seguimiento del ACC (`35870bb`)   ⏳ · bloquea: nada · abierta en S35

**Tipo:** validar en LFS · **Tiempo:** ~10 min
**Por qué:** el ACC se reescribió entero en S35. Es el cambio de conducta más grande sin validar:
mientras siga abierto, **cualquier retoque del tráfico se apila sobre código sin veredicto** y
contamina el experimento (por eso el resto de la cola de conducción va detrás de esta).
**Pasos:**
  1. Arranca `ai_control` y carga el mapa freeroam `test1` (`.map ui` → **Run**).
  2. Lanza 3-4 IAs con tráfico activado y déjalas circular.
  3. Métete tú con un coche humano **delante de una IA** y baja a ~40 km/h.
  4. Observa 30 s en recta, y luego para del todo y mira cómo se queda.
**Resultado esperado:** al ir bloqueada, la IA **iguala** tu velocidad —ni oscila ni se descuelga—
y mantiene el hueco: ~8 m en marcha, ~7 m cuando os paráis.
**Señales de fallo:** acelerón-frenazo en bucle (oscila), se queda muy atrás, o te embiste.
**Si falla, dime:** cuál de los tres y a qué velocidad. Los diales son `PARADA_ABSOLUTA_M`
(`traffic/cruise_control.py`) y `MIN_GAP_FLOOR_M` (`traffic/orchestrator.py`).

### U4 — Fix (3): radar en la transición road↔roadlink (`3a628c3`)   ⏳ · bloquea: nada · abierta en S34

**Tipo:** validar en LFS · **Tiempo:** ~10 min (aprovecha la misma partida que U3)
**Por qué:** el radar dejaba de ver coches justo al entrar y salir de un cruce. Es la base sobre la
que se apoya la conducta de cesión de la Fase 8: si el radar miente en el cruce, el 8.7 no se podrá
interpretar.
**Pasos:**
  1. Con IAs circulando en `test1`, quédate **parado con tu coche dentro de una vía que muere en un cruce**, delante de una IA.
  2. Ponte a circular **en la vía de destino** de un cruce y mira si las IAs que entran te ven.
  3. Aparca en una **transversal lejos** del cruce (>25 m) y comprueba que las IAs que pasan por el cruce **no** frenan por ti.
**Resultado esperado:** (a) frena por el lento que se le queda de frente en la vía que deja;
(b) ve a los que ya circulan en la vía de destino; (c) **no** frena por fantasmas de la transversal lejana.
**Señales de fallo:** te atraviesa (a/b) o frena sin motivo aparente (c).
**Si falla, dime:** cuál de los tres casos y a qué distancia del cruce. Dial:
`_LINK_TRANSITION_WINDOW_M` (`traffic/radar.py`, hoy 25 m).

### U5 — Guard: no adelantar dentro de un cruce (`8af862d`)   ⏳ · bloquea: nada · abierta en S34

**Tipo:** validar en LFS · **Tiempo:** ~5 min (misma partida que U3/U4)
**Por qué:** puede ser demasiado conservador. Si lo es, se revierte **solo ese commit**, sin tocar
el radar — por eso va en un commit aparte.
**Pasos:**
  1. Con tráfico en `test1`, ponte a mirar un cruce con varias IAs pasando.
  2. Fíjate en si alguna **inicia** un adelantamiento estando dentro del cruce.
**Resultado esperado:** nadie adelanta dentro del cruce; adelantan antes o después, no en medio.
**Señales de fallo:** se quedan pegadas detrás de un lento **también fuera** del cruce, o abortan
adelantamientos que ya iban bien encaminados (el guard está siendo demasiado agresivo).
**Si falla, dime:** si el problema es que **no adelanta nunca** cerca de cruces → revierto `8af862d`.

### U6 — Fix (4): no adelantar metiéndose por una vía cerrada (`d968abf`)   ⏳ · bloquea: nada · abierta en S33

**Tipo:** validar en LFS · **Tiempo:** ~5 min (misma partida)
**Por qué:** la IA adelantaba invadiendo un carril que no llevaba a ninguna parte, y se quedaba
atrapada.
**Pasos:**
  1. En `test1`, busca un tramo con una vía lateral cerrada / sin salida junto a un carril lento.
  2. Deja que una IA rápida alcance a una lenta ahí y mira por dónde intenta adelantar.
**Resultado esperado:** no usa la vía cerrada para adelantar; espera o adelanta por un lateral válido.
**Señales de fallo:** se mete por la vía cerrada y se queda encajada o da media vuelta.
**Si falla, dime:** en qué punto del mapa (nombre del road) pasó.

### U7 — Fix (1): el intermitente ya no hace flip en salidas juntas (`1a8eaac`)   ⏳ · bloquea: nada · abierta en S33

**Tipo:** validar en LFS · **Tiempo:** ~5 min (misma partida)
**Por qué:** con dos salidas RoadLink muy próximas, el enlace comprometido cambiaba de una a otra
y el intermitente parpadeaba a izquierda y derecha alternativamente.
**Pasos:**
  1. Localiza en `test1` un punto con **dos salidas RoadLink muy juntas**.
  2. Sigue a una IA por detrás mientras lo atraviesa y mírale el intermitente.
**Resultado esperado:** elige una salida y **se queda con ella** (pegajosa mientras sea válida); el
intermitente no parpadea alternando lados.
**Señales de fallo:** el intermitente hace flip izquierda/derecha, o cambia de decisión a última hora.
**Si falla, dime:** en qué cruce y si acabó tomando la salida correcta.

## ✅ Cerradas (recientes — el registro completo está en `HISTORIAL.md`)

<!-- Tope ~15 líneas: lo que rebose se cae, ya está en el historial. -->

- [x] U1 — **"Link auto" en la pestaña Grabar** — S41: *"validado, funciona perfectamente"*.
      Desbloqueó el 8.4.
- [x] U2 — **Ajustes de la pestaña Grabar** — S41: *"funciona todo perfectamente"* (toggle
      Tráfico, Vel. grabar, Auto pegajoso). Desbloqueó el 8.4.

<!-- Las de abajo se cerraron ANTES de que existieran las fichas, por eso no llevan ID. -->

- [x] **W4 ceda-el-paso (modelo viejo)** — S35: *"funciona, pero regular"* → **NO superado**. Motivó
      la Fase 8. No perder tiempo afinando el modelo viejo.
- [x] **Fix (5): histéresis del ceda-el-paso** (`73bbae7`) — S33. Obsoleta como estaba escrita (el
      modelo viejo ya no rige la conducta desde el 8.3); la histéresis se **reutiliza** en la cesión
      nueva y se validará con ella en el 8.7.
- [x] **Editor de `priority_rules` de zonas** — S33. Obsoleto: ya no rige la conducta (8.3); el
      editor se retira en 8.4/8.6.
- [x] **3 bugs del radar con humanos** — S35: *"desaparecieron todos los tirones"*.
- [x] **"Apunta"** (S31) · **fin de vía → espectadores** (S29→S30) · **reconexión de `ai_control`** (S20).
