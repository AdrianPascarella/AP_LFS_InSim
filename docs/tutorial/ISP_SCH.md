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
| CharB | byte | Tecla a pulsar (usar mayúscula para letras estándar) |
| Flags | byte | bit 0: SHIFT / bit 1: CTRL |
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
        # CTRL + C (Flags bit 1 = CTRL)
        self.send_ISP_SCH(CharB=ord('C'), Flags=2)

    def presionar_escape(self):
        # Para teclas especiales usar IS_MST con /press
        self.send_ISP_MST(Msg="/press escape")
```
