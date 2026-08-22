# Pre-Registration — Objective 4 (Consistency Judge Classification)

> # ⏱ Timestamped **2026-08-14**
> **Frozen at that timestamp. Zero (0) image-pair labels existed when it was written.**
> The `annotations` table (`docs/specs/annotation-surface.md` §2.1) is empty, the donated corpus has not
> been collected, and no fine-tune has been trained. **That ordering is this document's entire evidentiary
> value** — every number below is a commitment made while the outcome was still unknown, not a description
> of one already seen.

**Status:** frozen · **Objective:** 4 (judge classification performance vs human reference labels)
**Owner spec:** `docs/specs/judge-finetune.md` §7 · **Binding decisions:** ADR-008 (revised 2026-07-25),
ADR-018 + amendment (a), ADR-019, ADR-004, ADR-010, ADR-016
**Protocol:** `docs/product/RESEARCH_PROTOCOL.md` §6, §8, §9, §12, §13

This document asserts **nothing about current project phase or build state**. For "what phase are we in /
which probes ran / what is built", read `docs/product/PHASE_05_RESULTS.md` and `AGENTS.md` — this file is
deliberately **not** part of the nine-file status surface (`AGENTS.md` § *The status surface*) and must never
be added to it.

---

## 0. What is being pre-registered, and why now

`judge-finetune.md` §7.5 opens: *"Write and timestamp the analysis plan before any label is collected. It is
the only thing separating a pre-declared ladder from a moved goalpost, and almost no capstone does it."*
**This is that document.** ADR-018 amendment (a) states the same requirement as a consequence, and
RESEARCH_PROTOCOL §13 states it as protocol.

Three commitments carry the rest:

| # | Commitment | Where it is enforced below |
|---|---|---|
| 1 | **The held-out test set is read exactly once.** All iteration happens on validation. | §7 |
| 2 | **The ladder is declared before labels exist.** δ = 3 F1 points is fixed as of this timestamp and is not adjustable afterwards. | §6 |
| 3 | **Every degree of freedom that could otherwise be exercised after seeing results is closed here** — or named as an open item, honestly, rather than papered over. | §9, §11 |

**Point, don't copy — and where this document deliberately copies.** House rule (`AGENTS.md`) is that a doc
links to a number rather than restating it. A pre-registration is the one document type that must restate the
things it *commits to*, because a commitment held only by reference is a commitment that can be edited
elsewhere. So: **thresholds, δ, resample counts, seeds, hyper-parameters and decision rules are restated here
on purpose**; corpus counts, probe results, split-size planning targets, phase state and model IDs are
**linked, never restated**.

**Amendment policy.** Any change after this timestamp is a **dated amendment appended below**, stating what
changed, when, and whether any held-out number had been seen at the time. Superseded prose is **struck
through and left visible**, never deleted (`AGENTS.md` § *Definition of Done*). A silent edit to this file is
indistinguishable from a moved goalpost and must be treated as one.

---

## 1. The hypotheses and endpoints

Ordered exactly as `judge-finetune.md` §7.1 and §7.4 give them. **This order is itself pre-registered** —
reordering endpoints after seeing results is a degree of freedom, and reporting a secondary first is how a
weak primary gets buried.

### 1.1 Objective 4's reported result (ADR-008, revised 2026-07-25)

> **The fine-tuned judge's agreement with human-established reference labels on the character-disjoint
> held-out set: precision, recall, and F1 on the `different_character` class, F1 primary.** Inter-rater
> reliability on those labels is reported alongside it. The held-out set is read once.

This absolute number **is** Objective 4. It does not depend on any comparison, and no rung of §6's ladder
changes what it reports.

### 1.2 Primary endpoint (§7.1) — the "did the fine-tune work" gate

> **ΔF1 on the `different_character` class, held-out test set, fine-tuned Qwen2.5-VL-7B vs. zero-shot
> Qwen2.5-VL-7B.** The gate passes only if the **95% CI on ΔF1 excludes zero.**

Same architecture, same weights, same prompt; the adapter is the only difference. This is a **deployment
build gate**, and — per ADR-008 — it may *also* be reported as Objective 4's optional secondary comparison.

⚠️ **Beating your own base model is necessary, not impressive**, and it is pre-committed here that this
number is **never presented alone**: §1.3 items 1 and 2 go on the same slide (`judge-finetune.md` §7.1).

### 1.3 Secondary endpoints (§7.4) — reported regardless of how the primary falls

