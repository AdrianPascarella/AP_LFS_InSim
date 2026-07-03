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
5. Leer la última entrada de `HISTORIAL.md`.
6. Leer la fase activa en `PLAN.md`.
7. Verificar con `git status` y `git log --oneline -5` que el repo coincide con lo escrito.
8. Resumir al usuario en 2-3 líneas dónde estamos y qué propongo. Luego actuar.

## 2. Protocolo de CIERRE de sesión (o de hito)

Antes de terminar, SIEMPRE:
1. Actualizar `ESTADO_ACTUAL.md`: estado, fase, próximo paso concreto y qué quedó a medias.
2. Añadir entrada a `HISTORIAL.md` (fecha, qué se hizo, decisiones tomadas, commits si los hubo).
3. Marcar en `PLAN.md` lo completado; reflejar tareas nuevas descubiertas.
4. Si hubo una decisión de diseño relevante, dejarla registrada con su porqué.
5. **Commit + `git push`** a `origin/refactor/estabilizacion`: no terminar nunca con trabajo
   local sin subir (permite continuar desde otro dispositivo).

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

- **No puedo ejecutar LFS.** La verificación funcional en vivo (ver a la IA conducir)
  la hace el usuario. Yo entrego cambios con tests + una nota de "qué probar en el juego".
- Los tests que dependan de red/sockets deben aislarse con mocks (no conectar a LFS real).
- El entorno del sistema (Python 3.14) no tiene el paquete ni pytest instalados: trabajar
  siempre dentro del venv del proyecto (`.venv`).

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
- **Requiere permiso explícito del usuario:** mergear a `main` (y cualquier push a `main`).
  El merge se hace solo cuando el proyecto esté estable: `pytest` verde **+** el usuario ha
  validado el comportamiento en LFS.
