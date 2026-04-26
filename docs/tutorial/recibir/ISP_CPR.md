# ISP_CPR — Connection Player Rename

## Descripción
LFS envía este paquete cuando un jugador conectado cambia su nickname o matrícula.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 36 |
| Type | byte | ISP_CPR |
| ReqI | byte | 0 |
| UCID | byte | ID de la conexión |
| PName | char[24] | Nuevo nickname |
| Plate | char[8] | Nueva matrícula — SIN CERO AL FINAL |

**Nota:** El campo `Plate` no tiene terminador nulo; usar los 8 bytes tal cual.

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_CPR

class MiInsim(InSimApp):
    def __init__(self):
        super().__init__()
        self.nombres = {}  # UCID -> pname

    def on_ISP_CPR(self, packet: ISP_CPR):
        nuevo_nombre = packet.PName
        viejo_nombre = self.nombres.get(packet.UCID, "desconocido")
        placa = packet.Plate
        self.nombres[packet.UCID] = nuevo_nombre
        print(f"UCID {packet.UCID}: '{viejo_nombre}' -> '{nuevo_nombre}' [{placa}]")
```
