# OutGaugePack — OutGauge

## Descripción
Paquete de telemetría del tablero del coche. LFS lo envía por UDP al puerto configurado en `cfg.txt` cuando se activa mediante `SMALL.SSG`. Contiene RPM, velocidad, temperatura, combustible, presión de aceite y luces del dashboard. Útil para dashboards externos, overlays HUD y sistemas de telemetría.

## Dirección
**LFS → InSim (UDP)**

## Activación
Enviar `ISP_SMALL(SubT=SMALL.SSG, UVal=intervalo_ms)` desde `on_connect()`. `UVal=0` detiene el envío.

No requiere flags ISF.

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Time | unsigned | Timestamp en ms |
| Car | char[4] | Nombre del coche (ej: "XFG") |
| Flags | OG | Flags de estado (turbo, km/h vs mph, bar vs psi) |
| Gear | GEAR | Marcha actual (REVERSE=0, NEUTRAL=1, FIRST=2...) |
| PLID | byte | ID del jugador |
| Speed | float | Velocidad en m/s |
| RPM | float | RPM del motor |
| Turbo | float | Presión de turbo (bar) |
| EngTemp | float | Temperatura del motor (°C) |
| Fuel | float | Combustible (0.0 a 1.0) |
| OilPressure | float | Presión de aceite (bar) |
| OilTemp | float | Temperatura del aceite (°C) |
| DashLights | DL | Luces del dashboard disponibles (bitmask) |
| ShowLights | DL | Luces del dashboard activas (bitmask) |
| Throttle | float | Acelerador (0.0 a 1.0) |
| Brake | float | Freno (0.0 a 1.0) |
| Clutch | float | Embrague (0.0 a 1.0) |
| Display1 | char[16] | Texto display 1 (velocímetro) |
| Display2 | char[16] | Texto display 2 (info adicional) |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.insim_enums import SMALL, GEAR, DL
from lfs_insim.packets.outsim import OutGaugePack

class MiInsim(InSimApp):

    def on_connect(self):
        # Activar envío cada 50 ms
        self.send_ISP_SMALL(SubT=SMALL.SSG, UVal=50)

    def on_OutGaugePack(self, packet: OutGaugePack):
        speed_kmh = packet.Speed * 3.6
        try:
            gear = GEAR(packet.Gear).name
        except ValueError:
            gear = str(packet.Gear)

        abs_active = bool(packet.ShowLights & DL.ABS)
        tc_active  = bool(packet.ShowLights & DL.TC)

        print(
            f"{packet.Car} | {speed_kmh:.0f} km/h | {gear} | "
            f"{packet.RPM:.0f} RPM | Fuel {packet.Fuel*100:.0f}%"
            f"{' [ABS]' if abs_active else ''}{' [TC]' if tc_active else ''}"
        )
```
