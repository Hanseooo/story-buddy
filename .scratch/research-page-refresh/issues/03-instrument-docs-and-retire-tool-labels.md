# 03 — Questionnaire docs and retiring Tool A/B/C

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** Both questionnaires exist as tracked docs, and no live doc uses Tool A/B/C.
**Source criteria:** US-24 AC-10, AC-13; US-28 AC-14–AC-18; D-05, D-06, D-21, D-27, D-28; O-12
**Scope:** New `docs/capstone/expert-evaluation-questionnaire.md` and `docs/capstone/iso-25010-questionnaire.md` from the verbatim source `docs/specs/research-page-refresh/evidence/questionnaires-source.md`. Update `research_instruments.md`, `iso-25010-scope-freeze.md` and `evaluation_instruments_brief.md`. Rename Tool B and Tool C, and remove Tool A, across about 25 live docs. Mark `functional-verification-matrix.md` Dropped.
**Out of scope:** The instruments page (13).
**Complexity:** Medium — wide mechanical rename plus two new docs
**Blast radius:** Shared — about 25 docs across capstone, product and specs
**Unblocks:** 06, 13, 16

## Context
The owner supplied both forms on 2026-11-21. Their exact text must be in the repo for the pages to pin to.

## Read first
- `docs/specs/research-page-refresh/evidence/questionnaires-source.md` — the full text of both forms
- `docs/specs/research-page-refresh/04-chapter-pages.md` — US-17 AC-11, AC-13
- `docs/specs/research-page-refresh.md` — D-27, D-28, O-12
- `docs/capstone/evaluation_instruments_brief.md` — §2–5, the heaviest Tool A/B/C user
- `docs/specs/functional-verification-matrix.md` — to mark Dropped

## Behavior this changes
`evaluation_instruments_brief.md` §3 and `RESEARCH_PROTOCOL.md` describe Tool A as a planned instrument; that is removed (D-28). The old CVI/α plan is marked superseded (D-06).

## Acceptance criteria
- [ ] Both docs exist, with no researcher name or email
- [ ] The ISO doc lists 23 items under six headings, matching D-27 exactly, and records O-12
- [ ] The US-28 AC-18 grep finds only allowed hits
- [ ] Frozen ADRs are unchanged; `ADRs.md` has one dated note
- [ ] `research-changelog.md` has one Correction row
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
The owner's ISO consent text says 25 items and five characteristics. Do not copy those numbers; use the questionnaire (O-12).

## Verification
Grep output for AC-18 and `git diff --stat` on `docs/product/adr/` (must be empty).
**Full suite:** not needed (docs only)

## Blocked by
None
