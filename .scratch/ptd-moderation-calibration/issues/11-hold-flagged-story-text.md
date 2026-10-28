# 11 — Flagged story text holds and the teacher can allow it unchanged

**Status:** implemented — synthetic-only, feature off; browser/hosted checks pending
**Type:** task
**Progress:** implemented
**Predecessors:** `.scratch/ptd-moderation-calibration/issues/07-teacher-allows-held-picture.md`; `08-teacher-stops-held-story.md`
**Conflict gate:** ADR-011, `AGENTS.md` child-safety rules. Discussion permission is recorded;
ADR-080 and the synthetic-only, feature-off build scope were accepted on 2026-10-27.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md)
**What to build:** With the setting on, a safety flag from `input_gate` holds the run instead of
failing it. The teacher reads the privacy-processed text and can allow it unchanged or stop. Allowed
text proceeds; every generated picture is still moderated.
**Source criteria:** US-01 AC-01 (story text); US-05 AC-10 (text), AC-13; SH-01, SH-02, SH-03,
SH-05, SH-11, SH-12; §9.4 rows: empty/too-short story, abuse disclosure (§4a).
**Scope:** `input_gate`/`moderation_router` flag path under the setting; hold persistence of
redacted text only; teacher inspection and allow/stop for a text subject.
**Out of scope:** Titles (12); rewriting the child's text; changing Presidio or classifier prompts (OD-01).
**Complexity:** Medium — reuses 05–08 machinery; the new part is the privacy ordering.
**Blast radius:** Shared — `input_gate`, `moderation_router`, teacher inspection.
**Unblocks:** 12

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
hosted verification gates remain before real-child enablement. Implementation evidence is recorded in moderation-stack §9.17.

## Context

Q2/Q11: the child need not rewrite text to satisfy a classifier. SH-03: privacy checks must succeed
before review material is retained; the current raw `jobs.input_text` row is not assumed to meet that
boundary. §4a says an abuse disclosure should route to the teacher — a hold does that more directly
than a failure; how release interacts with it is OD-02.

## Read first

- `backend/pipeline/input_gate.py` — `input_gate`, `result()`: concurrent Presidio and classifiers, `redacted_text` always set.
- `backend/pipeline/graph.py` — `moderation_router`: `passed=False` → raise.
- `backend/tests/test_input_gate_node.py` — posture trio and redaction tests.
- `docs/specs/input-gate-hardening.md` — redaction output form (pseudonyms).

## Behavior this changes

Setting on: `moderation_router` no longer fails the job on an input flag. Existing
`test_input_gate_node.py` and graph tests stay green for setting off.

## Acceptance criteria

- [x] Setting on: a classifier flag holds; a Presidio failure persists nothing and is a service error, not a hold (SH-03, SH-01).
- [x] Teacher sees `redacted_text`, never `raw_text` (CC-2, SH-03).
- [x] Allow continues with the unchanged redacted text; generated pictures still pass `char_ref_mod`/`output_mod` (AC-10).
- [x] Backstop error stays `moderation_error`, not a hold (SH-01).
- [x] Empty/invalid input still uses existing validation; maximum-size input is not newly rejected (SH-12).
- [x] Child copy is neutral; no category or reasoning (SH-05).

## Guidance

Trap: a router that raises discards the node's writes, so today a blocked run has no recorded input
verdict (research-run-browser §5.1). A hold must keep the verdict it is asking the teacher about.

## Verification

Seam per §9.6 (accepted contract in §9.9.8). Main: flagged text → hold → allow → analyze runs. Failure: Presidio
raises → nothing persisted, job reports a service error.
**Targeted:** `cd backend && uv run pytest tests/test_input_gate_node.py tests/test_graph_stub.py`
**Full suite:** required now (Shared).

## Predecessors

`.scratch/ptd-moderation-calibration/issues/07-teacher-allows-held-picture.md`; `08-teacher-stops-held-story.md`

Design/conflict acceptance is settled in ADR-080. No repeat owner verdict is required for the
accepted synthetic-only, feature-off scope. Audit/calibration and real-child release gates remain.

## Comments

Implemented the accepted exact-text hold, allow/stop, guarded delivery and withdrawal flow.
Privacy processing succeeds before intake persistence. The original classifier verdict remains
unchanged and the clearance binds the processed text hash and committed decision policy.
Later reference/scene checks remain independent. Migration 0024 was owner-approved and applied
only to the disposable local database. See moderation-stack §9.17 for final verification and
release limits. Both review axes have no unresolved findings.
