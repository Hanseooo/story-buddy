# StoryBuddy — Methods

> **Derived document.** Sources of truth: `docs/product/RESEARCH_PROTOCOL.md`, `docs/product/ADRs.md`,
> `docs/specs/judge-finetune.md`. Where they disagree with this file, they win.
>
> **This is the manuscript's Methods section, drafted before any result exists.** That is deliberate.
> A Methods section written after seeing results is a narrative; written before, it is a pre-registration.
> Sections marked ⚠️ **require adviser sign-off before the first data point is collected** — after that,
> changing them is moving a goalpost.

---

## 1. Research design

A **within-story, between-reader blind ablation**, supplemented by an instrument-validity study.

The same story corpus is processed twice by the same system under two conditions:

- **pipeline-ON** — canonical character reference + VLM consistency judge + targeted regeneration.
- **pipeline-OFF** — naive per-scene generation. No reference image, no judge, no regeneration.

Both arms share the same story text, the same scene segmentation, the same style preset, and **the same
random seed**. The only difference is the consistency mechanism. Seed-matching is what licenses the causal
reading of RQ2, and it requires that seeds actually reproduce on *both* generation endpoints — verified
empirically in the Phase 0.5 spike rather than assumed from vendor documentation.

Condition is **within-story** (every story is generated both ways) but **between-reader** for RQ5. A reader
who has seen the pipeline-ON book already knows the story; asking them to recall it from the OFF book
measures memory, not transmission. Each RQ5 reader therefore sees **exactly one book, in exactly one
condition**, and condition is counterbalanced across stories.

---

## 2. System under test

A deterministic LangGraph pipeline. Nodes execute in fixed order; the only conditional edges are
moderation pass/fail and consistency pass/fail. There is no autonomous agent routing, so the execution
path is a function of the input and is reportable.

| Stage | Function |
|---|---|
| Input moderation | Text safety gate + PII redaction (Presidio, with custom Filipino recognizers) |
| Story Analyzer | Entity and coreference extraction into the Story Memory contract |
| Scene Segmentation | Selects 10–15 scenes; floor of ≥ 3 for short stories; never invents content |
| Character Bible | ≤ 2 canonical characters, each rendered once as a reference image |
| Style preset | One of three hand-authored prompt fragments, frozen for the storybook |
| Prompt Optimizer | Scene + character bible + style preset + story memory → structured prompt |
| Image Generator | Reference-conditioned image edit (ON) or text-to-image (OFF) |
| Consistency judge | Prompted VLM; emits `differences_observed` **before** `same_character`, plus `failure_reasons` |
| Regeneration | One targeted, prompt-corrected retry; best-of fallback; capped |

**Models.** Text: `qwen/qwen3-32b`. Images: `Qwen-Image-Edit` (Apache-2.0). Judge: prompted
`gemma-3-27b-it`. Narration: `Kokoro-82M`. All open-weight; no proprietary vendor model appears anywhere
in the pipeline. Model identifiers and versions are pinned and reported.

**Reason-then-score.** The judge's structured output declares *what differs* before *whether they match*.
Field order is load-bearing: a model that emits a verdict first will rationalize toward it. `failure_reasons`
is drawn from a **closed taxonomy** (`wrong_colour`, `wrong_species`, `wrong_body_feature`, `wrong_clothing`,
`wrong_style`, `different_face`, `character_absent`), fixed before any labelling begins. Extending the
taxonomy after annotation starts invalidates every collected label.

**The judge in the loop is a prompted model.** A fine-tuned `Qwen2.5-VL-7B` is evaluated as a candidate
replacement (§7.3) and ships only on clearing a pre-registered gate.

---

## 3. Materials: the story corpus

Stories are **donated child writing**, not researcher-authored prose. Builder-authored clean text would
measure best-case behavior only, and RQ4 — graceful handling of under-length, messy stories — would be
unanswerable.

- **Population:** Grade 5–6 (ages 10–12), Philippines. English, with Taglish code-switching tolerated.
- **Target:** 50 stories; 60–70 if recruitment allows.
- **Provenance:** Ethics Stage 1 story donation (§8). Documented; reviewers will ask.

The corpus size is set by RQ6, not by the ablation. Stories yield characters, and *characters* are the unit
of the fine-tune's character-disjoint split (33 train / 5 validation / 12 held-out test). More characters is
the cheapest statistical power available. **The corpus is closed once labelling begins and cannot be grown
afterwards.**

**One corpus, three uses:** the ablation's stimuli (RQ2), the rating material (RQ1, RQ3, RQ5), and — once the
pipeline has illustrated it and researchers have labelled the illustrations — the judge's training and
evaluation data (RQ6).

