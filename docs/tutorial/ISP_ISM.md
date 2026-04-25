# ISP_ISM — InSim Multi

## Descripción
LFS envía este paquete cuando se inicia o se une a un host multijugador. Puede solicitarse en cualquier momento con `TINY_ISM`. Si LFS no está en modo multijugador, el nombre del host estará vacío.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 40 |
| Type | byte | ISP_ISM |
| ReqI | byte | 0 normalmente / o ReqI recibido en TINY_ISM |
| Zero | byte | 0 |
| Host | byte | 0 = guest / 1 = host |
| Sp1 | byte | Reservado |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| HName | char[32] | Nombre del host al que se unió o que se inició |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_ISM
from lfs_insim.insim_enums import TINY

class MiInsim(InSimApp):
    def on_connect(self):
        # Solicitar info multijugador al conectar
        self.send_ISP_TINY(ReqI=1, SubT=TINY.ISM)

    def on_ISP_ISM(self, packet: ISP_ISM):
        nombre = packet.HName.decode('latin-1', errors='replace').rstrip('\x00')
        rol = "host" if packet.Host else "guest"
        if nombre:
            print(f"Conectado como {rol} al servidor: {nombre}")
        else:
            print("LFS no está en modo multijugador")
```
