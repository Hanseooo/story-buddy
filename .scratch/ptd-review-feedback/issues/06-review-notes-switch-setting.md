# 06 — "Let students read my notes" classroom switch

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Blocked by:** `.scratch/ptd-review-feedback/issues/05-notes-schema-and-teacher-api.md`

**Parent:** `docs/specs/teacher-review-and-approval.md` §14
**What to build:** Classroom settings has a "Let students read my notes" control, off by default.
Saving it changes `classrooms.review_notes_enabled` through a teacher endpoint.
**Source criteria:** US-05 / AC-18, AC-20, OD-3 (stored notes kept when off)
**Scope:** a server write endpoint behind `owned_classroom`; a section on the classroom settings page; tests
**Out of scope:** what the switch hides in the dialog (07) and for the child (08)
**Complexity:** Low — follows the moderation-settings form already on the page
**Blast radius:** Local — one settings page and one endpoint
**Unblocks:** None (07 and 08 read the column, which 05 creates)

## Context
`0025`'s rule is that classroom columns are browser-readable and written only by the server. The
settings page already has one server-written section (review themes) to copy.

## Read first
- `frontend/app/classroom/[classroomId]/settings/page.tsx` — `saveThemes`, `getToken`, the themes `<fieldset>`
- `frontend/app/classroom/[classroomId]/settings/page.test.tsx` — how the fetch is mocked
- `backend/app/moderation_hold.py` — `PATCH /teacher/classrooms/{classroom_id}/moderation-settings`
- `backend/app/auth.py` — `owned_classroom`
- `backend/app/classrooms.py` — `rename_classroom`, the simpler teacher PATCH shape

## Behavior this changes
None.

## Acceptance criteria
- [x] The settings page shows a labeled native checkbox "Let students read my notes" with a line
      explaining that students read the notes. It is unchecked for a new classroom (AC-18).
- [x] Saving sends the value to the endpoint. The control is disabled while saving. Success and
      error each announce in an `aria-live` region, and on error the control reverts to the stored value.
- [x] The endpoint is behind `owned_classroom`. Another teacher's classroom gives the same `404` as a
      nonexistent one. A student token is rejected before the handler (AC-20).
- [x] Turning the switch off deletes no notes (OD-3).

## Guidance
Suggested (non-binding): `PATCH /classrooms/{classroom_id}/review-notes` on `teacher_router` with
`{"enabled": bool}`. There's no version counter like `moderation_settings_version`, and last write
wins, as §4.12 accepts for one teacher.

## Verification
Backend: test client, plus a check that notes survive a toggle off. Frontend: the existing settings
page test.
**Targeted:** `cd backend && uv run pytest tests/test_review_notes.py -k switch` and
`cd frontend && pnpm exec vitest run "app/classroom/[classroomId]/settings/page.test.tsx"`
**Full suite:** at the batch gate

## Blocked by
05 (the column).

## Comments

## Answer

Implemented `PATCH /classrooms/{classroom_id}/review-notes` in the existing notes module,
behind `owned_classroom`, with a strict boolean body and last-write-wins persistence.
The settings page reads the stored column, provides the native checkbox and save control,
announces results, disables during saving, and restores the stored value on failure.
The endpoint only updates the classroom column, leaving stored notes intact.

Verification (2026-10-29):
- Backend red: the two switch tests failed with missing-route `404`; green:
  `uv run pytest tests/test_review_notes.py` passed all 19 tests.
- Frontend red: the new switch tests failed because the checkbox was absent; green:
  `pnpm exec vitest run "app/classroom/[classroomId]/settings/page.test.tsx"` passed all 9 tests.
- `uv run ruff check .`, `pnpm lint`, and `pnpm build` passed. The build includes typechecking.
  Windows uses `pnpm.cmd` because script execution policy blocks `pnpm.ps1`.
- Full `uv run pytest`: 1576 passed, 130 skipped, 6 deselected, 6 PDF-export failures (OSError).
- Full `pnpm test`: 751 passed, 3 failed in unchanged books/gallery tests. An isolated rerun of
  those files passed 51 tests with one books-page retry test still failing.
- Real database/RLS checks were skipped without a configured local database. No browser pass
  or remote migration was performed.
- Separate code-review standards and spec reviews: zero findings on either axis.
