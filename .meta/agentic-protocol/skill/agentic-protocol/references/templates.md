# Templates for the files you generate

Adapt the headings to the working language; keep the structure. **Keep the file names canonical and
in English** (`INDEX.md`, `STATE.md`, `LOG.md`, `PLAN.md`, `DIAGNOSIS.md`, `PROTOCOL.md`) even when
their content is in another language — future sessions and `close_check.py` depend on them.

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
2. **LOG.md** — last entry, for recent context.
3. **PLAN.md** — the active phase and its checklist.
4. **PROTOCOL.md** — the rules (mandatory). Read when in doubt.
5. **DIAGNOSIS.md** — known problems. On demand.

## The files
| File | What it is | When it is updated |
|---|---|---|
| STATE.md | Handoff between sessions | End of every session and at every milestone |
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

## Validation queue (only the user closes these)
- [ ] ⏳ S<n> — <change> → <what to test, what should happen>
- [x] ✅ S<n> — <change> — validated by the user YYYY-MM-DD

## Constraints right now
<What would trip up the next session: a paused phase, a blocked dependency, a pending decision.>
```

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
