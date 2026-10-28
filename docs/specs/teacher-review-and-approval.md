# Feature Spec — teacher: review & approval

**Status:** draft · **Phase:** 2 · **Owner:** `supabase/migrations/0011_jobs_rejected_at.sql`,
`backend/app/review.py`, `backend/app/auth.py` (`owned_job`),
`frontend/app/classroom/[classroomId]/books/**`
**Derived from:** `docs/specs/teacher-dashboard-docket.md` S3 · **Rationale:** ADR-017 (approval is
always manual), ADR-021 (the gallery is display-only), ADR-025 (failure posture, `failure_reason`
shape), PRD §11.1, `ethics_and_safety.md` §4, MASTER_SPEC §5 (CC-4, CC-5, CC-6, CC-8, CC-9)

> A state-model session. It closes the set of states a book can occupy from the teacher's side,
> gives every transition an actor and a trigger, and picks a rendering for each — teacher-facing and
> child-facing. It does **not** provision anything (S2), does not build the gallery that consumes
> `approved_at` (`classroom-sharing`), and adds no recovery verb (kid-flow docket: three, and only
> three).

## 1. Purpose

`0008:15` added `approved_at timestamptz` and nothing else. Today, a book the teacher looked at and
decided against is byte-identical to one that arrived thirty seconds ago: both have
`approved_at is null`. The teacher re-reads it every session, forever, with no way to record *I have
seen this*. PRD §11.1 says "manually approved **or rejected**"; the schema can only express one of
those words.

This spec makes the second word real, and builds the screen where both are spent. It is the only
thing standing between a generated book and a peer.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

None. `backend/contracts/` is untouched, no `StoryMemory` field moves, no pipeline node changes.
`run_job.py`'s `_finish` remains the only writer of `pages` and `reveal` (kid-flow docket).

## 3. Position in the system map

```
child finishes a book ──▶ jobs.status = 'complete', approved_at null, rejected_at null
                                  │
                                  ▼
        /classroom/[id]/books ── "Needs review" tab (browser SELECT, RLS)
                                  │
                                  │  teacher opens the <dialog>, reads, decides
                                  ▼
        POST /jobs/{id}/review  {decision}      (teacher_router, S1-4)
                                  │  require_teacher + owned_job
                                  ▼
              approved_at set ──▶ peers can read it   (0008:28, classroom-sharing)
              rejected_at set ──▶ peers cannot; teacher's queue shrinks
              both null       ──▶ back in the queue   (Undo)
```

Nothing downstream changes. `0008`'s student, researcher and storage policies all read
`approved_at is not null` and keep their exact current meaning.

## 4. Behavior & edge cases

### 4.1 Three states, derived from two timestamps (Q11)

| State | Predicate |
|---|---|
| **pending** | `approved_at is null and rejected_at is null` |
| **approved** | `approved_at is not null` |
| **rejected** | `rejected_at is not null` |

No stored enum, no `review_status` column. `approved_at` keeps its exact current semantics, so
`0008`'s four consuming policies, S3-8, and the future gallery read unchanged — the migration is
purely additive to everything that already exists.

**Migration `0011`** (ADR-flagged per `AGENTS.md` §2 — it is a schema change):

```sql
alter table jobs add column rejected_at timestamptz;

alter table jobs add constraint jobs_review_exclusive
  check (approved_at is null or rejected_at is null);
```

**The CHECK is what closes the set.** Without it, both-set is a fourth, unnamed state reachable by
any bug, and it would render as *approved* to the gallery and *rejected* to the teacher
simultaneously — the exact "reads identically to a different state" failure the docket's stance
forbids. It is a DB constraint rather than application code because the application is not the only
thing that will ever write these columns (a support fix, a backfill, a psql session).

**Review state is meaningful only on `status = 'complete'`.** A `failed`, `queued`, `running` or
`awaiting_confirm` row carries neither timestamp and is not reviewable. This is enforced in the
endpoint (§4.3), not by a second CHECK: the endpoint has to return a legible error anyway, and a
composite constraint would buy nothing the endpoint does not already guarantee.

### 4.2 All six transitions (Q12)

The decision is a **value**, not two buttons. One control, three values, six transitions, one code
path:

| From → To | pending | approved | rejected |
|---|---|---|---|
| **pending** | — | approve | reject |
| **approved** | undo | — | reject |
| **rejected** | undo | approve | — |

Back-to-pending is allowed because it is free — the same write with both columns nulled — and
because it is what makes **Undo** possible (§4.7), which is what lets the screen skip a confirmation
dialog on every one of forty decisions. A teacher who mis-taps has a remedy that costs one tap
instead of asking a child to remake their book.

**Un-approving is permitted.** `0008:52`'s policy already allowed it and the docket correctly called
it a product decision. A book pulled from the gallery is exactly the case ADR-017's manual gate
exists to catch — a mistake caught late is still worth catching. The child-facing consequence is
§4.10: none.

### 4.3 The write surface (S1-6, S1-4, S1-5)

```
POST /jobs/{job_id}/review
body:   {"decision": "approved" | "rejected" | "pending"}
```

Hung on S1's `teacher_router` — there is no second teacher router and the router carries no prefix
(S1-4). New module `backend/app/review.py`.

**Authorization is two dependencies. Neither is a handler-body check** (S1-5):

1. `require_teacher` — already carried on the router, so it cannot be forgotten.
2. **`owned_job`** — new, added to `backend/app/auth.py` beside `owned_classroom`, on the same
   pattern. S1-5 explicitly sanctions this: *"a session needing ownership of a different resource
   adds one on the same pattern rather than checking inline."* It resolves `job_id` from the path,
   joins `jobs → classrooms` on `owner_id = auth.uid()`, and returns the row.

**Responses:**

| Case | Response |
|---|---|
| Job does not exist | `404` |
| Job exists, different teacher's classroom | `404` — **the same response**, so job UUIDs cannot be probed for existence |
| `status != 'complete'` | `422`, naming the status |
| `decision` not one of the three | `422` (Pydantic `Literal`) |
| Valid | `200`, the row's new review state |
| Deciding what is already decided | `200`, current state, no write — matches S2's double-confirm posture |

