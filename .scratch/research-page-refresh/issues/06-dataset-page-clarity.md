# 06 — Dataset page explains pairs, labels, splits and process

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** A non-ML groupmate can read `/research/dataset` and explain the dataset correctly.
**Source criteria:** US-04 AC-01–04, US-05 AC-05–09, US-06 AC-10–12, US-07 AC-13–18, US-08 AC-19–20, US-09 AC-21–25, US-27 AC-26, AC-28; SH-01–03, SH-05, SH-06, SH-09, SH-10
**Scope:** Edit `frontend/app/(research)/research/(reference)/dataset/page.tsx`, `data.ts`, `data.test.ts`, `page.test.tsx`. Definitions box, one verbatim record, the splits and why, the ten-step process with the dataset-flow figure, corrections, and the labelling-tool section.
**Out of scope:** PNG export mechanics (11).
**Complexity:** Medium — much copy, each sentence pinned
**Blast radius:** Local — one page
**Unblocks:** None

## Context
Full criteria: `docs/specs/research-page-refresh/02-dataset.md`. Draft copy: `evidence/audit-1-dataset.md` B1–B8.

## Read first
- `frontend/app/(research)/research/(reference)/dataset/page.tsx` — current sections; `:147` and `:156-160` are wrong
- `frontend/app/(research)/research/(reference)/dataset/data.test.ts` — the pin pattern
- `data/judge/freezes/obj4-v1/manifest.val.jsonl` — row `033b8372e89e4c06`
- `docs/specs/research-labelling-demo.md` — for AC-28

## Behavior this changes
The "795" sentence, the human/non-human table and "No test label changed" are corrected (US-09, US-05 AC-08). The existing tests pinning them change.

## Acceptance criteria
- [ ] Every AC in 02-dataset.md is met
- [ ] The shown JSON is checked against the manifest (red if one field is altered)
- [ ] The split totals test reads the runbook (red if a runbook total changes)
- [ ] Clothing-or-style-is-Same is visible at 390px next to the reasons table
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
Shorten long values with "…" only; never reformat the JSON.

## Verification
**Targeted:** `pnpm exec vitest run "app/(research)"` from `frontend/`
**Full suite:** at the batch gate

## Blocked by
03 (labelling-tool reasons), 04 (runbook facts), 10 (dataset-flow figure)

## Answer

- `/research/dataset` rewritten: definitions box, what a pair is, ten steps with the dataset-flow figure (inline SVG copy, PNG download link, GitHub source link), one verbatim record plus a 13-field table, labelling rules and who decided, why the team built its own tool, splits and why test is donated-only, corrected human/non-human table, agreement, examples, training record. Files: `dataset/{page.tsx,data.ts,data.test.ts,page.test.tsx}`, `public/research/diagrams/dataset_build_and_annotation_flow.drawio.svg` (byte copy, tested).
- New fact recorded first (SH-02): the 14 constructed matches are 12 human with human and 2 tortoise with tortoise. Runbook entry "Constructed matches" and one changelog row. Counted read-only from the freeze and corpus run memories.
- Tests: split rows, reason counts and agreement read the runbook (red when a runbook row changes). The verbatim record is compared with `manifest.val.jsonl` (red when a field is altered); it runs where the freeze exists, including a worktree via the main checkout, and skips elsewhere.
- AC-28: `/annotate?demo=1` sits behind researcher sign-in (middleware) and no tracked demo screenshots exist, so the page links the demo spec and says the demo needs sign-in.
- Deviation from AC-14: the page says "12 of the 15 donated candidate stories finished" and that the 3 failures are not in the dataset. It does not say they were replaced by backups, because no tracked doc states it.
- The PNG is not created. Ticket 11 exports it. The download link will 404 until then.
