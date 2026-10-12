# 📜 Protocolo de trabajo — AP_LFS_InSim (lfs_insim)

<!-- protocol-template-version: 3 -->

## Configuración

**Idiomas.** El chat, los mensajes de commit y la documentación de trabajo (`docs/dev`) se escriben
en **castellano**. Todo lo que leen los usuarios de la biblioteca va en **inglés**: identificadores,
comentarios, docstrings, README, ejemplos y documentación pública. *Por qué: es una biblioteca
pública para la comunidad de LFS, que es internacional, y los docstrings son lo que el editor
enseña al autocompletar (decisión del usuario, S1).*

**Qué es el proyecto.** `lfs_insim` es una **biblioteca de Python para el protocolo InSim de Live
for Speed** (InSim, OutSim y OutGauge), pensada para usarse como cualquier otra biblioteca:
`pip install lfs-insim` e `import lfs_insim`, igual que matplotlib o FastAPI. Requisitos: **Python
3.11 o superior** y **ninguna dependencia externa** en tiempo de ejecución. Se publicará en PyPI.
Es un proyecto **empezado de cero en S1 (2026-10-12)**, en una rama huérfana. El proyecto anterior
(framework `lfs_insim` v0.2.0 sin publicar, con las aplicaciones `ai_control`, `users_management`,
`test_insim` y `prueba_botones`) funcionaba, pero creció sin control. Sirve **solo como
consulta**: se rescata de él únicamente lo que demuestre valor.
- **Las aplicaciones van aparte.** La cámara libre, el control de IA y el registrador de eventos
  son proyectos separados que instalan la biblioteca como cualquier usuario. Que se puedan escribir
  con comodidad es la prueba de que la biblioteca funciona. Dentro de este repositorio solo caben
  ejemplos cortos (`examples/`).
- **La especificación no se copia a mano en el repositorio.** La fuente es la página oficial
  https://www.lfs.net/programmer/insim, que un script descarga a una carpeta ignorada por git. En
  git solo queda qué versión se ha comprobado. **Los paquetes se generan** a partir de esa
  especificación. OutSimPack2 no está publicado en la web: su fuente es
  `C:\LFS\docs\OutSimPack.txt`, que solo se lee.

**Ramas.** Se trabaja en **`dev`**. **`main`** está protegida: solo recibe merges con permiso
explícito del usuario. Ambas nacieron vacías en S1, como rama huérfana. El proyecto anterior se
conserva en la rama **`refactor/estabilizacion`** y en las etiquetas **`archivo/*`** (una por cada
rama borrada en S1).

**Máquinas.** De momento solo hay un equipo: el portátil Windows 11 Pro, con Python 3.14 (y un 3.9
antiguo, inservible aquí), Git y `gh`. **No tiene Python 3.11, 3.12 ni 3.13**: las versiones que
este equipo no tiene las comprueba el CI de GitHub (desde S3). LFS está instalado en `C:\LFS`.
No se descarta usar más equipos. Cuando llegue otro, se anota aquí qué cambia entre ellos (versión
de Python, si tiene LFS), y se hace pull y push en cada sesión.

**Verificación.** `.venv/Scripts/python scripts/verify.py` (desde S2). Detecta: un intérprete
equivocado o sin las herramientas de desarrollo, o un `lfs_insim` importado desde otra carpeta;
errores de lint y sintaxis posterior a Python 3.11 (ruff); formato; tipos (mypy estricto); tests
que fallan (pytest). También avisa, sin fallar, de los archivos `.py` demasiado largos (P4), salvo
los generados desde la especificación (desde S4: los marca su primera línea). Se
prepara el entorno con `py -3.14 -m venv .venv` y `.venv/Scripts/python -m pip install -e . --group dev`.
Visto en rojo en S2. **CI** (desde S3): el workflow `verify` de GitHub ejecuta el mismo comando
en Python 3.11–3.14, en Linux y en Windows, en cada push a `dev` o `main` y en cada pull request.
**Especificación** (desde S3): `.venv/Scripts/python scripts/fetch_spec.py` detecta si la página
de lfs.net o `OutSimPack.txt` difieren de la versión comprobada (`spec/checked.json`), y
`--accept` registra la nueva tras revisarla. Los tests que necesitan red se saltan por defecto
(`pytest -m network`). El workflow `spec` los ejecuta cada lunes (**solo desde `main`**, que es
la rama por defecto) y en cada push que cambie la especificación.

