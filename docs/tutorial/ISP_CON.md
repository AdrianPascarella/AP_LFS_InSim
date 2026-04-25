# ISP_CON — Contact Between Cars

## Descripción
LFS envía este paquete cuando dos coches colisionan con una velocidad de cierre superior a 0.25 m/s. Contiene información detallada de ambos coches en el momento del impacto (velocidad, steer, aceleración, posición).

## Dirección
**LFS → InSim**

## Flags requeridos (si aplica)
Requiere `ISF.CON` en `set_isi_packet()`.

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 44 |
| Type | byte | ISP_CON |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| SpClose | word | bits 0-11: velocidad de cierre (10 = 1 m/s); bits 12-15: reservados |
| SpW | word | Reservado |
| Time | unsigned | Timestamp en ms |
| A | CarContact | Info del coche A |
| B | CarContact | Info del coche B |

### Estructura CarContact (16 bytes)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| PLID | byte | ID del jugador |
| Info | byte | Flags CCI_x (como en CompCar) |
| Sp2 | byte | Reservado |
| Steer | char | Ángulo de dirección en grados (derecha positivo) |
| ThrBrk | byte | bits 4-7: acelerador / bits 0-3: freno (0-15) |
| CluHan | byte | bits 4-7: embrague / bits 0-3: freno de mano (0-15) |
| GearSp | byte | bits 4-7: marcha (15=R) / bits 0-3: reservado |
| Speed | byte | Velocidad en m/s |
| Direction | byte | Dirección del movimiento (0=Y mundial, 128=180°) |
| Heading | byte | Dirección del eje delantero (0=Y mundial, 128=180°) |
| AccelF | char | Aceleración longitudinal en m/s² (adelante positivo) |
| AccelR | char | Aceleración lateral en m/s² (derecha positivo) |
| X | short | Posición X (1 metro = 16) |
| Y | short | Posición Y (1 metro = 16) |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_CON
from lfs_insim.insim_enums import ISF

class MiInsim(InSimApp):
    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.CON

    def on_ISP_CON(self, packet: ISP_CON):
        vel_cierre = (packet.SpClose & 0x0FFF) / 10.0  # m/s
        print(f"Colisión entre PLID {packet.A.PLID} y PLID {packet.B.PLID}: "
              f"cierre a {vel_cierre:.1f} m/s")
        # Registrar PLIDs involucrados para sistema de penalizaciones
```
