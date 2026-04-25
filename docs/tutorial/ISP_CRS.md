# ISP_CRS — Car Reset

## Descripción
LFS envía este paquete cuando un jugador resetea su coche (vuelve a pista desde una posición de emergencia). Es un paquete de solo 4 bytes.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 4 |
| Type | byte | ISP_CRS |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_CRS

class MiInsim(InSimApp):
    def on_ISP_CRS(self, packet: ISP_CRS):
        print(f"PLID {packet.PLID} reseteó su coche")
        # Se puede usar para invalidar tiempos de vuelta en curso
        # o para registrar el evento en logs
```
