# 14 — Teacher turns on optional classroom review themes

**Status:** implemented — verification and review in progress
**Type:** task
**Progress:** implementation built in the accepted synthetic-only, feature-off scope
**Blocked by:** None — ticket 05 is merged
**Conflict gate:** ADR-011, `AGENTS.md` child-safety rules. Discussion permission is recorded;
ADR-080 and the synthetic-only, feature-off build scope were accepted on 2026-10-27.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md)
**What to build:** A classroom setting with three switches — mild suspense/spooky settings;
non-graphic fighting, arguments or bullying; sadness, loss or separation — all off by default. An
enabled theme detected in the submitted text holds the story for review. Check text once and group
detected enabled themes into one review before paid generation. Settings are captured per submission.
**Source criteria:** US-06 AC-14, AC-15; SH-01, SH-06, SH-08, SH-10; §9.4 rows: multiple themes,
switch changes mid-run, emergency shared-policy change (OD-11, out).
**Scope:** Classroom setting UI with explanation that shared checks still apply; snapshot of settings
on each submission; one submitted-text check producing a grouped optional-origin hold before paid generation.
**Out of scope:** Free-text custom rules; lenient mode or alternative shared rubric; acceptance once
per submission (15); per-picture optional-theme screening; incident containment (OD-11).
**Complexity:** Medium — versioned settings snapshot and the structured detector defined in §9.9.7.
**Blast radius:** Shared — classroom settings, submission, moderation.
**Unblocks:** 15

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

Q12/Q14/Q15/Q20/Q21. Turning a theme off removes only that extra review; it never disables shared
safety, privacy or provider restrictions.

## Read first

- `frontend/app/classroom/[classroomId]/settings/page.tsx` and its `page.test.tsx` — existing classroom settings page.
- `backend/app/main.py` — `create_storybook`: where a submission snapshot would be captured.
- `backend/providers.py` — classifier prompts (where any theme detection would sit, OD-04).
- `.scratch/ptd-moderation-calibration/map.md` — Q14/Q15/Q20/Q21 decisions.

## Behavior this changes

Feature-mode intake captures classroom themes/version transactionally. The real graph checks
enabled themes once after shared text safety clears, then persists one optional-origin hold
before analysis or paid generation. Baseline intake and shared classifiers are unchanged.

## Acceptance criteria

- [x] Three named switches, all off by default; enabling one requests review, not rejection or an unsafe label (AC-14).
- [x] Turning a switch off explains that shared safety checks still apply (AC-15).
- [x] Each submission captures its settings; later changes affect new submissions only, never
      release a hold or start paid generation (AC-15, SH-06).
- [x] A theme hold is marked optional-origin, distinct from shared safety (SH-01).
- [x] Check submitted text once and group detected enabled themes into one review before paid
      image generation. No per-picture optional screening; shared image-safety checks remain (AC-14).
- [x] Setting changes show saved only after a durable write; failure keeps state with retry (SH-08, SH-11).

## Guidance

Use §9.9.7's three exact theme IDs/definitions, one structured detector and processed-story hash
identity; §9.9.2/9.9.3 defines persisted classroom settings and the owner-only PATCH contract.
All were accepted on 2026-10-27; implementation/verification remains. Detection is text-only, grouped once before paid generation.

## Verification

Main: J-04 first half — enable theme, new submission captures it, matching content holds as optional.
Failure: toggling during a hold leaves that hold and its settings unchanged.
**Targeted:** `cd backend && uv run pytest tests/test_main.py`; `cd frontend && pnpm test app/classroom`
**Full suite:** required now (Shared).

## Blocked by

None — predecessor 05 is merged. Grouped-theme acceptance remains ticket 15.

Design/conflict acceptance is settled in ADR-080. No repeat owner verdict is required for the
accepted synthetic-only, feature-off scope. Audit/calibration and real-child release gates remain.

## Comments
