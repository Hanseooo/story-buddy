# 06 — Character magic pencil at the reveal

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Blocked by:** `.scratch/ptd-child-creative-control/issues/04-draw-again-undoable-at-reveal.md`

**Parent:** `docs/specs/magic-pencil.md` (US-02, US-06)
**What to build:** Beside "Draw again", each pictured character has "Magic pencil". The child writes a
change. The text is redacted, then moderated; a flag holds for the teacher with no image drawn.
Cleared text edits the current reference once (no judge), the result passes reference moderation,
and the child chooses "Keep this" or "Use the old one". Every use is logged.
**Source criteria:** US-02 / AC-06, AC-07, AC-08, AC-09, AC-10 (flag holds; replacement is 07), AC-11;
SH-03, SH-04, SH-05, SH-07, SH-08, SH-10; US-06 / AC-22 (character target); OD-08
**Scope:** the pencil request through the reveal resume; redaction before any storage, log or model
call; text moderation; a new pencil-text hold kind; one `edit_image` call with the fixed keep clause;
shared 3-go allowance; keep/old with the losing picture kept as a version; the log row; the process
page pencil UI; one `research-changelog.md` row
**Out of scope:** teacher replacement of a held result (07); child changes in later page prompts (08);
page pencil (10)
**Complexity:** High — a new resume action, a new hold kind with a request-only stop, and a pending
keep/old state that survives the tab closing
**Blast radius:** Shared — graph routing at the reveal, the hold contract and teacher queue, a
check-constraint migration on `job_moderation_reviews.kind`, the process page
**Unblocks:** 07, 08

## Context
ADR-082 Decisions 2–3. OD-08 (owner, 2026-11-01): a teacher stop on a held pencil text ends only the
request. The reveal returns with the old picture and the story continues.

## Read first
- `backend/pipeline/reveal.py` — `reveal`, `_project_reveal` (`taps_left`)
- `backend/pipeline/char_bible.py` — `_mint_targeted` (go accounting, `ref_generation_prompt`)
- `backend/providers.py` — `redact_pii`, `check_text`, `edit_image`, `is_fal_content_flag`
- `backend/pipeline/char_ref_mod.py` — `_hold_reference`; `backend/pipeline/graph.py` — `moderation_router`, `route_reveal`
- `backend/app/moderation_hold.py` — `confirm_review_job`, `stop_held_job`, `teacher_review_detail`
- `backend/contracts/story_memory.py` — `ReviewContext.kind`; `supabase/migrations/0022_teacher_moderation_hold.sql` — `kind` check
- `frontend/app/s/[profileId]/process/[jobId]/page.tsx`; `frontend/components/NeedsHelpQueue.tsx`

## Behavior this changes
- `MAX_RETRY_TAPS` becomes the shared go count for "Draw again" and the pencil (AC-06); the
  "redraws left" copy is pinned in `process/[jobId]/page.test.tsx` and changes on purpose.
- `stop_held_job` stops the whole story; for a pencil-text hold it must not (OD-08).

## Acceptance criteria
- [ ] Text box labelled, capped at `MAX_PENCIL_CHARS` (~200) with a count; submit disabled when empty
      or whitespace; goes left shown (AC-07).
- [ ] Raw text is never persisted or logged; a redaction failure rejects with a retryable message and
      spends nothing (SH-03).
- [ ] Flagged text: hold with "Your teacher is taking a look", no image, no go; teacher allow runs the
      edit; teacher stop ends only the request and the reveal returns (AC-08, SH-05, OD-08).
- [ ] Cleared text: one `edit_image` on the current reference, no `judge` call, one go spent (AC-09).
- [ ] Result flagged by `char_ref_mod`: held under the ADR-080 reference hold; go spent (AC-10).
- [ ] fal refusal: "We couldn't change this picture. Try different words.", no go spent (SH-04).
- [ ] "Use the old one" restores the old reference and keeps the new one as a version; closing the
      tab leaves the old one current and the choice waiting (AC-11).
- [ ] Stale source rejected and double submit spends once (SH-08); the text reaches the model as
      written after redaction, in any language (SH-10).
- [ ] Log row: job, target, before, after or reason, redacted text, moderation outcome, choice (AC-22).
- [ ] All SH-07 states, focus, Escape/Enter and named controls; Draw again disabled with the reason
      at 0 goes.

## Guidance
Suggestion: model it on the `try_again` loop (reveal → edit in `char_bible` → `char_ref_mod` →
reveal), so the result is moderated by the existing node. Trap: `require_reference_clearance` raises
if any current reference is not cleared. Keep the unmoderated result as a pending candidate and leave
the current reference unchanged until it clears and the child keeps it.

