# ISP_NPL — New Player

## Descripción
LFS envía este paquete cuando un jugador entra a la carrera, o cuando sale de pits (si ya existía el PLID). También se usa para solicitudes de unión al servidor si `ISF_REQ_JOIN` está activo (en ese caso `NumP=0`). Se puede solicitar lista con `TINY_NPL`.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 76 |
| Type | byte | ISP_NPL |
| ReqI | byte | 0, o el ReqI de TINY_NPL |
| PLID | byte | ID único del jugador (asignado al unirse) |
| UCID | byte | ID de la conexión del jugador |
| PType | byte | bit 0: female / bit 1: AI / bit 2: remote |
| Flags | word | Flags de jugador (PIF_x) |
| PName | char[24] | Nickname |
| Plate | char[8] | Matrícula (sin terminador nulo) |
| CName | char[4] | Nombre del coche |
| SName | char[16] | Nombre del skin |
| Tyres | byte[4] | Compuestos de neumáticos [rear L, rear R, front L, front R] |
| H_Mass | byte | Masa añadida (kg) |
| H_TRes | byte | Restricción de admisión |
| Model | byte | Modelo de piloto |
| Pass | byte | Byte de pasajeros |
| RWAdj | byte | Reducción de ancho de neumáticos traseros (bits 0-3) |
| FWAdj | byte | Reducción de ancho de neumáticos delanteros (bits 0-3) |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| SetF | byte | Flags de configuración (SETF_x) |
| NumP | byte | Posición en carrera (0 = solicitud de unión) |
| Config | byte | Configuración del coche |
| Fuel | byte | Combustible inicial (% si /showfuel yes; 255 si no) |

### Flags PIF_x (jugador)
| Flag | Valor | Descripción |
|------|-------|-------------|
| PIF_LEFTSIDE | 1 | Conducción por la izquierda |
| PIF_AUTOGEARS | 8 | Cambios automáticos |
| PIF_SHIFTER | 16 | Palanca de cambios |
| PIF_FLEXIBLE_STEER | 32 | Dirección flexible |
| PIF_HELP_B | 64 | Ayuda de freno |
| PIF_AXIS_CLUTCH | 128 | Embrague por eje |
| PIF_INPITS | 256 | Está en pits |
| PIF_AUTOCLUTCH | 512 | Embrague automático |
| PIF_CUSTOM_VIEW | 8192 | Vista personalizada |

### Flags SETF_x (configuración)
| Flag | Valor |
|------|-------|
| SETF_SYMM_WHEELS | 1 |
| SETF_TC_ENABLE | 2 |
| SETF_ABS_ENABLE | 4 |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_NPL
from lfs_insim.insim_enums import TINY

class MiInsim(InSimApp):
    def __init__(self):
        super().__init__()
        self.jugadores = {}  # PLID -> info

    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NPL)

    def on_ISP_NPL(self, packet: ISP_NPL):
        if packet.NumP == 0:
            # Solicitud de unión — responder con IS_JRR
            return
        nombre = packet.PName.decode('latin-1').rstrip('\x00')
        coche = packet.CName.decode('latin-1').rstrip('\x00')
        es_ai = bool(packet.PType & 2)
        self.jugadores[packet.PLID] = {
            'nombre': nombre, 'coche': coche, 'ucid': packet.UCID
        }
        print(f"{'[AI]' if es_ai else ''} PLID {packet.PLID}: {nombre} en {coche}")
```
