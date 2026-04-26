# ISP_III — InSim Info (/i message)

## Descripción
LFS envía este paquete cuando un usuario escribe `/i MENSAJE` en el chat. El mensaje va al InSim del host y no se muestra en pantalla. Tamaño variable entre 12 y 72 bytes.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 12, 16, 20… 72 (según longitud de Msg) |
| Type | byte | ISP_III |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| UCID | byte | ID de conexión (0 = host) |
| PLID | byte | ID de jugador (si es 0, usar UCID) |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| Msg | char[64] | Texto del mensaje (variable, último byte es cero) |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_III
from lfs_insim.utils import TextColors as c

class MiInsim(InSimApp):
    def on_ISP_III(self, packet: ISP_III):
        # Mensaje privado del usuario al InSim via /i
        mensaje = packet.Msg
        print(f"Mensaje /i de UCID {packet.UCID}: {mensaje}")

        # Responder con un mensaje local al remitente
        if mensaje.strip() == "estado":
            self.send_ISP_MTC(
                UCID=packet.UCID,
                Msg=f"{c.GREEN}El servidor está operativo"
            )
```
