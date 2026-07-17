# Research Instruments and Their Validation

> **Manuscript-prose section.** Written in the formal register of the manuscript, intended to be pasted into
> the Methodology chapter after *Data Collection* and *Data Set*. It is the prose realization of
> `docs/capstone/methodology.md` §5.2 and §6, and it inherits the separation of instrument families declared
> there. Where this section and `methodology.md` disagree, `methodology.md` is authoritative and this is a
> defect. Items marked ⚠️ require adviser sign-off before administration.

---

## Research Instruments

This study uses **two distinct families of instrument**, and they answer different questions. Conflating them
is the most common way a system-evaluation is quietly hollowed out — a high average rating on a satisfaction
questionnaire is not evidence that the consistency mechanism works, because such a questionnaire has no control
condition, no blinding, and no ground truth. The instruments are therefore described and reported separately,
and the division of labour between them is stated explicitly at the end of this section.

The first family measures the **effectiveness of the consistency pipeline** — whether it improves visual
consistency and whether that improvement lets a reader recover the child's story. These are causal and outcome
claims, and they are answered by blind, controlled measurement rather than by opinion. The second family
measures the **perceived quality of the software artifact** — whether the delivered system is functional,
usable, reliable, efficient, and secure — and is answered by a structured questionnaire administered to expert
evaluators.

### A. The blind storybook rating instrument (RQ1, RQ2, RQ3)

Adult raters are shown generated storybooks with the experimental condition and provenance stripped away:
opaque filenames, shuffled presentation order, and no indication of whether a book was produced by the
pipeline-ON or pipeline-OFF condition. For each book, raters record ordinal (five-point) judgments on the
following dimensions:

| Measure | Definition | Scale |
|---|---|---|
| Character consistency | Is the same character recognizable across scenes? | Ordinal, 1–5 |
| Style consistency | Is the visual style maintained across scenes? | Ordinal, 1–5 |
| Narrative coherence | Do the illustrations tell a connected story? | Ordinal, 1–5 |
| Illustration quality | Craft of the illustration, independent of consistency | Ordinal, 1–5 |
| Story completeness | Proportion of annotated major plot points represented in the selected scenes | 0–1 |

Because every story is generated twice under seed-matched pipeline-ON and pipeline-OFF conditions, and raters
never learn which is which, the difference in ratings between the two conditions is attributable to the
pipeline and not to incidental factors. This is the instrument that carries the study's central effectiveness
claim (RQ2).

### B. The naive-reader comprehension instrument (RQ5)

A reader who has **never seen the original story text** is given the finished book alone and then asked:

1. **Who was the story about?** — free recall of characters.
2. **What happened?** — free recall of events.
3. *What can you say about the story?* — reflective and **unscored**, retained only as a qualitative source.

Free recall is used rather than multiple choice because a recognition item contains its own answer, whereas
free recall does not. The reader is a naive third party rather than the child author because an author knows
what they intended and will read that intention into any illustration, whereas a stranger can only recover what
the book actually transmits. Each reader sees exactly one book in exactly one condition, counterbalanced across
stories, so that recall measures transmission and not memory of a story already seen. Responses are scored
against the plot-point and character annotation described in Instrument C. This is the study's outcome measure
of record.

### C. The plot-point and character annotation (shared substrate for RQ1 and RQ5)

Two trained annotators independently mark the **major plot points** and **characters** of each corpus story
*from the text alone*, before any illustration is generated, so that the annotation cannot be contaminated by
what the system happened to draw. This single annotation is used twice: to score whether the system selected
scenes covering those plot points (RQ1) and to score whether a naive reader recovered them from the finished
book (RQ5).

### D. The system-evaluation questionnaire — perceived software quality (ISO/IEC 25010) ⚠️

Separately from the effectiveness instruments above, the delivered software artifact is evaluated with a
structured questionnaire administered to **Information Technology practitioners and teaching practitioners**,
following the **ISO/IEC 25010** software product quality model. Items are five-point Likert-type and are
reported as the mean and standard deviation per quality characteristic, against an interpretation scale
declared in advance of administration.

| Characteristic | What the items ask about |
|---|---|
| Functional suitability | Does the system do what it claims — analyze, segment, illustrate, narrate, export? |
| Usability | Can a Grade 5–6 student and a teacher operate it without instruction? |
| Reliability | Does it recover from a stalled or failed generation without losing work? |
| Performance efficiency | Is generation time acceptable within a classroom period? |
| Security | Are classroom data isolation and asset-access controls effective? |

This questionnaire measures **perceived software quality only.** It is a software-engineering deliverable and
it belongs in the study, but it does not, and is not presented to, answer whether the consistency pipeline
improves consistency (RQ2) or whether that improvement transmits the story (RQ5) — it involves no control
condition, no blinding, and no ground truth. The consistency dimensions in Instrument A are deliberately *not*
folded into this questionnaire.

