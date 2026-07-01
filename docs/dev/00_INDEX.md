# 🧭 Sistema de contexto — AP_LFS_InSim

> **Filosofía:** el contexto no vive en la sesión de chat, vive aquí. Cada sesión
> **empieza leyendo** estos archivos y **termina actualizándolos**. Así cualquier
> sesión nueva continúa exactamente donde quedó la anterior, sin que el usuario
> tenga que repetir nada.

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

El arranque automático está enganchado en **`/CLAUDE.md`** (sección "Contexto de trabajo persistente"),
que instruye a Claude a leer estos archivos al inicio de cada sesión.