**The server sets the timestamps.** The client never supplies one. `approved` writes
`approved_at = now(), rejected_at = null`; `rejected` mirrors it; `pending` nulls both. Because every
decision nulls its opposite in the same statement, `jobs_review_exclusive` cannot be violated by this
endpoint at all.

**CC-5 — one log line per *state-changing* decision:** job id, classroom id, teacher id, from-state,
to-state. An idempotent repeat writes nothing and logs nothing. This is
the only audit trail that will ever exist for the gate `ethics_and_safety.md` §4 rests on, and it is
the substantive reason this is an endpoint rather than a browser UPDATE. A browser write has nowhere
to put this line and lets the client choose the timestamp.

### 4.4 The RLS write path goes away

`0009:38` grants `authenticated` UPDATE on `approved_at`, and `0008:52`'s `teachers approve jobs`
policy permits the row. With the write on FastAPI, **both are unreachable.** `0011` removes them:

```sql
revoke update (approved_at) on public.jobs from authenticated;
drop policy "teachers approve jobs" on public.jobs;
```

An inert policy on the ethics-critical column is precisely what misleads whoever next audits the auth
surface — it documents a write path the product does not use.

**This is an amendment to two frozen constraints and is flagged as such:**

- **S1-7** ("`authenticated` holds UPDATE on exactly one column of `jobs`") — now holds UPDATE on
  none.
- **S3-8** from the auth docket ("the only RLS write path is the teacher's UPDATE on `jobs`") — there
  is now no RLS write path at all, which makes **S3-7** ("writes never go through RLS") true with no
  exceptions. The system gets simpler, not more complex, but the change must be recorded rather than
  discovered.

`0009` itself is not edited — S1 is DONE. `0011` revokes what `0009` grants.

### 4.5 The library query

One browser SELECT under `teachers read classroom jobs` (`0008:36`), per S1-6 and S2-7. No endpoint
is a read.

```
jobs
  .select("id, status, failure_reason, approved_at, rejected_at, created_at,
           input_text, pages, profile_id, profiles(display_nickname)")
  .eq("classroom_id", classroomId)
```

Two things about that query are load-bearing:

- **`classroom_id` is filtered explicitly.** S4-4 and S2-2 say the same thing twice: RLS does not
  scope a list. A teacher with two classrooms whose query omits the filter gets both classrooms'
  books in one queue.
- **`removed_at` is *not* filtered.** S2-1 froze that a student's books survive their removal, so a
  departed child's pending book still needs a decision and still belongs to the classroom. This is a
  deliberate departure from S2-2, which governs lists of *students*; a list of books is not one. The
  row is attributed to the same `display_nickname` it always was (S2 §4.5).

The embedded `profiles(display_nickname)` join works because `jobs.profile_id` references
`profiles(id)` (`0008:13`) and the teacher holds `teachers read classroom profiles` (`0008:101`).

### 4.6 The screen (Q14)

`/classroom/[classroomId]/books` — **the only route S3 adds** (S2-5). Inside `TeacherShell`, which
gains one tab and nothing else (S2-6).

| View | Rows | Order |
|---|---|---|
| **Needs review** *(default)* | `complete`, both timestamps null | `created_at` desc |
| **Approved** | `approved_at is not null` | `approved_at` desc |
| **Rejected** | `rejected_at is not null` | `rejected_at` desc |
| **Didn't finish** *(a `<details>`, not a tab)* | `failed` | `created_at` desc |

**In-flight rows never appear.** `queued`, `running` and `awaiting_confirm` are books being written
right now; there is nothing a teacher can do with one, and showing them would put non-actionable rows
in a screen whose entire purpose is actions. It would also be the one part of the list that needs
Realtime to not be a lie.

**Freshness: refetch on mount and on `visibilitychange`.** With in-flight rows hidden, the list only
changes when a job finishes — an event the teacher is not sitting and watching. No Realtime
subscription, so **S4-8 holds by construction**: `useJob` remains the only per-job status hook and no
second job-status state model is introduced anywhere.

**Empty states, one per view, and they are not interchangeable:**

- *Needs review* empty is the **goal state** and must read as finished, not as absence — "Nothing
  waiting. You're all caught up." A generic "no items" here reads as a broken screen at the exact
  moment the teacher has succeeded.
- *Approved* empty — "Nothing approved yet. Books you approve appear in the class gallery."
- *Rejected* empty is the common case and should be quiet — "Nothing here."
- *Didn't finish* renders only when non-empty. A `<details>` with a zero count is noise.

### 4.7 The review dialog, and the pass (Q15)

**Per-book approval only. No bulk of any kind.** ADR-017's "manual, always" is not satisfied by a
human hand on a select-all: forty books is forty deliberate decisions, and the friction is the
feature. The design work goes into making each read fast, not into skipping it.

S2-5 froze `/books` as the only route, so there is no `/books/[jobId]`. The reader is a native
`<dialog>` (S2-8), which is also the right answer: focus trap, `Esc`, `::backdrop` and an inert
background are all native and are exactly what is easy to get subtly wrong by hand.

**Approval includes classroom downloads (ADR-072).** Before approval, the dialog explains:
“Classmates will be able to read and download this book. Copies already saved remain after approval
is withdrawn or the book is deleted.” Associate this explanation with the approval control.

**The dialog advances.** This is the single decision that makes forty books tractable:

1. A row opens the dialog at that book.
2. Approve or reject — one tap each.
3. The dialog does not close. It loads the **next pending book** and the decided row leaves the
   queue behind it.
4. When the queue empties, the dialog closes onto §4.6's caught-up state.

Forty books becomes one continuous pass rather than forty open-decide-close cycles, and it costs an
index into the pending list. `Esc` leaves the pass at any point; reopening resumes from the top of
what is left.

**No confirmation dialog on reject.** A confirm on every decision in a forty-item queue trains the
teacher to dismiss it, which is worse than no guard at all. The guard is **Undo**: every decision
raises a toast with an undo action, which is `decision: "pending"` on the same endpoint. §4.2's sixth
transition pays for itself here.

**Writes render optimistically and reconcile against the response** (S2 §4.9). On failure the row is
restored to its view and the toast reports the error — a decision that silently did not happen is the
one outcome this screen cannot afford.

