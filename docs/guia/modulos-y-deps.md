# Módulos y dependencias

Cómo se estructura un módulo, cómo declara que depende de otro, y los patrones
para módulos que crecen (comandos, mixins, estado compartido). Si vienes del
[quickstart](quickstart.md), esto es el siguiente paso.

---

## Anatomía de un módulo

Un módulo (una `InSimApp`) es una carpeta bajo `insims/` con, como mínimo:

```
insims/mi_modulo/
├── insim.json        manifiesto: nombre, versión, dependencias, entry point
├── __init__.py       marca la carpeta como paquete
└── main.py           el entry point: define la clase InSimApp
```

El **loader** descubre el módulo por su `insim.json`, importa el `entry_point` e
**instancia la primera clase que herede de `InSimApp`** que encuentre en él.

> **El nombre de la clase no es lo que la localiza.** Por convención se escribe en
> CamelCase del nombre del módulo (`mi_modulo` → `MiModulo`), pero el loader busca
> por herencia, no por nombre — por eso `ai_control` puede exponer una clase
> llamada `AIControl`. Ten una sola clase `InSimApp` por entry point para evitar
> ambigüedad.

---

## El manifiesto `insim.json`

```json
{
    "name": "mi_modulo",
    "version": "1.0.0",
    "description": "Descripción breve",
    "author": "Tu nombre",
    "entry_point": "main.py",
    "insim_dependencies": {
        "users_management": ">=1.0.0"
    },
    "python_dependencies": []
}
```

| Campo | Para qué |
|---|---|
| `name` | Nombre del módulo (así lo invocas: `lfs-insim run mi_modulo`). |
| `version` | Versión del módulo. La usan los **constraints** de quien dependa de ti. |
| `description` | Descripción libre (la muestra `lfs-insim info`). |
| `author` | Autor. |
| `entry_point` | Archivo con la clase `InSimApp` (normalmente `main.py`). El loader lee **`entry_point`**, no `entry`. |
| `insim_dependencies` | Otros módulos de los que dependes, como `{"nombre": "constraint"}`. Ver abajo. |
| `python_dependencies` | Paquetes PyPI que el módulo necesita (p. ej. `ai_control` declara `matplotlib`). |

---

## Depender de otro módulo

### 1. Declarar la dependencia

En `insim.json`, dentro de `insim_dependencies`, con un **constraint de versión**:

```json
"insim_dependencies": {
    "users_management": ">=1.0.0"
}
```

El loader lo trata así, en orden:

1. **Carga la dependencia primero** (recursivamente). Las dependencias se registran
   en el cliente ANTES que el dependiente, de modo que el **orden de dispatch sigue
   al de dependencias**: un tracker procesa cada paquete antes que la app que
   consume su estado.
2. **Valida la versión.** Compara la `version` del manifiesto de la dependencia
   contra tu constraint. Si no cumple, aborta con `InSimModuleError`:
   ```
   'mi_modulo' requires 'users_management>=2.0.0' but the installed version is 1.0.0
   ```
3. **Fail-fast** (P20): si la dependencia no se puede cargar (no existe, sin clase
   `InSimApp`, manifiesto roto...), la carga del dependiente se aborta con la cadena
   completa en el mensaje, en vez de fallar mucho más tarde:
   ```
   Cannot load 'mi_modulo': dependency 'users_management' failed: InSim not found: users_management
   ```

### 2. Acceder a la dependencia en runtime

Con `self.get_insim("nombre")`. Guárdala en `on_connect()`:

```python
class MiModulo(InSimApp):

    def on_connect(self):
        self.um = self.get_insim("users_management")

    def on_ISP_MCI(self, packet):
        for info in packet.Info:
            player = self.um.get_player(info.PLID)   # usar el estado de la dependencia
            ...
```

`get_insim` devuelve la **misma instancia** que el loader registró (las
dependencias son singletons dentro de un cliente), o `None` si el módulo no está
cargado.

---

## Compartir estado con otro módulo

