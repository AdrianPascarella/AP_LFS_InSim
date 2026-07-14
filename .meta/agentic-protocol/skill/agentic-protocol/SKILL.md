---
name: agentic-protocol
description: Install the Agentic Work Protocol in a project — a file-based context system (STATE / USER_ACTIONS / LOG / PLAN / DIAGNOSIS / PROTOCOL) that survives across sessions, machines and models, plus a declared blind spot, a queue of the things only the human can test, do or decide, and a safety-net policy for fragile code. Use it when the user asks to install/set up the agentic protocol, to make sessions resume where the last one stopped, to stop re-explaining the project every session, or to set up a session handoff / context system. Runs an interview, audits the repo, and writes every file itself.
---

# Agentic Work Protocol — installer

You are installing a context system into this project. **You write everything.** The user never
edits any of the generated files; they answer questions in chat and read the results.

The full portable specification lives next to this file:

- `references/protocol.md` — the rules (Part II). You will instantiate this into the project.
- `references/templates.md` — what each generated file looks like.
- `scripts/close_check.py` — a close-of-session checker you copy into the project.

Read `references/protocol.md` **before** the interview: its rules tell you what the questions are
for. Read `references/templates.md` when you are about to write the files, not before.

---

## The ownership contract

1. **You are the sole writer of the context files.** The user never edits them and must never be
   asked to.
2. Their only inputs are conversational: answers, verdicts on what you cannot verify, corrections.
   You turn those into files.
3. **The files must stay readable by a human who did not write them** — their language, plain prose,
   no private shorthand. They read them to audit where you are taking the project. Do not compress
   them into telegrams for your own benefit.
4. If you ever find hand edits, treat them as truth and reconcile. Never silently overwrite.

---

## Step 1 — Language, first and alone

Ask one question, before anything else:

> *In which language should I work with you? I will talk to you, write the commit messages and
> write all the project documentation in that language.*

Everything from here on happens in that language. Ask separately whether the **code**
(identifiers, comments, docstrings) should use a different language; propose whatever the codebase
already does.

## Step 2 — Audit the repo before asking anything else

Never ask what you can find out. Derive as much of the configuration as you can:

- **Stack and layout**: languages, manifest, entry points, where the source lives.
- **How it is verified**: test runner and how to invoke it, lint/format commands, CI, any smoke or
  end-to-end command.
- **Git reality**: current branch, remotes, default/protected branch, commit convention (read the
  last ~30 subjects), signs that more than one machine pushes.
- **Fragility**: files that concentrate the fixes (churn in `git log`), oversized files, warning
  comments ("HACK", "PATCH", "do not touch").
- **Hand-made data**: anything that could not be regenerated from code — recorded datasets,
  fixtures, maps, calibrations.