**Signing follows S3-6's join, not a path rewrite.** `pages` holds durable Storage paths and never
signed URLs (kid-flow docket); signing happens at read time under `teachers read classroom images`
(`0008:145`). List rows sign **only a first-page thumbnail**; the dialog signs the full page set when
it opens, and prefetches the next book's set during the current one. Signing 40 × N URLs on mount is
the thing to avoid.

### 4.8 Books that didn't finish (Q13)

Failed books appear, outside the review tabs, because there is nothing to approve — but a child whose
story was stopped must not be invisible to the adult responsible for them, which is what
`ethics_and_safety.md` §4 assumes and what the kid-flow docket parked here.

**Two readings, selected by `failure_reason`, and nothing else:**

**Eight exact safe teacher readings, selected by `failure_reason` (amended by ADR-038):**

| `failure_reason` | Teacher-facing label | Also shown |
|---|---|---|
| `child_text` | The submitted title or story did not pass the input safety check. | The child's own `input_text` |
| `character_safety` | A generated character reference did not pass the image safety check. | Nothing |
| `scene_safety` | A generated scene did not pass the image safety check. | Nothing |
| `service_busy` | A required story-making service was temporarily unavailable. | Nothing |
| `worker_stopped` | The worker process stopped or exceeded its job deadline. | Nothing |
| `service_limit` | The configured story-making service reported exhausted quota or credits. | Nothing |
| `book_limit` | The job reached its paid-image circuit breaker. | Nothing |
| `system_error` (**or null, legacy `machine`, or unknown**) | The job ended because of an unclassified system error. | Nothing |

The child-facing wording for these same reasons is
[story failure recovery](story-failure-recovery-ux.md) §3's, implemented as
`frontend/lib/failureCopy.ts`. The teacher review surfaces now render the checked title
per [story titles](story-titles.md) §5, with the existing excerpt fallback for legacy rows.

**The fail-safe default is preserved across the audience change.** `system_error` is the fallback label for any unclassified or unknown failure reason. A new enum value can never accidentally tell a teacher that a child wrote something wrong. CC-8's "the teacher-facing view is deliberately a different answer" means *more* than the child is told, not *differently safe*.

**Never rendered:** a moderation category, a flagged span, or `jobs.error`. This is not only policy —
it is also what is available. `graph.py` writes exact sentinels; `mod.categories` lives in the LangGraph
checkpoint and is never written to `jobs`. `jobs.error` holds a raw exception string for machine
failures and ADR-025 D5 marks it dev-only. It is unfit for an adult UI for the same reason it is unfit for a child's.

**Showing the flagged text is not a new exposure.** `teachers read classroom jobs` (`0008:36`) already
grants the teacher `input_text` on every book in their classroom. The choice here is framing, not
access.

**No fourth verb.** The teacher cannot retry, revise or redraw a child's failed book. The section is
informational; the three verbs stay the child's (kid-flow docket).

### 4.9 The pending count (Q16)

A **client component** in the shell's Books tab fetches the pending count via RLS after hydration.

`TeacherShell` is a server component owning a **single** `profiles` read (S2-6); adding a count query
to it would put a second server read on every teacher navigation for a number that changes on someone
else's action. Fetching it in the browser keeps S2-6 intact and follows S1-6 — reads via RLS in the
browser.

No email, no push. Both would need a provider, a scheduler, and a decision about sending
flagged-story signals to an adult's inbox — three `AGENTS.md` §2 decisions that do not belong to a
state-model session.

### 4.10 What the child sees: nothing (the child-facing consequence)

> **Amended by §14 (ADR-081 accepted 2026-10-29).** The child still never sees a verdict word. A child may
> now read a teacher's note, and the download line is reworded. The text below is the pre-amendment
> reasoning and still binds everything §14 does not name.

**A child is never shown a review state.** Their own book always reads as finished. Pending, approved
and rejected are indistinguishable from inside the kid flow.

`students read own jobs` (`0008:24`) carries no `approved_at` filter, so a child can always read their
own book and *could* read both timestamps. Not showing them is a choice:

- Telling a 10-year-old their teacher rejected their story hands them a verdict with no adult present
  to frame it, and directly opposes the kid-flow posture that a child is never told their own writing
  was the problem (`kid-flow-failure-semantics.md` §4.10).
- Showing pending-but-not-rejected means a rejected book says "waiting for your teacher" forever — a
  lie that does not decay.
- The real-world mechanism already exists and is better than either: the teacher says *"I've put your
  books up."*

**This binds `classroom-sharing`.** That row renders the gallery and must not invent a rejection
signal, an absence badge, or a "why isn't mine here" affordance without amending this spec. S3 adds
**zero** kid-facing code and does not reach into a DONE docket's frozen surface.

### 4.11 UX rules for the screen

The teacher arriving here has ~40 books, ten minutes, and probably a phone.

- **Land on the work.** The default tab is the queue and the heading carries the count — *"12 waiting"*
  — rather than a badge to hunt for. The number is the first thing read.
- **One decision per screenful.** On mobile the dialog is full-viewport; the two actions are fixed at
  the bottom, thumb-reachable, and never scroll out from under the pages.
- **Approve is primary, reject is secondary but never hidden.** A destructive-styled reject would be
  wrong — rejecting a book is an ordinary, reversible editorial act, not a danger zone.
- **Undo over confirm** (§4.7). Every decision is recoverable in one tap for as long as the toast
  lives; nothing asks "are you sure" forty times.
- **Skeleton rows, not a spinner,** on first load, so the list does not reflow under the teacher's
  thumb as thumbnails sign in. Thumbnails are lazy and have a reserved aspect box.
- **Mobile-first, per S2 §4.11** — cards below `sm`, table at and above.
- **Native elements only** (S2-8): `<dialog>` for the reader, `<details>` for the didn't-finish
  section, the toast S2 already hand-rolled. No component library; adding one is an `AGENTS.md` §2
  decision.
- **CC-6:** the `<dialog>` supplies the focus trap and `Esc`. Tabs carry `role="tablist"` with arrow-key
  movement; page images take their `alt` from the page's caption; the pending count is in an
  `aria-live="polite"` region so a decision announces the new number; the toast's undo is a real
  `<button>` reachable by keyboard before it expires.

