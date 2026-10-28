# 08 — Teacher or child stops a held story without deleting the writing

**Status:** implemented — synthetic-only, feature off; browser/hosted checks pending
**Type:** task
**Progress:** implemented
**Predecessor:** `.scratch/ptd-moderation-calibration/issues/06-teacher-inspects-held-story.md` (implemented)
**Conflict gate:** ADR-011, `AGENTS.md` child-safety rules, teacher-review-and-approval invariants.
Discussion permission is recorded in the map; ADR-080 and the synthetic-only, feature-off build scope were accepted on 2026-10-27.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md)
**What to build:** The classroom teacher or child author can **Stop this story** while it is held.
It asks for confirmation. Cancel leaves the hold unchanged.
Confirm ends the run without deleting the writing; the child sees neutral stopped-story copy, can go
back to the bookshelf and reuse the writing through the existing new-submission flow.
**Source criteria:** US-05 AC-13; SH-02, SH-04, SH-05, SH-08, SH-11; J-03; §9.4 rows: cancel/confirm
stop, attempt to reopen, child stop racing teacher release.
**Scope:** Stop command (teacher/child authorized, exact subject); confirmation dialog; ended-run state; child
stopped view and bookshelf entry; reuse-writing route into the existing submission flow.
**Out of scope:** Teacher reopen (not agreed); carrying pictures into a new submission; teacher
comments or revision cycle (rank 3); cancellation of actively running generation.
**Complexity:** Medium — confirmation, terminal state and child recovery on known flows.
**Blast radius:** Shared — job lifecycle, teacher Books, child bookshelf/process page.
**Unblocks:** 10, 11

## Accepted design handoff (2026-10-27)

[moderation-stack §9.9](../../../docs/specs/moderation-stack.md#99-technical-completion-proposal-2026-10-27)
defines the accepted fields, statuses, commands, routes, private delivery, lifecycle, UX and
verification. [ADR-080](../../../docs/product/adr/ADR-080-teacher-held-moderation-and-exact-content-clearance.md)
is **Accepted**. The owner explicitly said “accept all” to the concrete design and the
synthetic-only, feature-off build exception while audit 01 remains open. Do not request the same
conflict verdict or design acceptance again. Ticket 02 is complete as a specification handoff.

Implementation is authorized in predecessor-ticket order, using synthetic data with the feature
disabled by default. Audit 01 remains open. Changed classifier prompts, paid replay, production
enablement and real-child use are not authorized by this acceptance. Educator/ethics/consent and
hosted verification gates remain before real-child enablement. No implementation is claimed here.

## Context

Initial Q18 and resumed Q15: stop ends a run, not the writing; the child author can now stop a held
run as well as the teacher. Leaving keeps waiting. Confirmed deletion is separate. Final child copy, the reuse-writing affordance and
navigation-failure behavior are OD-07; held-state deletion compatibility is OD-08.

## Read first

- `frontend/app/classroom/[classroomId]/books/page.tsx` — existing undo/confirm patterns (`handleUndo`).
- `frontend/components/FailureScreen.tsx` and `FailureScreen.test.tsx` — current child failure copy.
- `frontend/app/s/[profileId]/page.tsx` — `BookshelfPage`, `BookCard` states.
- `backend/app/main.py` — `POST /storybooks` (the existing new-submission path) and job status writes.
- `docs/specs/kid-flow-failure-semantics.md` — child failure semantics.

## Behavior this changes

None asserted today; held runs do not exist before 05.

## Acceptance criteria

- [x] Stop requires confirmation; Cancel/Escape changes nothing and restores focus (AC-13, SH-08).
- [x] Confirm ends the run; no further paid generation; writing is not deleted; existing lifecycle applies (AC-13, SH-04).
- [x] Ownership rechecked; a stale or duplicate stop yields one outcome (SH-02).
- [x] Child stop and teacher release racing reconcile to one current state; no blind resume or
      duplicate paid work. Stop remains distinct from leaving and confirmed deletion (AC-13).
- [x] Child sees neutral stopped-story copy, no category or reasoning, a bookshelf exit, and a route to
      reuse the writing in a new submission (AC-13, SH-05).
- [x] A stopped run cannot be reopened by the teacher (§9.4).
- [x] Failure of the stop request keeps context and offers retry/reconcile (SH-11).

## Guidance

Use §9.9.3's confirmed stop command and §9.9.7's child copy/sessionStorage draft handoff with
copy-writing recovery. First committed stop/allow wins; a stale child stop cannot cancel a
now-running story. §9.9.5 specifies ADR-044 held/stopped compatibility without assigning this
slice the previously unbuilt general deletion feature. No teacher revision workflow.

## Verification

Seam per §9.6 (accepted contract in §9.9.8). Main: J-03 cancel then confirm. Failure: stop request fails →
hold unchanged, teacher sees error with retry. Browser check of child stopped view at phone width.
**Targeted:** `cd backend && uv run pytest tests/test_main.py`; `cd frontend && pnpm test app/classroom components/FailureScreen app/s`
**Full suite:** required now (Shared).

## Predecessor

`.scratch/ptd-moderation-calibration/issues/06-teacher-inspects-held-story.md`

Design/conflict acceptance is settled in ADR-080. No repeat owner verdict is required for the
accepted synthetic-only, feature-off scope. Audit/calibration and real-child release gates remain.

## Comments

Implemented against the accepted §9.9 contract. Ticket 06's predecessor implementation is
present. Teacher/active-author stop shares the locked job transaction, advances the epoch once,
records an immutable decision and never dispatches a continuation. Writing remains intact.
The child can return to the bookshelf or transfer processed writing to the existing form,
confirming any draft replacement. Root-mounted cleanup removes handoffs on sign-out/access
loss even across reload. Storage/navigation failure preserves selectable writing and copy recovery.

Verification and remaining limits are recorded in moderation-stack §9.14. No feature enablement,
paid replay, classifier change, general deletion implementation or real-child release is included.
