# The protocol (instantiate this into `<context_dir>/PROTOCOL.md`)

Write it in `{{working_language}}`, resolving every `{{placeholder}}` from the interview. **Keep the
"why" attached to each rule**: a rule whose purpose you know is a rule you will not rationalize your
way around.

Open the generated file with a **Configuration** section, in prose, stating: the language of the
chat/docs and the language of the code; the work branch and the protected one; whether work syncs
across machines; the verify / lint / smoke commands; **the blind spot**; **what must never be lost**;
what is pre-authorized and what needs permission; and the known traps of this machine. Everything
below refers to those values.

---

## §0 — Prime directive

Context lives in files, not in the chat session. Never assume you will remember anything from one
session to the next. If it matters, it goes into `{{context_dir}}`.
*Why: without this you restart from zero every session and the user re-explains the project forever.
Files in git also outlive the model, the tool and the machine.*

## §1 — You own the files

You are their only writer. Keep them readable by a human who did not write them: their language,
prose, no private shorthand. The human reads them to audit you; they never edit them.
*Why: a single writer removes format drift, duplicate IDs and contradictory versions of the same
fact — and readable files are the user's only way to see where you are taking the project.*

## §2 — The context files

| File | What it is | Size |
|---|---|---|
| `STATE.md` | The handoff: where we are, **the next step**, a pointer to the pending user actions | **Hard cap ~120 lines.** |
| `USER_ACTIONS.md` | Everything that needs the human: what they must test, do, decide or provide | Pending cards + a capped list of closed ones. |
| `LOG.md` | Append-only journal, one entry per session | Unbounded. Only the last entry is read on start. |
| `PLAN.md` | Phased plan with checklists and acceptance criteria | Unbounded. Only the active phase is read on start. |
| `DIAGNOSIS.md` | Known problems, each with a stable ID and its status | Reference. Read on demand. |
| `PROTOCOL.md` | These rules | Read when in doubt. |
| `INDEX.md` | Entry point | Tiny. |

**The cap on `STATE.md` is a rule.** When it overflows, the oldest material moves to `LOG.md`.
Keep only: current state, the pointer to the pending user actions, the next concrete step, and what
was left half-done.
*Why: `STATE.md` is the one file read on **every** session, so its size is a recurring tax. Left
unchecked it silently becomes a second journal and buries the next step under months of narrative.*

**Stable IDs.** Problems are `P<n>` (`DIAGNOSIS.md`), workstreams `W<n>` (`PLAN.md`), sessions
`S<n>` (`LOG.md`), actions owed by the human `U<n>` (`USER_ACTIONS.md`). An ID never changes
meaning. A solved problem keeps its ID and gains `RESOLVED (S<n>): <how>` — it is never deleted.
**You assign the session number yourself at close: the last one in `LOG.md` plus one.** Never reuse
or renumber an ID.
*Why: without stable IDs every document re-explains the same thing in different words, and the
versions drift apart.*

**Reading budget — what you read at the start of a session, and what you do not.**

| Read in full | Read partially | Do NOT read on start |
|---|---|---|
| `STATE.md` (it is capped for exactly this reason) · `USER_ACTIONS.md` (small by construction) · this file | the **last entry** of `LOG.md` · the **active phase** of `PLAN.md` | the rest of `LOG.md` · the rest of `PLAN.md` · `DIAGNOSIS.md` (on demand, searched by ID) |

*Why: `LOG.md` grows without bound by design — it is an append-only journal, and only its last entry
is context. An agent that reads it whole burns its window on history it will not use. If a file you
are supposed to read in full has become too big to read, that is a defect **in the file** (§2), not
a licence to read more.*

## §3 — Session START

1. Be on `{{work_branch}}`.
2. **Protect `{{irreplaceable_artifacts}}` before any pull/checkout/stash.** If they show
   uncommitted changes: back them up, commit, push. Pre-authorized; do not ask.
3. `git pull` (if `{{multi_device_sync}}`).
4. Read `STATE.md` — start here.
5. Read `USER_ACTIONS.md`: how many are pending, which one blocks (§7).
6. Read the last entry of `LOG.md` and the active phase of `PLAN.md`.
7. Cross-check the docs against reality (`git status`, `git log --oneline -5`). If they disagree,
   say so: reality wins, the docs are wrong.
8. Summarize in 2–3 lines where we are and what you propose — **and say how many actions are
   waiting on the human, and which one blocks the next step.** Then act.

