# ADR-008 — Evaluation: three-objective evaluation (expert validation + judge classification + ISO-25010)

**Status:** Accepted · **revised 2026-07-25** — realigned to the updated manuscript, which is now the
authoritative statement of scope. Supersedes the 2026-07-22 revision. Three changes: (1) the **RQ5
naive-reader comprehension study is dropped entirely** — no reader-recall leg, no Tier-2 children, no Fun
Toolkit; (2) the **fine-tuned judge's classification performance is promoted to a formal objective**
(Objective 4: precision / recall / F1 vs human reference labels, F1 primary), with an **optional**
comparison vs the zero-shot base and the existing prompted baseline permitted; (3) the **RQ1–RQ6
apparatus is retired** in favour of the manuscript's five numbered objectives.

> **Revision history.** *2026-07-20:* the pipeline-ON-vs-OFF ablation (RQ2) was dropped as the study
> spine and RQ6 (judge comparison) was promoted to primary comparative study in its place.
> *2026-07-22:* RQ6 was demoted too — judge reported descriptively, no comparative claim, and Objective 4
> became ISO/IEC 25010. *2026-07-25 (this revision):* the updated manuscript reinstates the judge as a
> **standing objective measured by standard classification metrics** and **removes the reader-comprehension
> leg** the 07-20/07-22 revisions had kept. The study now has **five objectives** and **three evaluation
> legs** (Obj 3, 4, 5). The comparative claim returns only in its weakest form — *optional*, secondary to
> the fine-tuned model's absolute agreement with human labels.

**Context:** The manuscript's Objectives section is now the contract. It enumerates five objectives and
evaluates the system through three procedures: expert validation of the generated picture books,
classification-performance evaluation of the fine-tuned Consistency Judge, and ISO/IEC 25010 software
quality. It lists no naive-reader/child-reader comprehension study in its Respondents or Data-Collection
sections. This ADR restructures the evaluation to match.

**Decision:** Five objectives (verbs from the manuscript: Implement → Produce → Determine → Evaluate →
Evaluate). The three evaluation legs are Objectives 3–5:

- **Objective 3 — acceptability of the generated picture books (expert validation).** Presentation
  quality + classroom suitability, judged by **purposively selected expert validators**: the
  **Dean/Professor of the Arts College**, one **Arts student/intern**, and one **Education student/intern**
  (Arts-sector → visual/artistic presentation; Education-sector → educational suitability). The instrument
  is a **written, open-ended interview form** (**Tool B**); responses are analysed by **content
  analysis** — pre-set categories from the five criteria (narrative coherence, story faithfulness, visual
  presentation, visual style consistency, classroom suitability), each response coded **positive /
  negative / suggestion** and tallied per criterion. This replaces the earlier feature-level scored rubric
  (CVI / Krippendorff's α), which is dropped (`research_instruments.md` §A).
- **Objective 4 — character-consistency classification performance of the fine-tuned judge.** The
  fine-tuned lightweight VLM (**Qwen2.5-VL-7B-Instruct**, QLoRA) predicts Same/Different Character on the
  character-disjoint held-out image pairs; its predictions are scored against the human reference labels
  using **precision, recall, and F1 (F1 primary)**. **Optionally**, the fine-tuned model may be reported
  alongside the **zero-shot base model** and the **existing prompted baseline** on the same held-out pairs.
  Full machinery in ADR-018 and `docs/specs/judge-finetune.md`.
- **Objective 5 — software quality (ISO/IEC 25010).** The questionnaire (**Tool C**), administered
  to the designated software-quality evaluators. Five applicable characteristics — Functional Suitability,
  Performance Efficiency, Usability, Reliability, Security — on a 5-point Likert scale; weighted mean + SD
  per characteristic, interpreted against the manuscript's Table 4 bands.

> **ADR-018's δ = 3 non-inferiority gate is a *deployment* gate and is unaffected** — it decides whether
> the fine-tuned judge replaces the prompted incumbent *in the product*, which is a build decision. The
> manuscript's Objective 4 (absolute classification performance) is a **reported research finding**; the
> optional base/prompted comparison is secondary to it.

**Reader comprehension (former RQ5) — dropped.** The single-arm naive-reader recall measure, its
validated recall protocol, its two-rater Cohen's κ, and the Tier-2 child cohort (Fun Toolkit: Smileyometer
+ Again-Again) are removed from the study. The manuscript measures fidelity through expert validation
(story faithfulness, narrative coherence) and does not run a reader-recall session. The in-app peer/gallery
comprehension surface stays cut (ADR-021).

**Former RQ1 / RQ4 — demoted to described pipeline behaviours.** Scene coverage against major plot points
(old RQ1) and graceful under-length handling (old RQ4) are no longer standalone measured questions with
their own instruments; they are described in methodology as properties of Scene Segmentation, consistent
with the manuscript, which sets no objective or data-collection activity for them.

**Corpus (manuscript-authoritative).** **15 stories collected** from Grade 5–6 learners → **10 primary
corpus + 5 backup**. Collected at Matina Aplaya Elementary School; development and evaluation at Holy Cross
of Davao College (HCDC), Davao City. The judge's image-pair dataset is derived from the pipeline's outputs
on this corpus. State as **donated child writing + researcher labels**; researcher-written fixtures are
development-only and never appear as evaluation stimuli.

**Ethics sequencing** is unchanged in shape (Stage 1 story donation unblocks the corpus and the judge's
training labels; the Stage-1 consent form must state that donated stories may be used to build and evaluate
an AI model), but Stage 2 no longer carries a Tier-2 comprehension study — it gates classroom system use
only.

**Consequences:**
- The study makes **no causal claim** and no pipeline ON/OFF comparison. Objective 4 restores a modest
  quantitative research finding (the judge's classification metrics) on top of the systems-and-instrument
  contribution; the optional base/prompted comparison is a bonus, not the spine.
- Dropping the reader-comprehension leg removes the `comprehension-instrument` and `tier2-fun-toolkit`
  build items (DECISION_BACKLOG) and their ROADMAP Phase-3 harness work.
- **Do not claim learning gains** — the manuscript's delimitations explicitly exclude creativity, literacy,
  writing-ability, and long-term learning outcomes, and the study uses no control/comparison group.

**Alternatives:**
- **Keep RQ6 purely descriptive / no comparison** (the 2026-07-22 position) — superseded: the manuscript
  makes classification performance a numbered objective and re-permits the optional comparison.
- **Keep the RQ5 reader-comprehension leg** — dropped: the manuscript has no reader respondents or
  reader-recall data collection; retaining it would put the docs ahead of the paper.
- **Keep the feature-level scored rubric for expert validation** — dropped: the manuscript specifies a
  written open-ended interview form analysed by content analysis, not a psychometric ordinal rubric.
- **Re-run the pipeline-ON-vs-OFF ablation** — remains dropped (corpus-gated, causal, outside the
  manuscript's scope).
