# StoryBuddy — Evaluation Instruments & Validation Brief

> **Audience: the team.** This is the plain-language summary of what we decided about *how we evaluate
> StoryBuddy* and *why it is defensible*. It is a briefing, not the formal manuscript text — the manuscript
> instrument prose lives in `research_instruments.md`, and where the two disagree, `research_instruments.md`
> (and `methodology.md` above it) win. Decisions marked ⚠️ still need **adviser sign-off** before we run them.
>
> **Date of decisions:** 2026-07-21.
> **Realigned to manuscript:** 2026-07-25 (ADR-008 revised same date).

---

## 0. TL;DR

- The study has **five objectives**, built around the **pipeline as the core**: **Implement the pipeline →
  Produce picture books through it → Determine acceptability via expert validation → Evaluate judge
  classification performance → Evaluate software quality.**
- We use **four tools**, one per objective (Tool A supports Objectives 1–2 jointly):
  - **Tool A — Functional Verification Matrix:** did each pipeline stage run and produce valid output?
    (Evidence for Objectives 1–2.)
  - **Tool B — Expert Validation Interview:** are the generated books acceptable in presentation quality and
    classroom suitability, judged by expert validators through a written, open-ended interview? (Objective 3.)
  - **Judge classification:** does the fine-tuned consistency judge classify character consistency to a
    standard comparable with human-established labels — precision, recall, F1 (F1 primary)? (Objective 4.)
  - **Tool C — ISO/IEC 25010 questionnaire:** is the *software* functional, usable, reliable, efficient,
    secure? (Objective 5.)
