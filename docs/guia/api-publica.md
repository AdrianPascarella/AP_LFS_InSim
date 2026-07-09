# Referencia de la API pública

La superficie estable del framework (P15). Cada módulo público define `__all__`;
lo que no aparece aquí es interno y puede cambiar sin aviso.

---

## Puntos de import recomendados

| Import | Qué trae |
|---|---|
| `lfs_insim` | Clases del core, config y excepciones (ver abajo). |
| `lfs_insim.packets` | Dataclasses de paquetes (`ISP_*`), sub-estructuras y OutSim. **No re-exporta enums.** |
| `lfs_insim.insim_enums` | Enums y constantes del protocolo (`ISF`, `TINY`, `SMALL`, `PTYPE`, `OSO`, ...). |
| `lfs_insim.utils` | Helpers: comandos, colores, PID, conversiones y distancia 3D. |

> `lfs_insim.insim_packet_class` es una **facade deprecada** (emite
> `DeprecationWarning`) que re-exporta paquetes + enums como el monolito original.
> No la uses en código nuevo.

---

## `lfs_insim`

```python
from lfs_insim import InSimApp, InSimClient, InSimLoader, build_config
```

| Nombre | Tipo | Descripción |
|---|---|---|
| `__version__` | `str` | Versión del paquete (fuente única; `pyproject` la lee de aquí). |
| `InSimApp` | clase | Clase base de todo módulo. Ver [su superficie](#insimapp). |
| `InSimClient` | clase | El cliente: sockets, decode, dispatch, ciclo de vida, reconexión. |
| `InSimLoader` | clase | Descubre y carga módulos, resuelve dependencias, los registra en el cliente. |
| `InSimTransport` | clase | Sockets TCP/UDP e hilos receptores (uno por cliente, inyectable). |
| `PacketSenderMixin` | clase | Da `send()` y los mágicos `send_ISP_*()`. |
| `DEFAULT_CONFIG` | `dict` | Defaults del framework. Ver [Config](#config). |
| `build_config(overrides)` | función | Devuelve un dict fresco: defaults fusionados con `overrides`. |
| `mute_send_logs(tipo)` / `unmute_send_logs(tipo)` | función | Silencia/reactiva el log de envío de un tipo de paquete (p. ej. `'ISP_AIC'`). |
| Excepciones | clases | Ver [Excepciones](#excepciones). |

---

## `InSimApp`

La clase que subclaseas para escribir un módulo.

**Atributos de clase** (los defines tú):

| Atributo | Default | Descripción |
|---|---|---|
| `dependencies` | `[]` | (Opcional) lista de nombres de módulos requeridos. Lo autoritativo para el loader es `insim_dependencies` del `insim.json`. |
| `version` | `"0.0.0"` | Se sobreescribe con la `version` del `insim.json`. |
| `description` | `""` | Se sobreescribe con la del `insim.json`. |

**Atributos de instancia** (los da el framework):

| Atributo | Tipo | Descripción |
|---|---|---|
| `self.config` | `dict` | Config efectiva (defaults + overrides del proyecto). Lee con `self.config.get('clave', default)`. |
| `self.name` | `str` | Nombre del módulo. |
| `self.logger` | `Logger` | Logger `InSim.<nombre>`. |
| `self.client` | `InSimClient` | El cliente donde está registrada (`None` hasta registrarse). |
| `self.isi` | `ISP_ISI` | Contribución de flags al ISI (solo `Flags`; el resto viene de la config del cliente). |
| `self.outsim_opts` | `OSO` | Bloques OutSim que el módulo necesita (`OSO.NONE` por defecto). |

**Métodos y hooks:**

| Miembro | Descripción |
|---|---|
| `get_insim(name)` | Devuelve la instancia de una dependencia (o `None`). |
| `set_isi_packet()` | Hook para declarar flags ISI. Llama a `super()` y añade con `self.isi.Flags \|= ...`. |
| `set_outsim()` | Hook para declarar bloques OutSim. Llama a `super()` y añade con `self.outsim_opts \|= ...`. |
| `on_connect()` | Tras conectar y enviar el ISI. Pide estado inicial y registra comandos. |
| `on_disconnect()` | Al perder la conexión (o al parar el cliente). |
| `on_reconnect()` | Tras restablecer la sesión (resetea aquí el estado por-sesión). |
| `on_tick()` | Cada `tick_interval` s. No es un timer de precisión. |
| `on_ISP_<TYPE>(packet)` | Handler de un paquete recibido (p. ej. `on_ISP_MSO`). Corre en el worker de dispatch. |
| `on_OutSimPack(packet)` / `on_OutSimPack2(packet)` / `on_OutGaugePack(packet)` | Handlers de telemetría UDP. |
| `send(packet)` | Envía un paquete ya construido (siempre TCP, thread-safe). |
| `send_ISP_<TYPE>(**campos)` | Construye y envía un paquete por nombre (vía `__getattr__` del mixin). |

Ver el contrato de hilos de estos métodos en [Arquitectura § Contrato de
hilos](arquitectura.md#contrato-de-hilos).

---

## Config

Claves de `DEFAULT_CONFIG` (capa del paquete). El proyecto las sobreescribe vía
`config/settings.py` → `INSIM_CONFIG`; un módulo las lee con `self.config.get(...)`.

**Conexión TCP (InSim):**

| Clave | Default | Descripción |
|---|---|---|
| `tcp_host` | `"127.0.0.1"` | Host de LFS. |
| `tcp_port` | `29999` | Puerto InSim (debe coincidir con `/insim <port>` en LFS). |
| `tcp_buffer` | `4096` | Tamaño del buffer TCP. |

**Paquete de inicialización (ISI):**

| Clave | Default | Descripción |
|---|---|---|
| `insim_name` | `"LFS-InSim"` | `IName` que muestra LFS. |
| `admin_pass` | `""` | Contraseña de admin de LFS (por máquina, nunca versionada). |
| `insim_ver` | `10` | Versión de InSim (v10 para LFS 0.7F+). |
| `prefix` | `"!"` | Prefijo de comandos de chat. |
| `interval` | `10` | Intervalo NLP/MCI en ms (lo envía LFS; **no** es `on_tick`). |
| `insim_udp_port` | `0` | `0` = NLP/MCI por TCP; `!= 0` los redirige a UDP. |

**UDP (OutSim / OutGauge):**

| Clave | Default | Descripción |
|---|---|---|
| `udp_host` | `"0.0.0.0"` | Interfaz de escucha UDP. |
| `udp_port` | `30000` | Puerto UDP local (debe coincidir con `OutSim Port` en `cfg.txt`). El socket solo se abre si algún módulo declara `outsim_opts`. |
| `udp_buffer` | `4096` | Tamaño del buffer UDP. |

**Reconexión** (ver [Arquitectura § Auto-reconexión](arquitectura.md#auto-reconexión)):

| Clave | Default | Descripción |
|---|---|---|
| `reconnect` | `True` | Reconectar automáticamente al perder la conexión. |
| `reconnect_delay` | `1.0` | Espera inicial entre intentos (s). |
| `reconnect_backoff` | `2.0` | Multiplicador de la espera tras cada intento fallido. |
| `reconnect_max_delay` | `30.0` | Tope de la espera (s). |
| `reconnect_max_attempts` | `0` | `0` = reintentar para siempre. |
| `reconnect_stable_time` | `10.0` | Una sesión que muere antes de esto mantiene el backoff escalando (P24). |

**Bucle principal y errores:**

| Clave | Default | Descripción |
|---|---|---|
| `tick_interval` | `0.1` | Segundos entre `on_tick`. Mínimo `0.01`; valor inválido → `InSimConfigurationError`. |
| `handler_errors` | `"log"` | `'log'` aísla y loguea los errores de handlers (producción); `'raise'` es fail-fast (desarrollo). |

---

## Excepciones

Toda la jerarquía cuelga de `InSimError`:

```
InSimError
├── InSimConnectionError      fallo de red/socket o autenticación (.host, .port)
├── InSimConfigurationError   config inválida o parámetros críticos ausentes
├── InSimPacketError          paquete malformado (.packet_type, .packet_size, .data)
├── InSimModuleError          fallo de carga o dependencia de un módulo (.module_name)
├── InSimProtocolError        LFS responde con error de protocolo / se viola la lógica InSim
└── InSimCommandError         comando de chat mal formado (.command_name)
```

Captura `InSimError` para atrapar cualquiera del framework, o la subclase concreta.

---

## `lfs_insim.utils`

```python
from lfs_insim.utils import strip_lfs_colors, CMDManager, PIDController, TextColors as c
```

**Chat y comandos:**

| Nombre | Descripción |
|---|---|
| `separate_message(packet)` | De un `ISP_MSO`, separa `(usuario, contenido)`. |
| `separate_command_args(prefix, packet)` | Devuelve `(comando_sin_prefijo, [args])` o `(None, None)`. |
| `strip_lfs_colors(texto)` | Quita los códigos de color de LFS (`^0`–`^9`, `^L`, `^h`). |
| `TextColors` | Constantes de color para mensajes (`c.RED`, `c.GREEN`, `c.YELLOW`, `c.WHITE`, `c.BLUE`, `c.CYAN`, `c.PURPLE`, `c.BLACK`). |
| `Command` | Define un comando con args tipados. |
| `CMDManager` | Builder fluido de árboles de comandos con espacio de nombres. |

**Control:**

| Nombre | Descripción |
|---|---|
| `PIDController(kp, ki, kd)` | PID con anti-windup y anti-derivative-kick; salida clamped a `[-1.0, 1.0]` (pedal/volante). `update(setpoint, measured, dt)`. |

**Conversión de unidades LFS:**

`lfs_pos_to_meters`, `lfs_speed_to_kmh`, `lfs_angle_to_degrees`,
`lfs_angvel_to_degrees_per_second`.

**Geometría 3D genérica:**

`calc_dist_3d(x1, y1, z1, x2, y2, z2)` — distancia euclídea 3D entre dos puntos.

> **Nota (v0.2.0):** la geometría/navegación **específica de la IA** (rumbos LFS,
> captura dinámica de waypoints, radar longitudinal/lateral: `calc_target_heading`,
> `get_heading_diff`, `calc_deviation_angle`, `calc_dist_point_to_segment_3d`,
> `get_closest_node_index`, `determine_smart_spawn_index`, `apply_antilag_window`,
> `evaluate_dynamic_capture`, `is_target_ahead_and_in_lane`) **ya no forma parte de
> la API pública del framework**: se movió a `ai_control`
> (`nav_modes/freeroam/geometry.py`). En `lfs_insim.utils` solo queda la primitiva
> genérica `calc_dist_3d`.

---

## Paquetes y enums

- **Paquetes**: importa las dataclasses de `lfs_insim.packets` (`ISP_MSL`,
  `ISP_MCI`, `ISP_NCN`, ...). Cada campo lleva `metadata={'fmt': ...}` para la
  serialización. La referencia por paquete está en `docs/tutorial/`.
- **Enums**: todos los flags y constantes del protocolo están en
  `lfs_insim.insim_enums` (`ISF`, `ISP`, `TINY`, `SMALL`, `PTYPE`, `OSO`, ...).

La fuente de verdad del protocolo binario es `docs/InSim.txt`.

---

## Ver también

- [Quickstart](quickstart.md) · [Módulos y dependencias](modulos-y-deps.md) ·
  [Arquitectura](arquitectura.md)
