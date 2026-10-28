# 05 — Notes schema and teacher note API

**Status:** implemented: schema and teacher API
**Type:** task
**Progress:** resolved
**Blocked by:** `.scratch/ptd-review-feedback/issues/03-adr-081-teacher-notes.md` (status Accepted)

**Parent:** `docs/specs/teacher-review-and-approval.md` §14
**What to build:** Migration `0026` and teacher endpoints. A teacher can GET, PUT (create or edit)
and DELETE the one note on a book in their own classroom. Every miss returns the same `404`.
**Source criteria:** §14.5 (table, columns, `0026`, endpoints, server-side switch), AC-04, AC-05,
AC-06, AC-08 (server side), AC-13 (edit clears `seen_at`), AC-19 (rows kept), SH-04, SH-05 (teacher),
OD-1, OD-2, OD-3, OD-5, OD-11, invariants 14–16, §14.4 rows: other classroom, wrong role, two tabs,
removed student
**Scope:** `supabase/migrations/0026_*.sql`; a backend notes module beside `app/review.py`; backend
tests; privilege tests
**Out of scope:** the settings write endpoint and control (06); the dialog UI (07); child endpoints (08)
**Complexity:** Medium — auth, 404 parity, switch gate, upsert and cascade interact
**Blast radius:** Shared — a new table and a `classrooms` column, browser-readable by every classroom consumer
**Unblocks:** 06, 07, 08

## Context
Notes can't be a `jobs` column because classmates and researchers select whole approved rows
(`0008:28,46`). The precedent is `job_moderation_reviews` (`0022`): RLS on, `revoke all` from
`authenticated`, reached only through FastAPI. The classroom column follows `0025`, which is
browser-readable and written only by the server.

## Read first
- `supabase/migrations/0022_teacher_moderation_hold.sql` — the private table's grants and the RLS-on pattern
- `supabase/migrations/0025_classroom_review_themes.sql` — classroom column precedent and its comment
- `backend/app/auth.py` — `owned_job`, `teacher_router` (no prefix, carries `require_teacher`)
- `backend/app/review.py` — how a teacher job endpoint is shaped, plus the `teacher_review_v1` branch
- `backend/app/main.py` — router registration via side-effect import
- `backend/tests/test_review.py` — how the client and Supabase are mocked for teacher endpoints
- `backend/tests/test_rls_isolation.py` — the privilege suite (skips without `SUPABASE_DB_URL`)

## Behavior this changes
None. The new surface is additive. `0008` policies must still return the same rows.

## Acceptance criteria
- [x] `0026` creates `job_review_notes` (`id`, `job_id` → `jobs` on delete cascade, `author_id`,
      `body`, nullable `scene_id` and `anchor`, `seen_at`, `created_at`, `updated_at`). It is unique on
      `job_id` where `scene_id is null`, has RLS on, and grants nothing to `anon` or `authenticated`.
      It adds `classrooms.review_notes_enabled boolean not null default false`.
- [x] Teacher endpoints sit behind `require_teacher` and `owned_job`. Another classroom's job and a
      nonexistent UUID give byte-identical `404`s. A student, researcher or missing token is
      rejected before the handler runs.
- [x] PUT on a book that isn't `complete` returns `422`. An empty, whitespace-only or 501-character
      body returns `422`, and exactly 500 characters is accepted.
- [x] A first PUT creates the row. A second PUT edits the same row and clears `seen_at`. DELETE
      removes it, and a later PUT creates a fresh row.
- [x] With `review_notes_enabled` false, PUT and DELETE return `409 notes_disabled` and change
      nothing. GET still returns the note (OD-11). The switch is read on the server on every call.
- [x] Privilege tests: `authenticated` and `anon` cannot select, insert, update or delete
      `job_review_notes`, and `authenticated` cannot update `review_notes_enabled`. Every `0008`
      SELECT policy returns the same rows as before.
- [x] Deleting a `jobs` row deletes its note (OD-5; no book-delete endpoint exists yet, so test
      the cascade directly).
- [x] ADR-081's index row and the spec §14 status move to "implemented: schema and teacher API".

## Guidance
Suggested paths (non-binding): `GET/PUT/DELETE /teacher/jobs/{job_id}/note`. Traps:
- `owned_job` selects a fixed column list without the classroom switch, so read
  `classrooms.review_notes_enabled` separately.
- `teacher_router` has no prefix. `hold_router` writes `/teacher/...` literally.
- Set `author_id` from `require_teacher`, never from the body. Timestamps are set by the server, as in §4.3.

## Verification
FastAPI test client in `backend/tests/test_review_notes.py`, mocking only at the Supabase boundary.
Expected values are hand-written literals. Break each guard and confirm red.
**Targeted:** `cd backend && uv run pytest tests/test_review_notes.py tests/test_rls_isolation.py`
(the RLS suite needs a local Supabase. Report it as *inconclusive* if it skips.)
**Full suite:** required now (Shared): `uv run ruff check . && uv run pytest`

## Blocked by
03 accepted by the owner.

## Comments

**2026-10-29 implementation:** migration `0026_teacher_review_notes.sql`, private
`teacher_review_note` RPC, and `GET/PUT/DELETE /teacher/jobs/{job_id}/note` are implemented.
The RPC handles the partial-index upsert and locks the book/classroom for atomic switch checks.
GET/PUT return a note row; DELETE returns `204`, or the standard `404` for a missing note.
UUID validation precedes the job query. Settings and child endpoints remain out of scope.

Verification: `uv run pytest tests/test_review_notes.py tests/test_rls_isolation.py -k review_notes -q`
against local synthetic PostgreSQL: **29 passed**. The complete targeted files: **59 passed,
9 failed**; the unchanged HEAD RLS file reproduces all nine failures (old browser approval-grant
expectations and invalid profile fixtures). Existing SELECT policy checks using valid fixtures pass.
All eight deliberate removals of HTTP/database guards produced the intended failing tests.
`uv run ruff check .` and `uv run python -m compileall -q app/review_notes.py` pass.
Standards and spec reviews have no remaining findings. No remote migration was applied.
Final full suite, `uv run pytest -q --tb=short`: **1,574 passed, 130 skipped, 6 deselected,
6 failed**. All failures are PDF tests returning `503` because this Windows runtime lacks
WeasyPrint native libraries. The six also reproduce in `uv run pytest tests/test_pdf_export.py -q`.
The skipped suites include the default unreachable database checks; the notes privilege and
concurrency tests were separately run against the local synthetic database above. Provider smoke
tests remain deselected by design. No frontend checks were run because no frontend code changed.
