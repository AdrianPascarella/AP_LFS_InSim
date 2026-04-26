# ISP_NCI — New Connection Info

## Descripción
Paquete enviado solo en el host cuando hay una contraseña de admin configurada. Proporciona información adicional sobre un guest que se conecta: idioma, tipo de licencia, ID de usuario LFS y dirección IP. Puede solicitarse con `TINY_NCI`.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 16 |
| Type | byte | ISP_NCI |
| ReqI | byte | 0, o el ReqI de la solicitud TINY_NCI |
| UCID | byte | ID de conexión (0 = host) |
| Language | LFS | Idioma (LFS_x) |
| License | LICENSE | DEMO=0 / S1=1 / S2=2 / S3=3 |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| UserID | unsigned | ID de usuario LFS |
| IPAddress | unsigned | Dirección IP del guest |

### Valores Language (LFS_x)
Algunos valores: 0=English, 1=Deutsch, 2=Portuguese, 3=French, 8=Turkish, 13=Russian, etc. Ver InSim.txt para lista completa.

## Ejemplo de uso

**Solicitar y procesar NCI de todos los guests:**
```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_NCI
from lfs_insim.insim_enums import TINY, LFS as LFS_LANG, LICENSE
import socket

class MiInsim(InSimApp):
    def on_connect(self):
        # Solicitar NCI de todos los guests (solo host con admin password)
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NCI)

    def on_ISP_NCI(self, packet: ISP_NCI):
        ip = socket.inet_ntoa(packet.IPAddress.to_bytes(4, 'little'))
        try:
            idioma = LFS_LANG(packet.Language).name.capitalize()
        except ValueError:
            idioma = f"id:{packet.Language}"
        try:
            licencia = LICENSE(packet.License).name
        except ValueError:
            licencia = "?"
        print(f"UCID {packet.UCID}: UserID={packet.UserID} IP={ip} "
              f"Idioma={idioma} Licencia={licencia}")
```
