# OutSimPack2 — OutSim v2 (configurable)

## Descripción
Paquete de telemetría física moderno y configurable. LFS lo envía por UDP al puerto configurado en `cfg.txt`. A diferencia de `OutSimPack`, su contenido depende del valor de `OutSim Opts` en `cfg.txt` — solo incluye los bloques de datos declarados con flags `OSO.*`.

El framework construye la clase `OutSimPack2` dinámicamente al arrancar según los `outsim_opts` que declaren los módulos en `set_outsim()`, y loguea exactamente qué poner en `cfg.txt`.

## Dirección
**LFS → InSim (UDP)**

## Activación en el framework

```python
from lfs_insim import InSimApp
from lfs_insim.insim_enums import OSO

class MiInsim(InSimApp):
    def set_outsim(self):
        super().set_outsim()
        self.outsim_opts = OSO.TIME | OSO.MAIN | OSO.INPUTS | OSO.DRIVE
```

Al arrancar, el log mostrará:
```
INFO | OutSim activo (OSO=0x3c): TIME | MAIN | INPUTS | DRIVE
INFO |   → cfg.txt requerido: OutSim Opts 3c | OutSim IP 127.0.0.1 | OutSim Port 30000
```

Configurar `cfg.txt` de LFS para que coincida:
```
OutSim Opts  3c
OutSim IP    127.0.0.1
OutSim Port  30000
```

## Bloques disponibles (flags OSO)

| Flag | Hex | Campos incluidos | Tamaño |
|------|-----|-----------------|--------|
| OSO.HEADER | 0x01 | L, F, S, T (firma "LFST") | 4 bytes |
| OSO.ID | 0x02 | ID (OutSim ID de cfg.txt) | 4 bytes |
| OSO.TIME | 0x04 | Time (ms) | 4 bytes |
| OSO.MAIN | 0x08 | AngVel, Heading, Pitch, Roll, Accel, Vel, Pos | 60 bytes |
| OSO.INPUTS | 0x10 | Throttle, Brake, InputSteer, Clutch, Handbrake | 20 bytes |
| OSO.DRIVE | 0x20 | Gear, EngineAngVel, MaxTorqueAtVel | 12 bytes |
| OSO.DISTANCE | 0x40 | CurrentLapDist, IndexedDistance | 8 bytes |
| OSO.WHEELS | 0x80 | OSWheels[4] (suspensión, fuerzas, slip, etc.) | 160 bytes |
| OSO.EXTRA_1 | 0x100 | SteerTorque, Spare | 8 bytes |
| OSO.ALL | 0x1ff | Todos los bloques | 280 bytes |

## Estructura OSMain (bloque MAIN)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| AngVel | Vector (3 floats) | Velocidad angular (rad/s) |
| Heading | float | Antihorario desde arriba (Z) |
| Pitch | float | Antihorario desde la derecha (X) |
| Roll | float | Antihorario desde adelante (Y) |
| Accel | Vector (3 floats) | Aceleración X, Y, Z |
| Vel | Vector (3 floats) | Velocidad X, Y, Z |
| Pos | Vec (3 ints) | Posición X, Y, Z (1m = 65536) |

## Estructura OutSimWheel (bloque WHEELS, ×4)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| SuspDeflect | float | Compresión de la suspensión |
| Steer | float | Ángulo de dirección (incluye Ackermann y toe) |
| XForce | float | Fuerza lateral (N) |
| YForce | float | Fuerza longitudinal (N) |
| VerticalLoad | float | Carga vertical (N) |
| AngVel | float | Velocidad angular de la rueda (rad/s) |
| LeanRelToRoad | float | Inclinación relativa al suelo (rad) |
| AirTemp | byte | Temperatura del aire en la rueda (°C) |
| SlipFraction | byte | Fracción de deslizamiento (0-255) |
| Touching | byte | 1 si la rueda toca el suelo |
| SlipRatio | float | Slip ratio |
| TanSlipAngle | float | Tangente del ángulo de deslizamiento |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.insim_enums import OSO, GEAR
from lfs_insim.packets.outsim import OutSimPack2
import math

class MiInsim(InSimApp):

    def set_outsim(self):
        super().set_outsim()
        self.outsim_opts = OSO.TIME | OSO.MAIN | OSO.INPUTS | OSO.DRIVE

    def on_OutSimPack2(self, packet: OutSimPack2):
        # Velocidad en km/h a partir del vector de velocidad
        vx, vy, vz = packet.OSMain.Vel
        speed_kmh = math.sqrt(vx**2 + vy**2 + vz**2) * 3.6

        # Posición en metros
        x = packet.OSMain.Pos[0] / 65536
        y = packet.OSMain.Pos[1] / 65536

        # Marcha
        try:
            gear = GEAR(packet.Gear).name
        except ValueError:
            gear = str(packet.Gear)

        # Inputs
        throttle = packet.OSInputs.Throttle  # 0.0 – 1.0
        brake    = packet.OSInputs.Brake

        print(
            f"pos=({x:.1f}, {y:.1f}) | {speed_kmh:.1f} km/h | "
            f"{gear} | gas={throttle*100:.0f}% freno={brake*100:.0f}%"
        )
```

**Con bloque WHEELS** (para análisis de neumáticos):

```python
from lfs_insim.insim_enums import OSO

class MiInsim(InSimApp):

    def set_outsim(self):
        super().set_outsim()
        self.outsim_opts = OSO.MAIN | OSO.WHEELS

    def on_OutSimPack2(self, packet: OutSimPack2):
        # packet.OSWheels: tuple de 4 OutSimWheel [RL, RR, FL, FR]
        for i, wheel in enumerate(packet.OSWheels):
            nombre = ['Trasera-Izq', 'Trasera-Der', 'Delantera-Izq', 'Delantera-Der'][i]
            print(f"{nombre}: carga={wheel.VerticalLoad:.0f}N slip={wheel.SlipRatio:.3f}")
```
