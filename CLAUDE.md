# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ Contexto de trabajo persistente — LEER PRIMERO

**IMPORTANTE:** Este proyecto usa un sistema de contexto que vive en archivos, no en la
sesión de chat, y se **sincroniza por GitHub** para poder continuar desde otro dispositivo.

**Al iniciar CUALQUIER sesión, antes de tocar nada:**
1. Sitúate en la rama de refactor y sincroniza: `git checkout refactor/estabilizacion` y `git pull`
   (puede haber cambios subidos desde otro dispositivo).
2. Lee `docs/dev/` en este orden:
   1. `docs/dev/ESTADO_ACTUAL.md` — dónde se quedó el trabajo y cuál es el próximo paso. **Empieza aquí.**
   2. `docs/dev/HISTORIAL.md` — última entrada (contexto reciente).
   3. `docs/dev/PLAN.md` — fase activa y su checklist.
   4. `docs/dev/MODUS_OPERANDI.md` — reglas de trabajo de obligado cumplimiento.
   5. `docs/dev/DIAGNOSTICO.md` — problemas conocidos (consultar según haga falta).

Punto de entrada e índice: `docs/dev/00_INDEX.md`.

**Al terminar la sesión o alcanzar un hito:** actualiza `ESTADO_ACTUAL.md`, añade una entrada
a `HISTORIAL.md`, marca lo completado en `PLAN.md`, y **haz commit + `git push`** para
sincronizar (no dejes trabajo local sin subir). Protocolo completo en `MODUS_OPERANDI.md`.

## Commands

```bash
# Install (editable mode, includes dev deps for testing)
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_utils.py

# Run a specific test
pytest tests/test_utils.py::TestPIDController::test_zero_dt_returns_zero -v

# Run an InSim by name
lfs-insim run ai_control

# List available InSims
lfs-insim list

# Show metadata for an InSim
lfs-insim info <name>

# Create a new InSim scaffold
lfs-insim init <name>

# Install git hooks (auto-generates .pyi stubs on commit)
bash scripts/install-git-hooks.sh   # Linux/Mac
./scripts/install-git-hooks.ps1     # Windows

# Regenerate type stubs manually
python src/lfs_insim/generate_stubs.py
```

No linter/formatter is configured. The core (`src/lfs_insim/`) has no external dependencies — pure Python 3.9+ stdlib. The `ai_control` InSim additionally requires `matplotlib` (declared in its `insim.json` and in the `[dev]` extra).

## Architecture

The framework is a composable plugin system for the **LFS InSim v10 binary protocol** (TCP 29999, UDP 30000).

### Core chain

```
CLI (cli.py)
  → InSimLoader        — discovers insim.json, resolves dependencies, registers apps into ONE client
    → InSimClient      — aggregates ISF flags/OSO opts, decodes and dispatches packets
      → InSimTransport — owns the TCP/UDP sockets and receiver threads (one per client, injectable)
      ← client.register(app)  — attaches each InSimApp (dependencies first)
    → InSimApp(PacketSenderMixin)  — base class every module inherits; declares deps, handles events
```

**Composition (P11, Fase 2)**: `InSimApp` does NOT inherit from `InSimClient`. The loader
lazily creates a single `InSimClient` (or accepts one injected via `InSimLoader(client=...)`)
and registers every loaded app into it in dependency order — a dependency processes each
packet BEFORE its dependents. The client merges `isi.Flags` and `outsim_opts` from every
registered app before sending `ISP_ISI`. `app.client` holds the owning client after
registration. There is no "Master" module and no coup d'état anymore.

**Dependency resolution**: declared in `insim.json` as `"insim_dependencies": {"module_name": ">=1.0.0"}`. Access at runtime via `self.get_insim("module_name")`.

### insim.json manifest schema

```json
{
  "name": "my_module",
  "version": "1.0.0",
  "description": "...",
  "author": "...",
  "entry_point": "app.py",
  "insim_dependencies": {
    "users_management": ">=1.0.0"
  },
  "python_dependencies": []
}
```

The loader reads `entry_point` (not `entry`) to find the file, then looks for a class whose name matches the module's name in CamelCase (e.g. `ai_control` → `AiControl`). Version constraints in `insim_dependencies` are enforced (`InSimModuleError` if unsatisfied), and a dependency that fails to load aborts the dependent's load (fail-fast, P20).

### Packet lifecycle