## Verification
API and worker tests, providers mocked (spec §6.2–6.3); vitest; one `playwright-cli` pass for US-02.
**Targeted:** `cd backend && uv run pytest tests/test_reveal_node.py tests/test_char_bible_node.py tests/test_char_ref_mod_node.py tests/test_teacher_hold.py tests/test_graph.py tests/test_main.py` · `cd frontend && pnpm exec vitest run "app/s/[profileId]/process/[jobId]/page.test.tsx"`
**Full suite:** required now (Shared)

## Blocked by
04. Pencil free text does not *ship* before `ptd-moderation-calibration` audit 01 (release gate, not
a build gate).

## Comments

## Answer (2026-11-02)

Done on feature jobs only (`has_versions`). The pencil request is a `pencil` confirm with the text and
the picture on screen. The API strips the text, caps it at `app.config.MAX_PENCIL_CHARS` (200),
redacts it (failure: 503, nothing spent) and moderates it (error: 503). Only the redacted text goes
past the API.

- **Cleared.** `char_bible` makes one `edit_image` call with the text and `PENCIL_KEEP_CLAUSE`. There
  is no judge call and one shared go is spent. A fal flag records `reason="refused"`, spends nothing,
  and the reveal shows "We couldn't change this picture. Try different words."
- **Flagged.** The hold is a new `character_pencil_text` kind, with no picture and no go spent. The
  child sees "Your teacher is taking a look" (`/state.pencil_hold`) and has no story stop. Allow runs
  the edit. "Stop this change" ends only the request, and the reveal comes back with the old picture
  and all its goes.
- **Keep/old.** "Keep this" or "Use the old one". "Old" restores the kept picture and keeps the
  result as a version. A stale source, a repeated submit, or a choice on a picture no longer waiting
  changes nothing (SH-08).
- **Log.** Every use is a `job_picture_records` row (`kind='pencil'`, migration 0029). It holds the
  before, the after or the reason, the redacted text, both moderation outcomes, and the choice.

Deviations:
- **The result is current while the choice waits.** The ticket guidance said to keep it as a
  pending candidate. Instead the result is the current reference with `ref_moderation_status=None`,
  so `char_ref_mod` and the ADR-080 reference hold handle it unchanged (AC-10). The old picture is a
  version. The API refuses `confirm` (422 `choice_pending`) and the UI hides the other tools and
  disables Continue until the child chooses, so the book cannot go on with an unchosen result. The
  spec's "the old one stays current" is not met literally. Closing the tab leaves the choice waiting
  with the new picture shown and the old one beside it.
- **A teacher stop on the AC-10 reference hold of a pencil result stops the story**, as any
  ADR-080 reference hold does.
- **The keep clause drops "its colours"** from the probe's clause, because the child may be asking
  for a colour change.
- **The pencil is offered only on a classifier-passed picture.** A teacher-allowed picture is
  never kept as a version (ticket 04), so "Use the old one" could not bring it back. The API and
  `char_bible` refuse it too.
- **A teacher-allowed pencil result is dropped, not kept, when the child picks "Use the old
  one"**, for the same reason. Its log row keeps the `teacher_allowed` outcome.
- **A removed child's pencil hold:** "Stop this change" stops the story, because nobody can come
  back to the reveal.
- Baseline jobs keep the old "redraws left" copy.

Checks: unit tests on reveal, char_bible, the contract and main, and Postgres integration runs for
cleared text (redaction, dedup, stale, keep/old, log row), redaction failure, and flagged text (stop,
allow, stop for a removed child). Each new test went red first. Frontend: vitest for every SH-07
state, focus, Escape/Enter, the shared-goes copy, keep/old, the held-pencil copy, and the teacher
queue (fixture captured from the integration run). Full suites: backend has only the 6 known
`test_pdf_export` failures (local PDF `OSError`, as on HEAD). Frontend lint, build and 784 tests
pass.

Not done or not verified:
- **No `playwright-cli` pass for US-02** (login wall, real fal edits).
- Migration 0029 must be applied to any hosted DB before the setting is turned on, after 0028.
- The `coalesce` that keeps a teacher-allowed outcome in the log row has no test of its own.
- Pencil free text must not ship before `ptd-moderation-calibration` audit 01.
- AC-12 (the change reaches later pages) is ticket 08. Teacher replacement of a held result is 07,
  and until then `moderation_replace` reports `replacement_source_unavailable` for it.