- **Key decision on Tool B:** there is **no ready-made, validated instrument** for rating AI-generated
  children's picture books on a numeric scale, and with only a three-person validator panel a numeric rubric's
  statistics (CVI, Krippendorff's α) aren't meaningful anyway. The defensible path is a **written, open-ended
  interview form analysed by content analysis** — pre-set categories from five criteria, each response coded
  positive / negative / suggestion, tallied per criterion.
- **The judge fine-tune is now a full objective (4), not a descriptive footnote.** We fine-tune the judge and
  report **precision, recall, and F1 (F1 primary)** against human-established reference labels, split at the
  character-identity level. An optional, secondary comparison against a zero-shot base model and the existing
  prompted baseline may also be reported.
- **The naive-reader recall study and the Tier-2 Fun Toolkit engagement instrument are dropped entirely** —
  those studies no longer exist.

---

## 1. The five objectives (locked)

The pipeline is the core of the study; the objectives are structured around it.

1. **Implement** an orchestrated AI pipeline as the core processing framework of StoryBuddy.
2. **Produce** digital picture books from child-written stories through the implemented pipeline.
3. **Determine the acceptability** of the generated digital picture books in terms of presentation quality and
   classroom suitability, through **expert validation**.
4. **Evaluate the character-consistency classification performance** of the fine-tuned lightweight
   vision-language model against human-established reference labels, using precision, recall, and F1-score
   (F1 primary).
5. **Evaluate the software quality** of StoryBuddy using applicable ISO/IEC 25010 quality characteristics.

*(Source of truth: `research_direction_and_goals.md` §Objectives — that file needs to match this numbering;
flagged as a cross-reference to check, not confirmed fixed by this edit. The earlier framing of judge
fine-tuning as "the primary comparative study" is retired: the fine-tuned judge's classification performance
against human labels is Objective 4 in its own right, with a baseline comparison optional and secondary —
see §6.)*

---

## 2. The tools at a glance

| Tool | What it measures | Answers | Instrument type |
|---|---|---|---|
| **A — Functional Verification Matrix** | Did each pipeline stage complete and emit valid output? | Objectives 1–2 (pipeline works) | System-generated pass/fail records |
| **B — Expert Validation Interview** | Are the generated books acceptable — narrative coherence, story faithfulness, visual presentation, visual style consistency, suitability for classroom use? | Objective 3 (acceptability) | Written, open-ended interview form, analysed by content analysis |
| **Judge classification** | Does the fine-tuned judge classify character consistency to a standard comparable with human-established labels? | Objective 4 (classification performance) | Precision / recall / F1 (F1 primary) against human reference labels |
| **C — ISO/IEC 25010 questionnaire** | Is the *software* good (functional, usable, reliable, efficient, secure)? | Objective 5 (software quality) | 5-point Likert questionnaire |

**Why the split matters:** perceived software quality (Tool C) is **not** evidence that the outputs are
acceptable (Tool B), and neither is evidence about the judge's classification performance (Objective 4).
Keeping the legs separate is what stops a high questionnaire score from being mistaken for "the pipeline
works."

---

## 3. Tool A — AI Pipeline Functional Verification Matrix (Objectives 1–2)

**What it is:** for each corpus/fixture story, we record whether every pipeline stage completed successfully,
and report a success rate per functional category. It runs on **fixture stories**, so it needs **no ethics
clearance** and is valid October-defense material.

| Functional category | Modules | Pass = | Unit |
|---|---|---|---|
| Input validation & moderation | Input gate (safety + PII redaction) | Story cleared/blocked correctly, schema-valid Story Memory seed emitted | per story |
| Story analysis | Story Analyzer | Entities/coreference extracted into schema-valid Story Memory | per story |
| Scene structuring | Scene Segmentation, Story Memory | Story converted to sequential scenes, Story Memory still schema-valid | per story |
| Visual planning | Character Bible, Style Preset, Prompt Optimizer | Character refs + style + structured prompt produced, all schema-valid | per scene |
| Scene generation & refinement | Image Generator, Consistency Judge, Regeneration | **Consistency loop ran to a terminal state and a shippable page was produced** (incl. best-of fallback) | per scene |
| Picture book production | Compose, TTS narration, Export | Scenes assembled + narrated + exported as a complete book | per book |

**Two things we must get right in the write-up:**

1. **The formula:** `Success Rate = Successful ÷ Total × 100`. *(An earlier draft had this inverted — it
   would produce ≥100%.)*
2. **"Pass" ≠ "good."** A Pass means the stage **executed and emitted valid output**, not that the output
   was high quality. For scene generation specifically, a Pass = *the loop shipped a page* (including a page
   the judge flagged and best-of-fell-back on) — **not** "the judge approved it." Defining Pass as
   judge-approved would use the judge to score outputs, which breaks the non-circularity rule (ADR-004).
   **Functional completion ≠ output quality** — Tool B measures quality, Tool A measures completion.

**State the unit** (per-story vs. per-scene) in the table — the sample data mixes 50-per-story and
500-per-scene denominators, and those rates are only comparable if the unit is labelled.

---

## 4. Tool B — Expert Validation Interview (Objective 3) — the researched decision

### 4.1 Why not a numeric rubric

Earlier drafts scored the generated books on a numeric feature-level rubric (adapted from DreamBench++ and
Caldecott/ALSC criteria), validated via Content Validity Index and Krippendorff's α. Two problems didn't go
away: there is still **no single published, psychometrically validated instrument** that rates AI-generated
children's picture books across our constructs, and — more decisively — **CVI and Krippendorff's α are not
statistically meaningful with a 3-person validator panel** (the math needs a much larger rater/expert pool than
this study can field). Rather than force statistics the sample can't support, the manuscript's answer is a
**written, open-ended interview form, analysed by content analysis** — a method built for exactly this
respondent count, whose trustworthiness comes from a transparent coding procedure rather than an under-powered
statistic.

### 4.2 The instrument

Three purposively selected validators, each judging what they're best placed to judge:

| Validator | Judges |
|---|---|
| Dean/Professor of the Arts College | Visual/artistic presentation |
| Arts student/intern | Visual/artistic presentation |
| Education student/intern | Educational suitability |

Each validator completes a **written, open-ended interview form** against **five pre-set criteria**: narrative
coherence, story faithfulness, visual presentation, visual style consistency, and suitability for classroom
use. There is no numeric scale.

### 4.3 The analysis: content analysis

Each written response is coded against the five criteria and, within each criterion, coded as **positive
feedback**, **negative feedback**, or a **suggestion for improvement**. Codes are tallied per criterion. This
produces a systematic, auditable account of validator feedback without leaning on a rating scale or an
under-powered reliability statistic.

**Note:** the closed failure taxonomy we already use for the judge (`wrong_colour`, `wrong_species`,
`wrong_body_feature`, `wrong_clothing`, `wrong_style`, `different_face`, `character_absent`) is **not** part of
this interview instrument — that taxonomy now lives entirely under Objective 4 (judge classification), where it
grounds the judge's structured failure-reason output.

---

## 5. Tool C — ISO/IEC 25010 questionnaire (Objective 5)

**Keep as-is** — it is the one genuinely validated *standard* in the set. Five characteristics: **Functional
Suitability, Performance Efficiency, Usability, Reliability, Security.** Items use a **5-point Likert scale
(1 = Poor … 5 = Excellent)**, administered to **designated software-quality evaluators** (a group separate
from the Objective 3 expert validators). Reported as **weighted mean and standard deviation** per
characteristic, against the Table 4 interpretation bands declared in advance:

| Range | Interpretation |
|---|---|
| 4.20–5.00 | Excellent |
| 3.40–4.19 | Very Good |
| 2.60–3.39 | Good |
| 1.80–2.59 | Fair |
| 1.00–1.79 | Poor |

**Before administration** (already required by `methodology.md §6.4`): run **CVI** on the items, then a
**pilot** with **Cronbach's α ≥ 0.70** per subscale. Report both figures with the results.

---

## 6. Fidelity measure and judge classification — status

**Naive-reader recall — dropped entirely.** The comprehension study — a reader who never saw the story given
the finished book and scored on free recall against a story-grammar protocol — no longer exists as an
instrument. There is no reader-recall Cohen's κ, no story-grammar scoring, and no captions-stripped session.
Objective 3's acceptability claim now rests entirely on the expert validation interview (§4); there is no
separate fidelity/comprehension leg. *(Any reference to a `comprehension-instrument` build spec, or to a
Tier-2 / Fun Toolkit child-engagement instrument, in the roadmap or backlog is stale and should be removed —
outside the scope of this brief, but flagged here.)*

**Judge classification — now Objective 4 in full, not a descriptive footnote.**

- **Model:** the consistency judge, **Qwen2.5-VL-7B-Instruct fine-tuned with QLoRA** (the one sanctioned LoRA,
  ADR-016→018), performs binary character-consistency classification: **1 = Different Character** (positive
  class), **0 = Same Character**.
- **Metrics:** **precision, recall, and F1-score**, with **F1 as the primary summary metric**, computed
  against human-established reference labels.
- **Split:** at the **character-identity level** (train / validation / held-out test) — the same identity
  never appears in two subsets, so there's no identity leakage inflating the number.
- **Human labels:** two researchers annotate independently; disagreements resolved via the established
  criteria procedure; inter-annotator agreement is reported (an agreement statistic per
  `docs/specs/judge-finetune.md` — a different figure from the now-dropped reader-recall κ).
- **Optional, secondary:** the fine-tuned judge may additionally be compared against a **zero-shot base
  model** and the **existing prompted Consistency Judge baseline**, on the same held-out pairs and labels.
  This is optional and secondary to the fine-tuned judge's absolute classification performance against human
  labels — it is not a required deliverable, and it is not "forbidden" or "build-gate only" either.
- **ADR-018's δ = 3 non-inferiority gate is unaffected** — it is a *deployment* gate (does the fine-tuned
  judge replace the prompted incumbent in the product), not a reported research finding.

