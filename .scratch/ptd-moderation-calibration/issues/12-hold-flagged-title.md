# 12 — A flagged title holds instead of rejecting the submission

**Status:** implemented — synthetic-only, feature off; browser/hosted checks pending
**Type:** task
**Progress:** implemented
**Predecessor:** `.scratch/ptd-moderation-calibration/issues/11-hold-flagged-story-text.md` (implemented)
**Conflict gate:** ADR-011, ADR-059 (titles are checked before a job exists), `AGENTS.md`
child-safety rules. Discussion permission is recorded in the map; ADR-080 and the synthetic-only, feature-off build scope were accepted on 2026-10-27.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md)
**What to build:** With the setting on, a title the classifiers flag no longer returns 422 to the
child. The submission is held privately for the teacher, who can allow the exact title or stop.
**Source criteria:** US-01 AC-01 (title); AC-10 (title); SH-01, SH-03, SH-05, SH-11, SH-12; §9.4
row: flagged title before a job exists.
**Scope:** `POST /storybooks` flagged-title branch under the setting; a private held representation
(OD-03); teacher allow/stop for a title subject; child submit page copy.
**Out of scope:** The redaction-confirm 409 flow (unchanged); length/empty validation (unchanged, SH-12).
**Complexity:** High — the title is checked before any job or checkpoint exists, so there is nothing to resume yet.
**Blast radius:** Shared — submission endpoint, child submit flow, teacher queue.
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

Q7: flagged titles join the same teacher-help experience. ADR-059 currently rejects before a job is
created; the representation of a held pre-job submission is explicitly "not approved" (§9.4).

## Read first

- `backend/app/main.py` — `create_storybook`: `check_text(payload.title)`, the 422 and the 409 `title_ack` flow.
- `backend/tests/test_main.py` — title rejection and `title_ack` tests.
- `docs/product/adr/ADR-059-story-titles-are-job-metadata-checked-synchronously-before-persistence.md` — title moderation decision.
- `docs/specs/story-titles.md` §4 — no logging of request values.

## Behavior this changes

Setting on: `test_main.py` cases asserting 422 "that title isn't allowed" gain a setting-on hold
counterpart; setting off keeps them as is. ADR-059 needs its amendment (OD-10).

## Acceptance criteria

- [x] Setting on: a flagged title creates a held private submission; the child sees neutral waiting copy, not a rejection (AC-01, SH-05).
- [x] Privacy checks succeed before anything is stored; failure stores nothing (SH-03).
- [x] The 409 redaction-confirm flow and length validation are unchanged (SH-12).
- [x] Teacher allow starts the run with the exact title; stop ends it with writing kept (AC-10, AC-13).
- [x] No request values in logs or 4xx bodies (story-titles §4).
- [x] Setting off: 422 behavior unchanged.

## Guidance

Authorization runs before moderation in `create_storybook`; keep that order.

## Verification

Seam per §9.6 (accepted contract in §9.9.8). Main: flagged title → held → teacher allows → job queued once.
Failure: allow sent twice queues one job.
**Targeted:** `cd backend && uv run pytest tests/test_main.py`
**Full suite:** required now (Shared).

## Predecessor

`.scratch/ptd-moderation-calibration/issues/11-hold-flagged-story-text.md`

Design/conflict acceptance is settled in ADR-080. No repeat owner verdict is required for the
accepted synthetic-only, feature-off scope. Audit/calibration and real-child release gates remain.

## Comments

Implemented the accepted private pre-graph title hold, exact-title allow, stop and neutral child
waiting flow. Duplicate allow/worker delivery starts one graph. The review-discovered projection
recovery gap has a failing-first database-outage regression and an explicit HTTP reconcile path.
See moderation-stack §9.18 for verification and release limits. Existing native PDF test failures
remain environmental and are reported separately. Feature remains disabled by default.
