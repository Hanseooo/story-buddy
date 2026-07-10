# StoryBuddy: Research Direction and Goals

> **This document is derived, not authoritative.** It exists so an adviser or panel can understand the
> research without reading an ADR. The sources of truth are `docs/product/RESEARCH_PROTOCOL.md` (method),
> `docs/product/ADRs.md` (why), `docs/product/PRD_v2.md` (what), `docs/product/ROADMAP.md` (when).
> **Where this document and those disagree, they win and this one is a bug.**

Target output format is **IMRaD / IEEE**. Section 9 maps each part below onto the manuscript.

---

## 1. The problem

There are two problems here. Only one of them is the research problem, and confusing them is the most
likely way this defense goes badly.

### 1.1 The motivating problem (the warrant — *not* what we measure)

A child writes a story. The teacher marks it. It goes in a folder. Nobody reads it. Prior work on writing
motivation is unusually consistent that an **authentic audience** and **actual publication** are among the
strongest levers on children's writing engagement.

But illustrating and publishing forty stories is not something a Grade 5–6 teacher can do. The cost of
publishing a child's story as an illustrated book is, in practice, *infinite*. Generative AI could collapse
that cost to three minutes and a few pesos.

**This is the motivation. It is established by prior literature, and it is not a finding of this study.**

### 1.2 The research problem (what we actually solve and measure)

Generative models drift. The hero is a boy on page one and a different boy on page four. The dog changes
breed. The style shifts halfway through.

> **An inconsistent picture book does not transmit the child's story — it transmits noise.**

