# StoryBuddy — Evaluation Instruments & Validation Brief

> **Audience: the team.** This is the plain-language summary of what we decided about *how we evaluate
> StoryBuddy* and *why it is defensible*. It is a briefing, not the formal manuscript text — the manuscript
> instrument prose lives in `research_instruments.md`, and where the two disagree, `research_instruments.md`
> (and `methodology.md` above it) win. Decisions marked ⚠️ still need **adviser sign-off** before we run them.
>
> **Date of decisions:** 2026-07-21.

---

## 0. TL;DR

- The study has **four objectives**, built around the **pipeline as the core**: **Develop → Implement →
  Evaluate the outputs → Evaluate the software.**
- We use **three evaluation tools**, one per evaluation job:
  - **Tool A — Functional Verification Matrix:** did each pipeline stage run and produce valid output?
    (Evidence for Objectives 1–2.)
  - **Tool B — Expert Picture Book Evaluation:** are the generated books *good*, judged by experts against
    feature-level criteria? (Objective 3.)
  - **Tool C — ISO/IEC 25010 questionnaire:** is the *software* functional, usable, reliable, efficient,
    secure? (Objective 4.)
- **Key research finding on Tool B:** there is **no ready-made, validated instrument** for rating
  AI-generated children's picture books. The honest, defensible path is to **adopt a validated protocol
  (DreamBench++) + recognized picture-book criteria (Caldecott), then re-validate the combined rubric
  ourselves** (content validity + inter-rater reliability). Producing that validated instrument is part of
  our contribution.
- **The judge fine-tune stays, but the fine-tuned-vs-baseline *comparison* is dropped** to fit the October
  timeline. We fine-tune the judge and **report its results descriptively** — no comparative claim.
- **RQ5 (naive-reader recall) is kept**, unchanged, as part of Objective 3.

---

## 1. The four objectives (locked)

The pipeline is the core of the study; the objectives are structured around it — one verb each.

1. **Develop** the StoryBuddy pipeline — child story → consistent illustrated storybook.
2. **Implement** the pipeline as a deployable, teacher-operated system.
3. **Evaluate the generated outputs** — storybook, illustrations, story consistency — by expert panel,
   plus a naive-reader recall measure.
4. **Evaluate the software quality** of StoryBuddy against ISO/IEC 25010.

