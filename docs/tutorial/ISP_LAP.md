# ISP_LAP — Lap Time

## Descripción
LFS envía este paquete cuando un jugador completa una vuelta. Contiene el tiempo de vuelta, tiempo total, laps completados, penalización actual y combustible restante.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 20 |
| Type | byte | ISP_LAP |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| LTime | unsigned | Tiempo de vuelta en ms |
| ETime | unsigned | Tiempo total transcurrido en ms |
| LapsDone | word | Laps completados |
| Flags | word | Flags de jugador (PIF_x) |
| Sp0 | byte | Reservado |
| Penalty | byte | Penalización actual (PENALTY_x) |
| NumStops | byte | Número de paradas en pits |
| Fuel200 | byte | Combustible restante (/showfuel yes: doble del % / no: 255) |

### Valores PENALTY_x
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | PENALTY_NONE | Sin penalización |
| 1 | PENALTY_DT | Drive-through |
| 2 | PENALTY_DT_VALID | Drive-through (ya puede cumplirse) |
| 3 | PENALTY_SG | Stop-go |
| 4 | PENALTY_SG_VALID | Stop-go (ya puede cumplirse) |
| 5 | PENALTY_30 | 30 segundos |
| 6 | PENALTY_45 | 45 segundos |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_LAP

def ms_a_tiempo(ms: int) -> str:
    mins = ms // 60000
    secs = (ms % 60000) / 1000
    return f"{mins}:{secs:06.3f}"

class MiInsim(InSimApp):
    def on_ISP_LAP(self, packet: ISP_LAP):
        tiempo_vuelta = ms_a_tiempo(packet.LTime)
        tiempo_total = ms_a_tiempo(packet.ETime)
        print(f"PLID {packet.PLID} - Vuelta {packet.LapsDone}: "
              f"{tiempo_vuelta} (total {tiempo_total})")
        if packet.Fuel200 != 255:
            combustible = packet.Fuel200 / 2.0  # convertir a porcentaje real
            print(f"  Combustible: {combustible:.1f}%")
```
