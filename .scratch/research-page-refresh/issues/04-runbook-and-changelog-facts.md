# 04 — Runbook and changelog entries for the new page facts

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** Every new number the dataset and results pages will show is recorded in the runbook first.
**Source criteria:** US-24 AC-01 runbook and changelog rows, AC-11; US-04 AC-02, US-05 AC-07–AC-09, US-09 AC-21, US-10 AC-03, US-11 AC-08, US-27 AC-27
**Scope:** `docs/capstone/research_runbook.md` entries: 422 of 795 later-attempt pairs; the 172/85 adjudications and owner visibility; 23 and 13 changed labels; 9 clothing/style-only labels; species recount; accuracy baseline; checkpoint finding. `research-changelog.md` rows. A rationale section in `annotation-surface.md`.
**Out of scope:** The page edits that cite these entries (06–08).
**Complexity:** Medium — each figure must be recounted from the freeze, not copied from the audit
**Blast radius:** Shared — the runbook is the source for several pages
**Unblocks:** 06, 07, 08

## Context
SH-02: a page states a fact only after a tracked doc does. Draft numbers: `docs/specs/research-page-refresh/evidence/audit-1-dataset.md`, `audit-2-results.md`; recount scripts in `evidence/`.

## Read first
- `docs/capstone/research_runbook.md` — the "Exact values of the partial comparison" section and the split table
- `docs/specs/research-page-refresh/evidence/kinds.py`, `chars.py` — recount scripts
- `data/judge/freezes/obj4-v1/manifest.*.jsonl` — the source of truth
- `data/judge/evaluations/obj4-v1/validation_checkpoint_scores.csv`

## Behavior this changes
The runbook's "too few to call it a pattern" on checkpoints is replaced (US-11).

## Acceptance criteria
- [ ] Each listed fact has a runbook entry with how it was counted
- [ ] Each recount was rerun and matches the audit, or the difference is reported
- [ ] One changelog row per fact, labelled Finding or Correction
- [ ] `annotation-surface.md` has the four owner-stated reasons
- [ ] The shared rules listed under the source stories hold (index §2)

## Guidance
Run the evidence scripts with `python -I`. Never run `score_*` or anything that appends to `test_access.jsonl`.

## Verification
Paste the recount output into the ticket answer.
**Full suite:** not needed (docs only)

## Blocked by
None
