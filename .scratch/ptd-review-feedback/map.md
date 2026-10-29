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
| 03 | [ADR-081: teacher notes the child can read](issues/03-adr-081-teacher-notes.md) | task | resolved | Owner accepted ADR-081 on 2026-10-29 |
| 04 | [Reword the child's download line](issues/04-reword-child-download-line.md) | task | open | — |
| 05 | [Notes schema and teacher note API](issues/05-notes-schema-and-teacher-api.md) | task | open | 03 accepted |
| 06 | ["Let students read my notes" switch](issues/06-review-notes-switch-setting.md) | task | resolved | 05 |
| 07 | [Teacher note row in the review dialog](issues/07-teacher-note-row-in-review-dialog.md) | task | resolved | 05 |
| 08 | [Child finds and reads the teacher's note](issues/08-child-reads-teacher-note.md) | task | open | 05, 07 |
| 09 | [Gentler teacher decision labels](issues/09-gentler-teacher-labels.md) | task | open | — |

Build tickets 03–09 cover spec §14 (source-to-ticket mapping in the 2026-10-29 breakdown). OD-9, the
ethics re-review, is a release gate before real children, not a ticket.

Highlights are a separate build ticket after comments ship, per the 2026-10-25 grill.

## Answers

**07 (2026-10-29).** [Teacher note row implemented](issues/07-teacher-note-row-in-review-dialog.md#answer):
native switch-gated row with send/edit/delete, current-note loading, readable errors and job-keyed
draft reset. Decisions, advance and Undo are unchanged. Lint, build/typecheck and all 78 source test
files pass (755 tests, one existing freeze-dependent skip). Standards and Spec reviews are clear.
The seeded-classroom browser pass remains unverified because no browser is available in the session.

**06 (2026-10-29).** [Classroom notes switch implemented](issues/06-review-notes-switch-setting.md#answer):
server-only ownership-checked PATCH, native checkbox, live save feedback and rollback. Stored notes
are kept when disabled. Focused tests, lint and build pass; full-suite failures are recorded in the ticket.

**01 (2026-10-29).** Conditional go on teacher comments in a private service-role table `job_review_notes` (not a `jobs` column, which classmates can read), a read-only note for the child, and gentler teacher-facing labels. Highlights later, sentence-level. No-go on a `jobs` note column, in-place child edits, and child replies. Drift found: the book page already tells a child "Your teacher needs to approve this book", against spec §4.10. Needs the owner verdict on §4.10 and an ethics re-review. See the ticket `## Answer`.
