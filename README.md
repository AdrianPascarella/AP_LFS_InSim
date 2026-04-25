# AP LFS InSim

Framework modular en Python para desarrollar plugins de **LFS InSim v10** (Live for Speed). Permite crear módulos independientes con gestión automática de dependencias, ciclo de vida estandarizado y acceso al protocolo binario completo de LFS.

> Python 3.9+ · Sin dependencias externas · Pure stdlib

---

## Requisitos

- **Live for Speed** v0.7F o superior con InSim activado (ajustar en `cfg.txt`)
- **Python 3.9+**

---

## Instalación

```bash
git clone https://github.com/AdrianPascarella/AP_LFS_InSim
cd AP_LFS_InSim
pip install -e ".[dev]"
```

---

## Configuración

Edita `config/settings.py` para ajustar la conexión:

```python
INSIM_CONFIG = {
    "tcp_host": "127.0.0.1",
    "tcp_port": 29999,
    "udp_port": 30000,
    "prefix": "!",        # prefijo de comandos en el chat
    "interval": 100,      # ms entre actualizaciones NLP/MCI
    "insim_name": "InSimApp",
    "insim_ver": 10,
}
```

---

## CLI

```bash
# Ejecutar un InSim por nombre
lfs-insim run ai_control

# Listar InSims disponibles
lfs-insim list

# Ver metadatos de un InSim
lfs-insim info users_management

# Crear un nuevo InSim vacío
lfs-insim init mi_modulo

# Instalar git hooks (genera stubs .pyi en cada commit)
bash scripts/install-git-hooks.sh    # Linux/Mac
./scripts/install-git-hooks.ps1      # Windows

# Regenerar stubs de tipo manualmente
python src/lfs_insim/generate_stubs.py
```

---

## Tests

```bash
# Ejecutar toda la suite
pytest

# Un archivo concreto
pytest tests/test_utils.py

# Un test específico
pytest tests/test_utils.py::TestPIDController::test_zero_dt_returns_zero -v
```

---

## Módulos incluidos

| Módulo | Descripción |
|--------|-------------|
| `users_management` | Rastrea en tiempo real conexiones, jugadores e IAs. Mapea UCID ↔ PLID ↔ username. Expone posición y velocidad. |
| `ai_control` | Controla coches IA mediante PID. Soporta **RouteMode** (waypoints grabados) y **FreeroamMode** (grafo de calles con FSM). Depende de `users_management`. |
| `test_insim` | Módulo de demostración y prueba del protocolo. Cubre todos los paquetes ISP mediante comandos de chat (`!test <cmd>`). Útil como referencia de uso del framework. |

---

## Documentación del protocolo

`docs/tutorial/` contiene **69 archivos Markdown**, uno por tipo de paquete ISP. Cada archivo incluye:
- Descripción y dirección del paquete
- Tabla de campos con tipos enum correctos
- Ejemplo de uso con el framework

La fuente de verdad del protocolo binario es `docs/InSim.txt`.

---

## Escribir un módulo

### 1. Crear el scaffold

```bash
lfs-insim init mi_modulo
```

Genera la siguiente estructura:

```
insims/
└── mi_modulo/
    ├── insim.json
    ├── __init__.py
    └── main.py
```

### 2. Manifiesto (`insim.json`)

```json
{
    "name": "mi_modulo",
    "version": "1.0.0",
    "description": "Descripción breve",
    "author": "Tu nombre",
    "entry_point": "main.py",
    "insim_dependencies": {},
    "python_dependencies": []
}
```

Declara dependencias de otros InSims en `insim_dependencies` (p. ej. `"users_management": ">=1.0.0"`). El loader las resuelve y puedes acceder a ellas con `self.get_insim("users_management")`.

### 3. Clase del módulo (`main.py`)

```python
from lfs_insim import InSimApp
from lfs_insim.packets import *
from lfs_insim.insim_enums import ISF, PTYPE, TINY
from lfs_insim.utils import CMDManager, separate_command_args, TextColors as c


class MiModulo(InSimApp):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd_prefix: str = self.config.get("prefix", "!")
        self.cmd_base: str = "mi_modulo"
        self.cmds: CMDManager
        self.users: dict[int, dict] = {}   # UCID -> datos
        self.players: dict[int, dict] = {} # PLID -> datos
        self.logger.info(f"Modulo {self.name} inicializado.")

    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.LOCAL | ISF.MCI  # añadir flags necesarios

    def on_connect(self):
        # Pedir snapshot inicial de conexiones y jugadores
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NCN)
        self.send_ISP_TINY(ReqI=1, SubT=TINY.NPL)

        # Registrar comandos de chat
        self.cmds = (
            CMDManager(self.cmd_prefix, self.cmd_base)
            .add_cmd("hola", "Saluda al servidor", None, self._cmd_hola)
        )
        self.send_ISP_MSL(Msg=f"{c.GREEN}{self.name} {c.WHITE}conectado")

    # Gestión de conexiones
    def on_ISP_NCN(self, packet: ISP_NCN):
        self.users[packet.UCID] = {"uname": packet.UName, "plid": None}

    def on_ISP_CNL(self, packet: ISP_CNL):
        self.users.pop(packet.UCID, None)

    # Gestión de jugadores
    def on_ISP_NPL(self, packet: ISP_NPL):
        is_ai = bool(packet.PType & PTYPE.AI)
        self.players[packet.PLID] = {"ucid": packet.UCID, "car": packet.CName, "is_ai": is_ai}
        if not is_ai and packet.UCID in self.users:
            self.users[packet.UCID]["plid"] = packet.PLID

    def on_ISP_PLL(self, packet: ISP_PLL):
        player = self.players.pop(packet.PLID, None)
        if player and not player["is_ai"] and player["ucid"] in self.users:
            self.users[player["ucid"]]["plid"] = None

    # Despacho de comandos de chat
    def on_ISP_MSO(self, packet: ISP_MSO):
        cmd, args = separate_command_args(self.cmd_prefix, packet)
        if cmd == self.cmd_base:
            self.cmds.handle_commands(packet, args)

    def _cmd_hola(self):
        self.send_ISP_MSL(Msg=f"{c.GREEN}Hola desde mi_modulo!")

    def on_tick(self):
        pass  # llamado cada 'interval' ms

    def on_disconnect(self):
        self.logger.info(f"Modulo {self.name} desconectado.")
```

