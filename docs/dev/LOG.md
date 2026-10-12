# 📓 Diario — AP_LFS_InSim (lfs_insim)
<!-- Solo se añade, lo más nuevo arriba. Una entrada por sesión. -->

## S1 — 2026-10-12 — Reinicio desde cero: rama huérfana, protocolo nuevo (modo FRESH) y plan inicial
**Contexto.** La sesión se abrió desde streamer-project (su S14), que necesita esta biblioteca para
la cámara libre. El usuario contó la historia del repositorio: lo empezó a mano, fue añadiendo IA y
avanzó mucho más rápido, pero «más pronto que tarde perdí el hilo y el control». Decidió empezarlo
de cero en el mismo repositorio, en una rama nueva, «cogiendo lo único que sea realmente útil», y
borrar todo el contexto antiguo (el protocolo antiguo fue el origen de la skill agentic-protocol).

**Hecho:**
- **Revisión del proyecto anterior** (`refactor/estabilizacion`, 358 commits del 21/04 al 05/09,
  46 sesiones, 914 tests en verde). Capas: el protocolo (paquetes y enums, ~3.000 líneas, lo más
  valioso), la especificación (`docs/InSim.txt`, desfasada: P2), el núcleo (conexión, reconexión,
  cargador de módulos, CLI, ~3.500 líneas: valen las ideas, no el código) y las aplicaciones
  (`ai_control` y otras, ~14.000 líneas más unas 150.000 de mapas JSON: donde se perdió el control,
  P4).
- **Ramas.** Se dejó una etiqueta `archivo/<rama>` en cada una (subidas a GitHub) y se borraron, en
  local y en GitHub, `main`, `fix/radar-false-positive-behind` (con 4 commits únicos del editor de
  mapas, recuperables desde su etiqueta), `feat/map-ui-refinements`, `feat/prueba-botones-completo`,
  `feat/overtake-refactor`, `fix/ai-test-remove-oldest-own-ai`, `fix/ai-control-stability` y
  `docs/update-readme`. Antes, `refactor/estabilizacion` pasó a ser la rama por defecto en GitHub.
- **Identidad y credenciales locales:** el repo tenía en local el correo de Veloik (un commit
  antiguo salió con él). Ahora `AdrianPascarella <pascarellaadrian@gmail.com>` y el ayudante de
  credenciales con el token de `AdrianPascarella`, como en streamer-project.
- **Rama huérfana `main`** y limpieza de la carpeta: se borraron las cachés, `.venv` (254 MB),
  `.venv39` (217 MB) y `logs/` (17 MB). `config/settings_local.py` se movió a
  `C:\Users\pasca\proyectos\_archivo_AP_LFS_InSim\` (puede tener la contraseña de administrador).
- **Especificación.** Se comprobó que https://www.lfs.net/programmer/insim publica el `InSim.txt`
  entero dentro de un `<pre>` (3.203 líneas, versión 0.8C27) y que la copia antigua tenía 41 líneas
  de diferencia. OutSim y OutGauge clásicos están en esa página; OutSimPack2 solo en
  `C:\LFS\docs\OutSimPack.txt` (idéntico a la copia antigua).
- **Protocolo instalado en modo FRESH** (plantilla v3): `docs/dev` completo, scripts de inicio y
  cierre y `CLAUDE.md` con el arranque. Basado en la versión en castellano de streamer-project, con
  la configuración de este proyecto. Ningún código.

**Decisiones:**
- **Biblioteca primero, no framework** → el usuario quiere que se use «como una librería más de
  python, que se pueda hacer un import… como se haría un import matplotlib o un import FastAPI». Lo
  de framework (módulos, dependencias, CLI) solo si una aplicación real lo pide. Se descartó repetir
  el framework del proyecto anterior.
- **Nombre `lfs_insim`** (`pip install lfs-insim`) → minúsculas como manda la convención de Python;
  libre en PyPI el 12/10. Se descartaron `import AP_LFS_InSim` (contra la convención),
  `ap_lfs_insim` e `insim` (demasiado genérico).
- **Python ≥ 3.11** → todas las versiones con soporte; 3.9 ya no lo tiene y 3.10 lo pierde este mes.
- **Las aplicaciones (cámara libre, control de IA, gestión de usuarios, registrador) van aparte** →
  idea del usuario: crearlas con comodidad es la comprobación de que la biblioteca funciona. El
  agente estuvo de acuerdo y añadió `examples/` y un LFS falso para los tests. **Discrepancia del
  agente:** la gestión de usuarios (UCID ↔ PLID ↔ nombre) la necesitan casi todas las aplicaciones,
  así que propone que esté en la biblioteca como algo opcional. Queda para W1.5.
- **Especificación descargada, no copiada** → petición del usuario: «no quiero que esté puesta
  harcodeada en el proyecto, quiero que la coja de la página de lfs.net». El agente añadió que la
  biblioteca nunca la descargue al usarse (dependería de internet), solo en desarrollo, y que en
  git quede la versión comprobada. El usuario aceptó además **generar los paquetes** a partir de
  ella en vez de escribirlos a mano.
- **Rama huérfana** → arranca sin los 45 MB de historial, que sigue en `refactor/estabilizacion`.
- **Ramas borradas con etiquetas de archivo** → recuperables si algún día hacen falta.
- **Todo lo público en inglés** (código, docstrings, README, ejemplos); la documentación de trabajo,
  en castellano.
- **Punto ciego**: el LFS real, la comodidad de la API y la instalación en otro equipo. El usuario:
  «Iniciemos siendo precavidos y ya después iremos afinando».
- **Lo que nunca se pierde**: el archivo del proyecto anterior (rama y etiquetas).
- **Instrucción permanente** (§15): decirle siempre cuando algo se puede hacer mejor.

**Después de instalar:** el usuario dio permiso y `main` pasó a ser la rama por defecto en GitHub.
Pidió dejar indicadas las aplicaciones de prueba («las que necesitamos aquí y las que ya
estaban»), pero insistió: «en la biblioteca solo esté lo que será de la biblioteca y no se mezcle
con los insims que vamos a crear aparte». Se acordó: **una lista de requisitos, solo texto**, en
`PLAN.md` («Aplicaciones aparte»: gestión de usuarios, registrador, cámara libre, botones y control
de IA, con los paquetes que usaban o usan), y **la prueba en vivo del protocolo como test de la
biblioteca** (W3.1), que sustituye al `test_insim` antiguo y no es un InSim para el usuario.

**Verificación:** no hay comando de verificación (P1, W1.2). Control de cierre al final.

**Commits:** instalación del protocolo en `main` (primer commit de la rama huérfana); `dev` sale de
ahí.