| # | Endpoint | Notes fixed in advance |
|---|---|---|
| 1 | **Fine-tuned vs. prompted `gemma-3-27b-it`.** Same metric, same test set. | Input to the product gate (δ = 3 non-inferiority, §6). Doubles as Objective 4's optional secondary comparison. |
| 2 | **Primary metric on the non-human character slice.** | The contribution, and the least-powered slice. Slice definition is frozen in §9. |
| 3 | **Cohen's κ vs. human**, overall and split human / non-human. | |
| 4 | **Latency and $/call.** | Measurement conditions frozen in §9. |
| 5 | **DreamBench++ transfer — descriptive only.** No comparison claim. | Binarization threshold declared in §8, **before the transfer eval runs**. |
| 6 | **Downstream:** serve the fine-tuned judge in the pipeline and ask whether the expert panel's feedback (Objective 3, `research_instruments.md` §A) is at least as favorable as under the prompted judge. | Non-comparative. The dropped pipeline on/off ablation stays dropped. |

Also reported, per §7.4's closing paragraph: **AUROC from the verdict-token logprob**, and **precision and
recall separately** — they are different failures with different costs.

**No endpoint may be added after this timestamp** without a dated amendment stating whether any held-out
number had been seen. Exploratory analyses are permitted and are **labelled exploratory** in the write-up.

---

## 2. Corpus provenance — the binding decision, and the limitation it creates

**Decided this session (2026-08-14). Provisional pending the adviser's sign-off** — `judge-finetune.md` §5.4
names the corpus reconciliation as an adviser decision, and `methodology.md` §4.1 carries the same open item.

| Split | Character source |
|---|---|
| **Train** | **Synthetic corpus**, authored for this purpose (researcher-written, train-split augmentation only) |
| **Validation** | **Synthetic corpus** |
| **Held-out test** | **Donated stories only** — exclusively |
| **Transfer test** | DreamBench++, never trained on (§8) |

**Rationale.** The donated corpus is fixed at 10 primary + 5 backup stories (`RESEARCH_PROTOCOL.md` §8,
ADR-008), yielding roughly 15–20 distinct characters against the ~50-character split `judge-finetune.md` §5.5
assumes. Spending donated characters on the training split would buy statistical power in the one place it is
not the binding constraint and spend it out of the one place it is. So: **test keeps external validity, train
gets statistical power, and the train half unblocks before ethics clearance** — Stage-1 consent gates donated
stories (RESEARCH_PROTOCOL §9), and it does not gate synthetic ones.

This is consistent with ADR-008's corpus rule and RESEARCH_PROTOCOL §8: *"researcher-written stories appear
only as judge-training-split augmentation, never as evaluation stimuli"* — here the rule is applied at full
strength, with **zero** synthetic characters in validation or test.

> ⚠️ **Pre-registered as a stated limitation, not only as a design choice.** A panel will ask whether a judge
> trained on synthetic stories generalizes to children's writing. **The honest pre-registered answer is that
> the held-out set is exactly the test of that** — every reported Objective-4 number is measured on characters
> drawn from real donated child writing, judged by a model that never saw one during training. A domain gap,
> if it exists, shows up *in* the headline number rather than hiding behind it. This is written here, before
> the number exists, so that it reads as a design property rather than as a post-hoc defense.

**Consequences pre-committed now:**

- The **held-out character count is reported as achieved**, not as planned. Objective-4 power is governed by
  that count (`methodology.md` §4.2), and it is reported honestly whatever it is.
- §5.5's split table stays a **planning target**. It is linked, not restated, and it is not a commitment.
- **Backup stories** (5) may be used to enlarge the held-out set **before labelling begins**; they may not be
  moved in or out after any label exists.
- ⚠️ If the adviser overturns this decision, that is a **dated amendment** to this file, and it must state
  whether any label had been collected at the time.

---

## 3. Splits — by character, never by pair

**Rule (ADR-018, `judge-finetune.md` §3.2, §5.5, `methodology.md` §4.3):** every image derived from a given
canonical reference belongs to **exactly one** split. The split unit is `char_id`. It is never the pair.

Pre-committed:

1. **`manifest.py` enforces disjointness and CI tests it** (`judge-finetune.md` §10). A manifest where any
   `char_id` appears in two splits is a hard failure, not a warning.
2. **Constructed negatives (`pair_type == "constructed"`) go into `train` only.** Validation and test contain
   pipeline pairs exclusively (§3.3). CI-tested.
