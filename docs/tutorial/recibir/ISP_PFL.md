# ISP_PFL — Player Flags

## Descripción
LFS envía este paquete cuando cambian las ayudas al conductor de un jugador (flags PIF_x). Por ejemplo, si el jugador activa o desactiva cambios automáticos, ABS, etc.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_PFL |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| Flags | PIF | Flags del jugador (PIF_x) — ver ISP_NPL |
| Spare | word | Reservado |

### Flags PIF_x principales
| Flag | Valor | Descripción |
|------|-------|-------------|
| PIF_LEFTSIDE | 1 | Conducción por la izquierda |
| PIF_AUTOGEARS | 8 | Cambios automáticos |
| PIF_SHIFTER | 16 | Palanca de cambios |
| PIF_FLEXIBLE_STEER | 32 | Dirección flexible |
| PIF_HELP_B | 64 | Ayuda de freno |
| PIF_AXIS_CLUTCH | 128 | Embrague por eje |
| PIF_INPITS | 256 | En pits |
| PIF_AUTOCLUTCH | 512 | Embrague automático |
| PIF_CUSTOM_VIEW | 8192 | Vista personalizada |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_PFL
from lfs_insim.insim_enums import PIF

class MiInsim(InSimApp):
    def on_ISP_PFL(self, packet: ISP_PFL):
        ayudas = []
        if packet.Flags & PIF.AUTOGEARS:
            ayudas.append("cambios automáticos")
        if packet.Flags & PIF.HELP_B:
            ayudas.append("ayuda de freno")
        if packet.Flags & PIF.AUTOCLUTCH:
            ayudas.append("embrague automático")
        print(f"PLID {packet.PLID} - Ayudas activas: {', '.join(ayudas) or 'ninguna'}")
```
