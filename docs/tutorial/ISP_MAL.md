# ISP_MAL — Mods Allowed

## Descripción
Paquete de doble uso para gestionar la lista de mods permitidos en el host. Permite configurar hasta 120 mods (identificados por SkinID comprimido). Enviar con NumM=0 limpia la lista y permite todos los mods. LFS también lo envía como notificación cuando la lista cambia. Se puede solicitar con `TINY_MAL`.

## Dirección
**Ambos**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 + NumM * 4 |
| Type | byte | ISP_MAL |
| ReqI | byte | 0, o el ReqI de la solicitud TINY_MAL |
| NumM | byte | Número de mods en el paquete |
| UCID | byte | ID de la conexión que actualizó la lista (info) |
| Flags | byte | 0 (por ahora) |
| Sp2 | byte | Reservado |
| Sp3 | byte | Reservado |
| SkinID | unsigned[120] | SkinID de cada mod en formato comprimido (0 a NumM) |

## Ejemplo de uso

**Solicitar y recibir la lista de mods:**
```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_MAL
from lfs_insim.insim_enums import TINY

class MiInsim(InSimApp):
    def on_connect(self):
        self.send_ISP_TINY(ReqI=1, SubT=TINY.MAL)

    def on_ISP_MAL(self, packet: ISP_MAL):
        if packet.NumM == 0:
            print("Todos los mods están permitidos")
        else:
            print(f"{packet.NumM} mods permitidos")
            for i in range(packet.NumM):
                print(f"  SkinID: {packet.SkinID[i]}")

    def permitir_todos_mods(self):
        # NumM=0 limpia la lista -> todos permitidos
        self.send_ISP_MAL(NumM=0, SkinID=[])
```
