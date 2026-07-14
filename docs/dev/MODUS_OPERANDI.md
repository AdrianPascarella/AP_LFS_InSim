# ⚙️ Modus Operandi — AP_LFS_InSim

Reglas de trabajo para Claude en este proyecto. De obligado cumplimiento.

## 0. Principio rector

**El contexto vive en `docs/dev/*.md`, no en la sesión de chat.** Nunca asumo que
recordaré algo de una sesión a otra: si es importante, va a un archivo. Si no está
escrito, no existe.

## 1. Protocolo de INICIO de sesión

Antes de tocar nada:
1. Estar en la rama de refactor (`git branch --show-current`; si no, `git checkout refactor/estabilizacion`).
2. **Proteger mapas modificados ANTES de cualquier `git pull`/checkout/stash** (instrucción
   permanente del usuario, 2026-07-03): si `git status` muestra cambios sin commitear en mapas
   freeroam (`insims/ai_control/nav_modes/freeroam/maps/*.json` y sus renders `*_rendered.png`),
   guardarlos SIEMPRE de forma segura — copia de respaldo fuera del repo + commit
   `data(ai_control): ...` + push. Es trabajo manual largo grabado en el juego y **no debe
   perderse nunca**. Este commit+push está autorizado de forma permanente, sin preguntar.
3. **`git pull`** para traer cambios hechos desde otro dispositivo (los `.md` o el código pueden haber cambiado).
4. Leer `ESTADO_ACTUAL.md` (dónde quedé, próximo paso).
5. Leer `ACCIONES_USUARIO.md`: cuántas hay pendientes y cuál bloquea (§8).
6. Leer la última entrada de `HISTORIAL.md`.
7. Leer la fase activa en `PLAN.md`.
8. Verificar con `git status` y `git log --oneline -5` que el repo coincide con lo escrito.
9. Resumir al usuario en 2-3 líneas dónde estamos y qué propongo — **y decirle cuántas acciones
   suyas hay pendientes y cuál bloquea el próximo paso**. Luego actuar.

### Presupuesto de lectura del arranque (S37, ampliado en S40)

Qué se lee al arrancar — y, tan importante, qué NO:

- **Entero:** `ESTADO_ACTUAL.md` (≤120 líneas, tope verificado por `close_check.py`),
  `ACCIONES_USUARIO.md` (corto por construcción) y este `MODUS_OPERANDI.md`.
- **En parte:** `HISTORIAL.md` → **solo la última entrada**; `PLAN.md` → **solo la fase activa /
  próximo paso** (localizar por headings con grep, no leerlo entero).
- **NO se lee al arrancar** (solo bajo demanda, cuando la tarea lo pida): el resto de `HISTORIAL.md`
  y su **Anexo (S37)**, `DIAGNOSTICO.md`, `AUDITORIA_HOTLOOP.md`, `PUBLICACION.md`, `docs/guia/`,
  `.meta/agentic-protocol/`.

## 2. Protocolo de CIERRE de sesión (o de hito)

Antes de terminar, SIEMPRE:
1. Actualizar `ESTADO_ACTUAL.md`: estado, fase, próximo paso concreto, qué quedó a medias y el
   **puntero a `ACCIONES_USUARIO.md`** (cuántas pendientes, cuál bloquea). **Tope duro: 120
   líneas** — lo que sobre se vuelca a `HISTORIAL.md`, no se acumula.
2. **Todo lo que le haya pedido al usuario esta sesión tiene que existir como ficha `U<n>` en
   `ACCIONES_USUARIO.md`** — escrita antes de cerrar, no prometida (§8). Actualizar los contadores
   de su cabecera.
3. Añadir entrada a `HISTORIAL.md` (fecha, qué se hizo, decisiones tomadas, commits si los hubo, y
   los veredictos que el usuario haya dado sobre alguna `U<n>`).
4. Marcar en `PLAN.md` lo completado; reflejar tareas nuevas descubiertas.
5. Si hubo una decisión de diseño relevante, dejarla registrada con su porqué.
6. **Commit + `git push`** a `origin/refactor/estabilizacion`: no terminar nunca con trabajo
   local sin subir (permite continuar desde otro dispositivo).
7. **Último paso, tras el push: `.venv\Scripts\python.exe scripts\close_check.py`** y pegar su
   salida. Debe dar **PASS** (árbol limpio, todo pusheado, tope del handoff, próximo paso, puntero
   a las acciones, contadores cuadrados y ninguna ficha sin pasos); si da FAIL, arreglar y repetir.
   Convierte este protocolo en algo comprobable.
8. **Terminar el informe con "lo que te toca a ti"**: las fichas pendientes, en el orden recomendado.

> Si el usuario cierra de golpe, hacer este cierre en cuanto se detecte un buen punto de parada.

