# 11 — PNG export with a manifest and tests

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** Every diagram and chart has a PNG under `frontend/public/research/diagrams/`, and a test catches a stale or missing one.
**Source criteria:** US-22 AC-06–AC-10; US-13 AC-10; US-14 AC-17; SH-06
**Scope:** One hand-run Playwright script from `frontend/`, `manifest.json` with SHA-256 values, and vitest tests for the hash and existence checks (seam S-4). Charts from 07 and 08.
**Out of scope:** Download links on new pages (12–15 add their own).
**Complexity:** Medium — rendering charts outside the page needs a route or a static render
**Blast radius:** Shared — every page that links a figure
**Unblocks:** 12, 14, 15

## Context
`docs/specs/research-page-refresh/05-diagrams-and-exports.md` US-22.

## Read first
- `frontend/package.json` — confirm Playwright is installed (AC-10)
- `frontend/app/(research)/research/(reference)/docs/entries.ts` and `entries.test.ts` — the existence-test precedent
- `frontend/app/(research)/research/(reference)/results/data.ts` — chart data

## Behavior this changes
None

## Acceptance criteria
- [ ] The hash test goes red after a diagram edit without re-export
- [ ] The existence test goes red when one PNG is deleted
- [ ] Light scheme, white background, 2× scale
- [ ] No new dependency; stop and ask if Playwright is missing
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
Chart PNGs can be screenshots of the rendered chart element on the running page.

## Verification
**Targeted:** `pnpm exec vitest run "app/(research)"` from `frontend/`
**Full suite:** required now: `pnpm test`, `pnpm lint`, `pnpm build` from `frontend/`

## Blocked by
07, 08, 09, 10
