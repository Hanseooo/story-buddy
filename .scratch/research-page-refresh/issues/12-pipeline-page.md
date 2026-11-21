# 12 — /research/pipeline page

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** A groupmate can read the conceptual framework and the current pipeline on one page.
**Source criteria:** US-15 AC-01–AC-05; SH-01–SH-04, SH-06, SH-08, SH-10
**Scope:** New `frontend/app/(research)/research/(reference)/pipeline/` with `page.tsx`, `data.ts`, `data.test.ts`, `page.test.tsx`. IPO figure, pipeline diagram, the 14 nodes by mode, module mapping, caps from `config.py`, failure behaviour per mode, the moved `PipelineMap`.
**Out of scope:** Header and Previous/Next (15).
**Complexity:** Medium — mode-aware explanations
**Blast radius:** Local — a new page
**Unblocks:** 15

## Context
`docs/specs/research-page-refresh/04-chapter-pages.md` US-15.

## Read first
- `backend/pipeline/config.py` — caps
- `frontend/app/(research)/research/(reference)/layout.tsx` — the reference layout
- `frontend/components/PipelineMap.tsx` (after 05)

## Behavior this changes
None

## Acceptance criteria
- [ ] Every US-15 AC is met
- [ ] The node list test compares against `graph.py`
- [ ] Figures have PNG links (SH-06)
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
None

## Verification
**Targeted:** `pnpm exec vitest run "app/(research)"` from `frontend/`
**Full suite:** at the batch gate

## Blocked by
01, 05, 09, 10, 11

## Answer
Resolved 2026-11-21. `/research/pipeline` is live at `frontend/app/(research)/research/(reference)/pipeline/` (`page.tsx`, `data.ts`, `data.test.ts`, `page.test.tsx`).

- Figures: IPO model and current pipeline through `ChartFigure` (alt text, "As of 2026-11-21", PNG download, GitHub link to the `.drawio.svg`). `ChartFigure` gained an optional `sourceNoun` so a diagram's link is not announced as "chart data".
- Nodes: the existing `PipelineMap` (14 nodes, 11 baseline, 3 teacher-review only, all visible on first render) is rendered here. Its node test still compares with `graph.py`. The landing page still imports it until ticket 15.
- Modules: the paper's ten modules mapped to nodes from `system_architecture.md`. Prompt Optimizer, Style Preset and Story Memory Manager are marked not graph nodes.
- Caps (SH-08): pages 10 max and 3 min, 3 attempts, 500 words (300 at corpus time, ADR-068), each pinned to a source line by a test. The 3 "try again" taps are in `backend/pipeline/reveal.py:24`, not `config.py`.
- Failure per mode (ADR-025, ADR-080) and the magic pencil and other versions at the reveal (ADR-082), each pinned to its source text.
- Checked in a real browser at 390px and 1280px: no console errors, no sideways page scroll.
