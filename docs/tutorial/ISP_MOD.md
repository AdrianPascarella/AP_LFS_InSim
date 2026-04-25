# ISP_MOD — Set Screen Mode

## Descripción
Instrucción para cambiar el modo de pantalla de LFS (resolución, frecuencia, ventana o pantalla completa). Si Width y Height son ambos cero, LFS cambia a modo ventana.

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 20 |
| Type | byte | ISP_MOD |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| Bits16 | MOD_BIT | BIT32=0 / BIT16=1 |
| RR | int | Frecuencia de refresco en Hz (0 = por defecto) |
| Width | int | Ancho en píxeles (0 = ir a ventana) |
| Height | int | Alto en píxeles (0 = ir a ventana) |

**Nota:** La frecuencia de refresco elegida por LFS será la mayor disponible menor o igual a la especificada.

## Ejemplo de uso

```python
from lfs_insim import InSimApp

class MiInsim(InSimApp):
    def cambiar_a_ventana(self):
        # Width=0 y Height=0 cambia a modo ventana
        self.send_ISP_MOD(Bits16=0, RR=0, Width=0, Height=0)

    def cambiar_a_fullhd(self):
        # 1920x1080 a 60 Hz, 32 bits
        self.send_ISP_MOD(Bits16=0, RR=60, Width=1920, Height=1080)
```
