# ISP_NCN — New Connection

## Descripción
LFS envía este paquete cuando un nuevo jugador se conecta al host. También se envía en respuesta a `TINY_NCN` para listar todas las conexiones activas. El host mismo (UCID=0) se incluye en la lista.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 56 |
| Type | byte | ISP_NCN |
| ReqI | byte | 0, o el ReqI de la solicitud TINY_NCN |
| UCID | byte | ID único de la nueva conexión (0 = host) |
| UName | char[24] | Nombre de usuario de LFS |
| PName | char[24] | Nickname del jugador |
| Admin | byte | 1 si es admin |
| Total | byte | Número total de conexiones (incluyendo host) |
| Flags | byte | bit 2: remoto (guest) |
| Sp3 | byte | Reservado |

## Ejemplo de uso

**Solicitar lista al conectar:**
```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_NCN
from lfs_insim.insim_enums import TINY
from lfs_insim.utils import TextColors as c

class MiInsim(InSimApp):
    def __init__(self):
        super().__init__()
        self.conexiones = {}  # UCID -> info

    def on_connect(self):
        # Solicitar todas las conexiones activas
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NCN)

    def on_ISP_NCN(self, packet: ISP_NCN):
        uname = packet.UName.decode('latin-1').rstrip('\x00')
        pname = packet.PName.decode('latin-1').rstrip('\x00')
        self.conexiones[packet.UCID] = {'uname': uname, 'pname': pname}
        print(f"Nueva conexión UCID {packet.UCID}: {pname} ({uname})")
        if packet.UCID != 0:  # no saludar al host
            self.send_ISP_MTC(
                UCID=packet.UCID,
                Msg=f"{c.YELLOW}Bienvenido {pname}!"
            )
```
