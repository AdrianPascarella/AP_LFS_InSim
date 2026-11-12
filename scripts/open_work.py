#!/usr/bin/env python3
"""The part of close_check.py that looks for what a session left open: processes and subagents.

Lives next to close_check.py, which imports it; a project copies both.

**Processes.** The session is the nearest ancestor of this process that is the Claude Code program
itself. What it started is what hangs below it in the process tree (Windows: Win32_Process through
PowerShell; elsewhere: ``ps``). That alone leaves out the person's other sessions (they hang from
their own terminals) and everything else on the machine. Below the session, these do not count, and
what is exempted by name is listed in the output:

  - the tool call running this check (the branch of the tree it hangs from);
  - a stdio MCP server declared in ``~/.claude.json``, the project's ``.mcp.json`` or an installed
    plugin, when it is a direct child of the session, is not a shell, and carries the declared
    command and arguments: Claude Code starts those by itself, while a tool call always goes through
    a shell, so the same server started by hand is still a leftover;
  - whatever ``--ignore`` names (a PID or a piece of the command line);
  - whatever is gone a second later (the harness runs its own short-lived git and ripgrep).

A process whose shell has already exited has lost its parent, so it no longer hangs from the session
and this check cannot see it (nothing on the system says who started it).

**Subagents.** An agent is finished when its own transcript ends in an ``end_turn``, or when the
session's transcript has a ``<task-notification>`` for it no older than its last record (stopped,
killed and failed agents only leave that). Checked in S24 against 296 real transcripts: the five open
were exactly the five running. From inside a subagent, that subagent counts as open and nothing tells
it which one it is. ``--delegated`` is for that case, a subagent closing the session for an orchestrator:
one open agent is taken to be the one running the check, and the output says it assumed so; two are a
failure. ``--ignore <agent id>`` still names one by its id when it is known.

Transcript format, session registry (``sessions/<pid>.json``) and ``CLAUDE_CODE_SESSION_ID`` are what
Claude Code does today, not a documented contract: unreadable means a WARN saying the check did not
run, never a PASS.

Stdlib only. Python 3.8+. Works on Windows, macOS and Linux.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROCESS_CHECK = "no processes left open"
AGENT_CHECK = "no agents left open"

WINDOWS_LISTING = [
    "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
    "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-CimInstance Win32_Process | ForEach-Object { "
    "[pscustomobject]@{pid=$_.ProcessId; ppid=$_.ParentProcessId; name=$_.Name; "
    "started=$(if ($_.CreationDate) { $_.CreationDate.ToFileTimeUtc() } else { 0 }); cmd=$_.CommandLine} "
    "} | ConvertTo-Json -Compress",
]
UNIX_LISTING = ["ps", "-axww", "-o", "pid=,ppid=,args="]
LISTING_TIMEOUT = 60
SETTLE_SECONDS = 1.0
MAX_COMMAND = 160
SHELLS = {"sh", "bash", "zsh", "dash", "fish", "cmd", "powershell", "pwsh"}
TOKEN = re.compile(r'"[^"]*"|\S+')
PS_LINE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(.*)$")
TASK_ID = re.compile(r"<task-id>([^<]+)</task-id>")
NOTIFICATION = "<task-notification>"


class TreeUnreadable(Exception):
    """The process list could not be read or understood."""


@dataclass(frozen=True)
class Proc:
    pid: int
    ppid: int
    name: str
    cmd: str
    started: int = 0  # 0 = unknown; only Windows gives it, and only Windows needs it


def run_listing(argv: "list[str]") -> str:
    try:
        result = subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace", timeout=LISTING_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as error:
        raise TreeUnreadable(f"{argv[0]}: {error}") from error
    if result.returncode != 0:
        raise TreeUnreadable(f"{argv[0]} exited with {result.returncode}: {result.stderr.strip()[:120]}")
    return result.stdout


def _stem(path: str) -> str:
    base = path.strip().strip('"').replace("\\", "/").rsplit("/", 1)[-1].lower()
    return base[:-4] if base.endswith((".exe", ".cmd", ".bat")) else base


def parse_windows(text: str) -> "list[Proc]":
    try:
        rows = json.loads(text.lstrip("﻿"))
        rows = [rows] if isinstance(rows, dict) else rows
        return [
            Proc(int(r["pid"]), int(r["ppid"]), r.get("name") or "", r.get("cmd") or "", int(r.get("started") or 0))
            for r in rows
        ]
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise TreeUnreadable(f"cannot parse the process list: {error}") from error


def parse_ps(text: str) -> "list[Proc]":
    procs = []
    for line in text.splitlines():
        match = PS_LINE.match(line)
        if match:
            cmd = match.group(3).strip()
            first = TOKEN.match(cmd)
            procs.append(Proc(int(match.group(1)), int(match.group(2)), _stem(first.group()) if first else "", cmd))
    return procs


def list_processes(runner, platform: str) -> "list[Proc]":
    windows = platform.startswith("win")
    try:
        output = runner(WINDOWS_LISTING if windows else UNIX_LISTING)
    except OSError as error:
        raise TreeUnreadable(str(error)) from error
    return parse_windows(output) if windows else parse_ps(output)


def is_claude(proc: Proc) -> bool:
    """The program itself, not a shell whose text mentions it."""
    tokens = TOKEN.findall(proc.cmd) or [""]
    if "claude" in (_stem(proc.name), _stem(tokens[0])):
        return True
    return _stem(tokens[0]) in {"node", "bun"} and "@anthropic-ai/claude-code" in " ".join(tokens[1:2]).replace("\\", "/")


def _is_parent(parent: Proc, child: Proc) -> bool:
    """Windows reuses a dead process's PID and keeps it as its children's parent: a parent younger
    than its child is someone else."""
    return not (parent.started and child.started and parent.started > child.started)


def _session_of(procs: "list[Proc]", me: int) -> "tuple[Proc | None, int]":
    """(the Claude Code process above ``me``, the branch below it that holds ``me``)."""
    by_pid = {p.pid: p for p in procs}
    current = by_pid[me]
    seen = {me}
    while current.ppid in by_pid and current.ppid not in seen:
        parent = by_pid[current.ppid]
        if not _is_parent(parent, current):
            break
        if is_claude(parent):
            return parent, current.pid
        seen.add(parent.pid)
        current = parent
    return None, me


def _children(procs: "list[Proc]") -> dict:
    by_pid = {p.pid: p for p in procs}
    children: dict = {}
    for proc in procs:
        parent = by_pid.get(proc.ppid)
        if parent is not None and proc.pid != proc.ppid and _is_parent(parent, proc):
            children.setdefault(proc.ppid, []).append(proc)
    return children


def _normal(text: str) -> str:
    return text.replace("\\", "/").replace('"', "").replace("'", "").lower()


def _servers_in(data: object, plugin_root: str = "") -> "list[tuple[str, list[str]]]":
    """(server name, the words its command line must carry) for each stdio server of a config."""
    if not isinstance(data, dict):
        return []
    found = []
    for name, server in (data["mcpServers"] if isinstance(data.get("mcpServers"), dict) else data).items():
        if not isinstance(server, dict) or not isinstance(server.get("command"), str):
            continue
        args = [str(a) for a in server.get("args") or []]
        words = [_stem(server["command"])] + [a.replace("${CLAUDE_PLUGIN_ROOT}", plugin_root) for a in args]
        found.append((str(name), [_normal(w) for w in words if w and "${" not in w]))
    return found


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def mcp_servers(config: Path, cwd: Path) -> "list[tuple[str, list[str]]]":
    """Every stdio MCP server Claude Code may have started by itself. A missing or unreadable file
    only means fewer exemptions: the server then shows up, named, as a leftover."""
    found = []
    for path in (config / ".claude.json", config.parent / ".claude.json"):
        data = _read_json(path)
        if isinstance(data, dict):
            found += _servers_in({"mcpServers": data.get("mcpServers") or {}})
            for project in (data.get("projects") or {}).values():
                if isinstance(project, dict):
                    found += _servers_in({"mcpServers": project.get("mcpServers") or {}})
    found += _servers_in(_read_json(cwd / ".mcp.json"))
    installed = _read_json(config / "plugins" / "installed_plugins.json")
    plugins = installed.get("plugins") if isinstance(installed, dict) else None
    for entries in (plugins.values() if isinstance(plugins, dict) else []):
        for entry in entries if isinstance(entries, list) else []:
            root = entry.get("installPath") if isinstance(entry, dict) else None
            if isinstance(root, str):
                found += _servers_in(_read_json(Path(root) / ".mcp.json"), root)
                manifest = _read_json(Path(root) / ".claude-plugin" / "plugin.json")
                found += _servers_in({"mcpServers": manifest.get("mcpServers")} if isinstance(manifest, dict) else {}, root)
    return found


def _mcp_name(proc: Proc, servers: "list[tuple[str, list[str]]]") -> "str | None":
    command = _stem(proc.name) or _stem(proc.cmd)
    text = _normal(proc.cmd)
    for name, words in servers:
        if words and (command not in SHELLS or command == words[0]) and all(w in text for w in words):
            return name
    return None


def _ignored(proc: Proc, ignore) -> bool:
    cmd = proc.cmd.lower()
    return any(t == str(proc.pid) or (t and not t.isdigit() and t.lower() in cmd) for t in ignore)


def _describe(proc: Proc) -> str:
    cmd = " ".join((proc.cmd or proc.name).split())
    return f"PID {proc.pid} ({cmd[:MAX_COMMAND]}{'...' if len(cmd) > MAX_COMMAND else ''})"


def inspect(procs: "list[Proc]", session: Proc, branch: int, servers, ignore) -> "tuple[list[Proc], list[str]]":
    """(what the session left running, what is exempted and why)."""
    children = _children(procs)
    left: "list[Proc]" = []
    exempted: "list[str]" = []
    stack = list(children.get(session.pid, []))
    direct = {p.pid for p in stack}
    while stack:
        proc = stack.pop()
        if proc.pid == branch:
            continue
        server = _mcp_name(proc, servers) if proc.pid in direct else None
        if server:
            exempted.append(f"MCP server {server}: {_describe(proc)}")
            continue
        if _ignored(proc, ignore):
            exempted.append(f"--ignore: {_describe(proc)}")
            continue
        left.append(proc)
        stack.extend(children.get(proc.pid, []))
    flagged = {p.pid for p in left}
    # A console host is part of its parent, not something anyone can act on separately.
    left = [p for p in left if not (_stem(p.name) == "conhost" and p.ppid in flagged)]
    return sorted(left, key=lambda p: p.pid), sorted(exempted)


def default_config(environ: "dict | None" = None) -> Path:
    environ = os.environ if environ is None else environ
    override = environ.get("CLAUDE_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".claude"


def find_transcript(config: Path, session_pid: int, environ) -> "Path | None":
    registry = _read_json(config / "sessions" / f"{session_pid}.json")
    for session_id in (registry.get("sessionId") if isinstance(registry, dict) else None, environ.get("CLAUDE_CODE_SESSION_ID")):
        if session_id:
            found = sorted((config / "projects").glob(f"*/{session_id}.jsonl"))
            if found:
                return found[0]
    return None


def _records(path: Path):
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                yield record


def _notifications(transcript: Path) -> dict:
    """{agent id: time of its latest task notification}."""
    latest: dict = {}
    for record in _records(transcript):
        message = record.get("message")
        text = record.get("content") if record.get("type") == "queue-operation" else None
        if text is None and record.get("type") == "user" and isinstance(message, dict):
            text = message.get("content")
        if isinstance(text, str) and text.lstrip().startswith(NOTIFICATION):
            match = TASK_ID.search(text)
            if match:
                stamp = str(record.get("timestamp") or "")
                latest[match.group(1)] = max(latest.get(match.group(1), ""), stamp)
    return latest


def open_agents(transcript: Path) -> "list[tuple[str, str]]":
    """(agent id, description) of every subagent of the session that has not finished."""
    folder = transcript.with_suffix("") / "subagents"
    if not folder.is_dir():
        return []
    notes = _notifications(transcript)
    result = []
    for path in sorted(folder.glob("agent-*.jsonl")):
        agent = path.stem[len("agent-"):]
        last: dict = {}
        for record in _records(path):
            if record.get("type") in ("assistant", "user"):
                last = record
        message = last.get("message") if isinstance(last.get("message"), dict) else {}
        if last.get("type") == "assistant" and message.get("stop_reason") == "end_turn":
            continue
        if agent in notes and notes[agent] >= str(last.get("timestamp") or ""):
            continue
        meta = _read_json(path.with_name(f"agent-{agent}.meta.json"))
        result.append((agent, str(meta.get("description") or "") if isinstance(meta, dict) else ""))
    return result


def check_agents(report, config: Path, session_pid: int, environ, ignore, delegated=False) -> None:
    transcript = find_transcript(config, session_pid, environ)
    if transcript is None:
        report("WARN", AGENT_CHECK, "did not run: this session's transcript was not found")
        return
    try:
        agents = open_agents(transcript)
    except OSError as error:
        report("WARN", AGENT_CHECK, f"did not run: {error}")
        return
    agents = [a for a in agents if a[0] not in ignore]
    if not agents:
        report("PASS", AGENT_CHECK)
        return
    if delegated and len(agents) == 1:
        report("PASS", AGENT_CHECK, f"{agents[0][0]} assumed to be the subagent running this check (--delegated)")
        return
    lines = "".join(f"\n         {agent} {description}".rstrip() for agent, description in agents)
    report("FAIL", AGENT_CHECK, f"{len(agents)} subagent(s) of this session not finished; stop them:{lines}")


def check(report, cwd: Path, ignore=(), runner=None, pid=None, environ=None, config=None, sleep=None, platform=None, delegated=False) -> None:
    """Report on what this session left open, through close_check's ``report(status, name, detail)``."""
    runner = run_listing if runner is None else runner
    pid = os.getpid() if pid is None else pid
    environ = os.environ if environ is None else environ
    config = default_config(environ) if config is None else config
    sleep = time.sleep if sleep is None else sleep
    platform = sys.platform if platform is None else platform

    def did_not_run(reason: str) -> None:
        report("WARN", PROCESS_CHECK, f"did not run: {reason}")
        report("WARN", AGENT_CHECK, "did not run: the session could not be identified")

    try:
        procs = list_processes(runner, platform)
    except TreeUnreadable as error:
        return did_not_run(str(error))
    if pid not in {p.pid for p in procs}:
        return did_not_run("this process is not in the process list")
    session, branch = _session_of(procs, pid)
    if session is None:
        if environ.get("CLAUDECODE"):
            return did_not_run("Claude Code was not found among this process's ancestors")
        for name in (PROCESS_CHECK, AGENT_CHECK):
            report("SKIP", name, "not inside a Claude Code session: nothing was checked")
        return None

    servers = mcp_servers(config, cwd)
    left, exempted = inspect(procs, session, branch, servers, ignore)
    if left:
        sleep(SETTLE_SECONDS)
        try:
            again, exempted = inspect(list_processes(runner, platform), session, branch, servers, ignore)
        except TreeUnreadable as error:
            report("WARN", PROCESS_CHECK, f"did not run: the second reading failed: {error}")
            check_agents(report, config, session.pid, environ, ignore, delegated)
            return None
        before = {(p.pid, p.cmd) for p in left}
        left = [p for p in again if (p.pid, p.cmd) in before]
    note = f"session PID {session.pid}"
    if exempted:
        note += "; exempted: " + "; ".join(exempted)
    if left:
        lines = "".join(f"\n         {_describe(p)}" for p in left)
        report("FAIL", PROCESS_CHECK, f"{len(left)} still running, stop them:{lines}\n         {note}")
    else:
        report("PASS", PROCESS_CHECK, note)
    check_agents(report, config, session.pid, environ, ignore, delegated)
    return None