### 4.12 Edge cases

| Case | Behavior |
|---|---|
| Teacher approves a book already approved | `200`, no write, no log line. Idempotent (§4.3). |
| Teacher opens a job UUID from another classroom | `404`, identical to a nonexistent job (§4.3). |
| Teacher tries to approve a `failed` book | `422`. The failed section offers no decision control at all, so this is only reachable by hand. |
| Two teachers own the same classroom | Not possible — `classrooms.owner_id` is single-valued (`0007`). |
| Two tabs, same teacher, same book | Last write wins. Both are the same principal making the same kind of decision; there is no conflict worth a version column. |
| A book is decided while the dialog is open on it elsewhere | The reconcile after the response corrects the view (§4.7). |
| Removed student's pending book | Appears and is reviewable, attributed to their nickname (§4.5, S2-1). |
| Classroom deleted while the screen is open | `jobs` cascades (`0008:13`); the refetch returns empty and the shell's classroom switcher no longer lists it. |
| A page image will not sign | The dialog renders the page with its caption and a placeholder rather than failing the whole book — a teacher can still judge the text. A book whose images *all* fail to sign is flagged in-dialog and the decision controls stay live. |
| `pages` is empty on a `complete` row | Not reachable by design (`_finish` writes both), and `0004`'s comment names the missing CHECK. Rendered as an empty book with decision controls live; the teacher can reject it. |
| `failure_reason` is `null` on a failed row | *Machine* reading. The fail-safe default (§4.8). |
| `failure_reason` holds an unknown value | *Machine* reading. Same default, same reason. |
| Undo pressed after the toast expired | Not possible from the toast; the book is in Approved or Rejected and the decision can be changed there (§4.2). |
| Queue empties mid-pass | The dialog closes onto the caught-up state (§4.7). |
| Teacher leaves the tab open through a lesson | `visibilitychange` refetches on return (§4.6). |

## 5. Invariants

1. **The state set is closed at three,** and `jobs_review_exclusive` makes the fourth combination
   unrepresentable (§4.1).
2. **Every transition is reachable and every state is leavable** (§4.2). No teacher-reachable dead
   end.
3. **The server sets every review timestamp.** No client ever supplies one (§4.3).
4. **Every review write passes `require_teacher` and `owned_job`,** both dependencies, never a handler
   body; unauthorized and nonexistent are the same `404` (§4.3, S1-4, S1-5).
5. **`authenticated` holds no UPDATE on `jobs`.** After `0011`, writes never go through RLS anywhere
   in the system, with no exceptions (§4.4).
6. **`approved_at`'s meaning is unchanged.** Every existing consumer policy reads correctly without
   modification (§4.1).
7. **Only `failure_reason = 'child_text'` names the child's writing.** Every other value, every
   unknown value and `null` render as *machine*, for the teacher as for the child (§4.8).
8. **No moderation category, flagged span, or `jobs.error` reaches any screen** — teacher or child
   (§4.8).
9. **The child is never shown a review state,** and `classroom-sharing` inherits that (§4.10).
   *Amended by §14 (SH-01): never shown a verdict word. A teacher's note and the reworded download
   line are the only review-related text a child reads.*
10. **There is no bulk decision and no auto-approve** (§4.7, ADR-017).
11. **No fourth recovery verb.** The teacher cannot act on a child's failed book (§4.8).
12. **Reads stay in the browser under RLS; the only endpoint is a write** (S1-6, S2-7).
    *Amended by §14 (SH-05): the private notes table is service-role only, so its reads go through
    owner-checked endpoints. Every other read in this spec stays in the browser.*

## 6. Access & the trust boundary

**One new endpoint, no new read surface.** The library, the counts and the thumbnails are all browser
reads under `0008`'s existing teacher policies. Storage access inherits S3-6's join back to `jobs` —
the `{job_id}/{scene_id}.png` shape is untouched.

**The policy surface shrinks.** `0011` drops one UPDATE policy and one column grant (§4.4). No policy
is added. No anon policy exists or is created (S3-4).

**`owned_job` is the whole trust boundary for the write.** It is the only thing between a
`require_teacher` principal and a book in someone else's classroom, which is why it is a dependency on
the same pattern as `owned_classroom` rather than a check a future endpoint could forget to copy.

**The flagged-text exposure is pre-existing, not new** (§4.8): `0008:36` already grants the teacher
`input_text` classroom-wide. Worth reading twice because this is the first screen that actually
renders it.

## 7. Deterministic tests (Tier A)

**Backend (`backend/tests/test_review.py`):**
- Each of the six transitions writes the expected timestamp pair, and the opposite column is nulled
  in the same write.
- A decision on a job in another teacher's classroom returns `404`, **byte-identical** to a decision
  on a nonexistent UUID.
- A decision without `require_teacher` (student token, researcher token, no token) is rejected before
  the handler runs.
- A decision on a `failed`, `queued`, `running` or `awaiting_confirm` job returns `422` and writes
  nothing.
- A repeated identical decision returns `200` and does not rewrite the timestamp.
- The response timestamp is server-generated: a client-supplied timestamp in the body is ignored or
  rejected.
- One log line is emitted per state-changing decision, carrying from-state and to-state.

**Migration (`backend/tests/test_rls_isolation.py`, extending the existing suite):**
- `jobs_review_exclusive` rejects an UPDATE setting both timestamps.
- `authenticated` cannot UPDATE `approved_at` after `0011` — the previously-passing write now fails.
- Every `0008` SELECT policy still returns the same rows for student, teacher and researcher after
  `0011`.

**Frontend:**
- Each tab's query returns only its own state; a book decided in the dialog leaves the default tab.
- The list query filters `classroom_id` explicitly — a two-classroom teacher sees one classroom's
  books (regression against S4-4 / S2-2).
- A removed student's pending book still appears (§4.5).
- `failure_reason` of `machine`, `null`, and an invented value all render the machine copy;
  **only** `child_text` renders the safety copy — the fail-safe default, pinned.
- No screen renders `jobs.error` or a moderation category.
- After a decision the dialog advances to the next pending book; when none remain it closes to the
  caught-up state.
