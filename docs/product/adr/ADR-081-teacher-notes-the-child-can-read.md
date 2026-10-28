# ADR-081 — Teacher notes the child can read

**Status:** Proposed (2026-10-29) · proposes amending teacher-review-and-approval §4.10,
invariants 9 and 12, and §13.6. Owner acceptance with a date is required before
ticket 05's migration `0026` lands. This record does not authorize implementation or release.

**Amendments:** `teacher-review-and-approval` §4.10, invariants 9 and 12, and §13.6,
as specified by [§14 SH-01 and SH-05](../../specs/teacher-review-and-approval.md#143-shared-behavior).
Children may read their own teacher note and see its badge and the reworded download line,
but no child surface shows a verdict word. Editorial API values remain unchanged.

## Context

The owner selected child-readable feedback in the
[audit 01 verdict](../../../.scratch/ptd-review-feedback/issues/01-audit-review-feedback.md#comments).
A note column on `jobs` would expose teacher-authored text to classmates and researchers:
the policies in `0008_authorization_surface.sql:28,46` grant whole-row reads.
[Spec §14](../../specs/teacher-review-and-approval.md#14-amendment-teacher-notes-the-child-can-read-2026-10-29-draft)
records the agreed scope and behavior. This ADR records that proposal, not a built feature.

## Decision

1. Use a separate `job_review_notes` table, with RLS enabled and browser-role access revoked,
   following ADR-080's private service-role table precedent. Reads go through server endpoints:
   the owning teacher via `owned_job`, the owning child via `jobs.profile_id`. No classmate,
   gallery, researcher or export read path exists. A note is deleted with its book by cascade.
2. Add `classrooms.review_notes_enabled`, off by default and written only by the server.
   Check it server-side on every note read and write. When off, hide child notes and all note UI,
   retain stored rows, return no notes to children, and reject teacher writes with
   `409 notes_disabled`. The teacher's GET still returns the stored note (OD-11).
3. Keep one note per book, edited in place or deleted, independent of its editorial decision.
   Do not redact notes or add a preview step. Tell the teacher the child reads the note.
   Owner-only delivery preserves the child's own name, with the acknowledged risk of a teacher
   naming another child. Exact schema and endpoint requirements belong to
   [§14.5](../../specs/teacher-review-and-approval.md#145-design-decisions-and-rationale).
4. Show an unread-note badge only when a note exists and the switch is on. Opening the note
   sets `seen_at`, clearing the badge on the next bookshelf load. Editing clears `seen_at`,
   restoring the badge. The closable panel and badge contain no verdict, and absence of a badge
   signals no decision. See [SH-01, SH-05 and SH-07](../../specs/teacher-review-and-approval.md#143-shared-behavior).

## Alternatives rejected

[§14.9](../../specs/teacher-review-and-approval.md#149-rejected-alternatives) rejects private
teacher notes the child cannot read, several notes per book now, a verdict badge such as
“Shared with class”, redaction with a preview, a note column on `jobs`, and a note as the
book's last page. Highlights remain later work.

## Consequences and gates

The downstream build spans more than three modules and remains subject to the project approval
gate ([§14.8](../../specs/teacher-review-and-approval.md#148-blast-radius)). This docs-only proposal
adds no migration or code. Ticket 05 stays blocked until the owner dates acceptance of ADR-081.

OD-9 requires ethics re-review **before real children see a note**. It is a release gate,
not a build gate. Owner design acceptance does not supply that ethics approval. Readiness,
settled decisions and verification seams remain in
[§14.10](../../specs/teacher-review-and-approval.md#1410-open-decisions-readiness-and-sources)
and [§14.7](../../specs/teacher-review-and-approval.md#147-verification).