**Punto ciego (lo que el agente no puede comprobar).**
- **Que funcione en el LFS real**: que el juego acepte los paquetes y haga lo esperado (cámara,
  botones, mensajes, IA…). El LFS falso de los tests solo comprueba lo que el agente cree que hace
  LFS. *Precisado en S9:* el agente puede abrir LFS y conectarse, así que comprueba él mismo lo que
  se ve como paquetes (que LFS acepta lo enviado, qué contesta y que todo lo recibido se lee bien).
  Queda en el punto ciego **lo que se ve en pantalla** (cómo quedan los botones, si la cámara se
  mueve bien).
- **Que la API sea cómoda**: el criterio del usuario al escribir una aplicación con ella.
- **Que se instale bien en otro equipo** con `pip install lfs-insim`, cuando se publique.

El usuario avisó en S1 de que esta lista **no es definitiva**: se empieza con prudencia y se irá
afinando, porque puede haber cosas que hoy cree que solo puede ver él y que el agente sí puede
comprobar, y al revés.

**Lo que nunca se debe perder.** El **archivo del proyecto anterior**: la rama
`refactor/estabilizacion` y las etiquetas `archivo/*`, que guardan, entre otras cosas, los mapas de
`ai_control` grabados a mano. Nunca se borran, mueven ni reescriben sin permiso explícito del
usuario. Además, `C:\Users\pasca\proyectos\_archivo_AP_LFS_InSim\settings_local.py` (la
configuración local antigua, que puede contener la contraseña de administrador de LFS) está fuera
del repositorio y no se borra. Igual que la **copia de los setups y las skins de LFS**
(`setups`, `skins` y `skins_dds` de `C:\LFS\data`), hecha en S9 antes de reinstalar el juego en
`C:\Users\pasca\proyectos\_archivo_AP_LFS_InSim\LFS_backup_2026-10-12`. Y nada dentro de `C:\LFS`
se modifica: solo se lee (lo que el propio LFS escriba al usarlo no cuenta).

**Autorizado sin preguntar:** hacer commit y push en `dev`; corregir la identidad de git del
repositorio (solo en local); descargar la especificación oficial de lfs.net; leer
`C:\LFS\docs\OutSimPack.txt`; **abrir `C:\LFS\LFS.exe` para las pruebas y cerrarlo** (desde S9), con
estas condiciones: nunca si ya hay un LFS abierto (el usuario puede estar jugando), solo se cierra
el que abrió el agente, y se cierra con `/exit` enviado por InSim, sin matar el proceso.
**Siempre con permiso:** cambiar `C:\LFS\cfg.txt`, cambio a cambio, diciendo qué línea y por qué y
guardando antes una copia (antes, probar si se puede hacer con un comando durante la partida); merge o push a `main`; borrar archivos, ramas o etiquetas; force-push;
publicar en PyPI o TestPyPI; crear tags de versión o releases; cambiar la configuración del
repositorio en GitHub; instalar software en el sistema; modificar cualquier cosa dentro de
`C:\LFS`. El repositorio es **público**: todo lo que se sube a GitHub lo puede ver cualquiera.

**Identidad.** Los commits van como **`AdrianPascarella <pascarellaadrian@gmail.com>`**, configurado
en local en este repositorio (la identidad global del equipo es la de Veloik y no se toca). El
remoto es el GitHub **público** **`AdrianPascarella/AP_LFS_InSim`**, con la cuenta
**`AdrianPascarella`**. La cuenta activa global de `gh` en este equipo es `Veloik-adrian` y **no se
cambia**. Este repositorio tiene un ayudante de credenciales local que pide siempre el token de
`AdrianPascarella`, así que `git pull`/`git push` funcionan sin cambiar de cuenta. Para comandos
`gh` sobre este repo: `GH_TOKEN=$(gh auth token --user AdrianPascarella) gh <comando>`.

**Trampas conocidas de este equipo:** ver §13.

**Versión de la plantilla del protocolo absorbida:** **3**.

Cuando se describa un comando de verificación, lint o smoke, se indica su nombre y qué clase de
defecto detecta, nunca su cableado interno. *Por qué: el cableado ya está en el código, completo y
siempre actualizado. Una paráfrasis puede quedarse desfasada en cuanto alguien refactoriza, y nadie
lo notaría.*

---

## §0 — Directiva principal
El contexto vive en archivos, no en la sesión de chat. Nunca des por hecho que recordarás algo de una
sesión a otra: si importa, va a `docs/dev`.
*Por qué: sin esto, cada sesión empieza de cero y el usuario reexplica el proyecto para siempre. Los
archivos en git sobreviven al modelo, a la herramienta y a la máquina.*

