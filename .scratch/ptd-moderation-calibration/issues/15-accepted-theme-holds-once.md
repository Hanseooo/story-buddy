# 15 — An accepted theme does not hold the same submission again

**Status:** implemented — browser/hosted verification pending
**Type:** task
**Progress:** resolved — accepted synthetic-only, feature-off scope built
**Blocked by:** None — 07 and 14 are implemented
**Conflict gate:** ADR-011. Discussion permission is recorded in the map; ADR-080 and the synthetic-only, feature-off build scope were accepted on 2026-10-27.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md)
**What to build:** The teacher accepts detected enabled themes in one grouped review of the
submitted text before paid generation. Acceptance covers those themes for the same unchanged
submission; do not screen optional themes again per picture. New shared-safety flags still hold.
**Source criteria:** US-05 AC-11; SH-01, SH-02, SH-06; J-04 second half; §9.4 rows: accepted theme
recurs, later scene gets new safety flag, multiple themes.
**Scope:** Recording grouped acceptance with its detected themes bound to the submission;
preventing repeat optional-origin holds for those themes.
**Out of scope:** Shared-safety suppression of any kind; acceptance carrying to a new submission.
**Complexity:** Medium — scoping rules across themes and submission identity.
**Blast radius:** Local — optional-theme hold path only.
**Unblocks:** None

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

Initial Q16 and resumed Q19: one grouped, submitted-text-only review before paid generation avoids
repeated per-page review. §9.9.2/9.9.7 now defines unchanged as the exact privacy-processed story
hash plus captured classroom settings version in the same job. Store grouped accepted IDs and
do not transfer them to a new submission or run the detector per picture.

## Read first

- Ticket 14's settings snapshot and optional-origin hold.
- Ticket 07's decision record.
- `.scratch/ptd-moderation-calibration/map.md` — Q16 decision.

## Behavior this changes

Teacher acceptance now records the grouped detected IDs in the same job's checkpoint and resumes
from the saved review. Exact processed-story hash, detection evidence and captured settings must
still match. Shared safety remains independent and every later picture is checked.

## Acceptance criteria

- [x] After acceptance, the same theme on later pages of the same unchanged submission does not hold (AC-11).
- [x] A shared-safety flag on a later page still holds its exact content (AC-11, SH-01).
- [x] Group all detected enabled themes in the review and record which were accepted. Acceptance
      never suppresses shared safety or carries to a new submission; no per-picture optional check (AC-14).
- [x] The acceptance is recorded with the submission's captured settings (SH-06).

## Guidance

None beyond OD-04's rules once decided.

## Verification

Main: J-04 — accept grouped themes before paid generation, then proceed without per-picture optional
checks or repeat holds. Failure: a shared-safety flag on a later scene still holds its exact content.
**Targeted:** the hold path's node and graph tests.
**Full suite:** at the batch gate.

## Blocked by

None — predecessor code is implemented. Browser/hosted checks remain release gates.

Design/conflict acceptance is settled in ADR-080. No repeat owner verdict is required for the
accepted synthetic-only, feature-off scope. Audit/calibration and real-child release gates remain.

## Comments

Implementation and fresh verification are recorded in moderation-stack §9.20. The feature remains
off by default. No changed classifier prompt, paid replay, hosted verification or real-child use.