No single generative model produces a coherent multi-scene picture book that holds a **stylized, invented,
frequently non-human** character across pages. This regime is not merely hard; it is *unmeasured*. No open
image model has published identity-similarity benchmarks split by human vs. non-human subject (as established in the project's Architecture Decision Record 001 [ADR-001] available in the source repository, which evaluated candidates like Qwen-Image-Edit and FLUX.1 and found that non-human/stylized identity preservation remains unbenchmarked),
and **no dataset exists that provides human pairwise identity judgments over stylized invented characters**
(`docs/specs/judge-finetune.md` §5.1 in the repository). That absence is itself a contribution of this work.

### 1.3 Why these are the same problem

The artifact is only worth publishing if it actually **is** the child's story. A book whose hero changes
on page four has not published the child — it has published the model.

> **The technical problem and the educational benefit are the same claim viewed from opposite ends.**
> That is what makes this research rather than integration.

**Central research question:**

> *Does an automated consistency-verification-and-correction loop produce picture books faithful enough
> that other readers recover the story the child meant to tell?*

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

**The shipped judge is a prompted `gemma-3-27b-it`.** A fine-tuned `Qwen2.5-VL-7B` is a candidate replacement
for that one part, evaluated in Phase 2.5, shipped only if it clears its gate. The pipeline is unchanged
either way. See `model_finetuning.md`.

---

## 3. How we measure it

| RQ | Question | Instrument |
|---|---|---|
| RQ1 | How accurately does the system identify key scenes from child-written stories? | Story Completeness vs. human-annotated major plot points |
| **RQ2** | **Does the Character Bible + VLM consistency loop measurably improve visual consistency vs. naive per-scene generation?** | **Blind ablation; human consistency ratings** |
| RQ3 | How acceptable is the storybook (coherence, consistency, illustration quality, usability)? | Blind scored ratings |
| RQ4 | How gracefully does the system handle **under-length** stories without inventing content? | Scene-count floor behavior |
| **RQ5** | **Do readers of a pipeline-ON book recover the author's characters and plot more accurately than readers of pipeline-OFF?** | **Naive-reader comprehension instrument** |
| RQ6 | Does fine-tuning an open VLM judge improve agreement with humans over the **un-fine-tuned base**, and does the gain concentrate on **non-human** characters? | Pre-registered superiority test on held-out ΔF1 |

**RQ2 is the mechanism. RQ5 is the outcome. RQ6 is instrument validity.** RQ1, RQ3 and RQ4 are supporting.
This is **one study**, not six.

### 3.1 The ablation (RQ2)

The same story corpus is generated **twice, from the same seed**:

- **pipeline-ON** — canonical reference + VLM consistency checker + targeted regeneration.
- **pipeline-OFF** — naive per-scene generation. No reference, no checker, no regeneration.

Adult raters judge **blind to condition**. Seed-matching is what makes the comparison fair, and it requires
that seeds actually reproduce on both generation endpoints — verified empirically in the Phase 0.5 spike,
not assumed from vendor documentation.

### 3.2 The comprehension instrument (RQ5)

A reader who has **never seen the story text** is given the book alone, then asked:

1. **Who was the story about?** (free recall of characters)
2. **What happened?** (free recall of events)
3. *What can you say about the story?* — reflective, unscored; it exists for the author's benefit.

Recalled characters and events are matched against the **same human-annotated plot points RQ1 already
requires.** One annotation, two uses.

Two properties worth stating in Methods. **The reader need not be a child**, which is why RQ5 runs on
adult raters and survives an ethics delay. And **asking the author "did it match your intent?" is a weaker
instrument** — authors know what they meant and will read it into any illustration. A naive reader cannot.

### 3.3 The non-circularity constraint

> **RQ2 is never evaluated using the judge.**

The judge drives regeneration inside the pipeline-ON arm. Using that same judge as the outcome measure would
be circular — the system would be grading its own homework. RQ2's outcomes are **human ratings** and RQ5.
This is the sharpest question a panel will ask, and the answer is fixed in ADR-004 (available in the project repository, which explicitly decouples the judge used for pipeline regeneration from the outcome measures of human consistency ratings and reader comprehension to ensure valid, non-circular research claims) so it is never improvised.

---

## 4. Data gathering

### 4.1 Corpus

Test stories must be **real or realistic child writing**, not builder-authored clean prose — which would
measure best-case only. Grade 5–6, English with Taglish code-switching tolerated.

**Target: 50 donated stories; take 60–70 if recruitment allows.** That number is set by the fine-tune, not
the ablation: stories yield characters, and characters are the unit of RQ6's character-disjoint 33 / 5 / 12
split. More characters is the cheapest statistical power the project has, **and the corpus is closed after
Phase 2.5 — it is unfixable later.**

**One corpus, three uses:** the ablation's stimuli (RQ2), the rating material (RQ1, RQ3, RQ5), and — once
the pipeline has drawn it and researchers have labelled the drawings — the judge's training data (RQ6).

Development and debugging use **researcher-written fixture stories**. These are not the corpus, carry no
ethics load, and are never used as stimuli or as evidence.

### 4.2 Participants, in two tiers

**Tier 1 — adults (N ≈ 15–30). Carries RQ1–RQ6. Designed to stand alone.** Blind scored ratings plus the
RQ5 comprehension instrument. Inter-rater reliability defined up front.

**Tier 2 — children (N ≈ 8–15). Enrichment. May slip without sinking the capstone.** Validated instruments
(Fun Toolkit: Smileyometer + Again-Again), a story-fidelity item, in-app peer comprehension, and behavioral
logging — which is more reliable than child self-report. Watch the novelty confound: repeat use *within* a
session matters more than first-reaction delight.

### 4.3 Ethics — two stages, because the original design had a hidden deadlock

The corpus is real child writing; the children who write it are the Tier-2 participants. A single ethics
submission therefore silently blocked Tier 1 on Tier-2 clearance — the exact dependency Tier-1
self-sufficiency exists to prevent. Splitting the submission is the fix.

- **Stage 1 — story donation.** Children write stories. They never touch the system. Anonymized text, nothing
  about the child. Narrow, low-risk, comparatively fast. *Unblocks the entire research track.*
- **Stage 2 — system use.** Children use StoryBuddy, read classmates' books, write reflections. Interactive,
  peer-visible, child-authored content. Materially heavier review. *Gates Tier 2 only.*

> **The Stage-1 consent form must state that donated stories may be used to build and evaluate an AI model.**
> The donated story becomes illustrations, researchers label those illustrations, and those labels become
> weights in a model we ship. Anonymising the child's *name* does not change that. It costs one sentence, and
> **there is no retroactive fix** — collect first and the only lawful options are to re-consent every child
> or delete the data.

Both stages require guardian informed consent **and** age-appropriate child assent (PH Data Privacy Act 2012).

### 4.4 Pre-registration

**The analysis plan — hypotheses, baselines, metrics, success criteria — is written and timestamped before
anything is run.** For RQ6 this converts a risk into an asset: a fine-tuned judge that *loses* to the prompted
incumbent becomes a publishable finding ("prompting remains competitive at this scale; the bottleneck is data,
not capacity") rather than a result to be spun. The same logic protects RQ2 — a null result becomes a finding
about the substrate, not a failed capstone.

Almost no capstone does this. It is the cheapest defensive move available.

---

## 5. Who benefits, and what we refuse to claim

**The benefit to a Grade 5–6 classroom is a design property, and it is defensible on architecture alone.**
An open-weight, self-hostable pipeline carries **no per-seat vendor cost** — the difference between a tool a
well-funded private school buys and one a provincial public school can run. That is the SDG-4 (Quality
Education) hook. It is a property of the system, not a hope about its effects.

Within the study, the demonstrated benefit is **fidelity of transmission**: RQ5 shows whether a reader
recovers the characters and events the child actually wrote. A book that transmits the child's story is the
authentic-audience artifact the motivating literature calls for.

**What this study does not claim, and why:**

| We do not claim | Why not |
|---|---|
| **Learning gains** in children's writing | N ≈ 8–15, no non-illustrated control, no pre/post design, no longitudinal window. Prior literature is the **warrant** for why fidelity matters; it is not our finding. Overclaiming here is the single most likely way the defense goes badly. |
| **Privacy preservation** | The child's text transits a hosted provider. Only on-device generation could claim otherwise (Future Work). |
| **Watermark provenance** | No open equivalent to SynthID-Image exists; C2PA is Future Work. |
| **That the fine-tuned judge will ship** | It ships only if it clears a pre-registered gate. Rung C — it beats its base but loses to the prompted incumbent — satisfies RQ6 and keeps the prompted judge in the product. |

---

## 6. Scope and boundaries

**Grade 5–6 (ages 10–12), Philippines, English with Taglish tolerated.** Each boundary is derived from a
research question, not chosen for convenience:

- They **write independently** → the story is unambiguously the child's. Scaffold a Grade 2 student and RQ5
  is meaningless: whose story did we illustrate?
- They **read fluently** → peer comprehension is measurable at all.
- **English is the medium of instruction** from Grade 4 → one language, one moderation regime, one TTS voice.
- They are **pre-adolescent** → peer feedback is unlikely to be cruel.

At N ≈ 8–15 the study cannot stratify by age, and age is one of the largest sources of variance in children's
writing. Broadening the band would add variance, not generality. **A tight population is a delimitation, not
an apology.**

**In scope:** Story Analyzer · Scene Segmentation (10–15 scenes, floor ≥ 3) · Character Bible + canonical
reference (≤ 2 canonical references) · three style presets · Prompt Optimizer · Image Generator
(Qwen-Image-Edit) · prompted VLM consistency judge + targeted regeneration · moderation stack (input text,
output images, Filipino PII redaction) · slide composer with Kokoro-82M narration · PDF export ·
teacher-gated classroom sharing with peer reflection.

**Permanently excluded:** public sharing. All sharing is classroom-scoped and teacher-gated.

**Deferred:** multi-child collaboration · kid-uploaded reference images · languages beyond English/Taglish ·
on-device generation · more than three art styles.

**Open-weight mandate.** No proprietary vendor models. This is what makes the equity claim a design property
rather than a hope, and it is why the system is self-hostable and replicable.

---

## 7. Intended contributions

1. **A pipeline whose causal contribution is measured, not asserted** (RQ2's blind, seed-matched ablation).
   This is the answer to *"isn't this just an API wrapper?"*
2. **Evidence on whether consistency actually transmits a story** (RQ5) — the bridge from a technical metric
   to a human outcome.
3. **A characterization of an unmeasured regime** — identity retention for stylized, invented, non-human
   characters, where ADR-001 (in the repository) records that no published benchmark splits identity similarity by human vs. non-human subject for current open image models.
4. **A fine-tuned open VLM consistency judge, honestly evaluated** against four baselines with a
   pre-registered claim ladder — including the outcome where it loses.
5. **Equity by construction** — an open-weight, self-hostable stack with no per-seat licensing cost.

---

## 8. Trajectory

Riskiest assumptions first. Build track and research track run in parallel and meet at Phase 2.5 and Phase 3.

| Phase | What | Status |
|---|---|---|
| 0 | Scaffolding & walking skeleton | ✅ done |
| **0.5** | **Open-weight spike — can the image model hold a non-human character?** | **⚠️ not run. Everything below is contingent on it.** |
| 1 | Core pipeline + prompted consistency judge | blocked on 0.5 |
| 2 | Moderation, classroom auth, sharing, narration, export | blocked on probe 4 |
| 2.5 | Judge fine-tuning + evaluation | blocked on Ethics Stage 1 → corpus → a Phase 1 run |
| 3 | Ablation, Tier-1 harness, Tier-2 | blocked on corpus |

**Phase 0.5 is a kill criterion, and it has not run.** If the image model cannot hold an invented non-human
character, that is a finding worth reporting and the product's scope changes. It is the cheapest possible
place to learn the substrate does not work — roughly one dollar. Every document downstream is written as
contingent, because it is.

**Ethics Stage 1 is the long pole and cannot be compressed by coding faster.** The fine-tune sits four hops
downstream of an ethics form: *Stage 1 → stories → images → labels → fine-tune.* Everything after `images`
is a weekend. Everything before it is months.

---

## 9. Mapping onto the IMRaD manuscript

| Manuscript section | Draw from |
|---|---|
| **Introduction** | §1.1 (motivation, cited to prior work) → §1.2 (the gap) → §1.3 (the research problem + central RQ) → §7 (contributions). Lead with the child and the folder; land on identity drift. |
| **Related Work** | §1.2's two absences — no non-human identity benchmark (per ADR-001 in the repository, which confirms this gap across current open models), no dataset with human pairwise identity judgments (see `docs/specs/judge-finetune.md` §5.1 in the repository, incl. the rejected-alternatives table). |
| **Methods** | **Drafted in full: `docs/capstone/methodology.md`** — development methodology, system under test, data collection, datasets, training and validation, instruments, analysis plan, ethics, threats to validity. |
| **Results** | Phase 0.5 probe results · the ablation table · RQ5 recall scores · RQ6's four-baseline table with CIs |
| **Discussion** | §5 — what the numbers support, and the four claims we refuse to make. Phase 0.5's non-human boundary belongs here if Quill fails. |
| **Limitations** | §5's table, §6's delimitation, and the fact that the corpus is one grade band in one country. |

**Write the Methods section before the Results exist.** It is already almost entirely determined by
`RESEARCH_PROTOCOL.md`, and writing it early is what makes the pre-registration in §4.4 real rather than
decorative.

→ **Drafted: `docs/capstone/methodology.md`.** Its §7 (analysis plan) is the pre-registration and needs
adviser sign-off **before the first data point is collected.** Its §6.4 (ISO/IEC 25010 system-evaluation
questionnaire) needs the required standard and evaluator profile confirmed with your adviser.