## §1 — Los archivos son del agente
El agente es su único escritor. Deben quedar legibles para una persona que no los escribió: en su
idioma, en prosa y sin abreviaturas privadas. El usuario los lee para auditar al agente y nunca los
edita.
*Por qué: un único escritor evita la deriva de formato, los IDs duplicados y las versiones
contradictorias de un mismo hecho.*

**Edición quirúrgica, nunca «limpiando» un bloque.** Para añadir contenido, se sustituye solo la
línea o el encabezado ancla. Las notas tachadas y las entradas antiguas no se podan por iniciativa
propia. Después de editar, revisa `git diff` y confirma que no se ha borrado nada que no tocaba.
*Por qué: una reescritura en bloque no se distingue de una limpieza hasta que pierde una línea que
nadie pidió quitar. Ni los tests ni `close_check.py` lo detectan.*

## §2 — Los archivos de contexto
| Archivo | Qué es | Tamaño |
|---|---|---|
| `STATE.md` | El relevo: dónde estamos, **el siguiente paso** y un puntero a las acciones pendientes | **Tope estricto de ~120 líneas.** |
| `USER_ACTIONS.md` | Todo lo que necesita al usuario: probar, hacer, decidir o aportar | Tarjetas pendientes y una lista corta de cerradas, **una línea cada una**. |
| `LOG.md` | Diario de solo añadir, una entrada por sesión | Sin límite. Al empezar solo se lee la última entrada. |
| `PLAN.md` | Plan por fases, con tareas y criterios de aceptación | Sin límite. Al empezar solo se lee la fase activa. |
| `DIAGNOSIS.md` | Problemas conocidos, con ID estable y estado | Referencia: se lee bajo demanda. |
| `API_DESIGN.md` | Cómo se usa la biblioteca: ejemplos y decisiones `D<n>` aprobadas | Referencia: se lee al tocar la API pública. |
| `PROTOCOL.md` | Estas reglas | **Se lee entero en cada sesión.** |
| `INDEX.md` | Punto de entrada | Mínimo. |

**El tope de `STATE.md` es una regla.** Cuando se desborda, lo más antiguo pasa a `LOG.md`.
*Por qué: es el único archivo que se lee en todas las sesiones. Si no se controla, se convierte en un
segundo diario y entierra el siguiente paso.*

**Lo mismo vale para la cabecera y la sección «Cerradas» de `USER_ACTIONS.md`.** La cabecera indica
los contadores actuales y se **reescribe** en cada sesión, nunca se le añade texto. Una tarjeta
cerrada se reduce a **una línea con fecha** y el veredicto en pocas palabras; la cita completa va a
`LOG.md`.
*Por qué: es el mismo fallo que un `STATE.md` sin tope, en otro archivo. Además es el que se comete
dos veces, porque cerrar una tarjeta parece merecer una frase propia.*

**IDs estables.** Problemas `P<n>` (`DIAGNOSIS.md`), fases `W<n>` y sus tareas `W<n>.<m>` (`PLAN.md`),
sesiones `S<n>` (`LOG.md`) y acciones del usuario `U<n>` (`USER_ACTIONS.md`). Un ID nunca cambia de
significado ni se reutiliza. **El número de sesión lo asigna el agente al cerrar: el último de
`LOG.md` más uno.**
*Por qué: sin IDs estables, cada documento reexplica lo mismo con otras palabras y las versiones
divergen.*

**Una tarea de `PLAN.md` terminada** se marca y lleva `hecho en S<n> → LOG.md S<n>`, nada más. Lo que
pasó vive en un único sitio: la entrada de `LOG.md`.
*Por qué: si la tarea acumula prosa al cerrarse, el mismo hecho acaba contado de dos formas que dejan
de coincidir.*

**`DIAGNOSIS.md` sigue la disciplina contraria, a propósito.** Al resolver un problema se **añade**
una línea `Resuelto (S<n>): <cómo y qué lo demostró>`, sin acortar ni borrar Evidencia, Impacto ni
Acción.
*Por qué: es la referencia autocontenida. Una entrada tiene que entenderse por sí sola, por su ID, sin
reconstruirla desde `LOG.md`.*

**La regla de fondo:** `LOG.md` es el diario del proceso (qué pasó y cuándo). Todo lo que tiene ID
temático propio es referencia (qué es verdad ahora). Un hecho va en uno de los dos, nunca en ambos.

**Presupuesto de lectura al empezar una sesión:**

