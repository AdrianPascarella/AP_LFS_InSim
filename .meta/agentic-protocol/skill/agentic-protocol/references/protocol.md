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
*Why: otherwise you restart from zero every session and the user re-explains the project forever.
Files in git also outlive the model, the tool and the machine.*

## §1 — You own the files

You are their only writer. Keep them readable by a human who did not write them: their language,
prose, no private shorthand. The human reads them to audit you; they never edit them.
*Why: a single writer removes format drift, duplicate IDs and contradictory versions of the same
fact — and readable files are the user's only way to see where you are taking the project.*

## §2 — The context files

| File | What it is | Size |
|---|---|---|
| `STATE.md` | The handoff: where we are, what is pending validation, **the next step** | **Hard cap ~120 lines** |
| `LOG.md` | Append-only journal, one entry per session | Unbounded; only the last entry is read on start |
| `PLAN.md` | Phased plan with checklists and acceptance criteria | Unbounded; only the active phase is read on start |
| `DIAGNOSIS.md` | Known problems, each with a stable ID and its status | Reference; read on demand |
| `PROTOCOL.md` | These rules | Read when in doubt |
| `INDEX.md` | Entry point | Tiny |

**The cap on `STATE.md` is a rule.** When it overflows, the oldest material moves to `LOG.md`. Keep
only: current state, the validation queue, the next concrete step, and what was left half-done.
*Why: `STATE.md` is the one file read on **every** session, so its size is a recurring tax. Left
unchecked it silently becomes a second journal and buries the next step under months of narrative.*

**Stable IDs.** Problems are `P<n>` (`DIAGNOSIS.md`), workstreams `W<n>` (`PLAN.md`), sessions `S<n>`
(`LOG.md`). An ID never changes meaning. A solved problem keeps its ID and gains
`RESOLVED (S<n>): <how>` — it is never deleted.
*Why: without stable IDs every document re-explains the same thing in different words, and the
versions drift apart.*

**Reading budget — what you read at the start of a session, and what you do not.**

| Read in full | Read partially | Do NOT read on start |
|---|---|---|
| `STATE.md` (it is capped for exactly this reason) · this file | the **last entry** of `LOG.md` · the **active phase** of `PLAN.md` | the rest of `LOG.md` · the rest of `PLAN.md` · `DIAGNOSIS.md` (on demand, searched by ID) |

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
5. Read the last entry of `LOG.md` and the active phase of `PLAN.md`.
6. Cross-check the docs against reality (`git status`, `git log --oneline -5`). If they disagree, say
   so: reality wins, the docs are wrong.
7. Summarize in 2–3 lines where we are and what you propose. Then act.

*Why (2): hand-made data is the only thing a repo cannot regenerate; one checkout at the wrong moment
destroys weeks of it. Why (6): a session that ended badly leaves lying docs.*

## §4 — Session CLOSE (and at every milestone)

1. Update `STATE.md`: state, next concrete step, what is half-done, the validation queue. Respect the
   cap; spill the old material into `LOG.md`.
2. Append an entry to `LOG.md`: what was done, **decisions with their why**, verification results,
   commits.
3. Tick off what is done in `PLAN.md`; add what you discovered.
4. Run `python scripts/close_check.py --context-dir {{context_dir}}` and **paste its output**. It
   checks what would otherwise be a promise: clean tree, everything pushed, `STATE.md` under the cap,
   a next step and a validation queue actually present. If it fails, fix it — do not report a close
   over a failing check.
5. Commit + push to `{{work_branch}}` (if `{{multi_device_sync}}`: never end with unpushed work).

If the user stops abruptly, do this at the first good stopping point.

## §5 — Touching fragile code: the safety net

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

## §7 — The blind spot: the human is the oracle

`{{agent_cannot_verify}}` is what you **structurally cannot check**. For anything that lands there:

- Deliver a **"what to test"** note: concrete steps, expected result, and what would indicate the fix
  failed.
- Put it in the **validation queue** in `STATE.md` — a list, not prose buried in a paragraph:

  ```
  ## Validation queue (only the user closes these)
  - [ ] ⏳ S14 — new follow law: does it stop oscillating in traffic?
  - [x] ✅ S13 — radar losing cars at junctions — validated by the user 2026-07-13
  ```
- **You never close your own validation.** It moves to ✅ only when the user says it works — and you
  are the one who edits the file when they do.
- If the queue keeps growing, say so and recommend a validation round before piling on more.

*Why: this is the highest-value line in the whole configuration. An agent that does not know what it
cannot see will call it done — and the user finds out in production.*

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
- **When you present options, mark the recommended one and justify it.** Recommend; do not enumerate
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

## §15 — Keeping the system alive

- **The configuration is not frozen.** When reality changes — a new verify command, a new trap, a new
  branch, a blind spot discovered later — you update this file yourself and say that you did.
- **When a rule proves wrong for this project, propose changing it**, with the reason and your
  recommendation, and then write the change. Do not quietly ignore a rule you dislike: a rule you
  stop following without saying so is worse than a rule that was never written.
- **The user only ever has to talk to you.** If they are editing these files by hand, the system has
  failed and you should fix whatever made that necessary.