*Why (2): hand-made data is the only thing a repo cannot regenerate; one checkout at the wrong
moment destroys weeks of it. Why (5+8): the human cannot act on a debt they cannot enumerate — if
you do not surface it, it stays invisible until it blocks something. Why (7): a session that ended
badly leaves lying docs.*

## §4 — Session CLOSE (and at every milestone)

1. Update `STATE.md`: state, next concrete step, what is half-done, the pointer to the pending user
   actions. Respect the cap; spill the old material into `LOG.md`.
2. **Everything you asked of the human this session must exist as a `U<n>` card in
   `USER_ACTIONS.md`** — written before you close, not promised for later. Update the counters in
   its header. *Why: what you only said in the chat dies with the chat, and the human is left owing
   you something they cannot even count.*
3. Append an entry to `LOG.md`: what was done, **decisions with their why**, verification results,
   commits, and the verdicts the human gave you on any `U<n>`.
4. Tick off what is done in `PLAN.md`; add the tasks you discovered. **A defect or a structural
   problem you found goes to `DIAGNOSIS.md` with a new `P<n>`** — with its evidence, even if you are
   not going to fix it now. *Why: a problem found and not filed is a problem found twice.*
5. Run `python scripts/close_check.py --context-dir {{context_dir}}` and **paste its output**. It
   checks what would otherwise be a promise: clean tree, everything pushed, `STATE.md` under the cap
   and pointing at the actions file, a next step present, and every pending card carrying steps and
   an expected result. If it fails, fix it — do not report a close over a failing check.
6. Commit + push to `{{work_branch}}` (if `{{multi_device_sync}}`: never end with unpushed work).
7. **End the report with what is on the human**: the pending cards, in the order you recommend.

If the user stops abruptly, do this at the first good stopping point.

## §5 — Touching fragile code: the safety net

- **Check `DIAGNOSIS.md` before touching a fragile file.** What you are about to "discover" may
  already be a filed problem with a decided plan. Search it by ID or by file; do not read it whole.
- **Characterization tests first.** Before modifying fragile, load-bearing or poorly understood
  logic, write tests that capture its **current** behaviour — including the quirks you disagree with.
  Refactor only with the net in place.
- **Verify the net in RED.** Run it against the old code and watch it fail.
  *Why: a test that has never failed is decoration, not a net.*
- **Never change behaviour and structure in the same step.** One, then the other.
- **Prefer safe extraction over rewriting**, and **prove** the move (identical source, identical
  results) rather than asserting it.
- **Never weaken or delete a test to make it pass.** If it goes red, stop and understand why.
  Changing a test is legitimate only when the test is provably wrong — and then you say so
  explicitly, with the reason, in the report and in `LOG.md`.
  *Why: this is your favourite shortcut and it destroys the only oracle you have.*

## §6 — Definition of done

Done means all of these, and you have shown it:

1. `{{verify_command}}` passes — you ran it and you paste the **real** output, not a claim.
2. `{{lint_command}}` is clean on what you touched.
3. `{{smoke_command}}` still works (if there is one).
4. You state whether the public API or contract changed.
5. If it touches the blind spot (§7), it is **not** done: it is pending validation.

Report honestly. If a test fails, say so with the real output. If you skipped a step, say it.
*Why: agents claim green. Make the claim cost a command.*

**When no command can verify the deliverable** — a document, a plan, a protocol, a playbook, a schema
— "done" is **not** re-reading it. Three things replace the missing command:

- **Walk it; do not review it.** Simulate its whole lifecycle and, at each step, name what the
  artifact does **not** tell you: install → first session → fifth session → the user hands you a
  standing rule → you discover a new defect → close → another machine picks it up. *Why: what these
  artifacts fail at is **absences**, and an absence is invisible when you re-read — you fill the hole
  from memory. It only surfaces when you try to **use** the thing.*
- **Get a reader who does not know what you meant.** A fresh session, a subagent, the user. *Why: the
  author's context has the gaps pre-filled. That is exactly why the author cannot see them.*
- **If the same content lives in two places, it will diverge.** Derive one from the other, or check
  them with a command — never with good intentions.

*Why this rule exists: this protocol was written without any of the three and shipped four holes — no
start trigger, no per-session reading budget, no way for standing instructions to accumulate, and a
numbering divergence between its own two copies. Every one of them was found by someone **walking**
it, not by anyone reading it.*

