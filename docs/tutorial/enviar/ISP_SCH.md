# ISP_SCH — Single Character

## Descripción
Envía una pulsación de tecla individual a LFS, como si el usuario la hubiera presionado. Para teclas estándar se deben usar letras mayúsculas. No funciona con todas las teclas (F-keys, flechas, CTRL no soportados). Para esas teclas usar `IS_MST` con `/press`, `/shift`, `/ctrl`, `/alt`.

## Dirección
**InSim → LFS**

## Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| Size | byte | 8 |
| Type | byte | ISP_SCH |
| ReqI | byte | 0 |
| Zero | byte | 0 |
| CharB | CHARS | Tecla a pulsar (usar mayúscula para letras estándar) |
| Flags | SCH_FLAGS | SCH_FLAGS.SHIFT / SCH_FLAGS.CTRL |
| Spare2 | byte | Reservado |
| Spare3 | byte | Reservado |

## Ejemplo de uso

```python
from lfs_insim import InSimApp

class MiInsim(InSimApp):
    def presionar_v(self):
        # Simular tecla V (cambiar vista en LFS)
        self.send_ISP_SCH(CharB=ord('V'), Flags=0)

    def presionar_h(self):
        # Simular tecla H (bocina)
        self.send_ISP_SCH(CharB=ord('H'), Flags=0)

    def presionar_ctrl_c(self):
        # CTRL + C
        from lfs_insim.insim_enums import SCH_FLAGS
        self.send_ISP_SCH(CharB=ord('C'), Flags=SCH_FLAGS.CTRL)

    def presionar_escape(self):
        # Para teclas especiales usar IS_MST con /press
        self.send_ISP_MST(Msg="/press escape")
```