| Se lee entero | Se lee en parte | NO se lee al empezar |
|---|---|---|
| `STATE.md` · `USER_ACTIONS.md` · este archivo | la **última entrada** de `LOG.md` · la **fase activa** de `PLAN.md` | el resto de `LOG.md` · el resto de `PLAN.md` · `DIAGNOSIS.md` (bajo demanda, buscando por ID) |

*Por qué: `LOG.md` crece sin límite por diseño. Si un archivo que se lee entero se vuelve demasiado
grande, el defecto está en el archivo, y eso no da permiso para leer más.*

**Esta misma disciplina se aplica a este archivo.** En una sección nueva o en una instrucción
permanente se escribe la regla y un porqué breve. La historia que la justifica va en `LOG.md`, citada
por número de sesión. Si una sección sigue siendo grande y es de **procedimiento** poco frecuente (no
una advertencia que haya que leer siempre antes), se puede mover a una skill del proyecto
(`.claude/skills/<nombre>/SKILL.md`), y aquí se deja un puntero de una línea. Solo es válido si se ha
comprobado que el entorno anuncia esa skill por su cuenta en la sesión siguiente. Si no la anuncia,
el contenido vuelve aquí entero.
*Por qué: este archivo se lee entero en cada sesión. Lo que se narra aquí, en vez de enlazarse, es un
coste que se paga para siempre.*

## §3 — INICIO de sesión
1. Estar en `dev`.
2. **Confirmar la identidad antes de hacer nada más con git.** Comprobar que `git config user.email`
   es `pascarellaadrian@gmail.com`. Si no lo es, corregirlo con `git config` en local (nunca
   `--global`). Autorizado sin preguntar. No se comprueba la cuenta activa de `gh`: aquí es
   `Veloik-adrian` a propósito, y este repo autentica con su propio ayudante de credenciales
   (Configuración).
3. Proteger lo que nunca se debe perder antes de cualquier pull, checkout o stash. Hoy la lista está
   vacía (Configuración).
4. `git pull`.
5. Leer `STATE.md`: se empieza aquí.
6. Leer `USER_ACTIONS.md`: cuántas acciones hay pendientes y cuál bloquea (§7).
7. Leer la última entrada de `LOG.md` y la fase activa de `PLAN.md`.
8. Contrastar los documentos con la realidad (`git status`, `git log --oneline -5`). Si no coinciden,
   decirlo: manda la realidad y los documentos están mal.
9. **Comprobar si la plantilla del protocolo ha avanzado**: leer solo la línea de versión de
   `~/.claude/skills/agentic-protocol/references/protocol.md` y compararla con la versión anotada en
   la Configuración. Si son distintas, avisar y ofrecer volver a ejecutar la skill en modo
   **UPGRADE**. Si la skill no está en el equipo, saltar este paso sin decir nada.
10. Resumir en 2–3 líneas dónde estamos y qué se propone, **diciendo cuántas acciones esperan al
    usuario y cuál bloquea el siguiente paso**. Después, actuar.

**Atajo:** los pasos 2, 4, 8 y 9 se hacen con un solo comando:

```
python scripts/session_start_check.py --git-identity "AdrianPascarella <pascarellaadrian@gmail.com>" --branch dev
```

Para el paso 7: `python scripts/ctx_log_last.py` y `python scripts/ctx_plan_active.py`. Si un script
falta o falla, el paso se hace a mano tal como está escrito: los scripts ahorran repetición, no
sustituyen ningún paso.

*Por qué (2): una identidad equivocada se publica en silencio y queda para siempre en el historial.
Con la cuenta de `gh` equivocada, un repo privado devuelve «not found», que parece «este repo no
existe» en vez de «estás con otro usuario». Por qué (3): los datos hechos a mano son lo único que el
repo no puede regenerar. Por qué (6 y 10): el usuario no puede saldar una deuda que no puede
enumerar. Por qué (8): una sesión que terminó mal deja documentos que mienten. Por qué (9): sin esto,
una mejora de la plantilla solo llega si alguien se acuerda de reinstalar.*

## §4 — CIERRE de sesión (y en cada hito)
1. Actualizar `STATE.md`: estado, siguiente paso concreto, lo que quedó a medias y el puntero a las
   acciones pendientes. Respetar el tope y pasar lo antiguo a `LOG.md`.
2. **Todo lo que se le haya pedido al usuario en la sesión debe existir como tarjeta `U<n>`** en
   `USER_ACTIONS.md`, escrita antes de cerrar, y con los contadores de la cabecera actualizados.
   *Por qué: lo que solo se dijo en el chat muere con el chat.*
