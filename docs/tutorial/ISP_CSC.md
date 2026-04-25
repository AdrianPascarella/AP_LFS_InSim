# ISP_CSC — Car State Changed

## Descripción
LFS envía este paquete cuando el estado de un coche cambia. Actualmente reporta cuando un coche se detiene (`CSC_STOP`) o empieza a moverse (`CSC_START`). Incluye el timestamp y la posición/velocidad del coche.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 20 |
| Type | byte | ISP_CSC |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| Sp0 | byte | Reservado |
| CSCAction | CSC | Acción (CSC_x) |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| Time | unsigned | Ms desde inicio (como SMALL_RTP) |
| C | CarContOBJ | Info del coche en el momento |

### Valores CSCAction (CSC_x)
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | CSC_STOP | El coche se detuvo |
| 1 | CSC_START | El coche comenzó a moverse |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_CSC
from lfs_insim.insim_enums import CSC

class MiInsim(InSimApp):
    def on_ISP_CSC(self, packet: ISP_CSC):
        estado = "detuvo" if packet.CSCAction == CSC.STOP else "comenzó a moverse"
        print(f"PLID {packet.PLID}: coche {estado} en t={packet.Time}ms")
        # Útil para detectar coches parados en pista (safety car, etc.)
```
