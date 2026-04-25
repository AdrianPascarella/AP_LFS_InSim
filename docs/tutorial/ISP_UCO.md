# ISP_UCO — User Control Object

## Descripción
LFS envía este paquete cuando un coche cruza un checkpoint InSim o entra/sale de un círculo InSim colocados en el layout. Permite crear sistemas de timing personalizados y zonas de detección.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 28 |
| Type | byte | ISP_UCO |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| Sp0 | byte | Reservado |
| UCOAction | byte | Acción (UCO_x) |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| Time | unsigned | Ms desde inicio (como SMALL_RTP) |
| C | CarContOBJ | Info del coche en el momento |
| Info | ObjectInfo | Info sobre el checkpoint o círculo |

### Valores UCOAction (UCO_x)
| Valor | Nombre | Descripción |
|-------|--------|-------------|
| 0 | UCO_CIRCLE_ENTER | Entró en un círculo InSim |
| 1 | UCO_CIRCLE_LEAVE | Salió de un círculo InSim |
| 2 | UCO_CP_FWD | Cruzó checkpoint en dirección hacia adelante |
| 3 | UCO_CP_REV | Cruzó checkpoint en dirección inversa |

### Identificar checkpoint vs círculo desde ObjectInfo
- **Checkpoint** (`Index=252`): el índice del checkpoint (0-3) está en `Flags bits 0-1`. 0=meta, 1=CP1, 2=CP2, 3=CP3
- **Círculo** (`Index=253`): el índice del círculo está en el byte `Heading`

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_UCO

UCO_CIRCLE_ENTER = 0
UCO_CIRCLE_LEAVE = 1
UCO_CP_FWD       = 2
UCO_CP_REV       = 3

MARSH_IS_CP   = 252
MARSH_IS_AREA = 253

class MiInsim(InSimApp):
    def on_ISP_UCO(self, packet: ISP_UCO):
        idx = packet.Info.Index
        if idx == MARSH_IS_CP and packet.UCOAction == UCO_CP_FWD:
            cp_idx = packet.Info.Flags & 0x03  # 0=meta, 1=CP1, 2=CP2, 3=CP3
            print(f"PLID {packet.PLID} cruzó checkpoint {cp_idx} en {packet.Time}ms")
        elif idx == MARSH_IS_AREA:
            circulo = packet.Info.Heading
            accion = "entró" if packet.UCOAction == UCO_CIRCLE_ENTER else "salió"
            print(f"PLID {packet.PLID} {accion} del círculo {circulo}")
```
