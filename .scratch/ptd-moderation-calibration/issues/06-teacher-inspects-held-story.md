# 06 — Teacher finds a held story in Needs your help and inspects it

**Status:** implemented — browser/hosted verification pending
**Type:** task
**Progress:** built in the accepted synthetic-only, feature-off scope
**Blocked by:** None — ticket 05 is merged.
**Conflict gate:** ADR-011, `AGENTS.md` child-safety rules, teacher-review-and-approval §4.8/§4.10.
Discussion permission is recorded in the map; ADR-080 and the synthetic-only, feature-off build scope were accepted on 2026-10-27.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md)
**What to build:** In classroom Books, a **Needs your help** queue lists held stories. Opening one
shows the privacy-processed title and story, available references and scene pictures, and the exact
held picture behind a warning with **Show picture to review**. Inspection changes nothing.
**Source criteria:** US-03 AC-05, AC-06, AC-07; SH-02 (inspection changes nothing, authority
recheck), SH-03, SH-08, SH-09; §9.4 rows on not-generated/unavailable pictures, empty queue, changed item.
**Scope:** Books queue tab/section, read of held-run context, inspection view with reveal, all
loading/empty/error/missing states, keyboard and phone behavior.
**Out of scope:** Decisions — allow (07), stop (08), replace (09). Criteria reference and per-hold
explanation (13). Comments/highlights (rank 3). Child surfaces (05).
**Complexity:** Medium — several states and a reveal control on an understood read path.
**Blast radius:** Shared — classroom Books page and a teacher read of held-run data.
**Unblocks:** 07, 08, 13

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
hosted verification gates remain before real-child enablement. Implementation and verification limits are recorded in moderation-stack §9.11.

## Context

Q17: held stories live in existing Books, not a moderation dashboard. Q19: flagged pictures are
hidden from teachers until an explicit reveal. `BookReviewDialog` assumes completed `job.pages` and
editorial `ReviewDecision`, so it is not a drop-in (§9.5); reuse reading presentation, not its
decision authority.

## Read first

- `frontend/app/classroom/[classroomId]/books/page.tsx` — `BooksPage` tabs, `FailedBookRow`, `EmptyState`, job select.
- `frontend/components/BookReviewDialog.tsx` — reading presentation and its completed-page assumptions.
- `frontend/app/classroom/[classroomId]/books/page.test.tsx` — Books test precedent.
- `docs/specs/teacher-review-and-approval.md` §4.8, §4.10, §5 — invariants this must amend narrowly.
- The hold representation landed by ticket 05.

## Behavior this changes

Teacher-review invariants on hidden review states (§9.5) — amended narrowly for safety holds once
OD-10's ADR drafts are accepted. Existing editorial tabs and tests stay unchanged.

## Acceptance criteria

- [x] Held stories appear in a distinct **Needs your help** queue, visibly separate from
      completed-book approval actions (AC-05, SH-09).
- [x] Inspection shows privacy-processed title/story and available pictures, including the exact
      held candidate; not-yet-generated vs unavailable/signing-failed are distinguished; no picture
      is generated to fill the view (AC-06).
- [x] The flagged picture starts hidden behind a warning; **Show picture to review** reveals it to
      the teacher only; reveal releases nothing (AC-07).
- [x] Ownership is rechecked on read; another classroom's teacher and the child cannot open it (SH-02).
- [x] Loading, queue-empty, missing content, service failure states with safe retry; an item that
      changed while open shows current state (SH-08, §9.4).
- [ ] Named controls, visible focus, keyboard activation; dialog closes on Escape and restores
      focus to the opener; actions reachable at phone width (SH-08).
- [x] Guarded authenticated, no-store image bytes per §9.9.5; private Storage remains signed
      internally, with no child-accessible flagged asset or original-PII text (SH-03).

## Guidance

Use §9.9.7's oldest-first order, one count per held job and unchanged editorial default tab.
Use §9.9.3's owner-only list/detail/reveal endpoints. Do not merge safety and editorial decisions.

## Verification

Precedent: `books/page.test.tsx`. Main: teacher opens a held synthetic story, reveals, closes with
Escape, focus returns. Failure: signing fails → picture marked unavailable, story still readable.
Browser at desktop and phone width, clean console; owner signs in.
**Targeted:** `cd frontend && pnpm test app/classroom`
**Full suite:** required now (Shared).

## Blocked by

None — ticket 05 is merged.

Design/conflict acceptance is settled in ADR-080. No repeat owner verdict is required for the
accepted synthetic-only, feature-off scope. Audit/calibration and real-child release gates remain.

## Comments
Implemented in moderation-stack §9.11. Named controls, Escape and connected/missing-opener
focus restoration pass component tests. The desktop/phone browser criterion remains unchecked:
the in-app browser is unavailable and browser inventory is empty. Hosted delivery and owner
sign-in verification are also unrun. Inspection creates no decisions or paid work.
