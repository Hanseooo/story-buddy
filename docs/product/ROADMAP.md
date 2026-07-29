# StoryBuddy — Implementation Roadmap

**Approach:** Walking skeleton → vertical slices → hardening. Riskiest assumptions first.
**SDLC:** Boehm's Spiral Model — each phase below is a stage-gated iteration (determine objectives →
identify/resolve risks → develop & verify → plan next iteration); full mapping in
`docs/capstone/methodology.md` §1.2.
**Team:** one developer (build), three researchers (corpus, annotation, study, ethics). The build track
is solo; the research track is not. They run in parallel and meet at Phase 2.5 and Phase 3.
**Companion docs:** PRD v2, ADRs, RESEARCH_PROTOCOL.

---

## Guiding principles

1. **Prove integration before depth.** The place a schedule dies is integration (async jobs, model wiring, storage). Get one story end-to-end through real infrastructure before making any single module smart.
2. **Riskiest-first.** Validate that the image model holds *your* characters consistent — **especially non-human ones** — and that the VLM-judge actually catches failures, in Phase 0.5, not Phase 4.
3. **Instrument from Day 1.** LangSmith tracing is your research dataset — turn it on in the skeleton.
4. **Exit criteria, not calendar.** Each phase has a definition of done.
5. **Ethics is the long pole and cannot be compressed by coding faster.** It starts before Phase 0.5.
6. **Findings propagate the same day they land.** A probe result or an ADR amendment silently
   falsifies sentences in *other* docs — phase status here, model IDs in `AGENTS.md`, procedure
   notes in `PHASE_05_RESULTS.md`. Grep for what changed and fix every hit in the same change;
   rule and blast radius in `AGENTS.md` → *Definition of Done*.

---

## Phase 0 — Scaffolding & Walking Skeleton *(done)*

One hardcoded story flows end-to-end through real infrastructure and produces one real slideshow.
`POST /storybooks` → job row → RQ worker → LangGraph stub nodes → image in Supabase Storage →
slideshow live via Realtime. LangSmith + Sentry on from the first commit.

**Status:** ✅ complete. Originally built against Gemini + Nano Banana; the open-weight swap
(ADR-001, ADR-002, ADR-015) landed with `backend/providers.py`, and `google-genai` is out of the
dependency tree entirely.

---

## Phase 0.5 — Open-Weight Model Spike *(~2 days; do not skip)*

**Goal:** retire the four unknowns the open-weight switch introduced, **before** Phase 1 depends on them.
This phase exists because ADR-001's headline capability is no longer vendor-verified: nobody has published
identity-similarity benchmarks for any open image model split by human vs. non-human subject.

The code half is done (`backend/providers.py`, `backend/spikes/phase_05.py`). **Status 2026-07-29:**
probe 1 run three times and resolved (Run 1 void, Run 2 FAIL, Run 3 FAIL on separation only) — branch
taken in the ADR-001 amendment, Qwen stays primary. Probe 3 **PASS** (both arms). Probes 2 and 4 not
run — 2 needs fal credit, 4 waits on the Phase-2 moderation spec; neither gates Phase 1. Results and
rationale in `PHASE_05_RESULTS.md`.

```
uv run python -m spikes.phase_05 consistency   # ~54 images, ~$1.90. Then score scores.csv blind.
uv run python -m spikes.phase_05 tally         # the kill criterion
uv run python -m spikes.phase_05 seed
uv run python -m spikes.phase_05 structured
uv run python -m spikes.phase_05 moderation
```

**1. Non-human character consistency — THE KILL CRITERION.** Two characters, deliberately: **Pip**, a fox
cub (a real animal with a canonical silhouette, heavily represented in illustration training data — the
*easy* case) and **Quill**, an invented three-eyed lizard-bird (the case ADR-001 is actually afraid of).
Each of **10 scenes** is generated **twice**: conditioned on the canonical reference (pipeline-ON) and from
the character description alone (pipeline-OFF) — n = 20 items per condition; at 5 scenes the 80% gate rode
on 8/10 items, too coarse for the project's most consequential decision (revised 2026-07-13, before any
probe ran). Items are shuffled behind opaque filenames; every team member scores `scores.csv` blind;
`tally` computes the result (per-item verdict = rater majority; ties score as not-identity).

