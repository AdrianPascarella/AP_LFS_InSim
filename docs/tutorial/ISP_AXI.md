# ISP_AXI — AutoX Info

## Descripción
LFS envía este paquete con información sobre el layout de autocross activo. Se envía automáticamente cuando se carga un layout y puede solicitarse con `TINY_AXI`.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 40 |
| Type | byte | ISP_AXI |
| ReqI | byte | 0, o el ReqI de TINY_AXI |
| Zero | byte | 0 |
| AXStart | byte | Posición de inicio de autocross |
| NumCP | byte | Número de checkpoints |
| NumO | word | Número de objetos |
| LName | char[32] | Nombre del layout cargado (si se cargó localmente) |

## Ejemplo de uso

**Solicitar y recibir:**
```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_AXI
from lfs_insim.insim_enums import TINY

class MiInsim(InSimApp):
    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.AXI)

    def on_ISP_AXI(self, packet: ISP_AXI):
        nombre = packet.LName.decode('latin-1').rstrip('\x00')
        if nombre:
            print(f"Layout cargado: '{nombre}'")
            print(f"  Objetos: {packet.NumO}  Checkpoints: {packet.NumCP}")
        else:
            print("No hay layout cargado")
```