3. **Deliberately induced drift** (weaker reference conditioning, higher temperature) is **training split
   only**. Validation and test keep the deployment distribution.
4. **Oversampling scenes for the test characters is legitimate and happens before labelling.** Stratifying the
   test split human / non-human is legitimate and happens before labelling. **Moving a character between
   splits after any label exists is not, under any circumstance.**
5. Splits are assigned **once**, by `build_dataset.py`, from a seeded assignment recorded in the manifest, and
   the manifest hash (§10) is what proves the assignment did not change.
6. `char_id` and `split` never enter the training text — they are manifest bookkeeping, and a model that could
   read them could read the answer off them (§5.3).

---

## 4. The annotated field set — frozen here, before annotation begins

`judge-finetune.md` §4 rule: **the taxonomy is extended *before* annotation begins and never during.** A set
that changes mid-annotation invalidates every label collected under the old one. **This section is that
moment.** `judge-finetune.md` §5.2 predates three fields the production contract now carries, so the field set
is restated in full here rather than referenced.

`VlmVerdict` (`backend/contracts/story_memory.py`) declares, in source order:
`differences_observed → same_character → attributes_present → style_match → anatomy_intact →
subjects_unique → text_free`. Which of those a **human** annotates is decided by one criterion only: **does it
gate `passed` in production?**

| Field | Gates `passed`? | Human-annotated? | Source of the training target |
|---|---|---|---|
| `differences_observed` | — (reason-then-score, ADR-004) | Indirectly | Rendered **deterministically by fixed template** from the ticked taxonomy + Character Bible attributes (§5.2). No human writes it; no model writes it. |
| `same_character` | **Yes** | **Yes** | Annotator radio (Different / Same) |
| `anatomy_intact` | **Yes** | **Yes** | Annotator checkbox — merged, missing or duplicated body parts (ADR-028) |
| `text_free` | **Yes** | **Yes** | Annotator checkbox — any visible letters, numbers or writing anywhere on the page |
| `subjects_unique` | No (recorded + ranked only) | **No** | Schema default (`True`) |
| `style_match` | No (recorded + ranked only) | **No** | Schema default (`False`) |
| `attributes_present` | No (best-of tiebreak) | **No** | Schema default (empty) |
| `failure_reasons` | Subset gates (`GATING_REASONS`) | **Yes** | Closed 7-item taxonomy checkboxes |

Verified against `backend/pipeline/consistency_check.py`:
`passed = same_character and anatomy_intact and text_free and not (GATING_REASONS & failure_reasons)`.

**The 7-item `failure_reasons` taxonomy is frozen as-is** (`judge-finetune.md` §4; `FailureReason` is frozen
at 7 values in the contract). `text_free` is a boolean, **not** an eighth reason — that was settled when
`lettering-suppression` landed, and it is restated here so nobody re-opens it during annotation.

⚠️ **Open item — the annotation surface does not yet carry these columns.** `annotation-surface.md` §2.1
declares `annotations` as `(pair_id, annotator_id, same_character, failure_reasons, created_at)` — no
`anatomy_intact`, no `text_free`. **That table and the `(research)/annotate/` UI must be extended before the
first label is written**, or this section's field set is aspirational. Extending it *after* labelling starts
is exactly the invalidation §4 forbids. Not fixed by this document — this document is docs-only and the
change is a schema change (`AGENTS.md`, Architectural Decisions).

⚠️ **Recorded discrepancy.** The field order stated in the task that commissioned this document
(`differences_observed, same_character, anatomy_intact, text_free, subjects_unique, style_match`) does **not**
match the contract's actual declaration order (above). The **code wins** (`AGENTS.md` § *Project Context*
precedence). Nothing in this pre-registration depends on the relative order of the non-gating fields; what is
load-bearing is only that `differences_observed` precedes `same_character` (ADR-004 amendment), which holds in
both.

**Label polarity, stated once.** The `annotations` column follows its own name: `true` = same character. The
manuscript's positive class is `1 = Different Character`, so **`label = not same_character`**, converted in
exactly one place — `build_dataset.py`'s export — and nowhere else. Inverting this flips precision and recall
while every number still looks plausible (`annotation-surface.md` §2.1). Pre-registered because a polarity bug
discovered after the fact is indistinguishable from a re-analysis.

**Annotation procedure, fixed in advance:** two researchers annotate independently (RLS-enforced, not
promised); a third adjudicates **only** pairs where the two disagree on `same_character`; Cohen's κ is
computed **after** labelling, never displayed during it (`annotation-surface.md` §4, RESEARCH_PROTOCOL §6).
**κ is reported whatever it is** — a judge that agrees with humans less than humans agree with each other has
found its ceiling, not a bug.

