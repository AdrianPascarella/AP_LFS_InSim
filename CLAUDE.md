# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable mode, no external deps required)
pip install -e .

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

No test suite exists. No linter/formatter is configured. No external dependencies — pure Python 3.9+ stdlib.

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
  "entry": "app.py",
  "class": "MyClass",
  "insim_dependencies": {
    "users_management": ">=1.0.0"
  }
}
```

### Packet lifecycle

1. Socket receives raw bytes → `insim_packet_io.py` buffers/assembles full packets (TCP) or reads frames (UDP)
2. `insim_packet_decoders.py` maps header byte → dataclass instance
3. Client dispatches `on_ISP_<TYPE>(packet)` sequentially to itself, then each module
4. Lifecycle hooks: `on_connect()`, `on_tick()` (every 0.1 s), `on_disconnect()`

`on_ISP_*` handlers are called from the IO receiver thread — avoid blocking; heavy work should be deferred.

### Sending packets

```python
self.send(ISP_MSL(Msg="hello"))          # explicit
self.send_ISP_MSL(Msg="hello")           # magic via PacketSenderMixin.__getattr__
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

For complex modules, use mixin composition (as done in `ai_control`): split concerns into `_CommandsMixin`, `_PhysicsMixin`, etc., each in its own file, and combine in the main `app.py` class.

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

Use `strip_lfs_colors(text)` from `utils.py` to remove LFS color codes (`^0`–`^9`, `^L`, `^h`) from message strings.

## Key conventions

- **Binary protocol**: LFS packets are little-endian, strings are latin-1 null-terminated. `Size` in packet header = total bytes / 4.
- **Packet definitions**: dataclasses in `src/lfs_insim/packets/insim.py`; sub-structures in `packets/structures.py`; OutSim/OutGauge in `packets/outsim.py`.
- **Enums**: all protocol flags and constants live in `src/lfs_insim/insim_enums.py` (ISF, ISP, TINY, PTYPE, OSO, etc.).
- **Global state**: sockets and master reference are singletons in `src/lfs_insim/insim_state.py` — do not instantiate these directly.
- **Config**: `config/settings.py` holds `INSIM_CONFIG` (TCP host/port, prefix, interval) and `OUT_CONFIG` (OutSim options); modules read settings via `self.config.get('key', default)`.
- **Type stubs**: `.pyi` files under `src/lfs_insim/` are auto-generated for IDE autocomplete only — do not edit manually.
- **PID control**: `PIDController` in `utils.py` has anti-windup and anti-derivative-kick; output is clamped to [-1.0, 1.0] for pedal/steering use.

## Existing InSims

| Module | Path | Purpose |
|---|---|---|
| `users_management` | `insims/users_management/` | Tracks users/players/AIs in real time (UCIDs, PLIDs, telemetry) |
| `ai_control` | `insims/ai_control/` | Controls AI cars via PID; two nav modes: RouteMode (recorded waypoints) and FreeroamMode (street graph FSM) |
