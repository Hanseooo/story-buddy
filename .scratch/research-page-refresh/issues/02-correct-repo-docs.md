# 02 — Correct repo docs to the owner's answers and the code

**Status:** ready-for-agent
**Type:** task
**Progress:** open
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
