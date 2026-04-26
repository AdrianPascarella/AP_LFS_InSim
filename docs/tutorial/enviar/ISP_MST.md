# ISP_MST — Message Type

## Descripción
Envía un mensaje de texto o comando a LFS como si el usuario lo hubiera escrito. Permite hasta 64 caracteres. También funciona para ejecutar comandos de LFS (ej: `/kick`, `/spectate`).

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 68 |
| Type | byte | ISP_MST |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| Msg | char[64] | Mensaje o comando — el último byte debe ser cero |

## Ejemplo de uso

```python
from lfs_insim import InSimApp

class MiInsim(InSimApp):
    def enviar_mensaje_chat(self, texto: str):
        # Enviar mensaje como si el host lo hubiera escrito
        self.send_ISP_MST(Msg=texto[:63])

    def kickear_jugador(self, username: str):
        # Ejecutar comando de admin
        self.send_ISP_MST(Msg=f"/kick {username}")

    def cambiar_track(self, track: str):
        self.send_ISP_MST(Msg=f"/track {track}")
```
