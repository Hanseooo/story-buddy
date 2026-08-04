# kid-flow-ui — session docket

> **Agent: read this before anything else.**
> This docket governs a multi-session design. You are working ONE session.
> - Do not widen scope past the current session's cluster, and do not
>   re-decompose it. If it should split, append an amendment — don't split it
>   in-session.
> - "Binding constraints" are decided. To challenge one, append a NEW session.
>   Never edit a DONE session.
> - Something real but outside this session's cluster: if it belongs to a later
>   session, add it to that session's open questions; otherwise one line under
>   `## Found & parked`. Never fix it. Never open a file or a tracker for it.
> - Stop at an approved spec. Do NOT continue to writing-plans or implementation.
> - To end the session, in this order: record the spec path, propose the
>   constraints it establishes, wait for the user to confirm them, write them in.
>   Only then set the session to DONE, and flip every session blocked on it to
>   READY. A session is not DONE until its constraints are confirmed.

**Goal:** the kid-facing flow — a multi-page book that something outside the LangGraph
checkpoint can read, the ADR-029 character reveal, what happens when it goes wrong, and the
reader/wait states the child actually sees.

**Cut rationale:** clustered by which open questions constrain each other. "What a page row
is" and "who may read it" are one trust question, so persistence and access share S1 and go
first — everything downstream reads that shape. The pause lifecycle needs S1's trust boundary
before it can define a resume endpoint. Failure semantics needs the lifecycle's terminal states
before it can name behaviour for each. The reader renders what S1 stores and what S3 decided,
so it goes last.

**Spec path convention:** `docs/specs/kid-flow-<topic>.md` — flat, beside the specs it
sequences, per AGENTS.md ("one canonical location per artifact type", no new folders). This
docket itself lives at `docs/specs/kid-flow-ui-docket.md` for the same reason; the skill's
default `docs/dockets/` would have been a new top-level folder for one file.

**Roster note:** `MASTER_SPEC.md` §7 and `DECISION_BACKLOG.md` carry `kid-flow-ui` as a single
row. It becomes four specs. Update both rosters when the docket reaches `DONE` throughout —
not before, or the index will point at files that don't exist.

**Engine (writes the spec, exactly one per session):** `superpowers:brainstorming` — installed.
**Hardener (optional, after the engine, writes nothing):** `grilling` — installed. Run it on a
draft spec before the constraint extract, so constraints come off the final text.
`grill-with-docs` is not installed; skip it.

---

## Binding constraints

Decided in earlier sessions. Later sessions treat these as given, not open.

**From S1** (`docs/specs/kid-flow-book-persistence.md`, 2026-08-02):

1. **A book is `jobs.pages`** — an ordered JSONB array of `{scene_id, caption, image_path}` on the
   `jobs` row. Durable Storage paths only, never signed URLs. Array order is page order; there is
   no `page_index` field.
2. **One writer, one write.** `run_job.py` writes `pages` exactly once, atomically with
   `status='complete'`. `compose` stays pure and returns `{}`. No later session adds a second writer.
3. **Non-empty `pages` ⟺ a complete book exists.** Not-ready is a distinct state from empty.
4. **Access is capability-link: the job UUID is the capability** — the existing `jobs` policy plus
   the new `storage.objects` policy. `auth-and-classroom` replaces both in one migration. **No
   session adds a third policy surface.**
5. **Kid routes stay flat** (`/write`, `/process/[jobId]`, `/book/[jobId]`) until
   `auth-and-classroom`.
6. **Progress lives on `current_stage`; there is no progress column.** Progress writes never touch
   `pages`. S4 may make `current_stage` advance without an amendment.
7. **A book that cannot be fully read fails as a whole** (ADR-025). No partial render, no
   page-shaped holes.
8. **Migration `0004` is claimed** by S1's spec. Next free number is `0005`. *(Superseded by
   constraint 16 — S2 took `0005`; next free is `0006`.)*

**From S2** (`docs/specs/kid-flow-pause-lifecycle.md`, 2026-08-02):

9. **A pause is `status='awaiting_confirm'` + `jobs.reveal`** — a jsonb projection
   `{characters: [{char_id, name, image_path, chips}], taps_left}`, computed pure in `reveal.py`,
   carried as the `interrupt()` payload and written verbatim by the worker. Durable Storage paths only.
   **Consumers switch on `status`, never on the presence of `reveal`**; it is deliberately left stale
   on finished rows.
