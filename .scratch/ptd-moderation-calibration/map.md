# ptd-moderation-calibration: map

**Phase:** [Post technical defense](../post-technical-defense/map.md), rank 2

**Conflict gate:** ADR-011 (moderation stack and ordering), the `AGENTS.md` child-safety rules ("no
unmoderated generated image reaches a child"; "the child never sees a moderation category"), and
ADR-003 (`reveal` holds the graph's only `interrupt()`). Before any grill, brainstorm, design or build
here, name the conflict to the owner and wait for the verdict.

Panel suggestions: better rubrics for rejecting text and images, because moderation was too strict at
the defense, and the teacher decides whether a flagged run continues.

## Tickets

| # | Ticket | Type | Progress | Blocked by |
|---|---|---|---|---|
| 01 | [Audit: why moderation over-refuses](issues/01-audit-moderation-false-alarms.md) | research | open | — |
| 02 | [Grill: moderation policy and teacher-held runs → spec](issues/02-grill-moderation-spec.md) | grilling | open | 01 |

## Answers

None yet.