3. Añadir una entrada a `LOG.md`: qué se hizo, **decisiones con su porqué**, resultados de la
   verificación, commits y veredictos del usuario sobre las `U<n>`.
4. Marcar lo hecho en `PLAN.md` y añadir las tareas descubiertas. **Un defecto o problema estructural
   encontrado va a `DIAGNOSIS.md` con un nuevo `P<n>`** y su evidencia, aunque no se arregle ahora.
   Si se cierra una fase que cambia lo que el proyecto es en esencia (arquitectura, pila, despliegue),
   se actualiza en el mismo cierre la Configuración de este archivo.
   *Por qué: un problema encontrado y no archivado se encuentra dos veces. Y atar la actualización de
   la Configuración al cierre de fase es el único disparador lo bastante preciso para que no se
   olvide.*
5. Ejecutar `python scripts/close_check.py --context-dir docs/dev` y **pegar su salida**. Si falla, se
   corrige: nunca se informa de un cierre con el control en rojo.
6. Commit y push a `dev`. Nunca terminar con trabajo sin subir.
7. **Terminar el informe con lo que queda en manos del usuario**: las tarjetas pendientes, en el
   orden recomendado.

Si el usuario corta de golpe, se hace todo esto en el primer punto razonable.

**Cerrar barato.** Para recortar un archivo se borran bloques enteros cuyo contenido ya está en
`LOG.md` o `PLAN.md`, nunca se reescribe prosa para ganar una línea. `close_check.py` se ejecuta
**una vez**, cuando todo está escrito. Se hace **un** commit con su push.
*Por qué: lo que se escribe al cerrar se lee entero en cada sesión futura.*

## §5 — Tocar código frágil: la red de seguridad
- **Consultar `DIAGNOSIS.md` antes de tocar un archivo frágil**, buscando por ID o por archivo: puede
  que ya esté archivado y con plan decidido.
- **Primero, tests de caracterización** que capturen el comportamiento **actual**, rarezas incluidas.
  Se refactoriza solo con la red puesta.
- **Comprobar la red en ROJO**: ejecutarla contra el código antiguo y verla fallar.
  *Por qué: un test que nunca ha fallado es decoración, no una red.*
- **Nunca cambiar comportamiento y estructura en el mismo paso.**
- **Mejor extraer con seguridad que reescribir**, y **demostrar** el movimiento, no afirmarlo.
- **Nunca debilitar ni borrar un test para que pase.** Si se pone rojo, se para y se entiende el
  porqué. Cambiar un test solo es legítimo si se demuestra que está mal, y entonces se dice
  explícitamente, con el motivo, en el informe y en `LOG.md`.
  *Por qué: es el atajo favorito y destruye el único oráculo que hay.*

## §6 — Definición de terminado
Terminado significa todo lo siguiente, y demostrado:
1. El comando de verificación pasa: se ejecuta y se pega la salida **real** (Configuración).
2. El lint está limpio en lo que se ha tocado (va incluido en el comando de verificación).
3. El smoke sigue funcionando, si lo hay.
4. Se dice si ha cambiado la API o el contrato público.
5. Si toca el punto ciego (§7), **no** está terminado: queda pendiente de validación.

Informar con honestidad: si un test falla, se dice con la salida real; si se salta un paso, se dice.
*Por qué: los agentes dicen «verde» con facilidad. Que esa afirmación cueste ejecutar un comando.*

**Cuando ningún comando puede verificar el entregable** (un documento, un plan, un guion, un
esquema), «terminado» no significa releerlo:
- **Recorrerlo, no revisarlo**: simular su ciclo de vida completo y señalar en cada paso lo que el
  artefacto **no** dice. *Por qué: estos artefactos fallan por ausencias, y una ausencia no se ve al
  releer porque el autor la rellena de memoria.*
- **Buscar un lector que no sepa qué se quería decir**: una sesión nueva, un subagente o el usuario.
- **Si el mismo contenido vive en dos sitios, divergirá**: derivar uno del otro o comprobarlos con un
  comando.

## §7 — Lo que solo puede hacer el usuario: punto ciego y cola de acciones
El punto ciego (Configuración) es lo que el agente **estructuralmente no puede comprobar**. También
se necesita al usuario para **hacer** cosas que el agente no puede, para **decidir** lo que solo
decide él y para **aportar** información que el agente no puede obtener.

**Todo vive en `USER_ACTIONS.md`, y nada de lo que se le pida al usuario puede existir solo en el
chat.** Una tarjeta por acción, con ID estable `U<n>`:

