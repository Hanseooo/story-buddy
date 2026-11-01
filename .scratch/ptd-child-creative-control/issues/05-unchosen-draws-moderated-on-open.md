# 05 — Unchosen first-round character pictures, moderated when opened

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Blocked by:** `.scratch/ptd-child-creative-control/issues/04-draw-again-undoable-at-reveal.md`

**Parent:** `docs/specs/magic-pencil.md` (US-01)
**What to build:** On feature jobs, the up to 2 draws `mint_reference` did not choose are kept. When
the child opens "Other versions", each unmoderated one is moderated first. A pass is shown. A fail is
marked excluded and hidden, with no hold. A classifier error hides it and shows "We couldn't load
this picture right now."
**Source criteria:** US-01 / AC-02 (unchosen draws), AC-03; SH-02; OD-03; edge row "An unchosen draw
fails moderation when opened"; "Old checkpoint without the new fields"
**Scope:** keep and record unchosen draws (feature jobs only); on-open moderation with the existing
image classifiers; store each outcome once; reveal control for characters that now have versions
from the first round
**Out of scope:** version choice mechanics and delivery (04); page attempts (09)
**Complexity:** Medium — lazy moderation with an exact once-only record, plus the error/flag split
**Blast radius:** Shared — `mint_reference` is the reference mint for every job; gating keeps baseline
and corpus byte-identical
**Unblocks:** None

## Context
ADR-082 Decision 1: already paid for, moderation spent only on what the child opens. Today the other
draws are discarded (`mint_reference` uploads only the winner).

## Read first
- `backend/pipeline/char_bible.py` — `mint_reference`, `_upload`, `char_bible` (the `n` sequence)
- `backend/pipeline/char_ref_mod.py` — `char_ref_mod`: classifier order, error vs flag handling
- `backend/providers.py` — `classify_image_primary`, `classify_image_backstop`
- the table and version delivery added by ticket 04
- `backend/tests/test_char_bible_node.py` — mint tests that count uploads

## Behavior this changes
- Feature jobs upload up to 2 more objects per character. Tests that assert exactly one upload per
  mint must stay true for non-feature jobs; add the feature case beside them.

## Acceptance criteria
- [ ] Feature job, mint picks draw 2 of 3: draws 1 and 3 are stored and recorded as unreviewed
      versions (AC-02). Non-feature jobs and corpus runs upload exactly as today.
- [ ] Opening versions moderates each unreviewed one once; a second open reuses the stored outcome (SH-02).
- [ ] A flagged draw is excluded, never shown, and creates no `job_moderation_reviews` row (AC-03, OD-03).
- [ ] A classifier error is not a flag: the picture is not shown, its outcome is not stored as
      excluded, and the child sees "We couldn't load this picture right now." (SH-02).
- [ ] A character accepted first time with unchosen draws now shows "Other versions" (AC-01).
- [ ] A checkpoint without the new fields loads with no kept draws.

## Guidance
Trap: the per-book `n` suffix in `_upload` is shared across all mint paths. Unchosen draws need a
path that cannot collide with a later tap or moderation redraw. Suggestion: give them their own
suffix within the same `{story_id}/` prefix, so deleting the story removes them. Moderate on open
in the API process, not the worker, because the graph is paused at the reveal.

## Verification
Worker test for the gated uploads; API tests for on-open moderation (flag, pass, error), providers mocked.
**Targeted:** `cd backend && uv run pytest tests/test_char_bible_node.py tests/test_teacher_hold.py tests/test_main.py`
**Full suite:** required now (Shared)

## Blocked by
04 (table, setting snapshot, version delivery).

## Comments
