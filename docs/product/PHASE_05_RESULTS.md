# Phase 0.5 — Probe Results

**Status (2026-07-29):** 🟨 Probe 1 **resolved** — Run 3 passed absolute (80%), failed separation
(+25 vs ≥30); escalation declined, Qwen-Image-Edit stays primary per the ADR-001 amendment, and the
failed gate is carried as a stated limitation. · ✅ Probe 3 **PASS**, both arms · ⬜ Probes 2 and 4
not run (2 needs fal credit; 4 waits on the Phase-2 moderation spec) ·
**Owner:** build track · **Companion:** ROADMAP Phase 0.5

This file is **written before the probes run.** Each section states what the probe tests, what
counts as a pass, and what to do on each way it can fail — *then* leaves a blank for the number.

Pre-committing the shape is the same discipline as pre-registering the analysis plan
(RESEARCH_PROTOCOL §13): you cannot retro-fit a narrative onto a number you have already seen.

Fill in `Result` and `Decision` immediately after each run. Do not edit the `Pass condition`
or `Branches` rows after seeing a number — if one turns out wrong, say so in `Notes` and leave
the original visible.

> **Revised 2026-07-13, before any probe ran** (round-2 review, 2026-07-12 — the review file was never
> committed; this note is the only surviving record of it):
> probe 1 scaled from 5 to 10 scenes per character (n = 20 per condition) and its tie rule recorded;
> probe 3 gains a raw field-order condition (Pydantic cannot see order); probe 4 probes the
> two-classifier **union** over an expanded ~26-case set, both directions.

---

## Probe 1 — Non-human character consistency 🟥 *(Run 1 void · Run 2 FAIL both gates · Run 3 FAIL separation only, on `omnigen-v2`)*

**THE KILL CRITERION.** Everything downstream is contingent on this.

Two characters: **Pip**, a fox cub (real animal, canonical silhouette, heavily represented in
illustration training data — the *easy* case) and **Quill**, an invented three-eyed lizard-bird
(the case ADR-001 is actually afraid of). **Ten scenes each** (n = 20 items per condition),
generated twice: conditioned on the canonical reference (**ON**) and from the description alone
(**OFF**). Shuffled behind opaque filenames. Every team member scores blind. Nobody opens `key.csv`.

Scoring rules, recorded before any number exists: per-item verdict is the **rater majority; a tie
scores as not-identity** (conservative). The team scorers are not naive raters — they designed the
mechanism and can often infer condition from pose/composition echo — so the κ and effect size this
probe yields are treated as **optimistic bounds** when sizing the Tier-1 load (R2), not as unbiased
estimates.

> **Revised 2026-07-28, before any probe ran: one rater, not four.** Scorer availability, not
> methodology. The gates are unchanged and still compute — `_majority` degrades correctly to a
> single column. Three things are lost, and they are losses, not simplifications:
> 1. **No inter-rater κ.** Undefined with one rater. Phase 3's instrument therefore gets **no
>    dress rehearsal** here (ADR-008); that rehearsal has to happen somewhere else before Phase 3.
> 2. **The conservative tie rule never fires** — with one column there are no ties, so the
>    single scorer's call *is* the verdict on every item.
> 3. **The designer-bias caveat above gets sharper, not softer.** It was already an optimistic
>    bound with four mutually-checking scorers; with one it is a single unchecked judgement by
>    someone who knows what the probe is trying to prove.
>
> Consequence for how the result may be reported: a PASS here licenses **"Phase 1 opens"** and
> nothing stronger. It is not a measured consistency rate fit for the paper. If any Probe-1 number
> is to appear as a finding rather than as a build gate, it is re-scored with ≥3 raters first.
>
> **Settled 2026-07-29 — single rater is the design, not a shortfall to be corrected.** Solo
> developer, one-month timeline, and the judgement is openly subjective. The earlier "raise this
> back to four raters when scorers are available" is withdrawn everywhere it appears: it was never
> going to happen, and a standing unmet TODO misrepresents the method. Probe 1 is a **build gate**,
> which one rater is adequate for, and that is now the claim it carries.
>
> The reliability gap this leaves is real, and the cheap solo fix is **intra-rater test–retest, not
> more people**: re-score the archived `run3/` items cold after a gap, blind to the first pass, and
> report agreement with yourself. One person, one sitting, and it yields a defensible reliability
> statistic where κ is undefined. Phase 3's actual instrument is the VLM judge (ADR-008); a single
> rater's labels are still usable ground truth to validate it against — what is unavailable is κ,
> not the labels.

```
uv run python -m spikes.phase_05 consistency
# ...all four raters fill spikes/out/scores.csv, blind...
uv run python -m spikes.phase_05 tally
```

**Pass condition — both must hold, on the `comic` preset only:**

| | Threshold |
|---|---|
| Absolute | pipeline-ON identity retained on **≥ 80%** of items |
| Separation | pipeline-ON − pipeline-OFF **≥ 30 points** |

**Branches:**

