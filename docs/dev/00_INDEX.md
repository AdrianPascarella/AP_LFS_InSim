# 🧭 Sistema de contexto — AP_LFS_InSim

> **Filosofía:** el contexto no vive en la sesión de chat, vive aquí. Cada sesión
> **empieza leyendo** estos archivos y **termina actualizándolos**. Así cualquier
> sesión nueva continúa exactamente donde quedó la anterior, sin que el usuario
> tenga que repetir nada.

## 🚀 Prompt de arranque (pégalo al empezar CADA sesión)

> **Arranca la sesión siguiendo tu protocolo de `docs/dev/`: sincroniza con git (ponte en la rama `refactor/estabilizacion` y haz `git pull`), lee `ESTADO_ACTUAL.md`, `HISTORIAL.md` y `PLAN.md`, resúmeme en 2-3 líneas dónde estamos y continúa desde el próximo paso.**

Con eso basta: a partir de ahí Claude sincroniza, se pone al día y sigue el trabajo sin más
indicaciones. El `CLAUDE.md` del repo ya obliga a este arranque, por lo que incluso una
versión corta como *"arranca la sesión según tu protocolo de inicio"* funciona.

## Orden de lectura al empezar una sesión

1. **[ESTADO_ACTUAL.md](ESTADO_ACTUAL.md)** — dónde quedé y cuál es el próximo paso. **Empieza siempre aquí.**
2. **[HISTORIAL.md](HISTORIAL.md)** — última entrada, para el contexto reciente.
3. **[PLAN.md](PLAN.md)** — la fase activa y su checklist.
4. **[DIAGNOSTICO.md](DIAGNOSTICO.md)** — referencia de problemas conocidos (consultar según haga falta).
5. **[MODUS_OPERANDI.md](MODUS_OPERANDI.md)** — cómo se trabaja aquí (reglas de obligado cumplimiento).

## Los archivos

| Archivo | Qué es | Cuándo se actualiza |
|---|---|---|
| `ESTADO_ACTUAL.md` | Handoff entre sesiones: estado, fase, próximo paso concreto | Al final de cada sesión y en cada hito |
| `HISTORIAL.md` | Bitácora append-only, una entrada por sesión | Al final de cada sesión |
| `PLAN.md` | Plan por fases con checklists y criterios de aceptación | Al completar tareas o replanificar |
| `DIAGNOSTICO.md` | Escaneo del proyecto y problemas detectados | Cuando se descubre algo nuevo |
| `MODUS_OPERANDI.md` | Protocolo de trabajo y reglas | Cuando cambian las reglas |
| `PUBLICACION.md` | Runbook de publicación en PyPI (no es lectura de arranque) | Al preparar o hacer una release |

El arranque automático está enganchado en **`/CLAUDE.md`** (sección "Contexto de trabajo persistente"),
que instruye a Claude a leer estos archivos al inicio de cada sesión.
