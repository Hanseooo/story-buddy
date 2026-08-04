# StoryBuddy: Research Direction and Goals

> **This document is derived, not authoritative.** It exists so an adviser or panel can understand the
> research without reading an ADR. The sources of truth are `docs/product/RESEARCH_PROTOCOL.md` (method),
> `docs/product/ADRs.md` (why), `docs/product/PRD_v2.md` (what), `docs/product/ROADMAP.md` (when), and
> above all the **capstone manuscript**, which is authoritative on scope, objectives, respondents, and
> instruments. **Where this document and those disagree, they win and this one is a bug.**

Target output format is **IMRaD / IEEE**. Section 9 maps each part below onto the manuscript.

---

## 1. The problem

There are two problems here. Only one of them is the research problem, and confusing them is the most
likely way this defense goes badly.

### 1.1 The motivating problem (the warrant — *not* what we measure)

A child writes a story. The teacher marks it. It goes in a folder. Nobody reads it. Prior work on writing
motivation is unusually consistent that an **authentic audience** and **actual publication** are among the
strongest levers on children's writing engagement.

But illustrating and publishing a class set of stories is not something a Grade 5–6 teacher can do. The
cost of publishing a child's story as an illustrated book is, in practice, *infinite*. Generative AI could
collapse that cost to minutes and a few pesos.

**This is the motivation. It is established by prior literature, and it is not a finding of this study.**

### 1.2 The research problem (what we actually solve and measure)

Generative models drift. The hero is a boy on page one and a different boy on page four. The dog changes
breed. The style shifts halfway through.

> **An inconsistent picture book does not transmit the child's story — it transmits noise.**

No single generative model produces a coherent multi-scene picture book that holds a **stylized, invented,
frequently non-human** character across pages. This regime is not merely hard; it is *under-measured*. No open
image model has *established* identity preservation for stylized, invented, non-human subjects — the
substrate's behaviour in this regime is unverified (recorded in the project's Architecture Decision Record 001
[ADR-001] available in the source repository, which evaluated candidates like Qwen-Image-Edit and FLUX.1). The
nearest evaluation benchmarks (e.g. DreamBench++) score *real, photographed* subjects, and **no dataset
provides human _pairwise_ identity judgments over stylized, invented, frequently non-human characters**
(`docs/specs/judge-finetune.md` §5.1 in the repository). That specific absence — human pairwise judgments over
invented non-human characters — is itself a contribution of this work.

### 1.3 Why these are the same problem

The artifact is only worth publishing if it actually **is** the child's story. A book whose hero changes
on page four has not published the child — it has published the model.

> **The technical problem and the educational benefit are the same claim viewed from opposite ends.**
> That is what makes this research rather than integration.

**Central research problem:**

> *Can an automated consistency-verification-and-correction pipeline transform child-written stories into
> coherent, visually consistent digital picture books — holding a stylized, invented, frequently non-human
> character across scenes — that expert validators judge acceptable in presentation quality and classroom
> suitability?*

**The pipeline itself is fully automated** — no person edits a scene, caption, or image between the child's
submitted story and the generated book. Human judgment enters only afterward: the teacher-gated review before
classroom sharing (§6), and the study's evaluation instruments (the expert validation panel, the human
reference labels for the Consistency Judge). This is what makes *AI-Powered* the accurate word for the title;
*AI-Assisted* would misdescribe generation as something a human helps produce.

---

## Objectives

Five objectives, in the manuscript's order — **Implement → Produce → Determine → Evaluate → Evaluate.**
This section restates the manuscript's objectives; the manuscript is authoritative.

1. **Implement** an orchestrated AI pipeline as the core processing framework of StoryBuddy.
2. **Produce** digital picture books from child-written stories through the implemented pipeline.
3. **Determine the acceptability** of the generated digital picture books — presentation quality and
   classroom suitability — through **expert validation**.
4. **Evaluate the character-consistency classification performance** of the fine-tuned lightweight
   vision-language model against human-established reference labels, using standard classification
   metrics: **precision, recall, and F1-score (F1 primary)**.
5. **Evaluate the software quality** of StoryBuddy against applicable **ISO/IEC 25010** quality
   characteristics.

The three evaluation legs are Objectives 3, 4, and 5 (ADR-008, revised 2026-07-25). Objectives 1–2 are the
built artifact. There is no reader-comprehension study and no pipeline ON/OFF ablation; the study makes no
causal or comparative claim about superiority over other methods.

---

## 2. How StoryBuddy solves it

The contribution is a **pipeline**, not a model. Each element exists because a single model cannot do the job.

