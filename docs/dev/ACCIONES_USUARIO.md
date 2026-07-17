# 🙋 Tus acciones — AP_LFS_InSim

> **1 pendiente** (**U9**, no bloquea nada aún) · actualizado en S46
>
> Todo lo que hay aquí necesita tus manos o tu criterio: Claude no puede hacerlo, o no puede
> comprobarlo (no puede ejecutar LFS). **Tú nunca editas este archivo**: me dices cómo ha ido y
> yo cierro la ficha. Reglas del mecanismo: `MODUS_OPERANDI.md §8`.

> ✅ **Ya puedes volver a mapear en LFS.** La restricción de S45 se levanta: el 8.6.5 dejó la UI y
> el recorder en el modelo nuevo, y el `AttributeError` que acechaba en `!map whereami` está
> arreglado **y con test** (no lo tenía: por eso se coló).

## ⏳ Pendientes

### U9 — Validar en LFS la herramienta de cesión rediseñada (8.6.5)

> 🔎 **Ya la empezaste** (se ve en el mapa que commiteó S46): grabaste la road `Erase_test` y el
> link `Erase_test->PitLane`, que es **el único del mapa con `yield_type=YIELD` y punto marcado**.
> O sea que el toggle, el marcado del punto y el guardado **funcionan**. Falta tu **veredicto**:
> las fichas no las cierro yo (MODUS §8). Cuéntame cómo fue y la cierro.
>
> ❓ **Y de paso:** ¿`Erase_test` (37 nodos + su link) es basura de la prueba o la quieres? Está
> commiteada tal cual — **no la borro por mi cuenta**, es trabajo tuyo grabado en el juego. Si es
> basura, se quita en 1 minuto la próxima sesión.

- **Tipo:** validar en el juego · **Tiempo estimado:** ~20-30 min (menos: ya la empezaste)
- **Bloquea:** nada todavía. El **8.6.6** (render) no te necesita y puedo hacerlo ya. Pero
  **cuanto antes la hagas, mejor**: es el rediseño entero de lo que en U8 dijiste *"funciona, a
  mejorar"*, y si algo está mal quiero saberlo **antes** de apilarle encima el render y la
  conducta de la zona (MODUS §8: apilar sobre lo no validado destruye el oráculo).
- **Por qué:** no puedo ejecutar LFS. Los 914 tests dicen que la lógica hace lo que pedí, pero
  **no dicen si la herramienta es usable**, que es justo lo que falló en U8.

**Pasos:**

1. `lfs-insim run ai_control`, entra al mapa `south_city` y abre `.map ui` → pestaña **Elementos**.
2. **Detalle de un RoadLink** (elige uno de un cruce de verdad):
   - Pulsa el toggle `[NONE]` → debe ciclar a `[YIELD]` → `[STOP]` → `[NONE]`.
   - Con `[YIELD]` y **sin punto**, el estado debe decir *"Sin punto: este giro NO cede"*.
   - Pulsa **[Auto]** → debe poner el punto **~5 m antes** del primer cruce real y decirte con
     qué vía cruza. **Mira dónde cae en el juego**: ¿es donde tú pararías?
   - Pulsa **[Remarcar punto]** con el coche donde quieras → debe MOVER el punto (no acumular).
   - **[Borrar]** quita el punto y deja el tipo como estaba.
   - La fila de **T** debe enseñar `4 (default)`, no `None`. Teclea `2.5` → se queda. Aparece
     **[Usar default]** → púlsalo y vuelve a `4 (default)`.
3. **Detalle de una Zona** (usa `test1`, aunque su forma sea la vieja):
   - Debe decir *"NO es poligono (2/3): no gobierna nada"*.
   - **[+ Grabar poligono]** → ve a la pestaña Grabar, marca **3+ puntos** rodeando un cruce y
     **Terminar** → al volver al detalle debe verse *"Poligono: N puntos"* y la **tabla de vías
     auto-poblada** con las que pisan el polígono.
   - Toggle de una vía → `NONE|YIELD|STOP`. **[X]** la saca. **[Re-detectar]** la devuelve
     conservando los tipos que hayas puesto en las demás.
