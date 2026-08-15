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

| `failure_reason` | The teacher is told | Also shown |
|---|---|---|
| `child_text` | The safety check stopped this story. | The child's own `input_text` |
| `machine`, `null`, **or any value this spec has not heard of** | Something went wrong while this was being made. They can try again. | Nothing |

**The fail-safe default is preserved across the audience change.** Kid-flow §4.2 built
`failure_reason` so that exactly one value blames the child's writing and every other value — present
or future — falls to *machine*. That property is why the teacher's map is written as a default rather
than a list: a new enum value can never accidentally tell a teacher that a child wrote something
wrong. CC-8's "the teacher-facing view is deliberately a different answer" means *more* than the child
is told, not *differently safe*.

**Never rendered:** a moderation category, a flagged span, or `jobs.error`. This is not only policy —
it is also what is available. `graph.py:24-31` collapses everything to three raw strings
(`content_flagged`, `moderation_error`, `ref_flagged`); `mod.categories` lives in the LangGraph
checkpoint and is never written to `jobs`. `jobs.error` holds a raw exception string for machine
failures (provider text, assertion text, `GraphRecursionError`) and ADR-025 D5 marks it dev-only. It
is unfit for an adult UI for the same reason it is unfit for a child's.

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
10. **There is no bulk decision and no auto-approve** (§4.7, ADR-017).
11. **No fourth recovery verb.** The teacher cannot act on a child's failed book (§4.8).
12. **Reads stay in the browser under RLS; the only endpoint is a write** (S1-6, S2-7).

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
- **`AGENTS.md:454` is still stale** (S1's parked finding). Not this spec's to fix.

## 13. Definition of done

1. `0011` ships the column, the CHECK, the revoke and the policy drop, behind an accepted ADR.
2. `owned_job` exists in `app/auth.py` on `owned_classroom`'s pattern and fails `404`.
3. `POST /jobs/{id}/review` handles all six transitions, is idempotent, and logs one line per change.
4. The screen ships four views with four distinct empty states, an advancing `<dialog>`, and Undo.
5. Failed books render two readings with *machine* as the default for everything unknown.
6. Every kid-facing surface renders identically for all three review states.

**Not done** if: both timestamps can be set at once; a teacher can reach a state they cannot leave; a
client can supply a timestamp; a `404` and a `403` are distinguishable; `authenticated` retains UPDATE
on `jobs`; an unknown `failure_reason` blames a child to anyone; a moderation category, flagged span
or `jobs.error` reaches a screen; a child learns their book was rejected; any bulk decision exists; or
the review queue's empty state reads as absence rather than as finished.
