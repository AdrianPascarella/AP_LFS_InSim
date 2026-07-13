#!/usr/bin/env python3
"""Parity check between the two copies of the protocol rules.

The rules live in two places on purpose (two delivery vehicles):

  * AGENTIC_PROTOCOL.md, PART II          -- the portable master, pasted into any agent.
  * skill/.../references/protocol.md      -- the Claude Code skill's copy.

Duplicated content drifts. It already did once: the master kept "Keeping the system
alive" outside the rules while the skill numbered it as a section, so the protocol a
project ended up with had different section numbers depending on which vehicle installed
it. A hand-run comparison caught it. Good intentions are not a system, so this is a
command.

Policy:
  * the section headings must match exactly (order included)  -> otherwise FAIL;
  * a section body MAY differ, but the divergence must be DECLARED in KNOWN_DIFFS below,
    with its reason -> an undeclared difference is a FAIL.

Bodies are normalized before comparing (paragraphs joined, whitespace collapsed), so the
two files can wrap their lines differently without tripping the check.

    python .meta/agentic-protocol/scripts/parity_check.py

Exit 0 = in parity, 1 = drift. Stdlib only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "AGENTIC_PROTOCOL.md"
SKILL = ROOT / "skill" / "agentic-protocol" / "references" / "protocol.md"

# Divergences that are deliberate. Key = section number, value = why.
KNOWN_DIFFS = {
    2: "the master's reading budget also excludes the installer spec itself; the skill's copy "
    "does not carry the installer",
    4: "the skill mandates the exact close_check.py command it ships; the master can only "
    "recommend a close check, since a pasted .md ships no script",
    11: "the master points at the tree/CI state; the skill points at its close check",
    15: "wording of the 'start it empty' note",
}

SECTION = re.compile(r"^## §(\d+)\s*[—-]\s*(.+?)\s*$")


def sections(path: Path) -> "dict[int, tuple[str, str]]":
    """{number: (title, normalized body)} for every '## §n — Title' section."""
    out: "dict[int, tuple[str, str]]" = {}
    current: "int | None" = None
    title = ""
    buf: "list[str]" = []

    def flush() -> None:
        if current is not None:
            body = "\n".join(buf)
            body = re.sub(r"\n(?!\n)", " ", body)  # unwrap hard-wrapped lines
            body = re.sub(r"\s+", " ", body).strip()
            out[current] = (title, body)

    for line in path.read_text(encoding="utf-8").splitlines():
        m = SECTION.match(line)
        if m:
            flush()
            current, title, buf = int(m.group(1)), m.group(2), []
        elif line.startswith("# ") and current is not None:
            flush()  # a new PART ends the rules
            current = None
        elif current is not None and line.strip() != "---":  # separators are not content
            buf.append(line)
    flush()
    return out


def main() -> int:
    failures = 0
    a, b = sections(MASTER), sections(SKILL)
    print("Parity check - protocol rules (master vs skill)")
    print("-" * 62)

    only_master = sorted(set(a) - set(b))
    only_skill = sorted(set(b) - set(a))
    if only_master or only_skill:
        failures += 1
        print(f"[FAIL] section sets differ - master only: {only_master}, skill only: {only_skill}")
    else:
        print(f"[PASS] same sections in both ({len(a)}: {min(a)}..{max(a)})")

    for n in sorted(set(a) & set(b)):
        (ta, ba), (tb, bb) = a[n], b[n]
        if ta != tb:
            failures += 1
            print(f"[FAIL] {n:>2} title differs - master: {ta!r} / skill: {tb!r}")
        elif ba == bb:
            pass  # identical, nothing to say
        elif n in KNOWN_DIFFS:
            print(f"[ OK ] {n:>2} body differs, declared - {KNOWN_DIFFS[n]}")
        else:
            failures += 1
            print(f"[FAIL] {n:>2} body differs and it is NOT declared - {ta}")
            print("       declare it in KNOWN_DIFFS with its reason, or make the two agree")

    print("-" * 62)
    if failures:
        print(f"RESULT: DRIFT ({failures}) - the two copies have separated.")
        return 1
    print("RESULT: IN PARITY - every divergence is declared.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