```markdown
### U3 — <título>          ⏳ · bloquea: <nada | W1.3 | el merge> · abierta en S<n>
**Tipo:** validar | hacer | decidir | aportar          **Tiempo:** ~5 min
**Por qué:** <qué depende de esto>
**Pasos:**
  1. <concretos y copiables; los comandos como comandos>
**Resultado esperado:** <qué pasa si funciona>
**Señales de fallo:** <cómo se ve cuando no funciona>
**Si falla, dime:** <qué necesita oír el agente para actuar>
```

- **Un campo que no se conoce se declara, no se omite** («Resultado esperado: no lo sé; dime qué
  observas»).
- **La cabecera responde en una línea a «¿cuántas cosas te debo?»**: cuántas hay pendientes, cuál
  bloquea y el orden recomendado. Las tarjetas que bloquean llevan 🚧.
- **`STATE.md` lleva un puntero a este archivo, nunca una copia.**
- **El agente nunca cierra una tarjeta; la cierra el usuario.** Con su veredicto, se registra en
  `LOG.md`, la tarjeta se reduce a una línea con fecha en «Cerradas» y se le avisa.
- **No se abre una tarjeta de validar antes de que lo validado esté en manos del usuario**, y antes de
  aceptar un veredicto se comprueba que lo probado lleva de verdad el cambio (versión, hash, fecha).
  *Por qué: si lo que el usuario ve es la versión anterior, su veredicto es sincero y no vale nada.*

**Bloquear es suave: parar y preguntar, nunca negarse.**
- El bloqueo se declara en la tarjeta (`bloquea: ...`), no se improvisa.
- **Una tarea que toca el mismo subsistema que una tarjeta pendiente de validar queda bloqueada por
  defecto.** *Por qué: apilar un cambio sobre otro sin validar deja dos sospechosos cuando algo falla.*
- Al toparse con un bloqueo, se para antes de escribir código: se nombra la tarjeta, qué bloquea y por
  qué, se recomienda un orden y se ofrece lo que se puede hacer mientras tanto.
- **El usuario siempre puede saltárselo.** Entonces se sigue sin discutir, se **registra** en la
  tarjeta (`⚠️ saltada en S<n> a petición del usuario`) y en `LOG.md`, y no se vuelve a sacar.

**Se recuerda en cuatro momentos y en ningún otro:** al inicio de sesión, cuando una tarea choca con
una tarjeta, cuando la cola pasa de ~4 pendientes (entonces se recomienda una ronda de validación) y
al cierre.

**Cuando cerrar el punto ciego exige poner algo en manos del usuario** (un vídeo, un borrador, un
archivo) y el usuario está disponible, se entrega antes de cerrar y se pide el veredicto en la misma
sesión.

*Por qué existe esta sección: un agente que no sabe lo que no ve lo da por terminado, y el usuario lo
descubre ya publicado.*

## §8 — Diagnosticar antes de arreglar
- **Reproducir o medir primero.** No se arregla lo que no se ha observado.
- **Plantear la hipótesis e intentar tumbarla.** Mejor la evidencia que un razonamiento que suena
  bien. **Informar de las hipótesis refutadas.**
- **Nombrar la causa raíz.** «Se comportaba raro y añadí una guarda» no es un diagnóstico.
- **Buscar la regla canónica que ya exista en el código**: muchas veces la lógica correcta está en otro
  sitio y el camino roto simplemente no la aplicaba.

*Por qué: dos arreglos plausibles y equivocados cuestan más que una medición.*

## §9 — Riesgo y reversibilidad
- Un cambio de comportamiento arriesgado va en **su propio commit**, para poder revertirlo solo.
- Nunca destruir lo que nunca se debe perder (Configuración).
- Antes de cualquier cosa destructiva o difícil de revertir (borrar, force-push, matar procesos,
  tocar `main`, cualquier cosa que salga hacia fuera, y en especial **publicar o escribir en redes y
  servicios**), se confirma, salvo que esté en la lista de autorizados. Una aprobación en un contexto
  no se extiende a otro.
- **Antes de matar procesos «huérfanos», mirar qué son.** Pueden ser trabajo del usuario.

## §10 — Decisiones
- Registrar toda decisión relevante **con su porqué** en `LOG.md`, incluido lo descartado y por qué.
- **Al presentar opciones, marcar la recomendada y justificarla.** Recomendar, no enumerar.
- Con información suficiente, actuar. No preguntar lo que se puede averiguar.

