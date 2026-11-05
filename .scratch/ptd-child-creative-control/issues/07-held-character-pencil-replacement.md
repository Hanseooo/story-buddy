# 07 — A held character pencil result is replaced by re-running the same edit

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Blocked by:** `.scratch/ptd-child-creative-control/issues/06-character-pencil-at-reveal.md`

**Parent:** `docs/specs/magic-pencil.md` (US-02)
**What to build:** When a teacher asks to replace a held pencil result, the worker runs the same edit
once more (same source picture, same redacted text) in ADR-080's per-book replacement slot. It does
not make a fresh text-to-image draw. The new result is moderated, then offered for keep or old.
**Source criteria:** US-02 / AC-10 (replacement); edge row "Held pencil result: teacher requests a replacement"
**Scope:** the replacement branch for a pencil-produced reference; its budget and slot checks; tests
**Out of scope:** "Draw again" replacement (unchanged, `replace_reference`); page replacement (11)
**Complexity:** Medium — the replacement must recognise a pencil result and reuse its exact inputs
**Blast radius:** Local — the reference replacement path for feature jobs
**Unblocks:** None

## Context
ADR-080's replacement for references redraws from `ref_generation_prompt` with `text_to_image`. For
a pencil result that would throw away the child's edit, which AC-10 rules out.

## Read first
- `backend/pipeline/char_bible.py` — `replace_reference`
- `backend/pipeline/moderation_replace.py` — `moderation_replace`, `reference_replacement_disabled_reason`
- `backend/app/moderation_hold.py` — `teacher_decision` (`replace` branch)
- what ticket 06 records as the pencil result's source picture and redacted text

## Behavior this changes
None for non-pencil references. `replace_reference` tests stay green.

## Acceptance criteria
- [ ] Held pencil result, teacher picks replace: one `edit_image` call with the recorded source and
      redacted text; no `text_to_image` call; `ref_mod_retry_count` advances (AC-10).
- [ ] Replacement slot used or `IMAGE_BUDGET` reached: replace is unavailable with the existing reason.
- [ ] The new result passes `char_ref_mod`; on pass the child sees keep/old; on flag it holds again
      as ADR-080 does.
- [ ] The log row for that pencil use records the replacement outcome (AC-22).

## Guidance
Trap: `replacement_disabled_reason` is also called from `teacher_review_detail` to set
`replacement_available`. Keep both callers consistent.

## Verification
Worker test, providers mocked; extend the replacement tests in `test_teacher_hold.py`.
**Targeted:** `cd backend && uv run pytest tests/test_teacher_hold.py tests/test_char_bible_node.py`
**Full suite:** at the batch gate

## Blocked by
06.

## Comments

## Answer (2026-11-02)

Done. When the held reference is a pencil result (the `PencilUse` whose `after_path` is current),
`replace_reference` makes one `edit_image` call with that use's redacted text plus
`PENCIL_KEEP_CLAUSE` on its `before_path` picture. It makes no `text_to_image` or judge call. It
spends ADR-080's slot (`ref_mod_retry_count` +1, `image_count` +1) and no child go. The use's
`after_path` moves to the new picture, and `char_ref_mod` moderates it. On pass, the reveal offers
keep/old. On flag, it holds again with `replacement_already_used`.
`reference_replacement_disabled_reason` no longer refuses pencil results, so `teacher_review_detail`
and `teacher_decision` both see the same slot and budget reasons.

Deviations:
- **The choice is reset.** A held pencil result that already has a choice can only be a kept result
  whose clearance a teacher withdrew. The replacement is a new picture, so the child is asked keep/old
  again and the row's earlier "kept" is cleared.
- **No new log column.** The use's row (AC-22) now shows the replacement picture and its moderation
  outcome. `record_pencil_uses` runs only at the reveal and hold projections, both after
  `char_ref_mod`, so the row never shows the new picture with the old outcome. The replaced, flagged
  picture is still in the first review's subject.
- A fal refusal of the replacement edit propagates, as it does for every ADR-080 replacement.

Checks: unit test of the replacement in `test_char_bible_node.py` (it replaces the ticket-06 test
that pinned the refusal). Postgres integration test in `test_teacher_hold.py` for three cases:
passes (keep/old, two goes left, row `passed`), flags again (new hold, `replacement_already_used`,
row `flagged`), and budget (422 `image_budget_exhausted`, no edit). The integration cases went red
on HEAD's code, and red again when the edit branch was switched off, falling back to the fresh draw.
Full backend suite with the disposable DB: 1,675 passed, 101 skipped. The only failures are the six
known `test_pdf_export` ones (native PDF `OSError`). No frontend change.

Not done or not verified: no test for a fal refusal on the replacement edit. No browser pass.