| Outcome | Meaning | Do this |
|---|---|---|
| Both hold | The reference does the work. ADR-007's mechanism is real. | **Phase 1 opens.** |
| Absolute holds, separation fails | The model draws a good fox with or without the reference. **This is a fail** — the reference is not doing the work and ADR-007 has no measurable effect on this substrate. *(RQ2 was dropped in ADR-008; this probe is a **technical substrate gate**, not a research arm — `methodology.md` §3.4. It still fails: the pipeline's consistency mechanism would be doing nothing.)* | Escalate to **OmniGen2** — rung 1 of ADR-001's fallback ladder, re-ordered 2026-07-28 before any probe ran (FLUX.1 Kontext is now rung 4). Verify fal routes it first. Re-run. |
| Both fail | The substrate cannot hold identity. | **Stop and surface it.** A Phase-0.5 finding, not a Phase-3 catastrophe. |
| Pip passes, Quill fails | **Not a defeat.** It maps the product's boundary and it is the most interesting sentence in the paper. | Record it. Decide scope deliberately. Do not paper over it. |

**Result — Run 1, 2026-07-29. VOID. Recorded, not acted on. See Notes.**

| | ON | OFF | ON − OFF | n |
|---|---|---|---|---|
| Pip | 90% | 90% | **0** | 10 |
| Quill | 0% | 40% | **−40** | 10 |
| **Combined (gates)** | 45% | 65% | **−20** | 20 |

Inter-rater agreement (κ): **N/A — single rater** (2026-07-28 revision). The Phase-3 instrument
dress rehearsal (ADR-008) does **not** happen in this probe and is still owed before Phase 3.

**Decision:** **Run 1 is void for Quill. Do not escalate on it.** The pre-declared both-fail branch
(→ OmniGen2, rung 1) is **not** taken, because the probe did not test what it was built to test —
two defects below, either sufficient on its own. Fix the reference, re-score to the written
instrument, re-run. Escalate only if Run 2 fails clean.

**Notes:**

**Defect 1 — the gating reference is off-spec.** `reference-quill-comic.png` was generated with
**two** amber eyes, not three (an orange spiky crest reads as a third at a glance; it is not an eye).
`reference-quill-cel.png` and `reference-quill-gouache.png` both correctly have three. `comic` is
`PRIMARY` and the only preset that gates.

Consequence: every Quill **ON** item was conditioned on a two-eyed reference and faithfully
reproduced a two-eyed creature, while every Quill **OFF** item received the full text description
including *"three amber eyes"* fresh on each call and had a real chance of drawing three. That is
the whole of `quill on: 0%` vs `quill off: 40%`, and the whole of the negative separation.

ADR-001 records the reference generator (`fal_image_model`) and the editor (`fal_image_edit_model`)
as a deliberate seam. **Step 1 failed before Step 2 was ever exercised.** Reading this as a verdict
on Qwen-Image-Edit's identity retention collapses that seam and is the error the seam exists to
prevent.

**Defect 2 — instrument drift, single rater.** The scorer compared items against the **character
description**, not against `reference-<character>-<style>.png` as the written instruction specifies,
and discovered the reference discrepancy partway through the 1–50 pass — so the criterion was not
even applied consistently within the run. With one rater and no κ (see the 2026-07-28 revision),
there is no second column to detect or absorb this. The single unchecked judgement the revision
warned about is exactly what failed.

Note the two criteria are genuinely different questions, and Defect 2 surfaced that the pre-committed
one is incomplete: *identity-vs-reference* asks whether the pipeline holds a character across scenes
(the gate); *identity-vs-description* asks whether the authored character was produced at all. A
correct reference makes them coincide. A wrong reference makes the book wrong in a way the gate,
as written, scores as a **pass** — Quill's ON items are faithful to their reference and would have
scored 1 under the written instrument. **The gate as pre-committed cannot see Defect 1.** Recorded
here as a finding about the instrument; the gate itself is left unchanged for Run 2 (changing a
threshold after seeing a number is the thing this file exists to prevent), with reference fidelity
checked separately below.

**What survives Run 1 as valid evidence:**

- **Pip: ON 90% / OFF 90%, separation 0.** Clean arm — on-spec reference, and prompt and reference
  agree, so the instrument drift is inert here. On the *easy* case, absolute passes and separation
  fails outright: the reference is doing no measurable work. This is the "absolute holds, separation
  fails" branch arriving on the character least expected to produce it, and it survives Run 2
  regardless of what the Quill fix does.
- **Quill on `cel` 60% and `gouache` 40% identity — both with correct three-eyed references.** The
  editor drops the third eye even when the reference has it. Non-gating, but this is the strongest
  evidence in the run and it is precisely the non-human failure ADR-001 exists to fear. Scored under
  the drifted instrument, so treat as indicative, not measured; re-scored in Run 2.
- **Per-scene failure modes, scorer's observation:** Pip's canonical black oval eyes (no sclera)
  degrade under high-affect scenes — smudged eyes on *surprised*, and occasional invented white
  sclera. Quill's third eye is the single dominant identity failure across all presets.

**Reference fidelity, checked by eye after the run (4 references, not a scored column):**

| Reference | Matches its description? |
|---|---|
| `reference-pip-comic` | Yes — black oval eyes, cream chest, oversized ears. "One bent whisker" is not legible; whiskers render on one side only. |
| `reference-quill-comic` | **No — two eyes.** Voids the gating arm. |
| `reference-quill-cel` | Yes — three eyes. |
| `reference-quill-gouache` | Yes — three eyes. |

**Product consequence, beyond this probe.** Step 1 silently produced an off-spec canonical reference
and nothing caught it. In production that is a whole book of the wrong character. ADR-007's pipeline
has **no reference-acceptance step**; it assumes the reference is correct because it was generated
from the description. Raise against ADR-007 — this is a gap the probe found in the architecture, not
just in the probe.

---

### Result — Run 2, 2026-07-29. Valid. **FAIL — both gates.**

| | ON | OFF | ON − OFF | n |
|---|---|---|---|---|
| Pip | 80% | 80% | **0** | 10 |
| Quill | 70% | 40% | **+30** | 10 |
| **Combined (gates)** | **75%** | 60% | **+15** | 20 |

| Gate | Threshold | Actual | |
|---|---|---|---|
| Absolute | ON ≥ 80% | **75%** (15/20) | **FAIL** — by one item |
| Separation | ON − OFF ≥ 30 | **+15** | **FAIL** |

**Decision:** **FAIL stands.** Both pre-committed gates are missed. Everything below is exploratory
analysis of *why*, recorded because it is decision-relevant — **none of it converts this into a
pass**, and no threshold is moved. The exploratory findings are hypotheses for Run 3, not results.

**The reference fix is validated.** Quill ON went **0% → 70%** on an unchanged prompt, unchanged
model, unchanged scenes — the only change was a reference that matches its description. Run 1's
void was correct and its −20 separation was entirely an artifact of the two-eyed reference.
Separation went −20 → +15.

**Pip contributes exactly zero separation, in both runs** (90/90 in Run 1, 80/80 in Run 2). Quill
contributes +30 — which *by itself* meets the separation threshold. Reference conditioning does
substantial work on the invented non-human character and **no measurable work at all** on the
canonical animal. The mechanism's value is concentrated precisely where ADR-001's risk is.

This is the most interesting result in the probe and **the pre-committed gate cannot see it**,
because it pools the two characters and the easy case dilutes the hard one to half its effect.
Recorded as a limitation of the instrument, not as grounds to re-cut the gate after the fact.

**Scene 5 is 0/6 — every item, both characters, all three presets, both conditions.**

| Scene | Identity |
|---|---|
| 3 running through tall grass in the rain | 6/6 |
| 6 perched on a rock / 7 paper crown / 8 digging at dusk | 4/4 each |
| 9 reflection in a puddle · 10 riding a turtle | 3/4 |
| 1 looking up at the moon · 4 sharing a berry | 3/6 |
| 2 **curled asleep** inside a teapot | 2/6 |
| 5 **peeking out from behind a mushroom, surprised** | **0/6** |

Scene 5 is the **only scene in the set that names an emotion.** Scene 2 (*curled asleep* — closed
eyes) is second-worst. The two worst scenes are the two that change the character's **eye state**,
and the scorer's independent observation before this analysis was run was that facial expression
drives the failures. Converging evidence, from an instrument that was not designed to test it.

If scene 5 is set aside, combined ON is 83% and the absolute gate would pass — **separation still
fails (+17)**. So the absolute gate rides on a single scene, but the *binding* failure is
separation, and no scene exclusion rescues it. Stated as a sensitivity, not a result.

**Scene fidelity is unmeasured, and it failed.** In one scene-9 item the puddle reflection rendered
as a detached mirrored "astral projection" beside the character rather than an image in water. The
character was still recognisable, so it **scored identity = 1**. The instrument has no column that
can see a scene rendered wrong. Distinct from identity, distinct from style, currently invisible to
every gate in this probe.

**`handmade` = 100% on all 50 items, all three presets.** No preset reads as generic AI art;
ADR-022's anti-slop authoring is doing its job. With zero variance the column now carries no
information — it should be retired or re-cut before Run 3. The `_distorted` column discussed before
scoring was **not added**, so the distortion rate is unquantified and rests on the scorer's
recollection.

**Confound, as pre-declared: `comic` 75% > `cel` 60% > `gouache` 40%.** The `comic` reference was
regenerated for Run 2 with three eyes in a legible frontal row; `cel` and `gouache` still use their
Run-1 references (two large eyes plus one smaller offset) and their items were cached and merely
re-scored. **`comic`'s lead is not attributable to preset.** Do not act on this ranking — including
the proposal to drop `cel` — until all three references share an eye layout.

**Notes, Run 2:** the sclera rule (invented white sclera → 0) was pre-committed before scoring and
applied, but the scorer flagged genuine ambivalence: white-sclera eyes sometimes read as *better*
because emotion is legible, while being inconsistent with the reference. Pip's 80% is sensitive to
this rule. Recorded as an open instrument question for the ≥3-rater re-score, **not** re-scored now.

---

**Unresolved: this file and `spikes/phase_05.py` disagree on the branches.** Recorded here rather
than edited, per this file's own rule — the Branches table above is left as originally written.

| Outcome | This file says | `phase_05.py:206-212` says |
|---|---|---|
| Absolute holds, separation fails | Escalate to OmniGen2, re-run | Reports "RQ2 has no story" — **names no escalation** |
| Both fail | **Stop and surface it** | Escalate to OmniGen2, re-run; stop only if *that* fails |

The two are close to inverted. Both were authored before any probe ran, so neither is contaminated
by a number — but **exactly one must be the pre-committed rule**, and Run 1 landed on the row where
they disagree most (both fail). Settle it and make the loser match, **before Run 2 executes**, or
the escalation rule is being chosen after seeing a result. This is why Run 1's void status is
load-bearing: it is the only reason there is still time to settle this honestly.

> **Settled 2026-07-29 — in favour of `phase_05.py`. Both fail → escalate one rung, then stop.**
> The doc's row is amended to match the code; the code is unchanged.
>
> **Reasoning:** ADR-001 ranks its four rungs on *subject-consistency* benchmarks (OmniContext 7.95,
> GEdit 7.560). Those measure **identity retention**, which is the **absolute** gate. The ladder is
> therefore a tool built to fix a failing absolute gate. The doc's mapping pointed it at the
> *separation* failure — a case where identity is already fine and only attribution is broken — and
> called for a full stop on the absolute failure, the one case the ladder exists for. Under the
> doc's rule no rung of a four-rung ladder is reachable through the branch it was built for. The
> code's mapping points the tool at the problem it solves. "Stop and surface it" is retained, one
> rung later, which also bounds cost against the one-month solo timeline.
>
> ⚠️ **This was settled on 2026-07-29, *after* Run 2's numbers were seen. That is contamination and
> it is recorded rather than smoothed over.** The mitigating argument is that the reasoning above
> turns on the *structure* of ADR-001's ladder and reaches the same answer with no number in hand —
> but a reader is entitled to weigh that themselves, so the timing is stated plainly. The lesson is
> the one this file already encodes: the conflict was visible on 2026-07-29 before Run 2 executed
> and should have been settled then.

**Run 2 — pre-committed before re-running:**

1. ✅ **Done 2026-07-29.** Regenerate `reference-quill-comic.png` until it has three legible amber
   eyes, using the **prompt unchanged** — only the roll differs. Reference selection is a Step-1
   input, not an outcome, and the acceptance criterion is *matches its description*, never *will
   score well*; the gate still measures Step 2 against whatever reference is fixed.

   **Yield: 1 valid in 4 draws.** Candidates 1, 3 and 4 came back **two-eyed**; only candidate 2
   rendered three. All four are kept in `spikes/out/reference-candidates/` and the voided Run-1
   reference in `spikes/out/run1-void/`. **A 25% hit rate on the character's single defining
   feature is the finding** — Run 1's defect was not bad luck, it is the modal outcome of this
   generator on this description, and it silently produced the off-spec reference three times in
   four. This is the evidence for the ADR-007 reference-acceptance gap above.

   ⚠️ **Confound to carry into the reading of Run 2.** The accepted candidate places all three eyes
   in a *horizontal row across the front of the face*, larger and more legible than the `cel` and
   `gouache` references, which both use two large eyes plus one smaller offset eye. If Quill's
   `comic` identity now beats `cel` (60%) and `gouache` (40%), eye **layout** is a live alternative
   explanation to preset, and the three presets are no longer comparable on identity. Do not read a
   `comic` win as a preset effect without re-generating the other two references to match.
2. ✅ **Done 2026-07-29.** Delete the 10 `tmp-quill-comic-*-on.png` files and re-run `consistency`.
   The `off` items and both Pip arms do not touch the reference and are cached, so they are reused
   unchanged; only the 10 Quill ON items regenerated (~$0.35). The script re-shuffles and rewrites
   `key.csv`. *(`scores.csv` was locked by another process on the first attempt and needs one more
   `consistency` run — free, everything is now cached — before scoring can start.)*
3. ⬜ **Re-score all 50 items** against `reference-<character>-<style>.png`, as the written
   instruction says — not against the description. All 50, not just Quill: the drift applied to the
   whole pass.
4. ✅ **Done 2026-07-29.** `tally`. Run 2 **failed both gates** — result recorded above.

**Run 3 — escalation to ADR-001 rung 1, pre-committed 2026-07-29 before it runs:**

fal routes OmniGen2 as **`fal-ai/omnigen-v2`** (verified 2026-07-29). ~~so escalation is an env
change — `FAL_IMAGE_EDIT_MODEL=fal-ai/omnigen-v2` — with no `providers.py` change.~~ **Struck the
same day, by step 1 below:** the env var is necessary but not sufficient. The endpoint renames the
reference field, so it also needs a `providers.REFERENCE_FIELD` row. Original left visible — it was
load-bearing and wrong, and the correction is the finding.

**Pre-registered secondary analysis — declared 2026-07-29, before Run 3 generated a single image.**

The pooled gate above is **untouched and still decides.** But it cannot return PASS on this item set
even if rung 1 works: Pip retained identity at 90% then 80% in *both* conditions across two runs, so
it contributes exactly **zero** separation and halves the instrument's sensitivity. A plausibly good
Run 3 — Quill 70%→85%, Pip unchanged — lands at ON 82.5% / OFF 60% = +22.5 and reads FAIL. That is a
property of the instrument, not of the substrate.

So, declared in advance: **Quill alone, ON ≥80% and separation ≥+30**, reported as a secondary and
gating nothing. It answers the narrower question ADR-001 actually asks — does reference conditioning
work for the *invented, non-human* character? — and `tally` now prints it as its own line.

This secondary is **motivated by Run 2's numbers**, which is stated here rather than hidden: that is
precisely why it is declared before the run and why it may not overturn the criterion. If the pooled
gate fails and Quill holds, the recorded outcome is *FAIL, with the pooled failure carried by Pip* —
not a pass. Rewriting the gate itself to Quill-only would need a dated ADR-001 amendment owning that
the pass condition was edited after seeing the numbers it failed. Not done, and not proposed.

1. ✅ **Done 2026-07-29 — and it fired.** The pre-flight was not a formality; the mismatch was real.

   OmniGen2 names the reference field **`input_image_urls`**, not Qwen's `image_urls`, and **fal
   silently ignores unknown arguments**. The first call returned HTTP 200 and a clean image of a
   **human boy in a blue tracksuit** — reference discarded, and with it the art style, which rides
   on the reference (ADR-007). No error was raised at any layer.

   **Had Run 3 been executed as planned, all 20 pipeline-ON items would have been unconditioned
   text-to-image. Identity would have scored ≈0%, rung 1 would have been recorded as a failed
   escalation, and the settled branch rule would then have stopped the project** — on a false
   negative produced entirely by a field name. Cost of catching it: one call, ~$0.03.

   Re-run with `input_image_urls` returns Quill correctly — three amber eyes, crest, striped scarf,
   halftone surface, style carried from the reference. Rung 1's mechanism works. Artifacts kept:
   `preflight-omnigen2.png` (the broken call) and `preflight-omnigen2-fixed.png` (the corrected one).

   **Fixed in code, not in the runbook:** `providers.REFERENCE_FIELD` maps endpoint → field name and
   `edit_image` now **raises** on any unmapped endpoint. A silent degradation became a loud failure.
   Escalating the ladder is consequently **not** the pure env change ADR-001 assumed — corrected there.

   *Second occurrence in two days of the same class of defect — a silent bad input misread as a
   substrate result (cf. Run 1's two-eyed reference). The pattern, not either instance, is the
   finding: this pipeline's inputs fail quietly, and every gate downstream inherits it.*
2. ⬜ **Swap the model and nothing else.** Same prompts, same 10 scenes, same references, same
   rubric — **including scene 5.** Expression-driven failure is the other live explanation for Run 2
   (scene 5 scored 0/6); fixing the prompt in the same run confounds the two permanently. Held
   fixed, a second 0/6 on scene 5 under a different substrate is a far stronger finding than either
   run alone can support. The swap is one line in `backend/.env` —
   `FAL_IMAGE_EDIT_MODEL=fal-ai/omnigen-v2` — plus the `REFERENCE_FIELD` row step 1 added; the
   `config.py` default stays on Qwen until a run earns the change.
3. ✅ **Done 2026-07-29.** Run 2 archived to `run2/` (`key.csv`, `scores.csv`), as Run 1 was; all
   `tmp-*.png` and `item-*.png` deleted. The four `reference-*.png` are **deliberately kept** — step 2
   holds references fixed, and `_reference()` re-uploads from disk rather than regenerating. Only the
   *editor* changes; the reference generator stays `fal-ai/qwen-image` (ADR-001's two-model seam).
4. ⬜ Re-score all 50 under the Run-2 rubric, unchanged. `consistency` now emits the `_distorted`
   column itself, and `tally` prints distortion pooled by scene — the direct test of Run 2's
   eye-state hypothesis. It does not gate: `_majority` never reads it, and unlike `identity` an
   unscored cell is tolerated rather than aborting the tally.
5. ⬜ `tally`. **If Run 3 fails both gates: stop and surface it.** Per the settled branch rule, that
   is a Phase-0.5 finding and the escalation ends there — do not climb to rung 2 without an explicit
   ADR-001 amendment.

**Unscored impression, written down 2026-07-29 before a single item was scored.** Recorded now
precisely so it can be checked against the numbers rather than remembered to agree with them.

From a skim of the raw `tmp-*.png`: **OmniGen2's art style is better than Qwen's; its scene
composition is worse.** The specific failure is *fusion* — the character merges into scene objects.
Pip hiding behind a mushroom has a body that **is** the mushroom; Quill riding a turtle loses its
legs and reads as a centaur with a turtle lower half.

This is the **third** defect in a row that the instrument cannot see. Identity may read 1 (it is
recognisably the character), `distorted` reads 0 (the face is clean), and the illustration is still
unusable in a children's book. Run 2's "astral projection" reflection was the same blind spot.
**A `fused` column is therefore added before scoring** — body merges into scenery or loses parts —
kept separate from `distorted` rather than merged into it, because scene 5 now carries **two**
competing explanations: *"surprised"* (expression, the Run-2 hypothesis) and *"peeking out from
behind"* (occlusion, which is exactly what invites fusion). One combined column could never
separate them; two columns scored per scene can. The gate is untouched — both are diagnostics.

**Run 3 completed 2026-07-29 at 45 items, not 50, for $0.** The fal balance hit −$0.36 with the 5
`gouache` ON items ungenerated. Two consequences, both recorded rather than smoothed over:

- **`gouache` dropped from the secondary arm for budget, not for evidence.** One-word restore in
  `SECONDARY`. The gating arm — both characters, both conditions, `comic`, 40 items — is complete
  and untouched, so **the kill criterion is fully answerable at 45.**
- **A bug was stranding the paid work.** `_reference()` uploaded eagerly, before the disk cache was
  consulted, and uploading is billed — so a run whose every image was already on disk still could
  not complete once the balance was gone. 45 paid-for images were locked behind a 403 raised for the
  5 that were missing. References are now resolved lazily; a fully cached run makes **no API call**.
  Worth noting as a cost-model finding, not just a defect: the spike's re-run-is-free property, which
  every "just re-run it, everything is cached" decision in this document leaned on, was never true.

⚠️ **Run 3 is not blind, and less blind than Run 2.** The `tmp-*.png` filenames encode character,
preset, scene **and condition**, and they were skimmed before scoring. Any Probe-1 number from Run 3
carries the same licence as Run 2's — a build gate, never a finding in the paper without a fresh,
blind, ≥3-rater re-score.

⚠️ **The trade-off this exposes is not measurable by the current criterion.** If the decision becomes
Qwen-vs-OmniGen2, identity alone cannot make it: style fidelity and scene fidelity are both
uninstrumented, and the skim says the two models trade places on exactly those axes. That is a
Phase-0.5 finding about the *instrument* (ADR-008), and it lands whichever way Run 3's gates fall.

⚠️ **Probe 2 (seed determinism) is invalidated by escalation.** Seed behaviour is per-`(provider,
model)`. ~~If `fal_image_edit_model` changes, Probe 2 must be re-run on `omnigen-v2` before CC-7 can
be claimed — a Probe-2 result on `qwen-image-edit-2511` says nothing about the model that ships.~~
**Moot as written, 2026-07-29:** the escalation was declined and the shipping model is
`qwen-image-edit-2511` again, so Probe 2 measures the right model with no re-run. The rule survives
the reversal — measure seeds on whatever ships. If the OmniGen2 escalation ever fires on a code path
whose output must be reproducible, that path needs its own Probe-2 result.

**Loss carried into Run 2, unfixable:** the re-score is **not blind**. The scorer has now seen the
items, knows the reference defect, and knows what Run 1 produced. Run 2's numbers are a build gate
and nothing more — weaker even than the "Phase 1 opens, and nothing stronger" licence the
2026-07-28 revision already imposed. No Probe-1 number from either run may appear as a finding in
the paper without a fresh, blind, ≥3-rater re-score.

### Result — Run 3, 2026-07-29. `fal-ai/omnigen-v2`, 45 items. **FAIL — separation only.**

| | ON | OFF | ON − OFF | n |
|---|---|---|---|---|
| Pip | 80% | 80% | **0** | 10 |
| Quill | 80% | 30% | **+50** | 10 |
| **Combined (gates)** | **80%** | 55% | **+25** | 20 |

| Gate | Threshold | Actual | |
|---|---|---|---|
| Absolute | ON ≥ 80% | **80%** (16/20) | **PASS** |
| Separation | ON − OFF ≥ 30 | **+25** | **FAIL** |
| *Pre-registered secondary (Quill alone)* | *ON ≥80% and ≥+30* | *80% / +50* | *holds* |

**Decision: FAIL stands.** One gate is met, the other is not, and the criterion requires both.
Nothing below moves a threshold.

**The escalation worked, on the axis it was chosen for.** Rung 1 vs rung 0, identical prompts,
scenes and references: Quill ON **70% → 80%**, Quill OFF **40% → 30%**, Quill separation
**+30 → +50**. Pooled absolute **75% → 80%**, clearing the bar Run 2 missed by one item. ADR-001's
ladder did what the ladder is for.

**Pip contributes exactly zero separation for the third consecutive run** (90/90, 80/80, 80/80).
This is no longer an observation, it is a measured property of the item: a fox cub is drawn
correctly from a text prompt alone, so its OFF baseline sits at ceiling and it is *structurally
incapable* of showing separation. Half the gate's items cannot move. **The pooled separation
failure is an artifact of item selection, and the pre-registered secondary — declared before the
run precisely to catch this — cleared both bars at 80% / +50.**

That does not convert FAIL into PASS. It does mean the correct reading is *"conditioning works;
the instrument that measures it is half dead weight"* — a finding about ADR-008's instrument, and
the concrete requirement it produces: **the Phase-3 evaluation set must not contain items whose
no-reference baseline is at ceiling.** Canonical animals measure nothing here.

#### The diagnostics overturned the Run 2 hypothesis

The two new columns were split apart to separate expression from occlusion on scene 5. They did.

| Scene | face mangled | body fused | |
|---|---|---|---|
| 2 — curled asleep **inside a teapot** | 40% | **80%** | containment |
| 5 — peeking out **from behind a mushroom**, surprised | 20% | **60%** | occlusion |
| 9 — reflection in a puddle | 0% | 25% | |
| 10 — riding **on the back of** a turtle | 0% | 25% | |
| 7 — wearing a paper crown at a picnic | 0% | **0%** | no spatial relation |
| all others | 0% | 20–25% | |

**Facial distortion is near-zero everywhere except the two scenes that also fuse.** Fusion is 3–4×
larger and tracks a clean structural signal: every scene placing the character *inside*, *behind*,
or *on top of* another object fuses; the one scene with no spatial relation to another object
(scene 7) is the only 0%. **Run 2's expression hypothesis is not supported.** Scene 5 was never
mainly about the word "surprised" — it was about "peeking out from behind", and Run 2 could not see
the difference because it had one column where it needed two.

⚠️ **A ~20–25% fusion floor across *every* scene is a product finding in its own right**, and it is
uninstrumented by the gate: identity can read 1 on an image whose body has merged into the
scenery. This is the defect class that made the reader prefer Qwen's output.

⚠️ **The Qwen-vs-OmniGen2 comparison on fusion cannot be made.** `fused` did not exist when Run 2
was scored, and Run 2's images were deleted during Run 3 setup — the archive convention inherited
from Run 1 keeps `key.csv` and `scores.csv` only. So the qualitative impression that *Qwen composes
scenes better* stands unquantified and cannot be checked without re-generating Run 2 at cost.
**Fix the convention: archive the images too.** They are the expensive part.

⚠️ **A third uninstrumented defect class, found while scoring.** Item 43 (`quill`, `comic`, scene 7,
OFF) has a **duplicated tail** — one as if seated, a second as if lying down. Correctly scored 0 for
both diagnostics, since `distorted` is facial and `fused` is merging-or-losing parts; a *duplicated*
part is neither. Left as scored rather than retrofitted. If a Phase-3 instrument keeps these
columns, `fused` should widen to *anatomy wrong: merged, missing, **or duplicated***.

### Secondary arm — style presets (ADR-022, **does not gate**)

> **Revised 2026-07-21, before any probe ran.** The preset set is re-authored to `cel` / `comic` /
> `gouache` (was `gouache` / `ink` / `watercolour`); `watercolour` is dropped — soft bleeding edges
> dissolve an invented silhouette, the fragile case. All three are now strong-line + flat-fill (the
> consistent family), because the shipped book is expert-scored on character consistency (ADR-008
> Leg 1). **`comic` is `PRIMARY`** — the representative-middle substrate: line-forward enough to hold
> identity, but textured enough (ben-day halftone) that the no-reference OFF baseline can't reproduce
> the character by luck, so the separation gate stays honest. `cel` (the flagship default kids see
> first) and `gouache` are validated for identity in the non-gating secondary arm.

Quill through all three presets, ON only. Second rater column: *"does this read as an intentionally
hand-drawn illustration, or as generic AI art?"*

**Prediction, recorded before the run.** From ADR-022's tension — *texture defeats the AI look, but line
and silhouette are what hold identity.* `cel` has the strongest, cleanest line and the flattest fill, so it
should score highest on identity; its anti-AI-slop signal is the deliberate flat-cartoon look, not paper
grain. `comic` adds ben-day halftone, so it should read as the most deliberately *drawn*. `gouache` has the
softest fill and visible paper grain, so it should score warmest, and is now **the preset most at risk of
losing Quill**. A result that contradicts this is a finding about the substrate, not a scoring error —
record it rather than explaining it away.

| Preset | identity (ON) | reads-as-drawn | Verdict |
|---|---|---|---|
| Preset | identity (ON) Run 1 → Run 2 | reads-as-drawn Run 1 → Run 2 | Verdict |
|---|---|---|---|
| `cel` | 60% → **60%** | 80% → **100%** | Reference unchanged from Run 1; items cached, re-scored only. |
| `comic` | *void* → **75%** | 95% → **100%** | Run 1 identity void (off-spec reference). Run 2 valid but **eye-layout confounded** — see below. |
| `gouache` | 40% → **40%** | 100% → **100%** | Reference unchanged; items cached, re-scored only. Holds Quill worst. |

Run 2, 2026-07-29. Run 1 was scored under the drifted instrument (Probe 1 Notes, Defect 2); Run 2
re-scored all 50 items against the reference PNGs as written. `cel` and `gouache` identity are
unchanged across the two scorings — the instrument fix moved neither, which is mild evidence the
drift mattered less on these presets than on the voided `comic` arm.

⚠️ **The ranking is confounded and must not be acted on.** Only `comic`'s reference was regenerated
between runs, and the replacement has a more legible three-eye layout than `cel`'s and `gouache`'s.
`comic`'s 15-point lead over `cel` is as well explained by eye layout as by preset. Re-generate all
three references to a common layout before comparing presets on identity.

**Against the prediction.** The prediction was `cel` highest on identity, `comic` most deliberately
drawn, `gouache` warmest and most at risk of losing Quill. All three held: cel 60% > comic > gouache
40% on identity, gouache 100% and most at risk. ADR-022's tension — *texture defeats the AI look,
line holds identity* — reproduced cleanly as a monotonic trade across the three presets. The
`comic` identity cell cannot corroborate it (void), but it does not contradict it either.

The `reads-as-drawn` column is the one unambiguously good result in the run: 80/95/100%. No preset
reads as generic AI art. ADR-022's anti-slop authoring works. What is in doubt is identity, on the
non-human case, which is ADR-001's problem and not ADR-022's.

Neither number gates Phase 1. But **a preset that cannot hold an invented chimera, or that reads
as generic AI art, is re-authored or dropped before a child sees it** — that is the binding
acceptance condition on ADR-022.

**Decision:** **Deferred to after Run 2.** No preset is dropped on Run 1 numbers — the `comic`
identity cell is void and the other two were scored under the drifted instrument.

Two things are open and both need deciding deliberately, not by drift:

1. **`cel` may be dropped for redundancy** (scorer's judgement, 2026-07-29: *"cel is not too
   different from comic, and comic is just better"*). Note the cost if it is: `cel` scored **highest
   identity of the three (60%)**, and ADR-022 names it *"the flagship default kids see first."*
   Dropping it trades measured identity retention and the default preset for visual distinctness
   between presets. That is a defensible trade, but it is an **ADR-022 amendment**, not a
   preference — and dropping the default also changes what `PRIMARY` means, since `comic` would
   then be both the gating preset and the flagship. Do not action it inside this file.
2. **No preset has yet cleared the binding acceptance condition on Quill.** 60/45/40% are all far
   from holding an invented chimera. If Run 2 does not move them, the condition bites on *all three*
   presets at once — which is an ADR-001 substrate problem (the editor drops the third eye), not an
   ADR-022 authoring problem, and re-authoring presets will not fix it.

---

## Probe 2 — Seed determinism ⬜

Same seed twice, on **both** `edit_image` and `text_to_image`. The ablation seed-matches
pipeline-ON against pipeline-OFF, so both endpoints must reproduce or the comparison is unfair.
Diff the bytes. Replicate has an open, unresolved bug (#334) where seeds are ignored under its
fast path — **verify empirically, do not trust the docs.**

```
uv run python -m spikes.phase_05 seed
```

**Pass condition:** byte-identical output on both endpoints.

**Does not gate Phase 1.**

**Branches:**

| Outcome | Do this |
|---|---|
| Both reproduce | Record against CC-7. Proceed. |
| Either fails | Record against **CC-7**, then choose: drop the reproducibility claim from the methodology (RQ2 itself is gone — ADR-008), or change provider. Do not silently keep the claim. |

**Result:** `edit_image` ______ · `text_to_image` ______

**Decision:** _____________________________________________

---

## Probe 3 — Structured output, in the shape each model is actually called with ✅ *(PASS 2026-07-29)*

The text model gets text. **The judge gets two images** — because that is the only way the judge
is ever invoked, and OpenRouter's structured-output support is per `(model, provider)` *and* per
modality. A text-only probe of the judge passes while the judge is broken. (This exact bug was
caught and fixed; see `tasks/lessons.md`.)

Also confirms `provider.require_parameters: true` is honored.

```
uv run python -m spikes.phase_05 structured
```

**Pass condition:** strict `json_schema` → Pydantic round-trip succeeds for the text model **and**
for the judge **called with two images**, **and** the raw response emits `differences_observed`
before `same_character` — Pydantic validation is order-insensitive, so the reason-then-score
property (ADR-004) is asserted on the raw text. As of 2026-07-13 `providers._chat` enforces this
order on every structured call; a provider that emits out of schema order now fails loudly instead
of silently voiding the mitigation.

**Does not gate Phase 1** — but Phase 1's `consistency_check` node cannot be written without it.

**Branches:**

| Outcome | Do this |
|---|---|
| Both pass | Proceed. |
| Judge fails on two images | The judge model or provider does not support structured multimodal output. Try another provider for the same model before changing models. Record it. |

**Result — 2026-07-29. PASS, both arms.**

| Arm | Model | Outcome |
|---|---|---|
| Text | `qwen/qwen3-32b` | **PASS** — `_Extraction(character_name='Pip', mood='sleepy')` |
| Judge, two images | `google/gemma-3-27b-it` | **PASS** — `_Verdict(differences_observed=<~1500 chars>, same_character=True, style_match=False)` |

`require_parameters` **honored** — implied, not separately observed: `providers._chat` sends it on
every OpenRouter call and `_assert_field_order` raises on out-of-order emission, so a PASS is also a
pass on ADR-004 reason-then-score. A silent downgrade to loose JSON would have surfaced as
`returned no parsable structured output`.

🔴 **Follow-up 2026-08-11 — production falsified the text arm. The result above is left exactly as
recorded; what is wrong is the inference that was drawn from it.** `qwen/qwen3-32b` failed the same
property in prod job `af068baf`: OpenRouter routed it to **DeepInfra**, which spent **1093 of 1497**
completion tokens on a reasoning block and returned JSON violating the strict schema (nested objects
where `str` was declared) — grammar-constrained decoding cannot be applied across a thinking block.
`text_model` moved to `mistralai/mistral-small-3.2-24b-instruct` the same day. Three things this
probe should be read as saying, and one it should not:

- ~~The text model supports strict structured output on OpenRouter.~~ **Too strong.** The probe
  measured *this model on whichever provider the router picked on 2026-07-29*. OpenRouter re-routes
  silently, and this ADR-002 property is per `(model, provider)` — as ADR-002's own Consequences
  already said, one paragraph the probe design did not act on.
- The `_assert_field_order` inference above **holds and is vindicated**: it is what caught the
  companion failure on the image guard the same day (Alibaba Cloud emitted `is_safe` before
  `safety_reasoning`, hard-failing `char_ref_mod`). Both are recorded in the ADR-002 amendment.
- `provider.require_parameters: true` was sent on the failing call. It selects providers that
  **accept** `response_format`, not providers that **honour** it — so this probe's "honored"
  line is true about *acceptance* and cannot be stretched to *fidelity*.
- **Method note for the remaining probes:** a probe result is only valid for the `(model, provider)`
  pair that served it, and a single call cannot establish a durable property of a model ID. The
  standing check is now `backend/tests/test_smoke_providers.py` — run before any deploy that changes
  a model ID, a base URL, or a provider — not a one-off probe.

**Decision:** proceed. Phase 1's `consistency_check` node can be written against this call shape.

**Procedure change made before the run.** The probe uploaded both judge images via
`providers.upload_reference` — a **fal** call, and billed. Nothing in Probe 3 touches fal: the judge
is OpenRouter and passes `image_url.url` through verbatim, so the bytes now go as base64 data URIs.
With the fal balance at zero this was not cosmetic — the upload 403s, and the judge arm would have
reported FAIL for a billing reason, the one failure mode a structured-output probe must not confuse
with its own result.

⚠️ **`style_match=False`, and it is not noise.** The inputs were `reference-pip-comic.png` (made by
`fal-ai/qwen-image`) and `item-01.png` (made by `fal-ai/omnigen-v2` in Run 3), and the judge's
unprompted reasoning names line weight, shading and texture as the differences. That is the *same*
observation as the human skim — OmniGen2 renders in its own style rather than inheriting the
reference's — arrived at independently, by the instrument, on its first real call. Two consequences:

1. ~~**Evidence for ADR-007's seam, and against the escalation.** Style riding on the reference is the
   assumption; the judge says it did not ride. This is a third, independent line of support for the
   2026-07-29 decision to keep Qwen primary.~~ **Withdrawn 2026-08-11 — see the follow-up below.**
   The instrument was not measuring what this line read it as measuring, so it cannot count as an
   independent line of support. The human skim of that pair still stands on its own; ADR-007's seam
   is unaffected, it simply has one fewer witness than recorded here.
2. **`style_match` is uninstrumented as a gate and should stay that way for now.** One observation,
   on one cross-model pair chosen for convenience, is not a style-fidelity measurement. Re-run this
   probe on a Qwen-generated scene before reading anything into the field — expected PASS/`True`,
   and a `False` there would be the interesting result. Logged as an ADR-008 instrument question,
   **not** as a Probe-3 failure: the probe tested whether the judge can be *called*, and it can.

### Probe 3 follow-up — the Qwen-generated re-run, 2026-08-11 (issue #24)

**Run as pre-registered in item 2 above. The interesting result landed: `False`, and the cause was
the instrument.**

Prod job `b9506307` (style preset `comic`, 7 scenes) returned `style_match=False` on **7 of 7**
scenes. Every image in it — references and pages — is Qwen: `fal-ai/qwen-image` for the refs,
`fal-ai/qwen-image-edit-2511` for the pages. So this is exactly the pair item 2 asked for, and it
came back the way item 2 called interesting.

Two hypotheses were pre-stated in issue #24 and both were tested against the job's own stored
images (`storybook-images/b9506307-…/`), 3 judge runs per cell, `google/gemma-3-27b-it` on Parasail:

| | positive control<br>comic ref + comic page (`ref-c0-1` / `s6-1`) | negative control<br>**cel** ref from job `e94cc400` + the same comic page |
|---|---|---|
| Unscoped prompt (as shipped) | `True` **1 / 6** | `True` 0 / 3 |
| Scoped prompt (now shipped) | `True` **3 / 3** | `True` 0 / 3 |

- **"The style is not landing" is falsified.** Direct inspection of the refs and pages shows the
  comic fragment landing on every one — halftone dots, heavy ink outline, flat spot colour, panel
  border, on both sides of the comparison. The scoped prompt then reads `True` on those same bytes.
- **"The judge is miscalibrated" is confirmed, and the mechanism is the question, not the model.**
  `style_match` was **emitted** on the wire every run — never defaulted in (`required` in the strict
  schema, and the raw JSON keys were checked). Asked unscoped, the judge answered about
  hair-strand detail, freckle rendering and background: the reference is one character on a plain
  neutral background and the page is a full illustration, so "do these match" is False by
  construction and the field was constant. `JUDGE_PROMPT` now names background, composition, pose,
  crop and expression as ignorable.
- **The negative control is what keeps the fix honest.** A prompt that just said "yes" would have
  scored 3/3 on the positive too. Reading `False` 0/3 on a genuinely different style family is the
  evidence that the scoped field still discriminates.

**Method note, same class as the one recorded above:** these numbers are valid for
`(gemma-3-27b-it, Parasail)` on one job's images. Six runs on one pair is enough to overturn a
constant, not enough to publish a rate. Objective 4's corpus is where a rate comes from.

**Still open, and NOT fixed here:** `wrong_style` appears in `failure_reasons` on runs where the
same call returns `style_match=True`, so the reason list and the boolean disagree — and it is the
reason list, not the boolean, that drives `correct_prompt`'s clause. Judges also emitted the same
enum value up to five times in one list (`consistency_check` dedupes, so it is currently harmless).

---

## Probe 4 — Filipino / Taglish moderation ⬜

**Release gate for Phase 2, not Phase 1.** You may build Phase 1 with this still red.

The respondents are Filipino children, the open image model ships **no built-in safety filter**,
and the proprietary backstop is gone (ADR-011 revision b). Nobody has published Llama Guard's
Filipino performance. Run the gate over harmful **and** benign Filipino/Taglish cases and check
**both directions.**

ADR-011's gate is **two independent classifiers — either one flagging fails the content** — so the
probe scores the **union**: harmful must be caught by at least one model, benign by neither. The
~26-case set spans threats, self-harm, bullying, dangerous instructions, abuse disclosure, and
hate (must flag) vs. mild peril, folklore horror, in-story death, and **fictional Filipino names**
(must not flag — the R8 false-positive direction).

⚠️ **Verified 2026-07-13 against the live OpenRouter catalog: neither meta-llama/llama-guard-3-8b nor Granite
Guardian is routable there** (only `meta-llama/llama-guard-4-12b` and `openai/gpt-oss-safeguard-20b`
are). This is the pre-declared "routing error is also a finding" branch arriving early: ADR-011's
pair must run on the worker, or the backstop needs an ADR amendment. `moderation_backstop_model`
stays unset until that decision is made.

```
uv run python -m spikes.phase_05 moderation
```

**Pass condition:** no MISS in either direction.

**Branches:**

| Outcome | Meaning | Do this |
|---|---|---|
| No misses | Gate is sound. | Phase 2 may ship. |
| Miss on a harmful case | **A child-safety hole.** | Blocks Phase 2. Add a backstop model or a rule layer. Re-run. |
| Miss on a benign case | Dead-ends a child's dragon fight. Mild peril is the *expected* case. | Blocks Phase 2. Retune thresholds; do not ship a gate that punishes normal children's writing. |
| Routing error | The gate cannot run where it was placed. | **This is also a finding** — it means the gate runs on the worker, not the API process. Record it. |

**Result:** harmful recall ______ · benign false-positive rate ______

**Decision:** _____________________________________________

---

## Exit

Phase 0.5 is done when every section above has a `Result` and a `Decision`, and **one** of:

- a green light for Qwen-Image-Edit, **or**
- a recorded **ADR amendment** naming the fallback that passed.

Then, and only then, update `tasks/todo.md` and open Phase 1.

> **Phase 0.5 closed 2026-07-29.** Probe 1 resolved — Qwen stays primary under the ADR-001 amendment; missed separation gate carried as stated limitation. Probe 3 PASS. Probes 2 and 4 not run; neither gates Phase 1. Phase 1 opened the same day. `story-memory-contract` is **built** (commits b4fb044–8777217 on `feat/story-memory-contract`): `StoryMemory` Pydantic contract exists in `backend/contracts/story_memory.py`, seven nodes are on partial-return, `input_gate` is the entry point, and `job_state.py` is deleted. Numbers are in `PHASE_05_RESULTS.md`.