---

## 5. Metrics and statistics

| Quantity | Commitment |
|---|---|
| **Primary metric** | **F1 on the `different_character` class** (the minority class; the class the control loop acts on; the class whose misses ship a broken page to a child). Never accuracy. |
| **Reported alongside, always** | **Precision and recall separately.** They are different failures with different costs and a single F1 hides the trade. |
| **Effect size** | ΔF1 with a **95% bootstrap CI, 10,000 resamples, resampled by `char_id`** |
| **Paired significance** | **McNemar's exact test** on the paired per-item decisions (all judges score the same items) |
| **Also reported** | **AUROC** from the verdict-token logprob; **Cohen's κ** vs human, overall and split human / non-human |
| **Decoding at eval** | **Temperature 0**, all judges, all baselines (CC-7) |

### 5.1 Why the bootstrap clusters by `char_id` and not by pair

**Stated at length because it is the likeliest place a statistics reviewer finds a hole** (ADR-018 amendment
(a), `judge-finetune.md` §7.1).

Up to ~15 scene images come from a single canonical reference. Those pairs are **not independent
observations**: they share one character, one reference image, one drawing style, one set of attributes the
generator finds easy or hard, and — critically — one *characteristic drift mode*. If the generator loses that
character's third eye, it loses it on most of that character's pages at once, and the judge either catches
that failure mode or misses it wholesale. The errors are correlated **within** character and roughly
independent **across** characters.

A pair-level bootstrap treats those 15 correlated observations as 15 independent draws. It therefore
**assumes an effective sample size far larger than the design actually delivers**, and the resulting interval
is **too narrow** — sometimes dramatically so with a held-out character count in the low double digits. A
narrow interval on ΔF1 is exactly what turns "no detectable difference" into "the CI excludes zero", which is
the primary endpoint's entire gate. **A pair-level bootstrap would let the primary endpoint pass on
arithmetic rather than on evidence.**

**The clustered (block) bootstrap resamples whole characters with replacement** — all of a character's pairs
travel together, or none do — so the resampling distribution reflects the unit the design actually varies. It
is also the honest statement of what the study is powered on: **the number of held-out characters, not the
number of pairs** (`methodology.md` §4.2). Growing pairs per character buys precision on each character's
estimate; it does not buy characters.

Pre-committed: **10,000 resamples, 95% percentile interval, cluster unit `char_id`, one fixed RNG seed
recorded in the results.** The same clustering applies to every reported CI — the primary ΔF1, the Gemma
comparison, the non-human slice, and κ.

### 5.2 Slice definitions, frozen before labelling

- **Human / non-human** is a property of the **character**, assigned at manifest-build time from the
  Character Bible's `species` field, before any label or prediction exists. It is never re-assigned after
  seeing results, and a character is never dropped from a slice for being awkward.
- The **non-human slice is the contribution and the least-powered slice** (ADR-018). Its CI will be wide, and
  **a wide CI is reported as a wide CI**, not narrowed by pooling, by dropping characters, or by switching to
  a pair-level bootstrap for that slice alone.

---

## 6. The claim ladder — deployment only

**The ladder decides which judge ships. It does not decide what Objective 4 reports** (ADR-008, revised
2026-07-25). Objective 4's primary result (§1.1) is unaffected by which rung lands.

| Rung | Condition | Requirement met? | Outcome (engineering) | Ship? |
|---|---|---|---|---|
| **A** | Beats base **and** beats prompted Gemma | Yes | Specialized 7B judge outperforms the prompted 27B incumbent on our in-domain held-out set, at lower latency and zero marginal cost — a clear swap | Yes |
| **B** | Beats base; within **δ = 3** F1 of Gemma; **no recall regression** | Yes | Specialization recovers 27B-level quality at 7B, self-hostable, zero marginal cost — non-inferiority satisfied, swap | Yes |
| **C** | Beats base; loses to Gemma by **> δ** | **Yes** | Fine-tuning worked, but specialization at 7B did not close the gap. Keep the incumbent; note it as a limitation, not a finding | No — keep the prompted judge |
| **D** | Does **not** beat base | No | The LoRA did nothing. A **bug report, not a result** | No — debug |

**δ = 3 F1 points**, chosen because it sits inside one annotator's disagreement band on ~60 minority-class
items. `judge-finetune.md` §7.5 and ADR-018 amendment (a) both say *"Adjust it once, before pre-registration.
Never after."*

