# ISP_PLC — Player Cars

## Descripción
Instrucción para limitar qué coches puede seleccionar una conexión específica. El conjunto resultante es la intersección con los coches permitidos globalmente en el host (via `/cars` o `SMALL_ALC`). Enviar Cars=0 impide seleccionar cualquier coche; Cars=0xffffffff permite todos los disponibles en el host.

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 12 |
| Type | byte | ISP_PLC |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| UCID | byte | ID de conexión (0 = host / 255 = todos) |
| Sp1 | byte | Reservado |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| Cars | unsigned | Bitmask de coches permitidos (ver CARS) |

### Bitmask CARS (coches disponibles)
| Bit | Valor | Coche |
|-----|-------|-------|
| 0 | 1 | XF GTI |
| 1 | 2 | XR GT |
| 2 | 4 | XR GT TURBO |
| 3 | 8 | RB4 GT |
| 4 | 0x10 | FXO TURBO |
| 5 | 0x20 | LX4 |
| 6 | 0x40 | LX6 |
| 7 | 0x80 | MRT5 |
| 8 | 0x100 | UF 1000 |
| 9 | 0x200 | RACEABOUT |
| 10 | 0x400 | FZ50 |
| 11 | 0x800 | FORMULA XR |
| 12 | 0x1000 | XF GTR |
| 13 | 0x2000 | UF GTR |
| 14 | 0x4000 | FORMULA V8 |
| 15 | 0x8000 | FXO GTR |
| 16 | 0x10000 | XR GTR |
| 17 | 0x20000 | FZ50 GTR |
| 18 | 0x40000 | BMW SAUBER F1.06 |
| 19 | 0x80000 | FORMULA BMW FB02 |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_NCN

# Solo coches de calle: XF GTI + XR GT + FXO TURBO + LX4 + LX6
COCHES_CALLE = 0x1 | 0x2 | 0x10 | 0x20 | 0x40

class MiInsim(InSimApp):
    def on_ISP_NCN(self, packet: ISP_NCN):
        # Restringir coches al nuevo jugador
        self.send_ISP_PLC(UCID=packet.UCID, Cars=COCHES_CALLE)

    def permitir_todos(self, ucid: int):
        self.send_ISP_PLC(UCID=ucid, Cars=0xffffffff)
```
