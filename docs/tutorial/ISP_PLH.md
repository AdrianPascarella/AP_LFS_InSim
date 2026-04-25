# ISP_PLH — Player Handicaps

## Descripción
Paquete de doble uso: el InSim lo envía para establecer hándicaps por jugador individual (no por modelo de coche); LFS lo envía de vuelta a todos los clientes InSim confirmando los hándicaps actualizados. También se emite cuando un hándicap se establece mediante comandos de texto (`/h_mass`, `/h_tres`). Los hándicaps duran hasta que el jugador especia o vuelve del pit/garage.

## Dirección
**Ambos**

## Flags requeridos (si aplica)
Para solicitar la lista actual: enviar `TINY_PLH`.

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 4 + NumP * 4 |
| Type | byte | ISP_PLH |
| ReqI | byte | 0, o el ReqI de la solicitud TINY_PLH |
| NumP | byte | Número de jugadores en el paquete |
| HCaps | PlayerHCap[48] | Array de hándicaps (hasta PLH_MAX_PLAYERS=48) |

### Estructura PlayerHCap (4 bytes)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| PLID | byte | ID único del jugador |
| Flags | byte | bit 0: set Mass / bit 1: set TRes / bit 7: silencioso (sin mensaje en pantalla) |
| H_Mass | byte | 0 a 200 — masa añadida en kg |
| H_TRes | byte | 0 a 50 — restricción de admisión |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_PLH
from lfs_insim.insim_enums import TINY, PHC

class MiInsim(InSimApp):
    def on_connect(self):
        # Solicitar hándicaps actuales
        self.send_ISP_TINY(ReqI=1, SubT=TINY.PLH)

    def on_ISP_PLH(self, packet: ISP_PLH):
        # LFS notifica hándicaps actualizados
        print(f"Hándicaps actualizados para {packet.NumP} jugadores")

    def aplicar_handicap_jugador(self, plid: int, masa: int, restriccion: int):
        # Flags=3 -> set Mass Y TRes; bit 7 en Flags=silencioso
        hcap = {
            'PLID': plid,
            'Flags': PHC.MASS | PHC.TRES | PHC.SILENT,
            'H_Mass': masa,
            'H_TRes': restriccion,
        }
        self.send_ISP_PLH(NumP=1, HCaps=[hcap])
```
