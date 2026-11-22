# 05 — Diagrams and exports

Index: [../research-page-refresh.md](../research-page-refresh.md). Evidence:
`evidence/audit-4-diagrams.md` (element-by-element tables), `evidence/decode.py` (reads the mxfile
inside a `.drawio.svg`). Every diagram is authored as `.drawio.svg` (ADR-065 decision 3): GitHub
draws it and draw.io still edits it.

## US-20 Update the existing diagrams

As a groupmate, I want the diagrams to match the system as built, so that the paper's figures are
true.

Applies: SH-06, SH-08

- **AC-01** `langgraph_pipeline_after_2026-10.drawio.svg` is replaced with a current pipeline
  diagram. It shows:
  - 14 nodes, adding `optional_themes`, `moderation_review` and `moderation_replace`
  - the second interrupt
  - the reveal → `moderation_review` edge
  - the reveal → `char_bible` edges for choose_version, pencil and pencil_choice
  - up to two redraws per page
  - "flag → job fails" marked as baseline mode only, with the teacher hold shown for
    teacher-review mode
  - the page magic pencil, as a separate job outside the graph (`app/page_pencil.py`)

  The subtitle says "as built <date>".
- **AC-02** `langgraph_pipeline_before_2026-07.drawio.svg` and `langgraph_pipeline.excalidraw` are
  labelled "Planned design, July 2026 (not as built)". Their content is unchanged.
- **AC-03** `system_architecture.drawio` is redrawn as `system_architecture.drawio.svg` with the
  US-18 AC-16 components:
  - Northflank instead of Railway
  - Mistral Small 3.2 as the text model instead of Qwen
  - every draw uploaded to Storage

  The old `.drawio` and `system_architecture.excalidraw` are removed once the redraw exists, so only
  one copy remains.

## US-21 New diagrams

As a groupmate, I want the figures the paper and pages need, so that empty figure slots get filled.

Applies: SH-06

- **AC-04** These new `.drawio.svg` files are created. Each lists its source files in a
  note inside the diagram:
  1. the IPO model (paper Figure 1, Appendix A)
  2. the dataset build and annotation flow (US-08)
  3. the student journey: write, wait, reveal, try again, magic pencil, other versions, read, notes
  4. the teacher journey: review, approve or reject, the hold, notes, PDF

  Source files for each are listed in `evidence/audit-4-diagrams.md` §(b).
- **AC-05** Not created (D-13): ER model, teacher-hold sequence, moderation-layer map, fine-tune and
  evaluation flow, expert and ISO evaluation flow.

## US-22 PNG export

As a groupmate, I want every figure as a PNG, so that I can paste it into the paper.

Applies: SH-06

- **AC-06** One script, run by hand from `frontend/`, renders every `docs/diagrams/drawio/*.drawio.svg`
  and every chart from US-13 and US-14 in Chromium through Playwright:
  - light colour scheme, white background, 2× device scale
  - a screenshot of the `<svg>` element
  - output to `frontend/public/research/diagrams/<name>.png`
- **AC-07** The script writes `frontend/public/research/diagrams/manifest.json` with each PNG's name,
  its source path and the SHA-256 of the source file.
- **AC-08** A vitest test fails when a source's SHA-256 differs from the manifest, naming the
  diagram to re-export.
- **AC-09** A vitest test fails when a diagram linked from any page or from `docs/entries.ts` has no
  PNG.
- **AC-10** No new dependency: Playwright and Chromium are already installed. If that turns out
  wrong, stop and ask (AGENTS.md: new dependency).

## US-23 Run viewer's pipeline map

As a researcher inspecting a run, I want the run viewer's map to show the current nodes, so that
runs through the new nodes are not shown as "not on this map".

Applies: SH-08

- **AC-11** `metrics/[jobId]/pipelineGraph.ts` includes the 14 nodes and the teacher-review edges.
  The "checked" date is updated.
- **AC-12** A test compares its node list with `backend/pipeline/graph.py`.
- **AC-13** A run waiting on the teacher shows a teacher-waiting state, not "Waiting for the child".
