# ADR-056 — Numeric attribute fidelity is a documented limitation, not a pre-campaign fix

**Status:** Accepted (2026-09-03) · **narrows ADR-028's stated remedy** · **clarifies the scope of
ADR-018 (no change to its decisions)** · **extends ADR-055 D5 and D3 to the reference judge** · no
freeze-key, provider, `StoryMemory` field, prompt, or pipeline-shape change

## Context

A character description states a number and the image shows a different one. Measured on 2 of 2
stories scored against the expert instrument in `corpus-smoke-h`:

- syn-001, Quill — *"had three amber eyes"*; the reference and every page show two. The judge
  caught it.
- syn-002, Mopsi — *"It had six legs"*; the reference and every page show four. `"six legs"` appears
  **twice** in `description.body_features`, so the spec reached the generator intact. The judge did
  not catch it, and did worse than miss: it listed `"six legs"` in `attributes_present` and recorded
  `differences_observed: "The image does not contradict any of the stated attributes."`

This is not the identity defect the project has been treating as its central risk. **Character
consistency across pages passes on both stories** — both characters are recognisably their
references on every page, so ADR-007's reference-conditioning mechanism works. The expert-instrument
items at risk are the ones about props and settings appearing as written, and about unexpected
changes across pages — not the recurring-character items.

Three fixes were proposed and one assumption was relied on. All four are dead, and this ADR exists
so they are not proposed again. The measurement is committed at
`docs/product/evidence/attribute-fidelity-2026-09-03.md`.

### The generator is attribute-specific, not uniformly incapable

`fal-ai/qwen-image`, 6 fixed seeds per subject, the prompt `char_bible` actually builds, no judge
call, USD 0.19:

| subject | stated | per-seed | hits |
|---|---|---|---|
| Quill | three amber eyes | 3, 2, 2, 3, 2, 3 | **3 / 6** |
| Mopsi | six legs | 5, 4, 4, 4, 4, 4 | **0 / 6** |

"Three eyes" is +1 on a canonical two-eye face and lands half the time. "Six legs" is +2 on a
quadruped body plan, never landed, and reached 5 once. There is no single verdict "the model can or
cannot count."

### The reference judge cannot tell, and a rule makes it worse

Those 12 images as a hand-labelled eval set — 9 that should flag, 3 that should not —
`google/gemma-3-27b-it`, 24 calls, no image spend:

| arm | caught real mismatches | false alarms on correct images |
|---|---|---|
| A — `JUDGE_PROMPT` verbatim | 6 / 9 | **2 / 3** |
| B — the same plus one explicit cardinality sentence | 6 / 9 | **3 / 3** |

The rule bought nothing on recall and destroyed precision. Worse than the score: on Quill the judge
flagged **5 of 6** images regardless of ground truth, including both that were correct. The
cardinality signal is close to uninformative rather than merely weak.

## Decision

1. **Numeric attribute fidelity is accepted as a documented limitation for this campaign.** No code
   change lands before the freeze on account of it. Every candidate fix was measured and none
   survived; shipping one anyway would be changing the frozen artifact on a premise the evidence
   contradicts.

