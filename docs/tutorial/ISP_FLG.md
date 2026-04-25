# ISP_FLG — Flag

## Descripción
LFS envía este paquete cuando un jugador recibe o pierde una bandera (azul o amarilla). Permite saber qué jugador la recibe y quién la causa.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_FLG |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador que recibe la bandera |
| OffOn | byte | 0 = bandera quitada / 1 = bandera puesta |
| Flag | byte | 1 = bandera azul / 2 = causando amarilla |
| CarBehind | byte | PLID del jugador obstruido (para bandera azul) |
| Sp3 | byte | Reservado |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_FLG
from lfs_insim.utils import TextColors as c

FLAG_BLUE   = 1
FLAG_YELLOW = 2

class MiInsim(InSimApp):
    def on_ISP_FLG(self, packet: ISP_FLG):
        if not packet.OffOn:
            return  # bandera quitada, no hacer nada
        if packet.Flag == FLAG_BLUE:
            print(f"PLID {packet.PLID} recibe bandera azul "
                  f"(obstaculiza a PLID {packet.CarBehind})")
            self.send_ISP_MTC(
                UCID=0,  # al host (broadcast local)
                Msg=f"{c.YELLOW}Bandera azul para PLID {packet.PLID}"
            )
        elif packet.Flag == FLAG_YELLOW:
            print(f"PLID {packet.PLID} causa bandera amarilla")
```
