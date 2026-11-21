# 13 — /research/methodology and /research/instruments pages

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** Groupmates find the design, setting, corpus and both instruments stated as in the repo.
**Source criteria:** US-16 AC-06–AC-10, US-17 AC-11–AC-14; SH-02, SH-03, SH-07
**Scope:** Two new pages under `frontend/app/(research)/research/(reference)/`. The instruments page shows the 7 expert questions, the 23 ISO items under six headings, "Survey pending", and "Content analysis or thematic analysis (to be decided)" (O-04).
**Out of scope:** Choosing the analysis method (O-04, GitHub issue).
**Complexity:** Low — quoting tracked docs
**Blast radius:** Local — new pages
**Unblocks:** 15

## Context
`docs/specs/research-page-refresh/04-chapter-pages.md` US-16, US-17.

## Read first
- `docs/capstone/expert-evaluation-questionnaire.md`, `iso-25010-questionnaire.md` (from 03)
- `docs/capstone/methodology.md` §1
- `docs/product/PHASE_05_RESULTS.md`

## Behavior this changes
None

## Acceptance criteria
- [ ] Every US-16 and US-17 AC is met
- [ ] Both implementation sites shown as undecided (O-07)
- [ ] No researcher contact details
- [ ] Question and item text pinned to the tracked docs
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
None

## Verification
**Targeted:** `pnpm exec vitest run "app/(research)"` from `frontend/`
**Full suite:** at the batch gate

## Blocked by
01, 02, 03
