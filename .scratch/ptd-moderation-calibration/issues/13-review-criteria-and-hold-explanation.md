# 13 — Teacher sees the review criteria and why this story is held

**Status:** implemented — browser/hosted verification pending
**Type:** task
**Progress:** built in the accepted synthetic-only, feature-off scope
**Blocked by:** None — ticket 06 inspection code is implemented.
**Conflict gate:** ADR-011. Discussion permission is recorded in the map; ADR-080 and the synthetic-only, feature-off build scope were accepted on 2026-10-27.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md)
**What to build:** An accessible **Review criteria** reference that separates shared safety from
optional classroom themes, and on each held story the applicable criterion, its origin, the recorded
explanation and the submission's settings — or "unavailable" when nothing was recorded.
**Source criteria:** US-04 AC-08, AC-09; SH-01, SH-05, SH-06, SH-08; §9.4 row: reasoning unavailable.
**Scope:** Criteria reference page/panel reachable from Books; per-hold explanation in inspection;
recording of the classifier label/reasoning and settings at hold time (per OD-03).
**Out of scope:** Writing the rubric itself (OD-01); changing classifier prompts; child-facing
explanations (children never see categories).
**Complexity:** Medium — presentation plus versioned evidence recording.
**Blast radius:** Shared — moderation logging/recording and teacher UI.
**Unblocks:** 07 (required criteria reference)

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
hosted verification gates remain before real-child enablement. Implementation and verification
limits are recorded in moderation-stack §9.12.

## Context

Q13: teachers get both a general reference and a per-hold explanation. `_check_image` already
returns a classifier label and providers log `safety_reasoning` (§4c CC-5), but nothing is persisted
for a teacher to read. Today's configuration is not evidence of an older call (SH-06).

## Read first

- `backend/pipeline/output_mod.py` — `_check_image` labels.
- `backend/providers.py` — `classify_image_primary`, `classify_image_backstop`, text classifiers: what reasoning exists.
- `docs/specs/moderation-stack.md` §4c CC-5 note and §9.5 evidence.
- The inspection view from ticket 06.

## Behavior this changes

None.

## Acceptance criteria

- [x] **Review criteria** distinguishes shared safety from optional themes and shows scope,
      triggers, exceptions, boundary examples and basis from the accepted §9.9.6/9.9.7 proposal
      (AC-08), honestly labelled as project policy pending external validation where applicable.
- [x] Each hold shows criterion, shared-vs-optional origin, recorded explanation and captured
      settings; missing reasoning reads as unavailable, never invented (AC-09, SH-06).
- [x] Recorded model/settings come from the time of the call, never today's config (AC-09).
- [x] Reference is keyboard-reachable with an in-app close/back (SH-08).
- [x] Nothing here reaches child surfaces (SH-05).

## Guidance

Use the accepted definitions from §9.9.6/9.9.7, one data source in
`backend/app/moderation_policy.py`, and the authenticated criteria/detail projection in §9.9.3.
Do not invent another policy or imply school/ethics approval. This slice supplies the reference
required by ticket 07. Changed classifier instructions remain gated by audit 01 and separate
calibration authorization; a static criteria UI does not establish detection accuracy.

## Verification

Main: a held synthetic story shows recorded reasoning; a hold with none shows "unavailable".
Failure: config change after a hold does not change the shown model.
**Targeted:** `cd frontend && pnpm test app/classroom`; backend recording test in the gate's node test file.
**Full suite:** required now (Shared).

## Blocked by

None — ticket 06 inspection code is implemented. Its hosted/browser checks remain separate.

Design/conflict acceptance is settled in ADR-080. No repeat owner verdict is required for the
accepted synthetic-only, feature-off scope. Audit/calibration and real-child release gates remain.

## Comments

Implemented in moderation-stack §9.12. No classifier prompt, feature setting or real-child
enablement changed. Existing scene holds now retain privacy-processed classifier reasoning;
historical missing evidence stays unavailable. Review criteria are provisional project policy,
with the accepted shared-safety and optional-theme definitions kept distinct.

## Answer

Teacher criteria/detail reads and Books disclosure are implemented. Provider/node/graph and
disposable-Postgres integration checks pass. Frontend lint/build/typecheck and all 30 Books tests
pass. Full backend: 1,545 passed, 89 skipped, six deselected and the same six existing native
WeasyPrint/PDF failures as ticket 06. Frontend fork workers stalled; the threads run passed all
77 source test files and 735 tests. No source tests were removed or loosened. Browser inventory is empty and the in-app browser is
unavailable, so desktop/phone and hosted verification remain unrun. See §9.12 for boundaries.

Required Standards/Spec review agents both stopped at the account usage limit without findings.
Local review covered both axes instead; the stale audience string in the captured policy fixture
was corrected. No other local findings remain. Independent review was not completed.
