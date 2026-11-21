# 08 — Limitations page brought up to November

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** `/research/limitations` states current limits with counts.
**Source criteria:** US-14 AC-12–AC-16; SH-02, SH-03, SH-06
**Scope:** Edit `frontend/app/(research)/research/(reference)/limitations/*`: reference-check counts, November state, two missing limitations, smaller fixes, page-check totals.
**Out of scope:** Chart PNGs (11).
**Complexity:** Low — copy and counts
**Blast radius:** Local — one page
**Unblocks:** 11

## Context
`docs/specs/research-page-refresh/03-results-and-limitations.md` US-14.

## Read first
- `frontend/app/(research)/research/(reference)/limitations/page.tsx`
- `frontend/app/(research)/research/(reference)/limitations/data.test.ts`
- `docs/product/adr/ADR-082-magic-pencil-child-edits-and-other-versions.md` — the 4-in-10 figure

## Behavior this changes
"Finds most bad references" is replaced (AC-12).

## Acceptance criteria
- [ ] Each AC in US-14 AC-12–16 is met
- [ ] 77 + 71 + 2 = 150 is explained
- [ ] No human-review sentence about the backstop (D-23)
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
None

## Verification
**Targeted:** `pnpm exec vitest run "app/(research)"` from `frontend/`
**Full suite:** at the batch gate

## Blocked by
04
