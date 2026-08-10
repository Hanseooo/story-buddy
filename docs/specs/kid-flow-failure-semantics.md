# Feature Spec — kid-flow failure & retry semantics

**Status:** built · **Phase:** 2 · **Owner:** no module — this spec owns a **vocabulary**, and names
the session or row that builds each half.
**Derived from:** `docs/specs/kid-flow-ui-docket.md` S3 · **Rationale:** ADR-025 (failure posture,
`failure_reason` shape, never partial), ADR-029 (the redraw), ADR-011 / PRD §13 (moderation),
ADR-012 (the word cap), PRD §7.5 / §11.4, S1 (`kid-flow-book-persistence.md`),
S2 (`kid-flow-pause-lifecycle.md`)

> **This spec builds nothing.** It is a semantics session: it names every failure a child can reach,
> gives each exactly one action, and separates the three things the product currently calls
> *"try again."* §10 lists who builds each half.

## 1. Purpose

Every failure in StoryBuddy is one row state. `run_job.py:43-47` is the **only** writer of
`status='failed'` in the repository, and it catches everything: a flagged story, a dead classifier, a
flagged drawing, a fal.ai outage, a `compose` assertion, a recursion limit. Six distinct causes, one
undifferentiated status, one dev-only `error` string.

That is fine for a worker and useless for a child. "Let's try changing a few words" (PRD §7.5) is the
right thing to say about a flagged story and blames a six-year-old for an outage. This spec fixes the
vocabulary before any screen is drawn.

## 2. Contract slice

`backend/contracts/` is **unchanged**. No `StoryMemory` field, no `schema_version` bump, no
migration, no new endpoint, no new status value. This spec defines meanings over data that already
exists or is already frozen elsewhere.

- **Reads (from `jobs`):** `status`, `input_text`, `pages`, and `failure_reason`
  (added by `job-failure-reason` / migration `0006`)
- **Writes:** nothing
- **Invariants:** see §5

## 3. Three verbs, three different nouns

The docket says *"try again"* is two actions wearing one label. It is three, and they separate by
what each one affects:

| Verb | Affects | Mechanism | Leaves the job? | Costs |
|---|---|---|---|---|
| **redraw** | one picture | `POST /jobs/{id}/confirm` `{action:"try_again"}` (S2) | no — same job, same thread | 1 image + 1 judge |
| **revise** | the child's words | child edits, then `POST /storybooks` | yes — brand-new job | a whole book |
| **retry** | the run | same text unchanged, `POST /storybooks` | yes — brand-new job | a whole book |

`redraw` is S2's and is already specified. `revise` and `retry` are this spec's, and **neither is
that endpoint** — the docket's carry-in constraint holds by construction, because neither takes a
`job_id` at all. They are the existing `POST /storybooks`, unchanged.

Child-facing copy for all three is S4's. These three words are the spec's names and the names tests,
logs and later specs use.

## 4. Behavior & edge cases

### 4.1 The failure map

Every state a child can observe that is not a success, and the one action each offers.

| What happened | Row state | Action | Counts (§4.5) |
|---|---|---|---|
| Text under `MIN_STORY_WORDS` | no job — `422` at `POST /storybooks` | `revise`, in place (never left the editor) | no |
| Text over the cap | job created, `truncated=true` | **none** — a notice, not a failure (ADR-012) | no |
| **Input text flagged** | `failed`, the child's-text reason | **`revise`** | yes |
| Both text classifiers down (`moderation_error`) | `failed`, machine | `retry` | yes |
| A canonical reference flagged | `failed`, machine | `retry` | yes |
| An output image flagged after soften-and-retry | `failed`, machine | `retry` | yes |
| Provider hard error / `compose` assertion / `GraphRecursionError` | `failed`, machine | `retry` | yes |
| A swept pause | the terminal value `data-deletion` picks — **not** `failed` | `retry`, distinct copy (S2 constraint 15) | no |
| A complete book whose images will not sign | `complete` | **re-sign**; second failure → `retry` (§4.7) | no |
| Unknown or stale job UUID | no row — the read `404`s | **none** — no text to resubmit; navigate out | no |