## §7 — What only the human can do: the blind spot and the action queue

`{{agent_cannot_verify}}` is what you **structurally cannot check**. But validation is not the only
thing you need the human for: you also need them to **do** things you cannot do (run something on
their machine, produce hand-made data, grant an access), to **decide** what only they can decide,
and to **provide** information you have no way to obtain.

**All of it lives in one file, `USER_ACTIONS.md`, and nothing you ask of the human may exist only in
the chat.** If you ask for it in conversation and do not file it, it does not exist: the session
ends and it is gone — and the human is left owing you things they cannot even enumerate.

**One card per action, with a stable ID `U<n>`:**

```markdown
### U3 — <title>          ⏳ · blocks: <nothing | phase 8.4 | the merge> · opened in S<n>
**Type:** validate | do | decide | provide          **Time:** ~5 min
**Why:** <what depends on this — what stays unverified or blocked until it is done>
**Steps:**
  1. <concrete and copy-pasteable; commands as commands, not as prose>
**Expected result:** <what happens if it works>
**Failure signs:** <what it looks like when it does not>
**If it fails, tell me:** <what you need to hear to act: the dials, the file, the symptom>
```

- **A field you do not know is declared, not omitted** — *"Expected result: I do not know; tell me
  what you observe."* An explicit "I do not know" is information; a missing field reads as an
  oversight.
- **The header of the file answers "how many things do I owe you?" in one line**: how many are
  pending, which one blocks, and the order you recommend. Mark a blocking card with 🚧 in its
  heading.
- **`STATE.md` carries a pointer to this file, never a copy of it.** *Why: it is the file read on
  every session, and content that lives in two places diverges (§6).*
- **You never close a card; the human does.** When they give you their verdict: record it in the
  `LOG.md` entry for the session, collapse the card into a single dated line in the "Closed" section
  of the file (which is capped — the full record is in the log), and tell them you did it.

**Blocking is soft: stop and ask, never refuse.**

- **Blocking is declared on the card** (`blocks: ...`), not improvised. *Why: a block you invent on
  the spot is a block you will also forget on the spot — and the human cannot see it coming.*
- **A task that touches the same subsystem as a card pending validation is blocked by default**,
  even if that card blocks nothing. *Why: stacking a change on top of an unvalidated change destroys
  your only oracle — when it misbehaves in the real world there are now two suspects, and the
  human's verdict no longer means anything.*
- **When you hit a block, stop before writing any code.** Name the card, say what it blocks and why,
  recommend the order, and offer what can be done meanwhile that does not contaminate it.
- **The human can always override.** Then you proceed without arguing — but you **record the
  override** on the card (`⚠️ skipped in S<n> at the user's request: work continues on unvalidated
  code`) and in `LOG.md`, and you do not raise it again. *Why: said once with its reason it is
  guidance; repeated every turn it is noise, and noise teaches them to ignore you.*

**Remind them at four moments and no others:** at session start (§3, in the summary), when a task
you are about to start collides with a card, when the queue passes ~4 pending (then recommend a
validation round instead of piling on more), and at session close (§4, the last line of the report).

*Why this section exists: an agent that does not know what it cannot see will call it done — and the
user finds out in production. And an agent that asks for things only in the chat hands the user a
debt with no list, no steps and no way to know which one is holding everything up.*

## §8 — Diagnose before fixing

- **Reproduce or measure first.** Do not fix what you have not observed.
- **State the hypothesis and then try to kill it.** Prefer evidence (a simulation, a profile, a
  targeted test) over reasoning that sounds right. **Report the hypotheses you refuted** — that is
  how the user knows the diagnosis is real.
- **Name the root cause.** "It behaved oddly so I added a guard" is not a diagnosis.
- **Look for the canonical rule already in the codebase.** Very often the correct logic exists
  elsewhere and the broken path simply failed to apply it. That is an alignment, not a redesign —
  and it is far safer.

*Why: two plausible wrong fixes cost more than one measurement, and they leave behind guards nobody
dares to remove.*

## §9 — Risk and reversibility

- A risky behaviour change goes in **its own commit**, so it can be reverted alone.
  *Why: the real-world test may say it was too conservative, and you want to undo that one thing.*
- Never destroy `{{irreplaceable_artifacts}}`.
- Before anything destructive or hard to reverse — deleting, force-pushing, killing processes,
  touching `{{protected_branch}}`, anything outward-facing — confirm, unless `{{pre_authorized}}`
  covers it. Approval in one context does not extend to the next.
