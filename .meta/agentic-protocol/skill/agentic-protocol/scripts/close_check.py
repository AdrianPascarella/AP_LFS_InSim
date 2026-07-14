#!/usr/bin/env python3
"""Close-of-session check for the Agentic Work Protocol.

Verifies what the protocol otherwise only promises:

  1. the working tree is clean,
  2. nothing is left unpushed,
  3. the handoff is under its hard cap (it is the file read on EVERY session),
  4. the handoff actually states a next step,
  5. the handoff points at the user-actions file (so the human can find what they owe),
  6. the handoff was actually touched recently (you did not close without updating it),
  7. the user-actions file exists, its counters match its cards, and no pending card is
     missing its steps or its fields — a card the user cannot act on is not a card.

Run it as the last step of every session close and paste its output.
Exit code 0 = green, 1 = at least one FAIL. Warnings never fail the run.

    python scripts/close_check.py
    python scripts/close_check.py --state ESTADO_ACTUAL.md --actions ACCIONES_USUARIO.md

File names default to the canonical English ones; pass them explicitly if the project
translated them. Stdlib only. Python 3.8+. Works on Windows, macOS and Linux.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# The templates mandate a "▶️ NEXT:" marker line; accept the arrow or common wordings.
NEXT_MARKER = re.compile(
    r"▶|\bNEXT\b|PR[ÓO]XIMO|SIGUIENTE|PROCHAIN|N[ÄA]CHSTE", re.IGNORECASE
)

# A pending action is a card heading ("### U7 — ..."); a closed one is a single "- [x] U7 — ..."
# line. That difference is what lets this script count them without parsing any prose, in any
# language.
CARD = re.compile(r"^###\s+(U\d+)\b(.*)$")
CLOSED = re.compile(r"^\s*-\s*\[[xX]\]\s*(U\d+)\b")
BLOCKING = "🚧"  # marks a card that blocks work
STEP = re.compile(r"^\s*\d+[.)]\s+\S")  # "1. do this"
FIELD = re.compile(r"^\s*\*\*[^*]+:\*\*")  # "**Why:** ...", whatever the language
MIN_FIELDS = (
    3  # why + expected result + one more; below that the card cannot be acted on
)

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
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
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
        report(
            "FAIL", "clean tree", f"{len(dirty)} uncommitted change(s): {shown}{more}"
        )
    else:
        report("PASS", "clean tree")

    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream.returncode != 0:
        report("WARN", "pushed", "branch has no upstream - nothing to compare against")
        return
    ahead = git("rev-list", "--count", "@{u}..HEAD")
    n = ahead.stdout.strip() or "0"
    if n != "0":
        report(
            "FAIL", "pushed", f"{n} commit(s) not pushed to {upstream.stdout.strip()}"
        )
    else:
        report("PASS", "pushed", f"in sync with {upstream.stdout.strip()}")


def parse_actions(path: Path) -> "tuple[list, int, int]":
    """Return ([(id, heading, body_lines), ...], closed_count, count_declared_in_header)."""
    cards: list = []
    closed = 0
    declared = -1
    current = None
    in_header = True

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = CARD.match(line)
        if m:
            in_header = False
            if current:
                cards.append(current)
            current = (m.group(1), line, [])
            continue
        if line.startswith("##"):  # a new section ends the card
            in_header = False
            if current:
                cards.append(current)
                current = None
        if current:
            current[2].append(line)
        elif CLOSED.match(line):
            closed += 1
        elif in_header and declared < 0 and line.startswith(">"):
            # "> **3 pending** - 1 blocking (U7) ..." -> the first number is the count.
            n = re.search(r"\d+", line)
            if n:
                declared = int(n.group())
    if current:
        cards.append(current)
    return cards, closed, declared


def check_actions(actions: Path, max_pending: int) -> int:
    """Check the user-actions file. Returns the number of pending cards."""
    if not actions.is_file():
        report("FAIL", "user actions exist", f"not found at {actions}")
        return 0

    cards, closed, declared = parse_actions(actions)
    pending = len(cards)
    blocking = [cid for cid, head, _ in cards if BLOCKING in head]
    report("PASS", "user actions exist", f"{pending} pending, {closed} closed listed")

    # The header answers "how many things do I owe you?" - it is not allowed to lie.
    if declared < 0:
        if pending:
            report("WARN", "counters match", "the header states no count")
    elif declared != pending:
        report(
            "FAIL",
            "counters match",
            f"the header says {declared} pending but there are {pending} cards",
        )
    else:
        report("PASS", "counters match", f"{pending} pending")

    # A card with no steps, or with barely any fields, is a note - the user cannot act on it.
    incomplete = []
    for cid, _head, body in cards:
        if not any(STEP.match(ln) for ln in body):
            incomplete.append(f"{cid} (no steps)")
        elif sum(1 for ln in body if FIELD.match(ln)) < MIN_FIELDS:
            incomplete.append(f"{cid} (fewer than {MIN_FIELDS} fields)")
    if incomplete:
        report("FAIL", "cards are actionable", ", ".join(incomplete))
    elif pending:
        report(
            "PASS",
            "cards are actionable",
            "every pending card has steps and its fields",
        )

    if blocking:
        report(
            "WARN",
            "blocking cards open",
            f"{', '.join(blocking)} - the user is the bottleneck",
        )
    if pending > max_pending:
        report(
            "WARN",
            "queue length",
            f"{pending} > {max_pending} - recommend a validation round before piling on more",
        )
    return pending


def check_state(state: Path, cap: int, actions_name: str, pending: int) -> None:
    if not state.is_file():
        report("FAIL", "handoff exists", f"not found at {state}")
        return

    text = state.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    if len(lines) > cap:
        report(
            "FAIL",
            "handoff cap",
            f"{len(lines)} lines > {cap} - move the oldest material to the log",
        )
    else:
        report("PASS", "handoff cap", f"{len(lines)}/{cap} lines")

    if NEXT_MARKER.search(text):
        report("PASS", "next step stated")
    else:
        report(
            "WARN",
            "next step stated",
            "no visible 'NEXT' marker - the next session is blind",
        )

    # The handoff POINTS at the actions file; it never copies it (duplicated content diverges).
    if actions_name in text:
        report("PASS", "points at user actions", actions_name)
    elif pending > 0:
        report(
            "FAIL",
            "points at user actions",
            f"{pending} pending action(s) and the handoff never mentions {actions_name}",
        )
    else:
        report(
            "WARN",
            "points at user actions",
            f"the handoff does not mention {actions_name}",
        )

    log = git("log", "-3", "--name-only", "--pretty=format:")
    if log.returncode == 0 and log.stdout:
        touched = {
            ln.strip().replace("\\", "/")
            for ln in log.stdout.splitlines()
            if ln.strip()
        }
        rel = state.as_posix()
        if not any(t.endswith(rel) or rel.endswith(t) for t in touched):
            report(
                "WARN",
                "handoff updated",
                "not modified in the last 3 commits - did you close without updating it?",
            )
        else:
            report("PASS", "handoff updated")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Close-of-session check (Agentic Work Protocol)."
    )
    parser.add_argument("--context-dir", default="docs/dev", help="default: docs/dev")
    parser.add_argument(
        "--state", default="STATE.md", help="handoff file, relative to context-dir"
    )
    parser.add_argument(
        "--actions",
        default="USER_ACTIONS.md",
        help="user-actions file, relative to context-dir",
    )
    parser.add_argument(
        "--cap", type=int, default=120, help="hard line cap for the handoff"
    )
    parser.add_argument(
        "--max-pending",
        type=int,
        default=4,
        help="warn above this many pending actions",
    )
    parser.add_argument("--skip-git", action="store_true")
    args = parser.parse_args()

    print("Close check - Agentic Work Protocol")
    print("-" * 60)

    if not args.skip_git:
        check_git()
    ctx = Path(args.context_dir)
    pending = check_actions(ctx / args.actions, args.max_pending)
    check_state(ctx / args.state, args.cap, args.actions, pending)

    print("-" * 60)
    if failures:
        print(
            f"RESULT: FAIL ({failures} failure(s), {warnings} warning(s)) - fix before closing."
        )
        return 1
    print(f"RESULT: PASS ({warnings} warning(s)) - the session can be closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
