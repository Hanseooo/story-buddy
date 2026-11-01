# 09 — Gentler teacher decision labels

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Blocked by:** None

**Parent:** `docs/specs/teacher-review-and-approval.md` §14
**What to build:** The teacher screen stops saying "Reject". The decision buttons read "Share with
class" and "Not ready to share yet". Tabs and state badges read "Shared with class" and "Not ready
yet". The toast reads "Shared" or "Marked not ready". API values, schema and log fields are unchanged.
**Source criteria:** US-02 / AC-09, AC-10, SH-04, OD-8 (settled 2026-10-29)
**Scope:** `BookReviewDialog` buttons, books page tabs and toast, `StateBadge`, and their tests
**Out of scope:** the note row (07); child copy (04, 08)
**Complexity:** Low — copy only
**Blast radius:** Local — the teacher books screen and `BookCard`'s badge
**Unblocks:** None

## Context
The panel found "Reject" harsh. Relabelling changes no API value (`approved`, `rejected`, `pending`)
and no CC-5 log field.

## Read first
- `frontend/components/BookReviewDialog.tsx` — the decision buttons and the ADR-072 explanation
- `frontend/components/BookCard.tsx` — `StateBadge`
- `frontend/app/classroom/[classroomId]/books/page.tsx` — tab labels, the toast `message`, empty states
- `frontend/app/classroom/[classroomId]/books/page.test.tsx` — assertions on the old words

## Behavior this changes
- Tests in `books/page.test.tsx` that find "Approve", "Reject", "Approved" or "Rejected" by name are
  overturned on purpose (AC-09). Update their expected strings, not their behavior.

## Acceptance criteria
- [ ] The buttons read "Share with class" and "Not ready to share yet". They still send `approved`
      and `rejected` (assert on the request body).
- [ ] The ADR-072 download explanation stays associated with "Share with class" (AC-10).
- [ ] The tabs and `StateBadge` read "Needs review", "Shared with class" and "Not ready yet". The
      toast reads "Shared" or "Marked not ready". Undo is unchanged.
- [ ] Where the empty-state copy says "approve", it uses "share" (§4.6 Approved empty state: "Nothing
      shared yet. Books you share appear in the class gallery.").
- [ ] Nothing on the teacher books screen renders the word "Reject" (a grep in the test).

## Guidance
If 07 has landed, its reject selector must follow the rename. If 07 is in flight, coordinate on the
shared selector.

## Verification
The existing page test, with the strings updated. Run it red against the old labels first.
**Targeted:** `cd frontend && pnpm exec vitest run "app/classroom/[classroomId]/books/page.test.tsx"`
**Full suite:** at the batch gate

## Blocked by
None. (OD-8 was settled 2026-10-29.)

## Comments
