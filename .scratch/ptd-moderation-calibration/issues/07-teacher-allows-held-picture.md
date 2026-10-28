# 07 — Teacher allows the exact held picture and the run resumes

**Status:** implemented — browser/hosted verification pending
**Type:** task
**Progress:** resolved — synthetic-only, feature-off build
**Blocked by:** None — 06 inspection and 13 criteria are implemented.
**Conflict gate:** ADR-011, ADR-003, `AGENTS.md` child-safety rules ("no unmoderated generated
image reaches a child"). Discussion permission is recorded in the map; ADR-080 and the synthetic-only, feature-off build scope were accepted on 2026-10-27.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

**Parent:** [moderation-stack §9](../../../docs/specs/moderation-stack.md)
**What to build:** From inspection, the teacher allows the exact held scene picture. The run resumes
from its checkpoint without redrawing completed scenes, the allowed picture is used, and every later
scene is still moderated; a later flag creates a new hold. The teacher explicitly confirms the
named criterion and can withdraw mistaken clearance as specified in AC-19.
**Source criteria:** US-05 AC-10 (picture), AC-19; SH-01, SH-02, SH-06, SH-07, SH-11; J-01 (resolution
half); §9.4 rows: double click/two tabs/lost response, old decision after replacement, later scene
flag, access withdrawn, missing checkpoint.
**Scope:** Allow command (authorized, bound to exact subject/version, idempotent); resume of the
held run; recording of the decision; withdrawal of clearance; teacher pending/success/error UI;
child view updates to progress or review.
**Out of scope:** Stop (08), replacement (09), text/title/reference allow (10–12), theme acceptance
(15), classroom-sharing approval (stays the editorial flow).
**Complexity:** High — serialized, idempotent resume against a checkpointer with paid steps after it.
**Blast radius:** System-wide — worker resume path, job state, teacher and child surfaces.
**Unblocks:** 09, 10, 11, 15

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

Q2/Q10/Q11: the teacher may overturn an automated flag against the written policy; no category is
an unconditional veto. Resumed Q4/Q6/Q9 settle explicit confirmation, no mandatory written
justification or new second-reviewer service, and withdrawal. OD-02/OD-03 now have exact proposed
commands, transaction/dispatch/epoch behavior, whole-book containment and guarded access in
§9.9.2–9.9.5. Use those accepted contracts. Ticket 13 supplies the required criteria UI;
it precedes allow rather than leaving confirmation without a policy reference.

## Read first

- `backend/app/main.py` — `/jobs/{job_id}/confirm`: existing authorized resume with a status guard.
- `backend/pipeline/reveal.py` — interrupt payload and resume value handling.
- `backend/pipeline/graph.py` — `route_after_output_mod`, `route_next_scene`.
- `backend/pipeline/output_mod.py` — `OVERRIDE_STATUS` skip: the existing operator-override precedent.
- `backend/tests/test_run_job.py` — worker/resume test precedent.
- `docs/specs/kid-flow-pause-lifecycle.md` — pause/resume lifecycle rules.

## Behavior this changes

`AGENTS.md` "no unmoderated generated image reaches a child" — a teacher-allowed flagged picture is
moderated but overridden; the rule's amendment is OD-02/OD-10. No existing test asserts teacher allow.

## Acceptance criteria

- [x] Allow binds to the exact held picture; a decision for an older candidate cannot release a newer
      one and returns current state (SH-02).
- [x] Ownership rechecked on decision and on resume; deleted story/withdrawn access → denied, nothing generated (SH-02, SH-11).
- [x] Double submit, two tabs or a lost response produce one transition and no duplicate paid work (SH-07).
- [x] Resume does not redraw or re-bill completed scenes; `check_image_budget` still guards later draws (SH-07).
- [x] Later scenes are moderated; a later flag creates a new hold despite the earlier allow (AC-10).
- [x] The decision and the policy/settings evidence approved under OD-03 are persisted (SH-06).
- [x] Explicit confirmation follows inspection against the named criterion; record teacher, exact
      content/version, criterion and current policy version without mandatory written justification (AC-10, SH-06).
- [x] An uncertain teacher can leave held, return later, replace within budget or stop; no release
      pretending uncertainty is a pass and no new escalation service (AC-10).
- [x] Withdrawal hides affected content from child/gallery, blocks further generation and returns
      the story to review, retaining writing/history; an in-flight result cannot bypass it (AC-19).
- [x] Withdrawal and later safety release do not automatically restore previous gallery approval (AC-19).
- [x] Missing checkpoint: no silent restart or re-charge; honest error (SH-04, §9.4).
- [x] Teacher UI: pending state disables competing decisions without trapping; success only after
      durable write; failure keeps context with retry/reconcile (SH-08, SH-11).
- [x] Allow does not set `approved_at` or any editorial field (SH-09).

## Guidance

Trap: resuming re-runs the interrupted node from the top; anything paid or classified before the
pause point in that node runs again. Confirm `/confirm`'s status-guarded update pattern fits before
adding another.

## Verification

Seam per §9.6 (accepted contract in §9.9.8). Main: J-01 end to end, provider mocked; assert scene count billed
equals scenes drawn once. Failure: second allow request after success changes nothing and bills nothing.
**Targeted:** `cd backend && uv run pytest tests/test_run_job.py tests/test_graph_stub.py tests/test_main.py`
**Full suite:** required now (System-wide).

## Blocked by

None — predecessor code is implemented. Browser and hosted verification remain separate release gates.

Design/conflict acceptance is settled in ADR-080. No repeat owner verdict is required for the
accepted synthetic-only, feature-off scope. Audit/calibration and real-child release gates remain.

## Comments

The uncertainty criterion is now complete across tickets 07–09: leave held, return later,
stop, or replace within budget. These later actions are implemented in tickets 08/09. No uncertain
teacher must allow content. Owner delegated the open-review withdrawal choice on 2026-10-28:
keep one open review, with earlier-clearance withdrawal unavailable while another picture is
held. The whole book remains hidden and paused; the inspection explains this boundary.

## Answer

Exact-scene allow, durable same-request delivery/retry, checkpoint-only continuation and
whole-book withdrawal are implemented in the accepted feature-off scope. The teacher confirms
the loaded exact picture against every named criterion. Pending delivery remains reachable after
refresh/reopen. Withdrawal fences in-flight work, retains incurred cost, resets sharing and
anchors at the saved continuation, including a pure committed later allow without paid replay.
Missing checkpoints fail honestly, including loss after an allow commits. See
[moderation-stack §9.13](../../../docs/specs/moderation-stack.md#913-ticket-07-implementation-2026-10-28)
for final commands, results and release limits. Standards and Spec reviews have no unresolved
findings. Browser/hosted verification, paid replay and real-child enablement remain unrun.