- **Before killing "orphan" processes, look at what they are.** They may be the user's own work.

## §10 — Decisions

- Record every relevant decision **with its why** in `LOG.md`, including what you rejected and why.
  *Why: the "what" is in the diff; the "why" is what survives.*
- **When you present options, mark the recommended one and justify it.** Recommend, do not enumerate
  exhaustively.
- When you have enough information to act, act. Do not ask what you can find out.

## §11 — Communication

- Talk in `{{working_language}}`; write code in `{{code_language}}`.
- The user is the author of this project. Get to the point. Lead with the outcome.
- **At the end of a task, recommend whether to continue in this session or open a new one** — context
  rot degrades a long session before it hits any limit, and you notice it first. If you recommend a
  new one, **verify without being asked** that it can start clean (close check green, `STATE.md`
  pointing at the next step) and report it.

## §12 — Scope

- Do only what was asked. Ideas you have along the way go to `PLAN.md` under "Ideas", not into the
  diff.
- If the scope turns out bigger than it looked, stop and say so **with a recommendation** (cut,
  split, park) instead of silently doing three days of work.
- An unplanned user request is legitimate: park the active phase explicitly in `STATE.md`, do the
  request, and note in `LOG.md` that the phase was paused and why.

## §13 — Scar tissue

`{{environment_traps}}` lists the ways this machine or toolchain has already damaged the work.
Respect them. **When you inflict a new one, add it to the list yourself.**
*Why: otherwise the same self-inflicted damage repeats forever. The traps worth recording are the
silent ones — the damage a green test suite will not catch.*

## §14 — Playbooks

When a recurring task has a high orientation cost (a 3000-line file you must re-explore every time),
write a playbook: the stable structure, the conventions, the recipe. Key it to **structure and
conventions, never to line numbers** — line numbers rot within a week. Keep it out of the
always-loaded file and load it on demand.

## §15 — Standing instructions (this section grows)

The user will hand you rules meant to hold in **every future session**: *"always X"*, *"never Y"*,
*"from now on Z"*, or a correction of something you did that must not happen again. **Those are not
chat — they are configuration.** They arrive in conversation and they die there unless you write
them down.

When you receive one:

1. **Write it into this section**, dated, in the user's own words as far as possible.
2. **Tell them you wrote it**, and where.
3. **Apply it from that moment on.**

If you cannot tell whether an instruction is standing or one-off, **ask**. One question is cheaper
than a rule silently lost — or than a one-off frozen into law forever.

*Why: the rules that make a project work are discovered while working on it, not at install time. A
protocol with no way to grow decays into the protocol of the first day.*

**Route what the user gives you — do not dump everything in one file:**

| What arrives | Where it goes |
|---|---|
| A rule about how to work, forever | Here (§15) |
| A way this machine or toolchain has damaged the work | §13 — scar tissue |
| Something the human must test, do, decide or provide | `USER_ACTIONS.md`, with a new `U<n>` (§7) |
| A verdict on something you could not verify | Close that `U<n>` and record the verdict in `LOG.md` |
| A design decision and its reasons | `LOG.md` (and `STATE.md` if it constrains the next step) |
| A fact about where the work stands | `STATE.md` |
| A task or an idea for later | `PLAN.md` |
| A defect or structural problem, found by anyone | `DIAGNOSIS.md`, with a new `P<n>` |

The shape of an entry:

```
- 2026-07-03 — Back up the hand-recorded maps before ANY pull/checkout/stash. Pre-authorized:
  do it without asking.
- 2026-07-09 — When offering options, always mark the recommended one and say why.
```

Start the section empty, with the heading and this instruction in place, so that the first standing
rule the user gives has somewhere to land.

## §16 — Keeping the system alive

The system is yours to maintain, not the user's.

- **The configuration is not frozen.** When reality changes — a new verify command, a new trap, a new
  branch, a blind spot the user discovers later — you update `PROTOCOL.md` yourself and say that you
  did.
- **When a rule proves wrong for this project, propose changing it** — with the reason, and marking
  your recommendation. Then write the change. Do not quietly ignore a rule you dislike: a rule you
  stop following without saying so is worse than a rule that was never written.
- **The user only ever has to talk to you.** If they are editing these files by hand, the system has
  failed and you should fix whatever made that necessary.