2. **ADR-028's stated remedy is narrowed.** `char_bible`'s docstring says the fix for the rate is
   swapping `fal_image_model` (ADR-001's named seam). That is **false as a blanket claim** — the
   generator already hits the target half the time on one of the two attributes tested. It survives
   only in the narrow form: *for a count far off the subject's canonical body plan, a different
   generator is the only remaining lever, and it is untested.* `fal_image_model` is a pinned freeze
   key; a swap needs its own ADR and its own measurement, and this ADR does not authorise one.

3. **`MAX_DRAWS` is not a remedy here, and the reason is recorded.** A redraw loop only helps if the
   gate can recognise a good draw. This gate rejects correct references about two thirds of the
   time, so more draws are more coin flips. Likely mechanism for syn-001's two-eyed Quill: at a 50%
   hit rate three consecutive misses have probability 0.125, so a correct draw was probably made and
   wrongly failed. **The best-of fallback does not rescue it.** `best_draw`
   (`char_bible.py:213-240`) ranks lexicographically on **`-len(contradictions)` first**, and that
   list is written by the same judge measured above to flag 5 of 6 Quills regardless of ground
   truth — so a correct three-eyed draw carrying one spurious contradiction loses to a two-eyed draw
   carrying none. `attributes_present` is only the third key, and ADR-034 already documented it as
   noise. The tiebreak inherits the gate's blindness rather than correcting for it. **Unverified on
   the actual syn-001 draws**, which were not retained, and not fixed here.

4. **No third reference-judge prompt wording.** ADR-055 **D5** stops guessing after two measured
   attempts, and ADR-055 **D3** sets what a measurement has to look like; both now govern the
   reference judge as well as `segment`. A future attempt must clear D3's bar: hold every input,
   vary only the prompt, report a rate with the classified outputs printed.

5. **ADR-018's scope is clarified, and its decisions are unchanged.** ADR-018 fine-tunes the
   **consistency** judge: primary endpoint ΔF1 on `different_character`, labels `same_character`
   plus the closed seven-value `FailureReason` taxonomy and `anatomy_intact`
   (`contracts/story_memory.py:33-41`, `finetune/annotation_truth.py:42-45`).

   **The taxonomy is not the gap.** `wrong_body_feature` is precisely a count axis: it gates
   (`consistency_check.py:175`), it has a repair clause (`prompt_optimizer.py:384`), and the visual
   pilot's own case 08 is literally *"2 eyes vs 4 eyes"*
   (`scripts/generate_visual_pilot.py:385`). `anatomy_intact` additionally covers missing or
   duplicated body parts (ADR-028). An earlier draft of this ADR claimed the taxonomy had no
   cardinality category. That was false, and the correction makes the argument stronger rather than
   weaker.

   **The gap is what the task compares.** The consistency judge's ground truth *is* the reference
   image — it asks whether this page's character matches that reference. Mopsi is four-legged in the
   reference and four-legged on every page, so the pairs are genuinely consistent,
   `wrong_body_feature` correctly does not fire, and a perfectly fine-tuned consistency judge still
   returns pass on all of them. The defect sits one step upstream in the **reference** judge
   (`char_bible._judge_reference` → `RefVerdict.contradictions`), which compares an image against
   *text*: a different question, its own prompt version, and a comparison no pair in ADR-018's
   dataset expresses. **A better consistency judge cannot reach this defect. The reference judge has
   no scheduled fix, and the writeup must not imply otherwise.**

6. **This goes in the limitations section, naming the instrument items it touches.** A limitation
   that is measured, bounded and written down is a result. One that is discovered by an expert rater
   is a finding against us.

## Consequences

- **The campaign runs on current code.** That is the point: no change survived measurement, so the
  freeze is unaffected and the pre-campaign window closes clean.
- **Some books will ship a character whose stated count is wrong**, and the judge will sometimes
  record a passing verdict on one. ADR-028 already holds that reference failure is made visible
  rather than prevented; this is that policy meeting a defect it does not detect.
- **`ref_verdict` is now untrustworthy in a second, documented direction.** ADR-034 established that
  `matches_description` disagrees with `contradictions`; this adds that `contradictions` itself can
  be empty on a contradicted image and `attributes_present` can name an attribute that is absent.
  Any Objective 3 claim resting on `ref_verdict` carries both caveats.
- **A fourth "the model just needs a better prompt" attempt is now out of bounds** on this defect
  without new measurement clearing ADR-055 D3's bar.

## Rejected alternatives

**Swap `fal_image_model` before the campaign.** Rejected on measurement (3/6 on Quill) and on
proportionality: a pinned freeze key changed on a premise false for half the tested cases, with no
evidence any candidate model does better, and no budget to find out.

**Extend the ADR-018 fine-tune to cover the reference judge.** Genuinely attractive and the only
identified path to a gate that can count. Rejected *for this campaign* on scope and sequencing: it
the `FailureReason` taxonomy would largely carry over, but the pairs would not. Every pair would be
an image against a text spec rather than against a reference image, so it needs its own pair
construction, its own labels, and its own pre-registered endpoint, and ADR-018's own sequencing
warning already applies. **Named as Future Work, not decided here.**

**Drop numeric attributes from `analyze`'s extraction** so the spec never states a count the
generator cannot meet. Rejected: it makes the metric look better by deleting the requirement, the
story said three eyes, and a picture book that silently drops what the child wrote is the failure
this project exists to avoid.

**Say nothing and let the fine-tune appear to cover it.** Rejected. It is the only option here that
is dishonest.

## Evidence

`docs/product/evidence/attribute-fidelity-2026-09-03.md`, with `scripts/count_probe.py` and
`scripts/judge_count_eval.py`. Images are not committed per that directory's convention, so the
counts were made by hand and are written down in the markdown and in `judge_count_eval.py`'s `TRUTH`
table; they are not recoverable otherwise.

**Scope.** n = 12 images, 2 attributes, 1 generator, 1 judge, 2 stories. Mechanism findings, not
corpus rates. syn-001 and syn-002 are measurement-only under the standing overfitting guard, and the
4 donated stories are holdout — no probe, no tuning, no page-scoring on them before the campaign.

## Verification

There is nothing to implement, so there is nothing to verify. The claim this ADR makes is that four
candidate fixes fail, and each failure is a committed measurement with its classified outputs
printed. **What would reopen it:** a reference judge that scores materially above chance on the
committed 12-image eval set. That is the bar any future attempt has to clear before it earns a code
change.

## Observations recorded but not decided

**`best_draw` inherits the gate's blindness.** Its primary key is a count of `contradictions`,
written by the same judge that cannot count; its third key, `attributes_present`, is documented
noise (ADR-034). Every key it ranks on comes from the judge whose cardinality output the evidence
shows is close to uninformative. Decision 3's mechanism depends on this and is unverified.

**The reference judge's failure is not symmetric.** It caught Quill's eye count on syn-001 and
missed Mopsi's leg count on syn-002. Whether some attribute classes are reliably checkable is
unmeasured.

**A named non-roster character is dropped entirely.** syn-002 `s3` directs *"Marisol hands money to
the librarian"* and no librarian is drawn. Same gap as ADR-055's Lola note — no reference image, no
discriminating axis — except Lola rendered wrong where the librarian vanished. Unowned.

**Props drift from the stated object.** The story says *"a bucket of creek water"*; `s1` draws a
watering can. Related to the same instrument items and not measured.
