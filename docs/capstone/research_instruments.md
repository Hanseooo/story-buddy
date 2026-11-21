# Research Instruments and Their Validation

> **Superseded in part, 2026-11-21 (D-05, D-06, D-21, D-27).** Objective 3 is now the expert questionnaire
> (seven open-ended questions, three evaluators; text in [`expert-evaluation-questionnaire.md`](expert-evaluation-questionnaire.md)).
> Objective 5 is now 23 Likert items on six characteristics, at least 30 respondents, descriptive statistics
> only (text in [`iso-25010-questionnaire.md`](iso-25010-questionnaire.md)). The five-criteria interview, the
> Arts/Education student validators, the five-characteristic scale, the CVI review and the Cronbach's α pilot
> below are superseded and stay as history. Objective 4 is unchanged.
>
> **Manuscript-prose section.** Written in the formal register of the manuscript, intended to be pasted into
> the Methodology chapter after *Data Collection* and *Data Set*. It is the prose realization of
> `docs/capstone/methodology.md` §5.2 and §6, and it inherits the separation of instrument families declared
> there. Where this section and `methodology.md` disagree, `methodology.md` is authoritative and this is a
> defect. Items marked ⚠️ require adviser sign-off before administration.
>
> **Objective 3 panel and form:** see the banner above (D-05, D-21). Names are not recorded in docs.

---

## Research Instruments

This study uses **three legs of evaluation instrument**, and they answer different questions. Conflating them
is the most common way a system evaluation is quietly hollowed out — a high result on one leg is not evidence
that another leg's claim holds, because each leg has its own respondents, method, and evidentiary scope. The
instruments are therefore described and reported separately, and the division of labour between them is stated
explicitly at the end of this section.

The first leg is **expert validation** — the acceptability of the generated digital picture books in terms of
presentation quality and classroom suitability, determined by three experts through a
seven-question, open-ended questionnaire, analysed by content analysis or thematic analysis (to be decided,
O-04) (Objective 3). The second leg is **judge
classification** — the character-consistency classification performance of the fine-tuned vision-language
consistency judge against human-established reference labels, reported with standard classification metrics
(Objective 4). The third leg is the **system-evaluation questionnaire** — the perceived quality of the
delivered software artifact against ISO/IEC 25010 (Objective 5).

### A. The expert validation instrument (Objective 3)

The acceptability of the generated digital picture books — in terms of presentation quality and classroom
suitability — is determined through **expert validation**: a **written, open-ended interview form**
administered to three experts: **two BEEd professors and one Arts professor** (D-05). Each signs the informed
consent form first, reviews the original child-written story and its generated book, and fills in one
questionnaire per book, with its Story ID. The form has **seven open-ended questions** (text in
`expert-evaluation-questionnaire.md`, D-21). There is no ordinal scale and no numeric score — the instrument
collects written responses, not ratings.

