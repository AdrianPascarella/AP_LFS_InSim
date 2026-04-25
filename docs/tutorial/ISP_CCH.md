# ISP_CCH — Camera Change

## Descripción
LFS envía este paquete cuando un jugador existente cambia de cámara. Para rastrear cámaras correctamente hay que considerar: (1) la cámara por defecto `VIEW_DRIVER`, (2) el flag `PIF_CUSTOM_VIEW` en NPL que indica vista personalizada al inicio o al salir de pits, (3) los cambios reportados por este paquete.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_CCH |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| Camera | byte | Identificador de vista (VIEW_x) |
| Sp1 | byte | Reservado |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |

### Valores VIEW_x
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | VIEW_FOLLOW | Arcade / seguimiento |
| 1 | VIEW_HELI | Helicóptero |
| 2 | VIEW_CAM | Cámara TV |
| 3 | VIEW_DRIVER | Cockpit |
| 4 | VIEW_CUSTOM | Personalizada |
| 255 | VIEW_ANOTHER | Viendo otro coche |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_CCH

VIEW_NAMES = {0: "arcade", 1: "helicoptero", 2: "TV", 3: "cockpit", 4: "personalizada"}

class MiInsim(InSimApp):
    def on_ISP_CCH(self, packet: ISP_CCH):
        vista = VIEW_NAMES.get(packet.Camera, f"desconocida ({packet.Camera})")
        print(f"PLID {packet.PLID} cambió a vista: {vista}")
```
