# ptd-review-feedback: map

**Phase:** [Post technical defense](../post-technical-defense/map.md), rank 3

**Conflict gate:** `docs/specs/teacher-review-and-approval.md` §12–13. It records no rejection reason
because that "would need its own ethics pass" (`:534`), and it fails if "a child learns their book was
rejected" (`:550`). Before any grill, brainstorm, design or build here, name the conflict to the owner
and wait for the verdict.

Panel suggestions: feedback on approve and reject, wording that is gentler than "reject" for a child,
feedback the child can see, and teacher comments. Owner idea: highlights and underlines with tooltip
notes, usable on mobile.

## Tickets

| # | Ticket | Type | Progress | Blocked by |
|---|---|---|---|---|
| 01 | [Audit: review decisions and what a child sees](issues/01-audit-review-feedback.md) | research | resolved | — |
| 02 | [Grill: feedback, comments and highlights → spec](issues/02-grill-review-feedback-spec.md) | grilling | open | 01 |

Highlights are a separate build ticket after comments ship, per the 2026-10-25 grill.

## Answers

**01 (2026-10-29).** Conditional go on teacher comments in a private service-role table `job_review_notes` (not a `jobs` column, which classmates can read), a read-only note for the child, and gentler teacher-facing labels. Highlights later, sentence-level. No-go on a `jobs` note column, in-place child edits, and child replies. Drift found: the book page already tells a child "Your teacher needs to approve this book", against spec §4.10. Needs the owner verdict on §4.10 and an ethics re-review. See the ticket `## Answer`.
