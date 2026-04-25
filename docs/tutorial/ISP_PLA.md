# ISP_PLA — Pit Lane

## Descripción
LFS envía este paquete cuando un jugador entra o sale del pit lane (la vía de boxes, no el box en sí). El campo `Fact` indica el motivo de la entrada.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_PLA |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| Fact | PITLANE | Hecho del pit lane (PITLANE_x) |
| Sp1 | byte | Reservado |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |

### Valores PITLANE_x
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | PITLANE_EXIT | Salió del pit lane |
| 1 | PITLANE_ENTER | Entró al pit lane |
| 2 | PITLANE_NO_PURPOSE | Entró sin propósito |
| 3 | PITLANE_DT | Entró para drive-through |
| 4 | PITLANE_SG | Entró para stop-go |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_PLA
from lfs_insim.insim_enums import PITLANE

class MiInsim(InSimApp):
    def on_ISP_PLA(self, packet: ISP_PLA):
        if packet.Fact == PITLANE.ENTER:
            print(f"PLID {packet.PLID} entró al pit lane")
        elif packet.Fact == PITLANE.EXIT:
            print(f"PLID {packet.PLID} salió del pit lane")
        elif packet.Fact == PITLANE.DT:
            print(f"PLID {packet.PLID} entró para drive-through")
```
