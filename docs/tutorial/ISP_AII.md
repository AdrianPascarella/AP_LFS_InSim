# ISP_AII — AI Info

## Descripción
LFS envía este paquete con información detallada sobre el estado físico de un coche AI local. Se obtiene enviando `SMALL_AII` con el PLID, o configurando el envío periódico con `CS_REPEAT_AI_INFO` en un `IS_AIC`. Contiene datos de posición, velocidad, aceleración, RPM, luces de dashboard, etc.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 96 |
| Type | byte | ISP_AII |
| ReqI | byte | ReqI del SMALL_AII que lo solicitó |
| PLID | byte | ID del jugador AI |
| OSData | OSMain | Datos de movimiento principales (ver abajo) |
| Flags | AI_FLAGS | Estado motor/palancas de cambio |
| Gear | GEAR | Marcha actual: REVERSE=0, NEUTRAL=1, FIRST=2... |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| RPM | float | RPM del motor |
| SpF0 | float | Reservado |
| SpF1 | float | Reservado |
| ShowLights | DL | Luces de dashboard activas (DL_x, como en OutGauge) |
| SPU1 | unsigned | Reservado |
| SPU2 | unsigned | Reservado |
| SPU3 | unsigned | Reservado |

### Estructura OSMain (datos de movimiento)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| AngVel | Vector (3 floats) | Velocidad angular (rad/s) |
| Heading | float | Antihorario desde arriba (Z) |
| Pitch | float | Antihorario desde la derecha (X) |
| Roll | float | Antihorario desde adelante (Y) |
| Accel | Vector (3 floats) | Aceleración X, Y, Z |
| Vel | Vector (3 floats) | Velocidad X, Y, Z |
| Pos | Vec (3 ints) | Posición X, Y, Z (1m = 65536) |

### Flags AIFLAGS_x
| Flag | Valor | Descripción |
|------|-------|-------------|
| AIFLAGS_IGNITION | 1 | Motor encendido |
| AIFLAGS_CHUP | 4 | Palanca de subida de marcha activa |
| AIFLAGS_CHDN | 8 | Palanca de bajada de marcha activa |

## Ejemplo de uso

**Solicitar info del AI y procesar:**
```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_AII
from lfs_insim.insim_enums import SMALL

class MiInsim(InSimApp):
    def solicitar_info_ai(self, plid: int):
        # SMALL_AII con UVal=PLID
        self.send_ISP_SMALL(SubT=SMALL.AII, UVal=plid)

    def on_ISP_AII(self, packet: ISP_AII):
        # Posición en metros
        x = packet.OSData.Pos[0] / 65536
        y = packet.OSData.Pos[1] / 65536
        z = packet.OSData.Pos[2] / 65536
        # Velocidad en m/s (magnitud del vector vel)
        import math
        vx, vy, vz = packet.OSData.Vel
        vel_ms = math.sqrt(vx**2 + vy**2 + vz**2)
        print(f"AI PLID {packet.PLID}: pos=({x:.1f}, {y:.1f}, {z:.1f}) "
              f"vel={vel_ms*3.6:.1f} km/h marcha={packet.Gear-1} "
              f"RPM={packet.RPM:.0f}")
```
