# 05 — Pipeline maps show the real 14-node graph

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** `PipelineMap` and the run viewer's map show the 14 nodes of `graph.py`, all visible, with no console error.
**Source criteria:** US-01 AC-04; US-15 AC-04; US-23 AC-11–AC-13; SH-08; D-25
**Scope:** Fix the SVG `calc()` path error. Add `optional_themes`, `moderation_review`, `moderation_replace` and the teacher-review edges. Remove the scroll-triggered hiding. Add a teacher-waiting state to the run viewer. Add parity tests that read `graph.py` as text (seam S-3).
**Out of scope:** Moving the map to `/research/pipeline` (12). The drawio diagrams (09).
**Complexity:** Medium — SVG layout plus mode-specific edges
**Blast radius:** Shared — the landing page and the run viewer
**Unblocks:** 12

## Context
The audit found 11 vs 14 nodes and a console error on `/research` (`evidence/audit-5-render.md` F1, F2).

## Read first
- `frontend/components/PipelineMap.tsx` — the node list, the SVG `d` attributes and the reveal animation
- `frontend/app/(research)/research/metrics/[jobId]/pipelineGraph.ts` and `.test.ts`
- `backend/pipeline/graph.py` — the `add_node` names
- `frontend/app/(research)/research/(reference)/results/data.test.ts` — the repo-root `read()` helper

## Behavior this changes
`pipelineGraph.test.ts` expectations for the node set change. A run inside the new nodes no longer shows "not on this map".

## Acceptance criteria
- [ ] The parity test goes red against today's 11-node list, then green
- [ ] No `calc()` inside an SVG `d` attribute
- [ ] Every node visible on first render; reduced motion is respected
- [ ] A teacher-held run shows a teacher-waiting state, not "Waiting for the child"
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
Read node names with a regex on `add_node("…"`; don't import Python.

## Verification
**Targeted:** `pnpm exec vitest run "app/(research)"` from `frontend/`
**Full suite:** required now: `pnpm test`, `pnpm lint`, `pnpm build` from `frontend/`

## Blocked by
None
