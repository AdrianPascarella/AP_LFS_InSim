# ISP_MSL — Message Local

## Descripción
Envía un mensaje que aparece solo en el ordenador local (no se muestra a otros jugadores en multijugador). Admite hasta 128 caracteres y permite especificar un efecto de sonido.

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 132 |
| Type | byte | ISP_MSL |
| ReqI | byte | 0 |
| Sound | byte | Efecto de sonido (SND_x) |
| Msg | char[128] | Mensaje — el último byte debe ser cero |

### Valores Sound (SND_x)
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | SND_SILENT | Sin sonido |
| 1 | SND_MESSAGE | Sonido de mensaje normal |
| 2 | SND_SYSMESSAGE | Sonido de mensaje del sistema |
| 3 | SND_INVALIDKEY | Sonido de tecla inválida |
| 4 | SND_ERROR | Sonido de error |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_MSO
from lfs_insim.utils import TextColors as c

SND_MESSAGE = 1
SND_ERROR = 4

class MiInsim(InSimApp):
    def on_ISP_MSO(self, packet: ISP_MSO):
        msg = packet.Msg.decode('latin-1', errors='replace').rstrip('\x00')
        if "hola" in msg.lower():
            # Responder solo visible en el PC local
            self.send_ISP_MSL(
                Sound=SND_MESSAGE,
                Msg=f"{c.GREEN}Hola recibido desde InSim!"
            )
```
