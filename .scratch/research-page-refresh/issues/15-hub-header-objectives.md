# 15 — Research hub, header, Previous/Next and objectives page

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** `/research` is a static hub; every page has the header and Previous/Next; `/research/objectives` answers each objective.
**Source criteria:** US-01 AC-01–AC-03, AC-05; US-02 AC-06–AC-09; US-03 AC-10–AC-15; SH-04, SH-07, SH-10; D-24, D-26
**Scope:** Rewrite `frontend/app/(research)/research/page.tsx` as the hub; update `ResearchHeader.tsx` and `RESEARCH_TABS`; add Previous/Next to the reference layout in §4.1 order; new `objectives/` page.
**Out of scope:** Content of the chapter pages (12–14).
**Complexity:** Medium — navigation across every page
**Blast radius:** Shared — the header and layout are on every research page
**Unblocks:** None

## Context
`docs/specs/research-page-refresh/01-hub-and-navigation.md`; reading order in index §4.1.

## Read first
- `frontend/app/(research)/research/page.tsx` — current session read to remove
- `frontend/app/(research)/_shared/components/ResearchHeader.tsx` and `.test.tsx`
- `frontend/app/(research)/_shared/constants.ts` — `RESEARCH_TABS`
- `frontend/app/(research)/research/(reference)/layout.tsx`, `layout.test.tsx`

## Behavior this changes
`ResearchHeader.test.tsx` expectations change for the three-item header; Annotate and Adjudicate stay for researchers (D-24).

## Acceptance criteria
- [ ] Every AC in 01-hub-and-navigation.md is met
- [ ] The hub renders the same logged in and out (D-26)
- [ ] Previous/Next targets follow §4.1, tested
- [ ] Objective 1 says Achieved; 3 and 5 say Survey pending
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
The landing page `/` is out of scope.

## Verification
**Targeted:** `pnpm exec vitest run "app/(research)"` from `frontend/`
**Full suite:** required now: `pnpm test`, `pnpm lint`, `pnpm build` from `frontend/`

## Blocked by
01, 07, 11, 12, 13, 14
