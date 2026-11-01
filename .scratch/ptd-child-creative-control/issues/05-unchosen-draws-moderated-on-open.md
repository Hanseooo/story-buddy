# 05 — Unchosen first-round character pictures, moderated when opened

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
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

## Answer (2026-11-01)

Done on feature jobs only (`has_versions`: `ENABLE_MAGIC_PENCIL` snapshot and `teacher_review_v1`).

- **Kept.** The initial mint uploads its up to 2 unchosen judged draws at
  `{story_id}/ref-<char>-<n>-u<draw>.png` (own suffix, same prefix, so a tap or redraw cannot collide
  and story deletion removes them) and records them as `ReferenceVersion(source="unchosen_draw")`
  with `ref_moderation_status=None` and their own verdict. Not on a moderation re-mint. Without the
  feature, `mint_reference` uploads exactly once, as before.
- **Projection.** The reveal lists them by id only (`unreviewed`), no path. The worker drops ids
  already stored as excluded, so a character whose kept draws all failed loses the control at the
  next pause (AC-01).
- **On open.** `POST /jobs/{id}/characters/{char_id}/versions/open`, in the API, same gate as the
  image route. Each unreviewed draw goes through `char_ref_mod.screen_reference` (primary, then
  backstop; primary error falls back; backstop or signing error is unchecked). The outcome is stored
  once in `job_picture_records.moderation_status` (migration 0028, `passed`/`excluded`, first write
  wins). A flag is excluded, never shown, no review row. An error stores nothing, counts as
  `unavailable`, and the page shows "We couldn't load this picture right now." with retry.
- **Delivery and choice.** `authorized_asset` serves a draw whose record is `passed`.
  `confirm_review_job` accepts choosing it and adds `cleared: true` to the resume (not a client
  field); `_choose_version` restores it as `passed`, otherwise as in 04.

Checks: worker test (draws 1 and 3 kept on best-of draw 2; non-feature uploads once), reveal and
contract tests, and one Postgres integration run (kept → not served → open: pass shown, error
unavailable and not stored → second open re-checks only the errored one, flag excluded → third open
spends nothing → no review row → excluded choice 422 → passed choice restored → excluded id gone
from the next reveal). Guards broken on purpose went red: image guard, error stored as excluded,
confirm skipping the record, flag shown, unavailable message, open call. Full suites: backend 1644
passed, 6 failed (`test_pdf_export`, local PDF `OSError`, as on HEAD); frontend lint, build, 773 tests.

Not done or not verified:
- **No `playwright-cli` pass** (login wall, real draws).
- Migration 0028 must be applied to any hosted DB before the setting is turned on, after 0027.
- Two concurrent opens can each pay for a classifier call; the stored outcome is still one.
- Within the same pause, a character whose draws were all excluded keeps the control and shows
  "There are no other pictures of <name> right now." until the next pause.
- On-open checks store the outcome only, not `ClassifierEvidence`; nothing holds on them (OD-03).
- `screen_reference` does not retry a signing failure as `char_ref_mod` does; it shows the retryable message.
