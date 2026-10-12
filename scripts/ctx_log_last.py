#!/usr/bin/env python3
"""Print only the most recent session entry from an append-only LOG.md.

LOG.md grows without bound by design (Agentic Work Protocol, §2): one entry per session, newest
entry at the top. A session that reads the whole file to get "the last entry" burns its context
window on history it will not use, and that cost grows forever as the log grows. This prints exactly
the first "## S<n>" block and nothing else.

    python scripts/ctx_log_last.py
    python scripts/ctx_log_last.py --log docs/dev/LOG.md

Exit code 0 on success. Exit code 1 if no "## S<n>" heading was found — in that case the whole file
is printed anyway (nothing is hidden), so the caller is never left with less information, only a
warning that the fast path did not apply. Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HEADING = re.compile(r"^##\s+S(\d+)\b")


def main() -> int:
    # The content printed here is the document's own prose (accents, arrows, emoji markers) - force
    # UTF-8 output regardless of the console's default codepage instead of mangling it to ASCII,
    # since unlike a script's own status messages, this text carries meaning that must survive intact.
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log", default="docs/dev/LOG.md", help="path to LOG.md (default: docs/dev/LOG.md)"
    )
    args = parser.parse_args()

    path = Path(args.log)
    if not path.is_file():
        print(f"error: {path} not found", file=sys.stderr)
        return 1

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    starts = [i for i, ln in enumerate(lines) if HEADING.match(ln)]

    if not starts:
        print(
            f"warning: no '## S<n>' heading found in {path}; printing the whole file",
            file=sys.stderr,
        )
        print("\n".join(lines))
        return 1

    start = starts[0]
    end = starts[1] if len(starts) > 1 else len(lines)
    print("\n".join(lines[start:end]).rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