## §11 — Comunicación
- Hablar en castellano. Lo que leen los usuarios de la biblioteca (código, comentarios,
  docstrings, README, ejemplos), en inglés.
- El usuario es el autor del proyecto: ir al grano y empezar por el resultado.
- **Al terminar una tarea, recomendar si seguir en esta sesión o abrir una nueva.** Si se recomienda
  una nueva, comprobar sin que se pida que puede arrancar limpia (control de cierre en verde y
  `STATE.md` apuntando al siguiente paso).

## §12 — Alcance
- Hacer solo lo pedido. Las ideas que surjan van a «Ideas» en `PLAN.md`, no al diff.
- Si el alcance resulta mayor de lo que parecía, parar y decirlo **con una recomendación** (recortar,
  dividir, aparcar).
- Una petición no planificada es legítima: se aparca la fase activa de forma explícita en `STATE.md`,
  se hace la petición y se anota en `LOG.md` que la fase se pausó y por qué.

## §13 — Cicatrices (trampas conocidas de este equipo)
Formas en que este equipo o sus herramientas ya han dañado o pueden dañar el trabajo. Se respetan.
**Cuando el agente cause una nueva, la añade él mismo.**
- **Cuenta de `gh` cruzada.** La cuenta activa global es `Veloik-adrian`; este repo es de
  `AdrianPascarella`, y `Veloik-adrian` no puede escribir en él (un push da 403). No cambiar la
  cuenta global. git usa el ayudante de credenciales local del repo, y `gh` se usa con
  `GH_TOKEN=$(gh auth token --user AdrianPascarella)`.
- **El push se colgaba con Git Credential Manager** (proyecto anterior, 2026-07). El ayudante global
  `manager` abre una ventana de autenticación que el agente no puede contestar y el push se queda
  esperando sin fin. El ayudante local del repo lo evita. Si vuelve a pasar, comprobar
  `git config --local --get-all credential.https://github.com.helper` antes de nada.
- **lfs.net no siempre responde desde este equipo.** En streamer-project se cortaba la conexión; en
  S1 de este proyecto respondió bien. El script de la especificación debe fallar con un mensaje
  claro y no dejar a medias la copia anterior.
- **Las barras invertidas rompen los scripts en línea** (visto en streamer-project). Un script de
  Python pasado por heredoc recibe `\n` como salto de línea real, así que rutas como `C:\LFS` lo
  rompen, y los heredocs largos fallan en esta terminal. **Regla:** los scripts largos se escriben
  con Write en el scratchpad de la sesión y se ejecutan desde ahí; los cambios pequeños, con Edit.
- **Caché de Python tras mutar un archivo para ver un test en rojo** (visto en streamer-project).
  Si se cambia un `.py` sin alterar su tamaño y se restaura en el mismo segundo, Python sigue usando
  el `.pyc` de la versión rota. Después de restaurar, borrar los `__pycache__` del proyecto.
- **pytest con colores oculta líneas a `grep`.** Para filtrar su salida, `--color=no`.
- **OutGauge de LFS ya está en uso** (puerto UDP 30000, lo usa otra aplicación del usuario). Los
  ejemplos y pruebas en vivo no ocupan ese puerto sin avisar.
- **El `python` de la terminal es el `.venv` de streamer-project** (visto en S2). Ejecutar con él
  instala o prueba en el proyecto equivocado. Aquí, siempre `.venv/Scripts/python`; el control de
  entorno de `verify.py` lo detecta.
- **`ruff format scripts` reformatea los scripts del protocolo** (visto en S4: `close_check.py` y
  `session_start_check.py` acabaron en un commit sin pedirlo). Vienen de la plantilla y no son
  nuestros. **Regla:** formatear solo las rutas de `CHECKED_PATHS` de `verify.py`, nunca la carpeta
  entera.
