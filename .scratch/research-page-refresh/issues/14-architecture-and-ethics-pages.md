# 14 — /research/architecture and /research/ethics pages

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
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

## Answer
`/research/architecture` and `/research/ethics` are built under `(reference)/`. Every value or quote is pinned to its source file in `data.test.ts` (SH-02, SH-08).
- Architecture: diagram figure (alt text, "As of 2026-11-21", PNG download, GitHub source link), an 18-row components table with source files, model IDs read from `config.py`, library versions read from `pyproject.toml` and `package.json`, training hardware copied from `hardware_and_hosting.md` section 7, hosting, and development hardware. Only the RTX 3050 Ti 4 GB is confirmed; the other three rows read "Owner to supply".
- Ethics: basis (D-08), consent (D-22, teacher's signed hard-copy consent only, no separate parental consent, expert evaluators sign their own form), privacy (D-07, D-09, ADR-045 person names not replaced by default), a moderation-layer table with where each runs, teacher approval, ADR-080, ADR-081, ADR-082 limits (200 characters, 5 page pencils), and a "not claimed" list.
- Drift found: the runbook line for the 3050 Ti is 711, not 549 as the spec and `hardware_and_hosting.md` say. The page cites 711 and a test pins the line. `ethics_and_safety.md` section 4 still describes guardian consent as the plan (it says so itself).
- Red before green: all four test files failed on the missing `./data` and `./page`, then 26 passed. Breaking a model ID, a library version, a quote and `MAX_PENCIL_CHARS` in the sources each failed the matching test.