Software development and debugging use **researcher-written fixture stories**, which are never used as
stimuli and never reported as evidence.

**Fallback.** If Stage 1 clearance slips, Tier 1 runs on researcher-written stories composed deliberately in
the register of a ten-year-old, or on a public child-narrative corpus if one is found to exist. This weakens
RQ1 and RQ4 and is reported as a limitation, not concealed.

---

## 4. Participants

### Tier 1 — adult raters (N ≈ 15–30). Carries every research question. Designed to stand alone.

Recruited as naive readers and blind raters. No expertise in generative modelling required or desired.

### Tier 2 — children (N ≈ 8–15). Enrichment; may slip without sinking the study.

Grade 5–6 students who write stories in the system, read classmates' books, and answer reflection prompts.

Tier 1 is **not** blocked on Tier 2. This is why the ethics submission is split: the corpus is real child
writing and the children who write it are the Tier-2 participants, so a single submission would have made
every result contingent on the heavier review.

Recruitment order, by speed: private school (principal's discretion) → tutoring or learning centre →
parent-recruited convenience sample. A public school requires a Schools Division Office permit. The
researcher occupies the teacher/owner role during the study, so no school partnership is required to reach
N ≈ 8–15.

---

## 5. Instruments and measures

### 5.1 Human-annotated plot points (the shared substrate)

Two annotators independently mark the **major plot points** and **characters** of each corpus story from the
text alone, blind to any generated output. Disagreements are adjudicated. **Inter-rater reliability is
computed and reported (Krippendorff's α) before the annotation is used.**

This single annotation serves RQ1 (did the system select scenes covering these points?) and RQ5 (did a naive
reader recover these points from the book?). One annotation, two uses.

### 5.2 Blind rating instrument (RQ1, RQ2, RQ3)

Raters see storybooks with **condition and provenance stripped**: opaque filenames, shuffled item order, no
indication of ON/OFF. Measures:

| Measure | Definition | Scale |
|---|---|---|
| **Character consistency** | Is the same character recognizable across scenes? | Ordinal, per storybook and per scene |
| **Style consistency** | Is the visual style maintained across scenes? | Ordinal |
| **Narrative coherence** | Do the illustrations tell a connected story? | Ordinal |
| **Illustration quality** | Craft, independent of consistency | Ordinal |
| **Story completeness** | Proportion of annotated major plot points represented in the selected scenes | Proportion, 0–1 |

### 5.3 Comprehension instrument (RQ5)

A reader who has **never seen the story text** receives the book alone, then answers:

1. **Who was the story about?** — free recall of characters
2. **What happened?** — free recall of events
3. *What can you say about the story?* — reflective, **unscored**; retained as a qualitative source

Free recall is scored against the §5.1 annotation: proportion of annotated characters recovered, and
proportion of annotated major plot points recovered. Two scorers, blind to condition; α reported.

Free recall is used rather than recognition (multiple choice) because recognition items leak the answer.
Asking the *author* "did it match what you meant?" is a weaker instrument — authors know what they intended
and read it into any illustration. A naive reader cannot.

### 5.4 Child instruments (Tier 2)

Fun Toolkit (Read & MacFarlane): **Smileyometer** (liking) and **Again-Again** (engagement proxy). Both are
validated for this age band and are cited as such. A single **story-fidelity** item, author-only: *"Did the
book tell the story you wanted to tell?"* Peer comprehension uses the §5.3 instrument, in-app.

**Behavioral logging** is treated as more reliable than child self-report: completion rate, time-on-task,
spontaneous second-story starts, retry frequency. Repeat use *within* a session is weighted over
first-reaction delight, because novelty inflates the latter.

### 5.5 Judge evaluation (RQ6)

The judge is scored against **human labels on image pairs**: a character's canonical reference against a
generated scene image, labelled `same_character` / `different_character` plus `failure_reasons` from the
closed taxonomy. Two annotators; disagreements adjudicated; α reported.

Splits are **character-disjoint** — every image derived from a given canonical reference belongs to exactly
one split. A character appearing in both train and test inflates agreement with nothing in the metrics to
reveal it.

Positives are **human-confirmed, never auto-labelled.** Treating "a reference image was used" as a positive
label teaches the model to detect *whether a reference was used* rather than *whether the character matches* —
and generation sometimes drifts, which is the entire reason the judge exists. Constructed hard negatives
(character A's reference against a scene generated from character B) are free and clean, and are placed in
**train only**, so validation and test retain the deployment distribution.

---

## 6. Procedure

1. **Phase 0.5 substrate probe.** Before the study, a blind ON/OFF ablation over two characters — one real
   animal, one invented non-human — establishes that reference conditioning retains identity at all. This
   doubles as a **pilot of the Phase 3 instrument**, yielding an effect-size estimate and a first
   inter-rater agreement figure. Pre-registered pass criteria: ON identity ≥ 80%, and ON − OFF ≥ 30 points.
2. **Corpus collection** under Ethics Stage 1.
3. **Annotation** of plot points and characters from text (§5.1), before any image is generated.
4. **Generation.** Each story processed twice, seed-matched, ON and OFF. Traces record per-scene verdicts,
   regeneration counts, latency, and cost.
5. **Rating sessions.** Tier-1 raters score blind (§5.2). Item order shuffled; condition never disclosed.
6. **Comprehension sessions.** Independent readers, one book each, one condition each (§5.3).
7. **Judge labelling weekend** (§5.5), then fine-tuning and evaluation (§7.3).
8. **Tier-2 sessions**, if Stage 2 clearance is granted.

Blinding is enforced by construction: generated items are written to opaque filenames and the condition key
is held in a file that raters never receive and that is excluded from version control.

---

## 7. Analysis plan ⚠️

**Written and timestamped before the first data point.** Almost no capstone does this; it is the cheapest
defensive move available, and it is what converts a null result from a failure into a finding.

### 7.1 RQ2 — does the consistency loop work?

- **Unit of analysis:** the storybook. Ratings are averaged within storybook before testing; individual
  scene ratings from one book are **not** independent observations.
- **Primary test:** Wilcoxon signed-rank on paired (ON, OFF) storybook-level consistency ratings.
- **Secondary:** cumulative-link mixed model on the ordinal ratings, with random intercepts for story and
  for rater, to use the item-level data without pretending it is independent.
- **Effect size:** rank-biserial correlation, with a 95% bootstrap CI resampled **by story**.
- **Reliability:** Krippendorff's α across raters, reported before any inferential test.
- **Pre-registered direction:** ON > OFF. A null result is reported as a finding about the substrate.

### 7.2 RQ5 — does consistency transmit the story?

- **Unit:** the reader × book. Between-groups, since each reader sees one condition.
- **Primary outcome:** proportion of annotated major plot points recovered in free recall.
- **Secondary outcome:** proportion of annotated characters recovered.
- **Test:** Mann–Whitney U on the primary outcome; mixed model with a random intercept for story as a
  secondary, since the same story appears in both arms with different readers.
- **This is the study's dependent variable of record.** RQ2 shows the mechanism moves; RQ5 shows it matters.

### 7.3 RQ6 — does fine-tuning the judge improve agreement with humans?

**Two gates, deliberately separated, because one number was being asked to decide two questions.**

- **Research gate (the RQ):** held-out ΔF1 on the `different_character` class, fine-tuned model vs.
  **zero-shot `Qwen2.5-VL-7B`** — its own un-fine-tuned base. Significance by **McNemar's exact test** on
  paired per-item decisions. Effect size by ΔF1 with a 95% bootstrap CI, 10,000 resamples, **clustered by
  character, not by pair.** Fifteen scenes of one character are not fifteen independent observations; a
  pair-level bootstrap yields an interval that is too narrow, and this is the likeliest place a statistics
  reviewer finds a hole. **Pass = CI excludes zero.**
- **Product gate (the engineering decision):** non-inferiority to the prompted `gemma-3-27b-it` incumbent
  within **δ = 3 F1 points**, with **no regression in recall** on `different_character` — a missed failure
  ships a broken page to a child.
- **Reported baselines:** zero-shot `Qwen2.5-VL-7B`, prompted `gemma-3-27b-it`, CLIP cosine, DINOv2 cosine.
  The two embedding baselines are **scientific controls, not product candidates**: they emit a scalar, and
  the regeneration controller consumes `failure_reasons`. A cosine cannot say *"restate the scarf."*
- **Secondary endpoint:** the human vs. non-human character slice — where the contribution is claimed to lie.
- **Robustness:** ≥ 3 training seeds. Transfer evaluated on DreamBench++ (**evaluated only, never trained on,
  never redistributed**).
- **The held-out test set is read exactly once.** All iteration happens on validation.

**Pre-registered claim ladder.** Declared before results exist:

| Rung | Condition | RQ6 answered? | Ship the fine-tuned judge? |
|---|---|---|---|
| A | Beats base **and** beats prompted Gemma | Yes | Yes |
| B | Beats base; within δ = 3 F1 of Gemma; no recall regression | Yes | Yes |
| C | Beats base; loses to Gemma by > δ | **Yes** | No — keep the prompted judge |
| D | Does not beat base | No | No — this is a bug, not a result |

Beating one's own base model is **necessary, not impressive**, and is never presented alone. The prompted-Gemma
comparison, latency, and cost are reported unconditionally. Rung C is a publishable negative result:
*prompting remains competitive at this scale; the bottleneck is data, not capacity.*

### 7.4 RQ1, RQ3, RQ4

RQ1: Story Completeness (proportion of annotated plot points covered by selected scenes), reported with its
IRR. RQ3: descriptive statistics on the acceptability ratings. RQ4: scene count as a function of story
length against the declared floor, plus a human check that no scene contains content absent from the source
text — the failure mode is *invention*, not brevity.

### 7.5 Non-circularity — the constraint that governs everything above

> **RQ2 is never evaluated using the judge.**

The judge drives regeneration inside the pipeline-ON arm. Using the same judge as the outcome measure would
be the system grading its own homework. RQ2's outcomes are **human ratings** (§5.2) and **RQ5** (§5.3). The
judge's own accuracy is a separate question with a separate instrument (RQ6), and its results are never
substituted for RQ2's.

---

## 8. Ethics

Approved in **two stages**, because a single submission created a hidden deadlock: the corpus is real child
writing, and the children who write it are the Tier-2 participants, so every Tier-1 result would have been
blocked on the heavier Tier-2 review.

**Stage 1 — story donation.** Children write stories. They never touch the system and never see each other's
work. Anonymized text is collected; nothing about the child is.

> The Stage-1 consent form **states that donated stories may be used to build and evaluate an AI model.**
> The donated story becomes illustrations; researchers label those illustrations; those labels become weights
> in a model. Anonymising the child's name does not change that. **There is no retroactive fix** — stories
> collected without this clause must be re-consented or deleted.

**Stage 2 — system use.** Children use the system, read classmates' books, and write reflections.
Interactive, peer-visible, child-authored content; a materially heavier review. Gates Tier 2 only.

Both stages require **guardian informed consent and age-appropriate child assent** (Philippine Data Privacy
Act of 2012 and the university ethics board).

**Child-safety measures, in the system.** Moderation runs in a fixed order — input text, then the canonical
character reference, then every output image — and **no unmoderated generated image ever reaches a child,
including the character reference before its reveal.** PII is redacted before storage, captioning, or export;
a child narrating real life is the expected case, not the exception. Every table is row-level secured; every
asset is served by signed URL; no bucket is public. The fine-tuned judge is **excluded from the safety path
by design** — safety is a gate with no fallback, and it stays on a prompted, unmodified model.

---

## 9. Threats to validity

| Threat | Mitigation |
|---|---|
| **Substrate dependence.** Results characterize one image model. | Reported as scope. The Phase 0.5 probe names the substrate and its non-human boundary explicitly. |
| **Circularity** of judge-as-metric | §7.5. Structural, not procedural. |
| **Character leakage** across judge splits inflates RQ6 | Character-disjoint splits, enforced in code and tested in CI. |
| **Shortcut learning** on auto-labelled positives | Positives are human-confirmed; constructed negatives are train-only. |
| **Rater fatigue and order effects** | Item shuffling; condition never disclosed; session length capped. |
| **Novelty confound** (Tier 2) | Within-session repeat use weighted over first-reaction delight. |
| **Researcher-as-teacher.** The researcher occupies the teacher role. | Acknowledged. All Tier-1 scoring is done by raters with no stake in the outcome. |
| **Author bias** in fidelity self-report | The story-fidelity item is explicitly secondary; RQ5's naive reader is the instrument of record. |
| **Small N** | Tier 1 (15–30) carries every RQ. Tier 2 is enrichment and may slip. No learning-gain claim is made. |
| **Generalizability** | One grade band, one country, one language regime. A delimitation derived from the RQs, not an apology. |

**No formal power analysis precedes Phase 0.5**, because the effect size of reference conditioning in this
regime is unpublished — that is the gap the study addresses. Phase 0.5 supplies the first effect-size
estimate, and it is used to size the Tier-1 rating load.

---

## 10. Reproducibility

Random seeds are fixed and reported; seed reproduction is verified empirically on both generation endpoints.
Model identifiers, versions, and provider routing are pinned. Every pipeline run is traced (per-scene
verdicts, regeneration counts, latency, cost). Deterministic software tests mock every model call and run in
CI; fuzzy quality is measured only in an offline eval harness, never in CI. The trained artifact is a LoRA
adapter of a few tens of megabytes over public, Apache-2.0 base weights.

Released: the pipeline source, the Story Memory schema, the judge prompt and its structured output schema,
the failure-reason taxonomy, the annotation guide, and the LoRA adapter. **Not released:** the story corpus,
which is child writing collected under a consent form that does not permit redistribution.
