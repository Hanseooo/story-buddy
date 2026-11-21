# 07 — Verification

Index: [../research-page-refresh.md](../research-page-refresh.md). **Nothing here has been run for
this change.** The results recorded below are the 2026-11-21 audit baseline, not evidence that the
change works.

## 1. Test seams (S-1 to S-4 approved by the owner, 2026-11-21; S-5 dropped, D-18)

| Seam | What it covers | Precedent |
|---|---|---|
| S-1 Page data module + `data.test.ts` | Every page value or sentence appears in its named source doc or data file (SH-02). Covers US-04–US-19, US-24. | `results/data.test.ts` (`between`, `states`); ADR-066 decision 6 |
| S-2 Page render test `page.test.tsx` | Rendered headings, the definitions box, "Survey pending", Previous/Next targets, back link, header items (SH-04, SH-07). | existing `page.test.tsx` per reference page; `ResearchHeader.test.tsx` |
| S-3 Graph parity test | Node names on the pipeline page, `PipelineMap` and `pipelineGraph.ts` equal the `add_node` names in `backend/pipeline/graph.py`, read as text (SH-08). | `pipelineGraph.test.ts`; the repo-root `read()` helper in `results/data.test.ts` |
| S-4 Figure manifest test | PNG exists for each linked diagram or chart, and the source SHA-256 matches `manifest.json` (US-22 AC-08, AC-09). | `entries.test.ts` (file existence) |
~~S-5 Real browser~~: dropped by the owner (D-18). No E2E runner is added.

**What nothing now checks automatically:**
- console errors
- horizontal scroll at 390px
- the visible scroll cue on wide tables
- Tab order (US-02 AC-08)

The S-2 render tests can assert that the cue and the links exist, but not how they look. If the
owner later wants these checked, `evidence/audit-5-render.md` holds the procedure.

## 2. Each new test fails first

Per the owner's testing rules, each new test is shown red for the intended reason before the change
makes it green:

| Test | Make it red by |
|---|---|
| S-3 | Run it against today's 11-node `PipelineMap`: red. |
| S-4 hash | Edit a diagram without re-exporting: red. |
| S-4 PNG | Delete one PNG: red. |
| S-1 (new facts) | Put the page value in before its runbook entry: red. |
| US-06 AC-12 | Alter one field of the shown JSON: red. |
| US-09 AC-25 | Change a runbook split total: red. |

## 3. Commands (from AGENTS.md)

- Frontend: `pnpm test`, `pnpm lint`, `pnpm build`, run from `frontend/`.
- The targeted research tests: `pnpm exec vitest run "app/(research)"`.
- No real-browser check is required (D-18).
- Do not run the backend scoring scripts (see 03).

## 4. Evidence required to call it done

1. `pnpm test`, `pnpm lint` and `pnpm build` output, all passing.
2. The red-then-green output for each test in §2.
3. (S-5 dropped, D-18.)
4. A grep showing US-24 AC-02 finds no current-state hits.
5. The list of open decisions (index §7) still unresolved at merge, each with the text shown in
   its place.

## 5. Audit baseline (2026-11-21, measured)

- **Page tests:**
  - reference pages: 9 files, 67 tests, passed
  - dataset data: 12/12 passed
  - results and limitations: 36/36 passed
  - docs hub: 18 passed
- **Live render:** all 5 pages returned 200 at both widths. No failed request, no horizontal
  scroll. 1 console error on `/research`: the SVG `calc()` path.
- **Main-session spot-checks:**
  - 14 `add_node` calls in `graph.py`
  - `max_scene_attempts = 3`
  - text model Mistral Small 3.2
  - 9 clothing/style-only Different labels (train 6, validation 1, test 2)
  - held-out FP/FN: seed 1 2/38, base 47/18
  - `hardware_and_hosting.md` is 4 bytes