**Never reaches the child**, named so S4 does not design screens for them:

- a consistency failure → `regenerate`, then best-of (ADR-010; the child sees a slower step)
- an `output_mod` soften-and-retry that succeeds (`output_mod.py`)
- a 4th tap at the reveal → becomes a confirm, *"use this one"* (S2 constraint 12). **The cap is not
  a failure** and must never reach the failure vocabulary.
- a `409`-shaped double-confirm → S2 returns `200` with the current status, by design

### 4.2 The one bit this spec requires of `job-failure-reason`

The docket forbids this session from building the enum, and ADR-025 Decision 5 already froze its
shape (`jobs.failure_reason`). This spec therefore states a **single requirement**, and nothing more:

> **Exactly one `failure_reason` value means "the child's own text was rejected." Every other value —
> present or future — maps to `retry`.**

Three properties follow, and they are why the requirement is phrased as a default rather than a list:

1. **It survives any taxonomy.** `job-failure-reason` may ship 3 values or 12; only one of them is
   ever load-bearing here.
2. **It fails safe.** A value this spec has never heard of falls to `retry` — the machine screen.
   A new enum value can never accidentally blame a child, which is the failure mode that actually
   matters in a child-facing product.
3. **It needs no second bit.** §4.5's counter is deliberately reason-blind, so nothing else about the
   taxonomy is load-bearing for the kid flow.

**The production site is exact and singular.** The child's-text value is written when, and only when,
`moderation_router` raises for the input text — `state.input.moderation.passed is False` and
`"moderation_error" not in categories` (`graph.py:24-28`). `moderation_error` is a dead classifier,
not a bad story, and maps to `retry`. So does the *second* call site of the same router, the one that
raises on `ref_moderation_status == "flagged"` (`graph.py:29-30`): a flagged canonical reference is
something the machine drew, not something the child wrote.

**`job-failure-reason`'s reopen trigger is hereby fired.** `DECISION_BACKLOG.md`'s deferral-watch
table gives it two: *"`teacher-dashboard` ships, **or** a Phase-2 failure needs naming."* This spec is
the second clause. The row moves from ⏸ deferred to required-before-S4's-screens-ship.

### 4.3 `revise` — the child's words

The child is returned to the editor with their text prefilled from `jobs.input_text`, edits it, and
submits. That submission is an ordinary `POST /storybooks`: a new UUID, a new row, a new graph run
from `input_gate`. **Nothing on the failed job is mutated.**

Three consequences, stated rather than discovered:

- **The prefilled text is the *clamped* text, not what the child typed.** `POST /storybooks` stores
  the output of `clamp_story` (`main.py:61-75`), so a child who wrote 900 words and was truncated
  gets back only the part that was going to be illustrated anyway. This is a one-time loss at first
  submit, not a compounding one — a revise of already-clamped text clamps to itself. It is
  acceptable because the child was shown the truncation notice at submit time (ADR-012's "never
  silent" is satisfied there, not here).
- **The prefilled text is *not* PII-redacted.** Redaction happens inside `input_gate` into
  `StoryMemory.input.redacted_text`; `jobs.input_text` holds the raw clamped text. Serving it back is
  not a new exposure — the row is already `for select to anon using (true)` and the text is the
  child's own, from their own device — but it means **`revise` re-serves un-redacted text to the same
  capability that submitted it**, and CC-2 should say so rather than imply the row is clean.
- **A `revise` after a flag re-displays text a classifier rejected.** There is no alternative: a child
  cannot change words they cannot see, and PRD §7.5 mandates exactly this interaction.

### 4.4 `retry` — the same run again

Identical mechanism, no edit: the same `input_text` is resubmitted verbatim as a new job. The child
presses one button.

**A retry re-runs the input gate.** It is a full pipeline run from `input_gate`, so a text that passed
once is classified again. Two things follow. First, one extra meta-llama/llama-guard-4-12b call per retry, which is a
local 0.6B model and costs effectively nothing. Second — and this is the honest edge — **a text that
passed on job 1 can be flagged on job 2**, because the backstop is nondeterministic. The child pressed
*"try again"* and lands on the `revise` screen. That is correct, not a bug: the new row's
`failure_reason` describes the new run, and the action follows the row.

**A retry re-pays for everything.** Every reference, every scene, every judge call, and every tap the
child spent at the reveal. A child who spent all 3 taps refining a character and then hit an
output-moderation failure loses all three and starts from zero draws. This is ADR-025's posture
applied consistently — a failed job is terminal and is never resumed from its checkpoint — and it is
named here so nobody later mistakes it for an oversight. There is no partial-restart path and this
spec does not open one.

### 4.5 The chain counter is deliberately dumb

PRD §11.4: after **N=3** failed revisions of the same story, suggest a fresh story rather than an
unbounded retry loop. The docket puts a lineage column out of bounds ("a schema decision this session
flags rather than takes"), so there is no server-side counter to count with.

**The counter is client-side, lives in the flow, and counts consecutive failed jobs — whatever the
reason.**

- **Incremented when the child presses `revise` or `retry` from a `failed` job**, not when a failure
  screen renders. Counting renders double-counts a page reload; counting presses counts attempts,
  which is what N=3 is about.
- **A press that does not follow a `failed` job does not count** — the swept-pause `retry` (§4.8) and
  the fall-through after a signing failure (§4.7). Neither is a failure, and neither is evidence that
  a story is not working.
- **Reset** when any job in the flow reaches `complete`, or when the editor is opened fresh rather
  than from a failure.
- **At 3, the editor gains a third offer: start something new** — the same `revise` mechanism with the
  box empty. It is a *variant*, not a fourth verb.
- **It never gates.** Both buttons stay live at 4, 5 and 40. A suggestion a child can decline is the
  whole of PRD §11.4; a lockout is not.

**Reason-blind is a choice with a named cost.** During a fal.ai outage, a child who retries three
times is told to try a different story, which will not help. The alternative is requiring
`job-failure-reason` to also answer *"was this a moderation failure"* — a second bit, a second thing
to keep correct, and a second way for a taxonomy change to break a kid screen. A sometimes-unhelpful
suggestion is cheaper than that, and the suggestion is declinable.

**`jobs.parent_job_id` is the named upgrade path** if the count ever has to be durable, cross-device,
or teacher-visible. It is a schema decision and belongs to `repeated-failure-offramp`, which stays
blocked on it — but blocked on *only* that half now, since this spec supplies the revision flow that
row was also waiting for.

### 4.6 Terminal is not not-ready — a gap this spec closes

S1 invariant 2 says the reader treats `status !== 'complete'` or `pages.length === 0` as *not ready*.
Read literally, that puts `failed` in the same bucket as `queued`. It is implemented that way today:
`frontend/app/book/[jobId]/page.tsx:61` renders the not-ready state for any non-complete row, so
**a child who reaches `/book/[jobId]` for a failed job watches a loading state forever.**

This spec splits the bucket. It is a refinement of S1's invariant, not an amendment to it — S1 was
distinguishing *empty* from *not ready* and had no failure vocabulary to spend:

| Bucket | Statuses | Renders |
|---|---|---|
| **in-flight** | `queued`, `running` | the wait state (S4) |
| **paused** | `awaiting_confirm` | the reveal (S2, rendered by S4) |
| **terminal-success** | `complete` with non-empty `pages` | the reader |
| **terminal-failure** | `failed`, and whatever `data-deletion` picks for a swept pause | the failure screen, with its one action |

**Every surface that can be reached by URL must handle all four**, because a job UUID is the
capability and a child can arrive at any route in any state. That includes `/book/[jobId]`, which
today handles two of them.

This inherits S2's carry-in requirement and strengthens it: **any surface rendering a terminal state
must seed from a `SELECT` and then subscribe.** `/process/[jobId]` subscribes with no initial fetch
(`page.tsx:18-38`), so a child returning to a *failed* job's URL sees nothing at all — the failing
UPDATE already happened and will never come again. Same bug S2 found at the pause, same fix, now
required by two sessions.

### 4.7 A complete book whose images will not sign

S1 §4.4: if any page fails to sign, the read fails as a whole. The row is `complete`, the pages are
real, and there is no `failure_reason` — the job never failed.

**The action is a re-sign, scoped to the reader**: re-run `createSignedUrls` over the same paths. It
is the correct-cost fix, because signing failures are transient — an expired URL (S1 §4.5's 3600s), a
network blip, a Storage hiccup — and the book already exists. Offering `retry` here would redraw an
entire N-page book to repair an expired link, which is real money against ADR-025's cost posture.

**If the re-sign also fails, fall through to the machine screen** and its `retry`. At that point the
objects are plausibly gone rather than unsigned, and a rebuild is the only remaining answer.

The re-sign is a third action that sits outside the two-verb vocabulary. That is deliberate and
bounded: it applies to exactly one state, it costs nothing, and it never creates a job. Whether it is
a button, an automatic first retry, or both is S4's rendering call.

### 4.8 A swept pause

S2 constraint 15: a swept pause is **not** ADR-025 `failed` and must not read to the child as their
story breaking. Nobody failed; a child closed a tab.

**Same action as a machine failure — `retry` — with distinct copy.** The story went to sleep; make it
again. Identical mechanism, so no new code path and no new verb; different words, so constraint 15
holds. `data-deletion` still picks the status value, and this spec adds one requirement to that row:

> **A swept job's row must survive long enough to offer `retry`** — that is, `input_text` must still
> be readable. If `data-deletion` deletes the row rather than restatusing it, the swept case degrades
> to §4.9's no-action `404`, which is a worse child experience and should be a deliberate choice
> rather than a side effect of a sweep order.

### 4.9 An unknown or stale job UUID

A mistyped link, a link from a deleted job, a link from another device after a purge. The read `404`s
and **there is no action** — no row means no `input_text`, so there is nothing to revise and nothing
to retry. The child is told the story cannot be found and offered a way out to the editor.

This is the one child-facing state with no recovery, and it is correct that it has none. Fabricating
one would mean guessing at a story that does not exist.

### 4.10 What the child is never told

**No failure screen shows a moderation category, a flagged span, or the `error` string.** The child is
told to change some words; never which words, and never why.

This is a deliberate call, not an omission. Telling a child which phrase tripped a safety classifier
teaches them to route around it, which converts a safety mechanism into a tutorial. It also risks
telling a child that something innocent they wrote about their real life was "bad." ADR-025 D5 already
marks `error` dev-only; this spec extends the same rule to `failure_reason`'s value, which selects a
screen and is never rendered as text.

The teacher-facing surface is a different question with a different answer, and it belongs to
`teacher-dashboard`.

### 4.11 Edge cases

| Case | Behavior |
|---|---|
| Child presses `retry` twice quickly | Two jobs, two books, two bills. No dedupe. Naturally bounded by a page navigation on the first press; `rate-limiting` owns the general case. |
| `retry` of a job whose text now passes | Normal book. The failure was transient; nothing records that it happened. |
| `retry` of a job whose text now fails the gate | New row, child's-text reason, the child lands on `revise` (§4.4). Correct — the action follows the row, not the button pressed. |
| `revise` to a text under `MIN_STORY_WORDS` | `422` in the editor, no job created. The same in-place state as a first submit. |
| `revise` to a text over the cap | Clamped and submitted with `truncated=true`, exactly as a first submit. The truncation notice fires again. |
| Failure *after* the reveal, taps spent | All 3 taps and every drawn reference are lost; the new job draws from zero (§4.4). |
| Failed job reached at `/book/[jobId]` | The failure screen, not the wait state (§4.6). Fixes today's infinite loading. |
| Failed job reached at `/process/[jobId]` after the UPDATE | Requires the `SELECT`-then-subscribe fix; without it the child sees nothing (§4.6). |
| Swept pause reached at `/process/[jobId]` | `retry` with sleep copy, not the failure copy (§4.8). |
| `failure_reason` is `null` on an old failed row | Falls to `retry` — the fail-safe default (§4.2). Pre-enum rows never blame a child. |
| `failure_reason` holds a value this spec has not heard of | `retry`. Same default, same reason. |
| Book signs on the second attempt | The reader renders normally; nothing is recorded and no job is created (§4.7). |
| Chain counter at 3, child presses `retry` anyway | Allowed. The off-ramp suggests; it never gates (§4.5). |
| Child reloads the failure screen five times | Counter unchanged — presses are counted, not renders (§4.5). |
| Two devices on the same failed job | Both offer the same action; each has its own counter. Independent presses make independent jobs, which is already true of the editor. |

## 5. Invariants

1. **Three verbs, and only three.** `redraw` never leaves its job; `revise` and `retry` never touch an
   existing job. A re-sign (§4.7) creates nothing.
2. **A terminal job is immutable.** No child-facing action mutates a `failed`, swept, or `complete`
   row. Recovery is always a new job.
3. **`revise` is offered only when `failure_reason` names the child's-text value.** Every other value,
   every unknown value, and `null` get `retry`. **The default never blames the child** (§4.2).
4. **The child is never shown a moderation category, a flagged span, or `jobs.error`** (§4.10).
5. **`failed` is terminal, never not-ready.** No surface renders a wait state for a terminal row
   (§4.6).
6. **No child-facing action spends money unless the child pressed `revise` or `retry`.** A re-sign, a
   reload, and a `404` all cost nothing.
7. **The chain counter suggests and never gates** (§4.5).
8. **The cap is not a failure.** A spent 3-tap budget stays inside S2's vocabulary — *"use this one"*
   — and never reaches a failure screen (§4.1).

## 6. Access & the trust boundary

**No new surface.** `revise` and `retry` are the existing unauthenticated `POST /storybooks`; the
prefill reads `jobs.input_text` under the existing `0001_jobs_table.sql:18-21` policy; the re-sign
uses S1's `storage.objects` policy. **Still exactly two policy surfaces** (S1 constraint 4, S2
constraint 16 — both unchanged), and `auth-and-classroom` still replaces exactly two.

**The retry buttons are a cost surface, not a trust surface.** Each press is a full book against
ADR-025 D4's *per-book* breaker, so N presses is N budgets. This is not new — a child can already
press *"Make my book"* repeatedly on `/write` — but it is now a one-tap loop reachable from a failure,
which is where a frustrated child is. `rate-limiting` owns the bound; this spec names the surface so
that row has something concrete to bound.

**§4.3's un-redacted prefill is the one thing worth reading twice.** It is not a new hole and it is
not fixable here — `jobs.input_text` is what `POST /storybooks` stores and what the worker needs — but
it means the kid flow does hand raw text back to a browser, and `auth-and-classroom` should know that
when it scopes the `jobs` policy.

## 7. The assertions this spec's semantics require

This spec builds nothing, so it writes no tests. It states what the sessions in §10 must assert, so
the semantics are pinned by something executable rather than by prose.

**`job-failure-reason` (backend, `test_run_job.py`):**
- An input-text flag writes the child's-text value; `moderation_error` does **not**; a flagged
  canonical reference does **not**; an output-moderation failure does **not**; a provider error does
  **not**. One value, one production site (§4.2).
- Every raise path writes *some* `failure_reason`, so no failed row is ever `null` after this ships.

**S4 (frontend):**
- The child's-text reason renders `revise`; **every other value, an unknown value, and `null` render
  `retry`** — the fail-safe default, pinned (invariant 3).
- A `failed` row at `/book/[jobId]` renders the failure screen, not the not-ready state (§4.6) —
  this is a regression test against today's behavior.
- A `failed` row reached at `/process/[jobId]` with no subsequent UPDATE renders the failure screen
  (the `SELECT`-then-subscribe fix).
- `revise` prefills from `jobs.input_text`; `retry` submits it unchanged; **neither issues any write
  against the old job** (invariant 2).
- No screen renders a moderation category or `jobs.error` (invariant 4).
- A per-path signing failure re-signs once before showing any failure screen (§4.7).
- The counter increments on press, not on render; three presses surface the start-something-new offer;
  a fourth press still works (§4.5, invariant 7).

## 8. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-9 Failure states = success states** — this spec is CC-9 for the kid flow. Every reachable
  failure has one named action (§4.1); the one state with no recovery is named as such (§4.9); a
  terminal row can never render as an in-flight one (§4.6); the tap cap and a swept pause are kept out
  of the failure vocabulary entirely (§4.1, §4.8).
- [x] **CC-4 Security** — no new endpoint, no new policy surface, still exactly two (§6). The
  `failure_reason` value selects a screen and is never rendered (§4.10).
- [x] **CC-2 PII redaction** — flagged, not clean: `revise` prefills from the **un-redacted**
  `jobs.input_text` (§4.3). Same capability, same child, same device, and no fix available without a
  schema change — but it is written down rather than implied.
- [x] **CC-3 Cost control** — every `retry` and `revise` is a full book; taps and draws are re-paid
  (§4.4); a signing failure costs nothing (§4.7); the press-loop is named for `rate-limiting` (§6).
- [x] **CC-5 Observability** — one log line per action taken (`revise` / `retry` / re-sign, the
  `failure_reason` that selected it, and the chain count at press time). This is the only evidence
  that will ever exist for whether PRD §11.4's N=3 is the right number, and it is the substrate
  `repeated-failure-offramp` reads if the count ever goes durable.
- [ ] CC-1 Moderation ordering — N/A. A `retry` re-runs the whole gate from `input_gate`; no path
  shortcuts it (§4.4).
- [ ] CC-6 Accessibility — S4's.
- [ ] CC-7 Reproducibility — N/A.
- [ ] CC-8 Kid vs teacher design — the child never sees a reason (§4.10); the teacher-facing view of
  the same enum is `teacher-dashboard`'s and is deliberately a different answer.
- [ ] CC-10 Checkpointing / resumability — N/A by decision: a failed job is terminal and is never
  resumed from its checkpoint (§4.4). CC-10 governs stalls, not failures.

## 9. Eval / quality checks

No new instrument. One rule imposed on an existing one:

**CC-5's per-action line is the only measurement of whether the vocabulary works.** The question
`repeated-failure-offramp` exists to answer — *does a child who fails three times benefit from being
pushed to a new story?* — is unanswerable without knowing which verb they pressed and how many times.
Logging it costs one line and is the difference between N=3 being a measured number and a number
copied out of a PRD.

## 10. Blast radius

**This spec changes no code.** It is a vocabulary, and the vocabulary is spent by others:

| Owner | What it builds from this spec |
|---|---|
| `job-failure-reason` (reopened, §4.2) | The enum, migration `0006`, and the map in `run_job.py`'s except block — with §4.2's one requirement and §7's assertions |
| **S4** (reader & wait states) | Both failure screens, the four-bucket render (§4.6), the `SELECT`-then-subscribe fix, the re-sign (§4.7), the prefill, and the chain counter (§4.5) |
| `data-deletion` | §4.8's added requirement: a swept row survives long enough to offer `retry` |
| `repeated-failure-offramp` | Unblocked on its revision-flow half (§4.5); still blocked on `jobs.parent_job_id`, which stays a flagged schema decision |
| `rate-limiting` | §6's named press-loop surface |
| `teacher-dashboard` | The teacher-facing reading of `failure_reason`, which §4.10 deliberately does not answer |

**Docs changed in the same change as this spec:**

| File | Change |
|---|---|
| `docs/product/DECISION_BACKLOG.md` | `job-failure-reason` moves from ⏸ deferred to reopened, with §4.2's requirement; `repeated-failure-offramp` records that its revision-flow half is satisfied |
| `docs/specs/kid-flow-ui-docket.md` | S3 → DONE with constraints 17–22; S4's cluster gains the four-bucket render and the `job-failure-reason` build-order dependency; an amendment records the reopen |
| `docs/specs/USER_FLOW.md` §6 | The three verbs, and §4.6's terminal-vs-not-ready split |

**Not touched:** `backend/` and `frontend/` — every line is S4's or `job-failure-reason`'s.
`MASTER_SPEC.md` §7 and `DECISION_BACKLOG.md`'s `kid-flow-ui` roster row wait for S4, per the
docket's roster note.

## 11. The migration number

**This spec claims none.** S2 left `0006` free and assigned it to `job-failure-reason`; §4.2 reopens
that row without moving its number. Next free after `job-failure-reason` is `0007`, unclaimed.

## 12. Linked decisions & open questions

**Depends on:** ADR-025 (D5's `failure_reason` shape; the never-partial posture; D4's per-book
breaker) · ADR-029 / S2 (the redraw, the tap cap, the swept pause) · ADR-011 / PRD §13 (what flags a
story) · ADR-012 (the cap and its notice) · ADR-017 (why an unauthenticated retry button is a
classroom surface, not an internet one) · PRD §7.5, §11.4 · S1 constraints 1–8 · S2 constraints 9–16.

**Takes no schema decision.** The two candidates — `jobs.failure_reason` and `jobs.parent_job_id` —
are both named, both scoped, and both left to their owners (§4.2, §4.5), per AGENTS.md
"Architecture is locked" and the docket's Explicitly-out line.

**Handed to later sessions:** see §10.

**Open:**
- **The chain counter is reason-blind and will occasionally give unhelpful advice** (§4.5). Accepted
  in exchange for keeping the `job-failure-reason` requirement at one bit. If CC-5's logs show
  children hitting the N=3 suggestion mostly during outages, the fix is a second bit, not a redesign.
- **N=3 is unvalidated.** It comes from PRD §11.4 and no child has ever seen it. §9's log line is what
  would make it measurable.
- **`revise` prefills clamped, un-redacted text** (§4.3). Both properties are consequences of what
  `POST /storybooks` stores, not choices this spec made, and neither is fixable without a schema
  change. Named so `auth-and-classroom` and `input-gate-hardening` can see them.
- **A `failed` job's checkpoint is abandoned, not reused** (§4.4). A partial-restart path would be a
  real cost saving on late failures and a real violation of ADR-025's terminal posture. Not opened
  here; it would need an ADR.

## 13. Definition of done

This spec is done — it is a semantics artifact and produces no code. **The vocabulary it defines is
done** when:

1. `job-failure-reason` ships §4.2's one requirement, with §7's five negative assertions.
2. S4 renders both screens with `retry` as the fail-safe default, the four-bucket split of §4.6, the
   `SELECT`-then-subscribe seed, the re-sign of §4.7, and the counter of §4.5.
3. `data-deletion` answers §4.8's row-survival requirement either way, deliberately.
4. CC-5's per-action line exists, so §9 is measurable.

**Not done** if: a machine failure tells a child to change their words; an unknown or `null`
`failure_reason` renders anything but `retry`; a moderation category, a flagged span, or `jobs.error`
reaches a child; a `failed` row renders as a wait state anywhere; the tap cap or a swept pause is
rendered as a failure; the chain counter blocks a button; a child-facing action mutates a terminal
job; or a signing failure costs a new book.