10. **One tail, one terminal write.** Both worker entrypoints converge on `_finish`, the only writer of
    `pages` *or* `reveal`. `resume_storybook_job` never constructs a `StoryMemory`. Constraint 2
    survives unchanged — no later session adds a second writer of either.
11. **`POST /jobs/{id}/confirm` is the only exit from a pause,** checked `404` → `422` (identity,
    per-character, against that row) → CAS on `awaiting_confirm`. Duplicate, late, finished or swept →
    **200 with the current status**, never an error. **A rejected payload or a failed enqueue never
    consumes the pause.**
12. **The 3-tap cap is enforced in `route_reveal`** — not the endpoint, not the UI.
    `cost.ref_retry_count` increments in `char_bible`'s targeted mode and counts only taps that bought
    a draw. A tap past the cap becomes a confirm.
13. **A redraw never reuses a Storage path.** References are `{story_id}/ref-{char_id}-{n}.png` from
    the first draw onward; superseded objects are left in place for `data-deletion` to sweep.
14. **A pause is entered only when at least one character has a reference, and every projected
    character offers at least one chip.** Both are what stop the pause from becoming a hang or a
    dead-ended button.
15. **A swept pause is not ADR-025 `failed`** and must not read to the child as their story breaking.
    `data-deletion` picks the terminal value and the TTL. A confirm against a swept job takes the same
    CAS-miss path as a double-confirm.
16. **Migration `0005` is claimed** by S2's spec; `job-failure-reason` moves to `0006`. **Still exactly
    two policy surfaces** (constraint 4 unchanged). `SUPER_STEP_PRELUDE = 15` is separate from
    `IMAGE_BUDGET`'s 9-**image** prelude.

**From S3** (`docs/specs/kid-flow-failure-semantics.md`, 2026-08-02):

