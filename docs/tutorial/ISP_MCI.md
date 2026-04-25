# ISP_MCI — Multi Car Info

## Descripción
Paquete detallado de posiciones de coches en carrera. Se envía a intervalos regulares cuando se activa `ISF_MCI` en el ISI. Si hay más de 16 coches, se envían múltiples paquetes MCI. Contiene posición 3D, velocidad, dirección y heading de cada coche. Puede solicitarse un paquete puntual con `TINY_MCI`.

## Dirección
**LFS → InSim**

## Flags requeridos (si aplica)
Requiere `ISF.MCI` en `set_isi_packet()` y un `Interval` mayor que 0 en el ISI.

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 4 + NumC * 28 |
| Type | byte | ISP_MCI |
| ReqI | byte | 0, o el ReqI de TINY_MCI |
| NumC | byte | Número de CompCar válidos en este paquete |
| Info | CompCar[16] | Info de cada coche (hasta MCI_MAX_CARS=16) |

### Estructura CompCar (28 bytes)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Node | word | Nodo actual del path |
| Lap | word | Vuelta actual |
| PLID | byte | ID único del jugador |
| Position | byte | Posición en carrera (0=desconocida, 1=líder, etc.) |
| Info | byte | Flags CCI_x |
| Sp3 | byte | Reservado |
| X | int | Posición X (65536 = 1 metro) |
| Y | int | Posición Y (65536 = 1 metro) |
| Z | int | Altitud Z (65536 = 1 metro) |
| Speed | word | Velocidad (32768 = 100 m/s) |
| Direction | word | Dirección del movimiento (0=Y mundial, 32768=180°) |
| Heading | word | Dirección del eje delantero (0=Y mundial, 32768=180°) |
| AngVel | short | Velocidad angular firmada (16384 = 360°/s) |

### Flags CCI_x (byte Info de CompCar)
| Flag | Valor | Descripción |
|------|-------|-------------|
| CCI_BLUE | 1 | En camino de un coche a una vuelta más |
| CCI_YELLOW | 2 | Lento/parado en zona peligrosa |
| CCI_OOB | 4 | Fuera del path |
| CCI_LAG | 32 | Con lag (paquetes perdidos o retrasados) |
| CCI_FIRST | 64 | Primer CompCar de este set de MCI |
| CCI_LAST | 128 | Último CompCar de este set de MCI |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_MCI
from lfs_insim.insim_enums import ISF

class MiInsim(InSimApp):
    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.MCI
        self.isi.Interval = 100  # cada 100 ms

    def on_ISP_MCI(self, packet: ISP_MCI):
        for i in range(packet.NumC):
            c = packet.Info[i]
            # Convertir posición de unidades LFS a metros
            x_m = c.X / 65536
            y_m = c.Y / 65536
            # Convertir velocidad (32768 = 100 m/s -> m/s)
            vel_ms = c.Speed * 100 / 32768
            vel_kmh = vel_ms * 3.6
            print(f"PLID {c.PLID}: ({x_m:.1f}, {y_m:.1f}) "
                  f"{vel_kmh:.0f} km/h P{c.Position}")
```
