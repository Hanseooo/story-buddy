# ADR-018 — Fine-tune the consistency judge (Qwen2.5-VL-7B, QLoRA)

**Status:** Accepted (2026-07-10) · **supersedes ADR-016** · **amends ADR-004** · **served by ADR-019**

**Context:** An external requirement directs the project to fine-tune a model, at the "demonstrate the
capability" level: **the pipeline remains the headline contribution (PRD §3)**; the fine-tune is one
component with its own results table. The question is *which* model, and the answer must be defensible
on technical merit rather than elimination.

ADR-016 already eliminated the two obvious targets, and its reasoning stands: **identity** cannot be
fine-tuned per character (a child invents the character at write-time; there is no dataset and no
40-minute budget inside a 1–3 minute flow), and **style** is already solved by ADR-007's constant.

That leaves the judge, and the judge is not a residual choice — it is the *right* one. ADR-004 records,
with citations, that VLM judges are a known-weak instrument for true instance identity: they conflate
category and scene similarity with identity ([NearID](https://arxiv.org/abs/2604.01973)), and prompting
with an explicit rubric plus reason-then-score ordering caps out near **79.6% human agreement**
([DreamBench++](https://arxiv.org/abs/2406.16855)). ADR-001 records that **no published benchmark splits
identity similarity by human vs. non-human subject** — which is exactly the regime this product lives in.

So: the load-bearing component of the control loop is the documented weakest link, prompting has a known
ceiling, and the gap in the literature coincides with the gap in the product.

**Decision:** Fine-tune **`Qwen2.5-VL-7B-Instruct`** (Apache-2.0, native multi-image, QLoRA-able) as the
consistency judge, via QLoRA. Same family as the text model, so the paper describes one open Qwen stack.
The full data-construction recipe, training configuration, baselines, and failure modes live in
**`docs/specs/judge-finetune.md`**. The decisions that bind are these:

- **Train in-domain; evaluate in-domain; transfer-test on public data.** Not the reverse.
  DreamBench++'s domain is *photographic* concepts; ours is stylized illustrations of invented, often
  non-human characters — the exact regime where the judge is weak. Training on photographs of real
  corgis to judge a cartoon dragon is a domain shift aimed straight at the weakness being fixed.
  DreamBench++ is therefore a **held-out transfer evaluation**, which is a stronger claim and sidesteps
  its image-provenance question entirely (evaluation is the benchmark's intended use).
- **Split by character, never by pair.** A character appearing in both train and test inflates κ silently.
- **Hard negatives are free; positives are not.** A negative is character A's reference against a scene
  generated from character B's reference, same species and same style — clean by construction, zero
  labour. But "same reference implies same character" is a *noisy positive*, noisy in the one direction
  that matters, because generation sometimes drifts — which is the entire reason the judge exists.
  Auto-label positives and the model learns *"was a reference image used?"*
  **Positives must be human-confirmed.**
- **Rationales are supervised, not distilled.** ADR-004's reason-then-score field order is load-bearing,
  so `differences_observed` must be a training target. Generate those rationales with Gemma-27B and you
  have distilled the incumbent's errors and mathematically cannot beat it. Instead, annotators pick from
  a **fixed checkbox taxonomy of failure reasons** (wrong colour / wrong species / wrong clothing /
  wrong style / different face). Fast to annotate, human-supervised — and ADR-010's targeted regeneration
  needs exactly that taxonomy anyway. **Annotate once, use twice.**
- **Report F1 on the `different_character` class**, not accuracy. If most scenes pass, a model that
  always says "same" scores well and is useless; the minority class is the one the control loop acts on,
  and a missed failure ships a broken page to a child.
- **Report κ split by human vs. non-human character.** That split is the contribution.
- **Four baselines, non-negotiable:** zero-shot `Qwen2.5-VL-7B` (proves the LoRA did the work, not the
  base model), prompted `gemma-3-27b-it` with reason-then-score (the incumbent, ADR-004 — the thing to
  beat), CLIP image–image cosine (the naive metric ADR-004 rejects), and **DINOv2 cosine** (the strong
  non-VLM baseline; self-supervised features beat CLIP at instance identity — if DINOv2 wins, that is a
  finding, and better learned now).
- **Pre-register the analysis plan** before running anything. A fine-tune that loses to prompted
  Gemma-27B is then a publishable result ("prompting remains competitive at this scale; the bottleneck is
  data, not capacity") rather than a defeat to be spun.
- **Deployment gate:** ship the fine-tuned judge only if it beats prompted Gemma-27B on held-out
  `different_character` F1. Otherwise it makes the product worse and shipped because it was built.
- **Never on the safety path.** ADR-011's image rubric stays on prompted Gemma. See ADR-004 amendment (b).

**Consequences:**
- The product gets *faster and cheaper*: a 7B judge beats a 27B API call on both latency and cost.
- The judge classification evaluation (Objective 4) is a reported contribution (ADR-008, revised 2026-07-25).
- ⚠️ **Sequencing.** Hard negatives and the in-domain eval set need pipeline output, so the fine-tune is a
  new **Phase 2.5** — *after* Phase 1's exit criterion has already depended on the prompted judge. If the
  prompted judge is weak, the fine-tune arrives too late to rescue Phase 1. ADR-010's best-of fallback
  means Phase 1 wobbles rather than collapses. Named here so it is not discovered.
- ⚠️ **Distribution shift.** The judge trains on Qwen-Image-Edit output. If the Phase 0.5 spike escalates
  to FLUX.1 Kontext (ADR-001), the training distribution no longer matches deployment. Retrain, or say so.
- ⚠️ **Ethics.** Training data derives from children's stories. **Stage-1 consent must state that donated
  stories may be used to build and evaluate an AI model** (ADR-008). One sentence, written before
  collection, not after.
- Hardware: **rent, do not buy.** QLoRA on a 7B VLM with two images needs ~16–20 GB; the available 8–16 GB
  card cannot comfortably hold it. A few hours on a rented 4090 is ~$5–15 (ADR-016 did this arithmetic).
- `backend/providers.py` grows a `judge()` function with a multimodal message path. It had none — the
  judge was being probed with text-only calls, which would have passed while the judge was broken.

**Alternatives:**
- **Per-character identity LoRA** — rejected permanently on latency (ADR-016).
- **Style LoRA** — rejected as speculative (ADR-007 delivers style; ADR-016 trigger (b) still governs).
- **Fine-tune the story analyzer on Taglish** — genuinely attractive and locally grounded, but it competes
  for the same budget, needs gold scene segmentations, and the language decision (English, Taglish
  tolerated) makes it a robustness note rather than a research problem. Named as Future Work.
- **Fine-tune a safety classifier** — rejected. Safety wants a proven, independently-evaluated model,
  never a student-trained one.
- **Fine-tuning as the headline contribution** — not what was asked (PRD §3 stands); the pipeline is the
  contribution, and making the fine-tune the headline would dilute that rather than strengthen it.

### Amendment (a) — 2026-07-10 — the evaluation gate is a pre-registered claim ladder

**Context for the amendment.** The external requirement has been clarified: the fine-tune must
**demonstrate measurable improvement**, not merely demonstrate the capability. That is a bar on a *research
result* rather than on a deliverable, and nobody can guarantee which way a comparison falls. The fix is to
notice that **two different questions were being decided by one number**, and to separate them.

- *"Did fine-tuning work?"* is the **research** question. Its comparator is the **un-fine-tuned base model.**
- *"Should this judge replace the one in the product?"* is the **engineering** question. Its comparator is
  the **prompted incumbent.**

Collapsing these into a single "beat Gemma" gate made a near-certain research result hostage to a coin-flip
engineering comparison. **This amendment supersedes the one-line deployment gate above.**

**The primary endpoint — the research gate. One number, declared before a single label is collected.**

> ΔF1 on the `different_character` class, held-out test set, **fine-tuned Qwen2.5-VL-7B vs. zero-shot
> `Qwen2.5-VL-7B`.** Superiority is claimed only if the 95% confidence interval on ΔF1 excludes zero.

This is the standard ablation every fine-tuning paper reports: *did the LoRA, rather than the base model, do
the work?* Same architecture, same weights, same prompt — the only difference is the adapter. It is the
cleanest causal statement available about the fine-tune, and on ~900 in-domain training pairs the expected
gap is large.

- **Significance:** McNemar's exact test on the paired per-item decisions (both judges score the same items).
- **Effect size:** ΔF1 with a 95% bootstrap CI, 10,000 resamples, **resampled by `char_id`, not by pair.**
  Fifteen scenes from one character are not fifteen independent observations; a pair-level bootstrap yields
  an interval that is too narrow. This is the likeliest place for a statistics reviewer to find a hole.

> ⚠️ **Beating your own base model is necessary, not impressive.** A panel's reflex is *"of course in-domain
> fine-tuning beats zero-shot."* It is a valid pre-registered result and it satisfies the requirement, but it
> is not the contribution. **Never present it alone.** The interesting numbers are the comparison against
> prompted Gemma-27B and the non-human slice, and both are reported prominently whatever they say.

**The product gate — the engineering decision. Separate, and non-blocking for the judge classification evaluation (Objective 4).**

Ship the fine-tuned judge only if **both** hold against prompted `gemma-3-27b-it`:

1. **Non-inferiority:** ΔF1 on `different_character` is no worse than δ = 3 points.
2. **No recall regression.** A judge that buys precision with recall ships broken pages to children.
   Consistency has a best-of fallback (ADR-010); a missed failure has none.

Failing the product gate does not fail Objective 4. It means the paper reports that specialization at 7B did not
close the gap to a prompted 27B, the product keeps the prompted judge, and ADR-019's Modal deployment is
dropped — which the ROADMAP's de-scope ladder already anticipates at rung 4.

**Secondary endpoints, ordered and declared in advance.** Reported whatever the primary does:

1. **Fine-tuned vs. prompted `gemma-3-27b-it`**, same metric and test. The number the panel will actually
   care about, and the input to the product gate.
2. The primary metric on the **non-human character slice** — where ADR-001 says nobody has measured, and
   where prompting should be weakest. This is the contribution; it is also the least-powered slice.
3. Cohen's κ vs. human, overall and split by human / non-human.
4. Latency and $/call. A structural win, not a contested one.
5. DreamBench++ transfer. **Descriptive only — no comparison claim is made on it**, because it is
   out-of-domain by construction.

**CLIP and DINOv2 are scientific controls, not product candidates.** They emit a scalar. ADR-010's
regeneration controller consumes `failure_reasons` — it must know to restate the scarf, and a cosine
similarity cannot tell it. **If DINOv2 wins on F1, that is a reported finding about metrics and changes
nothing in the pipeline**, because DINOv2 cannot do the job the judge exists to do. Stating this in advance
is what stops it becoming a defense ambush.

**Powering the test set — decide before labelling, not after.** The primary endpoint is now cheap to power:
base-vs-tuned gaps on in-domain data are large. **The secondary Gemma comparison and the non-human slice are
not**, and they are where the contribution lives. So:

- Test split: **12 characters, stratified so human and non-human are balanced.** Splitting is a design
  choice and may be stratified; moving a character after seeing results may not.
- **Oversample scenes for the test characters** before labelling. Growing the test set is legitimate.
- **Induce drift deliberately** (weaker conditioning, higher temperature) to harvest natural negatives —
  **training split only. Never the test set**, which must keep the deployment distribution (see the class-
  imbalance rule above).
- ~~**Raise the corpus target to 60–70 donated stories if Stage-1 recruitment allows.**~~ **Superseded by
  ADR-008 (revised 2026-07-25):** the 60–70 target belonged to the dropped comparative judge study. The
  corpus is now **15 stories — 10 primary + 5 backup** (`RESEARCH_PROTOCOL.md` §"Corpus", which bans the old
  numbers outright). The reasoning below still holds *within* that cap: it is a *recruitment* decision, not a
  modelling one, so it is made at Stage 1, not at Phase 2.5 when it is unfixable.

**The claim ladder. Declared before results exist; that is the whole point.**

| Rung | Condition | Requirement met? | Claim | Ship? |
|---|---|---|---|---|
| **A** | Beats base **and** beats prompted Gemma | Yes | A specialized 7B judge **outperforms** a prompted 27B incumbent in-domain, at lower latency and zero marginal cost | Yes |
| **B** | Beats base; within δ = 3 F1 of Gemma; no recall regression | Yes | Specialization **recovers 27B-level quality at 7B**, self-hostable, zero marginal cost | Yes |
| **C** | Beats base; loses to Gemma by > δ | **Yes** | Fine-tuning worked, but **specialization at 7B did not close the gap** to a prompted 27B: *"the bottleneck is data, not capacity."* An honest, publishable negative result | No — keep prompted judge; drop ADR-019 |
| **D** | Does not beat base | No | The LoRA did nothing. A **bug report, not a result** | No — debug |

δ = 3 F1 points is a judgment call, chosen because it sits inside one annotator's disagreement band on ~60
minority-class items. **Adjust it once, before pre-registration. Never after.**

**Consequences of this amendment:**
- **Objective 4 can no longer be lost to a coin flip.** Rung D is the only failing outcome, and rung D is a bug.
- **The engineering risk is now isolated in rung C**, where it is survivable: the product keeps the judge it
  already shipped Phases 1 and 2 with, and the de-scope ladder already lists this at rung 4.
- The analysis plan must be **written and timestamped before any label is collected.** Not a formality — it
  is the only thing separating a pre-declared ladder from a moved goalpost.
- **All iteration happens on the validation split.** The held-out test set is looked at once. If it is
  consulted during development, it is no longer held out and the primary endpoint is void.
- ⚠️ **The weakness of rung C is presentational, not scientific.** "We beat our own base model" invites
  *"so what?"*. The defense answer is the non-human slice and the cost/latency table — which is why those are
  reported prominently and unconditionally, not as consolation.
