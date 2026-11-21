# 07 — Results page in plain words with the false-alarm tradeoff

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** `/research/results` says what the judge result means, without overstating it.
**Source criteria:** US-10 AC-01–07, US-11 AC-08, US-12 AC-09, US-13 AC-11; SH-02, SH-03, SH-05, SH-09
**Scope:** Edit `frontend/app/(research)/research/(reference)/results/*`. How-to-read box, the verbatim tradeoff sentence, the accuracy table, McNemar in words, partial-status note, the checkpoint finding, recommendations, and chart data in `data.ts`.
**Out of scope:** Chart PNG files (11).
**Complexity:** Medium — statistics in plain words, each pinned
**Blast radius:** Local — one page
**Unblocks:** 11, 15

## Context
Measured table and verbatim sentence: `docs/specs/research-page-refresh/03-results-and-limitations.md`.

## Read first
- `frontend/app/(research)/research/(reference)/results/page.tsx` — `:337` and `:447` change
- `frontend/app/(research)/research/(reference)/results/data.ts`, `data.test.ts` — the `between`/`states` helpers
- `data/judge/evaluations/obj4-v1/heldout-1/qwen_comparison.partial.json` — read only

## Behavior this changes
"part of why their recall is low" becomes "may lower their recall"; the "possible explanation" bullet is replaced.

## Acceptance criteria
- [ ] The AC-02 sentence appears verbatim
- [ ] No ROC or threshold curve is promised
- [ ] Recommendations 2–4 are marked untested
- [ ] Chart values come from `data.ts`
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
Never run scoring scripts.

## Verification
**Targeted:** `pnpm exec vitest run "app/(research)"` from `frontend/`
**Full suite:** at the batch gate

## Blocked by
04

## Answer
`/research/results` now opens with a "How to read this page" box (catch, miss, false alarm, precision, recall, F1) and a "What the scores show" section that carries the AC-02 sentence verbatim. Every new fact is pinned to a source doc by `data.test.ts` (SH-02).
- Accuracy table with the always-Same baseline (85.7%), McNemar in words (40 vs 65 wrong pairs), a partial-status bullet, the B-6 unreadable sentence, and a "What we recommend" section with items 2 to 4 marked untested.
- The checkpoint "possible explanation" bullet is now a measured lead (tie table plus chart), with three untested explanations left. The runbook gained all 57 validation checkpoint rows and a "No score to sweep" paragraph, the changelog a matching row, and group-guide 5.2 the tradeoff sentence, the unreadable sentence and the recommendations.
- No ROC or threshold curve is promised: AUROC is null for all four judges.
- Charts use the new `ChartFigure` (SH-06). Ids: `judge-confusion-matrices`, `judge-f1-precision-recall`, `judge-catches-false-alarms`, `judge-validation-checkpoints`. PNG links point at `/research/diagrams/<id>.png`; ticket 11 creates the files.
- Red before green: the new data tests failed on missing exports (9 failed), the page tests failed on missing sections (11 failed), then both passed.
- Deviation: AC-08 says both seeds answered Same from checkpoint 130. The runbook and the CSV show seed 0 from 120 and seed 1 from 130, so the page says that.
