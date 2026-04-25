# ISP_OBH — Object Hit

## Descripción
LFS envía este paquete cuando un coche golpea un objeto de autocross o un objeto desconocido del entorno. Contiene información sobre el coche y el objeto golpeado.

## Dirección
**LFS → InSim**

## Flags requeridos (si aplica)
Requiere `ISF.OBH` en `set_isi_packet()`.

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 28 |
| Type | byte | ISP_OBH |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| SpClose | word | bits 0-11: velocidad de cierre (10 = 1 m/s) |
| SpW | word | Reservado |
| Time | unsigned | Timestamp en ms |
| C | CarContOBJ | Info del coche |
| X | short | Posición X del objeto (como ObjectInfo) |
| Y | short | Posición Y del objeto (como ObjectInfo) |
| Zbyte | byte | Zbyte del objeto (si OBH_LAYOUT está activo) |
| Sp1 | byte | Reservado |
| Index | byte | AXO_x del objeto o 0 si es desconocido |
| OBHFlags | byte | Flags del objeto (OBH_x) |

### Estructura CarContOBJ (8 bytes)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Direction | byte | Dirección del movimiento |
| Heading | byte | Dirección del eje delantero |
| Speed | byte | Velocidad en m/s |
| Zbyte | byte | Altitud |
| X | short | Posición X (1 metro = 16) |
| Y | short | Posición Y (1 metro = 16) |

### Flags OBH_x
| Flag | Valor | Descripción |
|------|-------|-------------|
| OBH_LAYOUT | 1 | Objeto añadido (del layout) |
| OBH_CAN_MOVE | 2 | Objeto móvil |
| OBH_WAS_MOVING | 4 | Estaba en movimiento antes del impacto |
| OBH_ON_SPOT | 8 | Objeto en su posición original |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_OBH
from lfs_insim.insim_enums import ISF

OBH_LAYOUT = 1

class MiInsim(InSimApp):
    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.OBH

    def on_ISP_OBH(self, packet: ISP_OBH):
        vel_ms = packet.C.Speed
        es_layout = bool(packet.OBHFlags & OBH_LAYOUT)
        tipo = f"objeto layout (idx {packet.Index})" if es_layout else "objeto desconocido"
        print(f"PLID {packet.PLID} golpeó {tipo} a {vel_ms} m/s")
```
