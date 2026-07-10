# StoryBuddy — Research and Development Methodology

**Reading note.** This document is written to be read on its own, without access to the project's source
repository. Where a claim is grounded in an internal engineering document, that document is named explicitly
and can be found at the stated path in the StoryBuddy source repository. Those files are the authoritative
records; this document summarizes them for a reader who has not seen them.

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

---

## 1. Development methodology (SDLC)

### 1.1 What model this is

**A risk-driven incremental model with stage-gated phases, influenced by Boehm's Spiral model.**

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

### 1.2 The phases and their gates

| Phase | Purpose | Gate to leave it |
|---|---|---|
| **0** — Scaffolding | One story end-to-end through real infrastructure | A real slideshow renders. ✅ done |
| **0.5** — Open-weight spike | Resolve the substrate risk cheaply | **Kill criterion.** Reference conditioning retains identity on ≥ 80% of items **and** exceeds unconditioned generation by ≥ 30 points |
| **1** — Core pipeline | The consistency loop is real, on clean stories | A story produces a consistent book; a case exists where the judge caught a drifted image and the retry fixed it |
| **2** — Safety & classroom | Safe for a real child, survives messy input | The Filipino/Taglish moderation probe passes in **both** directions |
| **2.5** — Judge fine-tuning | An honestly evaluated specialized judge | A results table exists and the held-out set was read exactly once |
| **3** — Evaluation & study | The ablation and the user study | One full ablation session end-to-end, clean metrics table |

Phase 0.5's kill criterion is the sharpest instance of the method. **It has not yet run**, and every claim
downstream of it is written as contingent, because it is. If the substrate cannot hold an invented non-human
character, that is a reportable finding and the product's scope changes — discovered for one dollar rather
than in month five.

### 1.3 Why the build track is iterative and the research track is not

