# ISP_IPB — IP Bans

## Descripción
Paquete de doble uso para gestionar la lista de IPs baneadas del host (hasta 120 IPs). LFS también lo envía cuando la lista cambia. Se puede solicitar con `TINY_IPB`.

## Dirección
**Ambos**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 + NumB * 4 |
| Type | byte | ISP_IPB |
| ReqI | byte | 0, o el ReqI de la solicitud TINY_IPB |
| NumB | byte | Número de IPs baneadas en el paquete |
| Sp0 | byte | Reservado |
| Sp1 | byte | Reservado |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| BanIPs | in_addr[120] | IPs baneadas (unsigned de 4 bytes, little-endian) |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_IPB
from lfs_insim.insim_enums import TINY
import socket
import struct

class MiInsim(InSimApp):
    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.IPB)

    def on_ISP_IPB(self, packet: ISP_IPB):
        print(f"IPs baneadas: {packet.NumB}")
        for i in range(packet.NumB):
            ip_bytes = struct.pack('<I', packet.BanIPs[i])
            ip_str = socket.inet_ntoa(ip_bytes)
            print(f"  {ip_str}")

    def banear_ip(self, ip_str: str):
        ip_bytes = socket.inet_aton(ip_str)
        ip_uint = struct.unpack('<I', ip_bytes)[0]
        self.send_ISP_IPB(NumB=1, BanIPs=[ip_uint])
```
