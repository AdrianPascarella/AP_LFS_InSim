# .meta/agentic-protocol — NO forma parte de AP_LFS_InSim

Meta-trabajo: un protocolo portable para que **cualquier IA agéntica, en cualquier proyecto**,
trabaje como se trabaja aquí. Vive en este repo solo porque es donde el sistema nació y funciona
(y así se sincroniza entre equipos por GitHub). No tiene relación con el framework InSim.

## Cómo se usa (lo único que tienes que saber)

Son **tres frases**. Nada más.

| Cuándo | Qué le dices |
|---|---|
| **Instalar** (una vez, en el proyecto nuevo) | *"Lee `AGENTIC_PROTOCOL.md` e instálalo en este proyecto."* |
| **Arrancar** (cada sesión) | *"Arranca la sesión según tu protocolo de inicio."* |
| **Cerrar** | *"Cierra la sesión según el protocolo."* (la IA también debe cerrar sola al llegar a un hito) |

La frase de arranque funciona por el mismo truco que ya usas aquí: la instalación **escribe un
enganche** en el archivo que el harness auto-carga en cada sesión (`CLAUDE.md` en Claude Code,
`AGENTS.md` en Codex, `.cursorrules` en Cursor…), y ese enganche obliga a leer el estado antes de
tocar nada. Si el entorno no tiene ningún archivo auto-cargado, la IA te lo dice y te entrega una
frase de arranque autosuficiente en su lugar. **La IA te entrega tu frase al terminar de instalar**
y la deja escrita en el `INDEX.md`, para que no se pierda.

A partir de la instalación lo hace todo ella: te pregunta el idioma, audita el repo, te hace las
preguntas que no puede responder sola, y **escribe ella misma** el sistema de contexto (estado,
historial, plan, diagnóstico, protocolo) y el enganche.

**Tú nunca editas nada de eso.** Solo hablas con la IA. Si algo está mal en un archivo, se lo
dices y ella lo corrige. Los archivos están escritos por la IA pero **en tu idioma y en prosa**,
para que puedas leerlos cuando quieras ver por dónde va la cosa — que es tu forma de supervisarla.

Lo único que tienes que aportar tú vive en un archivo propio, **`USER_ACTIONS.md`** (S40): todo lo
que necesita tus manos o tu criterio —**validar** lo que la IA no puede comprobar (aquí: cómo
conduce la IA dentro de LFS), **hacer** algo que ella no puede hacer, **decidir**, **aportar** un
dato— con una **ficha por acción**: pasos concretos, resultado esperado, señales de fallo y qué
contarle si falla. La cabecera te dice de un vistazo **cuántas hay, cuál bloquea y en qué orden**.
Nada de lo que te pida puede quedarse solo en el chat. Y si vas a tocar algo que una ficha abierta
bloquea, la IA **para y te lo dice antes de escribir código** — puedes saltártelo, y lo registra.

## Ejemplo: lo que la IA acabaría escribiendo aquí

No es un formulario. Es lo que la entrevista extraería en **este** proyecto, y sirve de prueba de
que el esquema cubre un caso real:

- **Idioma:** español (chat, commits y docs); código del core en inglés, insims en español.
- **Ramas:** trabajo en `refactor/estabilizacion`; `main` intocable sin permiso; sync multi-equipo.
- **Verificación:** `pytest` · `ruff check` + `ruff format --check` · smoke: `lfs-insim list`.
- **Punto ciego:** *cómo CONDUCE la IA dentro de LFS.* La IA no puede ejecutar el juego: todo
  cambio de conducta (radar, ACC, navegación, adelantamiento, UI in-game) lo valida el usuario
  jugando. Los tests prueban que el código hace lo que se dice, no que se sienta bien al volante.
- **Nunca perder:** los mapas freeroam grabados a mano en el juego
  (`insims/ai_control/nav_modes/freeroam/maps/*.json` + sus renders). Horas de trabajo manual
  imposibles de regenerar desde el código → respaldar antes de cualquier `pull`/`checkout`.
- **Trampas del entorno:** `Get-Content | Set-Content` en PowerShell 5.1 corrompe las fuentes
  (mojibake silencioso; la suite sigue verde, así que no te enteras) · mirar qué es un proceso
  antes de matarlo (puede ser el InSim del propio usuario probando) · `git push` pelado se atasca
  en Git Credential Manager en algún equipo.
- **Autorizado sin preguntar:** commit + push en la rama de trabajo; respaldar los mapas.
  **Requiere permiso:** merge o push a `main`; borrar; cualquier cosa destructiva.

