# ptd-ai-assisted-review: map

**Phase:** [Post technical defense](../post-technical-defense/map.md), rank 7

**Conflict gate:** ADR-017 (review is manual, always; auto-approve is deferred to Future Work pending
an ethics re-review) and `docs/specs/teacher-review-and-approval.md` §12–13 (fails if "any bulk
decision exists"). Before any grill, brainstorm, design or build here, name the conflict to the owner
and wait for the verdict.

**Waits on:** the `ptd-moderation-calibration` audit (a trustworthy "unsure" signal) and the
`ptd-review-feedback` spec (what the teacher sees and writes).

Panel suggestion: the teacher reviews only the books the AI is unsure about. Owner: it is a toggle,
so a teacher can keep reviewing everything.

## Tickets

| # | Ticket | Type | Progress | Blocked by |
|---|---|---|---|---|
| 01 | [Audit: is there a signal the AI can be trusted on?](issues/01-audit-review-signal.md) | research | open | — |
| 02 | [Grill: AI-assisted review → spec](issues/02-grill-ai-review-spec.md) | grilling | open | 01, `ptd-moderation-calibration` 01, `ptd-review-feedback` 02 |

## Answers

None yet.
