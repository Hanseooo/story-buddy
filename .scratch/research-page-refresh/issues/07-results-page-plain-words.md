# 07 — Results page in plain words with the false-alarm tradeoff

**Status:** ready-for-agent
**Type:** task
**Progress:** open
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