## 3. Reglas de refactorización — red de seguridad: **tests de caracterización primero**

- **Antes de tocar lógica frágil** (traffic, navigation, radar, física), escribir tests
  que capturen el comportamiento ACTUAL. Refactorizar solo con la red puesta.
- **Cambios pequeños y verificables.** Nada de refactors masivos de una sola vez.
- **No cambiar comportamiento y estructura a la vez.** Primero uno, luego el otro.
- Mantener la suite verde en todo momento. Si un test se rompe, parar y entender por qué
  antes de seguir.
- Preferir extracción segura (mover código sin alterar lógica) sobre reescritura.

## 4. Limitaciones conocidas

- **No puedo ejecutar LFS.** La verificación funcional en vivo (ver a la IA conducir) la hace el
  usuario. Yo entrego cambios con tests + una **ficha `U<n>` en `ACCIONES_USUARIO.md`** con los
  pasos exactos, el resultado esperado y las señales de fallo (§8). Nunca doy por "hecho" algo que
  toque la conducta en el juego: queda **pendiente de validación**.
- Los tests que dependan de red/sockets deben aislarse con mocks (no conectar a LFS real).
- El entorno del sistema (Python 3.14) no tiene el paquete ni pytest instalados: trabajar
  siempre dentro del venv del proyecto (`.venv`).
- **NUNCA editar fuentes con `Get-Content | ... | Set-Content` (PowerShell 5.1).** `Get-Content`
  lee como ANSI, no como UTF-8: reescribe el fichero **doble-codificado** y deja todos los
  acentos en mojibake (pasó en S35 con `test_traffic.py`, y se coló en 2 commits). Los tests
  siguen pasando —es texto válido— así que no te enteras. Editar con las herramientas de edición.
- **Antes de matar procesos "huérfanos", mirar qué son** (`Get-CimInstance Win32_Process`): en S35
  los que parecían restos de un comando abortado eran **el InSim del propio usuario** probando en
  LFS. También explican que la suite tarde el doble: no toda lentitud es una regresión.

## 5. Convenciones del proyecto

- Idioma: **español** en docs/dev, commits, tests, insims y chat (LFS y con el usuario).
  **Excepción (decidida en S06):** el código nuevo del **core** (`src/lfs_insim/`) se escribe
  en **inglés** — identificadores, docstrings y mensajes de error/log — pensando en la
  comunidad LFS internacional y una eventual publicación en PyPI. El código viejo del core
  se traduce al tocarlo en el refactor, no en pasadas masivas.
- Convenciones técnicas (protocolo binario, mixins, comandos, paquetes): ver `/CLAUDE.md`.
  **No duplicar esa información aquí**; este archivo es solo el protocolo de trabajo.
- Commits: `tipo(scope): descripción` — feat / fix / refactor / chore / test / docs
  (coherente con el historial existente).
- **No commitear ni pushear** salvo que el usuario lo pida explícitamente.

## 6. Estilo de comunicación

- El usuario es el autor del proyecto y es técnico. Ir al grano.
- Recomendar una opción, no enumerar exhaustivamente. Cuando haya información suficiente, actuar.
- **Al plantear una pregunta con opciones, marcar SIEMPRE cuál es la recomendada**
  (p. ej. «(Recomendada)» en la etiqueta) y decir por qué. Nunca dejar la elección sin guía.
- **Las preguntas al usuario se hacen con el selector interactivo de opciones**
  (herramienta `AskUserQuestion`) **siempre que sea posible** — no como texto libre en el
  chat (instrucción del usuario, S38). La recomendada va primera y marcada. Texto libre
  solo cuando la respuesta sea genuinamente abierta (explicar una visión, describir un bug).
- **Al terminar una tarea, recomendar si conviene seguir en esta misma sesión o abrir una
  nueva** (para evitar el context-rot cuando el contexto se alarga). Decir cuál recomiendo.
  **Si recomiendo abrir una sesión nueva, comprobar SIEMPRE —sin que el usuario lo pida— que
  esa próxima sesión puede arrancar limpia, y reportarlo:** árbol limpio y en sync con `origin`
  (nada sin commitear/pushear), CI verde si aplica, y handoff coherente (`ESTADO_ACTUAL` apunta
  el próximo paso, `PLAN`/`HISTORIAL` al día). Es decir, dejar hecha la verificación que el
  usuario tendría que pedir de otro modo.
- Reportar resultados con honestidad: si un test falla, decirlo con la salida real.

## 7. Flujo de Git — sincronización con GitHub y merge a `main`

- **Todo el trabajo de refactorización se hace en la rama `refactor/estabilizacion`.**
  `main` permanece estable e intacta hasta el merge.
