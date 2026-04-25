# ISP_NLP — Node and Lap Packet

## Descripción
Paquete compacto de posiciones de todos los coches en carrera. Se envía a intervalos regulares cuando se activa `ISF_NLP` en el ISI. Contiene información básica: nodo actual, vuelta y posición en carrera. Para información más detallada usar `IS_MCI`. Puede solicitarse un paquete puntual con `TINY_NLP`.

## Dirección
**LFS → InSim**

## Flags requeridos (si aplica)
Requiere `ISF.NLP` en `set_isi_packet()` y un `Interval` mayor que 0 en el ISI. **No activar a la vez ISF_NLP e ISF_MCI** ya que la información de NLP está incluida en MCI.

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 4 + NumP * 6 (+ 2 si necesario para múltiplo de 4) |
| Type | byte | ISP_NLP |
| ReqI | byte | 0, o el ReqI de TINY_NLP |
| NumP | byte | Número de jugadores en carrera |
| Info | NodeLap[40] | Info de cada jugador (hasta NLP_MAX_CARS=40) |

### Estructura NodeLap (6 bytes)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Node | word | Nodo actual del path |
| Lap | word | Vuelta actual |
| PLID | byte | ID único del jugador |
| Position | byte | Posición en carrera (0=desconocida, 1=líder, etc.) |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_NLP
from lfs_insim.insim_enums import ISF

class MiInsim(InSimApp):
    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.NLP
        self.isi.Interval = 200  # cada 200 ms

    def on_ISP_NLP(self, packet: ISP_NLP):
        for i in range(packet.NumP):
            info = packet.Info[i]
            print(f"P{info.Position} PLID {info.PLID}: "
                  f"nodo {info.Node} vuelta {info.Lap}")
```