1. **Story Memory** — a Pydantic contract carried across every stage, so late modules see what early ones
   decided. Character identity is *state*, not a hope pinned to a prompt string.
2. **Character Bible + canonical reference image** — each main character (≤ 2 canonical references) is drawn
   *once*, up front. Every scene is then generated **conditioned on that image**, not re-invented from text.
3. **Style presets** — three hand-authored prompt fragments. Style rides the canonical reference, so a preset
   is a different constant, not a different mechanism (as detailed in ADR-022 in the project repository, which specifies that style is anchored by the canonical character reference itself, allowing presets to be implemented as prompt fragments rather than requiring separate exemplar images).
4. **VLM-as-judge, reason-then-score** — a vision-language model compares each generated scene against the
   character's canonical reference. It must state *what differs* before it states *whether they match*;
   field order is load-bearing, because a model that scores first rationalizes afterwards (as outlined in ADR-004 in the repository, which notes that VLM judges can conflate category and scene similarity with identity, requiring a reason-then-score field ordering to force the reasoning to condition the verdict).
5. **Targeted regeneration** — the judge's structured `failure_reasons` (drawn from a closed taxonomy:
   `wrong_colour`, `wrong_species`, `wrong_clothing`, …) are fed back into exactly one corrected retry.
   This is what makes regeneration *purposeful* rather than a random re-roll. If the retry still fails, the
   higher-scoring image is kept — a child never sees a broken page (per ADR-010 in the repository, which establishes the policy of one targeted retry using the VLM's extracted failure reasons, followed by a best-of fallback to ensure a guaranteed shippable page).

**The consistency judge is a vision-language model.** The study **fine-tunes a lightweight open VLM —
`Qwen2.5-VL-7B-Instruct`, QLoRA — for the character-consistency classification task**, and evaluates its
performance against human reference labels (Objective 4, §3). A prompted `gemma-3-27b-it` serves as the
existing baseline the fine-tuned model is measured against. Whether the fine-tuned judge replaces the
prompted incumbent *in the shipped product* is a separate deployment decision (ADR-018); the pipeline is
unchanged either way. See `model_finetuning.md` and `docs/specs/judge-finetune.md`.

---

## 3. How we measure it

The study has **three evaluation legs** (ADR-008), one per evaluation objective:

- **Objective 3 — acceptability of the generated picture books (expert validation).** Purposively selected
  expert validators judge the generated books on presentation quality and classroom suitability.
- **Objective 4 — character-consistency classification performance of the fine-tuned judge.** The
  fine-tuned VLM's Same/Different-Character predictions are scored against human reference labels with
  precision, recall, and F1.
- **Objective 5 — software quality.** The ISO/IEC 25010 questionnaire, administered to designated
  software-quality evaluators.

There is no reader-comprehension leg and no pipeline ON/OFF ablation (both removed — ADR-008). Former RQ1
(scene coverage against major plot points) and former RQ4 (graceful handling of under-length stories without
inventing content) are **not standalone measured questions**; they are described in `methodology.md` as
properties of Scene Segmentation.

### 3.1 Objective 3 — expert validation (the method)

The generated books are evaluated **directly**, by expert validators purposively selected from the Arts and
Education colleges:

- the **Dean/Professor of the Arts College**,
- one **Arts student/intern**, and
- one **Education student/intern**.

The **Arts-sector validators** judge the visual and artistic presentation; the **Education-sector validator**
judges educational suitability and appropriateness. The instrument is a **written, open-ended interview form**
(Tool B). Responses are analysed by **content analysis**: pre-set categories are defined from the five
criteria — **narrative coherence, story faithfulness, visual presentation, visual style consistency, and
suitability for classroom use** — and each written response is coded **positive / negative / suggestion** and
tallied per criterion to summarise the level of acceptability. Software usability is *not* judged by this
panel; it is measured separately by the ISO/IEC 25010 questionnaire (Objective 5).

### 3.2 Objective 4 — Consistency Judge classification performance (the method)

The fine-tuned `Qwen2.5-VL-7B-Instruct` predicts, for each held-out image pair, whether the generated scene
shows the **Same Character** or a **Different Character** relative to the canonical reference. Predictions are
matched to the human reference labels by unique pair ID and scored with **precision, recall, and F1-score**;
**F1 is the primary summary metric** because it balances precision and recall. The held-out split is
**character-disjoint** — the same character identity never appears in more than one subset — so the model is
never evaluated on identities it trained on. **Optionally**, the fine-tuned model is reported alongside its
**zero-shot base** and the **existing prompted baseline** on the same held-out pairs, to characterise the
effect of fine-tuning; this comparison is secondary to the fine-tuned model's absolute agreement with human
labels. Full machinery in `docs/specs/judge-finetune.md` and ADR-018.

### 3.3 The non-circularity constraint

> **The expert-validation outcome is never scored using the judge.**

The judge drives regeneration inside the pipeline. Using that same judge as the acceptability outcome would be
circular — the system grading its own homework. The Objective-3 acceptability outcome is the **expert
validators' content-analysed judgments**; the ISO/IEC 25010 outcome (Objective 5) is a separate questionnaire.
The judge's own accuracy is the separate Objective-4 question, measured on a human-labeled, character-disjoint
held-out set it never trained on. This is the sharpest question a panel will ask, and the answer is fixed in
ADR-004 so it is never improvised.

---

## 4. Data gathering

### 4.1 Corpus

Test stories must be **real child writing**, not builder-authored clean prose — which would measure best-case
only. Grade 5–6, English with Taglish code-switching tolerated.

**Fifteen (15) original stories** are collected from qualified Grade 5–6 learners; after screening against the
inclusion/exclusion criteria, **ten (10) eligible stories comprise the primary corpus and five (5) are
retained as backup** if a primary story is later excluded (`methodology.md` §4.1). Learners participate by
**submitting stories only** — they do not validate the books or evaluate the software. Stories are anonymized
and assigned unique identifiers before processing.

**One corpus, two uses:** the picture books generated from these stories are the expert-validation stimuli
(Objective 3), and — once the pipeline has drawn them and researchers have labelled the character image pairs
— the Consistency Judge's training and evaluation data (Objective 4). The judge's image-pair dataset is
derived from the pipeline's own outputs on this corpus; researcher-written stories appear only as
training-split augmentation, never as evaluation stimuli or in the judge's held-out test split (ADR-008).

Development and debugging use **researcher-written fixture stories**. These are not the corpus, carry no
ethics load, and are never used as stimuli or as evidence.

### 4.2 Respondents

Three groups, treated separately because they address different aspects of the study:

- **Grade 5–6 learners** — provide the child-written stories (15 → 10 primary + 5 backup). Story submission
  only; no evaluation role.
- **Expert validators** — the Dean/Professor of the Arts College + one Arts student/intern + one Education
  student/intern, purposively selected (§3.1). They validate the generated picture books.
- **Software-quality evaluators** — a separate designated group who complete the ISO/IEC 25010 questionnaire
  (§3, Objective 5).

### 4.3 Ethics — two stages, because the original design had a hidden deadlock

The corpus is real child writing. A single ethics submission would bundle low-risk story donation with the
heavier review of children using the system. Splitting the submission is the fix.

- **Stage 1 — story donation.** Children write stories; they never touch the system. Anonymized text, nothing
  about the child. Narrow, low-risk, comparatively fast. *Unblocks the corpus, the expert-validation stimuli,
  and the judge's training/evaluation labels.*
- **Stage 2 — system use.** Children use StoryBuddy in a teacher-guided, classroom-scoped setting. Interactive,
  child-authored content. Materially heavier review, and not on the critical path for the three evaluation
  legs.

> **The Stage-1 consent form must state that donated stories may be used to build and evaluate an AI model.**
> The donated story becomes illustrations, researchers label those illustrations, and those labels become
> weights in a model we ship. Anonymising the child's *name* does not change that. It costs one sentence, and
> **there is no retroactive fix** — collect first and the only lawful options are to re-consent every child
> or delete the data.

Both stages require guardian informed consent **and** age-appropriate child assent, in compliance with the
**Data Privacy Act of 2012 (Republic Act No. 10173)**. Stories are collected at **Matina Aplaya Elementary
School**; development and evaluation are conducted at **Holy Cross of Davao College (HCDC), Davao City**,
subject to institutional and ethics clearances.

### 4.4 Pre-registration

**The analysis plan — objectives, metrics, success criteria — is written and timestamped before anything is
run.** For Objective 4 this fixes the reporting before the held-out set is read once: the judge's precision,
recall, and F1 against human labels are reported whatever they turn out to be, and the deployment gate that
decides whether the fine-tuned judge replaces the prompted incumbent is declared in advance rather than chosen
after seeing the numbers. The same discipline governs the expert validation: the criteria and the
content-analysis coding frame are fixed before data, so a weak result is a finding, not a fudge.

Almost no capstone does this. It is the cheapest defensive move available.

---

## 5. Who benefits, and what we refuse to claim

**The benefit to a Grade 5–6 classroom is a design property, and it is defensible on architecture alone.**
An open-weight, self-hostable pipeline carries **no per-seat vendor cost** — the difference between a tool a
well-funded private school buys and one a provincial public school can run. That is the SDG-4 (Quality
Education) hook. It is a property of the system, not a hope about its effects.

Within the study, the demonstrated benefit is **acceptability of the generated books**: expert validators
judge whether the outputs are coherent, faithful, and suitable for classroom use. A book experts validate as
faithful is the authentic-audience artifact the motivating literature calls for.

**What this study does not claim, and why:**

| We do not claim | Why not |
|---|---|
| **Learning gains** in children's writing/literacy | No control or comparison group, no pre/post design, no longitudinal window. Prior literature is the **warrant** for why fidelity matters; it is not our finding. The manuscript's delimitations exclude creativity, literacy, writing-ability, and long-term learning outcomes. |
| **Superiority over other methods** | No control/comparison group; the study makes no causal or comparative claim of superiority. |
| **Privacy preservation** | The child's text transits a hosted provider; the study does not claim complete on-device privacy (Future Work). |
| **Perfect preservation** | Story content, character appearance, and visual style are not guaranteed to be perfectly preserved in every generated book. |
| **Watermark provenance** | No open equivalent to SynthID-Image exists; C2PA is Future Work. |

---

## 6. Scope and boundaries

**Grade 5–6 (ages 10–12), Philippines, English with Taglish tolerated.** Each boundary is derived from the
study's needs, not chosen for convenience:

- They **write independently** → the story is unambiguously the child's. Scaffold a Grade 2 student and it is
  unclear whose story was illustrated.
- **English is the medium of instruction** from Grade 4 → one language, one moderation regime, one TTS voice.
- They are **pre-adolescent** → appropriate for a teacher-guided classroom setting.

The corpus is one grade band in one country. **A tight population is a delimitation, not an apology.**

**In scope (the pipeline's ten logical modules):** Input Moderation · Story Analyzer · Scene Segmentation
(up to 10–15 scenes, target ≥ 3 distinct major plot points where the arc supports it — never padded, and
never-invent overrides the floor) · Story Memory Manager · Character Bible + canonical reference (≤ 2
canonical references) · Style Preset (three presets) · Prompt Optimizer · AI Scene Generation
(Qwen-Image-Edit) · Consistency Judge & Targeted Regeneration (prompted judge in the product; fine-tuned
`Qwen2.5-VL-7B` evaluated in Objective 4) · Picture Book Composition (slide composer with expressive TTS
narration via Chatterbox, PDF export). Moderation stack (input text, output images, Filipino PII redaction)
and teacher-gated, display-only classroom sharing wrap the pipeline.

**Permanently excluded:** public sharing. All sharing is classroom-scoped and teacher-gated.

**Deferred:** multi-child collaboration · kid-uploaded reference images · languages beyond English/Taglish ·
on-device generation · more than three art styles.

**Open-weight mandate.** No proprietary vendor models. This is what makes the equity claim a design property
rather than a hope, and it is why the system is self-hostable and replicable. StoryBuddy nonetheless remains
dependent on compute, network connectivity, and some external hosted services — it does not claim complete
on-device operation.

---

## 7. Intended contributions

1. **A multi-module consistency pipeline, evaluated on its outputs** — Story Memory, canonical reference,
   and judge-driven targeted regeneration, whose generated books are validated by an expert panel and
   against ISO/IEC 25010 (Objectives 3 and 5), not asserted from a bare API call. This is the answer to
   *"isn't this just an API wrapper?"*: the contribution is the architecture and the demonstration that it
   produces outputs experts validate as acceptable.
2. **A fine-tuned open VLM consistency judge, evaluated as a classifier** — its precision, recall, and F1
   against human reference labels on a character-disjoint held-out set (Objective 4), optionally alongside
   its zero-shot base and the prompted baseline.
3. **A characterization of an unmeasured regime** — identity retention for stylized, invented, non-human
   characters, where existing benchmarks (e.g. DreamBench++) evaluate real photographic subjects rather than
   the stylized, invented, non-human regime this product lives in, and none provides human pairwise identity
   judgments over it (ADR-001 and `docs/specs/judge-finetune.md` §5.1 in the repository).
4. **A human-labeled character-consistency image-pair dataset** over stylized, invented, frequently non-human
   characters — the specific absence identified in §1.2.
5. **Equity by construction** — an open-weight, self-hostable stack with no per-seat licensing cost.

---

## 8. Trajectory

Riskiest assumptions first. Build track and research track run in parallel and meet at Phase 2.5 and Phase 3.

| Phase | What | Status |
|---|---|---|
| 0 | Scaffolding & walking skeleton | ✅ done |
| **0.5** | **Open-weight spike — can the image model hold a non-human character?** | **⚠️ Run 2026-07-29. Split result: absolute gate met (80%), separation gate missed (+25 vs ≥30). Probe 3 passed; probes 2 and 4 outstanding.** |
| 1 | Core pipeline + prompted consistency judge | ✅ **complete (2026-08-02)** — all ten specs built; opened on a stated limitation, not a clean pass |
| 2 | Moderation, classroom auth, sharing, narration, export | **in progress (2026-08-04)** — moderation stack, input-gate hardening and the kid-facing flow built; auth/RLS, teacher review, narration, export, data deletion open. Release still gated on probe 4 |
| 2.5 | Judge fine-tuning + classification evaluation (Objective 4) | blocked on Ethics Stage 1 → corpus → a Phase 1 run |
| 3 | Expert validation (Objective 3) + ISO/IEC 25010 (Objective 5) | blocked on corpus |

**Phase 0.5 is a kill criterion, and it has now run (2026-07-29).** It did not kill the project and it did
not clear it either. Reference conditioning held the invented non-human character (Quill) on **80%** of
items — the absolute gate — but beat the unconditioned control by only **+25 points** against a
pre-committed **≥30**. Escalating one rung down ADR-001's fallback ladder reproduced the same split, so
the escalation was declined and Qwen-Image-Edit stayed primary.

The interesting sentence turned out to be the opposite of the one anticipated. The *invented* character
separated strongly (+50, ON 80% vs OFF 30%); the *easy* character, a fox cub, separated not at all (80%
vs 80%, three runs running) — the model already knows what a fox looks like, so the reference adds
nothing measurable and drags the pooled separation below its threshold. Reference conditioning appears to
buy the most exactly where the product needs it most, which is the reverse of the risk this probe was
built to expose. That is a claim from a single-rater, non-blind build gate and is **not** reportable as a
finding without a blind re-score (`PHASE_05_RESULTS.md`).

Downstream documents stay contingent — but on the *separation* result and the limitation it forces into
the writeup, no longer on whether the substrate works at all.

**Ethics Stage 1 is the long pole and cannot be compressed by coding faster.** The fine-tune sits four hops
downstream of an ethics form: *Stage 1 → stories → images → labels → fine-tune.* Everything after `images`
is a weekend. Everything before it is months.

---

## 9. Mapping onto the IMRaD manuscript

| Manuscript section | Draw from |
|---|---|
| **Introduction** | §1.1 (motivation, cited to prior work) → §1.2 (the gap) → §1.3 (the research problem) → §7 (contributions). Lead with the child and the folder; land on identity drift. |
| **Related Work** | Situate against the crowded character-consistency field (ConsiStory, StoryDiffusion, The Chosen One, DreamBench++), then §1.2's true gap: existing benchmarks are photographic or method-preference studies, and **none provides human pairwise identity judgments over stylized, invented, non-human characters** (`docs/specs/judge-finetune.md` §5.1 in the repository, incl. the rejected-alternatives table). Cite only arXiv IDs you have re-verified (see `design_decisions_and_risks.md`, R6). |
| **Methods** | **Drafted in full: `docs/capstone/methodology.md`** — development methodology (quantitative-developmental; Boehm's Spiral Model), system under test, data collection, datasets, training and validation, instruments, analysis plan, ethics, threats to validity. |
| **Results** | Phase 0.5 probe results · expert-validation content-analysis summary (Objective 3) · Consistency-Judge precision/recall/F1 on the held-out set (Objective 4) · ISO/IEC 25010 weighted means + SD (Objective 5) |
| **Discussion** | §5 — what the numbers support, and the claims we refuse to make. Phase 0.5's non-human boundary belongs here if the substrate fails. |
| **Limitations** | §5's table, §6's delimitation, and the fact that the corpus is one grade band in one country. |

**Write the Methods section before the Results exist.** It is already almost entirely determined by
`RESEARCH_PROTOCOL.md`, and writing it early is what makes the pre-registration in §4.4 real rather than
decorative.

→ **Drafted: `docs/capstone/methodology.md`.** Its analysis plan is the pre-registration and needs adviser
sign-off **before the first data point is collected.** Its ISO/IEC 25010 questionnaire section needs the
evaluator profile confirmed with your adviser.