Si necesitas colgar estado tuyo de un objeto que gestiona otro módulo (p. ej.
`users_management` te da los objetos de IA), usa el diccionario `extra` en vez de
subclasear o parchear:

```python
from dataclasses import dataclass

@dataclass
class MiEstado:
    ultimo_tick: float = 0.0

# Al crear tu estado para esa IA:
ai.extra["mi_modulo"] = MiEstado()

# Al leerlo (comprueba existencia primero):
if "mi_modulo" in ai.extra:
    estado = ai.extra["mi_modulo"]
```

Usa una clave propia (el nombre de tu módulo) para no chocar con otros. Así
`ai_control` guarda su `AIBehavior` en `ai.extra["aic"]`.

---

## Comandos de chat

El patrón recomendado es `CMDManager`, un builder fluido para árboles de comandos
con espacio de nombres:

```python
from lfs_insim.utils import CMDManager, separate_command_args

def on_connect(self):
    cmds = CMDManager(self.cmd_prefix, self.cmd_base)
    (cmds
     .add_cmd("start", "Arranca la IA", None, self._cmd_start)
     .add_cmd("speed", "Fija la velocidad", (("kmh", int),), self._cmd_speed)
     .add_cmd("msg",   "Envía un mensaje", "text", self._cmd_msg, is_mso_required=True)
    )
    self.cmds = cmds.submit()   # imprime la ayuda de uso en el chat de LFS

def on_ISP_MSO(self, packet):
    cmd, args = separate_command_args(self.cmd_prefix, packet)
    if cmd == self.cmd_base:
        self.cmds.handle_commands(packet, args)
```

- Los args se declaran tipados: `(("kmh", int),)` valida y convierte antes de
  llamar a tu handler. `None` = sin args; `"text"` = resto de la línea como texto.
- **`is_mso_required=True`** pasa el `ISP_MSO` crudo como primer argumento del
  handler (útil para leer `packet.UCID` y validar quién manda el comando).
  `False` (default) pasa solo los args tipados.
- Escribir `!base <cmd> ?` en el juego muestra la ayuda de ese comando.

Para comandos sueltos sin árbol, `separate_command_args(prefix, packet)` te da el
comando y sus args. Recuerda **validar el `UCID`** antes de actuar sobre comandos
sensibles.

> Limpia los códigos de color de LFS (`^0`–`^9`, `^L`, `^h`) de los mensajes con
> `strip_lfs_colors(texto)`. Para enviar color, usa las constantes de `TextColors`.

---

## Módulos complejos: mixins

Para separar responsabilidades, divide el módulo en mixins (cada uno en su archivo)
y combínalos por MRO. **`InSimApp` va al final** para que los mixins hereden
`self.send_*`:

```python
class AIControl(_CommandsMixin, _PhysicsMixin, _NavigationMixin, InSimApp):
    pass
```

Dentro de cada mixin, usa el patrón `TYPE_CHECKING` para que el IDE reconozca los
métodos del framework sin crear un ciclo de herencia en runtime:

```python
# mi_modulo/_commands.py
from __future__ import annotations
from typing import TYPE_CHECKING
from lfs_insim.utils import TextColors as c

if TYPE_CHECKING:
    from lfs_insim import InSimApp as _Base
else:
    _Base = object

class _CommandsMixin(_Base):
    def _cmd_ejemplo(self):
        self.send_ISP_MSL(Msg=f"{c.GREEN}Ejemplo")   # el IDE reconoce send_ISP_*
```

En runtime el mixin hereda de `object` (no de `InSimApp`), así que **no cuenta como
clase `InSimApp`** para el loader — solo la clase final (`AIControl`) lo es.

---

## Ver también

- [Referencia de la API pública](api-publica.md) — la superficie de `InSimApp`,
  las utilidades y las claves de config.
- [Arquitectura](arquitectura.md) — orden de dispatch, hilos y ciclo de vida.
- Ejemplos: `insims/test_insim/` (referencia mínima), `insims/users_management/`
  (tracking) y `insims/ai_control/` (mixins + navegación).
