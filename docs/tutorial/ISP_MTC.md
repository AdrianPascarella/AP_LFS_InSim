# ISP_MTC — Message To Connection

## Descripción
Envía un mensaje de texto a una conexión específica, a un jugador específico, o a todos (UCID=255). El mensaje aparece en la pantalla del destinatario. Funciona solo en hosts. Soporta hasta 128 caracteres con efecto de sonido opcional.

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 + TEXT_SIZE (TEXT_SIZE = 4, 8, 12… 128) |
| Type | byte | ISP_MTC |
| ReqI | byte | 0 |
| Sound | SND | Efecto de sonido (SND_x) |
| UCID | byte | ID de conexión destino (0 = host / 255 = todos) |
| PLID | byte | ID de jugador destino (si es 0, usar UCID) |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| Text | char[variable] | Texto hasta 128 caracteres (last byte = 0) |

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
from lfs_insim.packets import ISP_NCN
from lfs_insim.insim_enums import SND
from lfs_insim.utils import TextColors as c

class MiInsim(InSimApp):
    def on_ISP_NCN(self, packet: ISP_NCN):
        nombre = packet.PName
        # Mensaje de bienvenida personal al nuevo jugador
        self.send_ISP_MTC(
            Sound=SND.SYSMESSAGE,
            UCID=packet.UCID,
            Msg=f"{c.YELLOW}Bienvenido {nombre}! Lee las normas del servidor."
        )

    def mensaje_a_todos(self, texto: str):
        self.send_ISP_MTC(Sound=SND.MESSAGE, UCID=255, Msg=texto)
```
