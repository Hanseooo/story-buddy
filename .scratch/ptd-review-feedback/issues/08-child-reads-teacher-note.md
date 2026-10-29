# 08 — Child finds and reads the teacher's note

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Blocked by:** `.scratch/ptd-review-feedback/issues/05-notes-schema-and-teacher-api.md`,
`.scratch/ptd-review-feedback/issues/07-teacher-note-row-in-review-dialog.md`

**Parent:** `docs/specs/teacher-review-and-approval.md` §14
**What to build:** A child whose book has an unopened note sees "A note from your teacher" on its
bookshelf card. Opening the book shows the note in a closable panel above it. After that the badge
is gone, until the teacher edits the note.
**Source criteria:** US-03 / AC-11–AC-16, AC-19 (child side), SH-01, SH-02, SH-05 (child), SH-07,
OD-2, OD-3, invariants 13 and 15, §14.4 rows: delete/edit after read, child asks for another's note,
offline child; §14.7 seam 4 (J1–J3)
**Scope:** child read and mark-seen endpoints; the bookshelf badge; the book page panel; tests; the
J1–J3 browser pass; doc updates
**Out of scope:** the download line (04); highlights; replies
**Complexity:** High — owner-only reads, the switch, `seen_at` timing and verdict-free copy all meet on two kid surfaces
**Blast radius:** Shared — two kid pages plus a new student-authenticated endpoint
**Unblocks:** None

## Context
Notes are private. A child reads only their own, and only through the server, with `jobs.profile_id`
checked against the signed-in student (SH-05). The bookshelf's jobs read stays a browser SELECT. The
note data comes from the new endpoint. A book without a badge says nothing (SH-07, §4.10).

## Read first
- `frontend/app/s/[profileId]/page.tsx` — the jobs query, the local `BookCard`, shelf vs failed split
- `frontend/app/s/[profileId]/book/[jobId]/page.tsx` — layout above the book, `aria-live` status pattern
- `frontend/app/s/[profileId]/page.test.tsx`, `book/[jobId]/page.test.tsx` — where the tests go
- `backend/app/pdf_export.py` — the student-viewer checks (role, `removed_at`, classroom, owner)
- `backend/app/moderation_hold.py` — `POST /jobs/{job_id}/stop`: the owner check and 404 on `deleting`
- `docs/specs/classroom-sharing.md` — where SH-07 gets recorded as inherited

## Behavior this changes
None removed. The new kid-facing text is limited to the badge and the panel heading (SH-01).

## Acceptance criteria
- [ ] Child endpoints return only the caller's own notes. Another child's job, a nonexistent job, a
      teacher or researcher token, and a signed-out call all get the same `404` (or a refusal before
      the handler). With the switch off they return none (AC-19, OD-11).
- [ ] The bookshelf card shows "A note from your teacher" only when a note exists, the switch is on,
      and `seen_at` is null (AC-11, SH-07). If the note fetch fails, the shelf still renders with no
      badge.
- [ ] The book page shows the note in a panel above the book, headed "A note from your teacher", with
      a "Close" button. Escape also closes it, focus returns to the control that opened it, and the
      note can be reopened (AC-12, SH-02).
- [ ] Opening the panel sets `seen_at`. The next shelf load has no badge. A teacher edit brings the
      badge back. A teacher delete removes the badge and panel with no explanation (AC-13, J3).
- [ ] For a book in each of the three review states, the badge and panel text contain none of
      "approved", "rejected", "pending" or any verdict (AC-14, SH-01).
- [ ] Classmates, the gallery and researchers have no path to a note (AC-15). A note sent while the
      child was offline shows on their next shelf load (AC-16).
- [ ] J1, J2 and J3 run in a real browser on seeded synthetic jobs, teacher then child, with a clean
      console. Cost $0.
- [ ] Docs: spec §14 status says it is built, `classroom-sharing.md` records SH-07 as inherited, and
      the ADR-081 row is updated.

## Guidance
Suggested (non-binding): `GET /me/notes` returns `[{job_id, body, seen}]` for the shelf and panel,
and `POST /jobs/{job_id}/note/seen` marks one seen. Traps:
- The jobs query in `s/[profileId]/page.tsx` already notes that RLS also returns classmates'
  approved jobs. The note endpoint must not rely on the browser's list to scope ownership.
- Set `seen_at` when the panel opens, not on page load, so a child who never opens it keeps the badge.

## Verification
Backend: test client in `test_review_notes.py` for owner-only reads, 404 parity, the switch and
`seen_at`. Frontend: the two page tests. Run each red first.
**Targeted:** `cd backend && uv run pytest tests/test_review_notes.py` and
`cd frontend && pnpm exec vitest run "app/s/[profileId]/page.test.tsx" "app/s/[profileId]/book/[jobId]/page.test.tsx"`
**Full suite:** required now (Shared), both stacks

## Blocked by
05 (table and switch), 07 (teacher UI for the J1–J3 pass).

## Comments