**Note for the record:** this changes the earlier framing, where this leg was reported "descriptively" with
"no comparative claim" and no F1/precision/recall metrics. Per the manuscript realignment (ADR-008, revised
2026-07-25), the fine-tuned judge's classification performance against human labels is Objective 4 outright,
scored with standard classification metrics, with an optional secondary baseline comparison.
**Propagation to `action_checklist.md`, `model_finetuning.md`, and `research_direction_and_goals.md` is
NOT covered by this edit** — those files are outside this brief's ownership and should be checked
separately for RQ-numbering and Objective-4-framing drift. *(A fourth target, `scope_revision_roadmap.md`,
was deleted 2026-07-27; the drift check no longer applies to it.)*

---

## 7. Validation methods — one-page reference

| Method | Used for | Target |
|---|---|---|
| **Content Validity Index (CVI)** — Lawshe (1975); Polit & Beck (2006) | ISO/IEC 25010 questionnaire (Tool C), before administration | I-CVI > 0.78; S-CVI/Ave ≥ 0.90 |
| **Cronbach's α** | Internal consistency of the ISO/IEC 25010 questionnaire (Tool C) | ≥ 0.70 |
| **Inter-annotator agreement** (statistic per `docs/specs/judge-finetune.md`) | Human reference labels for judge classification (Objective 4) | per `judge-finetune.md` |
| **Content analysis coding** | Expert validation interview responses (Tool B) — positive / negative / suggestion, tallied per criterion | Qualitative; not a reliability statistic |

