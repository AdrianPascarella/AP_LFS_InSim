# Arquitectura

Cómo está construido el framework por dentro: la cadena de objetos, el ciclo de
vida de un paquete, el modelo de hilos y la reconexión automática. No necesitas
leer esto para escribir un módulo (ve al [quickstart](quickstart.md) para eso),
pero sí para entender por qué las cosas están donde están.

> El **core** (`src/lfs_insim/`) es Python 3.9+ puro, sin dependencias externas.
> Implementa el protocolo binario de **LFS InSim v10** (TCP 29999, UDP 30000).

---

## Visión general: composición, no herencia

El framework es un sistema de plugins componible. La pieza clave es que
**`InSimApp` NO hereda de `InSimClient`**: hay **un cliente y N apps** registradas
en él.

```
CLI (cli.py)
  └── InSimLoader          descubre insim.json, resuelve dependencias,
       │                   registra cada app en UN cliente
       ├── InSimClient     agrega flags ISF/OSO, decodifica y despacha paquetes
       │    └── InSimTransport   posee los sockets TCP/UDP y sus hilos receptores
       │
       └── client.register(app)   ← cada InSimApp se registra (deps primero)
            └── InSimApp(PacketSenderMixin)   clase base de todo módulo
```

El loader crea **un solo `InSimClient`** de forma perezosa (o acepta uno inyectado
con `InSimLoader(client=...)`) y registra en él cada app cargada, **en orden de
dependencias**: una dependencia procesa cada paquete ANTES que sus dependientes.
El cliente fusiona los `isi.Flags` y los `outsim_opts` de todas las apps
registradas antes de enviar el `ISP_ISI`. Tras registrarse, `app.client` apunta
al cliente que la posee.

**No hay "módulo Master" ni "coup d'état".** (Ese era el diseño anterior al
refactor de composición; si lees documentación vieja que lo menciona, está
obsoleta.)

### Los objetos del core

| Objeto | Archivo | Responsabilidad |
|---|---|---|
| `InSimLoader` | `insim_loader.py` | Descubre `insim.json`, resuelve dependencias y versiones, registra las apps en el cliente en orden de dependencias. |
| `InSimClient` | `insim_client.py` | Agrega flags ISF/OSO, decodifica bytes → paquetes, despacha `on_ISP_*`, corre los hooks de ciclo de vida, gestiona keep-alive y reconexión. |
| `InSimTransport` | `insim_transport.py` | Posee los sockets TCP y UDP, los hilos receptores, el evento de stop y el lock de envío — **uno por cliente** (inyectable). |
| `InSimApp` | `insim_app.py` | Clase base de todo módulo. Declara dependencias, contribuye flags ISI/OSO, maneja paquetes y eventos. |
| `PacketSenderMixin` | `packet_sender_mixin.py` | Da a las apps `send(packet)` y los mágicos `send_ISP_*(**campos)`. |

Como el estado (sockets/hilos) vive en el `InSimTransport` de cada cliente,
**varios clientes pueden coexistir en un mismo proceso**. El único estado global
opcional es el "cliente por defecto" (`insim_state.py`), usado solo como fallback
por los helpers del mixin (Command, CMDManager, RouteManager).

---

## Ciclo de vida de un paquete

```
LFS ──bytes──► InSimTransport ──► InSimClient._on_raw_bytes ──► decoders
                (hilos de IO)                                       │
                                                                    ▼
   worker de dispatch ◄──── cola FIFO ◄──── (encolar; keep-alive se contesta ya)
        │
        ▼
   on_ISP_<TYPE>(packet)  →  cliente, luego cada app en orden de dependencias
```

1. El socket recibe bytes crudos. `InSimTransport` (uno por cliente) reensambla
   paquetes completos sobre TCP (o lee frames sobre UDP) y los pasa a
   `InSimClient._on_raw_bytes`.
2. `insim_packet_decoders.py` mapea el byte de cabecera → instancia de dataclass.
   El **hilo de IO** contesta el keep-alive (`TINY.NONE`) en el acto —para que una
   cola ocupada nunca retrase el ping a LFS— y **encola** el paquete. El hilo de IO
   nunca ejecuta handlers.
3. Un **worker de dispatch dedicado** (`InSim_Dispatch_Worker`) saca paquetes de la
   cola (FIFO estricto) y despacha `on_ISP_<TYPE>(packet)` de forma secuencial: al
   cliente primero y luego a cada app en orden de registro (= orden de
   dependencias).

> **Nota:** `Size` en la cabecera del paquete = bytes totales ÷ 4. Los paquetes
> son little-endian; las strings son latin-1 terminadas en null.

### Hooks de ciclo de vida

Además de los handlers `on_ISP_*`, una app puede definir:

| Hook | Cuándo se llama |
|---|---|
| `on_connect()` | Tras conectar y enviar el ISI. Pide aquí el estado inicial (`TINY.NCN`/`TINY.NPL`) y registra comandos. |
| `on_tick()` | Cada `tick_interval` segundos (default 0.1). Ver la nota de abajo. |
| `on_disconnect()` | Al perderse la conexión (o al parar el cliente). |
| `on_reconnect()` | Tras restablecer la sesión. Resetea aquí el estado por-sesión. |

