# Research Instruments and Their Validation

> **Manuscript-prose section.** Written in the formal register of the manuscript, intended to be pasted into
> the Methodology chapter after *Data Collection* and *Data Set*. It is the prose realization of
> `docs/capstone/methodology.md` §5.2 and §6, and it inherits the separation of instrument families declared
> there. Where this section and `methodology.md` disagree, `methodology.md` is authoritative and this is a
> defect. Items marked ⚠️ require adviser sign-off before administration.
>
> **This section is also where the two things `methodology.md` §6.2 defers are finalized:** the three named
> expert evaluators, and the feature-level indicators their rubric scores.

---

## Research Instruments

This study uses **two distinct families of instrument**, and they answer different questions. Conflating them
is the most common way a system-evaluation is quietly hollowed out — a high average rating on a satisfaction
questionnaire is not evidence that the generated outputs are good, because such a questionnaire has no
feature-level ground truth and no reader-recall task. The instruments are therefore described and reported
separately, and the division of labour between them is stated explicitly at the end of this section.

The first family measures the **quality and fidelity of the generated outputs** — whether the delivered
storybook, its illustrations, and its cross-scene consistency are good, and whether the finished book lets a
naive reader recover the child's story. These are **absolute, single-arm** measures on the one generated book:
the comparative pipeline-ON-vs-OFF ablation is dropped (ADR-008), so no instrument here makes a causal
"the pipeline helped" claim, and the October type-A defense does not require one. The second family measures
the **perceived quality of the software artifact** — whether the delivered system is functional, usable,
reliable, efficient, and secure — and is answered by a structured questionnaire administered to practitioner
evaluators.

The study's one **comparative** result lives outside both families, in the fine-tuned judge's agreement with
human labels (RQ6, §D and `docs/specs/judge-finetune.md`), which is the primary comparative study (ADR-008).

### A. The expert-panel output-quality rating instrument (RQ1, RQ3)

The generated storybooks are rated by a **three-person expert panel** — **one professor, one education
student, and one art student** — the panel the defense panel asked for to *evaluate the generated outputs*
(storybook, illustrations, story consistency), not the internal pipeline components. Each brings a distinct
lens: the art student judges illustrative craft, the education student judges classroom and narrative fit, and
the professor anchors overall acceptability. Books are presented with provenance stripped: opaque filenames and
shuffled order. Because the ablation is dropped, ratings are **absolute on the single generated arm** — there
is no ON/OFF condition to compare against; the panel scores how good each output is on its own terms.

For each book the panel records ordinal (five-point) judgments on the following measures. Crucially, **each
measure is scored against explicit feature-level indicators, not a bare "consistent / inconsistent" verdict**
(defense-panel note 13): a rater marks which specific features hold or fail across scenes, and the ordinal
score is grounded in that checklist rather than an overall impression.

| Measure | Feature-level indicators the rater checks across scenes | Scale |
|---|---|---|
| Character consistency | Colour/palette, species/silhouette, body features (e.g. eye count, wings, hairstyle), clothing/accessories, facial identity, presence in frame | Ordinal, 1–5 |
| Style consistency | Rendering technique (e.g. flat gouache vs. photorealistic), palette, line/texture treatment held across scenes | Ordinal, 1–5 |
| Narrative coherence | Do the illustrations, in sequence, tell a connected story? | Ordinal, 1–5 |
| Illustration quality | Craft of the illustration, independent of consistency | Ordinal, 1–5 |
| Story completeness | Proportion of annotated major plot points (Instrument C) represented in the selected scenes | 0–1 |

**The character- and style-consistency indicators are the same closed taxonomy the consistency judge is
trained and evaluated on** (`docs/specs/judge-finetune.md` §4): `wrong_colour`, `wrong_species`,
`wrong_body_feature`, `wrong_clothing`, `wrong_style`, `different_face`, `character_absent`. Reusing one
taxonomy for the human rubric and the model's targets means the human ratings and RQ6's judge evaluation speak
about consistency in exactly the same vocabulary — one taxonomy, designed once (Phase 1), used everywhere.

