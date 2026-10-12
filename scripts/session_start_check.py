#!/usr/bin/env python3
"""Session-START check for the Agentic Work Protocol - close_check.py's counterpart at the other
end of a session.

Consolidates the mechanical half of PROTOCOL.md's Session START section into one command instead of
four or five separate git/gh calls run and re-read by hand every session: commit identity, the
active branch, the active `gh` account, a pull that never runs over a dirty tree, a short reality
cross-check, and whether the installed protocol template has moved on since this project last
absorbed it.

None of this replaces judgment. It replaces re-typing the same commands and re-parsing their raw
output every single session - the report is deliberately verbose about *why* something failed, not
just that it did, so nothing a human would have caught by eyeballing raw git output gets hidden
behind a bare PASS/FAIL.

    python scripts/session_start_check.py --git-identity "Name <email>" --branch main
    python scripts/session_start_check.py --git-identity "..." --gh-account Veloik-adrian
    python scripts/session_start_check.py --git-identity "..." --no-pull

This script never fixes anything by itself, even a mismatch the protocol pre-authorizes fixing
without asking (a wrong git identity, a wrong `gh` account) - it only reports. Applying a
pre-authorized fix is a deliberate act with its own git command; a script silently rewriting repo
config as a side effect of a "check" is the wrong shape of tool for that.

Exit code 0 = green, 1 = at least one FAIL. Warnings and info lines never fail the run.
Stdlib only. Python 3.8+. Works on Windows, macOS and Linux.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

VERSION_RE = re.compile(r"protocol-template-version:\s*(\d+)")

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
    print(line)


def git(*args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def check_branch(expected: str) -> None:
    res = git("branch", "--show-current")
    actual = res.stdout.strip()
    if actual == expected:
        report("PASS", "branch", actual)
    else:
        report("WARN", "branch", f"on '{actual or '(detached HEAD)'}', expected '{expected}'")


def check_identity(expected: str) -> None:
    res = git("log", "-1", "--format=%an <%ae>")
    if res.returncode != 0:
        report("SKIP", "git identity", "no commits yet in this repo")
        return
    actual = res.stdout.strip()
    if actual == expected:
        report("PASS", "git identity", actual)
    else:
        report(
            "FAIL",
            "git identity",
            f"expected '{expected}', got '{actual}' - fix repo-local git config (never --global) "
            "before doing anything else",
        )


def gh_active_account() -> "str | None":
    proc = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    combined = proc.stdout + proc.stderr
    candidate = None
    for line in combined.splitlines():
        m = re.search(r"[Ll]ogged in to \S+ account (\S+)", line)
        if m:
            candidate = m.group(1)
            continue
        m2 = re.search(r"Active account:\s*(true|false)", line)
        if m2 and candidate:
            if m2.group(1) == "true":
                return candidate
            candidate = None
    return None


def check_gh_account(expected: str) -> None:
    try:
        active = gh_active_account()
    except FileNotFoundError:
        report("SKIP", "gh account", "'gh' is not installed on this machine")
        return
    if active is None:
        report("WARN", "gh account", "could not parse an active account from 'gh auth status'")
    elif active == expected:
        report("PASS", "gh account", active)
    else:
        report(
            "FAIL",
            "gh account",
            f"active account is '{active}', expected '{expected}' - "
            f"gh auth switch --hostname <host> --user {expected}",
        )


def check_pull(do_pull: bool) -> None:
    status = git("status", "--porcelain")
    dirty = [ln for ln in status.stdout.splitlines() if ln.strip()]
    if dirty:
        shown = ", ".join(ln[3:] for ln in dirty[:5])
        more = f" (+{len(dirty) - 5} more)" if len(dirty) > 5 else ""
        report(
            "WARN",
            "pull",
            f"skipped - {len(dirty)} uncommitted change(s) present: {shown}{more} "
            "- commit, stash or back up first",
        )
        return
    if not do_pull:
        report("SKIP", "pull", "--no-pull")
        return

    res = git("pull")
    out = res.stdout + res.stderr
    low = out.lower()
    if res.returncode != 0:
        if re.search(r"could not resolve host|network|timed out|could not read from remote", low):
            report("WARN", "pull", "network issue - could not reach the remote")
        elif "conflict" in low or "diverged" in low or "not something we can merge" in low:
            report(
                "FAIL",
                "pull",
                "merge conflict or diverged history - resolve by hand, never force",
            )
        else:
            last = out.strip().splitlines()[-1] if out.strip() else "git pull failed"
            report("FAIL", "pull", last)
    elif "already up to date" in low:
        report("PASS", "pull", "already up to date")
    else:
        report("PASS", "pull", "pulled new changes")


def check_reality() -> None:
    log = git("log", "--oneline", "-5")
    commits = log.stdout.strip()
    report("INFO", "recent commits", commits.replace("\n", " | ") if commits else "(no commits)")


def read_version(path: Path) -> "int | None":
    if not path.is_file():
        return None
    m = VERSION_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    return int(m.group(1)) if m else None


def check_protocol_version(project_file: Path, skill_file: Path) -> None:
    skill_version = read_version(skill_file)
    if skill_version is None:
        report("SKIP", "protocol template version", f"{skill_file} not found on this machine")
        return
    project_version = read_version(project_file)
    if project_version is None:
        report(
            "WARN",
            "protocol template version",
            f"{project_file} has no version marker - it predates the versioning mechanism",
        )
        return
    if project_version < skill_version:
        report(
            "WARN",
            "protocol template version",
            f"installed template is v{skill_version}, this project absorbed v{project_version} "
            "- offer to run the skill's UPGRADE mode",
        )
    elif project_version > skill_version:
        report(
            "WARN",
            "protocol template version",
            f"project claims v{project_version}, newer than the installed template's "
            f"v{skill_version} - check the skill install on this machine",
        )
    else:
        report("PASS", "protocol template version", f"v{project_version}, up to date")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Session-START check (Agentic Work Protocol)."
    )
    parser.add_argument(
        "--git-identity",
        required=True,
        help="expected 'Name <email>' commit identity for this repo",
    )
    parser.add_argument("--branch", default="main", help="expected work branch (default: main)")
    parser.add_argument(
        "--gh-account", default=None, help="expected active 'gh' account, if pushed via gh"
    )
    parser.add_argument(
        "--protocol-file",
        default="docs/dev/PROTOCOL.md",
        help="this project's instantiated PROTOCOL.md (default: docs/dev/PROTOCOL.md)",
    )
    parser.add_argument(
        "--skill-template",
        default=str(Path.home() / ".claude" / "skills" / "agentic-protocol" / "references" / "protocol.md"),
        help="the installed skill's protocol.md, used for the version check",
    )
    parser.add_argument(
        "--no-pull", action="store_true", help="skip 'git pull' even over a clean tree"
    )
    args = parser.parse_args()

    # Detail strings can carry real repo content (commit subjects, identities) in any language -
    # force UTF-8 output regardless of the console's default codepage instead of mangling it.
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("Session start check - Agentic Work Protocol")
    print("-" * 60)

    check_branch(args.branch)
    check_identity(args.git_identity)
    if args.gh_account:
        check_gh_account(args.gh_account)
    check_pull(do_pull=not args.no_pull)
    check_reality()
    check_protocol_version(Path(args.protocol_file), Path(args.skill_template))

    print("-" * 60)
    if failures:
        print(f"RESULT: FAIL ({failures} failure(s), {warnings} warning(s)) - fix before continuing.")
        return 1
    print(f"RESULT: PASS ({warnings} warning(s)) - continue with the session.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
