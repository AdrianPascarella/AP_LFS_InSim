# ISP_MSO — Message Out

## Descripción
LFS envía este paquete cuando aparece un mensaje en la pantalla del juego: mensajes del sistema, mensajes de usuarios, mensajes con prefijo especial y mensajes `/o`. El tamaño varía entre 12 y 136 bytes según la longitud del mensaje.

## Dirección
**LFS → InSim**

## Flags requeridos (si aplica)
Para recibir los mensajes con colores LFS intactos, activar `ISF.MSO_COLS` en `set_isi_packet()`.

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 12, 16, 20… 136 (según longitud de Msg) |
| Type | byte | ISP_MSO |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| UCID | byte | ID de conexión (0 = host) |
| PLID | byte | ID de jugador (si es 0, usar UCID) |
| UserType | byte | Tipo de mensaje (MSO_x) |
| TextStart | byte | Índice del primer carácter del texto real (tras el nombre del jugador) |
| Msg | char[128] | Texto del mensaje (variable, último byte es cero) |

### UserType values (MSO_x)
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | MSO_SYSTEM | Mensaje del sistema |
| 1 | MSO_USER | Mensaje normal visible del usuario |
| 2 | MSO_PREFIX | Mensaje oculto con prefijo especial (ver ISI) |
| 3 | MSO_O | Mensaje oculto con comando `/o` |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_MSO
from lfs_insim.insim_enums import ISF
from lfs_insim.utils import strip_lfs_colors, TextColors as c

class MiInsim(InSimApp):
    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.MSO_COLS  # conservar códigos de color

    def on_ISP_MSO(self, packet: ISP_MSO):
        # Obtener solo el texto (sin nombre del jugador)
        texto_completo = packet.Msg.decode('latin-1', errors='replace')
        texto_real = texto_completo[packet.TextStart:]
        texto_limpio = strip_lfs_colors(texto_real)

        if packet.UserType == 2:  # MSO_PREFIX — mensaje con prefijo
            print(f"Comando de UCID {packet.UCID}: {texto_limpio}")
            if texto_limpio.startswith("hola"):
                self.send_ISP_MSL(Msg=f"{c.GREEN}Hola desde InSim!")
```
