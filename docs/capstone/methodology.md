# StoryBuddy — Research and Development Methodology

**Reading note.** This document is written to be read on its own, without access to the project's source
repository. Where a claim is grounded in an internal engineering document, that document is named explicitly
and can be found at the stated path in the StoryBuddy source repository. Those files are the authoritative
records; this document summarizes them for a reader who has not seen them. The **capstone manuscript** is
authoritative on scope, objectives, respondents, and instruments; this document conforms to it.

| If you want… | Read, in the repository |
|---|---|
| Why a technical decision was made | `docs/product/ADRs.md` (Architecture Decision Records) |
| The full research protocol | `docs/product/RESEARCH_PROTOCOL.md` |
| The fine-tuning recipe in operational detail | `docs/specs/judge-finetune.md` |
| Phase order, gates, and dependencies | `docs/product/ROADMAP.md` |
| Probe results and their pre-declared pass criteria | `docs/product/PHASE_05_RESULTS.md` |

**Where this document and those disagree, they are correct and this one is a defect.**

> **This methodology is written before any result exists.** That is deliberate. A methodology written after
> seeing results is a narrative; written before, it is a **pre-registration**. Sections marked ⚠️ require
> adviser sign-off **before the first data point is collected** — after that, changing them is moving a
> goalpost.

The study employs a **quantitative-developmental** research design: a developmental component that builds and
iteratively refines the ten-module pipeline, and an evaluation component that measures the system and its
outputs through three procedures — expert validation of the generated picture books (Objective 3), the
Consistency Judge's classification performance against human labels (Objective 4), and ISO/IEC 25010 software
quality (Objective 5).

---

## 1. Development methodology (SDLC)

### 1.1 What model this is

**Boehm's Spiral Model** — a risk-driven, iterative SDLC with stage-gated phases.

It is not Waterfall: requirements were not frozen before construction, phases overlap, and a phase can
change the specification of a later one. It is not Scrum: there are no sprints, no backlog grooming, no
story points, and the build track is one developer.

Three properties define it:

**Riskiest assumptions first.** Before any dependent code was written, the project's dominant technical
unknown — *can an open image model hold a stylized, invented, non-human character across scenes?* — was
isolated into a throwaway prototype (Phase 0.5) costing roughly one US dollar, carrying a **pre-declared
kill criterion**. Nothing in that prototype ships. This is risk resolution in Boehm's sense: identify the
dominant risk, build the cheapest artifact that resolves it, and only then commit resources.

**Walking skeleton, then vertical slices.** Phase 0 pushed one hardcoded story end-to-end through real
infrastructure — real queue, real worker, real storage, real database — before any module was made
intelligent. The place a schedule dies is integration, not algorithms. Every subsequent phase is a vertical
slice through the whole stack rather than a horizontal layer.

**Exit criteria, not calendar.** Each phase advances on evidence, not on a date. Gates are recorded in
`docs/product/ROADMAP.md` and are pass/fail.

### 1.2 Spiral Model quadrant mapping

While structured chronologically as phases, the development process represents iteration loops mapping
directly to the four core quadrants of Boehm's Spiral Model:

1. **Determine objectives:** Defining goals for the current iteration (e.g., scaffolding, core pipeline, evaluation).
2. **Identify & resolve risks:** The defining feature of this project's SDLC. Identifying the biggest unknown (e.g., Phase 0.5 for substrate risk, Phase 2.5 for judge accuracy) and building a targeted spike to resolve it *before* full implementation.
3. **Develop & verify:** Building the vertical slice (Phase 0 walking skeleton, Phase 1 pipeline) and verifying against pre-declared criteria.
4. **Plan next iteration:** Using the evidence from the exit gates to adjust the subsequent phase's architecture.

### 1.3 The phases and their gates

| Phase | Iteration loop / Spiral stage | Purpose | Gate to leave it |
|---|---|---|---|
| **0** & **0.5** | **Loop 1: Risk resolution** | Scaffolding and open-weight spike to resolve the substrate risk cheaply | A real slideshow renders. Reference conditioning retains identity on ≥ 80% of items **and** exceeds unconditioned by ≥ 30 points. ✅ Phase 0 done |
| **1** | **Loop 2: Core pipeline** | The consistency loop is real, on clean stories | A story produces a consistent book; a case exists where the judge caught a drifted image and the retry fixed it |
| **2** & **2.5** | **Loop 3: Integration & tuning** | Safe for a real child, survives messy input. An honestly evaluated specialized judge | The Filipino/Taglish moderation probe passes in **both** directions. A results table exists and the held-out set was read exactly once |
| **3** | **Loop 4: Evaluation** | Expert validation (Obj 3), judge classification (Obj 4), and ISO/IEC 25010 software quality (Obj 5) | Expert-validation responses collected and content-analysed; the judge held-out classification table read exactly once; ISO/IEC 25010 questionnaire administered |

