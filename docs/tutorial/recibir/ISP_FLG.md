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
| OffOn | OFFON | 0 = bandera quitada (OFFON.OFF) / 1 = bandera puesta (OFFON.ON) |
| Flag | BYF | BYF.BLUE=1 (bandera azul) / BYF.YELLOW=2 (causando amarilla) |
| CarBehind | byte | PLID del jugador obstruido (para bandera azul) |
| Sp3 | byte | Reservado |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_FLG
from lfs_insim.insim_enums import BYF, OFFON
from lfs_insim.utils import TextColors as c

class MiInsim(InSimApp):
    def on_ISP_FLG(self, packet: ISP_FLG):
        if packet.OffOn == OFFON.OFF:
            return  # bandera quitada, no hacer nada
        if packet.Flag == BYF.BLUE:
            print(f"PLID {packet.PLID} recibe bandera azul "
                  f"(obstaculiza a PLID {packet.CarBehind})")
            self.send_ISP_MTC(
                UCID=0,
                Msg=f"{c.YELLOW}Bandera azul para PLID {packet.PLID}"
            )
        elif packet.Flag == BYF.YELLOW:
            print(f"PLID {packet.PLID} causa bandera amarilla")
```
