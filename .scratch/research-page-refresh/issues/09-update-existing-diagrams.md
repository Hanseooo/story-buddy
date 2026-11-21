# 09 — Existing diagrams match the system as built

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** The pipeline and architecture diagrams match the code; old designs are labelled as planned.
**Source criteria:** US-20 AC-01–AC-03; SH-06, SH-08
**Scope:** Replace `docs/diagrams/drawio/langgraph_pipeline_after_2026-10.drawio.svg` content; label the July diagram and the excalidraw file as planned; redraw `system_architecture.drawio` as `.drawio.svg` and remove the old copies.
**Out of scope:** New diagrams (10). PNG export (11).
**Complexity:** Medium — hand-authored mxGraph XML
**Blast radius:** Local — diagram files
**Unblocks:** 11, 12, 14

## Context
Element-by-element gaps: `evidence/audit-4-diagrams.md`; reader: `evidence/decode.py`.

## Read first
- `docs/diagrams/drawio/langgraph_pipeline_after_2026-10.drawio.svg` — decode with `decode.py`
- `backend/pipeline/graph.py` — nodes, edges, interrupts
- `backend/app/page_pencil.py` — the separate pencil job
- `backend/app/main.py` — web-tier moderation and Presidio

## Behavior this changes
The docs hub entry saying "as it runs today" stays wrong until this lands (US-25 AC-07).

## Acceptance criteria
- [ ] The pipeline diagram has 14 nodes and the edges in US-20 AC-01, subtitled "as built <date>"
- [ ] Planned diagrams carry the label; content unchanged
- [ ] One architecture copy remains, with the US-18 AC-16 components
- [ ] Each file opens in draw.io (valid mxfile) and renders on GitHub
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
Use the `draw-io-diagram-generator` skill. draw.io desktop is not installed; check by decoding and rendering the SVG in Chromium.

## Verification
Decode each file with `decode.py` and list its nodes against `graph.py`.
**Full suite:** not needed

## Blocked by
None
