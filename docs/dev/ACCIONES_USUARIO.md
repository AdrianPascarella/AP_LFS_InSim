# 🙋 Tus acciones — AP_LFS_InSim

> **0 pendientes** · nada te bloquea ahora mismo · actualizado en S44
>
> Todo lo que hay aquí necesita tus manos o tu criterio: Claude no puede hacerlo, o no puede
> comprobarlo (no puede ejecutar LFS). **Tú nunca editas este archivo**: me dices cómo ha ido y
> yo cierro la ficha. Reglas del mecanismo: `MODUS_OPERANDI.md §8`.

## ⏳ Pendientes

*(Ninguna.)* La cola de validación (Fase 7 + UI del 8.4) quedó despejada en S43 y sigue a 0.

El **diseño del rediseño de la cesión** se cerró contigo en S44 (por selector) y está escrito en
`PLAN.md § Fase 8, bloque 8.6`: implementarlo es trabajo mío y no te necesita. Lo que **sí** te
tocará, cuando llegue:

- **Al terminar el 8.6** → ficha U nueva: validar en LFS la herramienta rediseñada.
- **En el 8.7 (migración)** → ficha U: **regrabar `test1` como polígono** (≥3 puntos). Hoy es un
  círculo con `radius_m`, y esa forma **no se convierte sola**; hay que rehacerla en el juego.

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
