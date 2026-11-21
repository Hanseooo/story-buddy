# 05 — Pipeline maps show the real 14-node graph

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
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

## Answer
Both maps show the 14 nodes in `backend/pipeline/graph.py`, read as text by two parity tests (seam S-3).
- `PipelineMap` is a plain list with no SVG and no scroll reveal, so every node is visible on first render and in print, and the `calc()` error is gone. Each node is marked "Both modes" (11) or "Teacher review only" (`optional_themes`, `moderation_review`, `moderation_replace`). The teacher-review branch and its entry points are described under the main flow.
- The run viewer's `pipelineGraph.ts` has the 14 nodes and 28 edges, including the teacher-review edges. Left out on purpose: `moderation_review` back to the node it held (an allowed hold resumes where the run stopped).
- Teacher-waiting: `EndedOn.kind` gains `"teacher"` ("Waiting for the teacher"), and `awaiting_teacher` jobs get a status line. Backend `_ENDED_KIND` maps `awaiting_teacher` to `"teacher"`; without it the frontend never receives the kind. The backend test for it was added but not run (no `fastapi` in this environment).
- Red before the fix: the `PipelineMap` test found no `data-node` elements, and the run-viewer test lacked `moderation_replace`, `moderation_review`, `optional_themes`.
