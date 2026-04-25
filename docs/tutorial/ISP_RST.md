# ISP_RST — Race Start

## Descripción
LFS envía este paquete al inicio de cada carrera o sesión de calificación. Contiene información sobre el track, número de jugadores, laps, y posiciones de splits. Puede solicitarse en cualquier momento con `TINY_RST`.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 28 |
| Type | byte | ISP_RST |
| ReqI | byte | 0, o el ReqI de la solicitud TINY_RST |
| Zero | byte | 0 |
| RaceLaps | byte | 0 si es calificación; número de laps si es carrera |
| QualMins | byte | 0 si es carrera; minutos de calificación |
| NumP | byte | Número de jugadores en carrera |
| Timing | RST_TIMING | Info de timing de laps (ver abajo) |
| Track | char[6] | Nombre corto del track, ej: "FE2R" |
| Weather | WEATHER | Condición climática (CLEAR/CLOUDY/RAIN) |
| Wind | WIND | Viento: OFF / WEAK / STRONG |
| Flags | HOSTF | Flags de carrera (HOSTF_x) |
| NumNodes | word | Número total de nodos en el path |
| Finish | word | Índice de nodo de la línea de meta |
| Split1 | word | Índice de nodo del split 1 |
| Split2 | word | Índice de nodo del split 2 |
| Split3 | word | Índice de nodo del split 3 |

### Byte Timing
- Bits 6-7 (`Timing & 0xc0`): `0x40` = timing estándar / `0x80` = checkpoints personalizados / `0xc0` = sin timing
- Bits 0-1 (`Timing & 0x03`): número de checkpoints si el timing está activo

### Flags HOSTF_x
| Flag | Valor | Descripción |
|------|-------|-------------|
| HOSTF_CAN_VOTE | 1 | Los jugadores pueden votar |
| HOSTF_CAN_SELECT | 2 | Los jugadores pueden seleccionar |
| HOSTF_MID_RACE | 32 | Unión a mitad de carrera permitida |
| HOSTF_MUST_PIT | 64 | Parada en pits obligatoria |
| HOSTF_CAN_RESET | 128 | Los jugadores pueden resetear |
| HOSTF_FCV | 256 | Velocidad fija para carros |
| HOSTF_CRUISE | 512 | Modo cruise |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_RST
from lfs_insim.insim_enums import TINY

class MiInsim(InSimApp):
    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.RST)

    def on_ISP_RST(self, packet: ISP_RST):
        track = packet.Track
        if packet.RaceLaps == 0:
            print(f"Calificación: {packet.QualMins} min en {track}")
        else:
            print(f"Carrera: {packet.RaceLaps} laps en {track}")
        print(f"Jugadores: {packet.NumP}")
```
