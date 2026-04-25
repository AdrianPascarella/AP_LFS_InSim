# ISP_FIN — Finished Race

## Descripción
LFS envía este paquete cuando un jugador cruza la línea de meta. Es una notificación inmediata, **no** el resultado final confirmado (para eso usar `IS_RES`). Si el jugador abandona antes de que se confirme el resultado, PLID será 0.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 20 |
| Type | byte | ISP_FIN |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador (0 si abandonó antes del resultado) |
| TTime | unsigned | Tiempo de carrera en ms |
| BTime | unsigned | Mejor vuelta en ms |
| SpA | byte | Reservado |
| NumStops | byte | Número de paradas en pits |
| Confirm | byte | Flags de confirmación (CONF_x) |
| SpB | byte | Reservado |
| LapsDone | word | Laps completados |
| Flags | word | Flags del jugador (PIF_x) |

### Flags CONF_x (confirmación)
| Flag | Valor | Descripción |
|------|-------|-------------|
| CONF_MENTIONED | 1 | Mencionado en resultados |
| CONF_CONFIRMED | 2 | Resultado confirmado |
| CONF_PENALTY_DT | 4 | Penalización DT |
| CONF_PENALTY_SG | 8 | Penalización SG |
| CONF_PENALTY_30 | 16 | Penalización 30s |
| CONF_PENALTY_45 | 32 | Penalización 45s |
| CONF_DID_NOT_PIT | 64 | No hizo parada obligatoria |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_FIN

CONF_DID_NOT_PIT = 64

def ms_a_tiempo(ms: int) -> str:
    mins = ms // 60000
    secs = (ms % 60000) / 1000
    return f"{mins}:{secs:06.3f}"

class MiInsim(InSimApp):
    def on_ISP_FIN(self, packet: ISP_FIN):
        if packet.PLID == 0:
            print("Un jugador terminó pero ya abandonó")
            return
        dsq = bool(packet.Confirm & CONF_DID_NOT_PIT)
        print(f"PLID {packet.PLID} terminó - Tiempo: {ms_a_tiempo(packet.TTime)}"
              f"{'  [DNP]' if dsq else ''}")
```
