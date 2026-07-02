# ISP_SET — Setup

## Descripción
LFS envía este paquete cuando un guest envía su setup al host (disponible desde 0.8C3). Contiene los 120 bytes del setup en crudo, casi igual que un fichero de setup sin sus primeros 12 bytes.

**Nota sobre las marchas:** el orden difiere del fichero de setup. En el fichero: 7ª marcha, luego FDR, luego las otras 6 marchas. En `Setup` (que viene de RAM): las 7 marchas y después la FDR.

## Dirección
**LFS → InSim**

## Flags requeridos (si aplica)
Requiere `ISF.SET` en `set_isi_packet()`.

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 136 (puede cambiar con futuras versiones de setup) |
| Type | byte | ISP_SET |
| ReqI | byte | 0 |
| PLID | byte | ID único del jugador |
| CName | char[4] | Prefijo del skin (nombre corto del coche) |
| Spare | unsigned | Reservado |
| FuelLoad | byte | Combustible al inicio |
| Sp1 | byte | Reservado |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| Setup | byte[120] | Setup en crudo (ver nota sobre marchas) |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_SET
from lfs_insim.insim_enums import ISF

class MiInsim(InSimApp):
    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.SET   # recibir setups de los guests

    def on_ISP_SET(self, packet: ISP_SET):
        print(f"PLID {packet.PLID} envió su setup de {packet.CName} "
              f"(fuel {packet.FuelLoad}, {len(packet.Setup)} bytes)")
        # packet.Setup es una lista de 120 ints (bytes crudos del setup)
```
