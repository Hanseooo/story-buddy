# 08 — Limitations page brought up to November

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
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

## Answer
`/research/limitations` is brought up to November. Every new count is pinned to its source doc in `data.test.ts` (SH-02), and group-guide 5.4 and 6 carry the same wording.
- Reference-check card: fails 15 of 17 bad references and 15 of 38 good ones (about 4 in 10, ADR-082). Page-check card: 23 of the 71 redrawn first drafts were already acceptable. A totals sentence explains 77 + 71 + 2 = 150.
- Duplicates count redrawn drafts (28 of 221) and finished pages (15 of 150). The klein bars add missed action (8 vs 2) and name the one rater. No-reference groups carry 24% vs 10%.
- Stated body counts names the magic pencil (on by default, children's wording unmeasured). A new tried row records the November 1 chip-only edit (2 of 9, rejected). The banner says generation versions 6 and 7 and 500-word stories are unmeasured.
- Two new limitations (11 in all): the reference check cannot verify stated details, and the stricter backstop stopped 4 of 30 synthetic stories. No human-review sentence (D-23), no "don-" ids.
- Charts use `ChartFigure`. Ids: `reference-check-outcomes`, `page-check-outcomes`. PNG links point at `/research/diagrams/<id>.png`; ticket 11 creates the files.
- Red before green: data tests failed on missing exports, 4 page tests failed on missing sections, then all 33 passed.