17. **Three verbs, and only three** — `redraw` (S2's `POST /jobs/{id}/confirm`, same job), `revise`
    (the child edits their words, brand-new job), `retry` (the same text unchanged, brand-new job).
    No later session adds a fourth or renames these. A re-sign creates nothing and is not a verb.
18. **A terminal job is immutable.** Recovery is always a new job; a `failed` job's checkpoint is
    never resumed. Reopening that needs an ADR.
19. **One bit from `job-failure-reason`, defaulting away from blame.** Exactly one enum value means
    *the child's own text was rejected*; every other value, every unknown value, and `null` map to
    `retry`. It is written only where `moderation_router` raises for the input text
    (`passed is False` and not `moderation_error`). **That row is reopened** and is a build-order
    prerequisite for S4's screens.
20. **Four render buckets, and every URL-reachable surface handles all four** — in-flight
    (`queued`/`running`), paused (`awaiting_confirm`), terminal-success (`complete` + non-empty
    `pages`), terminal-failure (`failed` + the swept value). **`failed` is never not-ready.**
21. **The child is never shown a moderation category, a flagged span, or `jobs.error`.** The reason
    selects a screen and is never rendered as text; the teacher-facing reading is
    `teacher-dashboard`'s.
22. **The N=3 counter is client-side, reason-blind, counts presses that follow a `failed` job, and
    never gates.** `jobs.parent_job_id` is the named upgrade path.
23. **No new surface** — no migration, no endpoint, no contract change. **Still exactly two policy
    surfaces** (constraints 4 and 16 unchanged). Next free migration after `job-failure-reason`'s
    `0006` is `0007`.

**Pre-existing constraints from ADRs, not from this docket.** These are already frozen and are
listed so no session re-decides them:

- ADR-029 froze the reveal's shape: an effect-free `reveal` node holding one `interrupt()`, a
  pure `route_reveal`, `ReferenceRetry {char_id, attribute}` + `Cost.ref_retry_count` on
  `StoryMemory` (both defaulted → no `schema_version` bump), the 3-tap cap enforced **in the
  router, not only the UI**, CC-3 `prelude` = 9, and `awaiting_confirm` + `POST /jobs/{id}/confirm`
  as the lifecycle. Sessions design *around* this, never re-open it.
- ADR-025: a book is never delivered partial — a failure fails the whole job.
- ADR-013: a page is an image plus a **verbatim** caption.
- ADR-017 / ADR-021: no self-serve signup, no public sharing; the gallery is display-only.
- `contracts/` is frozen. A session that believes it needs a Story Memory change stops and
  says so (AGENTS.md "Architecture is locked") — it does not write one.

---

## Sessions

Statuses: DONE (spec linked **and** constraints confirmed) · PARTIAL (stopped early,
resumable) · READY · BLOCKED (needs Sn)

### S1 · Book persistence & access — DONE

**Spec:** `docs/specs/kid-flow-book-persistence.md` (2026-08-02) · constraints 1–8 above.

**Cluster:** what durably holds an N-page book and who may read it. What a page is as stored
data; whether it lives in a new table or a column on `jobs`; who writes it (the worker after
`invoke()`, or `compose`, which returns `{}` today); what happens to the existing single-scene
`jobs.caption` / `jobs.image_path` columns and their live readers; how N images become N
viewable URLs; what RLS the new surface carries given `0001_jobs_table.sql:18-21` is
`for select to anon using (true)`; whether the kid routes move to the `/s/[profileId]` tree
now or stay flat until `auth-and-classroom`; and whether per-scene progress (for S4's stepper)
is part of this same write or a separate concern.

**Explicitly out:** the pause lifecycle (S2), anything about failure behaviour (S3), anything
visual (S4), and the actual auth model — issuing accounts, sessions, classroom scoping — which
is `auth-and-classroom`'s. This session may *name the boundary* with that spec; it may not
design past it.

**Stance:** persistence session — done means a schema, a named owner for each write, and the
invariants the shape must never violate (including what stops an unreadable or half-written
book from being shown as complete).

**Open questions:** ⚠️ a storage-shape choice is a schema decision under AGENTS.md §2 — if the
session lands on one that is hard to reverse, it writes an ADR and flags it rather than
settling it inline. `export-pdf` is the other consumer of whatever this decides; design for two
readers, don't build for the second.

---

### S2 · Pause & resume lifecycle — DONE

**Spec:** `docs/specs/kid-flow-pause-lifecycle.md` (2026-08-02) · constraints 9–16 above.

**Cluster:** the job's life across a human-shaped pause. How the worker distinguishes "returned
with an interrupt pending" from "returned complete" and writes `awaiting_confirm`; the shape and
validation of the `POST /jobs/{id}/confirm` payload as a **trust boundary**; where the tappable
`attribute` chips come from (`CharacterDescription` fields, or something else); what a second
resume enqueued against the same `thread_id` does — double-tap, double-confirm, a resumed job
that was already resumed; what the child is shown when `ref_retry_count` hits the ADR-029 cap of
3; and a pause nobody ever confirms.

**Explicitly out:** the reveal *screen* (S4), what "try again with a different story" means
(S3 — a different thing that shares the words), and the `awaiting_confirm` sweep itself, which
`data-deletion` owns per ADR-029's ⚠️. This session says what a swept pause must mean to the
child; `data-deletion` picks the terminal status.

**Stance:** lifecycle session — done means every transition into and out of the pause is named,
including the ones a client can force by retrying, and each has a chosen behaviour.

**Open questions:** carried in from the cluster above; add here as they surface.

---

### S3 · Failure & retry semantics — DONE

**Spec:** `docs/specs/kid-flow-failure-semantics.md` (2026-08-02) · constraints 17–23 above.

**Cluster:** what the child can do when something goes wrong, and what each thing means.
**"Try again" is currently two different actions wearing one label** — ADR-029's redraw-this-
character tap, and the backlog's "try again with a different story" — and this session settles
the vocabulary before either is built. Which failures reach the child at all (moderation
rejection at the input gate, char-ref rejection, a job-level `failed`, the retry cap) and which
offer which action; whether a resubmit is a brand-new job or carries lineage to the old one; and
what, if anything, this session hands `repeated-failure-offramp`, which is blocked on exactly
this flow existing.

**Explicitly out:** how the failure screens *look* (S4), the `job-failure-reason` enum (its own
deferred row — this session may state what it would need, and must not build it), and any
cross-run counter or lineage column, which is a schema decision this session flags rather than
takes.

**Stance:** semantics session — done means every failure the child can reach has one named,
chosen action, and the two "try again"s have distinct names.

**Open questions:** carried in from the cluster above; add here as they surface.

- **From S2:** one of the two "try again"s is now built and named — the ADR-029 reference redraw,
  addressed by `char_id` + `attribute` against a paused job via `POST /jobs/{id}/confirm`. Whatever
  this session names the resubmit-a-different-story action, **it is not that endpoint**, and the
  vocabulary must keep the two apart.
- **From S2:** a swept pause needs a child-facing meaning that is not `failed` (constraint 15). This
  session may name what the child is shown; `data-deletion` still picks the status value.

---

### S4 · Reader & wait-state experience — DONE

**Spec:** `docs/specs/kid-flow-reader-and-wait-states.md` (2026-08-04) · Docket complete. `kid-flow-ui` now maps to four feature specs: S1 (book-persistence), S2 (pause-lifecycle), S3 (failure-semantics), S4 (reader-and-wait-states). Update MASTER_SPEC §7 accordingly.

**Cluster:** every state the child observes, rendered. The multi-page reader over whatever S1
stores (paging, controls, page position); the generation wait — a per-scene stepper driven by
Realtime, and what it shows when progress data is coarse; the reveal screen S2 defined a
lifecycle for; the failure screens S3 gave semantics to; and the ROUTE_MAP §8 open question
about landscape lock, which `screen.orientation.lock()` cannot deliver on iOS Safari.

**Explicitly out:** re-opening any data shape (S1), any lifecycle transition (S2), or what an
action means (S3). If a rendering seems to require changing one, that is an amendment, not an
in-session fix.

**Stance:** interaction session — done means every state the child can observe has a chosen
rendering, including the ones nobody wants to see. Per AGENTS.md, failure screens get the same
design care as success screens; a wait state is a state, not an absence of one.

**Open questions:** `DESIGN.md` and `USER_FLOW.md` §4/§6 already commit to a register
(cartoon-pop, Lottie, giant tap zones) — read them as input, not as decisions to re-derive.

- **From S2 (required, not optional):** any surface rendering the pause must seed from a `SELECT`
  and then subscribe. `/process/[jobId]` subscribes today with no initial fetch, so a child
  returning to a paused job sees nothing until the next UPDATE — which, at a pause, never comes.
- **From S2:** render *"use this one"* at `taps_left == 0` (ADR-029 — the button never dead-ends),
  and re-read the row after each resume so a stale chip list cannot surface a `422` to a child.
- **From S2:** the reveal screen renders constraint 9's projection as-is. It signs `image_path` at
  read time; it does not re-derive chips, and it never reads graph state.
- **From S3 (build order, not design):** the differentiated failure screens select on
  `job-failure-reason`, which is not built. S4 designs **both** screens regardless — because
  constraint 19's default is `retry`, only the *selector* waits on that row, so S4 does not stall.
- **From S3 (required):** constraint 20's four-bucket render applies to **every** URL-reachable
  surface, not only the reader. `book/[jobId]/page.tsx:61` currently renders a `failed` job as
  not-ready — an infinite wait state — and that is a regression test S4 owes.
- **From S3:** a complete book whose images will not sign re-signs in place before any failure
  screen; it never offers a rebuild for an expired URL (spec §4.7).
- **From S3:** the N=3 off-ramp counter lives in the flow, increments on press, and never gates
  (constraint 22). Where the suggestion appears is S4's; when it fires is not.

---

## Found & parked

Turned up mid-session, belongs to no session here. Recorded so it is not lost, and not this
docket's work.

- 2026-08-02 (from decomposition): `ROUTE_MAP.md` §1 documents a `/s/[profileId]/…` route tree;
  the built app is flat (`/write`, `/process/[jobId]`, `/book/[jobId]`). Whether that is drift or
  intended sequencing is S1's boundary question — noted here only so it is not mistaken for a
  discovery later. ✅ **Resolved by S1:** intended sequencing (binding constraint 5). S1's spec
  §11 adds the status note to `ROUTE_MAP.md` §1.
- 2026-08-02 (from S1): `docs/specs/plans/` holds four plans whose modules are all built —
  `2026-07-29-story-memory-contract`, `2026-08-02-regeneration-controller-part-1/-part-2`,
  `2026-08-02-moderation-stack`. AGENTS.md says plans are disposable and deleted once built +
  green + spec updated; that folder should hold only in-flight work. Not this docket's work.

## Amendments

- **2026-08-02 (from S3): `job-failure-reason` is reopened and becomes a prerequisite of S4's
  screens.** Its `DECISION_BACKLOG.md` deferral-watch row gave two reopen triggers —
  *"`teacher-dashboard` ships, **or** a Phase-2 failure needs naming."* S3's two-action vocabulary is
  the second clause: the child-facing screen needs one bit off the row to choose between "change your
  words" and "try again", and only that enum supplies it. S3 did **not** build it (the docket's
  Explicitly-out line holds); it states the one requirement in constraint 19 and hands the build to
  that row. This is a build-order dependency, not a design one — S4 is READY.