1. Socket receives raw bytes → `insim_transport.py` (`InSimTransport`, one per client) buffers/assembles full packets (TCP) or reads frames (UDP) and hands them to `InSimClient._on_raw_bytes`
2. `insim_packet_decoders.py` maps header byte → dataclass instance; the IO thread answers keep-alive pings immediately and enqueues the packet (it never runs handlers)
3. The client's dedicated dispatch worker thread takes packets from the queue (FIFO) and dispatches `on_ISP_<TYPE>(packet)` sequentially to the client, then each registered app in registration (= dependency) order
4. Lifecycle hooks: `on_connect()`, `on_tick()` (fixed ~100 ms main-loop cadence, independent of `interval`), `on_disconnect()`, `on_reconnect()`. `INSIM_CONFIG["interval"]` (default 10 ms) controls how often LFS sends NLP/MCI, not `on_tick`.

**Auto-reconnection (P12)**: if LFS drops the TCP connection, the client's main loop detects it (≤100 ms), dispatches `on_disconnect()` and retries with exponential backoff (`reconnect*` keys in `DEFAULT_CONFIG`; `reconnect_max_attempts: 0` = forever). On success it resends the ISI, dispatches `on_reconnect()` (apps reset their per-session state here) and THEN re-requests `TINY.NCN`/`TINY.NPL`, so the replies rebuild trackers on a clean slate (order matters — P22). A reconnect is only **provisional** (P24): LFS may accept TCP and drop the connection right after the ISI (e.g. admin password mismatch) — if the session dies within `reconnect_stable_time` (default 10 s) the next cycle resumes the escalating backoff instead of starting fresh, so a rejected ISI never becomes a connection storm. A session that dies young without having received a single packet logs an explicit hint ("ISI likely rejected — check admin_pass / InSim version"), since LFS gives no feedback on the socket when rejecting an ISI. With `reconnect: False` (or attempts exhausted) the client stops cleanly instead. Lifecycle hooks always run on the main thread; `on_tick` pauses while reconnecting.

**Threading contract (P2)**: `on_ISP_*` handlers run on the client's dispatch worker thread, one packet at a time in strict FIFO order — never on the IO threads. A slow handler no longer blocks reception (or the keep-alive), but it delays the packets queued behind it. Lifecycle hooks (`on_connect`/`on_tick`/`on_disconnect`/`on_reconnect`) run on the main thread; there is no cross-thread ordering guarantee between lifecycle hooks and packet handlers. `send()` is thread-safe from any thread. On `stop()`, pending queued packets are dispatched before the worker exits.

### Sending packets

```python
self.send_ISP_MSL(Msg="hello")           # preferred: magic via PacketSenderMixin.__getattr__
self.send(ISP_MSL(Msg="hello"))          # explicit: only when building the packet separately
```

Sending is thread-safe: `client.send(packet)` = `encode_packet()` (pure serialization in `insim_packet_sender.py`) + `transport.send(bytes)` (per-instance lock). Sending is **always TCP** — LFS only accepts InSim packets over TCP; the UDP socket is receive-only (OutSim/OutGauge, NLP/MCI). Mixin `send`/`send_ISP_*` route through `self.client`, falling back to the process's default client for helper classes.

### Writing a module

```python
class MyInSim(InSimApp):
    dependencies = ["users_management>=1.0.0"]

    def on_connect(self):
        self.um = self.get_insim("users_management")

    def set_isi_packet(self):
        super().set_isi_packet()
        self.isi.Flags |= ISF.LOCAL   # add needed flags

    def on_ISP_MSO(self, packet: ISP_MSO):
        # chat message received
        pass
```

For complex modules, use mixin composition (as done in `ai_control`): split concerns into `_CommandsMixin`, `_PhysicsMixin`, etc., each in its own file, and combine them in the main class via MRO — `InSimApp` appears last so mixins get `self.send_*` via inheritance:

```python
class AIControl(_CommandsMixin, _PhysicsMixin, _NavigationMixin, _TrafficMixin, InSimApp):
    pass
```

### Commands (in-game)

```python
from lfs_insim.utils import separate_command_args, Command

# Define a command with typed args
cmd = Command(".myCmd", args=[("speed", int)], help="Set speed")

def on_ISP_MSO(self, packet):
    prefix, args = separate_command_args(".myCmd", packet)
    if prefix:
        # validate UCID before acting
        if packet.UCID not in self.cmds_white_list:
            return
```

Use `strip_lfs_colors(text)` from `utils.py` to remove LFS color codes (`^0`–`^9`, `^L`, `^h`) from message strings. For sending colored messages, use constants from `TextColors` (e.g. `TextColors.RED`, `TextColors.YELLOW`).

`CMDManager` provides a fluent builder for namespaced command trees:

