# 08 — A kept character change is drawn on later pages

**Status:** ready-for-agent
**Type:** task
**Progress:** done
**Blocked by:** `.scratch/ptd-child-creative-control/issues/06-character-pencil-at-reveal.md`

**Parent:** `docs/specs/magic-pencil.md` (US-02)
**What to build:** When the child keeps a pencil result, its redacted text is appended to the
character's child changes. Every later scene prompt for that character renders them after the
description, through ADR-035's style filter, even when they contradict the story.
**Source criteria:** US-02 / AC-12; SH-06; edge rows "Text contradicts the story", "Text uses a
style-forbidden trait", "Old checkpoint without the new fields"
**Scope:** an additive, defaulted `Character` field (ordered list); append on keep; render in
`build_prompt` (roll fold and description lines); style filtering; contract doc; one
`research-changelog.md` row
**Out of scope:** page pencil (page edits never touch canon, AC-19, ticket 10); the analysed
description, which stays unmutated (ADR-069)
**Complexity:** Medium — two render sites in `build_prompt` and the style filter must both apply
**Blast radius:** Shared — `build_prompt` builds every scene prompt; `backend/contracts/` is a
critical path; no `schema_version` bump (ADR-029 §3 precedent)
**Unblocks:** None

## Context
ADR-082 Decision 4 amends ADR-069 for the child only. Without this, pages are drawn from a
description that disagrees with the kept reference (audit 01).

## Read first
- `backend/contracts/story_memory.py` — `Character`; `docs/specs/story-memory-contract.md` §8 (additive fields)
- `backend/pipeline/prompt_optimizer.py` — `build_prompt` (roll fold and `descriptions`), `filtered_description`, `permitted_words`
- `backend/pipeline/char_bible.py` — `_describe` (shared draw/judge describer; the judge must not see child changes)
- `backend/tests/test_prompt_optimizer.py`, `backend/tests/test_story_memory.py`

## Behavior this changes
None for characters without child changes: prompts stay byte-identical. Assert that in tests.

## Acceptance criteria
- [x] Keep → the redacted text is appended; "Use the old one" → nothing appended (AC-12).
- [x] A scene with that character renders its child changes after its description, in order, in
      both the referenced (roll) and unreferenced paths (SH-06).
- [x] A change containing a style-forbidden word (e.g. "glowing" under comic) is stored verbatim and
      filtered out of the rendered prompt (ADR-035).
- [x] A contradicting change ("blue hair" vs story's black) is rendered, not dropped.
- [x] An old checkpoint loads with an empty list; prompts unchanged.
- [x] Contract doc and changelog row updated.

## Guidance
Trap: `_describe` is shared by the draw prompt and the reference judge prompt. Adding child changes
there would make them stated attributes for the judge. Render them in `build_prompt` only.

## Verification
Pure projection tests, no mocks (spec §6.1): hand-written expected prompt strings.
**Targeted:** `cd backend && uv run pytest tests/test_prompt_optimizer.py tests/test_story_memory.py tests/test_generate_scene_node.py`
**Full suite:** required now (Shared, contract)

## Blocked by
06 (the keep action that appends).

## Comments