Phase 0.5's kill criterion is the sharpest instance of the method. **It ran on 2026-07-29 and split its
two gates**: reference conditioning retained identity on **80%** of pipeline-ON items (absolute gate met)
but exceeded pipeline-OFF by only **+25 points** against a pre-committed ≥30 (separation gate missed).
Per ADR-001 the project escalated one rung, re-ran, and got the same split on the fallback — so the
escalation was declined and Qwen-Image-Edit remains primary, with the missed gate carried as a stated
limitation rather than reported as a pass. The method's value showed exactly where it was supposed to:
the substrate question was answered for about **$12**, in month one, and the answer was neither the
clean pass the plan hoped for nor the kill the plan feared. Claims downstream stay contingent on the
separation result, not on whether the probe ran.

### 1.4 Why the build track is iterative and the research track is not

The two tracks run in parallel and meet twice: at Phase 2.5 (the fine-tune consumes Phase 1's output) and at
Phase 3 (the study needs a working system).

**The software process is iterative.** Code is cheap to revise because it can be tested, and a design flaw
found in week six costs a rewrite.

**The research process is plan-driven and pre-registered.** The metrics, units of analysis, and success
criteria in §7 are fixed before the first data point. Adapting an analysis after seeing the data is not
agility — it is p-hacking. Data is collected once, and children cannot be re-consented.

If asked whether pre-registration is "just Waterfall": pre-registration constrains **inference**, not
**implementation**. The image generator can be rewritten on Tuesday. The analysis plan cannot.

### 1.5 Engineering practices that carry research weight

- **Contract-first.** Every pipeline stage reads and writes a single versioned Pydantic schema (*Story Memory*).
  Language models are constrained to strict JSON-schema structured output, so a malformed response fails at the
  boundary rather than propagating.
- **Deterministic orchestration.** The pipeline is a fixed state machine (LangGraph). Conditional edges exist
  only at moderation pass/fail and consistency pass/fail. There is **no autonomous agent routing**, so the
  execution path is a function of the input, and worst-case cost is bounded. This underwrites
  **reproducibility**: the same story and seed produce the same book, so every generated artifact reported in
  the expert validation and every image-pair fed to the judge evaluation (Objective 4) is regenerable, and
  per-run traces (verdicts, regen counts, latency, cost) are attributable to a fixed path rather than to
  nondeterministic routing.
- **The testing bright line.** Deterministic tests mock every model call; fuzzy quality — "is the character
  consistent?" — is measured only in an offline evaluation harness against real models. The two never mix. A
  generated-content assertion in a deterministic suite is a flaky test, not a measurement. *Continuous
  integration is planned, not yet standing:* the repository has no CI configuration at the time of writing, so
  the deterministic suite is run locally and the "must stay green" rule is an intended practice rather than an
  enforced one.
- **Frozen decisions.** Architectural decisions are recorded in `docs/product/ADRs.md` and are not revised
  silently; changing one requires appending a new record stating context, decision, consequences, and
  alternatives.

---

## 2. System under test

A deterministic pipeline of **ten logical modules**, in order:

| # | Module | Function |
|---|---|---|
| 1 | Input Moderation | Text safety gate, then personally-identifiable-information redaction |
| 2 | Story Analyzer | Entity and coreference extraction into the Story Memory contract |
| 3 | Scene Segmentation | Selects **up to** 10–15 scenes; scene count tracks the story's distinct major plot points (target ≥ 3 where the arc supports it); never padded to reach a count and never invents content — never-invent overrides the floor |
| 4 | Story Memory Manager | Maintains the versioned Pydantic *Story Memory* contract that carries state across every stage |
| 5 | Character Bible | ≤ 2 canonical characters, each rendered **once** as a reference image |
| 6 | Style Preset | One of three hand-authored prompt fragments, frozen for the storybook |
| 7 | Prompt Optimizer | Scene + character bible + style preset + story memory → structured prompt |
| 8 | AI Scene Generation | Reference-conditioned image edit — the pipeline's single generation mode |
| 9 | Consistency Judge & Targeted Regeneration | Vision-language judge (emits `differences_observed` **before** `same_character`); one targeted, prompt-corrected retry; best-of fallback; capped |
| 10 | Picture Book Composition | Slide composer with expressive TTS narration; PDF export |

> **Logical vs. implemented.** These are the manuscript's ten logical modules. In the implementation graph
> (`docs/MASTER_SPEC.md` §2, ADR-003) some are realized as cross-cutting concerns rather than discrete graph
> nodes — the **Story Memory Manager** is the shared Pydantic contract every node reads and writes, and
> **Style Preset** and **Prompt Optimizer** are node *inputs* rather than standalone nodes — but the logical
> decomposition maps one-to-one onto the deterministic pipeline. The architecture is unchanged.

**Models.** Text analysis: `qwen/qwen3-32b`. Image generation: `Qwen-Image-Edit` (Apache-2.0). Consistency
judge: prompted `gemma-3-27b-it`. Narration: `Chatterbox` (MIT), served via hosted inference, with
`Kokoro-82M` retained as a CPU fallback (ADR-020, revised). All open-weight. No proprietary vendor model
appears anywhere in the pipeline — a constraint that makes the system self-hostable and the equity claim a
property of the design rather than an aspiration. Model identifiers, versions, and provider routing are
pinned and reported.

**Reason-then-score.** The judge's structured output declares *what differs* before *whether the characters
match*. Field order is load-bearing: a model that emits a verdict first will rationalize toward it.
`failure_reasons` is drawn from a **closed taxonomy** — `wrong_colour`, `wrong_species`, `wrong_body_feature`,
`wrong_clothing`, `wrong_style`, `different_face`, `character_absent` — fixed before any labelling begins.
Extending the taxonomy after annotation starts invalidates every label already collected.

**The judge in the shipped pipeline is a *prompted* model.** The study **fine-tunes a lightweight open VLM —
`Qwen2.5-VL-7B-Instruct`, QLoRA — for the character-consistency classification task**, and evaluates its
classification performance against human reference labels (Objective 4, §5, §7.2). Whether the fine-tuned
judge replaces the prompted incumbent *in the shipped product* is a separate deployment decision (ADR-018);
the pipeline's architecture is identical either way.

---

## 3. Data collection

### 3.1 What is collected, from whom

| Data | Source | Used for |
|---|---|---|
| Story text | Donated Grade 5–6 child writing (15 collected → 10 primary + 5 backup) | Generation input; the source of every generated image; expert-validation stimuli |
| Generated picture books | Pipeline output over the primary corpus | Expert validation (Objective 3) |
| Expert-validation responses | Expert validators (Dean/Professor of the Arts College + Arts student/intern + Education student/intern) | Objective 3 — acceptability |
| Image-pair identity labels | Two trained annotators | Objective 4 — the judge's training and evaluation data |
| System-evaluation questionnaire | Designated software-quality evaluators | Objective 5 — software quality (§6.3) |

### 3.2 Ethics: two stages, and the deadlock they resolve

The corpus is real child writing. A single ethics submission would bundle low-risk story donation with the
materially heavier review of children using the interactive system. Splitting the submission removes that
dependency.

**Stage 1 — story donation.** Children write stories. They never touch the system. Anonymized text is
collected; nothing about the child is. Narrow, low-risk, comparatively fast. This stage unblocks the corpus,
the expert-validation stimuli, and the judge's training and evaluation labels.

**Stage 2 — system use.** Children use StoryBuddy in a teacher-guided, classroom-scoped setting. Interactive,
child-authored content; a materially heavier review. It is not on the critical path for the three evaluation
legs.

> **The Stage-1 consent form states that donated stories may be used to build and evaluate an AI model.**
> The donated story is turned into illustrations, researchers label those illustrations, and those labels
> become weights in a model. Anonymising the child's *name* does not change that the child's creative content
> flows into the model. It costs one sentence, and **there is no retroactive fix**: stories collected without
> this clause must be re-consented or deleted.

Both stages require **guardian informed consent and age-appropriate child assent**, in compliance with the
**Data Privacy Act of 2012 (Republic Act No. 10173)** and the university ethics board. Stories are collected
at **Matina Aplaya Elementary School**; system development and evaluation are conducted at **Holy Cross of
Davao College (HCDC), Davao City**, subject to institutional and ethics clearances. Draft consent and assent
language is held in `docs/product/RESEARCH_PROTOCOL.md` §9.

**Ethics Stage 1 is the project's longest dependency and cannot be compressed by coding faster.** The
fine-tuned judge sits four hops downstream of an ethics form: *clearance → stories → images → labels →
fine-tune.* Everything after `images` takes a weekend. Everything before it takes months.

### 3.3 Respondents

Three groups, treated separately because they address different aspects of the study:

- **Grade 5–6 learners** provide the child-written stories — fifteen collected, ten forming the primary
  corpus and five retained as backup. Their participation is limited to the voluntary submission of original
  stories; they do not validate the books or evaluate the software. Stories are anonymized and assigned unique
  identifiers.
- **Expert validators**, purposively selected from the Arts and Education colleges: the **Dean/Professor of
  the Arts College**, one **Arts student/intern**, and one **Education student/intern**. The Arts-sector
  validators judge the visual and artistic presentation; the Education-sector validator judges educational
  suitability. They complete the written expert-validation instrument (§6.1).
- **Software-quality evaluators** — a separate designated group who complete the ISO/IEC 25010 questionnaire
  (§6.3). Their responses are treated separately from the expert validation because the two activities address
  different objects: the generated picture-book outputs versus the StoryBuddy software system.

### 3.4 Procedure

1. **Phase 0.5 substrate probe** — a blind comparison of **reference-conditioned vs. unconditioned**
   generation over two probe characters (one real animal, one invented non-human), scored by the research
   team as the substrate kill-criterion. *(This is a technical substrate gate, not a research arm — the
   pipeline-ON-vs-OFF study ablation is dropped, ADR-008.)*
2. **Corpus collection** under Ethics Stage 1: fifteen original stories from Grade 5–6 learners at Matina
   Aplaya Elementary School, screened against the inclusion/exclusion criteria to ten primary + five backup.
3. **Generation.** Each primary story processed **once** through the full pipeline. Traces record per-scene
   verdicts, regeneration counts, latency, and cost. Seeds are fixed and reported for reproducibility.
4. **Expert-validation sessions.** The generated picture books are presented to the expert validators, who
   complete the written open-ended interview form against the five criteria (§6.1).
5. **Image-pair labelling**, then fine-tuning and classification evaluation of the Consistency Judge (§5).
6. **ISO/IEC 25010 questionnaire** administered to the designated software-quality evaluators (§6.3).

**Reproducibility of stimuli.** Generated items are written to opaque filenames with provenance metadata
stripped, so the mapping from a book back to its source story is recorded separately and excluded from version
control; every reported artifact is regenerable from a fixed seed (§10).

---

## 4. Datasets

### 4.1 The story corpus

Stories are **donated child writing**, not researcher-authored prose. Builder-authored clean text would
measure best-case behavior only, and the system's handling of under-length, messy child writing would be
unobservable by construction.

- **Population:** Grade 5–6 (ages 10–12), Philippines. English, with Taglish code-switching tolerated.
- **Size:** **fifteen (15) original stories collected**; after screening against the inclusion/exclusion
  criteria, **ten (10) eligible stories comprise the primary corpus and five (5) are retained as backup** and
  substituted if a primary story is later excluded.
- **Provenance:** documented. Reviewers will ask.

**One corpus, two uses:** the picture books generated from these stories are the expert-validation stimuli
(Objective 3); and — once the pipeline has illustrated them and researchers have labelled the character image
pairs — the judge's training and evaluation data (Objective 4). Corpus = **donated child writing + researcher
labels**; researcher-written stories appear only as judge-training-split augmentation (§4.3), never as
evaluation stimuli or in the judge's validation/held-out-test splits (ADR-008).

> **Open reconciliation item (flag for adviser).** With the corpus fixed at ten primary stories, the number of
> **distinct characters** available for the judge's character-disjoint split (§4.3) is far smaller than the
> ~50-character split the earlier ~50-story plan assumed. The judge's split sizes are therefore **planning
> targets to be finalized against the actual character yield of the ten primary stories** (see
> `docs/specs/judge-finetune.md`), and Objective-4 statistical power — governed by the held-out **character**
> count — must be reported honestly against that yield. Training-split augmentation with researcher-written
> stories (train only) partially offsets a small character count but does not enlarge the held-out set.

Software development and debugging use **researcher-written fixture stories**. These carry no ethics load,
are never used as stimuli, and are never reported as evidence.

### 4.2 The judge dataset: there is nothing to download

**No public dataset provides human pairwise identity judgments over stylized, invented, non-human characters.**
Candidates were surveyed and rejected on the record (full table in `docs/specs/judge-finetune.md` §5.1):

| Candidate | Fatal problem |
|---|---|
| **DreamBench++** | 150 **photographic** subjects. Training a judge on photos of real corgis and deploying it on a cartoon dragon aims a domain shift straight at the weakness being fixed. Used as a **held-out transfer test only** — evaluated, never trained on, never redistributed. |
| **PororoSV / FlintstonesSV** | Nine and seven characters in total. With so few, a character-disjoint split is impossible, so the model learns *"recognise Pororo,"* not *"compare two images."* |
| **StorySalon** | No identity ratings, and copyright-encumbered (frames scraped from video and e-books). |

**That absence is itself a contribution of this work.** The dataset is therefore *manufactured* from the
pipeline's own output over the donated corpus: each primary story yields canonical character references and
generated scene images, which are paired — a canonical reference against a scene containing that character —
and augmented with **constructed hard negatives** (one character's reference against a scene generated from a
different character's reference). Each pair is human-labelled Same/Different Character. Exact image, pair, and
cost totals are **planning targets** in `docs/specs/judge-finetune.md`, to be finalized against the character
yield of the ten primary stories; **Objective-4 statistical power is set by the number of held-out
characters** (§4.3) — the effect-size bootstrap clusters by character — not by the raw pair total.

### 4.3 Splits, and the three ways this dataset can lie to you

The annotated image-pair dataset is divided into **train / validation / held-out test** subsets **at the
character-identity level** — the same character identity never appears in more than one subset. Target split
sizes are planning figures (`docs/specs/judge-finetune.md` §5.5) to be finalized against the corpus's actual
character yield (§4.1).

**Character leakage.** Splits are by **character, never by pair**. Every image derived from a given canonical
reference belongs to exactly one split. If one character appears in both train and test, agreement inflates
and nothing in the metrics reveals it. This is enforced in code, with a dedicated leakage test in the
deterministic suite (run locally today; continuous integration is planned, §1.5).

**Shortcut learning.** Hard negatives are free and clean: character A's reference against a scene generated
from character B's reference. Positives are **not** free. Treating *"the same reference was used"* as a
positive label looks free but is noisy in exactly the direction that matters — because generation *sometimes
drifts*, which is the entire reason the judge exists. A model trained on auto-labelled positives learns to
detect ***"was a reference image used?"*** rather than ***"is this the same character?"***. It will score
brilliantly on validation and be useless in the loop. **Every positive is human-confirmed.** Accordingly, the
dataset is **not** classified merely by whether the same reference image was used during generation; the
identity shown in the generated image is assessed against the established character-consistency criteria.

**Class imbalance.** The minority class (`different_character`) is the one the control loop acts on, and a
missed failure ships a broken page to a child. The training set is therefore balanced using constructed
negatives — but those negatives are placed in **train only**, so validation and test preserve the true
deployment distribution.

---

## 5. Training and validation

Two distinct kinds of training happen in this project, and both must be documented: the model is trained, and
so are the human annotators.

### 5.1 Model training ⚠️

- **Base model:** `Qwen2.5-VL-7B-Instruct` (Apache-2.0, native multi-image support).
- **Method:** **QLoRA** — 4-bit quantized base weights with a trainable low-rank adapter. Fits on a single
  24 GB consumer GPU (RTX 4090, rented), 1–2 hours, roughly US$5–15 per run. The artifact is a **LoRA adapter
  of a few tens of megabytes** over public base weights, not a model.
- **Hyperparameters:** LoRA rank 16, alpha 32, 4-bit quantization, `qwen2_vl` chat template, images capped at
  262,144 pixels. Fixed seed. Best checkpoint selected on validation loss.
- **Robustness:** every reported result is over **≥ 3 training seeds.**

**What each split is for, and the discipline that makes the result meaningful:**

- **Train** fits the adapter.
- **Validation** is where *all* iteration happens — hyperparameters, prompt format, early stopping, checkpoint
  selection. Every decision that could be influenced by looking at data is made here.
- **The held-out test set is read exactly once.** Touching it twice makes it a validation set, the correction
  is not knowable after the fact, and the primary endpoint is void.

**No fine-tuning is performed on the image generator or the text model.** Only the consistency judge is
trained, and it is **excluded from the child-safety path by design** — safety is a gate with no fallback, and
it stays on a prompted, unmodified model. Full recipe: `docs/specs/judge-finetune.md`.

### 5.2 Human annotator training ⚠️

Annotators are not instruments until they are calibrated. Every human measurement in this study follows the
same protocol:

1. **A written annotation guide** with worked examples and explicit edge cases, produced before any data is
   scored. For the image-pair task, the guide fixes the closed failure-reason taxonomy (§2).
2. **Practice items drawn from outside the corpus** — for the image task, pairs from the Phase 0.5 probe.
   Never from material that will be scored for real.
3. **Calibration.** Agreement is computed on the practice set before scoring of real data begins; if the floor
   is not met, the guide is revised and the annotators re-calibrate. **Revising the guide is legitimate;
   revising the data is not.**
4. **Adjudication.** Disagreements on real data are resolved through the established criteria procedure, and
   the adjudication rate is reported.
5. **Drift check.** Agreement is recomputed midway through scoring. Annotators relax over long sessions.

The final inter-annotator reliability on the real image-pair data is **reported alongside the judge results.**
A measure without its agreement figure is not a measure.

---

## 6. Instruments, and how they are evaluated

Three evaluation instruments appear in this study, one per evaluation objective. Section 6.4 states plainly
what each can and cannot do.

### 6.1 The expert-validation instrument (Objective 3)

The generated picture books are presented to the expert validators (§3.3) using a **written, open-ended
interview form**. The validators examine the outputs against five established criteria:

- **narrative coherence**,
- **story faithfulness**,
- **visual presentation**,
- **visual style consistency**, and
- **suitability for classroom use**.

**How it is evaluated — content analysis.** Before analysis, pre-set categories are defined from the five
criteria. Each validator's written response is reviewed and coded into **positive feedback**, **negative
feedback**, or **suggestion for improvement**, then tallied per criterion to produce a structured summary of
expert judgments. This determines the level of acceptability and classroom suitability of the generated books
as perceived by the validators, from the recurring patterns across their written responses. This instrument
is **qualitative** — it replaces the earlier ordinal feature-rubric (dropped, ADR-008). The full instrument
and its criteria wording are finalized in `docs/capstone/research_instruments.md`.

### 6.2 The Consistency-Judge classification evaluation (Objective 4)

The fine-tuned judge's evaluation is a **classification** measurement, not a questionnaire: the human
image-pair labels (§4, §5.2) are the ground truth, and the model's predictions are scored against them with
precision, recall, and F1 (§7.2). The instrument here *is* the labelled held-out set and the annotation guide
that produced it; its validity rests on the calibration and reliability discipline in §5.2.

### 6.3 The system-evaluation questionnaire (Objective 5, ISO/IEC 25010) ⚠️

**Confirm the evaluator profile with your adviser before administering this.**

The software artifact is evaluated with a structured questionnaire administered to the designated
software-quality evaluators, following **ISO/IEC 25010** software product quality characteristics. Five
applicable characteristics are assessed on a **5-point Likert scale (1 = Poor to 5 = Excellent)**:

| Characteristic | What is asked about |
|---|---|
| Functional Suitability | Does the system do what it claims — analyze, segment, illustrate, narrate, export? |
| Performance Efficiency | Is generation time acceptable in a classroom period? |
| Usability | Can a Grade 5–6 student and a teacher operate it without instruction? |
| Reliability | Does it recover from a stalled or failed generation without losing work? |
| Security | Are classroom data isolation and asset access controls effective? |

**How it is evaluated.** For each characteristic, the **weighted mean** determines the overall level of
acceptability and the **standard deviation** the consistency of ratings among evaluators. The weighted mean is
interpreted against the descriptive rating scale:

| Weighted mean range (5-point Likert) | Descriptive rating |
|---|---|
| 4.20 – 5.00 | Excellent |
| 3.40 – 4.19 | Very Good |
| 2.60 – 3.39 | Good |
| 1.80 – 2.59 | Fair |
| 1.00 – 1.79 | Poor |

**Content validity precedes administration.** Before any evaluator sees it, the questionnaire is reviewed for
clarity and relevance of each item to the characteristic it claims to measure; a **Content Validity Index
(CVI)** is computed and sub-threshold items are revised or removed. The validated questionnaire is then
**piloted** on a small group held out from the reported sample, with **internal consistency reported
(Cronbach's α, floor ≥ 0.70)** per characteristic before the instrument is used for real.

### 6.4 What each instrument can and cannot do — and the trap to avoid

> **A mean Likert score of 4.5 / 5 on ISO/IEC 25010 is not evidence that the consistency loop works.**

This is the single most common way a capstone's evaluation is quietly hollow. The three instruments answer
three different questions and are never substituted for one another:

| Question | Instrument (Objective) | What it can support |
|---|---|---|
| Are the generated books acceptable? | Expert validation, open-ended + content analysis (Obj 3) | The **acceptability** of the outputs — presentation quality and classroom suitability, as experts judge them; not a causal claim |
| Can the judge measure consistency automatically? | Judge classification evaluation (Obj 4) | The judge's **classification performance** against human labels (precision/recall/F1) |
| Is the software any good? | ISO/IEC 25010 questionnaire (Obj 5) | **Perceived software quality.** Not efficacy |

No instrument makes a **causal** "the pipeline helped" claim: there is no control or comparison group, and the
study makes no causal or comparative claim of superiority (§9). Reading perceived software quality as efficacy
would be an error of the same class as claiming learning gains. Likewise, the fine-tuned judge is **never**
used to score the expert validation (§7.4).

---

## 7. Analysis plan ⚠️ (pre-registration)

**Written and timestamped before the first data point.** Almost no capstone does this. It is the cheapest
defensive move available, and it converts a null result from a failure into a finding.

### 7.1 Objective 3 — acceptability (expert validation)

- **Design.** The generated picture books are validated **directly** by the expert panel (§6.1); there is no
  control condition and no ON/OFF contrast (the ablation is dropped, ADR-008).
- **Analysis.** Content analysis: written responses coded into positive / negative / suggestion categories
  against the five pre-set criteria (narrative coherence, story faithfulness, visual presentation, visual
  style consistency, classroom suitability), then tallied per criterion.
- **Reporting.** A structured per-criterion summary of the coded categories, with representative excerpts, that
  determines the level of acceptability and classroom suitability of the generated books.
- **What it cannot support.** No causal "the pipeline caused this quality" claim — there is no control arm. It
  reports what the outputs are, as experts validate them.

### 7.2 Objective 4 — the fine-tuned judge's classification performance

The fine-tuned judge predicts Same/Different Character for each held-out image pair; predictions are matched to
the human reference labels by unique pair ID and scored with **precision, recall, and F1-score on the
`different_character` class, F1 primary**, each with a 95% bootstrap confidence interval (10,000 resamples,
**clustered by character, not by pair**). Fifteen scenes of one character are not fifteen independent
observations; a pair-level bootstrap yields an interval that is too narrow, and this is the likeliest place a
statistics reviewer finds a hole. A **secondary descriptive endpoint** reports the human versus non-human
character slice, where the judge's difficulty is expected to concentrate.

**Optional comparison (secondary).** To characterise the effect of fine-tuning and the model's suitability for
integration, the fine-tuned model **may** be reported alongside its **zero-shot base** (`Qwen2.5-VL-7B`) and
the **existing prompted baseline** (`gemma-3-27b-it`) on the same held-out pairs and human labels — paired
per-item comparison via **McNemar's exact test**. This comparison is secondary to the fine-tuned model's
absolute agreement with human labels; embedding baselines (CLIP, DINOv2 cosine similarity) are reported as
scientific controls, not product candidates — a cosine emits a scalar and cannot say *"restate the scarf."*

**Deployment gate (an engineering decision, ADR-018 — separate from the reported finding).** Whether the
fine-tuned judge replaces the prompted incumbent in the product is decided by a pre-registered non-inferiority
gate (within **δ = 3 F1 points** of the prompted incumbent, **no regression in recall** on
`different_character`). The gate is a build decision; the reported research finding is the classification
performance above.

| Rung | Condition | Ship the fine-tuned judge? |
|---|---|---|
| A | Beats base **and** beats prompted baseline | Yes |
| B | Beats base; within δ = 3 F1 of the baseline; no recall regression | Yes |
| C | Beats base; loses to the baseline by more than δ | No — keep the prompted judge |
| D | Does not beat base | No — a bug to debug |

**Methodological requirements.** The human labels carry two annotators plus adjudication with **inter-annotator
reliability reported**, and the **held-out set is read exactly once** (§5.1).

### 7.3 Objective 5 — software quality (ISO/IEC 25010)

Weighted mean and standard deviation per characteristic (Functional Suitability, Performance Efficiency,
Usability, Reliability, Security), interpreted against the Table in §6.3, with Content Validity Index and
Cronbach's α reported for the instrument.

### 7.4 Non-circularity — the constraint that governs everything above

> **The expert validation is never scored using the judge.**

The judge drives regeneration inside the pipeline. Using that same judge as the acceptability outcome would be
the system grading its own homework. The Objective-3 outcome is the **expert validators' content-analysed
judgments**; the Objective-5 outcome is the ISO/IEC 25010 questionnaire. The judge's own accuracy is the
separate Objective-4 question, measured on a human-labeled, character-disjoint held-out set it never trained
on, and its results are never substituted for the expert validation.

This is the sharpest question a panel can ask, and the answer is fixed in the project's Architecture Decision
Records (`docs/product/ADRs.md`, ADR-004) so that it is never improvised under pressure.

---

## 8. Ethics and child-safety measures in the system

Beyond the consent architecture in §3.2, the system itself carries safety obligations because its users are
children.

- **No unmoderated generated image ever reaches a child** — including the canonical character reference before
  it is revealed. Moderation runs in a fixed order: input text, then the character reference, then every output
  image.
- **Personally-identifiable information is redacted before storage, captioning, or export.** A child narrating
  real life is the *expected* case, not the exception. Stock redaction tooling leaks Filipino names and address
  structures (`Barangay`, `Purok`, `Sitio`) and `+63 9xx` mobile formats, so custom recognizers are built for
  them.
- **Row-level security on every table; signed URLs for every asset; no public storage bucket.**
- **All sharing is classroom-scoped and teacher-gated.** Public sharing is permanently excluded, not deferred.
- **The fine-tuned judge is excluded from the safety path.** Safety is a gate with no fallback; it runs on a
  prompted, unmodified model.
- Failure and moderation screens receive the same design care as success screens.

Detail: `docs/capstone/ethics_and_safety.md` and `docs/product/ADRs.md` (ADR-011).

---

## 9. Threats to validity

| Threat | Mitigation |
|---|---|
| **Substrate dependence.** Results characterize one image model. | Reported as scope. The Phase 0.5 probe names the substrate and its non-human boundary explicitly. |
| **Circularity** of judge-as-metric | §7.4. Structural, not procedural. |
| **Character leakage** across judge splits inflates Objective-4 metrics | Character-disjoint splits, enforced in code with a leakage test in the deterministic suite (§4.3; CI is planned, not yet standing). |
| **Shortcut learning** on auto-labelled positives | Positives are human-confirmed; constructed negatives are train-only. |
| **Small held-out character count.** Ten primary stories yield few distinct characters, limiting Objective-4 power. | Split sizes are planning targets finalized against actual yield; power reported against the held-out **character** count (bootstrap clusters by character); backup stories and train-only augmentation partially offset. **Flagged as an open reconciliation item (§4.1).** |
| **Annotator fatigue and drift** | Calibration before scoring; mid-session drift check; adjudication rate reported. |
| **Perceived quality mistaken for efficacy** | §6.4. The ISO/IEC 25010 result is never presented as an answer to Objective 3 or 4. |
| **No causal or comparative claim** | By design: no control/comparison group. The study does not claim superiority over other picture-book generation methods, and makes **no learning-gain claim** — creativity, literacy, writing ability, and long-term outcomes are outside scope. |
| **Generalizability** | One grade band, one country, one language regime, one source school. A delimitation derived from the study's scope, not an apology. |

**No formal power analysis precedes Phase 0.5**, because the effect size of reference conditioning in this
regime is unpublished — that is precisely the gap the study addresses. Phase 0.5 supplies the first
effect-size estimate for the substrate behaviour.

---

## 10. Reproducibility

Random seeds are fixed and reported, and seed reproduction is **verified empirically on both generation
endpoints** rather than assumed from vendor documentation. Model identifiers, versions, and provider routing
are pinned. Every pipeline run is traced: per-scene verdicts, regeneration counts, latency, and cost.
Deterministic software tests mock every model call; fuzzy quality is measured only in an offline evaluation
harness, never in the deterministic suite. (Those tests are run locally; continuous integration is planned but
not yet configured in the repository — see §1.5.) The trained artifact is a LoRA adapter of a few
tens of megabytes over public, Apache-2.0 base weights.

**Released:** the pipeline source, the Story Memory schema, the judge prompt and its structured output schema,
the failure-reason taxonomy, the annotation guide, and the LoRA adapter.

**Not released:** the story corpus. It is child writing collected under a consent form that does not permit
redistribution.
