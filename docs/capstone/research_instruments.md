# Research Instruments and Their Validation

> **Manuscript-prose section.** Written in the formal register of the manuscript, intended to be pasted into
> the Methodology chapter after *Data Collection* and *Data Set*. It is the prose realization of
> `docs/capstone/methodology.md` §5.2 and §6, and it inherits the separation of instrument families declared
> there. Where this section and `methodology.md` disagree, `methodology.md` is authoritative and this is a
> defect. Items marked ⚠️ require adviser sign-off before administration.
>
> **This section is also where the two things `methodology.md` §6.2 defers are finalized:** the three named
> expert validators, and the five content-analysis criteria their interview form covers.

---

## Research Instruments

This study uses **three legs of evaluation instrument**, and they answer different questions. Conflating them
is the most common way a system evaluation is quietly hollowed out — a high result on one leg is not evidence
that another leg's claim holds, because each leg has its own respondents, method, and evidentiary scope. The
instruments are therefore described and reported separately, and the division of labour between them is stated
explicitly at the end of this section.

The first leg is **expert validation** — the acceptability of the generated digital picture books in terms of
presentation quality and classroom suitability, determined by purposively selected expert validators through a
written, open-ended interview form, analysed by content analysis (Objective 3). The second leg is **judge
classification** — the character-consistency classification performance of the fine-tuned vision-language
consistency judge against human-established reference labels, reported with standard classification metrics
(Objective 4). The third leg is the **system-evaluation questionnaire** — the perceived quality of the
delivered software artifact against ISO/IEC 25010 (Objective 5).

### A. The expert validation instrument (Objective 3)

The acceptability of the generated digital picture books — in terms of presentation quality and classroom
suitability — is determined through **expert validation**: a **written, open-ended interview form**
administered to a small, purposively selected panel of validators from the Arts and Education colleges. Each
brings a distinct lens, mapped explicitly onto the criteria they are best placed to judge: the
**Dean/Professor of the Arts College** and **one Arts student/intern** judge the visual and artistic
presentation of the delivered books, while **one Education student/intern** judges educational suitability.
Books are presented with provenance stripped: opaque filenames and shuffled order.

The interview form asks each validator to respond, in their own words, against **five pre-set criteria**:
**narrative coherence, story faithfulness, visual presentation, visual style consistency, and suitability for
classroom use.** There is no ordinal scale and no numeric score — the instrument collects written responses,
not ratings.

**Analysis: content analysis.** Each written response is coded against the five pre-set categories, and within
each category coded as **positive feedback, negative feedback, or a suggestion for improvement**. Codes are
tallied per criterion, producing a qualitative-but-systematic account of what validators judged to be working,
not working, and improvable, criterion by criterion. This is a coding procedure suited to a three-person
validator panel, where a numeric scale and its accompanying statistics (Content Validity Index,
Krippendorff's α) are not statistically meaningful.

This instrument carries the acceptability claim of Objective 3. It is a qualitative acceptability measure, not
a causal one — there is no control or comparison arm.

### Objective 4 — Judge classification: the fine-tuned consistency judge

The pipeline's vision-language consistency judge — **Qwen2.5-VL-7B-Instruct, fine-tuned with QLoRA** — performs
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
validators of Objective 3 — following the **ISO/IEC 25010** software product quality model, restricted to the
five applicable characteristics below. This is the operator-facing *software* leg, kept as a separate
instrument from expert validation (defense-panel note 11): Objective 3 judges the artifacts the system
produces; this questionnaire judges the system itself.

| Characteristic | What the items ask about |
|---|---|
| Functional suitability | Does the system do what it claims — analyze, segment, illustrate, narrate, export? |
| Performance efficiency | Is generation time acceptable within a classroom period? |
| Usability | Can a Grade 5–6 student and a teacher operate it without instruction? |
| Reliability | Does it recover from a stalled or failed generation without losing work? |
| Security | Are classroom data isolation and asset-access controls effective? |

Items use a **five-point Likert scale (1 = Poor … 5 = Excellent)**. Results are reported as the **weighted
mean and standard deviation** per characteristic, interpreted against the following bands:

| Range | Interpretation |
|---|---|
| 4.20–5.00 | Excellent |
| 3.40–4.19 | Very Good |
| 2.60–3.39 | Good |
| 1.80–2.59 | Fair |
| 1.00–1.79 | Poor |

This questionnaire measures **perceived software quality only.** It does not, and is not presented to, answer
whether the generated outputs are acceptable (Objective 3) or how well the consistency judge classifies
(Objective 4).

---

## Validation of the Instruments

An instrument is not trustworthy merely because it exists. Two properties are established before any
instrument's results are reported: that it measures the right thing (**validity**) and that it measures
consistently (**reliability**). The procedure differs between the questionnaire and the human-scored
instruments, and both are described below.

### Content and face validity of the questionnaire ⚠️

Before administration, the ISO/IEC 25010 system-evaluation questionnaire is reviewed by a panel of **content-
validity reviewers** — practitioners with relevant software-engineering or educational-technology background —
who judge whether each item is clear, relevant to the quality characteristic it claims to measure, and free of
ambiguity. Item-level and scale-level agreement is quantified with a **Content Validity Index (CVI)**, and
items falling below the accepted threshold are revised or removed. The questionnaire is not administered to
real evaluators until this review is complete. This step establishes that the questionnaire measures the
ISO/IEC 25010 characteristics it claims to, rather than assuming it.

### Reliability pilot of the questionnaire

The validated questionnaire is then piloted with a small group of evaluators who are not part of the reported
sample. The **internal consistency** of each subscale is computed as **Cronbach's α**, with a conventional
floor of **α ≥ 0.70**. A subscale that falls below the floor is revised — by clarifying or replacing items —
and the pilot is repeated before the questionnaire is used for real. The final internal-consistency figures are
reported alongside the questionnaire results.

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
| Are the generated books acceptable in presentation quality and classroom suitability? | Expert validation interview (A) | **Qualitative acceptability**, coded per criterion via content analysis (Objective 3) |
| Does the fine-tuned judge classify character consistency to a usable standard? | Judge classification (Objective 4) | **Classification performance** against human-established reference labels — precision, recall, F1 (F1 primary); optionally compared against zero-shot and prompted baselines |
| Is the delivered software any good? | ISO/IEC 25010 questionnaire (D) | **Perceived software quality** — explicitly *not* output quality or classification performance (Objective 5) |

The system-evaluation questionnaire's average score is never presented as evidence that the generated outputs
are acceptable, or that the judge classifies well; those claims rest on Objective 3's expert validation and
Objective 4's classification metrics respectively. No instrument in this study makes a causal or
comparative-superiority claim about the pipeline itself: there is no control or comparison group (ADR-008). No
learning-gain claim is made by any instrument.