Two criteria, **both** must hold:
- **Absolute:** pipeline-ON identity retained on ≥ 80% of items.
- **Separation:** pipeline-ON exceeds pipeline-OFF by ≥ 30 points.

Absolute-but-no-separation is a **fail**: the reference is not doing the work, and ADR-007's mechanism has no
measurable effect on this substrate. *Fail →* ~~escalate to FLUX.1 Kontext [dev]
(non-commercial, permitted — ADR-015) and re-run.~~ escalate **one rung down ADR-001's ladder** and
re-run — rung 1 is **OmniGen2**; Kontext is rung 4. *(Corrected 2026-07-29: this branch was authored
before the 2026-07-28 ladder reorder and still named the old first choice. Run 3 did escalate, and
correctly went to OmniGen2 per the ADR, not to Kontext per this line.)* If both fail, **stop and
surface it** — that is a Phase-0.5 finding, not a Phase-3 catastrophe.

If Pip passes and Quill fails, that is **not a defeat** — it maps the product's boundary, and it is the most
interesting sentence in the paper. Record it and decide scope, don't paper over it.

**Secondary arm (ADR-022, non-gating).** Run Quill through all three style presets — the secondary presets
run 5 of the 10 scenes, ~12 extra images, ~$0.50.
The scoring sheet gains one item beside identity: *"does this read as a hand-illustrated children's book, or
as AI art?"* Neither gates. But a preset that cannot hold an invented chimera, or that reads as generic AI
art, is re-authored or dropped **before** a child sees it. Author the three fragments before running the probe
so this is one probe, not two.

This probe is also a **dress rehearsal of the Phase 3 instrument** (ADR-008): it yields an absolute rate, a
mini-ablation, and an inter-rater agreement number, before anything has been built.