**Analysis: content analysis or thematic analysis (to be decided, O-04).** The written answers are coded by
one of these two methods, which suit a three-person panel where a numeric scale and its accompanying
statistics (Content Validity Index, Krippendorff's α) are not statistically meaningful.

This instrument carries the acceptability claim of Objective 3. It is a qualitative acceptability measure, not
a causal one — there is no control or comparison arm.

### Objective 4 — Judge classification: the fine-tuned consistency judge

The study's vision-language consistency judge — **Qwen3.5-9B, fine-tuned with QLoRA under the 2026-09-30 postregistration amendment** — performs
binary character-consistency classification on generated scene pairs: **1 = Different Character** (the
positive class) and **0 = Same Character**. (The schema field `same_character: bool` encodes the same
distinction; the int/bool framing is noted once here and not belaboured elsewhere.) Its structured output
includes the classification itself plus a **failure-reason taxonomy** — the same closed set of feature-level
failure modes used to ground human judgments elsewhere in this study: `wrong_colour`, `wrong_species`,
`wrong_body_feature`, `wrong_clothing`, `wrong_style`, `different_face`, `character_absent`.

Two researchers annotate the human-established reference labels independently; disagreements are resolved via
the established criteria procedure (see *Calibration and reliability* below). The evaluation set is split at
the **character-identity level** — train, validation, and held-out test — so that the same character identity
never appears in two subsets, controlling for identity leakage.

**Metrics: precision, recall, and F1-score, with F1 as the primary summary metric**, computed against the
human-established reference labels on the character-disjoint held-out set. Full method, split sizes, and
training details are in `docs/specs/judge-finetune.md`.

**Optional, secondary comparison:** the fine-tuned judge's classification performance may additionally be
compared against a **zero-shot base model** and the **existing prompted Consistency Judge baseline**, evaluated
on the same held-out pairs and human labels. This comparison is optional and secondary to the fine-tuned
judge's absolute classification performance — it is not required to satisfy Objective 4.

The judge is never used to score the output-quality evaluation of Objective 3, since the judge drives
regeneration inside the pipeline and using it to score the outputs it helped produce would be circular
(ADR-004).

### D. The system-evaluation questionnaire — perceived software quality (ISO/IEC 25010, Objective 5) ⚠️

Separately from Objectives 3 and 4, the delivered **software artifact** is evaluated with a structured
questionnaire administered to **designated software-quality evaluators** — a group separate from the expert
validators of Objective 3 — following the **ISO/IEC 25010** software product quality model, with the
six characteristics below. This is the operator-facing *software* leg, kept as a separate
instrument from expert validation (defense-panel note 11): Objective 3 judges the artifacts the system
produces; this questionnaire judges the system itself.

**Pending adviser approval (2026-09-04):** the functional-suitability item below was corrected — it named
`narrate` and `export`, both **cut at that date** (ADR-058) and never built at that date. An instrument change needs sign-off before
administration; it cannot be relabelled after collection.

**2026-10-21 update (ADR-071):** PDF download is restored; narration stays excluded. The revised item below remains a proposal until adviser sign-off and deployed-feature verification. No collected ratings or historical compose-only results may be relabelled.

The form is final as the owner supplied it (D-06, D-27; text in `iso-25010-questionnaire.md`). It has **23
Likert items on six characteristics**: Functional Suitability, Interaction Capability, Reliability,
Performance Efficiency, Security and Compatibility. Items use a **five-point Likert scale where 5 = Strongly
Agree**. It goes to **at least 30 respondents** from IT experts, IT students, teachers and education students,
not split equally. Results are reported as **descriptive statistics only**: the mean and standard deviation
per characteristic. There is no Content Validity Index and no Cronbach's α pilot.

This questionnaire measures **perceived software quality only.** It does not, and is not presented to, answer
whether the generated outputs are acceptable (Objective 3) or how well the consistency judge classifies
(Objective 4).

---

## Validation of the Instruments

An instrument is not trustworthy merely because it exists. The human-scored instruments are calibrated before
their results are reported, as described below. The two questionnaires (Objectives 3 and 5) are the owner's
final forms: there is no CVI review and no Cronbach's α pilot for the ISO/IEC 25010 questionnaire (D-06), and
the expert questionnaire is qualitative.

### Calibration and reliability of the human reference labels ⚠️

The human-established reference labels used to evaluate the fine-tuned judge (Objective 4) are themselves
human judgments, and a rater is not an instrument until calibrated. The two annotators follow the same
protocol:

1. **A written scoring guide** with worked examples and explicit edge cases, fixing the closed taxonomy of
   feature-level failure modes (`wrong_colour`, `wrong_species`, `wrong_body_feature`, `wrong_clothing`,
   `wrong_style`, `different_face`, `character_absent`), is produced before any real data is labeled.
2. **Practice items drawn from outside the held-out set** are labeled first. Real material is never used for
   calibration.
3. **Calibration.** Inter-annotator agreement is computed on the practice set (see `docs/specs/judge-finetune.md`
   for the specific agreement statistic and threshold). Labeling of real data does not begin until the floor is
   met. If the floor is not met, the guide is revised and the annotators re-calibrate.
4. **Adjudication.** Disagreements on real data are resolved by a third researcher, and the adjudication rate is
   reported.
5. **Drift check.** Agreement is recomputed midway through labeling, because raters relax over long sessions.
6. **Blinding.** No annotator sees provenance (opaque filenames, shuffled order) while labeling.

The final inter-annotator agreement on the real held-out labels is reported alongside Objective 4's results — a
measure reported without its reliability figure is treated as incomplete.

---

## What each instrument can and cannot support

To prevent any instrument from being asked to carry a claim it cannot bear, the division of labour is fixed in
advance:

| Question | Instrument | What it can support |
|---|---|---|
| Are the generated books acceptable in presentation quality and classroom suitability? | Expert validation interview (A) | **Qualitative acceptability**, from seven open-ended answers (Objective 3) |
| Does the fine-tuned judge classify character consistency to a usable standard? | Judge classification (Objective 4) | **Classification performance** against human-established reference labels — precision, recall, F1 (F1 primary); optionally compared against zero-shot and prompted baselines |
| Is the delivered software any good? | ISO/IEC 25010 questionnaire (D) | **Perceived software quality** — explicitly *not* output quality or classification performance (Objective 5) |

The system-evaluation questionnaire's average score is never presented as evidence that the generated outputs
are acceptable, or that the judge classifies well; those claims rest on Objective 3's expert validation and
Objective 4's classification metrics respectively. No instrument in this study makes a causal or
comparative-superiority claim about the pipeline itself: there is no control or comparison group (ADR-008). No
learning-gain claim is made by any instrument.
