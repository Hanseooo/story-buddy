# 11 — A held page pencil result is replaced by re-running the same edit

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Blocked by:** `.scratch/ptd-child-creative-control/issues/10-page-pencil-on-finished-book.md`

**Parent:** `docs/specs/magic-pencil.md` (US-04)
**What to build:** When a teacher asks to replace a held page pencil result, the page-edit task runs
the same edit once more (same source picture, same redacted text) within the replacement slot and
the budget. The new result is moderated, then offered to the child for keep or old.
**Source criteria:** US-04 / AC-18 (replacement); edge row "Held pencil result: teacher requests a replacement"
**Scope:** the replace decision for page pencil kinds; slot and budget checks; re-enqueue of the
page-edit task; tests
**Out of scope:** scene replacement during the run (`moderation_replace`, unchanged); character
replacement (07)
**Complexity:** Medium — reuses ticket 10's task with a replacement flag and one more limit
**Blast radius:** Local — page pencil holds only
**Unblocks:** None

## Context
Mirrors 07 for pages. `scene_replacement_disabled_reason` reads checkpoint attempts, which do not
include pencil results (OD-01). The slot for a page pencil result is counted from the pencil log.

## Read first
- `backend/pipeline/moderation_replace.py` — `replacement_disabled_reason`, `scene_replacement_disabled_reason`
- `backend/app/moderation_hold.py` — `teacher_decision` (`replace`), `teacher_review_detail` (`replacement_available`)
- ticket 10's page-edit task and log row

## Behavior this changes
None for in-run scene holds.

## Acceptance criteria
- [ ] Held page result, teacher replaces: one `edit_image` with the recorded source and text; no
      `text_to_image`; one image spent (AC-18).
- [ ] Slot used or `image_count` at `IMAGE_BUDGET`: replace unavailable with the reason in the dialog.
- [ ] New result moderated; pass → keep/old for the child; flag → held again.
- [ ] The log row records the replacement outcome (AC-22).

## Guidance
Keep `replacement_disabled_reason` the one function both `teacher_review_detail` and
`teacher_decision` call, so the dialog and the endpoint cannot disagree.

## Verification
API and worker tests, providers mocked.
**Targeted:** `cd backend && uv run pytest tests/test_teacher_hold.py tests/test_run_job.py`
**Full suite:** at the batch gate

## Blocked by
10.

## Comments
