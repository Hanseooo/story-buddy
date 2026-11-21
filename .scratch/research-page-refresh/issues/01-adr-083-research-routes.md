# 01 — ADR-083: new research routes and hub

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** ADR-083 exists with status Accepted (2026-11-21) and has its row in `docs/product/ADRs.md`.
**Source criteria:** US-26 AC-08, AC-09; D-01–D-03, D-13, D-19
**Scope:** One new ADR file plus its index row. It records the new static public routes, `/research` as the hub, the three-item header and the PNG export of diagrams. It extends ADR-065/066/067 and keeps their static, synthetic-only rules.
**Out of scope:** Any page code (tickets 12–15).
**Complexity:** Low — one doc in the existing ADR format
**Blast radius:** Local — documentation only
**Unblocks:** 12, 13, 14, 15

## Context
Project rule: frozen ADRs need a new ADR before routes are built. The owner accepted it in the grill session (D-19). See `docs/specs/research-page-refresh.md` §3.

## Read first
- `docs/product/ADRs.md` — the last rows: index format
- `docs/product/adr/ADR-065-*.md` — decisions 1–7 being extended
- `docs/product/adr/ADR-082-magic-pencil-child-edits-and-other-versions.md` — the latest ADR shape

## Behavior this changes
None

## Acceptance criteria
- [ ] ADR-083 file and `ADRs.md` row exist; status Accepted, dated 2026-11-21
- [ ] It lists the new routes (`/research/pipeline`, `methodology`, `instruments`, `architecture`, `ethics`, `objectives`), the hub, the header (D-03) and PNG export (D-13)
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
Copy the newest ADR's heading layout. Name what it extends; don't restate ADR-065.

## Verification
Read it against D-01–D-03, D-13 and D-19. No tests.
**Full suite:** not needed (docs only)

## Blocked by
None
