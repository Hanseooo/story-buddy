# 09 — Other versions of a page on the finished book

**Status:** ready-for-agent
**Type:** task
**Progress:** done
**Blocked by:** `.scratch/ptd-child-creative-control/issues/04-draw-again-undoable-at-reveal.md`

**Parent:** `docs/specs/magic-pencil.md` (US-03, US-05)
**What to build:** On a `complete` feature book that is not held or stopped, a page with more than one
kept attempt shows "Other versions". Unreviewed attempts are moderated when opened. Choosing one
replaces the page picture in the book and the PDF. A change to an approved or rejected book asks
the child to confirm first, then returns the book to pending and takes it out of the gallery.
**Source criteria:** US-03 / AC-13, AC-14, AC-15; US-05 / AC-20, AC-21; SH-02, SH-07, SH-08, SH-09;
OD-01, OD-03; edge rows "Pencil on a page of a book held…", "Book stopped or failed", "Book
approved, child edits a page", "Teacher approves while a page edit is in flight", "PDF export
after an edit", "Teacher review note (ADR-081) points at a page"
**Scope:** page versions from `Scene.attempts` minus `excluded`; on-demand moderation with stored
outcome; a choose-page-version endpoint that updates `jobs.pages` and resets approval in one
transaction; the delivery guard and PDF reading the current `jobs.pages` picture; book page UI with
the confirm dialog and all SH-07 states
**Out of scope:** page pencil (10, 11); page-level approval (excluded by the spec)
**Complexity:** High — moves the complete-book delivery guard off the checkpoint without opening a
path a browser can choose, and keeps approval reset atomic with the page write
**Blast radius:** Shared — `authorized_asset` (every teacher-review image read), PDF export, gallery
visibility, the book page
**Unblocks:** 10

## Context
OD-01: `jobs.pages` is the book and the checkpoint is not changed. That leaves SH-02's "store
`safety_eligibility`" with no home on `Attempt` (spec drift, flagged in the breakdown). Store the
on-demand outcome in the ticket-04 table.

## Read first
- `backend/app/moderation_hold.py` — `authorized_asset` (complete branch reads checkpoint `final_image_ref`), `job_image`
- `backend/app/pdf_export.py` — `_approved_book`, the per-page `authorized_asset` checks
- `backend/app/review.py` — `review_job` (teacher-review branch, `approved_at`/`rejected_at`)
- `backend/worker/run_job.py` — where `pages` is written at completion
- `backend/pipeline/output_mod.py` — `_check_image` (the output moderation call to reuse)
- `frontend/app/s/[profileId]/book/[jobId]/page.tsx` — page signing via `signPaths`; `frontend/app/s/[profileId]/gallery/page.tsx`

## Behavior this changes
- `authorized_asset` for `scene-<id>` on a complete book returns the current `jobs.pages` picture
  when it is an eligible attempt or recorded version, not only checkpoint `final_image_ref`. Existing
  guard tests in `test_teacher_hold.py` and `test_pdf_export.py` must stay green for unedited books.

## Acceptance criteria
- [ ] Only pages with ≥2 non-excluded attempts show the control (AC-13); none on held, stopped,
      failed or non-feature books (SH-09, SH-01).
- [ ] On open, each unreviewed attempt is moderated once; a fail is excluded with no hold; an error
      shows "We couldn't load this picture right now." (AC-14, SH-02).
- [ ] Choosing updates that page in `jobs.pages`; the book page and the PDF show it; no image spent (AC-15).
- [ ] Approved/rejected book: confirm "Your teacher will look at your book again before classmates
      can see it."; Cancel changes nothing; confirm sets pending and removes it from the gallery (AC-20, AC-21).
- [ ] Teacher approves while a change is in flight: the change still returns the book to pending.
- [ ] Stale source rejected, double submit applied once, one request per book in flight (SH-07, SH-08).
- [ ] UI states, focus, Escape/Enter, names with the page number (SH-07).

## Guidance
Trap: `review_job` refuses approval while any review is open. Ticket 10's pencil holds will rely on
that, so leave it. Write `jobs.pages` and clear `approved_at`/`rejected_at` under the same
`for update` row lock.

## Verification
API tests (FastAPI client, providers mocked); vitest on the book page; `playwright-cli` pass for
US-03 and US-05 on a seeded synthetic classroom.
**Targeted:** `cd backend && uv run pytest tests/test_teacher_hold.py tests/test_pdf_export.py tests/test_review.py tests/test_main.py` · `cd frontend && pnpm exec vitest run "app/s/[profileId]/book/[jobId]/page.test.tsx"`
**Full suite:** required now (Shared)

## Blocked by
04 (setting snapshot, table).

## Comments

**2026-11-02 — built.** `POST /jobs/{id}/pages/{scene_id}/versions/open` and `POST /jobs/{id}/pages/{scene_id}/version`
in `app/moderation_hold.py`. Version ids are `<scene_id>-attempt-<index>` into the frozen checkpoint's
`Scene.attempts`. The on-open outcome is a `job_picture_records` row (`source='scene_attempt'`), so no
migration was needed. `authorized_asset` serves `scene-<id>` from `jobs.pages` when it names the cleared or
teacher-allowed final, or (feature jobs only) a cleared or opened-and-passed attempt. It also serves
`page-version-<id>` to the author. The worker marks qualifying pages `other_versions: true` at completion
(`book_pages`). The choice writes `jobs.pages` and clears `approved_at`/`rejected_at` in one `for update`
transaction, and the confirm is browser-side only, so an approval landing mid-change is still cleared.
Decisions taken without the owner: a teacher-allowed attempt that is no longer current is never offered (ticket
04's rule); the control is in the Pages view only, not the Scroll view.
Known gap, fixed 2026-11-03 (code review, see ticket 10): a teacher withdrawal of a scene or text clearance on a complete
book rebuilt `jobs.pages` from the checkpoint finals, so the child's page choices were lost. They now come back on pages
the rerun did not redraw.
Not done: the `playwright-cli` pass on a seeded classroom.

**2026-11-02 — review.** Fixed: `book_pages` counted teacher-allowed attempts that are never offered, so a page
could show "Other versions" with nothing to choose. It now counts the current page plus cleared or unreviewed
attempts (red, then green). Left as they are: focus goes to the panel, not its first button, matching the reveal's
shipped panel (`process/[jobId]/page.tsx`), because the choices are disabled while they load. The one-change-per-book
rule holds per tab, and across tabs the `for update` lock runs the requests one at a time. Two simultaneous opens can
both call the classifier, but only the first stored outcome counts. The flag still stays on after an on-open
exclusion and shows the empty state.
