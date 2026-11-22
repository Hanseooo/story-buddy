# 11 — PNG export with a manifest and tests

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
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

## Answer

Resolved 2026-11-21. All 13 figures are PNGs in `frontend/public/research/diagrams/` with a `manifest.json`, and a test catches a stale or missing one.

- Script: `frontend/scripts/export-research-figures.mjs`, run by hand from `frontend/` with `pnpm dev` up (`node scripts/export-research-figures.mjs [baseUrl]`). Owner decision: no dependency. It uses node's stdlib and the globally installed `playwright-cli` (Chromium, light scheme, 2x device scale), not a Playwright dependency. The header lists the prerequisites and outputs.
- Diagrams (7, every `docs/diagrams/drawio/*.drawio.svg`, the planned July diagram included, D-13): `<drawio name>.png`, each in the manifest with its source path and SHA-256. The `.drawio.svg` is inlined in a white page with 12px padding, because the browser blocks `file:` URLs and hangs on a bare `.svg` URL.
- Charts (6): the `[data-chart-id]` figure on `/research/results` and `/research/limitations`, restyled for the export to a white, square, flat card with the download links removed.
- `system_architecture.drawio.svg`: group label is now "Northflank, North America" (D-07) in the embedded mxfile and the visible SVG, moved to the bottom of the group so the REST arrow does not cross it. The subtitle no longer says the diagram shows no host region.
- Tests: `app/(research)/research/(reference)/docs/figures.test.ts` (S-4). Hash match, drawio set equals manifest set, every manifest PNG exists, every `/research/diagrams/*.png` link under `app/(research)` exists. Red first on an edited diagram (names the file) and on a deleted PNG (names the PNG). The dataset page's byte-copy SVG identity test is untouched and passes.
- Known gap: the two check charts show a 1 px off-white line on their top edge from sub-pixel layout.
