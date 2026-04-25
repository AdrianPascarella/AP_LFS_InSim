# ISP_SSH — Screenshot

## Descripción
Paquete de doble uso para tomar capturas de pantalla. El InSim lo envía para solicitar una screenshot; LFS responde con otro IS_SSH confirmando el resultado. La imagen se guarda en `data\shots` en el formato configurado (bmp/jpg/png). Si Name está vacío, LFS genera un nombre automáticamente.

## Dirección
**Ambos**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 40 |
| Type | byte | ISP_SSH |
| ReqI | byte | solicitud: distinto de cero / respuesta: mismo valor |
| Error | byte | 0 = OK / otros valores son errores (ver abajo) |
| Sp0 | byte | 0 |
| Sp1 | byte | 0 |
| Sp2 | byte | 0 |
| Sp3 | byte | 0 |
| Name | char[32] | Nombre del archivo sin extensión — último byte = 0 |

### Códigos de error (SSH_x)
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | SSH_OK | OK: captura completada |
| 1 | SSH_DEDICATED | No se puede capturar en host dedicado |
| 2 | SSH_CORRUPTED | IS_SSH corrupto (ej: Name sin terminador) |
| 3 | SSH_NO_SAVE | No se pudo guardar la imagen |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_SSH
import time

class MiInsim(InSimApp):
    def tomar_screenshot(self, nombre: str = ""):
        self.send_ISP_SSH(ReqI=1, Error=0, Name=nombre[:31])

    def tomar_screenshot_automatica(self):
        # LFS genera nombre automáticamente con Name vacío
        timestamp = int(time.time())
        self.send_ISP_SSH(ReqI=1, Error=0, Name=f"insim_{timestamp}")

    def on_ISP_SSH(self, packet: ISP_SSH):
        if packet.ReqI:  # es respuesta
            nombre = packet.Name.decode('latin-1').rstrip('\x00')
            if packet.Error == 0:
                print(f"Screenshot guardado: {nombre}")
            else:
                print(f"Error en screenshot: código {packet.Error}")
```
