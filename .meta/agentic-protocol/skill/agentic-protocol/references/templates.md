# Templates for the files you generate

Adapt the headings to the working language; keep the structure. **Keep the file names canonical and
in English** (`INDEX.md`, `STATE.md`, `USER_ACTIONS.md`, `LOG.md`, `PLAN.md`, `DIAGNOSIS.md`,
`PROTOCOL.md`) even when their content is in another language — future sessions and `close_check.py`
depend on them.

### `INDEX.md`

```markdown
# 🧭 Context system — <project>

> The context does not live in the chat session. It lives here. Every session **starts by reading
> these files** and **ends by updating them**, so a new session picks up exactly where the last one
> stopped without the user having to repeat anything.

## 🚀 Start sentence (say this at the beginning of every session)

> **<the exact sentence, in the user's language — the short one if a hook is installed, the
> self-contained one otherwise>**

To close: **"<the close sentence>"** — the agent must also close on its own at any milestone.

## Reading order
1. **STATE.md** — where we stopped and what the next step is. Always start here.
2. **USER_ACTIONS.md** — what is waiting on you: what to test, do, decide or provide.
3. **LOG.md** — last entry, for recent context.
4. **PLAN.md** — the active phase and its checklist.
5. **PROTOCOL.md** — the rules (mandatory). Read when in doubt.
6. **DIAGNOSIS.md** — known problems. On demand.

## The files
| File | What it is | When it is updated |
|---|---|---|
| STATE.md | Handoff between sessions | End of every session and at every milestone |
| USER_ACTIONS.md | What needs your hands or your judgement | When the agent needs you, and when you give a verdict |
| LOG.md | Append-only journal | End of every session |
| PLAN.md | Phases, checklists, acceptance criteria | When tasks complete or plans change |
| DIAGNOSIS.md | Known problems, stable IDs | When something new is found |
| PROTOCOL.md | The working rules | When the rules change |

> These files are written by the agent, never by hand. If something in them is wrong, tell the agent
> and it will fix it.
```

### `STATE.md`

```markdown
# 📍 State — <project>
> Updated: YYYY-MM-DD (S<n>) — <2–4 lines: what just happened; is the tree clean and pushed>
> **▶️ NEXT: <the one concrete next step>**

## Where we are
<Active phase and its status. What was left half-done and exactly where it stopped.
Max ~40 lines. Older narrative belongs in LOG.md.>

## What is waiting on you
<A pointer, never a copy — the cards live in USER_ACTIONS.md (§7).>
**<N> pending actions** (<M> blocking: <U7>) → see `USER_ACTIONS.md`. Start with **U7**.

## Constraints right now
<What would trip up the next session: a paused phase, a blocked dependency, a pending decision.>
```

### `USER_ACTIONS.md`

The file that answers, at a glance, *"how many things do I owe you, and which one is holding
everything up?"*. One card per action; the header carries the counters. `close_check.py` verifies
that the counters match the cards and that no pending card is missing its steps or its expected
result — so the template is not decoration, it is checked.

```markdown
# 🙋 Your actions — <project>
> **<N> pending** · <M> blocking (**U7**) · recommended order: U7 → U3 → U5 · updated S<n>
>
> Everything here needs your hands or your judgement: the agent cannot do it, or cannot verify it.
> **You never edit this file** — tell the agent the outcome and it will close the card.

## ⏳ Pending

### U7 — <title>          🚧 · blocks: <phase 8.4> · opened in S<n>
**Type:** validate | do | decide | provide          **Time:** ~<n> min
**Why:** <what depends on this — what stays unverified or blocked until it is done>
**Steps:**
  1. <concrete and copy-pasteable; commands as commands, not as prose>
  2. <...>
**Expected result:** <what happens if it works>
**Failure signs:** <what it looks like when it does not>
**If it fails, tell me:** <what the agent needs to hear to act: the dials, the file, the symptom>

### U3 — <title>          ⏳ · blocks: nothing · opened in S<n>
<...>

## ✅ Closed (recent — the full record is in LOG.md)
<Capped: ~15 lines. What overflows is dropped; it is already in the log.>
- [x] U2 — <title> — YYYY-MM-DD (S<n>): <the user's verdict, in their own words>
```

Rules that make it work (§7): a field you do not know is **declared** (*"Expected result: I do not
know; tell me what you observe"*), never omitted. A pending card is a `### U<n>` heading; a closed
one is a single `- [x]` line — that is what lets the check count them.

### `LOG.md`

```markdown
# 📓 Log — <project>
<!-- Append-only, newest first. One entry per session. -->

## S<n> — YYYY-MM-DD — <headline>
**Done:** <what changed>
**Diagnosis:** <root cause; the hypotheses you refuted and how>
**Decisions:** <decision → why → what was rejected and why>
**Verification:** <real output of the verify command; what is pending validation>
**Commits:** <hashes>
```

### `PLAN.md`

```markdown
# 🗺️ Plan — <project>
> Phases with acceptance criteria. `[x]` = done. `P<n>` refers to DIAGNOSIS.md.

## Phase <n> — <name>   ⏳ ACTIVE
**Goal:** <one line>
- [ ] <task> (**P<n>**)
- [x] <task> — done in S<n>: <what was actually done>
**Acceptance criteria:** <how we know the phase is finished>

## Ideas (parked, not committed to)
- <idea> — <why not now>
```

### `DIAGNOSIS.md`

```markdown
# 🩺 Diagnosis — <project>
> Initial scan: YYYY-MM-DD. Updated whenever something new is found.

## Verdict
<2–4 lines: what is healthy, where the debt is concentrated.>

## ✅ Healthy (do not touch without a reason)
- <...>

## 🔴 High severity
### P1 — <title>   [OPEN | ✅ RESOLVED (S<n>)]
- **Evidence:** <files, measurements, churn>
- **Impact:** <what it breaks or blocks>
- **Action:** <proposed fix, in which phase>
- **Resolved (S<n>):** <how, and what proved it>
```
