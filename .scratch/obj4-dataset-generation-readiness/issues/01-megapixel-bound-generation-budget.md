# 01 — Enforce a megapixel-bound generation budget

**What to build:** Paid corpus generation has a defensible upper spend bound before any image request is sent. Both text-to-image and image-edit requests pin an approved maximum output size, and the corpus runner reserves spend from that size, the provider's megapixel rounding rule, and an operator-recorded current price rather than assuming an unconstrained flat call price.

**Blocked by:** None — can start immediately.

**Status:** completed
**Labels:** `criticality:critical`, `complexity:high`

- [x] Both paid image routes send an explicit output-size constraint whose maximum megapixels are known before dispatch.
- [x] Spend reservation derives a conservative per-call ceiling from maximum megapixels and the current operator-supplied provider rate, including provider rounding.
- [x] A request that would exceed the remaining authorization is rejected before the provider call; exact-boundary completion is retained rather than quarantined.
- [x] Operator output records the pinned size, maximum megapixels, price basis, and authorization used for the run.
- [x] Deterministic tests cover both image routes, fractional-megapixel rounding, exact-budget completion, and over-budget rejection without making provider calls.
- [x] The zero-cost fixture still completes with zero image calls and zero spend.
- [x] The corpus-generation spec and canonical operator instructions describe the same budget calculation and paid-smoke parameters.


## Verification (2026-08-27)

Criteria confirmed against committed code, not self-reported:

| Criterion | Evidence |
|---|---|
| Both routes pin output size | `providers.py:344` (text-to-image), `providers.py:373` (image-edit), both using `GENERATED_IMAGE_SIZE` at `providers.py:330` |
| Conservative ceiling from max MP + rate, with rounding | `build_corpus.SpendPolicy.maximum_megapixels` / `.billable_megapixels` (`ROUND_CEILING`) / `.conservative_call_usd` |
| Rejected before dispatch; exact boundary retained | `test_next_call_past_story_limit_is_blocked_before_submission`, `test_exact_story_draw_limit_still_writes_a_completed_bundle` |
| Operator output records size, MP, basis, authorization | `_budget_basis`; fixture run emitted `image_size`, `maximum_megapixels`, `billable_megapixels`, `price_per_megapixel`, `price_basis`, `authorized_usd` |
| Deterministic tests, both routes, no provider calls | `test_text_to_image_pins_corpus_generation_size`, `test_edit_image_pins_corpus_generation_size` (both mock `providers._fal`) |
| Zero-cost fixture, zero calls, zero spend | `--fixture --limit 1` returned `images_spent: 0`, `usd_high: "0.000"`, `telemetry` all zero |
| Spec and runbook agree on the calculation | `research-corpus-operations.md` lines 296-305 vs `research_runbook.md` preamble; both state `1024*768/1e6 = 0.786432` MP and `ceil(MP) * rate` |

The boxes were previously unticked while the implementation was complete; this reconciles the
record. No code changed for this ticket.
