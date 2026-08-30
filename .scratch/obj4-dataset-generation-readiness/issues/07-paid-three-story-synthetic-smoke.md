# 07 — Execute the paid three-story synthetic smoke

**What to build:** An operator-authorized run generates exactly three synthetic story bundles through the canonical producer under the pinned megapixel and dollar limits, leaving enough evidence to decide whether full synthetic generation is safe.

**Blocked by:** 06 — Run the synthetic-generation readiness gate.

**Status:** ready-for-agent
**Labels:** `criticality:critical`, `complexity:medium`

- [ ] Before execution, the operator records authorization, current official price basis and date, pinned output size, maximum megapixels, per-call ceiling, and total dollar cap.
- [ ] The canonical corpus and deterministic limit select exactly three synthetic stories; no donated or held-out record is loaded.
- [ ] Each completed bundle passes structural and provenance validation, and actual image count and bounded spend are recorded per story and in aggregate.
- [ ] Any interruption, uncertain billing result, or quarantine uses the supported reconciliation/resume path rather than silently retrying paid calls.
- [ ] The run stops at the first unexplained provider, budget, validation, or recovery anomaly and does not proceed to full corpus generation.
- [ ] A final smoke verdict records whether all three stories completed, whether the spend bound held, and the exact residual conditions for authorizing full synthetic generation.
- [ ] No GPU training, donated-story intake, annotation, dataset freeze, or held-out evaluation occurs in this ticket.

## Smoke verdict (2026-08-27)

**FAIL — 0 of 3 bundles.** `data/judge/corpus/runs/` is empty. syn-002 and syn-003 never started.

**The spend bound held.** USD 1.33 conservative (38 calls x USD 0.035) against the USD 3.12
authorization. No budget control failed; criterion 5 worked as designed, stopping the run at the
first validation anomaly rather than proceeding.

**Root cause — two defects, both now fixed.**

1. The v1 extraction prompt carried the agency rule on one line of a prompt whose other ~28 lines
   were about appearance. The model weighted the bulk and put inert objects and places in
   `characters[]` (`the hill`, `the river`, `the jar of pickles`). `at most 3` read as a quota:
   27 of 30 rosters padded to exactly 3. Fixed in `fde50b0` (prompt v2).
2. `reconcile_declared_roster` demanded roster equality, which requires the corpus author and the
   model to agree exactly on whether a bit player has agency — a question with no objective answer.
   After v2 removed every hallucination, 22 of 30 still failed. Fixed in `4f5fe44`: coverage, not
   equality. Every declared character must reach the reference slice `characters[:2]`, classified
   as declared; an additional minor actor does not quarantine the story.

The check also ran at terminal packaging, so a mismatch cost a story's entire image spend to
discover something one text call reveals. Moved pre-image in `fde50b0`; `de8dfb6` adds
`--check-rosters` as a text-only pre-flight (runbook step 1a) that runs the real node and the real
reconciliation, so the gate cannot drift from the paid run.

**Decision (operator, 2026-08-27): do not salvage syn-001.** Under the coverage rule its abandoned
checkpoint would now reconcile, and 8 final assets survive locally (2 canonical refs + 6 scenes).
It is not packaged, because `_bundle` stamps `extraction_prompt_version` from the live constant
(now 2) while that memory was produced under v1 — recording a prompt version that did not generate
it, and mixing a v1-cast story into a v2 corpus. syn-001 is regenerated from scratch instead.
`build_state.json` is preserved unedited: it is the audit ledger for calls that were really paid for.

**Residual conditions before authorizing full synthetic generation.**

- A fresh three-story smoke completes 3 of 3 bundles passing structural and provenance validation.
- `--check-rosters` passes live across all 30 records, not a replay of recorded extractions.
- syn-001's quarantine is cleared through `--restart-quarantined` (preserving
  `restart_attempted_baseline`), never by hand-editing the state file.
- A new dollar authorization covers the 38 calls already charged plus the fresh run; syn-001 has
  already consumed its one-time `cap_extended_at` and cannot extend again.
- Tickets 03 and 05 remain open at 0/7, so ticket 06's completed status still rests on unmet
  blockers. They do not gate generation, but the inconsistency is unresolved.

## Authorization record — canary run (2026-08-27)

| Field | Value |
|---|---|
| Authorized by | operator, this session |
| Scope | syn-001 only (one-story canary), isolated restart |
| Total dollar cap | USD 2.21 campaign ceiling |
| Already charged | 38 calls = USD 1.33 (abandoned syn-001 executions; counted against the cap) |
| New spend permitted | 25 calls = USD 0.875 |
| Per-call ceiling | USD 0.035 |
| Price basis | https://fal.ai/models/fal-ai/qwen-image + https://fal.ai/models/fal-ai/qwen-image-edit-2511 (verified 2026-08-26) |
| Pinned output size | 1024x768 |
| Maximum megapixels | 0.786432 raw; ceil(MP) = 1 billable |

Price basis is dated 2026-08-26, one day stale. Not re-verified against fal.ai this session. The
gate is fail-closed on this: a rate above USD 0.035 makes `reserve_usd > remaining_usd` and halts
the run before the first call rather than overrunning the authorization.

Canary rather than the full three-story smoke because two prior runs failed; USD 0.875 of new spend
proves the fixed pipeline end-to-end before committing USD 2.63.
