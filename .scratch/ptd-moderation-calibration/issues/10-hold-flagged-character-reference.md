# 10 — A flagged character reference holds for the teacher

**Status:** implemented — browser/hosted verification pending
**Type:** task
**Progress:** resolved — synthetic-only, feature-off build
**Blocked by:** None — predecessors 07–09 are implemented.
**Conflict gate:** ADR-011, ADR-003, `AGENTS.md` child-safety rules, `reference-moderation-retry.md`.
Discussion permission is recorded in the map; ADR-080 and the synthetic-only, feature-off build scope were accepted on 2026-10-27.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md)
**What to build:** With the setting on, the first flag on a character reference holds the run
instead of clearing it and redrawing. The teacher inspects the exact candidate and can allow,
replace or stop with the same rules as scene pictures.
**Source criteria:** US-01 AC-01 (reference); AC-06, AC-10, AC-12, AC-13 applied to references;
SH-01–SH-08; §9.4 rows: flagged reference path currently cleared, no characters/references.
**Scope:** `char_ref_mod` first-flag path; private retention of the flagged candidate; teacher
inspection shows references; allow/replace/stop wired for a reference subject.
**Out of scope:** Child appearance prompts (rank 4); changes to `reveal` choices.
**Complexity:** High — the flagged path is cleared today, and the skip-if-passed optimisation is a CC-1 hazard.
**Blast radius:** Shared — `char_ref_mod`, `char_bible` mint paths, `moderation_router`, teacher UI.
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

Today a flagged reference has `canonical_ref_image` cleared and `moderation_router` routes back to
`char_bible` for one redraw (`MAX_MOD_REDRAWS = 1`). AC-01 requires holding before that redraw, and
AC-06 requires the exact candidate to stay reviewable; §9.9.2/9.9.5 defines private immutable
retention and guarded review delivery. §9.9.4 defines the existing one-per-book replacement slot
and the no-reference-replacement rule after dependent scenes exist.

## Read first

- `backend/pipeline/char_ref_mod.py` — `char_ref_mod`: skip on `"passed"`, flag clears the ref, `MAX_MOD_REDRAWS`.
- `backend/pipeline/graph.py` — `moderation_router`: char-ref branch back to `char_bible`.
- `backend/pipeline/char_bible.py` — targeted and untargeted mint paths that clear `ref_moderation_status`.
- `docs/specs/moderation-stack.md` §4b — CC-1 warning on a third write path to `canonical_ref_image`.
- `backend/tests/test_char_ref_mod_node.py`, `backend/tests/test_graph_stub.py` (MAX_MOD_REDRAWS tests).

## Behavior this changes

Setting on: the flag-then-redraw tests in `test_graph_stub.py` (§6 tests 7 and 17) and
`test_char_ref_mod_node.py` stay green for setting off and gain hold assertions for setting on.

## Acceptance criteria

- [x] Setting on: first reference flag holds before any redraw; the candidate is retained privately (AC-01, AC-06, SH-03).
- [x] Allow, replace and stop on a reference behave as in 07–09, including budget and exact-subject rules.
- [x] Any path that writes `canonical_ref_image` (including replacement) clears `ref_moderation_status` (§4b CC-1).
- [x] No characters or no references: no empty review is created (§9.4).
- [x] Setting off: today's redraw-once behavior unchanged.

## Guidance

Replacement here is a third write path to `canonical_ref_image`; §4b says it must clear the status
or the skip must go.

## Verification

Seam per §9.6 (accepted contract in §9.9.8). Main: reference flag → hold → allow → reveal proceeds. Failure:
replacement written without clearing status is caught by a test that goes red first.
**Targeted:** `cd backend && uv run pytest tests/test_char_ref_mod_node.py tests/test_graph_stub.py`
**Full suite:** required now (Shared).

## Blocked by

None — predecessors 07–09 are implemented. Hosted/release gates remain separate.

Design/conflict acceptance is settled in ADR-080. No repeat owner verdict is required for the
accepted synthetic-only, feature-off scope. Audit/calibration and real-child release gates remain.

## Comments

## Answer

Captured teacher-review jobs hold the first exact flagged reference, then review remaining
references in order after allow. Private inspection, allow/replace/stop, same-request delivery
and withdrawal reuse the existing held-picture lifecycle. One reference replacement preserves
the recorded prompt and tapped emphasis, clears prior moderation, and receives fresh checks.
The existing per-book slot, image budget and dependent-scene restriction are enforced in the
command and worker paths. Baseline redraw behavior is preserved. See
[moderation-stack §9.16](../../../docs/specs/moderation-stack.md#916-ticket-10-implementation-2026-10-28)
for verification and remaining release gates. Intake remains disabled by default.
