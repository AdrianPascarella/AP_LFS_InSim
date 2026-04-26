# ISP_AXO — AutoX Object Hit

## Descripción
LFS envía este paquete cuando un jugador golpea un objeto de autocross (penalización de 2 segundos). Es un paquete mínimo de 4 bytes que solo identifica al jugador.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 4 |
| Type | byte | ISP_AXO |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |

**Nota:** Para información detallada sobre el objeto golpeado (posición, tipo), usar `IS_OBH` con `ISF_OBH` activo.

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_AXO

class MiInsim(InSimApp):
    def __init__(self):
        super().__init__()
        self._golpes = {}  # PLID -> contador de golpes

    def on_ISP_AXO(self, packet: ISP_AXO):
        self._golpes[packet.PLID] = self._golpes.get(packet.PLID, 0) + 1
        golpes = self._golpes[packet.PLID]
        print(f"PLID {packet.PLID} golpeó objeto de autocross "
              f"(total: {golpes} golpes, +2s penalización)")
```
