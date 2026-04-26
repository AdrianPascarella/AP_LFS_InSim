# ISP_VER — Version Info

## Descripción
Paquete de información de versión enviado por LFS. Se recibe automáticamente al conectar si `ReqI` en el `IS_ISI` es distinto de cero. También puede solicitarse en cualquier momento enviando `TINY_VER`.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 20 |
| Type | byte | ISP_VER |
| ReqI | byte | Igual al ReqI del paquete de solicitud |
| Zero | byte | 0 |
| Version | char[8] | Versión de LFS, ej: "0.7F" |
| Product | char[6] | Producto: "DEMO" / "S1" / "S2" / "S3" |
| InSimVer | byte | Versión InSim negociada por LFS |
| Spare | byte | Reservado |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_VER
from lfs_insim.insim_enums import TINY

class MiInsim(InSimApp):
    def on_connect(self):
        # Solicitar versión manualmente
        self.send_ISP_TINY(ReqI=1, SubT=TINY.VER)

    def on_ISP_VER(self, packet: ISP_VER):
        print(f"LFS versión: {packet.Version}")
        print(f"Producto: {packet.Product}")
        print(f"InSim versión negociada: {packet.InSimVer}")
        if packet.InSimVer < 10:
            print("Advertencia: LFS no soporta InSim v10")
```
