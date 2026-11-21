# 16 — Docs hub grouped by paper chapter

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
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

## Answer

`/research/docs` now groups 38 entries under 8 paper-chapter headings, each with a last-changed date, above a "What the paper must say" panel.

- **Entries:** added audit-3 D6 and D7, both questionnaires, ADR-083, `hardware_and_hosting.md` and the five new diagrams. All are in `entries.test.ts`. `functional-verification-matrix.md` is listed but labelled dropped (D-28).
- **AC-04 date choice:** a literal `lastChanged` per entry in `entries.ts`, not a "Last reviewed" line (most docs have none) and not a runtime git call (no git at Vercel build or in a shallow checkout). `entries.test.ts` fails when the literal is older than the file's last author date in git, and skips the comparison where git history is unusable. Cost: editing a listed doc later makes that test red until its date is bumped.
- **AC-07:** the pipeline diagram's own subtitle says "as built 2026-11-21", so its entry now says "as built on 2026-11-21, in both baseline and teacher-review modes". "As it runs today" is gone.
- **Panel:** `paper.ts` holds P1-P24 plus C1 (why three donated stories are missing), the nine changelog section 1 points and the four typos. `paper.test.ts` pins every value to a phrase in its source doc (SH-02).
- **Open:** only O-04 (#135), O-07 (#136) and O-12 (#137) show as open, each linked.
- **Donated stories (coordinator ruling):** P6 (13 vs 12) and C1 show as "Repo is right". Twelve were generated. Three ended invalid_terminal or budget_stopped, then were left out on purpose. The changelog row and the spec do not conflict.
- **Deviation:** P7 (who removed names) and P24 (dev hardware CPU and RAM) are shown as "Repo is right" with the repo's wording, not open, to leave only the three open items. Both rest on inferred or unconfirmed evidence.
- **Typo "considerable":** the corrected word "substantial" comes from audit-2 P10 (Landis and Koch), not a repo doc.