> ## δ = 3 is fixed as of **2026-08-14**. It is not adjustable after this timestamp.
> Not by rounding, not by "recomputing the disagreement band on the actual annotators", not by a footnote.
> If the achieved held-out minority-class count differs materially from the ~60 the δ was reasoned against,
> **that is reported as a limitation on the non-inferiority conclusion** — it is not grounds to move δ.

**Both product-gate conditions are conjunctive.** Rung B requires non-inferiority **and** no recall
regression. A judge that buys precision with recall ships broken pages: consistency has a best-of fallback
(ADR-010), a missed failure has none.

**Rung D is the only failing outcome, and it is a bug** — that is what separating the research gate from the
engineering gate buys. Rung C is survivable: the product keeps the judge it already shipped Phases 1 and 2
with, and ADR-019's Modal deployment is dropped (ROADMAP de-scope ladder, rung 4).

---

## 7. Test-set access policy

**The held-out test set is read exactly once.** All development, all prompt iteration, all checkpoint
selection, all threshold fitting, and all debugging happen on **train and validation only**. Consult the test
set during development and it is no longer held out and the primary endpoint is void (ADR-018 amendment (a)).

**The rung-D exception (pre-registered 2026-07-13 in `judge-finetune.md` §7.5, restated here as a
commitment).** Rung D is only *discoverable* by reading the held-out set, and "debug" implies re-evaluating —
which would be a second read of a set that must be read once. Without an explicit rule, "read once" and
"rung D → debug" are individually correct and jointly contradictory, and a panel that notices asks whether
you would have re-run until it passed. The pre-declared resolution:

1. Rung D triggers a debugging investigation conducted **exclusively on train and validation**.
2. **Exactly one (1)** second held-out evaluation is permitted, **after** the defect is identified and fixed.
3. **Both readings and the deviation are reported in full** — the first numbers, the second numbers, what the
   defect was, and what changed between them.
4. **This is the only circumstance under which the held-out set is read twice.** There is no third read, and
   no other rung buys one.

A rung-D fix that turns out to be a *modelling* change rather than a *defect* fix does not qualify: the
exception covers bugs (a broken loader, a mis-serialized target, a wrong adapter), not hyper-parameter
search dressed as debugging.

---

## 8. DreamBench++ binarization threshold — declared before the transfer eval runs

`judge-finetune.md` §7.4 item 5 requires this threshold be fixed **in the pre-registration, before the
transfer eval runs**, because DreamBench++'s human scores are *graded* concept-preservation ratings and the
judge emits a *binary* verdict. **A threshold picked after seeing results makes the one transfer number in
the paper post-hoc.**

