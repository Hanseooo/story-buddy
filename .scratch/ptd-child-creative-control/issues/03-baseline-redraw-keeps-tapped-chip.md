# 03 — Baseline: a flagged "Draw again" picture is redrawn with the tapped chip

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Blocked by:** None

**Parent:** `docs/specs/magic-pencil.md` (US-07)
**What to build:** In a baseline-mode job, when `char_ref_mod` flags a reference that a "Draw again" tap
produced, the one automatic moderation redraw is a single draw from that tap's prompt, including
`Be sure to include: {chip}.`. Untapped references keep today's untargeted 3-draw re-mint.
**Source criteria:** US-07 / AC-23, AC-24, AC-25; edge-case rows "Baseline job: …" (×3)
**Scope:** `char_bible` (record the tap prompt in baseline, targeted moderation redraw), the
`char_ref_mod` → `char_bible` redraw route, tests, one `research-changelog.md` row
**Out of scope:** teacher-review mode (its replacement already reads `ref_generation_prompt`); the
setting from SH-01 (this ships normally, not behind it); everything else in the spec (04–11)
**Complexity:** Medium — a flag clears the picture, so the redraw must know it came from a tap after
`canonical_ref_image` is already `None`
**Blast radius:** Local — the reference prelude of baseline jobs; corpus runs never tap (`build_corpus`
auto-confirms), so the corpus path is unchanged
**Unblocks:** None

## Context
Closes `docs/specs/reference-moderation-retry.md` §8.1 for baseline (ADR-082 Decision 7). Not behind
the new setting: it corrects existing behaviour.

## Read first
- `backend/pipeline/char_bible.py` — `_mint_targeted`, `char_bible`, `mint_reference`: how a tap draws and how a flagged ref is re-minted
- `backend/pipeline/char_ref_mod.py` — `char_ref_mod`: the baseline flag sets `ref_moderation_status="flagged"` and `canonical_ref_image=None`
- `backend/pipeline/graph.py` — `moderation_router`: the `MAX_MOD_REDRAWS` route back to `char_bible`
- `backend/contracts/story_memory.py` — `Character.ref_generation_prompt`, `Cost.ref_mod_retry_count`
- `docs/specs/reference-moderation-retry.md` — §4.5, §4.6 ("The redraw flags too"), §8.1
- `backend/tests/test_char_bible_node.py`, `backend/tests/test_graph.py` — existing redraw tests

## Behavior this changes
- Today a flagged tapped reference in baseline is re-minted untargeted (3 draws, chip lost). AC-23
  replaces that with one targeted draw. Any test in `test_char_bible_node.py` / `test_graph.py` that
  pins an untargeted re-mint after a tap is overturned on purpose; tests for an untapped flag stay.

## Acceptance criteria
- [ ] Baseline job, tap on chip X, the result is flagged: exactly one `text_to_image` call, whose
      prompt contains `Be sure to include: X.` (AC-23).
- [ ] That redraw advances `ref_mod_retry_count`, not `ref_retry_count`; `image_count` rises by 1 (AC-24).
- [ ] The redraw flags too: the job fails with `ref_flagged`, as today (AC-24).
- [ ] An untapped initial reference that is flagged still gets the untargeted re-mint (AC-25).
- [ ] Teacher-review jobs are unchanged (their flag holds).
- [ ] One `research-changelog.md` row records the pipeline change.

## Guidance
Trap: `ref_generation_prompt` is set only when `moderation_mode == "teacher_review_v1"` in both
`_mint_targeted` and `char_bible`, so AC-23's "recorded prompt" does not exist in baseline today
(spec drift, flagged in the breakdown). Suggestion: record the tap's prompt in baseline as well, and
in `char_bible` route a flagged character whose recorded prompt came from a tap to a one-draw path.
Keep `n` on the shared per-book sequence so the flagged object survives as evidence.

## Verification
Worker seam, providers mocked (spec §6.6). Red first: run the new test against today's code; it must
fail on the 3-draw re-mint.
**Targeted:** `cd backend && uv run pytest tests/test_char_bible_node.py tests/test_char_ref_mod_node.py tests/test_graph.py`
**Full suite:** at the batch gate (`uv run ruff check . && uv run pytest`)

## Blocked by
None.

## Comments

## Answer (2026-11-01)

Done. In baseline, `_mint_targeted` now records the tap's `ref_generation_prompt`. When that
character comes back flagged, `char_bible` replays the prompt in one draw (`_redraw_recorded`,
shared with `replace_reference`) at the shared suffix `n`, spending `ref_mod_retry_count`. Untapped
flags keep the 3-draw re-mint; teacher-review is gated out. Tests: two at the `char_bible` node
(AC-23/24 red on 3 draws before the fix; AC-25) and one graph run tap → flag → redraw → flag →
`ref_flagged` (red before the fix). Spec lines updated in `reference-moderation-retry.md`,
`moderation-stack.md`, `character-bible.md`; one `research-changelog.md` row.

Not done: the replay path, like `mint_reference` and `_mint_targeted`, does not call
`check_image_budget()` itself (AGENTS.md invariant); inherited, left as is.
