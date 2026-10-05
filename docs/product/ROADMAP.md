# StoryBuddy — Implementation Roadmap

**Approach:** Walking skeleton → vertical slices → hardening. Riskiest assumptions first.
**SDLC:** Boehm's Spiral Model — each phase below is a stage-gated iteration (determine objectives →
identify/resolve risks → develop & verify → plan next iteration); full mapping in
`docs/capstone/methodology.md` §1.2.
**Team:** one developer (build), three researchers (corpus, annotation, study, ethics). The build track
is solo; the research track is not. They run in parallel and meet at Phase 2.5 and Phase 3.
**Companion docs:** PRD v2, ADRs, RESEARCH_PROTOCOL.
**Current follow-up:** [C3 findings and issues #94–#100](#c3-findings-follow-up).

---

## Guiding principles

1. **Prove integration before depth.** The place a schedule dies is integration (async jobs, model wiring, storage). Get one story end-to-end through real infrastructure before making any single module smart.
2. **Riskiest-first.** Validate that the image model holds *your* characters consistent — **especially non-human ones** — and that the VLM-judge actually catches failures, in Phase 0.5, not Phase 4.
3. **Instrument from Day 1.** Langfuse tracing is your research dataset — turn it on in the skeleton.
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
slideshow live via Realtime. Langfuse + Sentry on from the first commit.

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

- **Story Memory contract** — the Pydantic schema. Written first; freezes MASTER_SPEC §3. ✅ **built 2026-07-29** (`feat/story-memory-contract`; `job_state.py` deleted; seven nodes on partial-return; `input_gate` entry point wired).
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

- **Moderation stack:** input text (meta-llama/llama-guard-4-12b on the worker + `gpt-oss-safeguard-20b` OpenRouter backstop, ADR-011c) → PII redaction (Presidio)
  → output image moderation (NSFW ViT on CPU + VLM safety rubric) on every image **including the canonical
  reference before reveal**. The open image model ships **no built-in safety filter** and the proprietary
  backstop is gone — this gate is load-bearing (ADR-011).
- **Filipino PII recognizers** — custom Presidio recognizers for Filipino names, `Barangay`/`Purok`/`Sitio`
  address structure, and `+63 9xx` mobile formats. **Not a polish item**: the stock configuration leaks the
  exact case ADR-011 calls expected. A small, reusable, publishable artifact in its own right.
- **Model self-refusal fallback** (soften-and-retry → gentle reframe) — for the model *declining* a benign
  mild-peril prompt. Distinct from `output_mod`'s soften-and-retry (model complied, classifier flagged),
  which shipped with `moderation-stack`.
- **Length guard** — word cap + truncate-at-scene-boundary (no summarization).
- **Repeated moderation-failure off-ramp (N=3)** — PRD §11.4; its own item, *not* part of the length guard.
  Counts failed revisions **across job submissions**, so it needs a cross-run counter that does not exist
  yet and a revision flow (`kid-flow-ui`) to count. Sequence it after both.
- **Auth & classroom** — Supabase Auth (teacher/owner) + classroom + student profiles + **RLS policies**
  (classroom isolation). Signed URLs. *(ADR-017 — supersedes ADR-006's role model.)* Add the **`researcher`
  role** here, while the role model is open: it is one enum value now, and a reopened auth decision in
  Phase 2.5 otherwise (ADR-026).
- **Teacher dashboard/library** + **teacher review gate** before a book enters the gallery.
- **Classroom sharing** — teacher-curated, display-only gallery of approved storybooks (ADR-021).
- **Story Map** — read-only page over Story Memory. No new models.
- ~~**Narration**~~ and ~~**Export**~~ — **both cut, ADR-058.** Neither was ever built; export invoked
  rung 3 of the ladder below. The accessibility cost of dropping narration is recorded in ADR-058, not here.
- **Rate limiting** (`slowapi`) + per-profile daily cap + cost circuit-breaker.
- **Data deletion path** for the teacher/owner.
- **Kid-flow polish** — cartoon-pop components, Lottie wait states, kid-appropriate failure states.

**Exit criteria:** A stranger's child could use the happy path safely; messy/short/over-length/mild-peril
stories all degrade gracefully; a teacher can sign up, see only their own classroom, approve a book into
the gallery and delete data. Probe 4 (Filipino moderation) is green.

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

**Scheduling update:** C3 labelling has already run while Phase 2 work remains. The product uses the
*prompted* judge until the registered product gate decides whether a fine-tuned judge ships.

- **Data.** There is **no dataset to download** — it is manufactured from Phase 1's own output over the
  Stage-1 corpus (**15 stories collected → 10 primary + 5 backup**, Grade 5–6, Matina Aplaya Elementary
  School — RESEARCH_PROTOCOL §8). Positives are **human-confirmed** by the researchers, except for ten
  owner-approved AI-assisted audit labels disclosed in `PREREGISTRATION_OBJ4.md`; auto-labelling them
  trains a detector for *"was a reference used?"*. Hard negatives are constructed for free and go into
  **train only**. Rationales are a **fixed checkbox taxonomy**, never model-generated. Splits are
  **character-disjoint** (train / validation / held-out test), test stratified human vs. non-human. Two annotators, IRR reported. ⚠️ Exact per-split character/image counts are a planning
  target owned by `docs/specs/judge-finetune.md` and need revisiting against the reduced 15-story corpus —
  they are not restated here.
- **Annotation surface** (`docs/specs/annotation-surface.md`, ADR-026) — `frontend/app/(research)/annotate/`
  and `adjudicate/`, behind the Phase-2 `researcher` role. One blinded pair at a time (opaque IDs, shuffled
  order), the frozen 7-item taxonomy, resumable across sessions. Labels land in a new **`annotations`** table
  whose RLS stops one annotator reading another's rows — independent labelling under a policy rather than a
  promise. **This supersedes `judge-finetune.md` §5's `labels/*.csv`**; `build_dataset.py` reads the table.
  It is built *before* labelling starts, not alongside it — ~1500 rows of silent spreadsheet misalignment is
  undetectable after the fact and would invalidate Objective 4.
- **Analysis plan and amendment.** The original plan was registered before labels; ADR-061 changed the
  base afterward and the postregistration status must accompany every result. **Two gates, not one**
  (ADR-018 amendment a). *Research gate (did the fine-tune work):* held-out ΔF1 on `different_character` vs. **zero-shot
  Qwen3.5-9B** at the ADR-061 pinned revision, 95% CI excluding zero, McNemar + bootstrap **clustered by character**. *Product gate:*
  non-inferiority to prompted Gemma-27B within δ = 3 F1, no recall regression. Claim ladder A/B/C/D declared
  in advance; **only rung D fails, and rung D is a bug.** Both gates are **build/deployment** decisions,
  separate from Objective 4 itself: Objective 4 reports the fine-tuned judge's precision/recall/F1 against
  human labels (F1 primary, IRR on the human labels, held-out set read once) as a formal research finding;
  the optional base/prompted comparison may be reported alongside it (ADR-008, revised 2026-07-25).
- **Train.** `Qwen3.5-9B` + QLoRA via the pinned LLaMA-Factory, on a qualified rented GPU,
  three seeds. The earlier 7B/4090 time, memory and cost estimates do not qualify this 9B run.
  Output is a **LoRA adapter**, not a new base model.
- **Evaluate.** Four baselines: zero-shot Qwen3.5-9B at the same revision, prompted Gemma-3-27B, CLIP cosine, DINOv2 cosine.
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

**Original dependencies:** Ethics Stage 1 → corpus → Phase 1 run over the corpus. C3 has reached
labelling; [#94](https://github.com/Hanseooo/story-buddy/issues/94) and the follow-up below track the
remaining study work. The judge learns the drift signature of the image model that drew its training
images, so a substrate swap before the registered result would change what is being measured.

---

## C3 findings follow-up

This is a provisional work order, not a new architectural decision. Issue bodies and comments hold
the investigation details. Some issue comments predate the [gate recount](../capstone/pipeline-gate-audit-2026-09.md);
use it for current gate semantics. [ADR-061](./adr/ADR-061-qwen3-5-9b-as-the-objective-4-judge-base.md)
amends the Objective 4 fine-tune base to Qwen3.5-9B after labels existed; the trainer/evaluator now
use its pins. Host qualification remains pending under the [research runbook](../capstone/research_runbook.md#qwen35-host-qualification).
Keep generation and the prompted product judge fixed for this result.
Public-trace review and read-only diagnosis on permitted synthetic material can proceed
in parallel. Offline model trials are separate experiments, not changes to the registered corpus.
Use the `C3-01`–`C3-13` labels to refer to these tasks; keep each label with its task if rows move.

| When / dependency | Work | Gate before moving on |
|---|---|---|
| **C3-01** · Dataset review complete 2026-09-30 | The registered freeze preserves all annotated pairs. A separately named exploratory freeze omits 16 disputed Same-labelled synthetic training pairs under the owner's decision; it changes no validation or test pair. Each selected scene image had one character pair, and the exploratory training manifest retains no natural or constructed pair using those images. The ten agreed-pair audit rows and AI assistance are disclosed in the pre-registration. | The [research runbook](../capstone/research_runbook.md#dataset-handoff-2026-09-30) records the two freeze hashes, counts and validation/test equality. Keep both freezes and the source images and labels for audit. |
| **C3-02** · Next, Objective 4 | The training/evaluation code is aligned with pinned Qwen3.5-9B under [#94](https://github.com/Hanseooo/story-buddy/issues/94) and the dated ADR-061 protocol amendment. The [canonical qualification status](../capstone/research_runbook.md#qwen35-host-qualification) records the preprocessing, learned-update and synthetic base/adapter contract evidence. Next complete [full-run readiness and cost preparation](../capstone/research_runbook.md#full-run-readiness-and-cost-assessment-2026-10-02), approve the actual training host, then run three seeds on the registered freeze. Select checkpoints using validation only; run the held-out primary and ambiguous-reference sensitivity analyses and guide-boundary comparison once under the access rule. Keep any run on the 16-pair filtered freeze exploratory and separately named. | Confirm governance and third-party processing approval before upload; record host/tool qualification and spend alarm. Follow the [agent evidence-capture reminders](../capstone/research_runbook.md#agent-reminders-and-capture-status), including owner screenshots and verified backup before instance deletion. Report the postregistration base change and AI-assisted labels as limitations. |
| **C3-03** · Now, parallel safety check | Public trace links are intentional: the owner plans to show one to the defense panel. Show a synthetic-story (`syn-*`) trace there, never a donated child's (recommended 2026-10-06). The [one-trace cross-check](../capstone/pipeline-gate-audit-2026-09.md) found raw story text in Langfuse state; the worker calls `set_trace_as_public()` for that trace. Verify the public view and choose a redaction or projection boundary in a dedicated ADR session while read-only judge diagnosis continues on permitted material. | A trace shared by URL exposes only approved, redacted research fields; verify this on the actual public view without exposing a child's story in the review record. |
| **C3-04** · Now, read-only | Audit the actual reference and scene gates before changing prompts or models. The [C3 gate audit](../capstone/pipeline-gate-audit-2026-09.md) separates draw attempts from selected images and `matches_description` from reference acceptance. Its live trace confirms capped failed-page selection; Fal screenshots make `s3`'s `wrong_body_feature` rejections review candidates and show invented lettering as a separate generator artifact. Compare full-size attempts with canonical references, then blindly review a preselected synthetic sample to classify false accepts and false rejections. Status 2026-10-06: the 28-image synthetic sample has a provisional AI review awaiting the owner's independent check; a [selected-page lettering screen](../capstone/pipeline-gate-audit-2026-09.md#selected-page-lettering-screen--2026-10-06) found `text_free` flags half its sampled positives wrongly and missed none, n=16, not a rate. | Report denominators, model/prompt/code versions, and human-checked error types. A failed verdict alone is not a bad image; a screenshot alone cannot establish a false rejection. |
| **C3-05** · After Objective 4, with read-only diagnosis possible earlier | Investigate references that add faces against descriptions [#99](https://github.com/Hanseooo/story-buddy/issues/99) and miss stated part counts [#100](https://github.com/Hanseooo/story-buddy/issues/100) on permitted synthetic material. The 21/79 mismatch count is a manual screen, and the [gate recount](../capstone/pipeline-gate-audit-2026-09.md) does not establish visual accuracy. Separate unsupported descriptions, generator misses, judge misses, and the capped best-of policy that can ship a failed reference. | Controlled rates for each failure stage before choosing a prompt or model. Preserve ADR-056's measured count limitation. |
| **C3-06** · After Objective 4 | For [#95](https://github.com/Hanseooo/story-buddy/issues/95), check affected descriptions and count existing hair entries; unstated hair length/style may leave mixed references. Then test whether a prompt-only `body_features` change improves reference and page agreement, without inferring appearance from names or assigning hair to hairless characters. | Report human-checked before/after rates on a fixed sample; a prompt change is a tested option, not an assumed fix. |
| **C3-07** · Before the next corpus campaign | For [#96](https://github.com/Hanseooo/story-buddy/issues/96), compare reference review before pages with review after generation. The product reveal pauses for human review, while `build_corpus` auto-confirms it. Define the rejection rule and estimate review effort, retries, spend, and false rejections. The existing 21/79 screen establishes defect prevalence in that corpus, not how well a live reviewer would detect defects. | The chosen process and observed review/rejection counts are recorded; the already-generated C3 corpus is handled through #94. |
| **C3-08** · After Objective 4, if stories require a visual transformation | Investigate [#97](https://github.com/Hanseooo/story-buddy/issues/97) jointly with #99; neither proposed change ships alone. Check each story for an actual change of form; speech or emotion alone does not establish one. Before a schema or gate change, decide canonical form, scene-state precedence over reference conditioning, and which identity checks stay active in a dedicated ADR session. | A visual probe and deterministic gate cases cover transformed and unchanged characters, including both in one scene; measure false scene states because they could disable identity checks. |
| **C3-09** · After Objective 4 for any additional product-judge investigation | The 2026-09-30 small Gemma/Qwen3.5 two-image pilot is recorded below; it was exploratory and did not establish task superiority. ADR-061 has now selected Qwen3.5 as the amended **fine-tune base**, so no additional provider model-selection campaign gates training. A later human-checked synthetic gate audit may compare reference-to-description and scene identity/constraint failures separately before a product-judge change. Do not use the Objective 4 held-out set to choose a product model. | Report human-checked false accepts/rejections, failure types, malformed outputs, latency, provider, prompt version and spend. Any further paid screen needs its own approved cap. |
| **C3-10** · After failure-stage audit, offline image-model screen | Against the current `fal-ai/qwen-image` reference and `fal-ai/qwen-image-edit-2511` scene-edit baselines, test Apache-2.0 [FLUX.2 klein 4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) on both legs. Use the `fal-ai/flux-2/klein/4b/base` endpoints: the distilled `klein/4b/edit` has no `negative_prompt`, fal silently drops it, and `NEGATIVE_PROMPT` is the only lettering ban (`providers.py`), so that arm would not be a fair comparison. A new edit endpoint also needs a `REFERENCE_FIELD` row. Test [Qwen-Image-2512](https://huggingface.co/Qwen/Qwen-Image-2512) on reference generation only ([fal endpoint](https://fal.ai/models/fal-ai/qwen-image-2512/api)). Use the same permitted synthetic stories and stratify scenes by zero, one, or two character references; do not mix new-model images into the registered Objective-4 corpus. Licences, fal prices (baseline ~USD 0.42�0.49 per book), reference caps and unverified billing details are in the [2026-10-06 desk research](../capstone/image-model-research-2026-10.md); it found no published cross-page identity evidence for any candidate. | Blindly score identity, story details, anatomy, invented lettering/artifacts, safety, retries, latency, and total cost per completed book. Verify reference-count support, negative-prompt parity, input-image billing and how each endpoint reports a safety flag (HTTP 422 vs. a black image; the code recognises only 422); set a spend cap. Any new image distribution requires rechecking the judge before a product swap and its ADR. |
| **C3-11** · After Objective 4, if upstream text errors remain | Compare the current Mistral text model with one open-weight reasoning candidate, starting with `analyze` and `segment` separately. `prompt_optimizer` is deterministic. `qwen/qwen3.6-35b-a3b` is a documented candidate, not a selected model; first prove actual-provider reachability, strict JSON/Pydantic output, and acceptable latency. Then compare story-grounded visual facts, invented attributes, roster and scene assignments on fixed synthetic stories before paying for paired images. | A text-model change needs a measured story-level and image-level benefit; do not use the Objective-4 held-out result for selection. |
| **C3-12** · After the amended judge result | Apply `PREREGISTRATION_OBJ4.md`'s fine-tuned Qwen3.5-9B versus prompted Gemma-3 product gate. Before any deployment, qualify LoRA serving and the production two-image schema on the selected host. Keep safety moderation independent. Further product-model or generator changes require separate measured decisions and ADRs; do not use Objective 4's held-out set for selection. | The amended Objective 4 result and product gate are reported with their postregistration status. A passing product gate and serving qualification are both required before a production swap. |
| **C3-13** · Last, after Objective 4 | Trial pixel art [#98](https://github.com/Hanseooo/story-buddy/issues/98) against an existing style on the same stories, including whether small identity details remain judgeable. | Approve the paid trial's spend first; a style change needs its own measured decision and ADR. |

The [2026-09-30 exploratory C3-09 provider pilot](../capstone/pipeline-gate-audit-2026-09.md#c3-09-exploratory-provider-pilot--2026-09-30)
used stored synthetic training labels only. It does not close C3-09's human-checked
reference and page audit or change the registered Objective-4 model plan.

`DECISION_BACKLOG.md` remains the queue for undecided architectural questions, not for these
investigations. If #97, #96, or a model trial reaches such a decision, log that question there
for its own session.

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
| 3 | ~~PDF export~~ — **taken 2026-09-04 (ADR-058)** | The out-of-container escape hatch; slideshow still works |
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
- **Phase 2 is much larger than the old "week 4."** Classroom auth, sharing, teacher gate, and Filipino PII
  all landed in it. Narration and export did too, until ADR-058 cut both.
- **At 3 months, the de-scope ladder is not optional.** At 6 months it is insurance.