The two tracks run in parallel and meet twice: at Phase 2.5 (the fine-tune consumes Phase 1's output) and at
Phase 3 (the study needs a working system).

**The software process is iterative.** Code is cheap to revise because it can be tested, and a design flaw
found in week six costs a rewrite.

**The research process is plan-driven and pre-registered.** The hypotheses, statistical tests, units of
analysis, and success criteria in §7 are fixed before the first data point. Adapting an analysis after seeing
the data is not agility — it is p-hacking. Data is collected once, and children cannot be re-consented.

If asked whether pre-registration is "just Waterfall": pre-registration constrains **inference**, not
**implementation**. The image generator can be rewritten on Tuesday. The hypothesis cannot.

### 1.4 Engineering practices that carry research weight

- **Contract-first.** Every pipeline stage reads and writes a single versioned Pydantic schema (*Story Memory*).
  Language models are constrained to strict JSON-schema structured output, so a malformed response fails at the
  boundary rather than propagating.
- **Deterministic orchestration.** The pipeline is a fixed state machine (LangGraph). Conditional edges exist
  only at moderation pass/fail and consistency pass/fail. There is **no autonomous agent routing**, so the
  execution path is a function of the input, and worst-case cost is bounded. This is a precondition for the
  ablation in §7.1: an ON/OFF comparison is only meaningful if the two arms differ in exactly one respect.
- **The testing bright line.** Deterministic tests mock every model call and must stay green in continuous
  integration. Fuzzy quality — "is the character consistent?" — is measured only in an offline evaluation
  harness against real models. The two never mix. A generated-content assertion in CI is a flaky test, not a
  measurement.
- **Frozen decisions.** Architectural decisions are recorded in `docs/product/ADRs.md` and are not revised
  silently; changing one requires appending a new record stating context, decision, consequences, and
  alternatives.

---

## 2. System under test

A deterministic pipeline. The stages, in order:

| Stage | Function |
|---|---|
| Input moderation | Text safety gate, then personally-identifiable-information redaction |
| Story Analyzer | Entity and coreference extraction into the Story Memory contract |
| Scene Segmentation | Selects 10–15 scenes; floor of ≥ 3 for short stories; never invents content |
| Character Bible | ≤ 2 canonical characters, each rendered **once** as a reference image |
| Style preset | One of three hand-authored prompt fragments, frozen for the storybook |
| Prompt Optimizer | Scene + character bible + style preset + story memory → structured prompt |
| Image Generator | Reference-conditioned image edit (ON) or plain text-to-image (OFF) |
| Consistency judge | Vision-language model; emits `differences_observed` **before** `same_character` |
| Regeneration | One targeted, prompt-corrected retry; best-of fallback; capped |

**Models.** Text analysis: `qwen/qwen3-32b`. Image generation: `Qwen-Image-Edit` (Apache-2.0). Consistency
judge: prompted `gemma-3-27b-it`. Narration: `Kokoro-82M`. All open-weight. No proprietary vendor model
appears anywhere in the pipeline — a constraint that makes the system self-hostable and the equity claim a
property of the design rather than an aspiration. Model identifiers, versions, and provider routing are
pinned and reported.

**Reason-then-score.** The judge's structured output declares *what differs* before *whether the characters
match*. Field order is load-bearing: a model that emits a verdict first will rationalize toward it.
`failure_reasons` is drawn from a **closed taxonomy** — `wrong_colour`, `wrong_species`, `wrong_body_feature`,
`wrong_clothing`, `wrong_style`, `different_face`, `character_absent` — fixed before any labelling begins.
Extending the taxonomy after annotation starts invalidates every label already collected.

**The judge in the shipped pipeline is a *prompted* model.** A fine-tuned `Qwen2.5-VL-7B` is evaluated as a
candidate replacement for that one component (§5) and ships only on clearing a pre-registered gate. The
pipeline's architecture is identical either way.

---

## 3. Data collection

### 3.1 What is collected, from whom

| Data | Source | Used for |
|---|---|---|
| Story text | Donated child writing (Grade 5–6) | Ablation stimuli; rating material; the source of every generated image |
| Plot-point annotations | Two trained researchers, from text alone | RQ1 scoring; RQ5 scoring |
| Storybook ratings | Adult raters, blind to condition | RQ2, RQ3 |
| Free-recall responses | Naive adult readers | RQ5 |
| Image-pair identity labels | Two trained annotators | RQ6 — the judge's training and evaluation data |
| System-evaluation questionnaire | Evaluators (IT practitioners, teachers) | Software-quality assessment (§6.4) |
| Child instrument responses | Grade 5–6 participants | Tier 2 enrichment |
| Behavioral logs | Instrumentation | Tier 2 engagement measures |

### 3.2 Ethics: two stages, and the deadlock they resolve

The corpus is real child writing, and the children who write it are the same children who would later use the
system. A single ethics submission therefore made every result — including the adult-only ones — contingent on
clearance for the heavier, interactive child-facing study. Splitting the submission removes that dependency.

**Stage 1 — story donation.** Children write stories. They never touch the system and never see each other's
work. Anonymized text is collected; nothing about the child is. Narrow, low-risk, comparatively fast. This
stage unblocks the entire research track.

**Stage 2 — system use.** Children use StoryBuddy, read classmates' books, and write reflections.
Interactive, peer-visible, child-authored content; a materially heavier review. It gates Tier 2 only.

> **The Stage-1 consent form states that donated stories may be used to build and evaluate an AI model.**
> The donated story is turned into illustrations, researchers label those illustrations, and those labels
> become weights in a model. Anonymising the child's *name* does not change that the child's creative content
> flows into the model. It costs one sentence, and **there is no retroactive fix**: stories collected without
> this clause must be re-consented or deleted.

Both stages require **guardian informed consent and age-appropriate child assent**, under the Philippine Data
Privacy Act of 2012 and the university ethics board. Draft consent and assent language is held in
`docs/product/RESEARCH_PROTOCOL.md` §9.

**Ethics Stage 1 is the project's longest dependency and cannot be compressed by coding faster.** The
fine-tuned judge sits four hops downstream of an ethics form: *clearance → stories → images → labels →
fine-tune.* Everything after `images` takes a weekend. Everything before it takes months.

### 3.3 Participants

**Tier 1 — adult raters and readers (N ≈ 15–30). Carries every research question. Designed to stand alone.**
Recruited as naive readers and blind raters; no expertise in generative modelling is required or desired.

**Tier 2 — children (N ≈ 8–15). Enrichment; may slip without sinking the study.** Grade 5–6 students who
write stories in the system, read classmates' books, and answer reflection prompts.

Recruitment order, by speed: private school (principal's discretion) → tutoring or learning centre →
parent-recruited convenience sample. A public school requires a Schools Division Office permit and is the
slowest available door. The researcher occupies the teacher/owner role during the study, so no school
partnership is required to reach N ≈ 8–15.

### 3.4 Procedure

1. **Phase 0.5 substrate probe** — a blind ON/OFF ablation over two characters (one real animal, one invented
   non-human), scored by the research team. It doubles as a **pilot of the Phase 3 rating instrument**,
   yielding a first effect-size estimate and a first inter-rater agreement figure.
2. **Corpus collection** under Ethics Stage 1.
3. **Annotation** of plot points and characters from text alone, *before any image is generated* (§6.1).
4. **Generation.** Each story processed twice, seed-matched, ON and OFF. Traces record per-scene verdicts,
   regeneration counts, latency, and cost.
5. **Rating sessions.** Blind, shuffled, condition never disclosed.
6. **Comprehension sessions.** Independent readers; one book each; one condition each.
7. **Image-pair labelling**, then fine-tuning and evaluation (§5).
8. **Tier-2 sessions**, if Stage 2 clearance is granted.

**Blinding is enforced by construction.** Generated items are written to opaque filenames; the file mapping
each item to its condition is withheld from raters and excluded from version control, so it cannot be
recovered from the repository's history.

---

## 4. Datasets

### 4.1 The story corpus

Stories are **donated child writing**, not researcher-authored prose. Builder-authored clean text would
measure best-case behavior only, and RQ4 — graceful handling of under-length, messy stories — would be
unanswerable by construction.

- **Population:** Grade 5–6 (ages 10–12), Philippines. English, with Taglish code-switching tolerated.
- **Target:** 50 stories; 60–70 if recruitment allows.
- **Provenance:** documented. Reviewers will ask.

The corpus size is set by the fine-tune, not by the ablation. Stories yield characters, and **characters** are
the unit of the judge's character-disjoint split (§4.3). More characters is the cheapest statistical power the
project has. **The corpus closes once labelling begins and cannot be grown afterwards** — this is a
recruitment decision, and it is unfixable later.

**One corpus, three uses:** the ablation's stimuli (RQ2); the rating material (RQ1, RQ3, RQ5); and — once the
pipeline has illustrated it and researchers have labelled those illustrations — the judge's training and
evaluation data (RQ6).

Software development and debugging use **researcher-written fixture stories**. These carry no ethics load,
are never used as stimuli, and are never reported as evidence.

**Fallback.** If Stage 1 clearance slips, Tier 1 runs on researcher-written stories composed deliberately in
the register of a ten-year-old, or on a public child-narrative corpus if one is found to exist. This weakens
RQ1 and RQ4, and is reported as a limitation rather than concealed.

### 4.2 The judge dataset: there is nothing to download

**No public dataset provides human pairwise identity judgments over stylized, invented, non-human characters.**
Candidates were surveyed and rejected on the record (full table in `docs/specs/judge-finetune.md` §5.1):

| Candidate | Fatal problem |
|---|---|
| **DreamBench++** | 150 **photographic** subjects. Training a judge on photos of real corgis and deploying it on a cartoon dragon aims a domain shift straight at the weakness being fixed. Used as a **held-out transfer test only** — evaluated, never trained on, never redistributed. |
| **PororoSV / FlintstonesSV** | Nine and seven characters in total. With so few, a character-disjoint split is impossible, so the model learns *"recognise Pororo,"* not *"compare two images."* |
| **StorySalon** | No identity ratings, and copyright-encumbered (frames scraped from video and e-books). |

**That absence is itself a contribution of this work.** The dataset is therefore *manufactured* from the
pipeline's own output over the donated corpus: roughly 50 stories yield ~50 canonical character references and
~800 scene images, at a cost of about US$29 in generation credits, producing ~1,200 labelled pairs.

### 4.3 Splits, and the three ways this dataset can lie to you

| Split | Characters | Pairs | Contents |
|---|---|---|---|
| Train | 33 | ~945 | Pipeline pairs + constructed negatives; deliberately balanced |
| Validation | 5 | ~75 | Pipeline pairs only, natural distribution. **All iteration happens here** |
| Held-out test | **12**, stratified human / non-human | ~240+, oversampled | Pipeline pairs only, natural distribution; two annotators + adjudication |
| Transfer test | — | as published | DreamBench++. Never trained on |

**Character leakage.** Splits are by **character, never by pair**. Every image derived from a given canonical
reference belongs to exactly one split. If one character appears in both train and test, agreement inflates
and nothing in the metrics reveals it. This is enforced in code and tested in continuous integration.

**Shortcut learning.** Hard negatives are free and clean: character A's reference against a scene generated
from character B's reference. Positives are **not** free. Treating *"the same reference was used"* as a
positive label looks free but is noisy in exactly the direction that matters — because generation *sometimes
drifts*, which is the entire reason the judge exists. A model trained on auto-labelled positives learns to
detect ***"was a reference image used?"*** rather than ***"is this the same character?"***. It will score
brilliantly on validation and be useless in the loop. **Every positive is human-confirmed.**

**Class imbalance.** The minority class (`different_character`) is the one the control loop acts on, and a
missed failure ships a broken page to a child. The training set is therefore balanced using constructed
negatives — but those negatives are placed in **train only**, so validation and test preserve the true
deployment distribution.

---

## 5. Training and validation

Two distinct kinds of training happen in this project, and both must be documented: the model is trained, and
so are the humans.

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

### 5.2 Human rater and annotator training ⚠️

Raters are not instruments until they are calibrated. Every human measurement in this study follows the same
protocol:

1. **A written annotation guide** with worked examples and explicit edge cases, produced before any data is
   scored. For the image-pair task, the guide fixes the closed failure-reason taxonomy (§2).
2. **Practice items drawn from outside the corpus** — for the story tasks, fixture stories; for the image task,
   pairs from the Phase 0.5 probe. Never from material that will be scored for real.
3. **Calibration.** Agreement is computed on the practice set. Scoring of real data does not begin until
   **Krippendorff's α ≥ 0.67** — the conventional floor for drawing even tentative conclusions; α ≥ 0.80 is
   the target. If the floor is not met, the guide is revised and the raters re-calibrate. **Revising the guide
   is legitimate; revising the data is not.**
4. **Adjudication.** Disagreements on real data are resolved by a third researcher, and the adjudication rate
   is reported.
5. **Drift check.** Agreement is recomputed midway through scoring. Raters relax over long sessions.
6. **Blinding.** No rater ever sees the condition (ON/OFF), and no rater sees the story text before scoring a
   comprehension response.

The final inter-rater reliability on the real data is **reported alongside every human measure.** A measure
without its α is not a measure.

---

## 6. Instruments, and how they are evaluated

Two different families of instrument appear in this study, and they answer different questions. Section 6.4
states plainly what each cannot do.

### 6.1 Plot-point annotation — the shared substrate

Two trained annotators independently mark the **major plot points** and **characters** of each corpus story
*from the text alone*, blind to any generated output. Disagreements are adjudicated; α is reported before the
annotation is used for anything.

This single annotation serves RQ1 (did the system select scenes covering these points?) and RQ5 (did a naive
reader recover these points from the finished book?). **One annotation, two uses.** It is produced before any
image exists, which is what prevents it from being contaminated by what the system happened to draw.

### 6.2 The blind rating instrument (RQ1, RQ2, RQ3)

Raters see storybooks with condition and provenance stripped: opaque filenames, shuffled order, no indication
of ON or OFF.

| Measure | Definition | Scale |
|---|---|---|
| Character consistency | Is the same character recognizable across scenes? | Ordinal |
| Style consistency | Is the visual style maintained across scenes? | Ordinal |
| Narrative coherence | Do the illustrations tell a connected story? | Ordinal |
| Illustration quality | Craft, independent of consistency | Ordinal |
| Story completeness | Proportion of annotated major plot points represented in selected scenes | 0–1 |

**How it is evaluated.** Inter-rater reliability (Krippendorff's α) across raters, reported before any
inferential test. The instrument is **piloted in Phase 0.5** on the two-character probe, which yields both a
first α and a first effect-size estimate — the rating instrument is thus tested before the study, not during it.

### 6.3 The comprehension instrument (RQ5) — the study's outcome measure

A reader who has **never seen the story text** receives the book alone, then answers:

1. **Who was the story about?** — free recall of characters
2. **What happened?** — free recall of events
3. *What can you say about the story?* — reflective, **unscored**; retained as a qualitative source

Responses are scored against the §6.1 annotation: proportion of annotated characters recovered, and proportion
of annotated major plot points recovered. Two scorers, blind to condition; α reported.

**Design justifications, because each will be challenged:**

- **Free recall, not multiple choice.** A recognition item contains its own answer. Free recall does not.
- **A naive reader, not the author.** Asking the child "did the book match what you meant?" is a weaker
  instrument: authors know what they intended and will read it into any illustration. A stranger cannot.
- **The reader need not be a child.** This is why RQ5 runs on Tier-1 adults and **survives an ethics delay.**
- **Between-reader by necessity.** A reader who has seen the pipeline-ON book already knows the story; their
  recall from the OFF book would measure memory, not transmission. Each reader sees exactly one book in
  exactly one condition, counterbalanced across stories. *This roughly doubles the readers required, and is
  not negotiable.*

### 6.4 The system-evaluation questionnaire (software quality) ⚠️

**Confirm the required standard and evaluator profile with your adviser before administering this.**

Separately from the research instruments above, the software artifact is evaluated with a structured
questionnaire administered to evaluators (IT practitioners and teachers), following **ISO/IEC 25010** software
product quality characteristics. Five-point Likert items, reported as mean and standard deviation per
characteristic, with an interpretation scale declared in advance.

| Characteristic | What is asked about |
|---|---|
| Functional suitability | Does the system do what it claims — analyze, segment, illustrate, narrate, export? |
| Usability | Can a Grade 5–6 student and a teacher operate it without instruction? |
| Reliability | Does it recover from a stalled or failed generation without losing work? |
| Performance efficiency | Is generation time acceptable in a classroom period? |
| Security | Are classroom data isolation and asset access controls effective? |

Internal consistency of the questionnaire is reported (Cronbach's α), and the evaluator sample is described.

### 6.5 What each instrument cannot do — and the trap to avoid

> **A mean Likert score of 4.5 / 5 from thirty evaluators is not evidence that the consistency loop works.**

This is the single most common way a capstone's evaluation is quietly hollow. The ISO/IEC 25010 questionnaire
measures **perceived software quality**. It is a software-engineering deliverable and it belongs in the
paper. It does **not** answer RQ2 (does the loop improve consistency?) or RQ5 (does the improvement transmit
the story?), because it involves no control condition, no blinding, and no ground truth. Presenting it as
though it did would be an error of the same class as claiming learning gains.

The division of labour is:

| Question | Instrument | What it can support |
|---|---|---|
| Does the loop change consistency? | Blind ablation (§6.2) | A **causal** claim — one variable differs |
| Does that change matter? | Comprehension instrument (§6.3) | A **human outcome** |
| Can the judge measure it automatically? | Judge evaluation (§7.3) | **Instrument validity** |
| Is the software any good? | ISO/IEC 25010 (§6.4) | **Perceived quality.** Not efficacy |

Likewise, the fine-tuned judge is **never** used to score RQ2 (§7.5).

---

## 7. Analysis plan ⚠️ (pre-registration)

**Written and timestamped before the first data point.** Almost no capstone does this. It is the cheapest
defensive move available, and it converts a null result from a failure into a finding.

### 7.1 RQ2 — does the consistency loop work?

- **Design.** Within-story: every story is generated twice, seed-matched, ON and OFF. Raters are blind.
- **Unit of analysis.** The **storybook**. Scene-level ratings from one book are not independent observations
  and are averaged within book before testing.
- **Primary test.** Wilcoxon signed-rank on paired (ON, OFF) storybook-level consistency ratings.
- **Secondary.** A cumulative-link mixed model on the ordinal ratings with random intercepts for story and for
  rater, using the item-level data without pretending it is independent.
- **Effect size.** Rank-biserial correlation with a 95% bootstrap confidence interval, resampled **by story**.
- **Reliability.** Krippendorff's α, reported before any inferential test.
- **Pre-registered direction.** ON > OFF. A null result is reported as a finding about the substrate.

### 7.2 RQ5 — does consistency transmit the story?

- **Unit.** Reader × book. Between-groups, since each reader sees one condition (§6.3).
- **Primary outcome.** Proportion of annotated major plot points recovered in free recall.
- **Secondary outcome.** Proportion of annotated characters recovered.
- **Test.** Mann–Whitney U on the primary outcome; a mixed model with a random intercept for story as
  secondary, since the same story appears in both arms with different readers.
- **This is the study's dependent variable of record.** RQ2 shows the mechanism moves; RQ5 shows it matters.

### 7.3 RQ6 — does fine-tuning the judge improve agreement with humans?

**Two gates, deliberately separated, because one number was being asked to decide two questions.**

- **Research gate (the research question).** Held-out ΔF1 on the `different_character` class, fine-tuned model
  versus **zero-shot `Qwen2.5-VL-7B`** — its own un-fine-tuned base. Significance by **McNemar's exact test**
  on paired per-item decisions. Effect size by ΔF1 with a 95% bootstrap confidence interval, 10,000 resamples,
  **clustered by character, not by pair.** Fifteen scenes of one character are not fifteen independent
  observations; a pair-level bootstrap yields an interval that is too narrow, and this is the likeliest place a
  statistics reviewer finds a hole. **Pass = the interval excludes zero.**
- **Product gate (the engineering decision).** Non-inferiority to the prompted `gemma-3-27b-it` incumbent
  within **δ = 3 F1 points**, with **no regression in recall** on `different_character` — a missed failure
  ships a broken page to a child.
- **Reported baselines.** Zero-shot `Qwen2.5-VL-7B`; prompted `gemma-3-27b-it`; CLIP cosine similarity;
  DINOv2 cosine similarity. The two embedding baselines are **scientific controls, not product candidates**:
  they emit a scalar, and the regeneration controller consumes structured failure reasons. A cosine cannot say
  *"restate the scarf."* If an embedding baseline wins on F1, that is a finding about metrics, not a product
  decision.
- **Secondary endpoint.** The human versus non-human character slice — where the contribution is claimed to lie.
- **Transfer.** DreamBench++, evaluated only.

**Pre-registered claim ladder**, declared before results exist:

| Rung | Condition | RQ6 answered? | Ship the fine-tuned judge? |
|---|---|---|---|
| A | Beats base **and** beats prompted Gemma | Yes | Yes |
| B | Beats base; within δ = 3 F1 of Gemma; no recall regression | Yes | Yes |
| C | Beats base; loses to Gemma by more than δ | **Yes** | No — keep the prompted judge |
| D | Does not beat base | No | No — this is a bug, not a result |

Beating one's own base model is **necessary, not impressive**, and is never presented alone. The
prompted-Gemma comparison, latency, and cost are reported unconditionally. **Rung C is a publishable negative
result**: *prompting remains competitive at this scale; the bottleneck is data, not capacity.* Rung D means
the adapter did nothing, which is a defect to debug rather than a finding to report.

### 7.4 RQ1, RQ3, RQ4, and the software evaluation

**RQ1:** Story Completeness — the proportion of annotated plot points covered by the selected scenes —
reported with its inter-rater reliability. **RQ3:** descriptive statistics over the acceptability ratings.
**RQ4:** scene count as a function of story length against the declared floor, plus a human check that no
scene contains content absent from the source text; the failure mode under test is **invention**, not brevity.
**Software evaluation:** mean and standard deviation per ISO/IEC 25010 characteristic, with Cronbach's α.

### 7.5 Non-circularity — the constraint that governs everything above

> **RQ2 is never evaluated using the judge.**

The judge drives regeneration inside the pipeline-ON arm. Using that same judge as the outcome measure would
be the system grading its own homework. RQ2's outcomes are **human ratings** (§6.2) and **RQ5** (§6.3). The
judge's own accuracy is a separate question with a separate instrument (§7.3), and its results are never
substituted for RQ2's.

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
| **Circularity** of judge-as-metric | §7.5. Structural, not procedural. |
| **Character leakage** across judge splits inflates RQ6 | Character-disjoint splits, enforced in code and tested in CI. |
| **Shortcut learning** on auto-labelled positives | Positives are human-confirmed; constructed negatives are train-only. |
| **Rater fatigue and order effects** | Item shuffling; condition never disclosed; session length capped; mid-session drift check. |
| **Novelty confound** (Tier 2) | Within-session repeat use weighted over first-reaction delight. |
| **Researcher-as-teacher.** The researcher occupies the teacher role. | Acknowledged. All Tier-1 scoring is done by raters with no stake in the outcome. |
| **Author bias** in fidelity self-report | The story-fidelity item is explicitly secondary; RQ5's naive reader is the instrument of record. |
| **Perceived quality mistaken for efficacy** | §6.5. The ISO/IEC 25010 result is never presented as an answer to RQ2 or RQ5. |
| **Small N** | Tier 1 (15–30) carries every research question. Tier 2 is enrichment and may slip. **No learning-gain claim is made.** |
| **Generalizability** | One grade band, one country, one language regime. A delimitation derived from the research questions, not an apology. |

**No formal power analysis precedes Phase 0.5**, because the effect size of reference conditioning in this
regime is unpublished — that is precisely the gap the study addresses. Phase 0.5 supplies the first
effect-size estimate, which is then used to size the Tier-1 rating load.

---

## 10. Reproducibility

Random seeds are fixed and reported, and seed reproduction is **verified empirically on both generation
endpoints** rather than assumed from vendor documentation. Model identifiers, versions, and provider routing
are pinned. Every pipeline run is traced: per-scene verdicts, regeneration counts, latency, and cost.
Deterministic software tests mock every model call and run in continuous integration; fuzzy quality is
measured only in an offline evaluation harness, never in CI. The trained artifact is a LoRA adapter of a few
tens of megabytes over public, Apache-2.0 base weights.

**Released:** the pipeline source, the Story Memory schema, the judge prompt and its structured output schema,
the failure-reason taxonomy, the annotation guide, and the LoRA adapter.

**Not released:** the story corpus. It is child writing collected under a consent form that does not permit
redistribution.