4. `!map check` → debe hablar del modelo nuevo (polígono, tabla de vías, tipo-sin-punto) y **no**
   petar ni nombrar `radius_m` / `priority_rules`.
5. `!map whereami zone` (y el overlay "Apunta"/zona de la pestaña Info) → **DENTRO** solo si estás
   dentro del polígono; fuera, metros al borde. **No debe petar.**

**Resultado esperado:** todo el flujo va sin errores y **crear una cesión es notablemente más
rápido que en el 8.4** (era el criterio de aceptación de la Fase 8: *"fáciles de crear, sin
teclear ids ni razonar en pares"*).

**Señales de fallo:** cualquier `AttributeError` en la consola · el punto de `[Auto]` cae dentro
del carril que cruzas (⇒ subir `yield_auto_setback_m`) o demasiado atrás (⇒ bajarlo) · la tabla de
la zona no se puebla o se puebla con vías que no pisan el cruce · un botón no responde.

**Qué contarme si falla:** qué pantalla, qué botón, el texto exacto del error de consola, y —para
lo de `[Auto]`— **a qué distancia del cruce te gustaría que parase** (es un dial: se cambia solo).

> ⚠️ **No conduzcas para probar la CESIÓN todavía**: el punto ya se graba, pero el render (8.6.6)
> y la conducta de la zona (8.6.7) no están. Esta ficha valida **la herramienta**, no la conducta.
> La conducta del link sí está migrada, así que si quieres probarla, adelante — pero su validación
> formal viene en el 8.6.8.

## 🔜 Lo que te tocará después (aún no es ficha)

- **En el 8.7 (migración)** → **regrabar `test1` como polígono** (≥3 puntos). Hoy es una cápsula de
  2 nodos, y esa forma **no se convierte sola**; hay que rehacerla en el juego. (Si en U9 ya
  regrabas `test1` como polígono, esta se queda medio hecha.)

## ✅ Cerradas (recientes — el registro completo está en `HISTORIAL.md`)

<!-- Tope ~15 líneas: lo que rebose se cae, ya está en el historial. -->

- [x] U8 — **UI de mapeo de la cesión (8.4)** — S43: *"funciona, a mejorar"*. El flujo va bien;
      pegas y mejoras pedidas (T default como float, auto-`yield_line`, zonas con tabla
      auto-poblada + toggle de prioridades, aclarar `yield_zone_id`) → alimentan el **bloque de
      rediseño 8.6** (PLAN § Fase 8). No superada del todo, como fue W4.
- [x] U3 — **Ley nueva de seguimiento del ACC** (`35870bb`) — S43: confirmado, funciona.
- [x] U4 — **Radar en la transición road↔roadlink** (`3a628c3`) — S43: confirmado, funciona.
- [x] U5 — **Guard: no adelantar dentro de un cruce** (`8af862d`) — S43: confirmado, funciona.
- [x] U6 — **No adelantar por vía cerrada** (`d968abf`) — S43: confirmado, funciona.
- [x] U7 — **Intermitente sin flip en salidas juntas** (`1a8eaac`) — S43: confirmado, funciona.
- [x] U1 — **"Link auto" (Grabar)** — S41: validado. · [x] U2 — **Ajustes pestaña Grabar** — S41: validado.

<!-- Las de abajo se cerraron ANTES de que existieran las fichas, por eso no llevan ID. -->

- [x] **W4 ceda-el-paso (modelo viejo)** — S35: *"funciona, pero regular"* → NO superado. Motivó la Fase 8.
- [x] **3 bugs del radar con humanos** — S35 · **"Apunta"** (S31) · **fin de vía → espectadores** (S29→S30).
