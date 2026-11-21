# 12 — /research/pipeline page

**Status:** ready-for-agent
**Type:** task
**Progress:** open
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