**The scale was verified, not guessed** (2026-08-14), from the benchmark's own rating instrument —
`dreambench_plus/prompts/user_prompt_subject_full.txt` in
[github.com/yuangpeng/dreambench_plus](https://github.com/yuangpeng/dreambench_plus), the identical
instructions given to the human raters and to the automated judge, cross-checked against
[arXiv:2406.16855](https://arxiv.org/abs/2406.16855):

| Score | Label | Verbatim definition |
|---|---|---|
| 0 | Very Poor | "No resemblance. The generated image's subject has no relation to the reference." |
| 1 | Poor | "Minimal resemblance. The subject falls within the same broad category but differs significantly." |
| 2 | Fair | "Moderate resemblance. The subject shows likeness to the reference with notable variances." |
| **3** | **Good** | **"Strong resemblance. The subject closely matches the reference with only minor discrepancies."** |
| 4 | Excellent | "Near-identical. The subject of the generated image is virtually indistinguishable from the reference." |

Concept preservation is scored on **shape, color, texture, and facial features (if applicable)**. Each
instance is rated by **at least two** of seven trained annotators.

> ### Pre-registered threshold
> **`same_character` ⇔ mean human concept-preservation score ≥ 3.0; `different_character` ⇔ mean < 3.0.**

**Why 3, and why it is the benchmark's own "preserved" convention rather than ours.** The 2 / 3 boundary is
the only place in the scale where the wording changes from *variance* to *match*: score 2 is "notable
variances", score 3 is "closely matches … only minor discrepancies". Our judge's `same_character` means the
same thing — ADR-004's rubric absolves background, composition, pose, crop and expression and asks about
instance identity. Score 1 ("same broad category but differs significantly") is precisely the failure ADR-004
names as the VLM judge's characteristic error (category similarity mistaken for identity), so it must fall on
the `different` side. Cutting at ≥ 2 would score that error as agreement.

**Fixed alongside the threshold, because each is its own degree of freedom:**

- **Aggregation:** the **mean** across the instance's human raters, then thresholded. Not a per-rater vote,
  not the max, not the median.
- **Ties:** the boundary is **inclusive at 3.0** (`≥ 3.0` = same). A mean of exactly 3.0 is `same`.
- **Unit:** the **entire published benchmark — all 150 subjects, both the 120 photorealistic and the 30
  non-photorealistic**. No subsetting. The temptation to report only the 30 non-photorealistic subjects
  *after* seeing which slice reads better is closed here; if the non-photorealistic subset is reported at all
  it is reported **as a pre-declared descriptive split, alongside the whole-benchmark number, never instead
  of it**.
- **Reported as:** **κ and AUROC** (`judge-finetune.md` §7.4 item 5). **Descriptive only — no comparison
  claim.** It is out-of-domain by construction, and it is evaluated, never trained on, never redistributed
  (§5.6).
- **One sensitivity analysis is pre-permitted:** the same κ/AUROC at a **≥ 2.5** cut, reported as a
  robustness line **beside** the primary ≥ 3.0 number. Pre-declaring it is what stops it becoming a second
  bite at the apple; **the ≥ 3.0 number is the reported one regardless of which reads better.**

⚠️ **Residual, and it does not reopen the threshold.** The published human-rating archive's exact shape —
whether it releases per-rater scores or only an aggregate per instance — was **not verified** from the
release itself (the rating data is a Google-Drive archive linked from the repo README, not inspected here).
If it turns out to publish only an aggregate, the aggregation rule above is satisfied by that aggregate and
**nothing changes**. If it publishes per-rater scores, the mean above is computed from them. **The cut point
(≥ 3.0) is closed either way** — only the arithmetic that reaches it depends on the archive's shape, and both
paths lead to the same rule.

---

## 9. Other researcher degrees of freedom, closed here

Hunted from `judge-finetune.md` §6–§7 and the ADRs. Each of these could otherwise be exercised after seeing
results.

### 9.1 Malformed output

**Pre-registered 2026-07-13 (`judge-finetune.md` §7.5), restated as a commitment.** Every judge runs under
constrained decoding where the serving stack supports it (vLLM guided decoding; OpenRouter
`provider.require_parameters`). **Any residual unparseable verdict is scored as a miss on
`different_character`, charged to the judge that produced it.** Applied **identically to the fine-tune and to
all four baselines** — no exemption, no re-prompt, no manual repair, no dropping the item.

Deciding this after seeing which baseline emits broken JSON would be a degree of freedom, and it is a large
one: the incumbent's provider has silently downgraded structured output before (`PHASE_05_RESULTS.md`,
Probe 3 follow-up, 2026-08-11). **Malformed items are counted and reported per judge** — a baseline that
fails to parse 20% of the time is a finding about that baseline, not a reason to shrink the test set.

### 9.2 The four baselines — all of them, no substitutions

Zero-shot `Qwen2.5-VL-7B` (primary comparator) · prompted `gemma-3-27b-it` reason-then-score (product gate) ·
CLIP image–image cosine (control) · **DINOv2 cosine** (control). Non-negotiable (`judge-finetune.md` §7.3).

**Pre-committed, so it cannot be argued at the defense:** CLIP and DINOv2 are **scientific controls, not
product candidates.** They emit a scalar; ADR-010's regeneration controller consumes `failure_reasons` and a
cosine cannot say *restate the scarf*. **If DINOv2 wins on F1, that is a reported finding about metrics and
changes nothing in the pipeline.**

### 9.3 The cosine baselines need a threshold, and the spec is silent — closed here

⚠️ **Genuine gap in `judge-finetune.md`.** CLIP and DINOv2 emit a similarity scalar, F1 needs a binary
decision, and no section says where the cut comes from. Left open, the cut would be fitted *on the test set*,
which would hand both controls an unfair advantage over every VLM judge in the table — and a reviewer who
noticed would be right to discard the comparison.

**Closed:** each cosine baseline's decision threshold is **fitted on the validation split** by maximizing
`different_character` F1 there, then **frozen and applied unchanged to the held-out set**. The fitted values
are reported. The test set is never used to select a threshold, for any baseline, for any reason. AUROC is
also reported for the cosine baselines, since it is threshold-free and is the fairer comparison.

### 9.4 Prompt parity across judges

The zero-shot base and the fine-tune receive **the same prompt** — the adapter must be the only difference
for §1.2's causal statement to hold. Prompted Gemma runs its **shipped** `consistency_check.JUDGE_PROMPT` at
the version recorded in §10; it is not re-tuned for the evaluation, in either direction. **No prompt is
edited after any held-out number is seen.**

### 9.5 Checkpoint selection and seeds

- **Pre-registered 2026-07-13 (`judge-finetune.md` §6.4).** Early stopping stays on eval loss, but the
  **reported checkpoint per seed is selected by `different_character` F1 on the validation split** — token
  loss is dominated by the majority class and by rationale tokens. Selection happens on **validation only**.
- **Three runs, `seed: 0, 1, 2`. Report mean ± std.** A single-seed delta at this dataset size is noise.
  Pre-committed: **all three seeds are reported**, including a bad one. Selecting the best seed against the
  held-out set is forbidden; if a single model must be named for deployment it is chosen by **validation** F1.

### 9.6 Latency and $/call measurement conditions

Fixed in advance so the structural win is not manufactured: **temperature 0, same hardware class for the
served fine-tune (ADR-019's Modal container), same image resolution (`image_max_pixels`, §10), same two-image
call shape, warm-start excluded from the headline latency and cold-start reported separately** (ADR-019's
cold-start budget is an open measurement, not an assumption). $/call for the incumbent is its actual
OpenRouter price at the measurement date, stated with the date.

### 9.7 Exclusions

**No item is excluded from the held-out set after labelling** — not for being ambiguous, not for annotator
disagreement, not for a malformed judge output (§9.1). Adjudication resolves disagreement; it does not delete
items. Any exclusion that becomes genuinely unavoidable (e.g. a corrupt image file) is reported with its
count and its reason.

### 9.8 What the judge is, and is not

- **The judge is a control signal, never an outcome measure** (ADR-004's non-circularity note). Objective 3's
  expert validation is **never scored using the judge**.
- **The fine-tuned model never sits on the child-safety path** (ADR-004 amendment b, ADR-011,
  `judge-finetune.md` §8). Image moderation stays on prompted Gemma with its own rubric. Consistency has a
  best-of fallback; safety has none.
- ADR-016's reasoning stands on why the judge — not identity, not style — is the fine-tune target.

---

## 10. Reproducibility pins (CC-7, `judge-finetune.md` §6.6)

**A blank labelled "to be filled at training time" is honest. A fabricated hash is fraud.** The blanks below
are filled **at the moment the value first exists**, by appending a dated line — never by back-dating this
document's timestamp.

| Pin | Value | Status |
|---|---|---|
| Base model | `Qwen/Qwen2.5-VL-7B-Instruct` | Fixed (ADR-018) |
| Base model **revision hash** | `________________________` | ⬜ **To be filled at training time.** Pin the exact commit; never `main`. |
| LoRA rank / alpha | **16 / 32** | Fixed (`train_qlora.yaml`, §6.3) |
| `lora_target` | `all` | Fixed |
| Quantization | 4-bit, `bnb` (QLoRA) | Fixed |
| Seeds | **0, 1, 2** — all three reported | Fixed (§9.5) |
| `image_max_pixels` | **262144** (512 × 512) | Fixed |
| `cutoff_len` | 2048 | Fixed |
| Epochs / LR / scheduler | 3.0 / 1.0e-4 / cosine, warmup 0.1 | Fixed |
| Batch × grad-accum | 1 × 8 | Fixed |
| **`manifest.jsonl` hash** | `________________________` | ⬜ **To be filled when the dataset is built.** This hash is what proves the splits did not move (§3). |
| **LLaMA-Factory version** | `________________________` | ⬜ **To be filled at training time** (exact release or commit). |
| Evaluation decoding | **temperature 0** | Fixed |
| `consistency_check.JUDGE_PROMPT_VERSION` at eval | `______` | ⬜ **To be filled at evaluation time.** Verdict rates are only comparable within one prompt version — an unrecorded reword once forced a whole prior series to be discarded (`story_memory.py`, `ref_verdict_prompt_version`). |
| Image generator that produced the pairs | `fal_image_model` / `fal_image_edit_model` as configured at generation time | ⬜ **Record the exact model IDs and the date.** ADR-018's distribution-shift warning: a judge trained on one generator's drift is matched to that generator. |
| Adapter artifact location | W&B artifact registry or Storage | ⬜ To be filled |
| Bootstrap RNG seed | `______` | ⬜ **To be filled at analysis time**, and reported. |

---

## 11. Open items this document could not close

Listed rather than papered over. **Each must be closed before the step it gates**, and closing one is a dated
amendment here.

| # | Open item | Gates | Status |
|---|---|---|---|
| 1 | **Corpus provenance is provisional pending adviser sign-off** (§2). `judge-finetune.md` §5.4 and `methodology.md` §4.1 both name this an adviser decision. | Dataset build | ⬜ Open — decision recorded, sign-off outstanding |
| 2 | **`annotations` table and `(research)/annotate/` do not carry `anatomy_intact` / `text_free`** (§4). | **The first label.** Extending after labelling starts invalidates every label collected. | ⬜ Open — schema change, out of scope for this doc |
| 3 | **DreamBench++ human-rating archive shape** — per-rater vs aggregate (§8). Threshold is closed either way; only the arithmetic reaching it depends on this. | Transfer eval | ⬜ Open, non-blocking |
| 4 | **Achieved held-out character count is unknown** and cannot be known before collection. All split sizes in `judge-finetune.md` §5.5 are planning targets. | Power reporting | ⬜ Open by construction — reported as achieved |
| 5 | **Stage-1 consent clause** must state that donated stories may be used to build and evaluate an AI model, plus the data-lock date (RESEARCH_PROTOCOL §9, ADR-018). **There is no retroactive fix.** | Corpus collection | ⬜ Open — ethics track |
| 6 | **The judge trains on images from whichever image model ships.** ADR-018's distribution-shift warning; the substrate history is in `PHASE_05_RESULTS.md`. If the generator changes after the pairs are made, retrain or say so. | Labelling weekend | ⬜ Standing sequencing rule |
| 7 | **Modal cold-start budget** for a study session — measure, don't assume (ADR-019). Affects §1.3 endpoint 4 only. | Latency reporting | ⬜ Open |
| 8 | **`wrong_style` vs `style_match` disagree** on live judge output, and the reason list — not the boolean — drives `correct_prompt` (`PHASE_05_RESULTS.md`, Probe 3 follow-up). Neither is a gating field here, so it does not touch the primary endpoint, but it is a known noise source in the `failure_reasons` targets. | Nothing in this plan | ⬜ Open, recorded |

**Source specs that disagree, recorded rather than reconciled:**

- **§5.2's example manifest is missing three fields the contract now carries** (`anatomy_intact`,
  `text_free`, `subjects_unique`). §4 above is the reconciliation; the spec is not edited by this document.
- **`judge-finetune.md` §5.4–§5.5's numbers assume ~50 donated stories**; ADR-008 and RESEARCH_PROTOCOL §8
  fix the corpus at 15 (10 primary + 5 backup) and **ban the old numbers outright**. §2 above resolves the
  provenance question; the split *sizes* remain planning targets and are not commitments of this document.
- **No baseline threshold rule for the cosine controls exists in any spec** — §9.3 closes it.

---

## 12. Amendments

### 2026-08-22 — Preset allocation and story-input freeze

**State when amended:** zero held-out results had been seen; donated stories had not entered the corpus;
no study labels had been collected; no fine-tune had been trained.

The original registration controlled style within each character cluster (§5.1) but did not state how the
product's three selectable ADR-042 presets enter the corpus. This amendment closes that degree of freedom:

- each story explicitly declares one of `cel`, `gouache` or `cut_paper`; its references and scenes remain in
  that preset, and legacy-only `comic` is excluded;
- the 30 synthetic stories are 24 train and 6 validation, allocated as 8 train and 2 validation stories per
  preset;
- the 15 donated candidates are assigned five per preset before generation; the 10 primary slots are
  4 Gouache, 3 Cel and 3 Cut-paper, and the five backups are 1 Gouache, 2 Cel and 2 Cut-paper. Gouache receives
  the extra primary slot because it is the product default, not because of generated outcomes;
- replacements preserve the vacated style slot when an eligible backup exists. Otherwise the achieved
  imbalance is reported without restyling or outcome-based selection;
- constructed negatives match style; overall held-out performance remains primary, and per-style results
  are exploratory diagnostics only.

Story input is a validated JSON list, not Python source. The checked-in synthetic file and controlled,
gitignored donated file share the strict record contract in `research-corpus-operations.md` §4.1. Declared
fictional character/non-human rosters are reconciled with final `StoryMemory` before pair materialization.
This amendment changes neither the primary endpoint nor the one-time held-out-test rule.
