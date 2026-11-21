# 14 — /research/architecture and /research/ethics pages

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** Groupmates find the components, specifications and ethics basis, each with its source.
**Source criteria:** US-18 AC-15–AC-18, US-19 AC-19–AC-22; SH-01–SH-03, SH-06, SH-08
**Scope:** Two new pages under `frontend/app/(research)/research/(reference)/`: components table, Tables 5–8 with sources, development hardware (confirmed rows only); ethics basis, consent, privacy disclosure, safety measures.
**Out of scope:** Supplying unconfirmed hardware rows (owner, in `hardware_and_hosting.md`).
**Complexity:** Medium — many sourced values
**Blast radius:** Local — new pages
**Unblocks:** 15

## Context
`docs/specs/research-page-refresh/04-chapter-pages.md` US-18, US-19.

## Read first
- `backend/pipeline/config.py` — model IDs
- `backend/pyproject.toml`, `frontend/package.json` — versions
- `docs/capstone/hardware_and_hosting.md` (after 02)
- `docs/capstone/ethics_and_safety.md` (after 02)

## Behavior this changes
None

## Acceptance criteria
- [ ] Every US-18 and US-19 AC is met
- [ ] Each spec value has a test reading its source
- [ ] Consent says only the teacher's signed hard-copy consent (D-22)
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
Versions come from the files; don't type them into tests.

## Verification
**Targeted:** `pnpm exec vitest run "app/(research)"` from `frontend/`
**Full suite:** at the batch gate

## Blocked by
01, 02, 09, 11