- A failed write restores the row to its view and surfaces the error.
- Undo issues `decision: "pending"` and returns the book to the queue.
- The kid-facing surfaces render identically for pending, approved and rejected rows (§4.10).

## 8. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-9 Failure states = success states** — every state has a rendering and a way out (§4.2);
  failed books get a designed section rather than an omission (§4.8); each empty state is written
  separately and the caught-up one reads as success (§4.6).
- [x] **CC-4 Security** — one new endpoint behind two dependencies; unauthorized and nonexistent are
  indistinguishable; the policy surface shrinks by one policy and one grant (§4.4, §6).
- [x] **CC-5 Observability** — one log line per decision, with from-state and to-state. The only
  evidence that will ever exist for how the gate was used (§4.3).
- [x] **CC-6 Accessibility** — native `<dialog>` focus trap and `Esc`; tablist semantics; captions as
  image `alt`; `aria-live` on the pending count; a keyboard-reachable undo (§4.11).
- [x] **CC-8 Kid vs teacher design** — the deliberate split the kid-flow docket parked here. The
  teacher sees two failure readings; the child sees none, and no review state at all (§4.8, §4.10).
- [x] **CC-2 PII redaction** — flagged, not clean. §4.8 renders the child's **un-redacted**
  `input_text` for a `child_text` failure. Access is pre-existing (`0008:36`); this is the first
  screen to render it, and it is the correct audience — the responsible adult, on their own device.
- [ ] CC-3 Cost control — N/A. No decision spends money; a review creates no job (§4.8, invariant 11).
- [ ] CC-1 Moderation ordering — N/A. No pipeline path changes (§2).
- [ ] CC-7 Reproducibility — N/A.
- [ ] CC-10 Checkpointing — N/A. Review acts on terminal rows only.

## 9. Eval / quality checks

No new instrument. **CC-5's per-decision line is the only measurement of whether the gate works** —
how many books are rejected, how often a decision is undone, and how long a book waits between
`created_at` and its decision. That last number is the one that tells you whether per-book review
survives a real class of 40, and it is the evidence any future argument for bulk approval would have
to be made from.

## 10. Blast radius

| Owner | What it builds |
|---|---|
| `supabase/migrations/0011_jobs_rejected_at.sql` | The column, the CHECK, the revoke, the policy drop (§4.1, §4.4) |
| `backend/app/auth.py` | `owned_job`, beside `owned_classroom` (§4.3) |
| `backend/app/review.py` | The one endpoint (§4.3) |
| `frontend/app/classroom/[classroomId]/books/**` | The screen, tabs, dialog, failed section (§4.6–§4.8, §4.11) |
| `frontend/` — `TeacherShell` consumer | One tab, plus a client-side pending count (§4.9) |

**Docs changed in the same change as this spec:**

| File | Change |
|---|---|
| `docs/specs/teacher-dashboard-docket.md` | S3 → DONE with its constraints; amendments recording §4.4's changes to S1-7 and S3-8 |
| `docs/product/adr/` + the `docs/product/ADRs.md` index | The `0011` ADR (`AGENTS.md` §2) as its own file plus an index row, covering the column, the CHECK, and the revoke |
| `docs/product/DECISION_BACKLOG.md` | `classroom-sharing` gains §4.10 as an inherited constraint |
| `docs/specs/ROUTE_MAP.md` | `/classroom/[classroomId]/books` reconciled — this route only (S4-9) |

**Not touched:** the pipeline, `backend/contracts/`, `run_job.py`, and every kid-facing screen.

## 11. The migration number

**`0011`.** S1 claimed `0009`, S2 claimed `0010`. Next free after this spec is `0012`.

## 12. Linked decisions & open questions

**Depends on:** ADR-017 (manual, always — the reason §4.7 has no bulk) · ADR-021 (display-only
gallery) · ADR-025 (D5's `failure_reason` shape and the dev-only `error`) · PRD §11.1 (approved *or
rejected*) · `ethics_and_safety.md` §4 · S1-4, S1-5, S1-6, S1-7 · S2-1, S2-5, S2-6, S2-7, S2-8 ·
S3-4, S3-6, S3-7, S3-8, S4-4, S4-8 · kid-flow failure semantics §4.2, §4.10.

**Takes one schema decision, and flags it:** `0011` is ADR-flagged and not implementable until the ADR
is accepted, on the same footing as `0009` (S1-8) and `0010` (S2-11). It adds a column, a CHECK, and —
more consequentially — removes a grant and a policy that two frozen constraints describe (§4.4).

**Open:**
- **Per-book review is unvalidated against a real class of 40.** §4.7 argues the friction is the
  feature and §4.9's timing data is what would prove or disprove it. If the evidence says teachers
  cannot finish a pass, the honest response is ADR-017's Future Work path behind an ethics re-review —
  not a select-all added quietly.
- **The dialog's advance order is `created_at` desc,** which means the newest book is reviewed first
  and the child who has waited longest waits longest. Oldest-first is arguably fairer. Left as newest-
  first because after a single lesson the whole queue is minutes wide; revisit if books accumulate
  across days.
- **Nothing records *why* a book was rejected.** A reason field would help a teacher remember and
  would be real evidence about what the gate catches — and it is also a place to write something about
  a child that the child cannot see. Not opened here; it would need its own ethics pass.
  *Partly answered by §14 (2026-10-29): a note the child **can** read is opened. A private reason the
  child cannot read stays closed (§14.9).*
