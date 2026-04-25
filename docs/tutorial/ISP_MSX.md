# ISP_MSX — Message Extended

## Descripción
Similar a `IS_MST` pero permite mensajes más largos (hasta 96 caracteres). No puede usarse para comandos de LFS, solo para mensajes de chat visibles en pantalla.

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 100 |
| Type | byte | ISP_MSX |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| Msg | char[96] | Mensaje (NO sirve para comandos) — el último byte debe ser cero |

## Ejemplo de uso

```python
from lfs_insim import InSimApp
from lfs_insim.utils import TextColors as c

class MiInsim(InSimApp):
    def anuncio_largo(self, texto: str):
        # Para mensajes que exceden los 64 caracteres de MST
        self.send_ISP_MSX(Msg=texto[:95])

    def on_connect(self):
        self.send_ISP_MSX(
            Msg=f"{c.YELLOW}Bienvenido al servidor. {c.WHITE}Respeta las normas de conducción."
        )
```
