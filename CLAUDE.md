# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

No linter/formatter is configured. No external dependencies — pure Python 3.9+ stdlib.

## Architecture

The framework is a composable plugin system for the **LFS InSim v10 binary protocol** (TCP 29999, UDP 30000).

### Core chain

```
CLI (cli.py)
  → InSimLoader        — discovers insim.json, resolves dependencies, chains modules
    → InSimApp         — base class every module inherits; declares dependencies, handles events
      → InSimClient    — master orchestrator; manages sockets, aggregates ISF flags, dispatches packets
        → PacketSenderMixin  — provides send_ISP_*() magic methods via __getattr__
```

**InSimLoader "coup d'état" pattern**: the last-loaded module becomes Master. All previously loaded modules are pushed into its `modules[]` list. The Master merges `isi.Flags` from every module before sending `ISP_ISI`.

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

The loader reads `entry_point` (not `entry`) to find the file, then looks for a class whose name matches the module's name in CamelCase (e.g. `ai_control` → `AiControl`). Version constraints in `insim_dependencies` are recorded but not yet enforced.

### Packet lifecycle

1. Socket receives raw bytes → `insim_packet_io.py` buffers/assembles full packets (TCP) or reads frames (UDP)
2. `insim_packet_decoders.py` maps header byte → dataclass instance
3. Client dispatches `on_ISP_<TYPE>(packet)` sequentially to itself, then each module
4. Lifecycle hooks: `on_connect()`, `on_tick()` (every `INSIM_CONFIG["interval"]` ms, default 100 ms), `on_disconnect()`

`on_ISP_*` handlers are called from the IO receiver thread — avoid blocking; heavy work should be deferred.

### Sending packets

```python
self.send_ISP_MSL(Msg="hello")           # preferred: magic via PacketSenderMixin.__getattr__
self.send(ISP_MSL(Msg="hello"))          # explicit: only when building the packet separately
```

`send_packet()` is thread-safe (uses a lock internally).

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
- **Packet definitions**: dataclasses in `src/lfs_insim/packets/insim.py`; sub-structures in `packets/structures.py`; OutSim/OutGauge in `packets/outsim.py`. Each field carries `metadata={'fmt': '...'}` for struct serialization. `insim_packet_class.py` is a compatibility facade — always import from `lfs_insim.packets` or `lfs_insim.insim_packet_class` (they are equivalent).
- **Enums**: all protocol flags and constants live in `src/lfs_insim/insim_enums.py` (ISF, ISP, TINY, SMALL, PTYPE, OSO, etc.).
- **Global state**: sockets and master reference are singletons in `src/lfs_insim/insim_state.py` — only the first setter wins; do not instantiate these directly.
- **Config**: `config/settings.py` holds `INSIM_CONFIG` (TCP host/port, prefix, interval) and `OUT_CONFIG` (OutSim options); modules read settings via `self.config.get('key', default)`.
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
