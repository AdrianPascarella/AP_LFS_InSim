# ISP_ACR — Admin Command Report

## Descripción
LFS envía este paquete cuando un usuario escribe un comando de administrador. Indica si el comando fue procesado, rechazado o desconocido. Tamaño variable entre 12 y 72 bytes.

## Dirección
**LFS → InSim**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 12, 16, 20… 72 (según longitud de Text) |
| Type | byte | ISP_ACR |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| UCID | byte | ID de conexión (0 = host) |
| Admin | byte | 1 si el usuario es admin |
| Result | byte | 1 = procesado / 2 = rechazado / 3 = comando desconocido |
| Sp3 | byte | Reservado |
| Text | char[64] | Texto del comando (variable, último byte es cero) |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.packets import ISP_ACR

class MiInsim(InSimApp):
    def on_ISP_ACR(self, packet: ISP_ACR):
        comando = packet.Text.decode('latin-1', errors='replace').rstrip('\x00')
        resultados = {1: "procesado", 2: "rechazado", 3: "desconocido"}
        estado = resultados.get(packet.Result, "?")
        admin = "admin" if packet.Admin else "usuario"
        print(f"Comando de {admin} UCID {packet.UCID}: '{comando}' -> {estado}")
```