- **Existing context**: `docs/dev`, `ADR/`, `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, a long
  `README`. Read them. **They are the previous state of the world and they beat your assumptions.**

## Step 3 — Announce the install mode

- **FRESH** — nothing exists; you create the whole system.
- **ADOPT** — an ad-hoc context system already exists. **Do not throw it away.** Migrate its content
  into the structure, preserving history and any stable IDs already in use. Report what you moved
  and what you dropped, and why.
- **UPGRADE** — the protocol is already installed and you are re-running. Reconcile, refresh the
  configuration, report the diff.

## Step 4 — The interview

Ask only what the audit could not settle. In the user's language, in plain words — **never by
showing them a config schema**. Always propose the answer you inferred so they only confirm or
correct it. When you offer options, **mark the recommended one and say why**. Group related
questions; do not interrogate one field at a time.

Two questions you **must not skip** — the user never volunteers them, and they are what make the
rest of the system work:

> **The blind spot.** *"What part of 'this works' can I not check from here? For example: how the
> car feels to drive in the game, how the interface looks on a real phone, whether it behaves
> correctly against production data. Whatever you name, I will never mark it done on my own — I will
> hand it to you with instructions on what to test."*

> **What must never be lost.** *"Is there anything here that was made by hand and could not be
> rebuilt from the code — recorded data, fixtures, maps, calibrations? I will protect it before any
> git operation that could destroy it."*

Also settle: the work branch and the protected one; whether work syncs across several machines;
what you may do **without asking** (typically commit + push on the work branch) and what **always
needs permission** (the protected branch, deleting, anything destructive or outward-facing); and any
known trap of this machine or toolchain that has already broken something.

## Step 5 — Write the system

In the context directory (default `docs/dev`, unless the project already has a convention). **Keep
the file names canonical and in English even when the content is in another language** — tooling and
future sessions depend on them:

| File | Content |
|---|---|
| `INDEX.md` | Reading order, the user's start sentence (Step 7), one line per file. |
| `STATE.md` | Where we are, the next concrete step, a pointer to `USER_ACTIONS.md`. **Hard cap ~120 lines.** |
| `USER_ACTIONS.md` | Everything you will need the user for — one card per action, stable ID `U<n>`, with steps, expected result and what blocks (§7). Seed it with the blind-spot validations you already owe them; leave it empty (heading + counters at zero) if there are none yet. |
| `LOG.md` | Append-only journal. First entry: this install. |
| `PLAN.md` | A first phase drafted from your audit, with acceptance criteria. |
| `DIAGNOSIS.md` | The problems found in the audit — stable ID `P<n>`, severity, evidence citing real files, proposed action. This is the audit's deliverable: be concrete. |
| `PROTOCOL.md` | `references/protocol.md`, instantiated. It opens with a **Configuration** section stating the resolved values in prose: languages, branches, verify/lint/smoke commands, the blind spot, what must never be lost, what is pre-authorized, known traps. |

Copy `scripts/close_check.py` into the project (`scripts/close_check.py`, or wherever the project
keeps its scripts) and reference it from `PROTOCOL.md` §4 as the last step of every session close.
If you renamed the context files into the working language (only do that if the project already had
that convention), pass the names with `--state` / `--actions` and write the exact command into
`PROTOCOL.md`, so the check keeps working.

**If the project has no way to verify itself** — no tests, no runnable check — that *is* the headline
finding. Record it as `P1` and make "establish a verification command" the first phase of `PLAN.md`.
Say it plainly: until there is a command that can fail, the safety-net rules are unenforceable and
every change is an assertion, not a result.

**Do not touch the code during the install.** Documentation only.

## Step 6 — Hook the start protocol into the session

This is what makes the system self-starting. Without it, the next session has no idea any of this
exists.

Find the file this environment auto-loads every session — `CLAUDE.md` (Claude Code), `AGENTS.md`
(Codex and others), `.cursorrules` or `AGENTS.md` (Cursor), `GEMINI.md` (Gemini CLI). Prefer
whatever already exists in the repo. **If it exists, merge into it — never clobber it.** Write a
short section at the **top**, in the user's language:

> **Persistent working context — READ FIRST.** This project keeps its context in files, not in the
> chat session. **At the start of ANY session, before touching anything:** switch to the work
> branch, pull, and read `<context_dir>/STATE.md` (where the work stopped and what the next step
> is), then the last entry of `LOG.md` and the active phase of `PLAN.md`. The full rules are in
> `<context_dir>/PROTOCOL.md` and are mandatory. **At the end of the session or at a milestone:**
> update `STATE.md`, append to `LOG.md`, tick off `PLAN.md`, run the close check, commit and push.

If this environment has **no** auto-loaded file, say so plainly. The system still works, but the
user's start sentence must then carry the pointer itself. Never fake it: an auto-load mechanism that
does not exist is a protocol that silently stops running.

## Step 7 — Report, and hand over the sentences

Close the install by telling the user, without jargon:

1. What now exists and what each file is for.
2. **Their start sentence, verbatim and in their language.** Exactly one:
   - with a hook installed → *"Start the session following your protocol."*
   - with no auto-loaded file → *"Read `<context_dir>/INDEX.md` and start the session following the
     protocol you find there."*

   Write it as well at the top of `INDEX.md` so it can never be lost.
3. **Their close sentence** (*"Close the session following the protocol"*) — and that you will also
   close on your own at any milestone, without being asked.
4. **What you will ask of them from now on**: whatever needs their hands or their judgement — always
   written as a card in `USER_ACTIONS.md`, never left in the chat. Point at the file, and tell them
   that at the start of every session you will say how many are pending and which one blocks, and
   that you will **stop and ask** before working on something an open card blocks (§7).
5. **What they never have to do**: edit any of these files. Ever. If something is wrong, they tell
   you and you fix it.
6. The first real step you recommend, and why.