**Dropped from this study:** Krippendorff's α and ICC(2,k) for a numeric expert rubric, and Cohen's κ for
naive-reader recall scoring — all tied to instruments that no longer exist (the feature-level rubric and the
comprehension study).

---

## 8. Still open — needs adviser / owner sign-off ⚠️

1. **Confirm the citation set below still applies.** DreamBench++ and Caldecott/ALSC were cited to ground the
   now-removed numeric feature-level rubric; verify whether they're still needed anywhere now that Objective 3
   uses an open-ended interview + content analysis instead (`action_checklist.md` A1/A2 history of unverified
   citations still applies to what remains).
2. **Judge-classification split sizes and the human-label agreement statistic/threshold** — deferred to
   `docs/specs/judge-finetune.md`, not finalized in this brief.

---

## 9. Citations

**Verified (high confidence) — safe to cite after a final check:**

- **DreamBench++** — Peng, Y. et al. (2024/2025), *DreamBench++: A Human-Aligned Benchmark for Personalized
  Image Generation.* arXiv:2406.16855; ICLR 2025. *(Now relevant to Objective 4's closed failure taxonomy —
  `wrong_colour`, `wrong_species`, etc. — not to Tool B, which dropped the numeric rubric this taxonomy
  originally anchored.)*
- **TIFA** — Hu, Y. et al. (2023), *TIFA: Accurate and Interpretable Text-to-Image Faithfulness Evaluation
  with Question Answering.* ICCV 2023; arXiv:2303.11897. *(No longer directly used by any surviving
  instrument in this brief — verify before citing.)*
- **Lawshe, C. H. (1975)** — *A quantitative approach to content validity.* Personnel Psychology, 28(4),
  563–575. *(Still used — grounds the ISO/IEC 25010 questionnaire's CVI step, Tool C.)*
- **Polit, D. F., & Beck, C. T. (2006)** — the Content Validity Index (CVI), Research in Nursing & Health.
  *(Still used — Tool C.)*
- **Caldecott Medal criteria** — Association for Library Service to Children (ALSC/ALA). *(Recognized
  criteria, not a validated instrument; its relevance to Tool B's five interview criteria — narrative
  coherence, visual presentation, suitability — is plausible but unconfirmed now that Tool B is qualitative;
  verify before citing.)*

**Do NOT cite (unverified / could not be traced):**

- A recurring "20 annotators, Fleiss κ = 0.72, Cronbach α > 0.8" story-visualization figure — no traceable
  primary source. It shows the *shape* of a standard protocol; do not attribute the numbers to any paper.
- Several future-dated / obscure arXiv IDs that surfaced in search (e.g. 260x.xxxxx) — unverified; ignore.