### 4. Ejecutar

```bash
lfs-insim run mi_modulo
```

---

## Arquitectura

```
CLI (cli.py)
  └── InSimLoader          descubre insim.json, resuelve deps, encadena módulos
        └── InSimApp       clase base de todo módulo; declara deps y maneja eventos
              └── InSimClient    orquestador maestro; gestiona sockets, agrega flags ISF, despacha paquetes
                    └── PacketSenderMixin    send_ISP_*() via __getattr__
```

**Patrón "coup d'état"**: el último módulo cargado se convierte en Master. Los cargados previamente pasan a `modules[]`. El Master fusiona los `isi.Flags` de todos antes de enviar `ISP_ISI`.

**Ciclo de un paquete**:
1. `insim_packet_io.py` recibe bytes por TCP/UDP y ensambla paquetes completos
2. `insim_packet_decoders.py` mapea el byte de tipo al dataclass correspondiente
3. `InSimClient` despacha `on_ISP_<TYPE>(packet)` al master y a cada módulo en `modules[]`

---

## Enviar paquetes

```python
# Forma recomendada (via PacketSenderMixin)
self.send_ISP_MSL(Msg="hola")

# Forma explícita (solo si necesitas construir el paquete por separado)
pkt = ISP_MSL(Msg="hola")
self.send(pkt)
```

---

## Módulos con mixins

Para módulos complejos, separa responsabilidades en mixins y combínalos con MRO. `InSimApp` debe ir al final para que los mixins hereden `self.send_*`. Usa el patrón `TYPE_CHECKING` para que el IDE reconozca los métodos del framework dentro del mixin:

```python
# mi_modulo/_commands.py
from __future__ import annotations
from typing import TYPE_CHECKING
from lfs_insim.packets import *
from lfs_insim.utils import CMDManager, TextColors as c

if TYPE_CHECKING:
    from lfs_insim import InSimApp as _Base
else:
    _Base = object

class _CommandsMixin(_Base):
    def _cmd_ejemplo(self):
        self.send_ISP_MSL(Msg=f"{c.GREEN}Ejemplo")  # IDE reconoce send_ISP_*
```

```python
# mi_modulo/main.py
from lfs_insim import InSimApp
from ._commands import _CommandsMixin
from ._physics import _PhysicsMixin

class MiModulo(_CommandsMixin, _PhysicsMixin, InSimApp):
    pass
```

---

## Utilidades

```python
from lfs_insim.utils import strip_lfs_colors, separate_command_args, CMDManager, PIDController, TextColors as c

# Quitar códigos de color de LFS (^0–^9, ^L, ^h)
texto_limpio = strip_lfs_colors(packet.Msg)

# Parsear comando del chat
cmd, args = separate_command_args("!", packet)

# Colores en mensajes (importar TextColors as c es la convención)
self.send_ISP_MSL(Msg=f"{c.RED}Error{c.WHITE} normal")
# Constantes: c.RED, c.GREEN, c.YELLOW, c.WHITE, c.BLUE, c.CYAN, c.PURPLE, c.BLACK

# PID con anti-windup (salida clamped a [-1.0, 1.0])
pid = PIDController(kp=0.5, ki=0.01, kd=0.1)
output = pid.update(setpoint, measured, dt)
```

---

## Stubs de tipo

Los archivos `.pyi` bajo `src/lfs_insim/` se generan automáticamente al hacer commit (via git hook) y proporcionan autocompletado en el IDE para todos los métodos `send_ISP_*`. Para instalar el hook:

```bash
bash scripts/install-git-hooks.sh    # Linux/Mac
./scripts/install-git-hooks.ps1      # Windows
```

---

## Excepciones

```
InSimError
├── InSimConnectionError    fallo de red o socket
├── InSimPacketError        paquete malformado
├── InSimModuleError        error de carga o dependencia
├── InSimConfigurationError ruta de config inválida
└── InSimCommandError       comando de chat incorrecto
```

---

## Protocolo LFS InSim v10

- Conexión TCP en el puerto **29999**, protocolo little-endian
- Strings en latin-1, terminadas en null; `Size` en la cabecera = bytes totales / 4
- OutSim/OutGauge vía UDP en el puerto **30000**
- Documentación oficial del protocolo en `docs/InSim.txt`
- Tutoriales por paquete en `docs/tutorial/`
