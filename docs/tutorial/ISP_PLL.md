# ISP_PLL — Player Leave Race

## Descripción
LFS envía este paquete cuando un jugador abandona la carrera para spectear (pierde su slot en la lista de jugadores). A diferencia de `IS_PLP`, el PLID queda liberado.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 4 |
| Type | byte | ISP_PLL |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador que abandona |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_PLL

class MiInsim(InSimApp):
    def __init__(self):
        super().__init__()
        self.jugadores = {}

    def on_ISP_PLL(self, packet: ISP_PLL):
        info = self.jugadores.pop(packet.PLID, {})
        nombre = info.get('nombre', f"PLID {packet.PLID}")
        print(f"{nombre} abandonó la carrera (spectate)")
```
