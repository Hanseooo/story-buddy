# 07 — A held character pencil result is replaced by re-running the same edit

**Status:** ready-for-agent
**Type:** task
**Progress:** open
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
