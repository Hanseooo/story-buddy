# Changelog

What changed in the repository, one entry per merged PR, newest first. The baseline at the bottom
is `main` as it stood before PR #101.

**How to add an entry.** In the PR itself, add a section at the top: the PR number and date, the
issues it closes or refers to, and what changed under Code, Docs and Checks. Sub-issues of the
defense-prep audit ([#102](https://github.com/Hanseooo/story-buddy/issues/102)) each add one when
their PR merges.

**What does not go here.** What a change means for the paper (findings, deviations, limitations)
goes in [`docs/capstone/research-changelog.md`](docs/capstone/research-changelog.md). Link to it
instead of repeating it.

---

## Direct to `main` · 2026-10-09 (agreement and sensitivity)

Objective 4's registered agreement and sensitivity analyses.
Refs [#94](https://github.com/Hanseooo/story-buddy/issues/94), #102

### Docs

- `research_runbook.md`: new section "Registered agreement and sensitivity analyses (2026-10-09)"
  with inter-rater κ, the guide-boundary split and the ambiguous-reference secondary analysis.
- `research-changelog.md`: Finding row and a κ line in §1. `group-guide.md` §5.2: κ and the
  secondary result in plain words. `ROADMAP.md` C3-02: dated status.

### Checks

- Analysis script (local, git-ignored) verifies the signed lock, manifest and prediction hashes,
  and that database labels equal the freeze labels, before computing anything. No model calls.

---

## Direct to `main` · 2026-10-09

Retry count and Objective 4 table corrections from the defense-prep audit.
Closes [#109](https://github.com/Hanseooo/story-buddy/issues/109) · Refs #102, #94

### Code

- **`/research` page copy**: the pipeline map and the "Targeted Regeneration" bullet said one
  retry; the code allows three attempts with the best kept (`settings.max_scene_attempts = 3`,
  ADR-037).

### Docs

- `group-guide.md` §3: same retry correction. §5.2: the Objective 4 table adds unreadable
  (unparsed) answers per judge (3 / 40 / 44 / 8 of 329), says they score as "same character", and
  cites the local result JSON as the numbers' source.
- `research-changelog.md`: the 2026-10-08 finding row cites the same JSON and the unparsed counts.
- `system_architecture.md`: same retry correction.

### Checks

- Frontend `pnpm lint && pnpm build && pnpm test`.

---

## PR #101 · 2026-10-09

Segment species fix, Objective 4 resume, October probes, group guide.
[PR #101](https://github.com/Hanseooo/story-buddy/pull/101) · Closes #28 · Refs #65, #94, #98, #100

### Code

- **`segment`** adds a cast member when the drawing direction names it by a unique species noun
  ("the moth" adds Ashwing). `human` never matches, a noun two cast members share is skipped, and
  plurals stay groups. (`19cc743`, `docs/specs/scene-segmentation.md`)
- **`analyze`** drops a schema key that leaked into object axes. (`2b15d25`)
- **`providers`**: a fal image flagged inside an HTTP 200 is treated as a content flag. (`80ebd6f`)
- **Styles**: hidden `pixel` trial preset behind `ENABLE_PIXEL_STYLE` and
  `NEXT_PUBLIC_ENABLE_PIXEL_STYLE`, both off by default; migration `0020`; redrawn `cut_paper`
  card. (`9f9d166`)
- **Objective 4 evaluation** (`backend/finetune/evaluate.py`): validation and held-out capture
  reuse verified saved prediction files and capture only the missing ones; HTTP 401 aborts instead
  of scoring as malformed; the CLIP control reads `pooler_output`. (`4fe5072`)
- **`/research` page**: the pipeline map shows all 11 graph nodes and the models in use; it had
  said 10 nodes and named Qwen3-32B and qwen3-vl-32b, both replaced on 2026-08-11. (`a87dbfb`)

### Docs

- October model probes: findings ledger, klein probes and blinded screen, one-moment direction
  test, limitations table (`docs/capstone/model-probes-2026-10.md`). ADR-062 and ADR-063: klein
  rejected, Qwen-Image-Edit stays.
- Pipeline stage audit, provisional and AI-scored (`docs/capstone/pipeline-stage-audit-2026-10.md`).
- Plain-language start page (`docs/capstone/group-guide.md`) and research changelog
  (`docs/capstone/research-changelog.md`), both linked from `AGENTS.md`.
- Diagrams: the July LangGraph drawio renamed `langgraph_pipeline_before_2026-07.drawio`;
  `langgraph_pipeline_after_2026-10.drawio` drawn from `graph.py`, with a list of what changed.
- `ROADMAP.md`: dated status on C3-02, 04, 05 and 13; C3-10 and C3-11 closed. A stray cp1252 byte
  that made the file invalid UTF-8 replaced.
- Stale moderation text in `TECH_STACK.md`, `moderation-stack.md` and `AGENTS.md` (#28).
- `AGENTS.md` rewritten from 828 to 224 lines: wrong facts fixed (two raters plus adjudication,
  migration numbering, export cut), the build log and dated history cut, still-true gotchas moved to
  Project Invariants and a new Known Gaps section.
- Root `CHANGELOG.md` added (this file).

### Checks

- Backend: `ruff` clean; `pytest` 1457 passed, 87 skipped. CI green on `f2f8c0e`.
- Frontend: `eslint` and `tsc` clean; `vitest` 529 passed; `/research` checked in a browser.
- Fixed on the way: a checksum test only failed its file on Windows, where CRLF translation changed
  the bytes; it now writes a wrong digest instead. (`7fa2d53`)

---

## Baseline: `main` at `863a16f` · 2026-10-06

The state before PR #101, for comparison.

- **Pipeline**: 11 LangGraph nodes, the reveal included. Text `mistral-small-3.2-24b-instruct`,
  references `fal-ai/qwen-image`, scene editor `fal-ai/qwen-image-edit-2511`, product judge
  prompted `gemma-3-27b-it`. `segment` added cast members only by name.
- **Objective 4**: three Qwen3.5-9B seeds trained and backed up; no held-out result yet.
- **C3 follow-up**: the September gate audit and the C3-01 to C3-13 tasks in `ROADMAP.md`; no
  October probes, no stage audit.
- **Known stale**: `/research` said 10 nodes and named retired models; the only LangGraph diagram
  was from July and missed the reveal; #28 open.
