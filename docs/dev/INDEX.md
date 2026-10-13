# 🧭 Sistema de contexto — AP_LFS_InSim (lfs_insim)

> El contexto no vive en la sesión de chat. Vive aquí. Cada sesión **empieza leyendo estos
> archivos** y **termina actualizándolos**, para que la siguiente continúe exactamente donde se
> quedó sin que tengas que repetir nada.

## 🚀 Frase de inicio (dila al empezar cada sesión)

> **Inicia la sesión siguiendo el protocolo.**

Para cerrar: **«Cierra la sesión siguiendo el protocolo»**. El agente también cierra por su cuenta
en cada hito.

## Orden de lectura
1. **STATE.md**: dónde nos quedamos y cuál es el siguiente paso. Se empieza siempre aquí.
2. **USER_ACTIONS.md**: lo que te espera a ti (probar, hacer, decidir o aportar).
3. **LOG.md**: la última entrada, para el contexto reciente.
4. **PLAN.md**: la fase activa y su lista de tareas.
5. **PROTOCOL.md**: las reglas (obligatorias). Se consulta ante cualquier duda.
6. **DIAGNOSIS.md**: los problemas conocidos. Bajo demanda.

## Los archivos
| Archivo | Qué es | Cuándo se actualiza |
|---|---|---|
| STATE.md | El relevo entre sesiones | Al final de cada sesión y en cada hito |
| USER_ACTIONS.md | Lo que necesita tus manos o tu criterio | Cuando el agente te necesita y cuando das un veredicto |
| LOG.md | Diario de solo añadir | Al final de cada sesión |
| PLAN.md | Fases, tareas y criterios de aceptación | Cuando se terminan tareas o cambia el plan |
| DIAGNOSIS.md | Problemas conocidos, con ID estable | Cuando se encuentra algo nuevo |
| API_DESIGN.md | Cómo se usa la biblioteca (decisiones `D<n>`) | Cuando cambia la API pública |
| LEGADO.md | Qué rescatar del proyecto anterior (propuestas sin decidir, S14) | Al planificar mejoras de la API |
| PROTOCOL.md | Las reglas de trabajo | Cuando cambian las reglas |

> Estos archivos los escribe el agente, nunca a mano. Si algo está mal, díselo al agente y lo
> corregirá.
