# 15 — Research hub, header, Previous/Next and objectives page

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
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

## Answer
`/research` is a static hub, the header has three items, every reading-order page has a back link and Previous/Next, and `/research/objectives` answers the five objectives.
- One page list: `_shared/readingOrder.ts` (title, route, group, one line, paper sections, in order). The hub, `PageNav` (Previous/Next) and the tests all use it. `readingOrder.test.ts` pins titles, routes, groups and order to index 4.1, and the paper section names to the audit's paper map.
- Hub: no session or profile read (a test fails if the Supabase client is called), header `showAccount` off, no PipelineMap, no "11 deterministic nodes", self-host or marketing copy.
- Header: Research home (current only on the hub itself), Docs, Runs, plus role-gated Annotate and Adjudicate, which still work where the layout passes the viewer (annotate, adjudicate, metrics).
- Objectives: wording pinned to `research_direction_and_goals.md`. Objective 1 Achieved (no Tool A). Objective 2: 42 books, 30 synthetic and 12 donated; 15 donated collected, 12 generated, three did not finish (two invalid_terminal, one budget_stopped). Objectives 3 and 5: "Survey pending" only. Objective 4: F1 0.31 vs 0.47, the verbatim tradeoff sentence, the partial note, link to Results.
- Polish: `ChartFigure` has a `wide` prop (pipeline, architecture and dataset diagrams use the full width; charts keep `max-w-3xl`); the dataset figure now uses `ChartFigure`. `ScrollTable` shows a "Scrolls sideways" label and an edge fade only while it overflows.
- Drift: AC-13 says the three donated stories "were replaced by backup stories of the same style". No tracked doc says that, so the page uses the sourced wording (methodology.md 3.3 and 4.1, obj4-readiness-audit.md section 7, changelog row 2026-09-16 to 17). AC-11 asks every objective for Evidence, but AC-14 and D-10 say Objectives 3 and 5 show "Survey pending" and nothing else, so they have no Evidence list. The app has no skip link, so AC-08's "skip" link does not exist; Tab goes logo, header links, back link, content, Previous, Next.
- Found in the real browser: the dataset figure's source file name did not wrap at 390px and made the page scroll sideways. Fixed in `ChartFigure` (`break-all`), with a test.
- Red before green: each new test file failed on the missing module or old markup first. Breaking the Objective 2 wording in `data.ts` failed its data and page tests.