- **`AGENTS.md:454` is still stale** (S1's parked finding). Not this spec's to fix.

## 13. Definition of done

1. `0011` ships the column, the CHECK, the revoke and the policy drop, behind an accepted ADR.
2. `owned_job` exists in `app/auth.py` on `owned_classroom`'s pattern and fails `404`.
3. `POST /jobs/{id}/review` handles all six transitions, is idempotent, and logs one line per change.
4. The screen ships four views with four distinct empty states, an advancing `<dialog>`, and Undo.
5. Failed books render two readings with *machine* as the default for everything unknown.
6. Every kid-facing surface renders identically for all three review states. *Amended by §14: no
   kid-facing surface shows a verdict word; the download line and the note badge are the named
   exceptions.*

**Not done** if: both timestamps can be set at once; a teacher can reach a state they cannot leave; a
client can supply a timestamp; a `404` and a `403` are distinguishable; `authenticated` retains UPDATE
on `jobs`; an unknown `failure_reason` blames a child to anyone; a moderation category, flagged span
or `jobs.error` reaches a screen; a child learns their book was rejected; any bulk decision exists; or
the review queue's empty state reads as absence rather than as finished.

## 14. Amendment: teacher notes the child can read (2026-10-29, draft)

**Status:** implemented: schema and teacher API (ticket 05, 2026-10-29). ADR-081 accepted by the owner on 2026-10-29; OD-8 settled. Settings, note UI and child endpoints remain pending. Seams and defaults confirmed 2026-10-29. **Source:**
`.scratch/ptd-review-feedback/` (audit 01 with its owner verdict, grill 02), phase map
`.scratch/post-technical-defense/map.md` rank 3. **Rationale:** ADR-081 (accepted 2026-10-29).

Verified existing behavior this amends: the teacher sees Approve and Reject and the child sees no
verdict (§4.10); `jobs` stores two timestamps and no reason (§4.1); a child's browser already receives
both (`useJob.ts:69`, `0008:24`); the book page already says "Your teacher needs to approve this book
before you can download it" (`book/[jobId]/page.tsx:340-345`, pinned by `page.test.tsx:113,186`), which
contradicts §4.10 (DECISION_BACKLOG D-V).

### 14.1 Purpose and scope

A teacher can send one short note to the child who owns a book. The child finds it from the bookshelf
and reads it beside the book. No verdict word is ever shown to a child. Teachers see gentler labels.
The panel's complaint was that "Reject" sounds harsh and a child gets no feedback.

**In:** table `job_review_notes`; teacher note endpoints; child read endpoint; teacher note UI in the
review dialog; bookshelf badge and book-page panel; reworded download line; relabeled decision
buttons; per-classroom switch `review_notes_enabled`, off by default; amending §4.10, invariants 9 and
12, and §13.6.

**Out (each a later ticket or a no-go):** highlights and tooltips (sentence-level, anchored by
`scene_id` plus sentence index; the table already carries nullable `scene_id` and `anchor`); "Make a
new version" (a paid run, N2); private teacher notes; child replies (rank 4's gate); the child editing
page text (breaks immutable `pages` and ADR-013); a note column on `jobs` (classmates and researchers
read the whole row, `0008:28,46`); redaction and a preview step; email or push.

**Acceptance journeys.**
- J1. A teacher presses "Not ready to share yet"; the note box opens; they type and Send. The child
  opens their bookshelf, sees the badge, opens the book, reads the note, closes it. The badge is gone
  on the next visit.
- J2. A teacher shares a book ("Share with class") and adds praise. The child reads it the same way.
- J3. The teacher edits the note, then deletes it. The child sees the new text, then no badge and no
  panel, with no explanation.

### 14.2 User stories and acceptance criteria

**US-01. As a teacher, I want to add a note to a child's book without slowing my review pass, so that
I can say what to change or what I liked.** Applies: SH-02, SH-03, SH-05, SH-06
- AC-01. When the switch is on, the review dialog shows a collapsed row "Add a note for [nickname]"
  (native `<details>`) on every `complete` book, in any review state.
- AC-02. Opening the row shows a labeled text box (placeholder "Something kind and specific…") and a
  Send button. A line under the box says the child reads the note. Approve and Reject work without
  touching it.
- AC-03. Pressing "Not ready to share yet" opens the row. It does not require a note and does not
  block the dialog advancing (§4.7).
- AC-04. Send stores the note and shows it as sent in the row. The row then offers Edit and Delete.
- AC-05. A book has at most one note. Sending again edits it. Edit and Delete are one tap from the
  row. Delete asks no confirmation. After Delete the row is empty and a new note can be written.
- AC-06. An empty, whitespace-only or over-500-character body is refused by the endpoint with `422`,
  and the Send button is disabled while the box is empty.
- AC-07. A failed send keeps the typed text and shows the error in an `aria-live="polite"` region.
- AC-08. A `failed`, `queued`, `running` or `awaiting_confirm` book offers no note row (§4.8).

**US-02. As a teacher, I want kinder decision labels, so that the screen does not say "reject" about a
child's story.** Applies: SH-04
- AC-09. The two decision buttons read "Share with class" and "Not ready to share yet". Their API
  values stay `approved` and `rejected`. `pending` and Undo are unchanged.
- AC-10. The ADR-072 download explanation (§4.7) stays beside "Share with class".

**US-03. As a child, I want to find and read my teacher's note, so that I know what they said about my
book.** Applies: SH-01, SH-02, SH-05, SH-07
- AC-11. When the switch is on and the book has a note the child has not opened, its bookshelf card
  shows a badge reading "A note from your teacher".
- AC-12. Opening the book shows the note in a panel above the book, headed "A note from your teacher",
  with a "Close" button. Escape also closes it. The note can be reopened from the same control.
- AC-13. Opening the note sets `seen_at`. The badge no longer shows from the next bookshelf load. Editing
  the note clears `seen_at`.
- AC-14. The panel and badge never contain the words approved, rejected, pending or any verdict.
- AC-15. Classmates, the gallery and researchers have no path to a note.
- AC-16. If the child is offline or logged out when the note is sent, the badge appears on their next
  bookshelf load. No push or email.

**US-04. As a child, I want the download line to tell me what to do, so that I am not stuck.**
Applies: SH-01
- AC-17. Where the book page shows "Your teacher needs to approve this book before you can download
  it", it shows "Ask your teacher about downloading this book". The button stays disabled until the
  book is approved, exactly as today.

**US-05. As a teacher, I want to choose whether my class sees notes, so that I only get the note UI
when I use it.** Applies: SH-04
- AC-18. Classroom settings has a control "Let students read my notes", off by default.
- AC-19. When off, no note row appears in the dialog and no badge or panel appears for the class. Stored
  notes are kept.
- AC-20. The value is written only by the server, the way `0025` classroom settings are.

### 14.3 Shared behavior

- **SH-01 No verdict word.** No child surface shows approved, rejected or pending. The reworded download
  line and the note badge are the only review-related text a child reads. The child can still tell
  approved from not-approved through the disabled download button, as today. This replaces "the child
  is never shown a review state" (§4.10, invariant 9, §13.6).
- **SH-02 Close.** Every note panel closes by a "Close" button and by Escape, and returns focus to the
  control that opened it.
- **SH-03 Teacher note row states.** Loading: Send disabled. Empty: collapsed. Error: message in an
  `aria-live` region, text kept. Switch off: the row is not rendered.
- **SH-04 API values.** Relabeling changes no API value, schema or log field (§4.3, CC-5).
- **SH-05 Private reads.** `job_review_notes` is readable only through server endpoints that check
  ownership: the teacher via `owned_job`, the child by `jobs.profile_id`. Not through RLS.
- **SH-06 Accessible names.** The note row, text box, Send, Edit and Delete have accessible names that
  include the child's nickname where useful. Controls are native elements.
- **SH-07 Badge is not an absence badge.** It shows only when a note exists. A book without a badge
  says nothing (honors §4.10's ban on absence signals).

### 14.4 Edge cases

| Case | Expected behavior | Home |
|---|---|---|
| Book deleted while a note exists | Note rows go with the book (`on delete cascade`). Nothing added to the four-store cleanup, to be confirmed against `storybook-deletion.md` §1 | §14.5, OD-5 |
| Teacher Undoes a decision after the child read the note | Note stays. It is tied to the book, not the decision | AC-05, SH-01 |
| Teacher moves a shared book back to "Not ready to share yet" after the child saw the note | Same. No note text depends on the state | SH-01 |
| Teacher deletes the note after the child read it | Badge and panel disappear with no explanation | J3, AC-05 |
| Teacher edits the note after the child opened it | Child sees the current text and the badge returns (`seen_at` cleared) | OD-2 |
| Switch turned off while notes exist | Child view hides them. Rows are kept | OD-3 |
| Child offline or logged out | Badge on next bookshelf load | AC-16 |
| Teacher names another child in a note | Not redacted. Only the owner reads it. Accepted (Q8) | §14.5 |
| Teacher writes something about a child that the child should not read | There is no private kind. A line under the box says the child reads the note | OD-6 |
| Two tabs, same teacher, same book | Last write wins, as §4.12 | §4.12 |
| Book in another teacher's classroom | `404`, identical to a nonexistent job | §14.5 |
| Student or researcher token on a teacher note endpoint | Rejected before the handler (`require_teacher`) | §14.5 |
| A child requests another child's note | `404`, identical to none | §14.5 |
| Removed student's book | Teacher can still note it (§4.5). The child cannot sign in, so nothing is read | §4.5 |
| Non-`complete` book | No note row | AC-08 |
| Dialog advances (§4.7) with the note row open | Row collapses for the next book. An unsent draft is discarded without a warning | OD-4 |
| Maximum note length | 500 characters, `422` beyond it | OD-1 |
| Screen reader or keyboard only | Native `<details>`, labels, `aria-live` errors, focus returns on close | SH-02, SH-03, SH-06 |

### 14.5 Design decisions and rationale

- **Table `job_review_notes`, not a `jobs` column.** `students read approved peer jobs` and
  `researchers read approved jobs` select the whole row, so any new `jobs` column leaks to classmates
  once a book is approved (*measured*, `0008:28,46`). Precedent for a private service-role table:
  `job_moderation_reviews` (`0022`): RLS on, `revoke all` from `authenticated`, reached through FastAPI.
- **Columns:** `id`, `job_id` (cascade), `author_id`, `body`, `scene_id` and `anchor` (nullable, unused
  until highlights), `seen_at`, `created_at`, `updated_at`. One row per book for now, unique on `job_id`
  where `scene_id is null`. The audit's `withdrawn_at` is dropped, since Delete removes the row.
- **Migration `0026`** (next free after `0025`). It adds the table and `classrooms.review_notes_enabled
  boolean not null default false`, following `0025`: classroom columns are browser-readable and
  server-written only. ADR-flagged (`AGENTS.md` §2): ADR-081, accepted 2026-10-29.
- **Endpoints (proposed shapes, final paths belong to the build ticket):** teacher `PUT`, `DELETE` and
  `GET` on a job's note behind `require_teacher` and `owned_job`; child `GET` returning only the
  caller's own notes and a call to mark one seen. Child reads check `jobs.profile_id` against the
  signed-in student. Every miss is the same `404`.
  **Implemented teacher paths:** `GET/PUT/DELETE /teacher/jobs/{job_id}/note`. GET and PUT return the
  note row; DELETE returns `204`. Missing notes and jobs use `404 {"detail":"not found"}`.
  PUT validates the untrimmed body (1–500 characters, nonblank), takes the author from the session,
  and requires a complete book. Reads are not cached. A service-only, security-invoker RPC
  `teacher_review_note` locks the book and classroom, reads the switch on every call, and uses the
  partial-index predicate for an atomic upsert. Edits preserve `id` and `created_at`, update
  `updated_at`, and clear `seen_at`. Disabled writes return `409 notes_disabled`; teacher GET still
  returns the stored note. Missing notes on DELETE return the same `404` as GET.
- **The switch is read server-side** on every note read and write, so a stale browser cannot bypass it.
- **No redaction (Q8).** The read path is owner-only, so a child's own name in their note is correct,
  and Presidio would turn it into a placeholder. *Inferred* cost: a teacher naming a different child.
- **One note, edit in place (Q7).** No history. The simplest model that matches what a teacher does.
- **The note box sits outside the decision (Q6).** The fast pass stays two taps (§4.7). It opens after
  "Not ready to share yet" because that is when a teacher most wants to explain.
- **The badge clears (Q9).** A badge that never clears becomes noise. It costs one `seen_at` column.
- **The download line is reworded, not removed (Q2).** A disabled button with no text is a dead end.
  The new line carries no decision.
- **Structure:** follows the existing pattern: a backend module beside `app/review.py`, dependencies in
  `app/auth.py`, teacher UI under `books/**`, child UI in the existing bookshelf and book page. No new
  framework. The exact module layout is the build ticket's, under `AGENTS.md`.
- **Rationale not recorded:** the 500-character cap (OD-1) was accepted as proposed, with no stated reason.

### 14.6 Invariants added

13. A child sees a teacher note only if it is theirs, it exists, and the classroom switch is on.
14. No `jobs` column holds teacher-authored text.
15. No role other than the owning teacher and the owning child can read a note. No researcher or export
    path exists.
16. A note is deleted with its book.

### 14.7 Verification

**Confirmed seams (owner, 2026-10-29):**
1. Backend HTTP behavior through the FastAPI test client in `backend/tests/test_review.py` or a sibling
   `test_review_notes.py`: auth, ownership, `404` parity, `422`, one note per book, owner-only child
   read, `seen_at`.
2. Privilege checks in `backend/tests/test_rls_isolation.py`: `authenticated` and anon have no access
   to `job_review_notes`; `0008` policies still return the same rows.
3. Frontend page tests in the existing files: `books/page.test.tsx` (note row, relabel, auto-open after
   "Not ready to share yet", advance), `s/[profileId]/page.test.tsx` (badge), `book/[jobId]/page.test.tsx`
   (panel, Escape, download line; replace the pinned strings at `:113,186`).
4. One real-browser pass per journey J1 to J3 on seeded synthetic jobs, console clean. Cost $0.

**Required checks.** Expected values are hand-worked literals. Each test is run red first by breaking
what it covers. Mock only at the network boundary.
- A note by a teacher in another classroom returns `404`, identical to a nonexistent job.
- A classmate, a researcher and a signed-out caller get no note, and the `authenticated` role cannot
  select the table.
- A second send edits the same row. Delete removes it. An empty body returns `422`.
- With the switch off, the child endpoint returns none and the dialog shows no row.
- Opening the note sets `seen_at`, and the next list omits the badge.
- No child surface renders approved, rejected or pending text for any of the three states.

**Ticket 05 verification (2026-10-29):** teacher HTTP checks and real local PostgreSQL privilege,
lifecycle, cascade and concurrent-write checks run in `test_review_notes.py` and
`test_rls_isolation.py`. The unchanged HEAD RLS suite reproduces nine existing failures caused by
old approval-grant expectations and invalid profile fixtures. Child, settings and browser journeys
remain un-run in this slice. The full backend run also encounters six PDF failures because this
Windows runtime lacks WeasyPrint's native libraries. No remote migration was applied.

### 14.8 Blast radius

New: migration `0026`, ADR-081 and its index row, a backend notes module, the note row, badge and panel.
Changed: `books/**`, the bookshelf page, the book page, classroom settings. More than three modules, so
the `AGENTS.md` §2 gate applies to the build tickets. Pipeline, contracts and `run_job.py` are untouched.

Docs to change with the build: this spec, `DECISION_BACKLOG.md` (D-V closed), `classroom-sharing`
(inherits SH-07), `ROUTE_MAP.md` only if a route is added.

### 14.9 Rejected alternatives

Private teacher notes (a place to write about a child that the child cannot read; §12 flagged it);
several notes per book now (highlights will need them); a verdict badge ("Shared with class"); redaction
with a preview; a note column on `jobs`; the note as the book's last page.

### 14.10 Open decisions, readiness and sources

**Readiness: Ready for build tickets.** OD-8 is settled. Owner acceptance of ADR-081 on 2026-10-29 satisfies the ADR prerequisite for migration `0026`. OD-9 remains a release gate.

| ID | Open decision | Blocks |
|---|---|---|
| OD-1 | **Settled:** 500 characters, enforced by the endpoint (`422`). | AC-06 |
| OD-2 | **Settled:** editing clears `seen_at`, so the badge returns. | AC-13, J3 |
| OD-3 | **Settled:** rows are kept and hidden while the switch is off. | AC-19 |
| OD-4 | **Settled:** no warning. The unsent draft is discarded when the dialog advances. | AC-03, §4.7 |
| OD-5 | **Checked in text:** `storybook-deletion.md` §1 deletes the `jobs` row last, so the cascade covers notes (*inferred*, as ADR-080 did for `0022`). The build ticket adds a test that deleting a book removes its note. | Build ticket test |
| OD-6 | **Settled:** a line under the box says the child reads the note. | AC-02 |
| OD-7 | **Settled:** the four seams in §14.7. | — |
| OD-8 | **Settled (owner, 2026-10-29):** tabs and state badges mirror the buttons, "Shared with class" and "Not ready yet". The toast reads "Shared" or "Marked not ready", and Undo is unchanged. | AC-09 |
| OD-11 | **Settled (owner, 2026-10-29):** with the switch off, teacher note writes return `409 notes_disabled` and the teacher's `GET` still returns the note. Child reads return none. | AC-19, §14.5 |
| OD-9 | Ethics re-review is a rollout step before real children see a note. Owner: not a design input. | Release, not build |
| OD-10 | Child "Make a new version" (N2): the finished-book entry point is unchecked, and each run is paid. | Later ticket |

**Sources:** audit 01 (`## Answer`, owner verdict 2026-10-29); grill 02 decisions Q1 to Q10 and the
three additions (auto-open after "Not ready to share yet", `seen_at`, edit and delete); map decision 6;
this spec §4.10, §12, §13; DECISION_BACKLOG D-V.

### 14.11 Coverage index

| Source requirement | Home |
|---|---|
| Q1 per-classroom switch, off by default | US-05, AC-18 to AC-20, OD-3 |
| Q2 reword download line, amend §4.10 | US-04, AC-17, SH-01 |
| Q3 child notes only | §14.1 out, §14.9 |
| Q4 N2 later | §14.1 out, OD-10 |
| Q5 any book, badge | AC-01, AC-11, SH-07 |
| Q6 collapsed row, independent, opens after "Not ready" | AC-01 to AC-03 |
| Q7 one note, edit, delete | AC-04, AC-05 |
| Q8 no redaction | §14.5, edge table |
| Q9 badge, panel above book, close, clears | AC-11 to AC-13, SH-02 |
| Q10 wording and retention | AC-02, AC-09, AC-12, invariant 16 |
| W2 labels, API unchanged | US-02, SH-04 |
| Offline child | AC-16 |
| Highlights later | §14.1 out |
| Ethics re-review | OD-9 |
