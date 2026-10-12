#!/usr/bin/env python3
"""Print only the active phase(s) from an unbounded PLAN.md.

PLAN.md grows without bound by design (Agentic Work Protocol, §2): one section per phase, and only
the active phase is read on session start. Phases are chronological (oldest first), so unlike
LOG.md's "newest on top" there is no positional shortcut — this finds the active phase by its
template-mandated marker instead: a "## W<n> ... <marker> ACTIVE" heading. The marker word itself
may be translated ("ACTIVA", "ACTIU", ...); what stays constant across every language a project
writes its docs in is the hourglass emoji next to it, so that is what this matches on.

    python scripts/ctx_plan_active.py
    python scripts/ctx_plan_active.py --plan docs/dev/PLAN.md

Prints every phase heading that carries the "in progress" marker (normally exactly one; zero or
several are both reported, never silently guessed at). Exit code 0 if at least one was found and
printed. Exit code 1 if none were found — in that case the whole file is printed anyway (nothing is
hidden), so the caller is never left with less information, only a warning that the fast path did
not apply. Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PHASE_HEADING = re.compile(r"^##\s+\S*\d+\b.*$")
ACTIVE_MARKER = "⏳"  # hourglass, not sand-timer: the exact emoji templates.md mandates
ANY_HEADING = re.compile(r"^##\s+\S")


def main() -> int:
    # The content printed here is the document's own prose (accents, emoji markers) - force UTF-8
    # output regardless of the console's default codepage instead of mangling it to ASCII, since
    # unlike a script's own status messages, this text carries meaning that must survive intact.
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan", default="docs/dev/PLAN.md", help="path to PLAN.md (default: docs/dev/PLAN.md)"
    )
    args = parser.parse_args()

    path = Path(args.plan)
    if not path.is_file():
        print(f"error: {path} not found", file=sys.stderr)
        return 1

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    phase_starts = [i for i, ln in enumerate(lines) if PHASE_HEADING.match(ln)]
    active_starts = [i for i in phase_starts if ACTIVE_MARKER in lines[i]]

    if not active_starts:
        print(
            f"warning: no phase heading with the '{ACTIVE_MARKER}' active marker found in {path}; "
            "printing the whole file",
            file=sys.stderr,
        )
        print("\n".join(lines))
        return 1

    all_heading_starts = sorted(
        set(phase_starts) | {i for i, ln in enumerate(lines) if ANY_HEADING.match(ln)}
    )

    blocks = []
    for start in active_starts:
        later = [i for i in all_heading_starts if i > start]
        end = later[0] if later else len(lines)
        blocks.append("\n".join(lines[start:end]).rstrip())

    print("\n\n".join(blocks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