**`on_tick` NO es un timer de precisión** (cadencia sujeta a la granularidad de
`time.sleep`, ~15 ms en Windows) y no hace catch-up tras un stall. El trabajo de
alta frecuencia va en handlers de paquetes (MCI/OutSim), no en `on_tick`.
`INSIM_CONFIG["interval"]` (default 10 ms) controla cada cuánto envía LFS los
NLP/MCI — eso es otra cosa distinta de `on_tick`.

---

## Contrato de hilos

Este es el contrato que debe respetar quien escriba un módulo:

- Los handlers **`on_ISP_*` corren en el worker de dispatch**, uno a uno, en orden
  FIFO estricto. Nunca corren en los hilos de IO. Un handler lento ya no bloquea la
  recepción (ni el keep-alive), pero **retrasa a los paquetes encolados detrás**.
- Los **hooks de ciclo de vida** (`on_connect`/`on_tick`/`on_disconnect`/
  `on_reconnect`) corren en el **hilo principal**. **No hay garantía de orden**
  entre los hooks de ciclo de vida y los handlers de paquetes (son mundos
  distintos).
- **`send()` es thread-safe** desde cualquier hilo.
- Al hacer `stop()`, los paquetes pendientes en la cola se despachan antes de que
  el worker salga (se mete un centinela al final de la cola).

### Política de errores de handlers

La clave de config `handler_errors` decide qué pasa cuando un handler o un hook
lanza una excepción:

- **`'log'`** (default, producción): aísla el error — lo loguea con traceback y el
  dispatch continúa. Un módulo roto no tira abajo a los demás.
- **`'raise'`** (desarrollo): fail-fast. El primer error detiene el cliente y se
  re-lanza fuera de `start()` con el traceback original (los paquetes pendientes se
  descartan).

Excepción deliberada: los errores de `on_disconnect` durante `stop()` se aíslan
**siempre**, para que la secuencia de apagado se complete. Un valor inválido de
`handler_errors` lanza `InSimConfigurationError` al crear el cliente.

---

## Envío de paquetes

Enviar es **siempre TCP**: LFS solo acepta paquetes InSim por TCP. El socket UDP
es solo de bajada (OutSim/OutGauge, y NLP/MCI si se redirigen a UDP).

```python
self.send_ISP_MSL(Msg="hola")      # preferido: mágico vía PacketSenderMixin
self.send(ISP_MSL(Msg="hola"))     # explícito: solo si construyes el paquete aparte
```

Bajo el capó, `client.send(packet)` = `encode_packet()` (serialización pura, en
`insim_packet_sender.py`) + `transport.send(bytes)` (con lock por instancia). El
mixin enruta `send`/`send_ISP_*` a través de `self.client`, cayendo al cliente por
defecto del proceso para las clases helper.

---

## Auto-reconexión

Si LFS tira la conexión TCP, el bucle principal del cliente lo detecta en ≤100 ms,
despacha `on_disconnect()` y reintenta con backoff exponencial (claves `reconnect*`
en la config; `reconnect_max_attempts: 0` = para siempre). Al reconectar:

1. Reenvía el ISI agregado.
2. Despacha `on_reconnect()` (las apps resetean aquí su estado por-sesión).
3. **Luego** re-solicita `TINY.NCN`/`TINY.NPL`, de modo que las respuestas
   reconstruyan los trackers sobre un estado limpio (el orden importa).

Una reconexión es solo **provisional**: LFS puede aceptar el TCP y tirar la
conexión justo después del ISI (p. ej. un admin password que no cuadra). Si la
sesión muere antes de `reconnect_stable_time` (default 10 s), el siguiente ciclo
retoma el backoff escalado en vez de empezar de cero — así un ISI rechazado nunca
se convierte en una tormenta de conexiones. Además, una sesión que muere joven sin
haber recibido un solo byte deja una pista explícita en el log ("ISI likely
rejected — check admin_pass / InSim version"), porque LFS no da feedback en el
socket al rechazar un ISI.

Con `reconnect: False` (o agotados los intentos) el cliente para limpiamente.
Los hooks de ciclo de vida siempre corren en el hilo principal; `on_tick` se pausa
mientras se reconecta.

---

## Config: dos capas

El core trae sus propios defaults (`DEFAULT_CONFIG` en `config.py`) y **nunca lee
archivos del proyecto**. La CLI es la que carga `config/settings.py` del proyecto
(si existe) y la propaga hacia abajo:

```
config/settings.py (INSIM_CONFIG)     ← capa de PROYECTO (la carga la CLI)
        │  ya aplica settings_local.py y variables de entorno
        ▼
InSimLoader(config=...) → cliente perezoso → cada app hereda la config del cliente
        ▲
DEFAULT_CONFIG (config.py)            ← capa del PAQUETE (defaults del core)
```

Los módulos leen ajustes con `self.config.get('clave', default)`. La lista completa
de claves está en la [referencia de la API](api-publica.md#config).

---

## Ver también

- [Quickstart](quickstart.md) — tu primer InSim en 5 minutos.
- [Módulos y dependencias](modulos-y-deps.md) — manifiesto, deps, mixins, comandos.
- [Referencia de la API pública](api-publica.md) — clases, config, utils, excepciones.
- `docs/InSim.txt` — la fuente de verdad del protocolo binario.