*(Source of truth: `research_direction_and_goals.md` §Objectives. The earlier Objective 4 — "assess the
judge fine-tune as the primary comparative study" — has been demoted; see §6.)*

---

## 2. The three tools at a glance

| Tool | What it measures | Answers | Instrument type |
|---|---|---|---|
| **A — Functional Verification Matrix** | Did each pipeline stage complete and emit valid output? | Objectives 1–2 (pipeline works) | System-generated pass/fail records |
| **B — Expert Picture Book Evaluation** | Is the generated book *good* (style/character consistency, faithfulness, layout, craft, suitability)? | Objective 3 (output quality) | Expert-rated feature-level rubric |
| **C — ISO/IEC 25010 questionnaire** | Is the *software* good (functional, usable, reliable, efficient, secure)? | Objective 4 (software quality) | Likert questionnaire |
| *RQ5 — Naive-reader recall* | Does the finished book *transmit the child's story* to someone who never read it? | Objective 3 (fidelity) | Free-recall, scored vs. plot-point annotation |

**Why the split matters:** perceived software quality (Tool C) is **not** evidence that the outputs are good
(Tool B), and neither proves the book transmits the story (RQ5). Keeping them separate is what stops a high
questionnaire score from being mistaken for "the pipeline works."

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

## 4. Tool B — Expert Picture Book Evaluation (Objective 3) — the researched decision

### 4.1 What the literature sweep found

- **There is no single published, psychometrically validated instrument** that rates AI-generated children's
  picture books across all our constructs (style consistency, character consistency, narrative layout,
  story faithfulness, illustration craft, educational suitability).
- What exists splits in two, and each covers only part:
  - **Validated AI/HCI rating protocols** (DreamBench++, TIFA) — cover **character/style consistency** and
    **story faithfulness**, and come with real **reliability protocols** — but say nothing about layout,
    craft, or educational suitability.
  - **Children's-literature criteria** (Caldecott/ALSC, classroom rubrics) — cover **layout, craft,
    suitability** — but carry **no validity/reliability evidence** (they are award criteria and teaching
    tools, not validated instruments).

### 4.2 The decision: adopt + adapt + re-validate

We build **one rubric** by combining the two, on a **single 0–4 ordinal scale with anchor descriptions per
level** (DreamBench++'s scale, because it ships with published anchors that make raters agree):

| Our construct | Based on |
|---|---|
| Character consistency | DreamBench++ "concept preservation" (shape, color, texture, face) — = our closed failure taxonomy (`wrong_colour`, `wrong_species`, `wrong_body_feature`, `wrong_clothing`, `wrong_style`, `different_face`, `character_absent`) |
| Visual style consistency | DreamBench++ texture/shape + `wrong_style` |
| Story faithfulness | DreamBench++ "prompt following" (relevance, accuracy, completeness) |
| Narrative layout & flow | Caldecott — pictorial interpretation / visual pacing |
| Illustration craft | Caldecott — excellence of execution |
| Overall suitability | Caldecott — appropriateness of style to audience |

**Note:** this is *not* "making up our own tool." Each construct is anchored to a published source, and the
combined rubric earns its validity through the validation procedure below. **The good news:** our existing
`research_instruments.md §A` already does feature-level indicators and already uses the closed taxonomy and
Krippendorff's α — so this decision mostly *grounds and cites* what we already had, and replaces the weaker
"bare Likert, mean/SD, no reliability" draft.

### 4.3 How we validate it (this is what makes the metrics trustworthy)

1. **Content validity, first, before any book is rated.** A **separate expert pool** scores each rubric item
   for relevance; we compute the **Content Validity Index (CVI)** — target **I-CVI > 0.78**, **S-CVI/Ave ≥
   0.90**. Sub-threshold items are revised or removed.
2. **Pilot** the rubric on 2–3 books with the anchored scoring guide; revise ambiguous items.
3. **Inter-rater reliability on real ratings:** **Krippendorff's α** (primary; ≥ 0.667 acceptable, ≥ 0.80
   good) and/or **ICC(2,k)** for the averaged 3-rater score.
4. **Internal consistency:** **Cronbach's α ≥ 0.70** across the items.

### 4.4 The 3-rater problem, and the safe fix ⚠️

Our rating panel is **3 people** (professor + education student + art student) — locked, and the one the
defense panel asked for. But with only 3 raters, CVI/κ/α are statistically fragile (content-validity math
isn't meaningful below ~5 experts). **Decision (⚠️ adviser-confirm):**

- **Keep the 3-person panel for rating the books.**
- **Run the content-validity (CVI) step with a *separate, larger* expert pool (≥ 5)** — reuse the same
  validator-panel concept we already use for the ISO/IEC 25010 questionnaire. This does **not** change the
  locked 3-person rating panel; it is a different group doing a different job (validating the instrument, not
  scoring the books).
- **Report the 3-panel reliability descriptively** — show the α, don't over-claim from n = 3.

This puts the statistical weight where it holds (content validity, ≥ 5 experts), keeps the rating panel the
defense endorsed, and claims nothing the sample can't support.

---

## 5. Tool C — ISO/IEC 25010 questionnaire (Objective 4)

**Keep as-is** — it is the one genuinely validated *standard* in the set. Five characteristics: functional
suitability, usability, reliability, performance efficiency, security. Reported as **mean and SD** per
characteristic against an interpretation scale declared in advance.

**Before administration** (already required by `methodology.md §6.4`): run **CVI** on the items, then a
**pilot** with **Cronbach's α ≥ 0.70** per subscale. Report both figures with the results.

---

## 6. RQ5 and RQ6 — status

**RQ5 (naive-reader recall) — kept, unchanged.** A reader who never saw the story gets the finished book and
freely recalls *who* and *what happened*; recall is scored against the plot-point annotation by two raters
(Cohen's κ). It is the study's **output-fidelity** measure and lives under **Objective 3**. Instrument text:
`research_instruments.md §B`. *(No new tool needed — this already exists.)*

**RQ6 (judge fine-tune) — fine-tune kept, comparison dropped.**

- **What stays:** we still **fine-tune the consistency judge** (the one sanctioned LoRA, ADR-016→018) and
  **report its results descriptively** (its agreement with human labels on the character-disjoint held-out
  set). For that number to be trustworthy, the human labels still need inter-rater reliability reported and
  the held-out set read once.
- **What's dropped:** the **fine-tuned-vs-baseline comparison** as a formal research claim. **Reason:** to
  finish the capstone by **October**, the comparative study leg was cut. We do not make a "fine-tuned beats
  prompted" claim.
- **Note for the record:** this **reverses** the earlier locked decision (`scope_revision_roadmap.md` §0.2,
  which made RQ6 the *primary comparative study*). Because it's a reversal of a locked decision, it is logged
  in `design_decisions_and_risks.md` (R4). **ADR-008 was revised 2026-07-22** to make this the authoritative
  position, and **propagation is done** across `methodology.md §7.3`, `research_direction_and_goals.md`
  (§Objectives and §3), `value_proposition.md`, `research_instruments.md`, `action_checklist.md`,
  `model_finetuning.md`, and `scope_revision_roadmap.md`. The study consequently has **no primary comparative
  study** and makes no causal or comparative claim. **ADR-018's δ = 3 non-inferiority gate is unaffected** —
  it is a *deployment* gate (does the fine-tuned judge replace the prompted incumbent in the product), not a
  reported finding.

---

## 7. Validation methods — one-page reference

| Method | Used for | Target |
|---|---|---|
| **Content Validity Index (CVI)** — Lawshe (1975); Polit & Beck (2006) | Every instrument, before use, scored by a **separate ≥5 expert pool** | I-CVI > 0.78; S-CVI/Ave ≥ 0.90 |
| **Krippendorff's α** | Inter-rater reliability of expert ratings (Tool B) and recall scoring | ≥ 0.80 good; ≥ 0.667 tentative floor |
| **ICC(2,k)** | Reliability of the averaged 3-rater score (alternative to α) | — |
| **Cohen's κ** | Two-rater recall scoring (RQ5) | reported |
| **Cronbach's α** | Internal consistency (Tool C questionnaire; Tool B if treated as one scale) | ≥ 0.70 |

---

## 8. Still open — needs adviser / owner sign-off ⚠️

1. **Validator-pool size and CVI/α thresholds** — recommendation is *3-person rating panel + separate ≥5
   CVI pool*; confirm with adviser (`action_checklist.md` B8/B9).
2. **Named recall protocol for RQ5** — story-grammar scoring, fit to Grade 5–6 English + Taglish; adviser-confirm.
3. **Citation verification** — verify every citation below independently before it enters the manuscript
   (we have a history of unverified citations; see `action_checklist.md` A1/A2).

---

## 9. Citations

**Verified (high confidence) — safe to cite after a final check:**

- **DreamBench++** — Peng, Y. et al. (2024/2025), *DreamBench++: A Human-Aligned Benchmark for Personalized
  Image Generation.* arXiv:2406.16855; ICLR 2025.
- **TIFA** — Hu, Y. et al. (2023), *TIFA: Accurate and Interpretable Text-to-Image Faithfulness Evaluation
  with Question Answering.* ICCV 2023; arXiv:2303.11897.
- **Lawshe, C. H. (1975)** — *A quantitative approach to content validity.* Personnel Psychology, 28(4),
  563–575.
- **Polit, D. F., & Beck, C. T. (2006)** — the Content Validity Index (CVI), Research in Nursing & Health.
- **Caldecott Medal criteria** — Association for Library Service to Children (ALSC/ALA). *(Recognized
  criteria, not a validated instrument — use for item language only.)*

**Do NOT cite (unverified / could not be traced):**

- A recurring "20 annotators, Fleiss κ = 0.72, Cronbach α > 0.8" story-visualization figure — no traceable
  primary source. It shows the *shape* of a standard protocol; do not attribute the numbers to any paper.
- Several future-dated / obscure arXiv IDs that surfaced in search (e.g. 260x.xxxxx) — unverified; ignore.
