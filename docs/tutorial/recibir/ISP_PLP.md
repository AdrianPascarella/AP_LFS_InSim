# ISP_PLP — Player Pits

## Descripción
LFS envía este paquete cuando un jugador va al pit lane para ajustes (mantiene su posición en la lista de jugadores). El jugador sigue existiendo con su PLID pero está en el garage. Cuando regrese, se recibirá un nuevo `IS_NPL`.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 4 |
| Type | byte | ISP_PLP |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_PLP

class MiInsim(InSimApp):
    def on_ISP_PLP(self, packet: ISP_PLP):
        print(f"PLID {packet.PLID} fue al garage (mantiene slot en la carrera)")
        # El jugador sigue en la lista pero no está en pista
        # Cuando salga del garage recibiremos IS_NPL con el mismo PLID
```
