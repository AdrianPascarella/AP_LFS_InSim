# ISP_TOC — Take Over Car

## Descripción
LFS envía este paquete cuando un jugador toma el control de un coche de otro jugador (driver swap). El PLID del coche permanece igual, pero el UCID cambia al nuevo conductor.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_TOC |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador (el coche) |
| OldUCID | byte | UCID del conductor anterior |
| NewUCID | byte | UCID del nuevo conductor |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_TOC

class MiInsim(InSimApp):
    def __init__(self):
        super().__init__()
        self.jugadores = {}  # PLID -> UCID actual

    def on_ISP_TOC(self, packet: ISP_TOC):
        self.jugadores[packet.PLID] = packet.NewUCID
        print(f"Driver swap en PLID {packet.PLID}: "
              f"UCID {packet.OldUCID} -> UCID {packet.NewUCID}")
```
