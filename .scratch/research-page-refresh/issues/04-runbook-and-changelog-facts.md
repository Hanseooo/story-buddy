# 04 — Runbook and changelog entries for the new page facts

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
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

## Answer

- `research_runbook.md`: two new sections, "Counts recounted for the research page refresh (2026-11-21)" and "Results figures recounted for the research page refresh (2026-11-21)", each fact with how it was counted. `research-changelog.md`: 7 rows (5 Finding, 2 Correction). `annotation-surface.md`: new section 1a with the four owner-stated reasons (D-24).
- Recount (python -I, read-only, from the main checkout `data/judge/freezes/obj4-v1/`): 899 pairs = 484/86/329; 795 natural + 104 constructed; later attempts 422 (first 373; 544 scene images, 79 references); raters differ on Same/Different 85; adjudication_rate 0.2289308 x 795 = 182.0; both raters Different and final Same 23 (train 19, val 3, test 1), of which 10 audit (9 train, 1 val) and 13 ordinary (10, 2, 1); clothing/style-only Different 9 (wrong_clothing 6, wrong_style 3; train 6, val 1, test 2; both raters Different 5, split 4); species recount train 12/32 characters and 178/306 pairs, val 9/2 and 75/11; always-Same 282/329 = 85.7- Mismatches with the audit: none. One figure could not be recounted: the 172 any-field conflicts (the freeze keeps only same_character). It is taken from the 2026-09-23 preregistration status check (172 conflicted, 78.4 percent agreement) and recorded as such.
