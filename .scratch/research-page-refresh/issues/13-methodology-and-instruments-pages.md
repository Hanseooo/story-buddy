# 13 â€” /research/methodology and /research/instruments pages

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** Groupmates find the design, setting, corpus and both instruments stated as in the repo.
**Source criteria:** US-16 AC-06â€“AC-10, US-17 AC-11â€“AC-14; SH-02, SH-03, SH-07
**Scope:** Two new pages under `frontend/app/(research)/research/(reference)/`. The instruments page shows the 7 expert questions, the 23 ISO items under six headings, "Survey pending", and "Content analysis or thematic analysis (to be decided)" (O-04).
**Out of scope:** Choosing the analysis method (O-04, GitHub issue).
**Complexity:** Low â€” quoting tracked docs
**Blast radius:** Local â€” new pages
**Unblocks:** 15

## Context
`docs/specs/research-page-refresh/04-chapter-pages.md` US-16, US-17.

## Read first
- `docs/capstone/expert-evaluation-questionnaire.md`, `iso-25010-questionnaire.md` (from 03)
- `docs/capstone/methodology.md` Â§1
- `docs/product/PHASE_05_RESULTS.md`

## Behavior this changes
None

## Acceptance criteria
- [ ] Every US-16 and US-17 AC is met
- [ ] Both implementation sites shown as undecided (O-07)
- [ ] No researcher contact details
- [ ] Question and item text pinned to the tracked docs
- [ ] The shared rules listed under the source stories hold (index Â§2)

## Guidance
None

## Verification
**Targeted:** `pnpm exec vitest run "app/(research)"` from `frontend/`
**Full suite:** at the batch gate

## Blocked by
01, 02, 03


## Answer
Added `/research/methodology` and `/research/instruments` under `frontend/app/(research)/research/(reference)/`, each with `page.tsx`, `data.ts`, `data.test.ts` and `page.test.tsx`. Data tests pin every sentence, the 7 question headings with prompts, and the 23 ISO items (6 headings) to the tracked docs, and check the form has no more or fewer entries. Both implementation sites show as "Undecided"; both instruments show "Survey pending"; the analysis method shows "Content analysis or thematic analysis (to be decided)". Deviations: the Phase 3 gate cell is left out (it says "content-analysed", which O-04 leaves open); "collected through their teachers" is not in a tracked doc, so the setting cites the teacher's hard-copy consent agreement from `ethics_and_safety.md` instead. Drift found: `methodology.md` sections 3.3 and 3.4 still describe the superseded expert validators and five criteria.