- **La trampa de las barras invertidas en heredocs se repitió en S4**: un `\b` de una regex se
  convirtió en un carácter de control y un test acabó con saltos de línea reales. Cualquier texto
  con `\` se escribe con Edit o Write, nunca con un heredoc de Python.
- **Un comando que pasa de su tiempo límite sigue vivo en segundo plano** (visto en S9: un `du`
  sobre `C:\LFS` bloqueó la carpeta y Windows negó el renombrado). Antes de mover o renombrar,
  comprobar que no queda ninguna tarea propia trabajando sobre esa ruta, y pararla.
- **`sed -i` de Git Bash convierte CRLF en LF en todo el archivo** (visto en S12 con
  `C:\LFS\cfg.txt`, que es CRLF; se rehízo desde la copia). **Regla:** los archivos de LFS se
  cambian línea a línea con Python en binario (`split(b"\r\n")`), y se comprueba después con `diff`
  contra la copia y con `od -c` que siguen en CRLF.
- **Git Bash convierte los argumentos que empiezan por `/` en rutas de Windows** (visto en S12:
  `/help` llegó a LFS como `C:/Program Files/Git/help`). Para pasar comandos de LFS como
  argumentos: `MSYS_NO_PATHCONV=1`.
- **Manejar LFS sin el usuario** (desde S12): `tests/lfs_screen.ps1` teclea (`-Keys`, `-Then`), hace
  clic (`-X`, `-Y`) y deja una captura en `tests/live_reports/screen.png`. InSim se activa con
  `-Keys "t" -Then "/insim=29999{ENTER}"`. Una pulsación justo después de otra pantalla a veces no
  llega: mirar siempre la captura antes del paso siguiente.

## §14 — Guías de procedimiento
Cuando una tarea recurrente tenga un coste de orientación alto, se escribe una guía con la
estructura estable, las convenciones y la receta, **nunca con números de línea**, que caducan en una
semana. Se guarda fuera de este archivo y se carga bajo demanda.

## §15 — Instrucciones permanentes (esta sección crece)
El usuario dará reglas para **todas las sesiones futuras** («siempre X», «nunca Y», «a partir de ahora
Z», o la corrección de algo que no debe repetirse). **Eso no es chat, es configuración.** Al recibir
una:
1. **Se escribe en esta sección**, con fecha y, en lo posible, con las palabras del usuario.
2. **Se le dice que se ha escrito**, y dónde.
3. **Se aplica desde ese momento.**

Si no está claro si una instrucción es permanente o puntual, **se pregunta**.

**Dónde va cada cosa:**

| Lo que llega | Dónde va |
|---|---|
| Una regla de trabajo para siempre | Aquí (§15) |
| Un daño causado por este equipo o sus herramientas | §13 |
| Algo que el usuario debe probar, hacer, decidir o aportar | `USER_ACTIONS.md`, con un nuevo `U<n>` |
| Un veredicto sobre algo que el agente no podía comprobar | Cerrar esa `U<n>` y registrar el veredicto en `LOG.md` |
| Una decisión de diseño y sus motivos | `LOG.md` (y `STATE.md` si condiciona el siguiente paso) |
| Un hecho sobre en qué punto está el trabajo | `STATE.md` |
| Una tarea o una idea para más adelante | `PLAN.md` |
| Un defecto o problema estructural | `DIAGNOSIS.md`, con un nuevo `P<n>` |

- **2026-10-12 (S1) — Decirle siempre cuando algo se puede hacer mejor.** «Tiene que tener muy
  claro que mi palabra no es ley, cuando creas que algo se puede hacer mejor de otra forma SIEMPRE
  tienes que decírmelo y aconsejar.» Ante cualquier decisión o petición del usuario, si hay una
  forma mejor, se dice con el motivo y una recomendación, antes de hacerla a su manera.
- **2026-10-12 (S6) — Lo que dice Scawen, si está al día, es la referencia.** «Todo lo que diga
  Scawen (y esté actualizado) va a biblia, él es el principal creador de LFS.» Sus palabras (en
  InSim.txt, en el foro de lfs.net o en las notas de las versiones) mandan sobre cualquier otra
  fuente: otros usuarios del foro, otras bibliotecas, el proyecto anterior o lo que el agente crea
  saber. «Al día» quiere decir que una explicación suya más reciente, o la especificación vigente,
  sustituye a una anterior. Si una fuente suya choca con la especificación, se dice y se investiga,
  sin elegir en silencio. Al usarla se cita dónde la dijo (hilo o versión) en el código o en
  `spec_overrides.py`, y en `LOG.md`.

## §16 — Mantener vivo el sistema
- **La configuración no está congelada.** Cuando cambie la realidad (un comando de verificación
  nuevo, una trampa, una rama, un cambio en el punto ciego), el agente actualiza este archivo y lo
  dice.
- **Si una regla resulta inadecuada para este proyecto, se propone cambiarla**, con el motivo y una
  recomendación, y después se escribe el cambio. Dejar de seguir una regla sin decirlo es peor que no
  haberla escrito.
- **El usuario solo tiene que hablar con el agente.** Si alguna vez edita estos archivos a mano, el
  sistema ha fallado y hay que arreglar lo que lo hizo necesario.
