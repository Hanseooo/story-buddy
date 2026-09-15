# ADR-060 — Rejected attempts are harvested, because the judge is deployed on candidates, not finals

**Status:** Accepted (2026-09-12) · **changes which images enter the corpus bundle and the manifest**
· **requires a preregistration amendment (append-only)** · no freeze-key, provider, `StoryMemory`
field, prompt, matching-rule, or pipeline-shape change · does not touch ADR-057

## Context

`download_images` (`finetune/build_corpus.py:309-336`) downloads exactly two things per story: each
character's `canonical_ref_image`, and each scene's `final_image_ref`. `pairs_from_memory`
(`finetune/build_dataset.py:94-115`) then walks `scene.final_image_ref` only. Every other image the
campaign paid for is left in Storage and never reaches the dataset.

Those other images are not lost. `Scene.attempts` (`contracts/story_memory.py:201`) retains every
attempt with its durable Storage path, its prompt, and the judge's verdict. ADR-037 caps
`max_scene_attempts` at 3 (`app/config.py:86`), so the pool is bounded by construction at two rejects
per scene — this is not an open-ended harvest.

### The judge is deployed on attempts, and evaluated on finals

`consistency_check` judges `scene.attempts[-1]` (`pipeline/consistency_check.py:296`, "Invariant 3:
only the last attempt is judged and mutated"). Every attempt is scored as it is generated. The
finalized image is then whichever attempt ranked best (`:424`, `final_image_ref = updated[best].image_ref`).

So the images the deployed judge actually sees are **candidates**. The images the dataset samples are
**finals** — a filtered subset, selected by the very model under evaluation. Sampling only finals is
itself a departure from the deployment distribution, not a preservation of it. This ADR corrects an
existing sampling bias rather than introducing one.

### What the train split learns is not what the test split measures

The negative class today is built almost entirely by `constructed_records`
(`build_dataset.py:195-242`): character A's canonical reference against a scene generated from
character B's. Those are train-only, deliberately and correctly — `§3.3` item 2, restated in the
function's own docstring: *"val and test must keep the deployment distribution."*

That leaves the two splits learning and measuring different things:

- **Train negatives:** A's reference vs B's scene — two genuinely different characters.
- **Val/test negatives:** A's reference vs a scene that was meant to be A and drifted.

The primary endpoint (§1.2) is ΔF1 on the `different_character` class on the held-out split. The
model would be trained to answer *"are these two different characters"* and scored on *"did this one
character drift."* The mismatch sits on exactly the class the endpoint measures.

### Measured, on the real bundles

`docs/product/evidence/scripts/count_attempt_pool.py`, USD 0, reads committed `memory.json` files
only — no provider call, no database write. Across all 10 existing corpus bundles:

```
finalized scenes             : 65
final images (in bundle now) : 65
harvestable rejects          : 86
rejects per finalized scene  : 1.32
scene-image pool multiplier  : 2.32x

finals that never passed     : 52 / 65
attempts passed=True but carrying failure_reasons: 6 / 151

failure_reasons across harvestable rejects:
  different_face         76  (88% of rejects)
  wrong_body_feature     56  (65% of rejects)
  wrong_style             7  (8% of rejects)
  character_absent        2  (2% of rejects)
  wrong_colour            1  (1% of rejects)
```

Three things in that table decide this ADR.

**The pool is 2.32× the scene images, not a rounding error.** 86 harvestable rejects against 65
finals. The attempt cap bounds it; the rate is measured, not assumed.

**`different_face` is on 88% of rejects and carries almost no information.** It is not a usable
selection filter — it would exclude 12% of the pool while implying a precision it does not have.
This is the same instrument the project already measured as unable to ground attributes: 6 of 151
attempts are `passed=True` while simultaneously carrying failure reasons. Selecting training or
evaluation data by this field means selecting by the base model's own decision boundary.

**52 of 65 finals never passed the judge.** The pipeline ships the best-ranked failing attempt in
80% of scenes. Read carefully: this does **not** establish that 80% of shipped images are truly
drifted, because the flags above are near-constant and untrustworthy. It establishes that the
`passed` boolean cannot be used to predict what the human raters will find, in either direction.
The size of the natural negative class is genuinely unknown until labels exist.

### The preregistration is silent on this

Grepping `PREREGISTRATION_OBJ4.md` for `final_image_ref`, `finalized`, and `attempt` returns exactly
one hit — `:669`, the requirement that a *hard-negative target* have at least one finalized scene.
Nothing in the registration commits the corpus to final images only.

This is the ADR-057 shape again: a restriction that lives in code and reads like a commitment,
but was never registered. Unlike ADR-057, the code here is not over-strict by accident; it simply
downloads what the first version needed. Either way the fix is the same — change it, and record the
change in an append-only amendment rather than letting a reader infer the old behaviour was
preregistered.

## Decision

1. **Every rejected attempt on a finalized scene is harvested.** A reject is an attempt whose
   `image_ref` is not the scene's `final_image_ref`. `download_images` fetches them as WebP on the
   same path as finals; `pairs_from_memory` mints a pair for each, against the canonical reference of
   every character in `scene.characters_present`, exactly as it does for the final.

2. **No `failure_reason` filter, and no per-scene cap.** ADR-037's attempt cap is the bound. Filtering
   by `different_face` is rejected on the measurement above: 88% prevalence, on a field the project
   has already measured as ungrounded. A filter derived from the base judge's verdict selects data by
   the base judge's decision boundary, which on the held-out split would bias the primary endpoint
   toward the incumbent.

3. **Harvested attempts are pipeline pairs and enter all three splits.** They carry
   `pair_type == "pipeline"` and inherit their split from `char_id` under §3.2, like every other
   natural pair. They are not constructed negatives (§3.3 item 2 does not reach them) and they are
   not induced drift (§3.3 item 3 does not reach them either — see Decision 4). Validation and test
   keep the deployment distribution, and under the reasoning above they keep it *better* than the
   finals-only corpus does.

4. **This is not the induced drift of §3.3 item 3, and does not consume that allowance.** Induced
   drift means deliberately degrading generation settings — weaker reference conditioning, higher
   temperature — to manufacture negatives, and is train-only for that reason. Harvested rejects were
   produced at unmodified production settings by the ordinary pipeline. Nothing about them is
   induced. ADR-057 Decision 4 names induced drift as the remedy for thin training negatives; this
   ADR supplies a different and cheaper one, and leaves that allowance unspent.

5. **Unfinalized scenes are not harvested.** `pairs_from_memory` keeps its existing
   `if not scene.final_image_ref: continue` guard. A scene with attempts but no final belongs to a
   run that did not complete, and admitting it would put partial-run artifacts into a frozen research
   artifact. All 10 existing bundles have zero such scenes; the guard is for the campaign.

6. **Constructed negatives are unchanged.** ADR-057 stands in full: coverage best-effort, species and
   style matching not negotiable, train-only, achieved count reported not targeted. This ADR adds a
   second source of negatives; it removes nothing.

7. **The achieved harvest count is reported, not targeted.** Whatever the campaign yields goes into
   the dataset statistics and the writeup. No threshold attaches to it, nothing fails on it, and no
   selection decision may be made after seeing it — the rule the 2026-08-22 amendment set for achieved
   style imbalance and ADR-057 Decision 3 reused.

8. **This requires a preregistration amendment, appended not edited.** §12 is append-only. The
   amendment records that finals-only was code and not registration, the measured pool, and the four
   standing conditions at amendment time. It must land before any non-pilot annotation, because the
   harvested pairs change what is in the annotation queue.

## Consequences

- **The annotation queue roughly doubles, and that is the real cost.** At 1.32 rejects per finalized
  scene the scene-image pool goes to 2.32×, and pairs scale with it. This lands on a single rater
  (2026-08-29 amendment) across two cold rounds plus adjudication. **This is a larger cost than the
  ~180 images estimated in the readiness audit before the pool was measured**; that estimate was read
  off filename suffixes, which undercount because the final is frequently not the last attempt.
  Bounding the harvest is a live option and would be a further ADR, not a code tweak.
- **Some harvested negatives will be easy.** `character_absent` and `wrong_species` rejects are
  trivially "different" and lift F1 for the fine-tuned and incumbent arms alike, which compresses
  ΔF1. Measured prevalence is low — `character_absent` is 2% of rejects, `wrong_colour` 1% — but it is
  a real effect on the primary endpoint and it is recorded here rather than discovered in the result.
- **Bootstrap power in cluster terms is unchanged.** §5.1 clusters by `char_id`; harvesting adds pairs
  within existing clusters and creates no new characters. It tightens within-cluster estimates and
  does not move the cluster count, which is what governs the interval.
- **Storage and egress rise roughly 2.3× on scene images.** P5 of the readiness audit already puts the
  campaign over the Supabase free tier before any harvesting, so this changes the size of a paid plan,
  not whether one is needed.
- **Training negatives stop depending on constructed pairs.** After ADR-057 the constructed count is
  best-effort and projected to be small. Real drift negatives now carry the train split, which is what
  ADR-018 assumed was happening all along.
- **The existing 10 bundles are not backfilled.** They are smoke and abandoned bundles; the campaign
  has not run. Nothing re-downloads and `build_state.json` is not touched.

## Rejected alternatives

**Filter to rejects flagged `different_face`.** The first proposal, and the measurement kills it.
88% prevalence means it barely bounds anything, and the 12% it excludes is chosen by the base model's
own verdict on a field measured as ungrounded. Acceptable as train-side hard-negative mining;
disqualifying on val and test, where it would tilt the primary endpoint toward the incumbent baseline
the fine-tune is being compared against.

**Harvest into train only.** Tempting by analogy with constructed pairs and induced drift, and wrong
for the same reason those two are train-only: they are *manufactured*, and rejects are not. Confining
real pipeline output to train would leave val and test sampling the judge-filtered subset — keeping
the distribution error this ADR exists to correct, in the one place it affects the reported result.

**Ship constructed-only and change nothing.** Costs nothing today and risks the endpoint. Train would
learn cross-character discrimination while the held-out split measures within-character drift. The
project's stated requirement is that the fine-tune show an improvement; this is the option most likely
to produce a null result for a reason that has nothing to do with fine-tuning working.

**Cap at one reject per scene to halve the annotation load.** A defensible position and not taken
here, because the cap is a distribution choice dressed as a budget choice: scenes that needed three
attempts are the hard ones, and down-weighting them to match easy scenes distorts the deployment
distribution in the direction of optimism. If the annotation load proves unmanageable in practice,
capping is the right lever — as its own ADR, with the achieved counts visible, not as an unrecorded
default.

**Use induced drift instead (ADR-057 Decision 4).** Already registered, but train-only by §3.3 item 3,
so it cannot fix the val/test side at all. It also requires generating new images, where harvesting
reads images the campaign has already paid for.

## Evidence

`docs/product/evidence/scripts/count_attempt_pool.py`, committed and re-runnable, USD 0, no provider
calls and no database writes. It reads every `runs/*/memory.json` under `data/judge/corpus-*` and
counts attempts whose `image_ref` is not the scene's `final_image_ref`.

**Scope.** 65 finalized scenes across 10 bundles is real generated output, not a projection — but
those are smoke and abandoned bundles, whose stories are shorter than the campaign's. The 1.32
rejects-per-scene rate is measured; the absolute campaign total is not knowable until the campaign
runs. The direction and the order of magnitude are not in doubt.

## Verification

Test-first, against `backend/tests/test_finetune_corpus.py` and `test_finetune_dataset.py`:

1. **Red:** a `StoryMemory` fixture with a scene holding three attempts, finalized on attempt 1.
   Assert `pairs_from_memory` returns a pair for each of the two rejects as well as the final. Must
   fail against current `build_dataset.py:94-115`, which returns only the final's pair.
2. **Red:** the same fixture through `download_images`. Assert the two reject paths are fetched as
   WebP. Must fail against current `build_corpus.py:309-336`.
3. **The final must not be double-counted.** `final_image_ref` is itself one of the attempts
   (`consistency_check.py:424`), so a naive "harvest all attempts" mints a duplicate `pair_id` for it
   — `mint_pair_id` keys on `(char_id, scene_image)` and would collide. A test asserts the final
   appears exactly once.
4. **Unfinalized scenes stay out.** A scene with attempts and no `final_image_ref` contributes no
   pairs and downloads nothing.
5. **Unchanged and re-run, not rewritten:** split disjointness (`manifest.py`), the constructed-pairs
   train-only rule, `validate_hard_negative_matches` in full, and the ADR-057 suite.
6. **Re-run the evidence script.** It must report the same 86 against the untouched bundles, proving
   the change did not alter what is already on disk.

## Observations recorded but not decided

**`passed=True` does not mean "no failure reasons".** 6 of 151 attempts are `passed=True` while
carrying `failure_reasons`, including `different_face`. Whatever gating rule produces that, it is
pre-existing, it is not read by anything in `finetune/`, and this ADR does not touch it. Recorded
because a reader comparing `passed` against `failure_reasons` in the harvested rows will find the
disagreement and should not read it as harvest corruption.

**80% of scenes exhaust the attempt cap.** 52 of 65 finals never passed. If that rate holds in the
campaign it is a product finding about generation quality, and possibly about the judge's strictness,
well outside this ADR. It is not evidence about the true drift rate, because the flags producing it
are the ungrounded ones.

**`wrong_body_feature` at 65% is the second near-constant flag.** Same caveat as `different_face`, and
the same reason not to select on it.

**The harvest makes the judge's own training data correlated with its own historical verdicts.**
Every harvested image was rejected by the incumbent judge at generation time, so the pool is not a
random sample of candidates — it is the candidates the incumbent disliked. Human labels are the
supervision, so this is a coverage question, not a label-contamination one: candidates the incumbent
wrongly *passed* reach the dataset only when they were finalized. Bounding that gap would require
harvesting passed-but-not-finalized attempts too, which the cap makes a small set. Not pursued here.