This instrument carries the output-quality claim of Objective 3 (RQ3) and, via Story completeness, the
scene-selection claim (RQ1). It is a quality measure, not a causal one.

### B. The naive-reader comprehension instrument (RQ5) — the output-fidelity measure

A reader who has **never seen the original story text** is given the finished book alone and then asked:

1. **Who was the story about?** — free recall of characters.
2. **What happened?** — free recall of events.
3. *What can you say about the story?* — reflective and **unscored**, retained only as a qualitative source.

Free recall is used rather than multiple choice because a recognition item contains its own answer, whereas
free recall does not. The reader is a naive third party rather than the child author because an author knows
what they intended and will read that intention into any illustration, whereas a stranger can only recover what
the book actually transmits. **This is a single-arm measure: each reader sees the one generated book and has
never read its source text**, so recall measures transmission, not memory of a text already seen. There is no
ON/OFF pairing (the ablation is dropped, ADR-008); the measure is the **recovery proportion itself** — the
proportion of annotated characters and of annotated major plot points recovered — not a between-arm difference.

Responses are scored against the plot-point and character annotation described in Instrument C, by **two
independent scorers**, with **Cohen's κ** reported. The scoring follows a **validated recall protocol**: a
**story-grammar inclusion score** — the source story is parsed into content units by story-grammar category
(setting, initiating event, attempt, consequence, reaction) in the Stein & Glenn (1979) tradition, and each
recall is scored for the proportion of those units it reproduces (cf. Mandler & Johnson 1977 for recall-protocol
scoring). This measures *content transmitted*, not the reader's own storytelling skill, which is why the
alternative Narrative Scoring Scheme is **not** used: NSS rates the narrator's production quality (character
development, mental-state language, cohesion) and would confound reader articulacy with book fidelity — the
wrong construct for a transmission measure. The story-grammar categories also map directly onto Instrument C's
"major plot points," so annotation and scoring share one skeleton, and they are language-robust across Grade 5–6
English and Taglish. ⚠️ **Adviser-confirm** the exact citation and its Grade 5–6 / Taglish adaptation before
administration (roadmap §0.6, §3; verify the citation against the A1/A2 integrity check). This is the study's
output-fidelity measure of record.

### C. The plot-point and character annotation (shared substrate for RQ1 and RQ5)

