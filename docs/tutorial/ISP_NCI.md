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
| Language | byte | Idioma (LFS_x) |
| License | byte | 0 = demo / 1 = S1 / 2 = S2 / 3 = S3… |
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
from lfs_insim.insim_enums import TINY
import socket

IDIOMAS = {0: "English", 1: "Deutsch", 2: "Português", 3: "Français", 13: "Русский"}

class MiInsim(InSimApp):
    def on_connect(self):
        # Solicitar NCI de todos los guests (solo host con admin password)
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NCI)

    def on_ISP_NCI(self, packet: ISP_NCI):
        ip = socket.inet_ntoa(packet.IPAddress.to_bytes(4, 'little'))
        idioma = IDIOMAS.get(packet.Language, f"id:{packet.Language}")
        licencias = {0: "Demo", 1: "S1", 2: "S2", 3: "S3"}
        licencia = licencias.get(packet.License, "?")
        print(f"UCID {packet.UCID}: UserID={packet.UserID} IP={ip} "
              f"Idioma={idioma} Licencia={licencia}")
```
