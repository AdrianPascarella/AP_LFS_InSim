#!/usr/bin/env python3
"""Close-of-session check for the Agentic Work Protocol.

Verifies what the protocol otherwise only promises:

  1. the working tree is clean,
  2. nothing is left unpushed,
  3. STATE.md is under its hard cap (it is the file read on EVERY session),
  4. STATE.md actually states a next step,
  5. STATE.md carries a validation queue (the blind spot has an owner),
  6. STATE.md was actually touched recently (you did not close without updating the handoff).

Run it as the last step of every session close and paste its output.
Exit code 0 = green, 1 = at least one FAIL. Warnings never fail the run.

    python scripts/close_check.py --context-dir docs/dev

Stdlib only. Python 3.8+. Works on Windows, macOS and Linux.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

CHECKBOX = re.compile(r"^\s*-\s*\[[ xX]\]")
# The templates mandate a "▶️ NEXT:" marker line; accept the arrow or common wordings.
NEXT_MARKER = re.compile(r"▶|\bNEXT\b|PR[ÓO]XIMO|SIGUIENTE|PROCHAIN|N[ÄA]CHSTE", re.IGNORECASE)

failures = 0
warnings = 0


def report(status: str, name: str, detail: str = "") -> None:
    global failures, warnings
    if status == "FAIL":
        failures += 1
    elif status == "WARN":
        warnings += 1
    line = f"[{status:4}] {name}"
    if detail:
        line += f" - {detail}"
    # ASCII only: the Windows console mangles non-ASCII output under legacy code pages.
    print(line.encode("ascii", "replace").decode("ascii"))


def git(*args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def check_git() -> None:
    if git("rev-parse", "--git-dir").returncode != 0:
        report("SKIP", "git", "not a git repository")
        return

    status = git("status", "--porcelain")
    dirty = [ln for ln in status.stdout.splitlines() if ln.strip()]
    if dirty:
        shown = ", ".join(ln[3:] for ln in dirty[:5])
        more = f" (+{len(dirty) - 5} more)" if len(dirty) > 5 else ""
        report("FAIL", "clean tree", f"{len(dirty)} uncommitted change(s): {shown}{more}")
    else:
        report("PASS", "clean tree")

    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream.returncode != 0:
        report("WARN", "pushed", "branch has no upstream — nothing to compare against")
        return
    ahead = git("rev-list", "--count", "@{u}..HEAD")
    n = ahead.stdout.strip() or "0"
    if n != "0":
        report("FAIL", "pushed", f"{n} commit(s) not pushed to {upstream.stdout.strip()}")
    else:
        report("PASS", "pushed", f"in sync with {upstream.stdout.strip()}")


def check_state(state: Path, cap: int) -> None:
    if not state.is_file():
        report("FAIL", "STATE.md exists", f"not found at {state}")
        return

    text = state.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    if len(lines) > cap:
        report(
            "FAIL",
            "STATE.md cap",
            f"{len(lines)} lines > {cap} - move the oldest material to LOG.md",
        )
    else:
        report("PASS", "STATE.md cap", f"{len(lines)}/{cap} lines")

    if NEXT_MARKER.search(text):
        report("PASS", "next step stated")
    else:
        report("WARN", "next step stated", "no visible 'NEXT' marker - the next session is blind")

    if any(CHECKBOX.match(ln) for ln in lines):
        report("PASS", "validation queue present")
    else:
        report(
            "WARN",
            "validation queue present",
            "no checklist items - is nothing pending the user's verdict?",
        )

    log = git("log", "-3", "--name-only", "--pretty=format:")
    if log.returncode == 0 and log.stdout:
        touched = {ln.strip().replace("\\", "/") for ln in log.stdout.splitlines() if ln.strip()}
        rel = state.as_posix()
        if not any(t.endswith(rel) or rel.endswith(t) for t in touched):
            report(
                "WARN",
                "STATE.md updated",
                "not modified in the last 3 commits - did you close without updating the handoff?",
            )
        else:
            report("PASS", "STATE.md updated")


def main() -> int:
    parser = argparse.ArgumentParser(description="Close-of-session check (Agentic Work Protocol).")
    parser.add_argument("--context-dir", default="docs/dev", help="default: docs/dev")
    parser.add_argument("--state", default="STATE.md", help="handoff file, relative to context-dir")
    parser.add_argument("--cap", type=int, default=120, help="hard line cap for STATE.md")
    parser.add_argument("--skip-git", action="store_true")
    args = parser.parse_args()

    print("Close check - Agentic Work Protocol")
    print("-" * 60)

    if not args.skip_git:
        check_git()
    check_state(Path(args.context_dir) / args.state, args.cap)

    print("-" * 60)
    if failures:
        print(f"RESULT: FAIL ({failures} failure(s), {warnings} warning(s)) - fix before closing.")
        return 1
    print(f"RESULT: PASS ({warnings} warning(s)) - the session can be closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
