# 09 — Teacher requests a replacement picture within budget

**Status:** implemented — browser/hosted verification pending
**Type:** task
**Progress:** resolved — synthetic-only, feature-off build
**Blocked by:** None — predecessor 07 is implemented.
**Conflict gate:** ADR-011, ADR-025 D4 (image budget), `AGENTS.md` child-safety rules.
Discussion permission is recorded in the map; ADR-080 and the synthetic-only, feature-off build scope were accepted on 2026-10-27.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md)
**What to build:** For a held scene picture, the teacher requests a replacement. It is drawn within
the existing image budget, preserving scene intent, approved references and style. It receives
fresh moderation and consistency checks; selection uses established limits and a safety flag
holds the exact candidate. With the budget exhausted, replacement is disabled with an explanation.
**Source criteria:** US-05 AC-12; SH-02, SH-07, SH-08, SH-11; J-02; §9.4 rows: replacement passes or
flags, budget exhausted, old decision after replacement, provider refuses before an image exists.
**Scope:** Replace command; one paid draw guarded by `check_image_budget`; moderation of the new
candidate and fresh scene-consistency judgment; new hold on flag; teacher disabled/explained state.
**Out of scope:** Custom appearance instructions or child-directed redraws (rank 4); extra budget;
generic safety-softened prompts; automatic extra image retries or new attempt budget.
**Complexity:** High — idempotent paid continuation and fresh-candidate routing under §9.9.4.
**Blast radius:** Shared — output_mod/generation path, budget accounting, teacher UI.
**Unblocks:** 10

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

Initial Q9: replacement protects progress without creative controls. Resumed Q17/Q18 select
same-intent generation rather than `_soften_prompt`, and a fresh scene-consistency judgment
(#78 shows the current soften retry skips it). §9.9.4 now proposes the exact routing/selection,
one existing moderation-redraw slot, fresh-only judgment/finalization and honest refusal failure.

## Read first

- `backend/pipeline/output_mod.py` — `output_mod` retry branch: `generate_and_store`, `referenced_characters` (issue #23), `passed=False` attempt record.
- `backend/app/config.py` — `check_image_budget`, image limits.
- `docs/specs/moderation-stack.md` §4c — #78 unjudged retry note.
- `docs/specs/self-refusal-fallback.md` — provider refusal handling.

## Behavior this changes

Extends the implemented scene hold/allow path with the accepted one-picture replacement.

## Acceptance criteria

- [x] Replacement draws at most one image per request, guarded by `check_image_budget` before spend (AC-12, SH-07).
- [x] Preserve scene intent, approved references and style; no generic safety-softening or custom instructions (AC-12).
- [x] Moderate the replacement; safety flag → new hold on that exact candidate. A fresh consistency
      judgment records its actual result and established selection/attempt limits apply; never
      silently reselect a rejected picture or grant extra draws (AC-12, OD-05).
- [x] A decision on the superseded candidate cannot release the replacement (SH-02).
- [x] Duplicate/lost requests produce one paid draw; ambiguous responses reconcile before retry (SH-07, SH-11).
- [x] Budget exhausted: replace disabled with an explanation; inspect, leave, allow and stop remain (AC-12).
- [x] `ref_paths` agree with the prompt's numbered image roll (issue #23 invariant).
- [x] Provider refusal before an image exists follows OD-05's recovery; no picture is invented.

## Guidance

Trap: today's retry attempt is recorded `passed=False` because no consistency judge runs. The new
path needs the replacement's actual judgment, never an inherited verdict. Follow §9.9.4:
`moderation_replace → consistency_check → output_mod`, fresh replacement only, no additional
consistency retry, no old rejected winner. Safety-cleared failing/unchecked consistency remains
honestly reported under the existing degraded-quality policy. The slot is spent after one draw;
another flag permits allow/stop, not a second replacement.

## Verification

Seam per §9.6 (accepted contract in §9.9.8). Main: J-02 pass and re-flag variants with mocked fal and classifiers.
Failure: budget at limit → no fal call, disabled control with explanation.
**Targeted:** `cd backend && uv run pytest tests/test_output_mod_node.py tests/test_run_job.py`
**Full suite:** required now (Shared).

## Blocked by

None — predecessor 07 is implemented. Hosted/release gates remain separate.

Design/conflict acceptance is settled in ADR-080. No repeat owner verdict is required for the
accepted synthetic-only, feature-off scope. Audit/calibration and real-child release gates remain.

## Comments

## Answer

The accepted scene replacement is implemented through the existing durable teacher decision and
worker continuation. One budget-guarded same-intent draw receives its own consistency and safety
checks. A second flag holds the exact fresh candidate with no second replacement. Budget/slot
explanations and same-request recovery reuse the existing teacher inspection surface.
See [moderation-stack §9.15](../../../docs/specs/moderation-stack.md#915-ticket-09-implementation-2026-10-28)
for behavior, commands, results and verification limits. Standards and Spec re-reviews have no
unresolved findings. Browser/hosted verification, paid providers and real-child release remain
unrun. Intake stays disabled by default.
