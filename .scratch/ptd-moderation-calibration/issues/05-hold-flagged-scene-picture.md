# 05 — A flagged scene picture holds the run and the child can leave and return

**Status:** complete, merged
**Type:** task
**Progress:** done — merged into `feat/account-onboarding` at `b03cc3f`
**Blocked by:** None — ticket 02/ADR-080 accepted; synthetic-only, feature-off scope.
**Conflict gate:** ADR-011, ADR-003 (reveal holds the only `interrupt()`), `AGENTS.md` child-safety
rules. Discussion permission is recorded in the map; ADR-080 and the synthetic-only, feature-off build scope were accepted on 2026-10-27.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md)
**What to build:** With the feature setting on, the first safety flag on a scene picture durably
holds the run before any soften-and-retry. The child sees neutral teacher-help status, can leave to
the bookshelf, sees the story marked as waiting, and returns to the same persisted state. With the
setting off, behavior is unchanged.
**Source criteria:** US-01 AC-01 (scene picture), AC-02; US-02 AC-03, AC-04; SH-01, SH-03, SH-04,
SH-05, SH-07, SH-10, SH-11, SH-12; J-01 (hold and leave/return half).
**Scope:** The off-by-default feature setting; hold state persisted for the run and the exact held
picture; `output_mod` first-flag path; child process page waiting state and bookshelf exit; bookshelf
waiting marker and return route; flagged picture hidden from the child.
Necessary enabling contracts are §9.9.2–9.9.5/9.9.8: private review table, mode capture,
`awaiting_teacher`, dedicated review node/worker projection, processed-text intake, guarded
feature-job image delivery and denial of direct browser Storage signing, generation epoch and
ADR-044 finish marker. These are part of this slice, not deferred behind a UI-only hold.
**Out of scope:** Teacher queue/inspection (06), allow and resume (07), stop (08), replacement (09),
references/text/titles (10–12), criteria copy (13), optional themes (14).
**Complexity:** High — a second pause point in the scene loop, checkpoint resume semantics and
durable child-visible state.
**Blast radius:** System-wide — graph topology, StoryMemory/jobs state, child surfaces.
**Unblocks:** 06, 14

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

§9.1: a child should not lose writing or restart because a classifier asked for review. This is the
enabling slice: the hold representation it introduces is what 06–15 build on. OD-03's concrete
contract is §9.9.2–9.9.5 and OD-10's setting/rollout contract is §9.9.8. Both were accepted on 2026-10-27; the ticket 05 implementation record is §9.10.

## Read first

- `docs/specs/moderation-stack.md` §9.1–9.4 — AC/SH text and edge-case table.
- `backend/pipeline/output_mod.py` — `output_mod`: first-flag branch, `check_image_budget`, `_soften_prompt`.
- `backend/pipeline/graph.py` — `route_after_output_mod`, `route_next_scene`, conditional edges.
- `backend/pipeline/reveal.py` — the existing `interrupt()` and why it lives in its own node.
- `backend/app/config.py` — `RECURSION_LIMIT`, `check_image_budget`.
- `backend/app/main.py` — `/jobs/{job_id}/confirm`: the existing resume/`awaiting_confirm` pattern.
- `frontend/app/s/[profileId]/process/[jobId]/page.tsx` — `ProcessingPage` waiting/failed states.
- `frontend/app/s/[profileId]/page.tsx` — `BookshelfPage`, `BookCard`.

## Behavior this changes

- With the setting on, `output_mod` no longer soften-retries on a first flag (AC-01).
  `backend/tests/test_output_mod_node.py` soften-and-retry tests must stay green for setting off and
  gain first-flag hold assertions for setting on — replaced coverage, never deleted (§9.6).
- ADR-003's single-interrupt rule and teacher-review invariants 8, 9, 11 need the amendments OD-10 names.

## Acceptance criteria

- [x] Setting off (default): existing output_mod/graph behavior tests pass, with baseline recursion unchanged.
- [x] Setting on: first flag → hold persisted before any further paid generation; no soften-and-retry call;
      later scenes not drawn while held (AC-01).
- [x] A classifier service error is not a hold; existing `moderation_error` path stands (AC-02, SH-01).
- [x] Child sees neutral teacher-help copy, never a category, reasoning or `jobs.error`; the flagged
      picture is not served to the child (AC-01, SH-05).
- [x] In-app bookshelf exit does not cancel; bookshelf marks the story waiting with a return route;
      reload or another authorized device loads persisted state first (AC-03).
- [x] No countdown, deadline or time-based release; existing deletion still applies (AC-04, SH-04).
- [x] Hold claimed only after durable write; failures show an error and reconcile (SH-11).
- [x] Ethics re-review is recorded as a precondition for enabling with real children (SH-10).

## Guidance

Traps found in code: a resumed node re-runs from the top (`reveal.py` docstring), so an `interrupt()`
inside `output_mod` would re-call the classifiers on resume. Routers that raise discard the node's
writes (research-run-browser §5.1), so a hold cannot ride the existing `RuntimeError` path.
`RECURSION_LIMIT == 87` is pinned in `tests/test_config.py`; a new loop node changes the arithmetic.

## Verification

Seam per §9.6 (accepted contract in §9.9.8): authenticated HTTP into the real compiled graph, providers mocked at
`backend/providers.py`. Main: flag → hold → child leaves → returns to same state. Failure: setting
off reproduces today's soften-and-retry exactly. Browser check of child waiting/bookshelf at phone width.
**Targeted:** `cd backend && uv run pytest tests/test_output_mod_node.py tests/test_graph_stub.py tests/test_run_job.py`
**Full suite:** required now (System-wide), backend and frontend.

## Blocked by

None — ticket 02/ADR-080 accepted; synthetic-only, feature-off scope.

Design/conflict acceptance is settled in ADR-080. No repeat owner verdict is required for the
accepted synthetic-only, feature-off scope. Audit/calibration and real-child release gates remain.

## Comments

Built on the isolated branch with the feature disabled by default. Migration 0022 must be applied
before deploying this code. The private review table, retained checkpoint and guarded read
boundary are merged and available for ticket 06. No teacher inspection or decision
UI is claimed here. See moderation-stack §9.10 for implementation and verification limits.

Phone-width visual browser verification and hosted service verification remain unrun. Local SQL
tests use a synthetic Supabase-compatible schema, not a hosted Storage/Realtime service.

Final checks: backend lint passed; full backend suite 1,542 passed, 89 skipped, six deselected,
six baseline PDF native-library failures (reproduced on the base). Frontend lint/build passed;
full suite 731 passed, one skipped. Both review axes are clear after recovery/quiescence fixes.
