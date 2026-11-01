# 10 — Page magic pencil on the finished book

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Blocked by:** `.scratch/ptd-child-creative-control/issues/09-page-other-versions.md`

**Parent:** `docs/specs/magic-pencil.md` (US-04, US-06)
**What to build:** Each page of a finished feature book shows "Magic pencil" while page pencils remain.
The text is redacted and moderated. Cleared text edits that page's current picture once in a small
worker task outside the graph, and the result passes output moderation. The child keeps it or goes
back. Any flag holds for the teacher while the book stays readable with its current pictures.
**Source criteria:** US-04 / AC-16, AC-17, AC-18 (hold, allow, stop), AC-19; SH-03, SH-04, SH-05,
SH-07, SH-08, SH-09, SH-10; US-06 / AC-22 (page target); US-05 / AC-20 re-verified for a kept
result; OD-01, OD-07; edge rows on fal refusal, page pencils used up / `image_count` at 55, held
page result stopped, child closes the tab
**Scope:** pencil endpoint, enqueue of the page-edit worker task; `check_image_budget()` against the
job's `image_count`; 5 page pencils per book; pencil hold kinds in `job_moderation_reviews` on a
`complete` job (OD-07); teacher allow/stop for those holds; keep/old updating `jobs.pages`; log row;
book page UI; one `research-changelog.md` row
**Out of scope:** teacher replacement of a held page result (11); character canon (a page edit never
changes it, AC-19)
**Complexity:** High — an out-of-graph worker task with exact spend, plus holds that must not pause or
hide a finished book
**Blast radius:** Shared — ADR-080 hold queries (teacher queue, decision endpoint, delivery guard),
a `kind` check migration, worker queue, book page
**Unblocks:** 11

## Context
OD-07 (owner, 2026-11-01): reuse `job_moderation_reviews` with pencil kinds; the job stays `complete`.
Three ADR-080 assumptions break and must be relaxed for pencil kinds only: `authorized_asset` 404s
while any review is open; `teacher_review_list` filters on `awaiting_teacher`; `teacher_decision`
requires `awaiting_teacher` and resumes the graph through `dispatch_review`.

## Read first
- `backend/app/moderation_hold.py` — `authorized_asset`, `teacher_review_list`, `teacher_decision`, `stop_held_job`, `dispatch_review`
- `backend/worker/run_job.py` — the completion write and the image-count update; `backend/worker/run_worker.py`
- `backend/pipeline/output_mod.py` — `_check_image`; `backend/providers.py` — `edit_image`, `redact_pii`, `check_text`
- `backend/app/config.py` — `check_image_budget`, `IMAGE_BUDGET`
- ticket 06's pencil-text kind and log row; ticket 09's page write and approval reset
- `frontend/app/s/[profileId]/book/[jobId]/page.tsx`; `frontend/components/NeedsHelpQueue.tsx`

## Behavior this changes
- The `job_moderation_one_open` index still allows one open review per job. A second pencil while
  one is held is disabled (SH-07). The teacher queue lists `complete` jobs with an open pencil review.

## Acceptance criteria
- [ ] Control shown only while page pencils remain and `image_count < IMAGE_BUDGET`; otherwise
      disabled with the reason; versions still work (AC-16, SH-04).
- [ ] Redaction before storage; flagged text holds, no image; book stays readable (AC-17, SH-05).
- [ ] Cleared text: one `edit_image` on that page's current picture; output moderation before
      display; one page pencil and one image spent (AC-18).
- [ ] Flagged result: held; the book keeps its current picture; teacher allow offers keep/old;
      teacher stop ends only the request; the book is never stopped (AC-18).
- [ ] fal refusal: no image, no pencil spent, the "Try different words" message (SH-04).
- [ ] Keep updates `jobs.pages` and resets approval as in 09; "Use the old one" keeps the result as
      a version; canon untouched (AC-19, AC-20).
- [ ] Stale source rejected; double submit spends once; tab closed mid-request still completes (SH-08).
- [ ] Log row per use (AC-22); UI states, focus and names with the page number (SH-07).

## Guidance
Trap: the checkpoint must stay unchanged (OD-01). Do not run this through the graph or
`PostgresSaver`. Suggestion: one RQ task keyed by the request id, like `dispatch_review`'s unique job
id, so a retry cannot spend twice.

## Verification
Worker test of the page-edit task (refusal, flagged result), API tests for holds and budget,
providers mocked; vitest; `playwright-cli` pass for US-04.
**Targeted:** `cd backend && uv run pytest tests/test_teacher_hold.py tests/test_run_job.py tests/test_main.py tests/test_review.py` · `cd frontend && pnpm exec vitest run "app/s/[profileId]/book/[jobId]/page.test.tsx"`
**Full suite:** required now (Shared)

## Blocked by
09 (page write, approval reset, guard on `jobs.pages`). Free-text release gate as in 06.

## Comments
