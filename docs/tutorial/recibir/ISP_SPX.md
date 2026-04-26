# ISP_SPX — Split X Time

## Descripción
LFS envía este paquete cuando un jugador pasa por un split (checkpoint de tiempo). Incluye el tiempo del sector, tiempo total, número de split y estado actual.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 16 |
| Type | byte | ISP_SPX |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| STime | unsigned | Tiempo del split en ms |
| ETime | unsigned | Tiempo total transcurrido en ms |
| Split | byte | Número de split: 1, 2 o 3 |
| Penalty | PENALTY | Penalización actual (PENALTY_x) |
| NumStops | byte | Número de paradas en pits |
| Fuel200 | byte | Combustible restante (/showfuel yes: doble del % / no: 255) |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_SPX

def ms_a_tiempo(ms: int) -> str:
    mins = ms // 60000
    secs = (ms % 60000) / 1000
    return f"{mins}:{secs:06.3f}"

class MiInsim(InSimApp):
    def on_ISP_SPX(self, packet: ISP_SPX):
        tiempo_split = ms_a_tiempo(packet.STime)
        print(f"PLID {packet.PLID} - Split {packet.Split}: {tiempo_split}")
```