Two trained annotators independently mark the **major plot points** and **characters** of each corpus story
*from the text alone*, before any illustration is generated, so that the annotation cannot be contaminated by
what the system happened to draw. This single annotation is used twice: to score whether the system selected
scenes covering those plot points (RQ1, via Instrument A's Story completeness) and to score whether a naive
reader recovered them from the finished book (RQ5, Instrument B). **One annotation, two uses.**

### D. The system-evaluation questionnaire — perceived software quality (ISO/IEC 25010) ⚠️

Separately from the output instruments above, the delivered **software artifact** is evaluated with a
structured questionnaire administered to **Information Technology practitioners and teachers**, following the
**ISO/IEC 25010** software product quality model. This is the operator-facing *software* leg, kept as a
**separate instrument** from the expert panel's output ratings (defense-panel note 11): the panel judges the
artifacts the system produces; this questionnaire judges the system itself. Its evaluators are practitioners
with the technical and classroom vantage to judge software-quality characteristics, not the output-artifact
panel of §A. Items are five-point Likert-type and are reported as the mean and standard deviation per quality
characteristic, against an interpretation scale declared in advance of administration.

| Characteristic | What the items ask about |
|---|---|
| Functional suitability | Does the system do what it claims — analyze, segment, illustrate, narrate, export? |
| Usability | Can a Grade 5–6 student and a teacher operate it without instruction? |
| Reliability | Does it recover from a stalled or failed generation without losing work? |
| Performance efficiency | Is generation time acceptable within a classroom period? |
| Security | Are classroom data isolation and asset-access controls effective? |

This questionnaire measures **perceived software quality only.** It is a software-engineering deliverable and
it belongs in the study, but it does not, and is not presented to, answer whether the generated outputs are
good (that is the expert panel's feature-level job, RQ3) or whether the book transmits the story (RQ5) — it
involves no feature-level ground truth and no reader-recall task. The output-quality dimensions in Instrument A
are deliberately *not* folded into this questionnaire, and usability is measured here (operator-facing), never
by the expert panel.

### E. Child instruments — Tier 2 enrichment ⚠️

Where Ethics Stage 2 clearance permits child participation, Grade 5–6 participants complete validated
child-appropriate instruments — the Fun Toolkit (Smileyometer and Again-Again tables) for engagement, and a
single story-fidelity item — supplemented by behavioral usage logs, which are more reliable than child
self-report. This tier is enrichment: it enriches the findings but is not required to answer any research
question, and it may be reduced or omitted without invalidating the study.

### The consistency judge as a validated instrument (RQ6)

The pipeline's own vision-language consistency judge is itself treated as a measurement instrument whose
validity is established empirically, against human labels, on a character-disjoint held-out set. Its
construction, training, and evaluation are described under *Data Set* and *Training and Validation* and in
`docs/specs/judge-finetune.md`; it is noted here only to record that it is held to the same standard of
demonstrated validity as the human instruments, that its agreement with humans (RQ6) is the study's **primary
comparative result** (ADR-008), and — critically — that it is **never** used to score the output evaluation,
since the judge drives regeneration inside the pipeline and using it to score the outputs it helped produce
would be circular (ADR-004).

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

The expert-panel rating instrument (A), the comprehension scoring (B), and the plot-point annotation (C) are
human judgments, and a rater is not an instrument until calibrated. Every human measurement in this study
follows the same protocol:

1. **A written scoring guide** with worked examples and explicit edge cases is produced before any real data is
   scored. For the image-related judgments, the guide fixes the closed taxonomy of feature-level indicators
   (Instrument A; `judge-finetune.md` §4).
2. **Practice items drawn from outside the reported corpus** — fixture stories for the text tasks, probe
   images for the image tasks — are scored first. Real material is never used for calibration.
3. **Calibration.** Inter-rater agreement is computed on the practice set as **Krippendorff's α**. Scoring of
   real data does not begin until **α ≥ 0.67**, the conventional floor for drawing even tentative conclusions;
   **α ≥ 0.80** is the target. If the floor is not met, the guide is revised and the raters re-calibrate.
   Revising the guide is legitimate; revising the data is not.
4. **Adjudication.** Disagreements on real data are resolved by a third researcher, and the adjudication rate is
   reported.
5. **Drift check.** Agreement is recomputed midway through scoring, because raters relax over long sessions.
6. **Blinding.** No rater sees provenance (opaque filenames, shuffled order), and no comprehension scorer sees
   the story text before scoring a recall response.

The final inter-rater reliability on the real data is reported **alongside every human measure** — a measure
reported without its reliability figure is treated as incomplete.

---

## What each instrument can and cannot support

To prevent any instrument from being asked to carry a claim it cannot bear, the division of labour is fixed in
advance:

| Question | Instrument | What it can support |
|---|---|---|
| Are the generated outputs good? | Expert-panel output rating (A) | **Feature-level output quality** — absolute, on the single generated arm; not a causal claim (RQ1, RQ3) |
| Does the book transmit the story? | Naive-reader comprehension (B) | A **human fidelity outcome** — whether the story is transmitted (RQ5) |
| Can the judge measure consistency automatically? | Judge evaluation (RQ6) | **Instrument validity** of the automated judge — the study's primary comparative result |
| Is the delivered software any good? | ISO/IEC 25010 questionnaire (D) | **Perceived software quality** — explicitly *not* output quality or efficacy |
| Do children enjoy and re-use it? | Fun Toolkit and usage logs (E) | **Engagement**, as Tier-2 enrichment |

The system-evaluation questionnaire's average score is never presented as evidence that the generated outputs
are good; that claim rests on the expert panel's feature-level ratings (A) and the comprehension instrument
(B). With the ablation dropped there is no control arm, so **no instrument makes a causal "the pipeline helped"
claim** — the outputs are evaluated in absolute terms, which is what the October type-A defense requires
(ADR-008). No learning-gain claim is made by any instrument.
