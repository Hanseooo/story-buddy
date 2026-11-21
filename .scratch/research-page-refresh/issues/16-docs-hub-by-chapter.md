# 16 — Docs hub grouped by paper chapter

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** `/research/docs` groups docs by chapter and shows what the paper must say.
**Source criteria:** US-25 AC-03–AC-07; SH-02, SH-04
**Scope:** Edit `frontend/app/(research)/research/(reference)/docs/*`: chapter groups, new entries, last-changed dates, the panel with corrections and typos.
**Out of scope:** Fixing the paper itself (groupmates).
**Complexity:** Medium — date source decision and the panel
**Blast radius:** Local — one page
**Unblocks:** None

## Context
`docs/specs/research-page-refresh/06-source-docs.md` US-25; P-rows in `evidence/audit-3-docs-paper.md`.

## Read first
- `frontend/app/(research)/research/(reference)/docs/entries.ts`, `entries.test.ts` — `REQUIRED`
- `frontend/app/(research)/research/(reference)/docs/page.tsx`
- `docs/capstone/research-changelog.md` §1

## Behavior this changes
The pipeline diagram entry's "as it runs today" wording changes unless 09 has landed.

## Acceptance criteria
- [ ] Every US-25 AC is met
- [ ] New entries are in `REQUIRED`
- [ ] Open items show as open
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
Pick "Last reviewed" or git date for AC-04 and record the choice.

## Verification
**Targeted:** `pnpm exec vitest run "app/(research)"` from `frontend/`
**Full suite:** at the batch gate

## Blocked by
02, 03
