# 07 — Teacher note row in the review dialog

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Blocked by:** `.scratch/ptd-review-feedback/issues/05-notes-schema-and-teacher-api.md`

**Parent:** `docs/specs/teacher-review-and-approval.md` §14
**What to build:** In the review dialog, when the classroom switch is on, every `complete` book has a
collapsed "Add a note for [nickname]" row. The teacher writes, sends, edits or deletes the one note
without slowing the pass.
**Source criteria:** US-01 / AC-01–AC-08, AC-19 (dialog side), SH-03, SH-06, OD-4, OD-6, §14.4 rows:
advance with the row open, two tabs, removed student
**Scope:** `BookReviewDialog` and the books page that drives it; `books/page.test.tsx`
**Out of scope:** button and tab relabel (09); child view (08); the switch control (06)
**Complexity:** Medium — the row's state interacts with the dialog's advance, optimistic decisions and Undo
**Blast radius:** Local — the teacher books screen
**Unblocks:** 08 (its J1–J3 browser pass needs this UI)

## Context
§4.7 makes the dialog a two-tap pass that advances to the next pending book. The note must sit
outside the decision (Q6): Approve and Reject never wait for it. Pressing reject opens the row
because that's when a teacher most wants to explain.

## Read first
- `frontend/components/BookReviewDialog.tsx` — props, `onDecide`, the ADR-072 download explanation,
  and the decision buttons
- `frontend/app/classroom/[classroomId]/books/page.tsx` — `openDialog`, `handleDecide`, advance logic,
  toast and Undo, the classroom read
- `frontend/app/classroom/[classroomId]/books/page.test.tsx` — dialog and advance tests to extend
- `frontend/lib/types/jobs.ts` — `Job`, `jobState`
- the endpoints from 05 (paths as built there)

## Behavior this changes
None removed. The dialog gains a row, and the existing advance and Undo tests must stay green unchanged.

## Acceptance criteria
- [ ] Switch on and a `complete` book in any review state: a native `<details>` row "Add a note for
      [nickname]" is shown collapsed (AC-01). Switch off: the row isn't rendered (AC-19, SH-03).
      Failed and in-flight books never show it (AC-08).
- [ ] Opening the row shows a labeled text box (placeholder "Something kind and specific…"), a Send
      button, and the line saying the child reads the note (AC-02, OD-6).
- [ ] Pressing the reject decision opens the row. It requires no note, and the dialog still advances
      as it does today (AC-03).
- [ ] Send is disabled while the box is empty or sending (SH-03). Send shows the note as sent, then
      offers Edit and Delete. Delete asks no confirmation and leaves an empty row (AC-04, AC-05).
- [ ] An existing note loads when its book opens in the dialog.
- [ ] A failed send keeps the text and shows the error in an `aria-live="polite"` region (AC-07).
      A `409 notes_disabled` or `422` shows a readable message, not a raw code.
- [ ] When the dialog advances, the row collapses and an unsent draft is discarded without a warning (OD-4).
- [ ] The row, box, Send, Edit and Delete have accessible names that include the nickname where useful (SH-06).

## Guidance
Traps:
- The dialog advances inside `handleDecide`. Key the note state by job id, or reset it on the job
  change, or the last book's draft leaks into the next one.
- Find the reject button by role and name in tests. 09 renames it to "Not ready to share yet", so
  keep the selectors in one place.
- Read the switch with the existing classroom data where the page already fetches it, not with a
  new server read in `TeacherShell` (S2-6).

## Verification
Extend `books/page.test.tsx`, mocking `fetch` at the network boundary. Cover the main journey (reject
→ row open → send → edit → delete) and one failure (a failed send keeps the text). Run each red
first. Then drive it in a real browser on a seeded synthetic classroom with the switch on and check
that the console is clean.
**Targeted:** `cd frontend && pnpm exec vitest run "app/classroom/[classroomId]/books/page.test.tsx"`
**Full suite:** at the batch gate

## Blocked by
05.

## Comments
