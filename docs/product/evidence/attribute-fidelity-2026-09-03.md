# Numeric attribute fidelity — three proposed fixes, all killed by measurement

**2026-09-03 · `a723126` · total spend USD 0.19 of Fal plus ~24 OpenRouter judge calls.**

The defect: a character description states a NUMBER ("three amber eyes", "six legs") and the
reference image shows a different number. Observed on 2 of 2 stories scored against the expert
instrument (`corpus-smoke-h`). This file is the measurement that decided what to do about it.

Images are not committed, per this directory's convention. **The counts below were made by hand and
are not recoverable from the files** — that is why they are written down here and embedded in
`scripts/judge_count_eval.py`'s `TRUTH` table.

## 1. Can the shipping generator hit a stated count?

`scripts/count_probe.py` — `fal-ai/qwen-image`, 6 fixed seeds per subject, the same
`reference_prompt` / `filtered_description` / negatives `char_bible` uses, no judge call.
12 images, USD 0.19.

| subject | stated | per-seed result (11, 22, 33, 44, 55, 66) | hits |
|---|---|---|---|
| Quill | three amber eyes | 3, 2, 2, 3, 2, 3 | **3 / 6** |
| Mopsi | six legs | 5, 4, 4, 4, 4, 4 | **0 / 6** |

**Achievability is attribute-specific.** "Three eyes" is +1 on a canonical two-eye face and lands
half the time. "Six legs" is +2 on a quadruped body plan, never landed, and reached 5 once.

## 2. Can the reference judge tell the difference?

`scripts/judge_count_eval.py` — the 12 images above as a hand-labelled eval set (9 should flag,
3 should not), `google/gemma-3-27b-it`, 24 calls, no Fal spend. Arm A is `JUDGE_PROMPT` verbatim;
arm B appends one sentence making cardinality explicit and holds everything else.

| arm | caught real mismatches | false alarms on correct images |
|---|---|---|
| A — shipping prompt | 6 / 9 | **2 / 3** |
| B — + explicit count rule | 6 / 9 | **3 / 3** |

**No.** The rule bought nothing on recall and destroyed precision. Worse than the score: on Quill
the judge flagged **5 of 6** images regardless of ground truth, including both that were correct.
The cardinality signal is close to uninformative, not merely weak.

## What this rules out

1. **"Swap `fal_image_model`."** Dead as a blanket fix — the generator hits the target half the
   time on one of the two attributes tested. Changing a pinned freeze key on a premise that is
   false for half the cases is not supportable.
2. **"Let `MAX_DRAWS = 3` find a good draw."** Dead. The redraw loop only helps if the gate can
   recognise a good draw; this one rejects correct references about two thirds of the time.
   Likely mechanism for syn-001's two-eyed Quill: at a 50% hit rate three consecutive misses have
   probability 0.125, so a correct draw was probably made and wrongly failed. The best-of fallback
   does not rescue it: `best_draw` (`char_bible.py:213-240`) ranks lexicographically on
   `-len(contradictions)` FIRST, and that list comes from the same judge that flagged 5 of 6 Quills
   regardless of ground truth, so a correct draw with one spurious contradiction loses to a wrong
   draw with none. `attributes_present` is only its third key and ADR-034 already calls it noise.
   Unverified on the actual draws, which were not retained, but consistent with what shipped.
3. **"A count-specific judge prompt."** Dead, measured above. Two arms is where ADR-055 D5 says
   guessing stops. Do not try a third wording.
4. **"ADR-018's fine-tune covers it."** It does not. ADR-018 fine-tunes the CONSISTENCY judge, whose
   primary endpoint is ΔF1 on `different_character`. **The taxonomy is not the reason.** An earlier
   version of this note claimed the labels had no cardinality category; that was wrong.
   `wrong_body_feature` is exactly that axis — it gates (`consistency_check.py:175`), it has a
   repair clause (`prompt_optimizer.py:384`), and visual-pilot case 08 is literally "2 eyes vs 4
   eyes" (`scripts/generate_visual_pilot.py:385`). The reason is what the task COMPARES: the
   consistency judge's ground truth is the reference image, and Mopsi is four-legged in the
   reference and four-legged on every page, so the pairs are consistent and a perfect fine-tune
   still passes them all. This defect is in the REFERENCE judge
   (`char_bible._judge_reference` → `RefVerdict.contradictions`), which compares an image against
   TEXT — a comparison no pair in ADR-018's dataset expresses.

## Standing conclusion

Numeric attribute fidelity is an **unowned, measured limitation** and belongs in the writeup's
limitations section, not in an assumption that something downstream absorbs it. No code change
before the campaign survived measurement, so the freeze is unaffected.

**Scope.** n = 12 images, 2 attributes, 1 generator, 1 judge. These are mechanism findings, not
corpus rates. syn-001 and syn-002 are measurement-only under the standing overfitting guard, and
the 4 donated stories remain holdout.
