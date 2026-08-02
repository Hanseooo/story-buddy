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
8. **Migration `0004` is claimed** by S1's spec. Next free number is `0005`.

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

### S2 · Pause & resume lifecycle — READY

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

### S3 · Failure & retry semantics — BLOCKED (needs S2)

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

---

### S4 · Reader & wait-state experience — BLOCKED (needs S3; S1 satisfied)

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

*(none yet)*