**2. Seed determinism.** Same seed twice, on **both** `edit_image` and `text_to_image` — the probe
seed-matches pipeline-ON against pipeline-OFF, so both endpoints must reproduce. Diff the bytes.
Replicate has an open, unresolved bug (#334) where seeds are ignored under its fast path. Verify
empirically; do not trust the docs. *Fail →* record against CC-7 and drop the reproducibility claim or
change provider.

**3. Structured output — in the shape each model is actually called with.** The text model gets text.
**The judge gets two images**, because that is the only way the judge is ever invoked, and OpenRouter's
structured-output support is per `(model, provider)` *and* per modality. A text-only probe of the judge
passes while the judge is broken. Confirm `provider.require_parameters: true` is honored.

**4. Filipino / Taglish moderation *(new — ADR-011 revision b)*.** The respondents are Filipino children,
the open image model has no built-in safety filter, and the proprietary backstop is gone. Nobody has
published Llama Guard's Filipino performance. Run the gate over harmful and benign Filipino/Taglish cases
and check **both directions**: a miss on a harmful case is a child-safety hole; a miss on a benign case
dead-ends a child's dragon fight. A routing error is also a finding — it means the gate runs on the worker.

**Exit criteria:** a written result per probe in **`docs/product/PHASE_05_RESULTS.md`** — which is filled
in *before* the probes run, so no number arrives without a pre-declared branch — and either a green light
for Qwen-Image-Edit or a recorded ADR amendment naming the fallback that passed.

**Gate → Phase 1:** probe 1 only. Both criteria must hold. Probes 2 and 3 record findings and do not block.
**Gate → Phase 2:** probe 4, no MISS in either direction.

> **Resolved 2026-07-29.** Probe 1 passed absolute (80%) and failed separation (+25 vs ≥30). Phase 1
> opens anyway under the ADR-001 amendment, which records the failed gate as a stated limitation
> rather than treating it as satisfied — see PHASE_05_RESULTS.md *Result — Run 3*. Probe 3 — the
> only remaining practical blocker, gating Phase 1's `consistency_check` node — **passed the same
> day**. Nothing in Phase 0.5 blocks Phase 1 now.

**⚠️ Kill-criterion phase.** The cheapest possible place to learn the substrate does not work.

---

## Phase 1 — Core Pipeline Intelligence *(~2–3 weeks; the research core)*

**Goal:** the pipeline works on a *clean* story you control, and the consistency loop is real.

**Entry:** probe 1 green. Each module gets a feature spec from `docs/specs/TEMPLATE.md` **before** its code
(CLAUDE.md §4), in the order below. The clean stories are yours — researcher-written dev fixtures, no ethics
load. They are **not** the corpus (RESEARCH_PROTOCOL §8).

- **Story Memory contract** — the Pydantic schema. Written first; freezes MASTER_SPEC §3.
- **Story Analyzer** — structured output (`json_schema`, strict) + Pydantic. Entity + coreference extraction tolerant of messy kid text, including light Taglish code-switching.
- **Scene Segmentation** — select up to 10–15 scenes; **floor behavior** for short stories (≥3, never invent content).
- **Character Bible + canonical reference image** — ≤2 canonical characters in the fixed style.
- **Style Presets** — author three style fragments once (config, not a module). Chosen before the canonical
  reference is generated; frozen for the storybook. Story Memory carries `style.style_preset_id` (ADR-022).
- **Prompt Optimizer** — scene + character bible + style constant + story memory → structured prompt.
- **Image Generator** — reference-conditioned Qwen-Image-Edit calls.
- **Consistency Checker (VLM-as-judge)** — prompted `gemma-3-27b-it` via `providers.judge()`.
  **Reason-then-score field order** (ADR-004 amendment). The *fine-tuned* judge arrives in Phase 2.5.
- **Regeneration controller** — one targeted, prompt-corrected retry using the judge's failure reasons;
  best-of fallback; capped. The **failure-reason taxonomy** it consumes is the same closed set the
  annotators will use in Phase 2.5 (ADR-018) — design it once, here.

**Exit criteria:** A clean multi-scene, multi-character story produces a coherent, character-consistent storybook, and you can point to a case where the VLM-judge caught an off-model image and the targeted retry fixed it. Traces show per-scene verdicts, regen counts, and cost.

**Gate → Phase 2:** the exit criteria above, **plus** probe 4 green and the worker's RAM headroom checked.
The failure-reason taxonomy is frozen here — extending it after Phase 2.5 labelling starts invalidates
every collected label (ADR-018).

**⚠️ Highest-risk phase**, and note the sequencing trap: this exit criterion depends on the *prompted*
judge. If it is weak, the fine-tune (Phase 2.5) arrives too late to rescue Phase 1. ADR-010's best-of
fallback means Phase 1 wobbles rather than collapses.

---

## Phase 2 — Safety, Classroom & Robustness *(~3–4 weeks)*

**Goal:** safe for a real child in a real classroom, and survives messy input.

**Entry:** probe 4 green (§0.5). **Check the worker's RAM tier now, not at the end** — see the warning below.

- **Moderation stack:** input text (Qwen3Guard-Gen on the worker + `gpt-oss-safeguard-20b` OpenRouter backstop, ADR-011c) → PII redaction (Presidio)
  → output image moderation (NSFW ViT on CPU + VLM safety rubric) on every image **including the canonical
  reference before reveal**. The open image model ships **no built-in safety filter** and the proprietary
  backstop is gone — this gate is load-bearing (ADR-011).
- **Filipino PII recognizers** — custom Presidio recognizers for Filipino names, `Barangay`/`Purok`/`Sitio`
  address structure, and `+63 9xx` mobile formats. **Not a polish item**: the stock configuration leaks the
  exact case ADR-011 calls expected. A small, reusable, publishable artifact in its own right.
- **Model self-refusal fallback** (soften-and-retry → gentle reframe).
- **Length guard** — word cap + truncate-at-scene-boundary (no summarization); repeated-failure off-ramp (N=3).
- **Auth & classroom** — Supabase Auth (teacher/owner) + classroom + student profiles + **RLS policies**
  (classroom isolation). Signed URLs. *(ADR-017 — supersedes ADR-006's role model.)* Add the **`researcher`
  role** here, while the role model is open: it is one enum value now, and a reopened auth decision in
  Phase 2.5 otherwise (ADR-026).
- **Teacher dashboard/library** + **teacher review gate** before a book enters the gallery or is exported.
- **Classroom sharing** — teacher-curated, display-only gallery of approved storybooks (ADR-021).
- **Story Map** — read-only page over Story Memory. No new models.
- **Narration** — expressive TTS (Chatterbox, hosted on fal.ai) pre-rendered per page onto Storage; Kokoro-82M CPU fallback (ADR-020, revised).
- **Export** — HTML template → PDF (Playwright/WeasyPrint).
- **Rate limiting** (`slowapi`) + per-profile daily cap + cost circuit-breaker.
- **Data deletion path** for the teacher/owner.
- **Kid-flow polish** — cartoon-pop components, Lottie wait states, kid-appropriate failure states.

**Exit criteria:** A stranger's child could use the happy path safely; messy/short/over-length/mild-peril
stories all degrade gracefully; a teacher can sign up, see only their own classroom, approve a book into
the gallery, export a PDF, and delete data. Probe 4 (Filipino moderation) is green.

**⚠️ Worker RAM.** Presidio+spaCy, the NSFW ViT, and the CPU text gate are resident in one
container (~2–3 GB). Check the plan tier at the *start* of this phase, not the end.

---

## Phase 2.5 — Judge Fine-Tuning *(~1.5–2 weeks; gated on Phase 1 output)*

**Goal:** an open, fine-tuned consistency judge that (i) improves over its own zero-shot base — the
research gate — and (ii) is **non-inferior to the prompted incumbent within δ = 3 F1** — the product gate
that decides whether it ships (ADR-018 amendment a; the older "beats the prompted incumbent" one-liner is
superseded). Plus a results table that survives a hostile question. Its **precision/recall/F1 against
human labels (F1 primary) is Objective 4 — a formal, reported research finding**, not a descriptive-only or
build-gate-only number; an optional secondary comparison against the zero-shot base and prompted baseline
may be reported alongside it (ADR-008, revised 2026-07-25). Full recipe: `docs/specs/judge-finetune.md` — **start at its §0, which is
the step-by-step order of operations.**

**The product is finished before this phase starts.** Phases 1–2 ship with the *prompted* judge; this phase
swaps one replaceable part. If it fails its gate, nothing else changes.

- **Data.** There is **no dataset to download** — it is manufactured from Phase 1's own output over the
  Stage-1 corpus (**15 stories collected → 10 primary + 5 backup**, Grade 5–6, Matina Aplaya Elementary
  School — RESEARCH_PROTOCOL §8). Positives are **human-confirmed** by the researchers; auto-labelling them
  trains a detector for *"was a reference used?"*. Hard negatives are constructed for free and go into
  **train only**. Rationales are a **fixed checkbox taxonomy**, never model-generated. Splits are
  **character-disjoint** (train / validation / held-out test), test stratified human vs. non-human and
  oversampled. Two annotators, IRR reported. ⚠️ Exact per-split character/image counts are a planning
  target owned by `docs/specs/judge-finetune.md` and need revisiting against the reduced 15-story corpus —
  they are not restated here.
- **Annotation surface** (`docs/specs/annotation-surface.md`, ADR-026) — `frontend/app/(research)/annotate/`
  and `adjudicate/`, behind the Phase-2 `researcher` role. One blinded pair at a time (opaque IDs, shuffled
  order), the frozen 7-item taxonomy, resumable across sessions. Labels land in a new **`annotations`** table
  whose RLS stops one annotator reading another's rows — independent labelling under a policy rather than a
  promise. **This supersedes `judge-finetune.md` §5's `labels/*.csv`**; `build_dataset.py` reads the table.
  It is built *before* labelling starts, not alongside it — ~1500 rows of silent spreadsheet misalignment is
  undetectable after the fact and would invalidate Objective 4.
- **Pre-register the analysis plan before a single label is collected.** **Two gates, not one**
  (ADR-018 amendment a). *Research gate (did the fine-tune work):* held-out ΔF1 on `different_character` vs. **zero-shot
  Qwen2.5-VL-7B**, 95% CI excluding zero, McNemar + bootstrap **clustered by character**. *Product gate:*
  non-inferiority to prompted Gemma-27B within δ = 3 F1, no recall regression. Claim ladder A/B/C/D declared
  in advance; **only rung D fails, and rung D is a bug.** Both gates are **build/deployment** decisions,
  separate from Objective 4 itself: Objective 4 reports the fine-tuned judge's precision/recall/F1 against
  human labels (F1 primary, IRR on the human labels, held-out set read once) as a formal research finding;
  the optional base/prompted comparison may be reported alongside it (ADR-008, revised 2026-07-25).
- **Train.** `Qwen2.5-VL-7B-Instruct` + QLoRA via LLaMA-Factory, on a rented 4090 (~$5–15, 1–2 hours,
  ≥3 seeds). W&B for runs. Output is a ~tens-of-MB **LoRA adapter**, not a model.
- **Evaluate.** Four baselines: zero-shot Qwen2.5-VL-7B, prompted Gemma-3-27B, CLIP cosine, DINOv2 cosine.
  Metrics: κ vs. human **split by human/non-human character**, F1 on `different_character`, AUROC, latency, cost.
- **Transfer-test** on DreamBench++ — **evaluate only, never train on it, never redistribute it.** Evaluation
  is the benchmark's intended use, so no permission is needed. No off-the-shelf training set exists for this
  task; that absence is a paper claim (`judge-finetune.md` §5.1).
- **Serve** behind vLLM on Modal, scale-to-zero (ADR-019). `JUDGE_BASE_URL` + `VLM_JUDGE_MODEL` is the whole
  change — no code. Rollback is the same two variables.

**Exit criteria:** the results table exists and is honest, and the held-out set was read exactly once.
**Gates:** rung A or B ships the fine-tuned judge. **Rung C is still a fine and reportable outcome** —
fine-tuning worked, the gap to a prompted 27B did not close, the product keeps the prompted judge and
ADR-019 is dropped. Rung D means the LoRA did nothing: a bug, not a result. The ladder is a **deployment**
ladder (ADR-008, revised 2026-07-25): it decides what ships, not what the paper reports — Objective 4
reports the fine-tuned judge's precision/recall/F1 against human labels either way, so no rung is an
embarrassment to write up.

**Blocked on:** Ethics Stage 1 → corpus → Phase 1 run over the corpus. **Do not label before Phase 0.5
passes** — the judge learns the drift signature of the image model that drew its training images, so a
substrate swap invalidates the weekend.

---

## Phase 3 — Evaluation Instrumentation & Study *(~3–4 weeks; overlaps the ethics window)*

- **Functional verification matrix (Objectives 1–2, Tool A)** — per-stage pass/fail success rates across the
  six functional categories, `Successful ÷ Total × 100`, computed by an **offline script over tracing
  exports** (`docs/specs/functional-verification-matrix.md`; no dashboard and no new table — ADR-026).
  A Pass means *the stage emitted valid output*, **never** *the judge approved it* — scoring outputs with the
  judge would break non-circularity (ADR-004). It runs on **fixture stories**, so it carries no ethics load
  and is valid October-defense material.
- **Expert-validation harness (Objective 3)** — the Dean/Professor of the Arts College, one Arts
  student/intern, and one Education student/intern respond to a written, open-ended interview form
  (Tool B); responses coded positive / negative / suggestion per criterion (narrative coherence,
  story faithfulness, visual presentation, visual style consistency, classroom suitability) via content
  analysis (ADR-008, RESEARCH_PROTOCOL §5). Stimuli are served by
  `frontend/app/(research)/books/` — provenance stripped, order shuffled per validator, so blinding holds in
  code rather than by discipline (ADR-026). The **responses themselves stay on paper**: the instrument is
  open-ended prose, not a form.
- **Story corpus** assembled from **Stage-1 story donation** (below): 15 stories collected → 10 primary +
  5 backup, provenance documented.
- **Software-quality harness (Objective 5)** — ISO/IEC 25010 questionnaire (Tool C), five
  characteristics, 5-point Likert, weighted mean + SD, administered to **designated software-quality
  evaluators** (IT practitioners and teachers) — never to the expert validators (RESEARCH_PROTOCOL §6).
- **Metrics export** — generation time, image/regen counts, cost from tracing. Objective 4's
  precision/recall/F1 is computed in Phase 2.5, against the judge's held-out set.

**Exit criteria:** one full expert-validation session (Objective 3) and one full ISO/IEC 25010 session
(Objective 5) end-to-end, and a clean metrics table.

---

## Phase 4 — Future Work *(named in the paper; built only if time allows)*

Kid-uploaded reference; **more** art styles beyond the three (ADR-022 ships three in v1); multi-language;
**"what happens next?" continuation** (cross-story character reuse); public sharing *(see ADR-017 — this one
is deliberately never built)*.

Reachable rather than hypothetical, because v1 already runs on open weights (ADR-015):
- **On-device / privacy-preserving generation** — the only version that can claim "the child's text never leaves the device." v1 cannot.
- **Style LoRA** — if and only if raters flag style drift (ADR-016 trigger (b)). ~$1–10, one-time.
- **Taglish story-analyzer fine-tune** — attractive and locally grounded; competes for the same budget (ADR-018).
- **Watermark / provenance** — C2PA Content Credentials + `invisible-watermark`, replacing the SynthID capability lost with Nano Banana. A real gap, not a solved substitution.

---

## Parallel track (Day 1 → study) — Ethics & Research

**The ethics submission is split in two (ADR-008 amendment a).** The original single submission created a
hidden dependency: the corpus is real child writing, and the Grade 5–6 learners who write it are the only
respondent group requiring guardian consent. Separating their low-risk story-donation role from any
evaluation role keeps the corpus — and everything downstream of it — from stalling on a heavier review it
doesn't need.

**Stage 1 — story donation.** Children write stories. They never touch the system, never see each other's
work; we collect anonymized text and nothing about the child. Narrow, low-risk, comparatively fast.
**The consent form must state that donated stories may be used to build and evaluate an AI model** —
training on participant data without that clause is a violation, and it costs one sentence.
*Unblocks:* the corpus → Objective 3's evaluation stimuli → the judge's training labels (Objective 4).

**Stage 2 — system use.** Children use StoryBuddy and read classmates' books in the display-only gallery.
Interactive, peer-visible, child-authored content (their own storybook). A heavier review. *Gates:*
in-classroom system use only — no evaluation leg (Objectives 3–5) depends on it.

**File Stage 1 immediately.** Guardian informed consent **and** age-appropriate child assent are required
for both stages regardless of who owns the account (**Data Privacy Act of 2012, Republic Act No. 10173**).
Removing parental controls from the product did not remove parental consent from the research; adding peer
sharing made Stage 2 heavier.

**Recruitment and locale.** Stories are collected at **Matina Aplaya Elementary School**, from qualified
Grade 5–6 learners. Expert validators (Objective 3) and the designated software-quality evaluators
(Objective 5) are recruited through **Holy Cross of Davao College (HCDC)**, Davao City, Philippines —
where system development and evaluation take place.

**Corpus insurance.** If Stage 1 slips, the evaluation stimuli fall back to researchers writing
deliberately as ten-year-olds, or a public children's-writing dataset. **Survey what public
child-narrative corpora actually exist before assuming one does** — one researcher, one day. Many
candidates turn out to be L2-learner essays or published books, not child writing.

---

## Dependency map (what blocks what)

```
Phase 0 skeleton ──► Phase 0.5 spike ──► Phase 1 pipeline ──────────────────────────┐
       │                   │                                                        │
       │                   └── seed determinism ──────────────► (CC-7)              │
       └──► Phase 2 safety + classroom ─────────────────────────────────────────────┴──► Phase 3 study

Ethics Stage 1 ──► story donation ──► CORPUS ──┬──► Objective 3 (expert validation)  ← carries the capstone
                                               │
                                               └──► Phase 1 run ──► images ──► human labels ──►
                                                    Phase 2.5 fine-tune ──► gate ──► serve or don't (Objective 4)

Ethics Stage 2 ────────────────────────────────────► classroom system use  ← gates no evaluation leg
```

Two edges nobody draws, and they are the two likeliest ways the schedule dies:

1. **corpus → Objective 3.** Expert validation carries the capstone and cannot start without stories.
2. **corpus → images → labels → fine-tune.** The fine-tune is four hops downstream of an ethics form.
   Everything after `images` is a weekend; everything before it is months. **File Stage 1 first.**

---

## De-scope ladder (decide now, not at 2 a.m. in month three)

| Order | Cut | What you lose |
|---|---|---|
| 1 | "What happens next?" continuation | Nothing the research needs |
| 2 | Story Map | An author-facing mirror |
| 3 | PDF export | The out-of-container escape hatch; slideshow still works |
| 4 | **Fine-tuned judge *ships*** → evaluate it offline instead | The "faster, cheaper product" claim. **Objective 4 survives** — the judge is still evaluated against human labels, just not served in production. Modal disappears (ADR-019) |
| **Never** | Phase 0.5, Objective 4's judge evaluation, the moderation stack | The project — the judge evaluation is Objective 4's classification-performance leg and the moderation stack is non-negotiable. (Objective 4 is a formal reported objective — precision/recall/F1 against human labels, F1 primary, with an optional secondary comparison — not a build-gate-only or descriptive-only measure; ADR-008, revised 2026-07-25.) |

---

## Schedule risk flags

- ~~**Non-human character consistency is the top risk and it is still unverified.**~~ **Retired
  2026-07-29.** Probe 1 ran: the invented non-human character held identity on 80% of pipeline-ON items
  and separated +50 from the control. The residual risk is narrower and inverted — the *pooled*
  separation gate failed (+25 vs ≥30) because the **easy** character shows zero separation, so ADR-007's
  mechanism is unproven on subjects the model already knows. That is a measurement/limitation problem,
  not a substrate risk.
- **Ethics latency, now with no participant access started.** The Stage-1/Stage-2 split is the mitigation.
  Nothing else compresses it.
- **The corpus gates Objective 3 (expert validation).** See the dependency map.
- **Phase 1 is still the crumple zone.** If judge quality is weak it eats time, and the fine-tune is too
  late to help. Best-of fallback (ADR-010) keeps "imperfect but shippable" always available.
- **Seed determinism** fails silently at Phase 3, months after provider choice. Probed in Phase 0.5.
- **Image moderation carries more weight than it used to.** No built-in filter, no proprietary backstop.
  Under-scoping it is a safety bug, not a polish item.
- **Phase 2 is much larger than the old "week 4."** Classroom auth, sharing, teacher gate, Filipino PII,
  and narration all landed in it.
- **At 3 months, the de-scope ladder is not optional.** At 6 months it is insurance.
