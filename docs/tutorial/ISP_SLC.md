# ISP_SLC — Selected Car

## Descripción
LFS envía este paquete cuando una conexión selecciona un coche (o lo deselecciona). Si `CName` está vacío, la conexión no tiene coche seleccionado. También se envía si un nuevo guest se conecta y ya tiene un coche seleccionado. Puede solicitarse con `TINY_SLC`.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_SLC |
| ReqI | byte | 0, o el ReqI de la solicitud TINY_SLC |
| UCID | byte | ID de conexión (0 = host) |
| CName | char[4] | Nombre del coche seleccionado (vacío si no hay coche) |

## Ejemplo de uso

**Solicitar y monitorear:**
```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_SLC
from lfs_insim.insim_enums import TINY

class MiInsim(InSimApp):
    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.SLC)

    def on_ISP_SLC(self, packet: ISP_SLC):
        coche = packet.CName
        if coche:
            print(f"UCID {packet.UCID} seleccionó: {coche}")
        else:
            print(f"UCID {packet.UCID} no tiene coche seleccionado")
```