- **Sincronización multi-dispositivo (GitHub es la fuente de verdad entre equipos):**
  - Al **iniciar** sesión: estar en la rama de refactor y hacer **`git pull`** (puede haber
    cambios subidos desde otro dispositivo).
  - Al **cerrar** sesión o hito: **commit + `git push`** a `origin/refactor/estabilizacion`.
    Nunca terminar con trabajo local sin subir. Commitear y pushear los avances de esta rama
    es flujo normal y está **autorizado de forma permanente**.
  - La rama tiene upstream `origin/refactor/estabilizacion` (`git push -u` la primera vez).
- Commits pequeños y temáticos dentro de la rama (`tipo(scope): ...`).
- **Si el `git push` falla o se cuelga, no reportarlo como fallo sin más:** reintentar con el
  método que ya haya funcionado en el equipo y avisar al usuario de esa vía. (En este equipo el
  `git push` pelado se atasca en Git Credential Manager, que abre un diálogo GUI irrespondible;
  el método que funciona —token de `gh` como credential helper de un solo uso— está guardado en
  la memoria del equipo, `git-push-gcm-workaround`.)
- **Requiere permiso explícito del usuario:** mergear a `main` (y cualquier push a `main`).
  El merge se hace solo cuando el proyecto esté estable: `pytest` verde **+** el usuario ha
  validado el comportamiento en LFS.

## 8. Acciones del usuario y bloqueo blando (S40)

Todo lo que necesita al usuario —**validar** en LFS (el punto ciego), **hacer** algo que yo no puedo
hacer, **decidir** lo que solo él decide, **aportar** un dato que no puedo obtener— vive en
**`ACCIONES_USUARIO.md`**, una ficha por acción con ID estable `U<n>`.

**Nada de lo que le pida puede vivir solo en el chat.** Si lo pido en conversación y no lo dejo
escrito, no existe: la sesión termina y se pierde — y el usuario se queda debiendo cosas que ni
siquiera puede enumerar. Ese fue exactamente el fallo que motivó esta sección.

**La ficha** lleva: tipo, tiempo estimado, **por qué** (qué depende de ella), **pasos** concretos y
copiables, **resultado esperado**, **señales de fallo** y **qué contarme si falla** (los diales, el
archivo, el síntoma). **Un campo que no sé se declara, no se omite** ("Resultado esperado: no lo sé,
dime qué observas"): un "no lo sé" explícito es información; un campo ausente parece un olvido.
La cabecera responde de un vistazo *cuántas hay, cuál bloquea y en qué orden hacerlas*.

**`ESTADO_ACTUAL.md` lleva un puntero, nunca una copia** (contenido duplicado diverge).
**Las fichas no las cierro yo**: cuando el usuario da su veredicto, lo registro en `HISTORIAL.md`,
colapso la ficha a una línea en la sección ✅ del archivo, y se lo digo.

### Bloqueo blando: parar y preguntar, nunca negarse

- **El bloqueo se declara en la ficha** (`bloquea: ...`), no se improvisa. Un bloqueo inventado
  sobre la marcha es un bloqueo que también se me olvidará sobre la marcha.
- **Una tarea que toca el mismo subsistema que una ficha pendiente de validar está bloqueada por
  defecto**, aunque la ficha no bloquee nada. *Por qué:* apilar un cambio sobre otro sin validar
  destruye el único oráculo que hay — si luego falla en el juego, ya hay dos sospechosos y el
  veredicto del usuario deja de significar nada.
- **Al chocar con un bloqueo: parar ANTES de escribir código.** Nombrar la ficha, decir qué bloquea
  y por qué, recomendar el orden, y ofrecer qué se puede hacer mientras tanto sin contaminarla.
- **El usuario siempre puede saltárselo.** Entonces se hace, sin discutir — pero **se registra el
  override** en la ficha (`⚠️ saltada en S<n> a petición del usuario: se trabaja sobre código sin
  validar`) y en `HISTORIAL.md`, y **no se vuelve a sacar el tema**. Dicho una vez con su motivo es
  guía; repetido cada turno es ruido, y el ruido enseña a ignorarme.

### Recordatorios: en cuatro momentos y en ninguno más

Al **arrancar** la sesión (§1, en el resumen), cuando una tarea que voy a empezar **choca** con una
ficha, cuando la cola pasa de **~4 pendientes** (entonces recomiendo una ronda de validación en vez
de seguir apilando) y al **cerrar** la sesión (§2, última línea del informe).

`close_check.py` lo verifica: que el archivo exista, que los contadores de la cabecera cuadren con
las fichas reales, que ninguna pendiente se quede sin pasos ni campos, y que `ESTADO_ACTUAL.md`
apunte al archivo. Avisa (WARN) si hay fichas bloqueantes abiertas o si la cola se alarga.
