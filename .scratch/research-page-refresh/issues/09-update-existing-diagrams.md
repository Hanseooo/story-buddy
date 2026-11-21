# 09 — Existing diagrams match the system as built

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
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
- [x] The pipeline diagram has 14 nodes and the edges in US-20 AC-01, subtitled "as built <date>"
- [x] Planned diagrams carry the label; content unchanged
- [x] One architecture copy remains, with the US-18 AC-16 components
- [x] Each file opens in draw.io (valid mxfile) and renders on GitHub
- [x] The shared rules listed under the source stories hold (index §2)

## Guidance
Use the `draw-io-diagram-generator` skill. draw.io desktop is not installed; check by decoding and rendering the SVG in Chromium.

## Verification
Decode each file with `decode.py` and list its nodes against `graph.py`.
**Full suite:** not needed

## Blocked by
None

## Answer

Done 2026-11-21. Drawn from `backend/pipeline/graph.py`, `reveal.py`, `moderation_review.py`, `char_ref_mod.py`, `app/page_pencil.py`, `worker/page_pencil.py`, `app/main.py`, `app/config.py` and the frontend Supabase client.

- `docs/diagrams/drawio/langgraph_pipeline_after_2026-10.drawio.svg` replaced (same name), subtitled "as built 2026-11-21". It shows the 14 nodes, `moderation_review` as the second interrupt, the reveal edges to `char_bible` and `moderation_review`, up to 2 redraws per page, baseline fail versus review-mode teacher hold, and the page magic pencil as a separate job.
- `langgraph_pipeline_before_2026-07.drawio.svg` and `docs/diagrams/excalidraw/langgraph_pipeline.excalidraw` carry "Planned design, July 2026 (not as built)". Their content is unchanged.
- `docs/diagrams/drawio/system_architecture.drawio.svg` added (Northflank, Mistral Small 3.2, Supabase Auth and Storage, Redis, OpenRouter, fal.ai, Presidio and web-tier moderation, Langfuse, Sentry). The old `system_architecture.drawio` and `.excalidraw` are deleted.
- Code over ticket: no host region is drawn (docs say Singapore, the paper says North America, code does not settle it). "Flag fails the job" is marked baseline only. Redraws come from `max_scene_attempts=3`, so up to 2 per page. `MAX_RETRY_TAPS=3` is shared by Draw again and the pencil.
- Each file was decoded with `decode.py` and rendered in Chromium with no overlaps. The docs hub caption "as it runs today" is left for US-25.