### E. Child instruments — Tier 2 enrichment ⚠️

Where Ethics Stage 2 clearance permits child participation, Grade 5–6 participants complete validated
child-appropriate instruments — the Fun Toolkit (Smileyometer and Again-Again tables) for engagement, and a
single story-fidelity item — supplemented by behavioral usage logs, which are more reliable than child
self-report. This tier is enrichment: it enriches the findings but is not required to answer any research
question, and it may be reduced or omitted without invalidating the study.

### The consistency judge as a validated instrument (RQ6)

The pipeline's own vision-language consistency judge is itself treated as a measurement instrument whose
validity is established empirically, against human labels, on a character-disjoint held-out set. Its
construction, training, and evaluation are described under *Data Set* and *Training and Validation*; it is
noted here only to record that it is held to the same standard of demonstrated validity as the human
instruments, and — critically — that it is **never** used as the outcome measure for RQ2, since the judge
drives regeneration inside the pipeline-ON arm and using it to score that arm would be circular.

---

## Validation of the Instruments

An instrument is not trustworthy merely because it exists. Two properties are established before any
instrument's results are reported: that it measures the right thing (**validity**) and that it measures
consistently (**reliability**). The procedure differs between the questionnaire and the human-scored
instruments, and both are described below.

### Content and face validity of the questionnaire ⚠️

Before administration, the ISO/IEC 25010 system-evaluation questionnaire is reviewed by a panel of **expert
validators** — practitioners with relevant software-engineering or educational-technology background — who
judge whether each item is clear, relevant to the quality characteristic it claims to measure, and free of
ambiguity. Item-level and scale-level agreement is quantified with a **Content Validity Index (CVI)**, and
items falling below the accepted threshold are revised or removed. The questionnaire is not administered to
real evaluators until this review is complete. This step establishes that the questionnaire measures the ISO/IEC
25010 characteristics it claims to, rather than assuming it.

### Reliability pilot of the questionnaire

The validated questionnaire is then piloted with a small group of evaluators who are not part of the reported
sample. The **internal consistency** of each subscale is computed as **Cronbach's α**, with a conventional
floor of **α ≥ 0.70**. A subscale that falls below the floor is revised — by clarifying or replacing items —
and the pilot is repeated before the questionnaire is used for real. The final internal-consistency figures are
reported alongside the questionnaire results.

### Calibration and reliability of the human-scored instruments ⚠️

The rating instrument (A), the comprehension scoring (B), and the plot-point annotation (C) are human
judgments, and a rater is not an instrument until calibrated. Every human measurement in this study follows the
same protocol:

1. **A written scoring guide** with worked examples and explicit edge cases is produced before any real data is
   scored. For the image-related judgments, the guide fixes a closed taxonomy of failure reasons.
2. **Practice items drawn from outside the reported corpus** — fixture stories for the text tasks, probe
   images for the image tasks — are scored first. Real material is never used for calibration.
3. **Calibration.** Inter-rater agreement is computed on the practice set as **Krippendorff's α**. Scoring of
   real data does not begin until **α ≥ 0.67**, the conventional floor for drawing even tentative conclusions;
   **α ≥ 0.80** is the target. If the floor is not met, the guide is revised and the raters re-calibrate.
   Revising the guide is legitimate; revising the data is not.
4. **Adjudication.** Disagreements on real data are resolved by a third researcher, and the adjudication rate is
   reported.
5. **Drift check.** Agreement is recomputed midway through scoring, because raters relax over long sessions.
6. **Blinding.** No rater sees the experimental condition, and no comprehension scorer sees the story text
   before scoring a recall response.

The final inter-rater reliability on the real data is reported **alongside every human measure** — a measure
reported without its reliability figure is treated as incomplete.

---

## What each instrument can and cannot support

To prevent any instrument from being asked to carry a claim it cannot bear, the division of labour is fixed in
advance:

| Question | Instrument | What it can support |
|---|---|---|
| Does the consistency loop change visual consistency? | Blind storybook rating (A), ON vs OFF | A **causal** claim about the pipeline — the two conditions differ only in whether it runs |
| Does that change matter to a reader? | Naive-reader comprehension (B) | A **human outcome** — whether the story is transmitted |
| Can the judge measure consistency automatically? | Judge evaluation (RQ6) | **Instrument validity** of the automated judge |
| Is the delivered software any good? | ISO/IEC 25010 questionnaire (D) | **Perceived software quality** — explicitly *not* effectiveness |
| Do children enjoy and re-use it? | Fun Toolkit and usage logs (E) | **Engagement**, as Tier-2 enrichment |

The system-evaluation questionnaire's average score is never presented as evidence that the consistency
pipeline works; that claim rests solely on the blind ablation (A) and the comprehension instrument (B). No
learning-gain claim is made by any instrument.