```python
cmds = CMDManager(self.cmd_prefix, self.cmd_base)
(cmds
 .add_cmd("start", "Start the AI", None, self._cmd_start)
 .add_cmd("speed", "Set speed", (("kmh", int),), self._cmd_speed)
 .add_cmd("msg",   "Send message", "text", self._cmd_msg, is_mso_required=True)
)
self.cmds = cmds.submit()   # prints usage hint in LFS chat

# In on_ISP_MSO:
cmd, args = separate_command_args(self.cmd_prefix, packet)
if cmd == self.cmd_base:
    self.cmds.handle_commands(packet, args)
```

`is_mso_required=True` passes the raw `ISP_MSO` packet as the first argument to the handler; `False` (default) passes only the typed args. Typing `!base <cmd> ?` in-game shows per-command help.

To suppress noisy send-logs for a specific packet type: `mute_send_logs('ISP_AIC')` (call at module level, from `lfs_insim import mute_send_logs`).

## Key conventions

- **Binary protocol**: LFS packets are little-endian, strings are latin-1 null-terminated. `Size` in packet header = total bytes / 4.
- **Packet definitions**: dataclasses in `src/lfs_insim/packets/insim.py`; sub-structures in `packets/structures.py`; OutSim/OutGauge in `packets/outsim.py`. Each field carries `metadata={'fmt': '...'}` for struct serialization. Import packet classes from `lfs_insim.packets` and enums from `lfs_insim.insim_enums` — `insim_packet_class.py` is a **deprecated** facade (emits `DeprecationWarning`) that re-exports both, kept only for old code.
- **Public API (P15)**: every module defines `__all__`; recommended import points are `lfs_insim` (core classes, config, exceptions), `lfs_insim.packets`, `lfs_insim.insim_enums` and `lfs_insim.utils`. `lfs_insim.packets` does NOT re-export enums (`from lfs_insim.packets import *` brings packets only).
- **Enums**: all protocol flags and constants live in `src/lfs_insim/insim_enums.py` (ISF, ISP, TINY, SMALL, PTYPE, OSO, etc.).
- **Global state**: none mandatory since P13 — sockets/threads live in each client's `InSimTransport`, so several clients can coexist in one process. `insim_state.py` only keeps the optional "default client" (first one created), used as fallback by `PacketSenderMixin` helper classes.
- **Config**: package defaults live in `src/lfs_insim/config.py` (`DEFAULT_CONFIG` + `build_config(overrides)`); the core never reads project files (P14). The **CLI** loads `config/settings.py` (`INSIM_CONFIG`, which already applies `settings_local.py` and env vars) from the CWD when present and passes it down: `InSimLoader(config=...)` → lazy client → each app inherits the client's effective config. Modules read settings via `self.config.get('key', default)`.
- **Type stubs**: `.pyi` files under `src/lfs_insim/` are auto-generated for IDE autocomplete only — do not edit manually.
- **PID control**: `PIDController` in `utils.py` has anti-windup and anti-derivative-kick; output is clamped to [-1.0, 1.0] for pedal/steering use.
- **Exceptions**: raise from the hierarchy in `exceptions.py` — `InSimError` → `InSimConnectionError`, `InSimPacketError`, `InSimModuleError`, `InSimConfigurationError`, `InSimCommandError`.
- **Requesting initial state**: send `ISP_TINY(SubT=TINY.NCN)` to request all connections and `ISP_TINY(SubT=TINY.NPL)` to request all players during `on_connect()`.
- **Module-specific state on foreign objects**: attach extra state to `users_management` objects via `ai.extra['my_module_key'] = MyDataclass()`. Check existence with `'key' in ai.extra` before accessing.

## Existing InSims

| Module | Path | Purpose |
|---|---|---|
| `users_management` | `insims/users_management/` | Tracks users/players/AIs in real time (UCIDs, PLIDs, telemetry) |
| `ai_control` | `insims/ai_control/` | Controls AI cars via PID; two nav modes: RouteMode (recorded waypoints) and FreeroamMode (street graph FSM) |
| `test_insim` | `insims/test_insim/` | Minimal reference InSim: own user/player tracking, CMDManager example, all handler categories covered — use as a starting template |

### ai_control nav system

`AIBehavior` (in `behavior.py`) is the per-AI state object stored in `ai.extra['aic']`. Its `active_mode` field holds the current `AINavModeState` subclass:

- **`RouteMode`** (`nav_modes/route/`) — follows a list of recorded waypoints; managed by `RouteManager`
- **`FreeroamMode`** (`nav_modes/freeroam/`) — topology-based FSM; state machine drives AI through a road graph of `RoadLink` / `LateralLink` / `Road` nodes; overtake FSM tracked in `overtake_state`

The road graph lives in `nav_modes/freeroam/graph.py`. `RoadLink` connects two roads; `LateralLink` connects two parallel lanes (used for lane changes and overtakes).
