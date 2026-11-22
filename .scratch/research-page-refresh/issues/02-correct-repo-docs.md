# 02 — Correct repo docs to the owner's answers and the code

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** The source docs that the pages will pin to state the current facts.
**Source criteria:** US-24 AC-01 (all rows except the runbook and changelog rows), AC-02, AC-12; D-04, D-07, D-08, D-09, D-15, D-16, D-20
**Scope:** `methodology.md`, `ethics_and_safety.md`, `RESEARCH_PROTOCOL.md`, `PRD_v2.md` (school name); `TECH_STACK.md` (region); `hardware_and_hosting.md` restored from `2cb6d2f^`, then updated; `system_architecture.md`; `group-guide.md` §3–4; Objective 1 recorded as Achieved; an ADR-008 amendment note in `ADRs.md`.
**Out of scope:** The questionnaire docs and Tool A/B/C (03); runbook and changelog facts (04).
**Complexity:** Medium — many docs, each change sourced
**Blast radius:** Shared — the page tests and groupmates read these docs
**Unblocks:** 13, 14, 16

## Context
Page tests pin copy to these docs (SH-02), so they land first (§4.2). Row-by-row table: `docs/specs/research-page-refresh/06-source-docs.md` US-24.

## Read first
- `docs/specs/research-page-refresh/06-source-docs.md` — US-24 table
- `git show 2cb6d2f^:docs/capstone/hardware_and_hosting.md` — the doc to restore
- `docs/specs/research-page-refresh/evidence/audit-3-docs-paper.md` — D-rows
- `backend/pipeline/config.py` — the caps and models the docs must match

## Behavior this changes
The repo currently says Matina Aplaya; the owner corrected it to Vicente Hizon, Sr. ES (D-04). ADR-008 itself is not edited.

## Acceptance criteria
- [ ] Each US-24 row is applied, and each change cites its decision or code line
- [ ] The AC-02 grep (`Matina Aplaya`, `Railway` as a host, `10–15 scenes`, `NSFW ViT`) finds no current-state claims outside history
- [ ] `hardware_and_hosting.md` is restored and updated with the US-18 training hardware and hosting facts
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
Grep the whole repo, excluding `.worktrees/` and `brag-output*/`, before editing. Trap: `2cb6d2f` was a 4-byte accidental overwrite, so restore first and edit second.

## Verification
The AC-02 grep output goes in the ticket answer. Run the existing page tests in case a pinned sentence moved.
**Full suite:** at the batch gate

## Blocked by
None

## Answer

Resolved 2026-11-21. Applied the US-24 rows that are not questionnaire, runbook or changelog rows.

- School (D-04): `methodology.md`, `ethics_and_safety.md`, `RESEARCH_PROTOCOL.md` (old name struck through, as pre-registered docs require), `PRD_v2.md`, plus `ROADMAP.md`, `design_decisions_and_risks.md` and `research_direction_and_goals.md`, which the grep also hit. ADR-008 is not edited. `ADRs.md` has a "Dated notes" entry instead.
- `methodology.md`: 3 to 10 scenes (`config.py:186,204`), up to two redraws (`config.py:101`), 12 donated books generated (`obj4-readiness-audit.md` §7), teacher-review mode, implementation-site options A and B (D-16).
- `system_architecture.md`: one retry count, Mistral primary and Gemma backstop (`config.py:68,73`), the three teacher-review nodes (`graph.py`), Northflank region.
- `ethics_and_safety.md`: new section 5 with ADR-071/072/080/081/082, the D-08 basis and the D-09 disclosure.
- `TECH_STACK.md`: region North America (D-07), the "unconfirmed" Supabase/Northflank bullet replaced, training-hardware bullet updated.
- `hardware_and_hosting.md`: restored from `2cb6d2f^` (241 lines), stale rows corrected, new section 7 with the A6000 training record (`hardware.json` and `run_plan.json`, read-only) and hosting.
- `group-guide.md` sections 3 and 4: teacher hold, magic pencil, notes, PDF; "Last updated" 2026-11-21; Objective 1 Achieved (D-20), with the dropped per-stage script described without the old label (D-28).
- Also fixed the same facts elsewhere: scene counts in `PRD_v2.md`, `ROADMAP.md`, `research_direction_and_goals.md`; Singapore in `MASTER_SPEC.md` and `PRD_v2.md`; NSFW ViT in `ROADMAP.md` and `PRD_v2.md`.

AC-02 grep (`Matina Aplaya|Railway|10[–-]15 scenes|NSFW ViT` over `docs`, `AGENTS.md`, excluding the spec, `docs/product/adr/` and `docs/diagrams`): remaining hits are history only (the struck-through names, the ADR-008 note, ADR-009/031 index rows, "was Railway" and "July plan" markers).

Not changed: `docs/diagrams/drawio/system_architecture.drawio` and `docs/diagrams/excalidraw/system_architecture.excalidraw` still say Railway. Diagrams belong to tickets 09 and 10.

Page tests: `pnpm exec vitest run "app/(research)"` gave 33 files passed, 2 failed (AnnotationClient and AdjudicateClient demo tests, 5000 ms timeouts under load; they render demo samples and read no edited doc). All reference-page and docs-hub data tests passed.