## La skill de Claude Code (capa 2)

Lo mismo, sin pegar nada: escribes **`/agentic-protocol`** en cualquier repo y arranca la
instalación. Fuente de verdad versionada en **`skill/agentic-protocol/`**:

- `SKILL.md` — el instalador (entrevista, auditoría, generación, enganche, entrega de frases).
- `references/protocol.md` — las reglas que se instancian en el proyecto. Se lee solo al escribirlas.
- `references/templates.md` — cómo queda cada archivo generado.
- `scripts/close_check.py` — el chequeo de cierre: árbol limpio, todo pusheado, `STATE.md` por
  debajo del tope y **apuntando** a `USER_ACTIONS.md`, con próximo paso, y las fichas del usuario
  **cuadradas** (contadores = fichas reales, ninguna sin pasos ni campos). Se copia al proyecto en
  la instalación.

**Para activarla en un equipo**, se copia a la carpeta de skills personales (así está disponible en
todos tus proyectos, incluso en uno recién clonado que aún no tiene `.claude/`):

```powershell
$dst = "$env:USERPROFILE\.claude\skills\agentic-protocol"
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item -Recurse -Force .meta\agentic-protocol\skill\agentic-protocol\* -Destination $dst
```

⚠️ **Cicatriz (S40).** El comando que había aquí antes (`Copy-Item -Recurse <carpeta> -Destination
$dst`, sin el `\*`) **solo funciona la primera vez**: si `$dst` ya existe, PowerShell copia la
carpeta *dentro* y crea `skills\agentic-protocol\agentic-protocol\`. Eso fue lo que pasó — la skill
quedó con una copia anidada al día y unas **reglas viejas en la raíz**, que eran las que Claude
leía de verdad. Es un fallo silencioso: la skill sigue cargando, solo que con la versión
equivocada. Con `\*` se sobrescribe el contenido en su sitio. Después de reinstalar, comprueba que
no hay carpeta anidada y que los hashes coinciden con los del repo.

Diferencia real frente a pegar el `.md`: el instalador **solo se necesita una vez**, así que como
skill no ocupa contexto en cada sesión (solo su descripción), puede repartirse en archivos que se
leen únicamente cuando hacen falta, y **puede traer un script** que verifica de verdad lo que el
`.md` solo puede pedir por escrito. A cambio, solo funciona en Claude Code: el `.md` sigue siendo la
fuente portable.

## Mantenimiento: las reglas viven en dos sitios

Las reglas están duplicadas a propósito (dos vehículos: el `.md` portable y la skill), y **el
contenido duplicado se separa solo** — ya pasó una vez. Por eso hay un comando, no una buena
intención:

```powershell
python .meta\agentic-protocol\scripts\parity_check.py
```

Exige que las **secciones sean idénticas** en ambas copias y que **cualquier divergencia de cuerpo
esté declarada** con su motivo en `KNOWN_DIFFS` (hoy: 4, todas legítimas — la skill trae script y el
`.md` no, etc.). Una divergencia **no declarada** es un fallo. Ejecútalo siempre que toques las
reglas.

## Estado

- [x] **Capa 1** — el `.md` maestro, agnóstico de harness (se pega en cualquier IA).
- [x] **Capa 2** — skill de Claude Code (`/agentic-protocol`), con chequeo de cierre ejecutable.
- [x] Regla de "hecho" para entregables que **ningún comando puede verificar** (§6) + chequeo de
      paridad ejecutable entre las dos copias.
- [x] **Prueba de fuego (S37):** aplicado a este proyecto — `ESTADO_ACTUAL.md` (>1000 líneas)
      partido en handoff + historial, y cola de validación montada con lo ⏳ pendiente.
- [x] **Primera cicatriz del uso real (S40):** las peticiones a mano quedaban apuntadas pero el
      usuario *"no sabía dónde mirarlo ni cuántas cosas tenía que hacer"*. → **`USER_ACTIONS.md`**
      (§7 reescrito): ficha por acción con `U<n>`, pasos, resultado esperado y señales de fallo;
      **bloqueo blando** (parar y preguntar, con override registrado) y regla del **mismo
      subsistema**; recordatorios en 4 momentos; y todo verificado por `close_check.py`.
- [ ] **Después de usarlo más:** revisión adversarial en sesión fresca (un lector que no sepa lo que
      quisimos decir), con las cicatrices que deje el uso real.
