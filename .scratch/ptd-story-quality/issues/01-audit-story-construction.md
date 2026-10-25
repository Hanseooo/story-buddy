# 01 — Audit: how analyze and segment read a story

**Status:** ready-for-agent
**Type:** research
**Progress:** open
**Blocked by:** None
**Conflict gate:** ADR-013, only if an option rewrites the child's words.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

## Question

Which part of story construction did the panel mean, where does it go wrong on real stories, and
would a written rubric with examples in the prompt fix it?

## Starting evidence (2026-10-25)

- Story reading happens in `backend/pipeline/analyze.py` and `segment.py`
  (`SEGMENT_PROMPT_VERSION = 3`, `segment.py:134`). Specs: `docs/specs/story-analyzer.md`,
  `docs/specs/scene-segmentation.md`.
- Captions are the child's verbatim, post-redaction text (ADR-013). The pipeline does not write the
  words a child reads; it writes scene splits and image directions.
- Runtime models must be open-weight (ADR-015), so a Claude skill cannot run in the pipeline. The
  equivalent is a written rubric plus worked examples in the prompt.
- C3-11 closed 2026-10-08: no open-weight text model beat Mistral on the strict-schema path
  (`docs/product/ROADMAP.md`).
- A prompt change is judged by its rate over many pages, never by one page (ADR-055). Prompt version
  constants bump on any wording change (`AGENTS.md`).

## Investigate

- Ask the owner what the panel pointed at: page breaks, scene choice, image directions, titles, or
  the words themselves.
- On stored synthetic books, the error types in that part, with counts.
- Whether a rubric with examples addresses those types. Propose any paid comparison with a cost.

## Edge cases the answer must cover

- Very short stories (floor of 3 plot points) and stories near the word ceiling (ADR-068).
- Filipino and Taglish stories.

## Done when

- Findings are labelled *measured* or *inferred*, with counts and denominators.
- Options with tradeoffs, cost estimate and a go/no-go.

## Comments
