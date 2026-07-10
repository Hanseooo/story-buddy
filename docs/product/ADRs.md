# StoryBuddy — Architecture Decision Records

Each ADR is intentionally short and revisitable. Format: Status · Context · Decision · Consequences · Alternatives.

---

## ADR-001 — Image generation model: Qwen-Image-Edit (open-weight, hosted inference)

**Status:** Accepted · **revised 2026-07-10** — supersedes the original Nano Banana decision. Driver: ADR-015.

**Context:** The core research problem is character consistency across scenes, **including non-human characters**. This is the module every other module depends on. Budget is small; timeline is ~1 month solo.

The original decision (Nano Banana / Gemini 2.5 Flash Image) is precluded by the open-weight mandate (ADR-015). Its rejection of open-source also rested on a premise that **no longer holds**: in 2024-era tooling (SDXL + IP-Adapter / InstantID), identity preservation on stylized or non-human characters did require per-character LoRA training. Reference-conditioned *editing* models now perform training-free multi-image identity transfer natively — the exact mechanism this pipeline already assumes (ADR-007).

**Decision:** Use **Qwen-Image-Edit (2509/2511 line)** — Apache-2.0, accepts 1–3 reference images — via **hosted inference on fal.ai** (Novita and Replicate are drop-in alternates). Condition every scene on the auto-generated canonical character reference. **The image model is never fine-tuned** (ADR-016's identity and style reasoning survives ADR-018, which fine-tunes the *judge* instead).

**Consequences:**
- Weights are open, so self-hosting is always *available* and never *required* (ADR-015).
- ~$0.02–0.035/image → ~$0.30–0.65/book. Same order of magnitude as before; PRD §15 holds.
- **Infrastructure is unchanged.** The worker calls an HTTP API exactly as it called Gemini. ADR-005, ADR-006, and ADR-009 are untouched.
- ⚠️ **Non-human / stylized identity preservation is unverified for this model — and for every candidate.** No published benchmark splits identity similarity by human vs. non-human subject. This is now the project's single largest technical risk. Retired by the **Phase 0.5 spike** (ROADMAP) with a pre-committed kill criterion.
- **SynthID is lost.** SynthID-*Text* is open-sourced; SynthID-*Image* is not, and has no drop-in equivalent. This is a genuine capability gap, not a substitution. C2PA Content Credentials + `invisible-watermark` is the layered replacement — **Future Work, not MVP**. Do not claim watermark provenance in the paper.
- **Google's built-in safety filter is lost.** Open image models ship nothing comparable. The output-image moderation gate (ADR-011) is therefore **load-bearing**, not defense-in-depth.
- **Seed determinism is provider-specific** and must be empirically verified, not assumed from docs — it underpins the Phase 3 ablation (CC-7, ADR-008). Probed in the Phase 0.5 spike.

**Alternatives:**
- **FLUX.1 Kontext [dev]** — stronger community reputation for character consistency. Its license is **non-commercial**, which is acceptable here because StoryBuddy is academic and will not be commercialized (ADR-015). **Designated fallback if the Phase 0.5 spike fails.**
- **FLUX.2 [klein] 4B** — Apache-2.0, multi-reference, faster and cheaper. Second fallback; unproven on non-human identity.
- **Adapter stacks — rejected on license grounds.** InstantCharacter, DreamO, UNO, and ACE++ ship permissive-looking wrapper licenses over a **FLUX.1-dev base whose non-commercial terms they inherit**. InstantID and PuLID depend on InsightFace's `antelopev2` (non-commercial) *and* are face-embedding based — their own documentation calls animal characters unstable, which this product requires. **Do not adopt one of these by accident**; the wrapper license does not override the base.
- **Per-character LoRA / DreamBooth** — rejected on *latency*, not cost. See ADR-016.
- **Nano Banana** (the original decision) — precluded by ADR-015.

---

## ADR-002 — Text/orchestration + VLM judge: open-weight models via OpenRouter

**Status:** Accepted · **revised 2026-07-10** — supersedes the original Gemini decision. Driver: ADR-015.

**Context:** Story analysis, segmentation, prompt-building, and the VLM-judge need a capable LLM/VLM with **reliable structured output**. The open-weight mandate (ADR-015) rules out Gemini. Serving open weights ourselves is rejected in ADR-015; we need an aggregator that fronts many open models behind one OpenAI-compatible API so a model swap is a config change.

**Decision:** Use **OpenRouter**. Text pipeline nodes: **`qwen/qwen3-32b`**. VLM judge: **`google/gemma-3-27b-it`**. Fallbacks, pre-vetted for structured-output support: `openai/gpt-oss-20b` (text, Apache-2.0) and `qwen/qwen3-vl-32b-instruct` (judge).

**Consequences:**
- ⚠️ **OpenRouter's structured-output support is per `(model, provider)` pair, not per model.** A routed provider that lacks it silently downgrades `json_schema` to loose `json_object` mode. **Always send `provider.require_parameters: true`**, and re-query `GET /api/v1/models?supported_parameters=structured_outputs` before implementing — the list changes. Without this, the Pydantic boundary (CLAUDE.md §2) is the *only* thing standing between a malformed response and the pipeline.
- OpenRouter is OpenAI-compatible, so LangSmith tracing (ADR-014) works unchanged.
- Swapping a model is an env-var change; swapping the *provider* is one file (`backend/providers.py`).
- **The child's text still leaves our infrastructure** (OpenRouter → upstream host). PII redaction (ADR-011) remains load-bearing. This ADR does **not** deliver a privacy guarantee — see ADR-015.
- ~~Read-aloud captions use the browser's Web Speech API.~~ **Superseded by ADR-020** — Kokoro-82M,
  pre-rendered on the worker. Consistent voice on classroom hardware; still zero cost, still open.
- The **judge's endpoint** is no longer necessarily OpenRouter. After Phase 2.5 it is a self-hosted vLLM
  server (ADR-018, ADR-019), reached through the same OpenAI-compatible client. `JUDGE_BASE_URL` decides.

**Alternatives:**
- **DeepSeek** — rejected: no vision model on OpenRouter, so it cannot serve the judge role.
- **InternVL3, Pixtral, GLM-4.5V/4.6V, Llama 4 Maverick** — rejected: no structured-output support on OpenRouter as of 2026-07.
- **Llama 4 Scout** — works, but Meta's Community License is not OSI-approved. Available if needed; prefer Apache-2.0.
- **Self-hosted Gemma/Qwen** — rejected in ADR-015 (ops burden on a solo build; no GPU on Railway).
- **Gemini** (the original decision) — precluded by ADR-015.

---

## ADR-003 — Pipeline as a deterministic LangGraph state machine (not an autonomous agent)

**Status:** Accepted

**Context:** The pipeline is a fixed sequence with only two real branch points (moderation pass/fail, consistency pass/fail). An autonomous "orchestrator agent" that decides routing adds nondeterminism, cost, and debugging difficulty, and harms research reproducibility.

**Decision:** Model the pipeline as an explicit **LangGraph state machine** with defined nodes and conditional edges only where genuinely needed. Call model APIs directly through `backend/providers.py` — no agent framework in between.

**Consequences:** Deterministic, debuggable, reproducible (matters for the ablation). Built-in checkpointing (see ADR-005). No autonomous-agent overhead.

**Alternatives:** Autonomous agent orchestrator — rejected (nondeterminism, cost, reproducibility). Plain Python without LangGraph — viable but loses checkpointing/persistence and graph structure for free.

---

## ADR-004 — Consistency via VLM-as-judge control loop; human ratings as headline metric

**Status:** Accepted · **amended 2026-07-10** (judge model + verdict schema) · **amended 2026-07-10b**
(the judge is fine-tuned — ADR-018; the safety rubric is not — ADR-011). The decision itself stands.

**Context:** Whole-image CLIP embeddings are dominated by background/pose/scale and degrade on stylized and non-human characters — unreliable both as a control signal and as an eval metric. Using the same automated score to drive regeneration *and* report results is circular.

**Decision:** Use a **VLM-as-judge** (open-weight vision model — `google/gemma-3-27b-it`, ADR-002) as the runtime control signal: given the reference + a generated scene, return a structured verdict (same character? attributes present? style match?) plus **failure reasons**. Use **human ratings as the headline research metric**; report **VLM–human agreement** as a secondary result that validates the automated metric. For multiple characters, verify **each character separately** against its own reference (max 2 canonical refs, v1).

**Amendment (2026-07-10) — reason-then-score verdict schema.** VLM judges are a known-weak instrument for true *instance identity* discrimination: they conflate category and scene similarity with identity (NearID, [arXiv:2604.01973](https://arxiv.org/abs/2604.01973)). The mitigation is established: an explicit rubric plus **reason-then-score** ordering reaches ~79.6% human agreement (DreamBench++, [arXiv:2406.16855](https://arxiv.org/abs/2406.16855)). Therefore the verdict model in `backend/contracts/` **must** order its fields so the judge writes free-text `differences_observed` **before** it emits `same_character`. Field order is load-bearing in structured output — it forces the reasoning to condition the verdict rather than rationalize it.

**Amendment (2026-07-10b) — two calls, two concerns, never merged.** The judge is fine-tuned
(ADR-018). ADR-011's *image safety rubric* currently runs on the same base model, and that
coincidence must not become a coupling. **The fine-tuned model never sits on the child-safety
path.** Consistency is a quality signal with a best-of fallback; safety is a gate with no fallback.
A student-trained LoRA is an acceptable risk for the first and an unacceptable one for the second.

**Consequences:** Robust on non-human/stylized characters; interpretable failures enable *targeted* regeneration (ADR-010); no circularity in the paper; a bonus publishable result (metric validation). The judge is a *signal*, not an oracle — ADR-010's best-of fallback is what keeps a shaky verdict from producing a broken page.

**The non-circularity argument, stated once so it can be cited.** The judge drives regeneration in
the pipeline-ON arm. It is therefore **never** an outcome measure. RQ2's outcomes are *human
consistency ratings* and *reader comprehension* (ADR-008) — neither of which the judge optimizes.
The judge's own accuracy (RQ6) is measured on a human-labeled, character-disjoint held-out set it
never trained on. **RQ2 is never evaluated using the judge.** Panels ask this question; the answer
lives here.

**Alternatives:** CLIP/face-embedding similarity as primary — rejected (fragile here, circular). Retained as *baselines* for RQ6, alongside DINOv2, whose self-supervised features are a stronger instance-identity signal than CLIP's (ADR-018).

---

## ADR-005 — Async job architecture: FastAPI + RQ worker + Redis + LangGraph checkpointing

**Status:** Accepted

**Context:** A storybook takes ~1–3 minutes to generate — impossible inside a request/response cycle. A stall must not re-generate already-good (already-paid-for) scenes.

**Decision:** `POST /storybooks` creates a job row and returns `job_id` immediately. A **separate RQ worker** (Redis broker) runs the LangGraph pipeline, **checkpointing to Supabase Postgres after each scene** (`langgraph-checkpoint-postgres`). Frontend tracks progress via **Supabase Realtime** on the job row. Resumability: a stall at scene N resumes from N.

**Consequences:** A 3-service deployment (web + worker + Redis), not one. Robust, resumable, cost-safe. Free-tier worker spin-down must be avoided before demos/study (keep-warm or paid tier).

**Alternatives:** Celery (heavier), ARQ (async-native; adopt later if concurrency needed), Postgres-backed queue to drop Redis (viable simplification — revisit if Redis feels like overhead). Websockets instead of Realtime — more work for the same result.

---

## ADR-006 — Supabase for Auth + DB + Storage + Realtime

**Status:** Accepted · ⚠️ **the auth *role model* below (parent → kid) is superseded by ADR-017**
(teacher → classroom → student). The platform choice, RLS posture, and everything else stand.

**Context:** Need parent accounts, kid profiles, generated-image storage, live progress, and strict data isolation for a children's product — fast, solo.

**Decision:** Use **Supabase** for Postgres (app data + LangGraph checkpoints), **Auth** (parent accounts; kid profiles as linked rows), **Storage** (images + PDFs via signed URLs), and **Realtime** (job progress). Enforce **Row-Level Security** so a parent can only access their own account's data.

**Consequences:** Large portion of the stack handled by one service; RLS gives DB-layer data isolation (correct design + strong paper point). Vendor dependency on Supabase.

**Alternatives:** Roll-your-own auth/storage — more control, much more work, weaker safety story. Firebase — comparable but less Postgres/RLS-native.

---

## ADR-007 — Style as a fixed constant carried by the character reference

**Status:** Accepted · **amended by ADR-022 (2026-07-10)** — one constant becomes three selectable presets.
The *mechanism* below is unchanged and is the reason presets are cheap: style rides the character reference.
ADR-022 also **removes the optional style-anchor image** on provenance grounds.

**Context:** v1 uses a single fixed art style. Generating a "style bible" per story is unnecessary, and style drift across images is a real risk with text-only prompting.

**Decision:** Author the style **once** as a constant: a hand-tuned prompt fragment + optional fixed style-anchor image. Because the canonical character reference is generated *in that style*, every scene conditions on that reference and inherits **both identity and style**; the style fragment is belt-and-suspenders.

**Consequences:** "Style Bible Generator" collapses into config; character and style consistency ride the same mechanism; cleaner consistency evaluation. Selectable styles become a clean Future Work item.

**Alternatives:** Per-story generated style, selectable styles, fine-tuned/LoRA style — all deferred; unnecessary complexity for a single fixed v1 style.

---

## ADR-008 — Evaluation: comparative ablation, self-sufficient Tier 1, enrichment Tier 2

**Status:** Accepted · **amended 2026-07-10** — adds reader comprehension (RQ5) as a Tier-1 measure
and splits the ethics submission in two. Driver: ADR-017, and the discovery below.

**Context:** Absolute satisfaction scores show the *artifact* is decent but not that the *pipeline* caused it. Child self-report is noisy; ethics clearance for child subjects can slip.

**Decision:** Spine = **blind comparative ablation** (pipeline-ON vs pipeline-OFF, same corpus + seed). **Tier 1 (adults)** carries the core claims and needs no special clearance. **Tier 2 (children)** is enrichment: Fun Toolkit (Smileyometer + Again-Again), a story-fidelity item, and behavioral logging. Use a **real/realistic story corpus** with documented provenance; define **inter-rater reliability** for plot-point annotation.

**Amendment (2026-07-10) — three changes.**

**(a) Tier 1 was not actually self-sufficient.** The corpus must be *real child writing*, and the
children who write it are the same children Tier 2 studies. So Tier 1 was silently blocked on Tier-2's
ethics clearance — the exact dependency this ADR exists to prevent. **The ethics submission splits in
two.** *Stage 1 — story donation:* children write stories, never touch the system, never see each
other's work; we collect anonymized text and nothing about the child. Narrow, low-risk, fast.
*Stage 2 — system use:* children use StoryBuddy, read classmates' books, write reflections.
Interactive and peer-visible; a heavier review. **Stage 1 unblocks the corpus, the ablation, and the
judge's training labels. Stage 2 gates only Tier 2.** Stage 1's consent form **must** state that
donated stories may be used to build and evaluate an AI model — training on participant data without
that clause is a violation, and it costs one sentence to avoid.

**(b) RQ5 — reader comprehension — is added, and it is the outcome variable.** "Does the picture
book transmit the story the child meant to tell?" is measured by giving a reader who has never seen
the story the book alone, then asking them to name the characters and recount what happened, scored
against human-annotated major plot points. **The reader need not be a child**, so RQ5 runs blind on
Tier-1 adults under the same ablation. The peer version — real classmates answering the same
questions inside the app (ADR-021) — is its Tier-2 sibling. Tier 1 still stands alone.

The annotation is nearly free: this ADR already requires human annotation of "major plot points" with
inter-rater reliability, for Story Completeness. **The same annotation is the answer key for RQ5.**

**(c) RQ6 — judge–human agreement — is promoted** from "bonus result" to a reported contribution,
because the judge is now fine-tuned (ADR-018). Its held-out set is character-disjoint and
human-labeled. See ADR-004's non-circularity note: **RQ2 is never evaluated using the judge.**

**Consequences:** Defensible causal claim; capstone survives a Tier-2 delay *for real this time*;
RQ5 turns the sharing feature from a product nicety into the study's dependent variable. The cost is
one extra ethics submission and a comprehension instrument to design. **Do not claim learning gains** —
N ≈ 8–15, no non-illustrated control, no pre/post, no longitudinal window. Prior literature on
authentic audience and publication is the *warrant* for why fidelity matters; it is not a finding of
this study. Overclaiming here is the most likely way the defense goes badly.

**Alternatives:** Single-tier absolute ratings — rejected (no causal claim). Builder-authored clean stories — rejected (measures best-case only); retained only as *insurance* if Stage-1 ethics slips. Asking the author "did it match your intent?" as the fidelity measure — rejected in favour of RQ5: authors know what they meant and will read it into any illustration. A naive reader cannot.

---

## ADR-009 — Hosting: Vercel (frontend) + Railway (backend), Singapore region

**Status:** Accepted

**Context:** Solo dev; a 3-service backend (web + worker + Redis); user base in the Philippines.

**Decision:** **Next.js on Vercel** (SSR for the public landing page). **FastAPI + RQ worker + Redis on Railway**, Singapore (ap-southeast) region. Render or Fly.io are acceptable equivalents; DigitalOcean App Platform is not preferred for the worker+queue shape.

**Amendment (2026-07-10):** ADR-019 adds a **fourth deployment target** — a scale-to-zero GPU
container serving the fine-tuned judge. It is deliberately the *last* thing built and the *first*
thing cut (ROADMAP de-scope ladder); dropping it returns the judge to OpenRouter with an env-var
change and costs only the "faster and cheaper product" claim, not RQ6.

**Consequences:** Good DX; low regional latency; free-tier spin-down must be handled before demos/study.
Worker RAM is now a real budget, not an afterthought: Presidio+spaCy, the NSFW ViT, Kokoro, and the
CPU text gate all resident in one container (~2–3 GB). Check the plan tier before Phase 2, not after.

**Alternatives:** Render (fine), Fly.io (more control/ops), DO App Platform (clunkier here), DO droplet (full control, most ops).

---

## ADR-010 — Regeneration policy: one targeted retry, best-of fallback

**Status:** Accepted

**Context:** Naive regeneration with the same prompt is resampling, not refinement — no reason attempt 2 beats attempt 1 — and every attempt costs money and time.

**Decision:** On a failed consistency check, perform **one regeneration with a prompt corrected using the VLM-judge's failure reasons** (strengthen the missing/incorrect attributes). If it still fails, **keep the higher-scoring image** (best-of), never a broken/placeholder page. Control seeds for reproducibility.

**Consequences:** Retries are meaningful (refinement); bounded worst-case cost/latency (~2 attempts/scene); always a shippable page.

**Alternatives:** Higher retry caps — rejected (linear cost, diminishing returns without correction). Placeholder/skip on failure — rejected (worse kid experience than a slightly-off character).

---

## ADR-011 — Moderation & safety stack (four mechanisms)

**Status:** Accepted · **revised 2026-07-10** — open classifiers become primary · **revised 2026-07-10b**
— the proprietary backstop is removed and replaced with an open one. Drivers: ADR-015 (hardened), ADR-017.

**Context:** Child users require moderation of input and output; a child narrating real life will include PII; the image model itself may refuse legitimate mild-peril scenes. One provider does not cover all of this.

Three things changed. First, the open-weight mandate (ADR-015) applies to safety classifiers too — they are on the child-safety critical path, and a paper claiming an open stack cannot quietly depend on a closed one. Second: **the open image model ships no built-in safety filter** (ADR-001). Google's filter used to be a silent second line of defense behind SafeSearch. It is gone. The output-image gate is now the *only* thing between a generated image and a child.

Third, and the reason for revision **b**: ADR-015 was hardened to *no proprietary models at all*, which
deletes the `omni-moderation-latest` backstop from both the text and the image path. Taken naively that
leaves the text gate standing alone. It also collides with ADR-017: the respondents are **Filipino
children**, and **nobody has published Llama Guard's Filipino or Taglish performance.** A gate that is
both unbacked and unmeasured in the respondents' language is not a gate.

**Decision:** **Two independent open classifiers per path, from different vendors, trained on different
data. Either signal flagging fails the content.** Independence is the property that matters; "open"
and "proprietary" were never the axis — vendor diversity was, and it is achievable without a closed model.

1. **Input text** — **`Qwen3Guard-Gen`** (Apache-2.0, **119 languages**) as primary, with
   **IBM `Granite Guardian`** (Apache-2.0, tops GuardBench) as the independent backstop. Qwen3Guard's
   multilingual coverage closes the Filipino/Taglish hole *by construction*; Granite Guardian's separate
   taxonomy and training data provide the independence `omni-moderation` used to.
   The 0.6B Qwen3Guard variant runs on the worker's CPU. **Verify at build time:** OpenRouter model ids
   for both, and whether the backstop is routable or must also run on the worker.
2. **PII** — **Presidio** redaction on input before storage/captioning/export. **Its default recognizers
   are English/US-centric and will miss Filipino PII**: spaCy NER misses Filipino names, and
   `Barangay`/`Purok`/`Sitio` address structure and `+63 9xx` mobile formats match no built-in pattern.
   *"Ako si Juan dela Cruz, taga Purok 3, Barangay San Isidro"* is the case this ADR calls expected, and
   the stock configuration leaks it. **Custom Filipino recognizers are a Phase-2 deliverable, not a polish item.**
3. **Output images** — on **every** image, **including the canonical reference before the reveal**:
   - **`Falconsai/nsfw_image_detection`** (ViT-base, 86M, Apache-2.0) — a specialist sexual-content gate, runs on the worker's CPU in milliseconds. No new service.
   - **`google/gemma-3-27b-it`** with a safety rubric via OpenRouter — covers violence, gore, and dangerous content, which the NSFW ViT does **not**. Open-weight (Gemma license, not OSI). A separate call with a separate concern — **never the fine-tuned judge** (ADR-004 amendment b).
   - These two are **complementary, not independent** — they cover disjoint categories. True redundancy on the image path is **ShieldGemma 2 (4B)**, and ADR-019's GPU container makes it affordable for the first time (see Alternatives).
4. **Model self-refusal fallback** — soften-and-retry, then a gentle reframe. Unchanged.
5. **Peer reflections are child-authored input** (ADR-021) and route through mechanisms 1 and 2 unchanged. No new surface.

Ordering is unchanged and non-negotiable: input gate → char-ref moderation → output moderation.

**Consequences:**
- No unmoderated generated image reaches a child; PII kept out of stored/exported content; scary-but-innocent stories don't dead-end.
- Both CPU classifiers bundle into the existing worker — no extra service for moderation, no GPU.
- ⚠️ **Both gates are unverified in Filipino and Taglish until the Phase 0.5 moderation probe runs.**
  A miss on a harmful case is a child-safety hole; a miss on a benign case dead-ends a child's dragon
  fight. The probe tests both directions and is a **release gate for Phase 2**, not a curiosity.
- Open image models refuse *less*, so self-refusal (mechanism 4) will fire more rarely while unsafe output is *more* likely. Budget test cases accordingly; do not read "fewer refusals" as "safer."
- The stack is now end-to-end open-weight with zero proprietary dependencies, which is a claim the paper can actually make.

**Alternatives:**
- **Llama Guard 4 12B** — the previous primary. Demoted: Llama Community License (not OSI-approved), English-centric, and beaten by Granite Guardian on GuardBench. Still a usable fallback.
- **ShieldGemma 2 (4B)** — purpose-built image-safety filter, broadest category coverage. Previously rejected because no hosted provider existed and self-hosting a 4B model was a new operational surface. **ADR-019 stands that surface up anyway for the judge**, so ShieldGemma 2 becomes cheap optional hardening on the image path. It must remain *optional*: image moderation may not hard-depend on the GPU container, because the ROADMAP's de-scope ladder allows dropping it.
- **OpenAI `omni-moderation-latest`** — removed. Proprietary (ADR-015, hardened). Its independence is replaced by Granite Guardian, not abandoned.
- **Vision SafeSearch** — dropped: proprietary and paid.
- **LlavaGuard** — research license; unusable.
- **Single-classifier moderation** — rejected. Independence is the whole design; one classifier is one bug away from a child seeing something.

---

## ADR-012 — Story length: hard cap + truncate-at-boundary (no summarization)

**Status:** Accepted

**Context:** Over-length stories must be handled, but AI-summarizing the child's story means illustrating the *summary*, not their narrative — bad experience and an evaluation-validity problem.

**Decision:** **Hard word cap (~500–800 words, tunable)** with a live indicator; if exceeded, **truncate at a scene boundary** with a kid-friendly "let's make a book of the first part." **No silent summarization.**

**Consequences:** Captions and scenes always reflect the child's actual words. Very long stories lose their tail (acceptable; rare for the target age).

**Alternatives:** Auto-summarize — rejected (fidelity + validity). Chunk into chapters — possible Future Work.

---

## ADR-013 — Caption source and PDF export

**Status:** Accepted (caption) · Open (PDF renderer — decide at build)

**Context:** Captions can be the child's words or LLM-rewritten; each generated surface adds a moderation surface and a fidelity risk. Export needs a PDF renderer.

**Decision:** Captions are the **child's verbatim text excerpt** (post-PII-redaction), not rewritten. PDF export renders an **HTML storybook template → PDF server-side** (Playwright or WeasyPrint — pick at build; `@react-pdf/renderer` is the lighter client-side fallback).

**Consequences:** Preserves fidelity; no extra generation/moderation surface for captions. PDF renderer choice deferred to a small build-time spike.

**Alternatives:** LLM-polished captions — rejected for MVP (fidelity + moderation surface); could be an opt-in Future Work toggle.

---

## ADR-014 — Observability provider: LangSmith

**Status:** Accepted

**Context:** MASTER_SPEC §8 flagged the observability provider (LangSmith vs Langfuse) as an
open Phase 0 decision — ROADMAP requires tracing wired from the first commit, and LangGraph
needs a trace destination for per-scene generation time, regen counts, and cost (PRD §16).

**Decision:** Use **LangSmith** for pipeline tracing in the MVP.

**Consequences:** Native LangGraph integration — tracing turns on via environment variables
(`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`) with no additional SDK code
in the pipeline nodes. Free tier is usage-limited; revisit if the study's trace volume exceeds it.

**Alternatives:** Langfuse — open-source, self-hostable, no vendor lock-in, but requires standing
up/administering a second project and more manual instrumentation. Rejected for MVP: solo build,
LangSmith's zero-code LangGraph wiring is the faster and lower-ops path to Day-1 instrumentation.

---

## ADR-015 — Open-weight model mandate: what "open source" means here

**Status:** Accepted (2026-07-10) · **hardened 2026-07-10b** · **drives the revision of ADR-001, ADR-002, ADR-011**

> **Hardening (2026-07-10b).** The project owner has ruled out **proprietary models entirely** — not
> merely as primaries, but as backstops and accessories. An audit of the stack against that rule
> removes exactly two things: **OpenAI `omni-moderation-latest`** (ADR-011's backstop → replaced by
> IBM Granite Guardian, Apache-2.0) and **ElevenLabs TTS** (→ replaced by Kokoro-82M, Apache-2.0,
> ADR-020). Everything else already complies: fal.ai and OpenRouter are *hosted inference of open
> weights*; Modal (ADR-019) is infrastructure; LangSmith and Sentry are services, not models.
> Gemma is open-weight (though not OSI-licensed) and therefore survives this ADR's own definition.
>
> Both replacements are **upgrades**, which is worth recording because it is not the usual outcome of
> a constraint: Qwen3Guard covers 119 languages where Llama Guard's Filipino performance was
> unmeasured, and Kokoro removes a vendor, an API key, and a per-character cost.
>
> A downstream benefit the paper should claim: an open-weight, self-hostable pipeline carries **no
> per-seat vendor cost**, which is the difference between a tool a well-funded private school buys and
> one a provincial public school can run. The mandate arrived as a constraint; it is now part of the
> significance (SDG 4).

**Context:** An external requirement (project supervision) directs StoryBuddy to use open-source
models rather than proprietary hosted ones. The phrase is ambiguous, and **the ambiguity is
load-bearing** — three readings imply three different systems:

1. **Open-weight** — the weights are published; who runs them is a separate question.
2. **Self-hosted** — we run the weights on infrastructure we control.
3. **On-device** — the weights run on the user's machine; their data never leaves it.

Reading 1 costs a model swap. Reading 2 adds a GPU service and its ops. Reading 3 rewrites the
deployment (ADR-005, ADR-009) and is currently listed as Future Work (PRD §5.2).

**Decision:**

- **"Open source" is interpreted as "open weight."** A model qualifies if its weights are publicly
  downloadable under a license permitting our use. **Prefer OSI-approved licenses** (Apache-2.0, MIT).
  Community licenses (Meta, Gemma) are accepted only where nothing better exists, and are named
  as such in the adopting ADR.
- **Hosting is orthogonal to openness.** v1 runs on **hosted inference of open weights**
  (fal.ai for images, OpenRouter for text/VLM). Because the weights are open, **self-hosting is
  permanently available to us and never required** — that availability is what satisfies the mandate.
- **StoryBuddy is academic and will not be commercialized.** Non-commercially-licensed weights
  (the FLUX.1-dev family) are therefore *permissible as fallbacks*, but never as the primary choice,
  so the paper can describe an OSI-clean stack.
- **On-device execution remains Future Work** — but it is now *reachable* rather than hypothetical:
  the same weights run quantized on a 12GB consumer GPU.

**Consequences:**

- ADR-003, ADR-005, ADR-006, ADR-007, ADR-009, ADR-010, ADR-012, ADR-013, ADR-014 are **unaffected**.
  The worker calls an HTTP API; only the URL and the payload change.
- Cost is comparable: ~$60–110/month at 200 books/month, dominated by image generation (PRD §15).
- **We now own three responsibilities Google previously owned:** output-image safety filtering
  (ADR-011), watermark/provenance (a real gap — ADR-001), and seed-determinism verification (CC-7).
- Model access is consolidated behind `backend/providers.py` — four thin functions, one implementation
  each. Swapping a model is an env var; swapping a provider is one file. This is not a plugin framework.
- ⚠️ **This ADR does not deliver a privacy guarantee.** The child's text still transits a third party
  (OpenRouter → upstream host). Do not claim privacy preservation in the paper. That claim requires
  reading 3, which is Future Work.
- The research contribution (PRD §3) is **unchanged**: the contribution is the pipeline, not the model.
  Open weights are an implementation constraint, and a substrate the pipeline should survive.

**Alternatives:**

- **Self-host from day 1** — rejected: relocates rather than removes the GPU dependency (drivers, CUDA,
  cold starts, autoscaling, hardware failure) onto a solo dev with a 1-month build. Railway offers no GPU
  outside its Enterprise plan (ADR-009), so it would also mean a fourth deployment target.
- **On-device / local inference** — rejected for v1: the available hardware is a consumer 8–16GB GPU
  (minutes per image at 1024px, quantized). Fine for prototyping and for demonstrating self-hostability;
  not viable for serving a deployed product or a timed user study.
- **Keep the proprietary stack** — precluded by the mandate.

**Operating assumption (2026-07-10):** the project owner judges that *hosted inference of open weights*
satisfies the requirement, and the build proceeds on that basis. This is **an assumption, not a
supervisor confirmation.** It is cheap to hold and expensive to discover wrong late, so:

- **Confirm it explicitly at the next supervisor checkpoint**, before Phase 2 hardening.
- If it turns out the mandate means *self-hosted*, this ADR is void: the fix is a GPU service and its
  ops (consequences above), and it costs days, not weeks — the pipeline code is unchanged, because
  every vendor call is already isolated in `backend/providers.py`. That isolation is the insurance
  premium for this assumption, and it is why `providers.py` exists.
- If the mandate means *on-device*, the deployment story changes and Phase 4 is promoted. That is a
  scope conversation, not a refactor.

---

## ADR-016 — No fine-tuning in v1

**Status:** ⚠️ **Superseded by ADR-018 (2026-07-10b).** An external requirement now mandates that the
project fine-tune a model. **This ADR is retained, not deleted, because its reasoning was correct and
is now load-bearing in the opposite direction:** it eliminates identity and style as fine-tuning
targets, which is precisely the argument for why the *judge* is the right one. Read ADR-018 with this
one open. The trigger conditions and the dataset-sourcing analysis below remain live.

**Context:** Moving to open weights (ADR-015) raised the question of whether the system must now
fine-tune a model. There are exactly two candidate targets: **character identity** and **art style**.
Neither has been requested; both are commonly assumed to be necessary when leaving a proprietary
image model. That assumption is what this ADR exists to settle.

**Decision:** **No fine-tuning in v1.** Character identity comes from training-free multi-reference
conditioning (ADR-001). Art style comes from the fixed style constant carried by the canonical
character reference (ADR-007).

**Rationale:**

- **Identity — blocked by latency, not cost.** A per-character LoRA or DreamBooth run is cheap
  (3–20 images, 30–60 minutes on a ~$0.49/hr rented RTX 4090). But a child *invents* a character at
  write-time: there is no dataset to train on and no 40-minute budget inside a 1–3 minute flow.
  Training-free alternatives that *are* fast (IP-Adapter, InstantID, PuLID) are **face-embedding
  based** and their own documentation calls animal and fantastical characters unstable — precisely
  the case StoryBuddy promises (PRD §1). Reference conditioning via the image model itself has none
  of these problems and is already the mechanism the pipeline is built around.
- **Style — already solved by ADR-007.** A style LoRA buys a *proprietary house style*. v1 requires
  *a* consistent style, and the canonical reference is generated **in** that style, so every scene
  conditioned on it inherits the style for free. Adding a LoRA would add a training artifact, a
  dataset-licensing problem, and a model-version dependency, for no user-visible gain.

**Consequences:** No GPU is needed. No dataset must be sourced or licensed. Phase 1 stays about the
pipeline — which is the contribution — rather than about training infrastructure. Fine-tuning is named
in the paper as Future Work, with the cost and the sourcing constraints already scoped (below).

**Trigger to revisit — reopen this ADR if either condition is met:**

- **(a)** The Phase 0.5 spike or Phase 1 eval shows human-judged character consistency on **non-human**
  characters is unacceptable with reference conditioning alone, **and** the FLUX.1 Kontext [dev]
  fallback (ADR-001) also fails. *Note: even then, a style LoRA is not the fix — identity is the
  failing variable. The correct response is a different base model, not training.*
- **(b)** Style drift across scenes is flagged by Tier-1 raters as a top-3 defect in Phase 3.
  *This* is what a style LoRA fixes.

**If reopened, the scoped cost (style LoRA):** 20–60 curated images, ~1000–3000 steps, 1–3 hours on a
rented RTX 4090 (~$0.45–0.49/hr) or A100 (~$1.50/hr), via **ai-toolkit** (Ostris) or **kohya_ss**.
**Roughly $1–10, one-time.** Our 8–16GB GPU **cannot** train Qwen-Image (needs 24–48GB) — rent, don't buy.

*The expensive part is the dataset, not the GPU:*
- **Project Gutenberg** illustrations — US public domain for pre-1929 works only, no illustration index
  (manual book-by-book vetting), and US public-domain status does not clear EU/UK life+70 rules.
- **Smithsonian Open Access** — 2.8M+ CC0 images, the cleanest source. Filter on the explicit CC0 tag.
- **Flickr Commons** — "no known copyright restrictions" is an institutional best-effort statement,
  not a legal guarantee. Accept only explicit CC0/PDM.
- **Synthetic bootstrap** — generate ~1000 images, hand-curate ~100, train on those. Established
  practice, and **not** model collapse: collapse ("model autophagy disorder") requires repeatedly
  training on *unfiltered* self-output. One human-curated round is not that.

**Alternatives:** Per-character LoRA at runtime — rejected on latency, permanently. Style LoRA in v1 —
rejected as speculative (ADR-007 already delivers style consistency; build it only if raters say it
didn't). Fine-tuning as a research contribution — explicitly not requested; the contribution is the
pipeline (PRD §3), and adding a training claim would dilute the ablation, not strengthen it.

---

## ADR-017 — Setting: teacher-owned classroom, student authors, no public mode

**Status:** Accepted (2026-07-10) · **supersedes the auth *role model* in ADR-006** · **drives ADR-008, ADR-021**

**Context:** The respondents are **Grade 5–6 students in the Philippines** (ages 10–12), and the product
gains **peer sharing**. The original design had a parent account holding nested kid profiles, and listed
teacher/classroom as out of scope (PRD §4).

Two pressures collide. Removing the parent as gatekeeper while *adding* peer-visible child-authored
content does not simplify the product — it converts it into a social network for ten-year-olds, with the
content moderation, age verification, abuse reporting, and takedown obligations that implies. And
removing parental *controls* from the product never removes parental *consent* from the research: under
the PH Data Privacy Act, processing a minor's personal information requires guardian consent regardless
of who holds the account.

**Decision:** **Move the gatekeeper; do not delete it.**

- An **owner** (a teacher) signs up, creates a **classroom**, and creates **student profiles**
  (nickname + avatar). Students never sign up and supply no PII.
- **RLS isolates by classroom.** Supabase, Auth, Storage, Realtime, and the RLS posture (ADR-006) are
  otherwise unchanged — only the role names and the isolation boundary move.
- **Sharing terminates at the classroom.** Not public, not link-based, not cross-classroom.
- The **teacher review gate** replaces the parent review gate: a book enters the classroom gallery only
  after the owner approves it. This is the human backstop behind automated moderation (ADR-011).
- The **parent's role is consent-giver**, which is where the law puts them.
- **Scope is Grade 5–6, and it is derived from the research questions, not chosen for convenience.**
  They write independently (so the story is unambiguously the child's, without which RQ5 is meaningless);
  they read fluently (without which peer comprehension cannot be measured at all); DepEd's medium of
  instruction is English by Grade 4 (so: one language, one moderation regime, one TTS voice); they are
  pre-adolescent (so peer feedback is unlikely to be cruel). Remove any boundary and a specific RQ breaks.

**Consequences:**
- Less work than parent signup: the teacher creates profiles; children never authenticate.
- RLS means something again — classroom isolation is a real, testable boundary (Tier A tests).
- Peer comprehension (RQ5, ADR-008) becomes measurable, which is what makes sharing a research
  instrument rather than a feature.
- **No public mode ever.** See Alternatives.
- **A classroom is just a container with an adult owner.** A tutoring centre owns one; a parent owns one
  with a single member. Same table, same policy, no second mode. Publishing *outside* the container is
  the PDF export (ADR-013) — the child shares the artifact, not the platform.
- At N ≈ 8–15 the study cannot stratify by age anyway. A tight band is a delimitation, not an apology.

**Alternatives:**
- **Two modes (classroom-scoped + public-scoped)** — rejected, firmly. It doubles the RLS model, the
  consent regime, and the spec set (violating CLAUDE.md §6's ban on parallel structures); it makes *mode*
  an uncontrolled variable inside the ablation; and an ethics board will not approve a public mode for
  content authored by minors. The underlying worry — "is this only useful in a classroom?" — is answered
  by the container argument above, at zero cost.
- **Open student accounts, no gatekeeper** — rejected. This is the social-network failure mode.
- **Keep parent accounts and add sharing** — rejected. Sharing between unlinked families is the hardest
  version to make safe and the hardest to get approved.
- **Researcher-run sessions only, no real accounts** — rejected as a *product* decision, but adopted as
  the *recruitment* posture: the researcher occupies the owner role during the study. Same code path, no
  throwaway mode, and no school partnership is required to reach N ≈ 8–15.

---

## ADR-018 — Fine-tune the consistency judge (Qwen2.5-VL-7B, QLoRA)

**Status:** Accepted (2026-07-10) · **supersedes ADR-016** · **amends ADR-004** · **served by ADR-019**

**Context:** An external requirement directs the project to fine-tune a model, at the "demonstrate the
capability" level: **the pipeline remains the headline contribution (PRD §3)**; the fine-tune is one
component with its own results table. The question is *which* model, and the answer must be defensible
on technical merit rather than elimination.

ADR-016 already eliminated the two obvious targets, and its reasoning stands: **identity** cannot be
fine-tuned per character (a child invents the character at write-time; there is no dataset and no
40-minute budget inside a 1–3 minute flow), and **style** is already solved by ADR-007's constant.

That leaves the judge, and the judge is not a residual choice — it is the *right* one. ADR-004 records,
with citations, that VLM judges are a known-weak instrument for true instance identity: they conflate
category and scene similarity with identity ([NearID](https://arxiv.org/abs/2604.01973)), and prompting
with an explicit rubric plus reason-then-score ordering caps out near **79.6% human agreement**
([DreamBench++](https://arxiv.org/abs/2406.16855)). ADR-001 records that **no published benchmark splits
identity similarity by human vs. non-human subject** — which is exactly the regime this product lives in.

So: the load-bearing component of the control loop is the documented weakest link, prompting has a known
ceiling, and the gap in the literature coincides with the gap in the product.

**Decision:** Fine-tune **`Qwen2.5-VL-7B-Instruct`** (Apache-2.0, native multi-image, QLoRA-able) as the
consistency judge, via QLoRA. Same family as the text model, so the paper describes one open Qwen stack.
The full data-construction recipe, training configuration, baselines, and failure modes live in
**`docs/specs/judge-finetune.md`**. The decisions that bind are these:

- **Train in-domain; evaluate in-domain; transfer-test on public data.** Not the reverse.
  DreamBench++'s domain is *photographic* concepts; ours is stylized illustrations of invented, often
  non-human characters — the exact regime where the judge is weak. Training on photographs of real
  corgis to judge a cartoon dragon is a domain shift aimed straight at the weakness being fixed.
  DreamBench++ is therefore a **held-out transfer evaluation**, which is a stronger claim and sidesteps
  its image-provenance question entirely (evaluation is the benchmark's intended use).
- **Split by character, never by pair.** A character appearing in both train and test inflates κ silently.
- **Hard negatives are free; positives are not.** A negative is character A's reference against a scene
  generated from character B's reference, same species and same style — clean by construction, zero
  labour. But "same reference implies same character" is a *noisy positive*, noisy in the one direction
  that matters, because generation sometimes drifts — which is the entire reason the judge exists.
  Auto-label positives and the model learns *"was a reference image used?"*
  **Positives must be human-confirmed.**
- **Rationales are supervised, not distilled.** ADR-004's reason-then-score field order is load-bearing,
  so `differences_observed` must be a training target. Generate those rationales with Gemma-27B and you
  have distilled the incumbent's errors and mathematically cannot beat it. Instead, annotators pick from
  a **fixed checkbox taxonomy of failure reasons** (wrong colour / wrong species / wrong clothing /
  wrong style / different face). Fast to annotate, human-supervised — and ADR-010's targeted regeneration
  needs exactly that taxonomy anyway. **Annotate once, use twice.**
- **Report F1 on the `different_character` class**, not accuracy. If most scenes pass, a model that
  always says "same" scores well and is useless; the minority class is the one the control loop acts on,
  and a missed failure ships a broken page to a child.
- **Report κ split by human vs. non-human character.** That split is the contribution.
- **Four baselines, non-negotiable:** zero-shot `Qwen2.5-VL-7B` (proves the LoRA did the work, not the
  base model), prompted `gemma-3-27b-it` with reason-then-score (the incumbent, ADR-004 — the thing to
  beat), CLIP image–image cosine (the naive metric ADR-004 rejects), and **DINOv2 cosine** (the strong
  non-VLM baseline; self-supervised features beat CLIP at instance identity — if DINOv2 wins, that is a
  finding, and better learned now).
- **Pre-register the analysis plan** before running anything. A fine-tune that loses to prompted
  Gemma-27B is then a publishable result ("prompting remains competitive at this scale; the bottleneck is
  data, not capacity") rather than a defeat to be spun.
- **Deployment gate:** ship the fine-tuned judge only if it beats prompted Gemma-27B on held-out
  `different_character` F1. Otherwise it makes the product worse and shipped because it was built.
- **Never on the safety path.** ADR-011's image rubric stays on prompted Gemma. See ADR-004 amendment (b).

**Consequences:**
- The product gets *faster and cheaper*: a 7B judge beats a 27B API call on both latency and cost.
- RQ6 is promoted from "bonus result" to a reported contribution (ADR-008 amendment c).
- ⚠️ **Sequencing.** Hard negatives and the in-domain eval set need pipeline output, so the fine-tune is a
  new **Phase 2.5** — *after* Phase 1's exit criterion has already depended on the prompted judge. If the
  prompted judge is weak, the fine-tune arrives too late to rescue Phase 1. ADR-010's best-of fallback
  means Phase 1 wobbles rather than collapses. Named here so it is not discovered.
- ⚠️ **Distribution shift.** The judge trains on Qwen-Image-Edit output. If the Phase 0.5 spike escalates
  to FLUX.1 Kontext (ADR-001), the training distribution no longer matches deployment. Retrain, or say so.
- ⚠️ **Ethics.** Training data derives from children's stories. **Stage-1 consent must state that donated
  stories may be used to build and evaluate an AI model** (ADR-008). One sentence, written before
  collection, not after.
- Hardware: **rent, do not buy.** QLoRA on a 7B VLM with two images needs ~16–20 GB; the available 8–16 GB
  card cannot comfortably hold it. A few hours on a rented 4090 is ~$5–15 (ADR-016 did this arithmetic).
- `backend/providers.py` grows a `judge()` function with a multimodal message path. It had none — the
  judge was being probed with text-only calls, which would have passed while the judge was broken.

**Alternatives:**
- **Per-character identity LoRA** — rejected permanently on latency (ADR-016).
- **Style LoRA** — rejected as speculative (ADR-007 delivers style; ADR-016 trigger (b) still governs).
- **Fine-tune the story analyzer on Taglish** — genuinely attractive and locally grounded, but it competes
  for the same budget, needs gold scene segmentations, and the language decision (English, Taglish
  tolerated) makes it a robustness note rather than a research problem. Named as Future Work.
- **Fine-tune a safety classifier** — rejected. Safety wants a proven, independently-evaluated model,
  never a student-trained one.
- **Fine-tuning as the headline contribution** — not what was asked (PRD §3 stands), and it would dilute
  the ablation rather than strengthen it.

### Amendment (a) — 2026-07-10 — the evaluation gate is a pre-registered claim ladder

**Context for the amendment.** The external requirement has been clarified: the fine-tune must
**demonstrate measurable improvement**, not merely demonstrate the capability. That is a bar on a *research
result* rather than on a deliverable, and nobody can guarantee which way a comparison falls. The fix is to
notice that **two different questions were being decided by one number**, and to separate them.

- *"Did fine-tuning work?"* is the **research** question. Its comparator is the **un-fine-tuned base model.**
- *"Should this judge replace the one in the product?"* is the **engineering** question. Its comparator is
  the **prompted incumbent.**

Collapsing these into a single "beat Gemma" gate made a near-certain research result hostage to a coin-flip
engineering comparison. **This amendment supersedes the one-line deployment gate above.**

**The primary endpoint — the research gate. One number, declared before a single label is collected.**

> ΔF1 on the `different_character` class, held-out test set, **fine-tuned Qwen2.5-VL-7B vs. zero-shot
> `Qwen2.5-VL-7B`.** Superiority is claimed only if the 95% confidence interval on ΔF1 excludes zero.

This is the standard ablation every fine-tuning paper reports: *did the LoRA, rather than the base model, do
the work?* Same architecture, same weights, same prompt — the only difference is the adapter. It is the
cleanest causal statement available about the fine-tune, and on ~900 in-domain training pairs the expected
gap is large.

- **Significance:** McNemar's exact test on the paired per-item decisions (both judges score the same items).
- **Effect size:** ΔF1 with a 95% bootstrap CI, 10,000 resamples, **resampled by `char_id`, not by pair.**
  Fifteen scenes from one character are not fifteen independent observations; a pair-level bootstrap yields
  an interval that is too narrow. This is the likeliest place for a statistics reviewer to find a hole.

> ⚠️ **Beating your own base model is necessary, not impressive.** A panel's reflex is *"of course in-domain
> fine-tuning beats zero-shot."* It is a valid pre-registered result and it satisfies the requirement, but it
> is not the contribution. **Never present it alone.** The interesting numbers are the comparison against
> prompted Gemma-27B and the non-human slice, and both are reported prominently whatever they say.

**The product gate — the engineering decision. Separate, and non-blocking for RQ6.**

Ship the fine-tuned judge only if **both** hold against prompted `gemma-3-27b-it`:

1. **Non-inferiority:** ΔF1 on `different_character` is no worse than δ = 3 points.
2. **No recall regression.** A judge that buys precision with recall ships broken pages to children.
   Consistency has a best-of fallback (ADR-010); a missed failure has none.

Failing the product gate does not fail RQ6. It means the paper reports that specialization at 7B did not
close the gap to a prompted 27B, the product keeps the prompted judge, and ADR-019's Modal deployment is
dropped — which the ROADMAP's de-scope ladder already anticipates at rung 4.

**Secondary endpoints, ordered and declared in advance.** Reported whatever the primary does:

1. **Fine-tuned vs. prompted `gemma-3-27b-it`**, same metric and test. The number the panel will actually
   care about, and the input to the product gate.
2. The primary metric on the **non-human character slice** — where ADR-001 says nobody has measured, and
   where prompting should be weakest. This is the contribution; it is also the least-powered slice.
3. Cohen's κ vs. human, overall and split by human / non-human.
4. Latency and $/call. A structural win, not a contested one.
5. DreamBench++ transfer. **Descriptive only — no comparison claim is made on it**, because it is
   out-of-domain by construction.

**CLIP and DINOv2 are scientific controls, not product candidates.** They emit a scalar. ADR-010's
regeneration controller consumes `failure_reasons` — it must know to restate the scarf, and a cosine
similarity cannot tell it. **If DINOv2 wins on F1, that is a reported finding about metrics and changes
nothing in the pipeline**, because DINOv2 cannot do the job the judge exists to do. Stating this in advance
is what stops it becoming a defense ambush.

**Powering the test set — decide before labelling, not after.** The primary endpoint is now cheap to power:
base-vs-tuned gaps on in-domain data are large. **The secondary Gemma comparison and the non-human slice are
not**, and they are where the contribution lives. So:

- Test split: **12 characters, stratified so human and non-human are balanced.** Splitting is a design
  choice and may be stratified; moving a character after seeing results may not.
- **Oversample scenes for the test characters** before labelling. Growing the test set is legitimate.
- **Induce drift deliberately** (weaker conditioning, higher temperature) to harvest natural negatives —
  **training split only. Never the test set**, which must keep the deployment distribution (see the class-
  imbalance rule above).
- **Raise the corpus target to 60–70 donated stories if Stage-1 recruitment allows.** More characters is the
  cheapest statistical power available, it buys the *secondary* endpoints rather than the primary, and it is
  a *recruitment* decision, not a modelling one — so it must be made at Stage 1, not at Phase 2.5 when it is
  unfixable.

**The claim ladder. Declared before results exist; that is the whole point.**

| Rung | Condition | Requirement met? | Claim | Ship? |
|---|---|---|---|---|
| **A** | Beats base **and** beats prompted Gemma | Yes | A specialized 7B judge **outperforms** a prompted 27B incumbent in-domain, at lower latency and zero marginal cost | Yes |
| **B** | Beats base; within δ = 3 F1 of Gemma; no recall regression | Yes | Specialization **recovers 27B-level quality at 7B**, self-hostable, zero marginal cost | Yes |
| **C** | Beats base; loses to Gemma by > δ | **Yes** | Fine-tuning worked, but **specialization at 7B did not close the gap** to a prompted 27B: *"the bottleneck is data, not capacity."* An honest, publishable negative result | No — keep prompted judge; drop ADR-019 |
| **D** | Does not beat base | No | The LoRA did nothing. A **bug report, not a result** | No — debug |

δ = 3 F1 points is a judgment call, chosen because it sits inside one annotator's disagreement band on ~60
minority-class items. **Adjust it once, before pre-registration. Never after.**

**Consequences of this amendment:**
- **RQ6 can no longer be lost to a coin flip.** Rung D is the only failing outcome, and rung D is a bug.
- **The engineering risk is now isolated in rung C**, where it is survivable: the product keeps the judge it
  already shipped Phases 1 and 2 with, and the de-scope ladder already lists this at rung 4.
- The analysis plan must be **written and timestamped before any label is collected.** Not a formality — it
  is the only thing separating a pre-declared ladder from a moved goalpost.
- **All iteration happens on the validation split.** The held-out test set is looked at once. If it is
  consulted during development, it is no longer held out and the primary endpoint is void.
- ⚠️ **The weakness of rung C is presentational, not scientific.** "We beat our own base model" invites
  *"so what?"*. The defense answer is the non-human slice and the cost/latency table — which is why those are
  reported prominently and unconditionally, not as consolation.

---

## ADR-019 — Serving the fine-tuned judge: vLLM, scale-to-zero, OpenAI-compatible

**Status:** Accepted (2026-07-10) · **amends ADR-009** (a fourth service) · **serves ADR-018**

**Context:** The fine-tuned judge ships in the live pipeline (ADR-018), and **OpenRouter cannot serve a
custom LoRA.** The judge is called once per scene attempt — roughly 12–24 times per book, inside a flow
that already takes 1–3 minutes.

**Decision:** Merge the LoRA and serve `Qwen2.5-VL-7B` behind **vLLM** on a **scale-to-zero GPU
container** (Modal; RunPod Serverless and Baseten are equivalents). vLLM exposes an **OpenAI-compatible**
endpoint, so `providers.judge()` does not change — only `JUDGE_BASE_URL` and `JUDGE_API_KEY`.

This is the promise of ADR-015 being cashed: *"swapping a model is an env var; swapping a provider is one
file."* Here it is not even one file. The only code concession is that OpenRouter's
`provider.require_parameters` flag is sent **only** to OpenRouter, since vLLM rejects the unknown field.

**Consequences:**
- A fourth deployment target (ADR-009 amended). Cold start ~30–90 s; keep one container warm during study
  sessions (~$1/hr — a three-hour session is pocket change).
- Cost *falls*: ~2,000 judge calls/month at ~3 s each is ~100 GPU-minutes, cheaper than 2,000 Gemma-27B
  API calls (PRD §15).
- **This is the first item on the de-scope ladder.** Dropping it reverts `JUDGE_BASE_URL` to OpenRouter and
  costs only the "faster and cheaper product" claim — RQ6 survives entirely, evaluated offline. Therefore
  **nothing may hard-depend on this container**, in particular not ADR-011's image moderation.
- The container makes **ShieldGemma 2** affordable as *optional* image-safety hardening (ADR-011).

**Alternatives:**
- **Offline research artifact only** (evaluate the judge in the Tier-B harness; ship prompted Gemma) —
  zero infrastructure, and the **pre-committed fallback** if the schedule compresses.
- **Local GPU behind a tunnel during the study** — free and honest, but the demo and the study then run
  different pipelines. Acceptable emergency posture; say so plainly in the paper if used.
- **HF Inference Endpoints / Fireworks LoRA hosting** — viable; VLM LoRA support is thinner. Revisit only
  if Modal disappoints.
- **CPU inference on the existing worker** — rejected: a 7B VLM on CPU is tens of seconds per call, and
  there are twelve to twenty-four calls per book.

---

## ADR-020 — Narration: Kokoro-82M, pre-rendered on the worker

**Status:** Accepted (2026-07-10) · **amends ADR-002's read-aloud consequence and PRD §17**

**Context:** The product needs read-aloud narration (CC-6, PRD §17). Three candidates: the browser's
Web Speech API (the current decision), ElevenLabs (proposed), and an open TTS model.

**Decision:** **`Kokoro-82M`** (Apache-2.0, 82M params, real-time on CPU). The worker pre-renders one MP3
per page during the pipeline and writes it to Supabase Storage behind a signed URL; the frontend is an
`<audio>` tag.

**Consequences:**
- **No new service and no GPU.** The worker already loads an 86M NSFW ViT (ADR-011); this is the same shape.
- Zero cost, zero API key, no ADR-015 exception to argue. ElevenLabs is proprietary and would need one.
- Narration reads the child's **verbatim redacted text** (ADR-013), so it adds **no new moderation surface**.
- Consistent voice across Android, Windows, and iOS — the Web Speech API's voice quality and `onboundary`
  support vary by platform, and the target deployment is Philippine classroom hardware.
- ⚠️ Kokoro is **English-only**. Taglish sentences are read with English phonology. Recorded as a
  limitation; not solved.
- **Word-level highlighting is dropped.** It requires character-level timestamps, which is the one thing
  ElevenLabs buys. It is a fluency aid for *emergent* readers; Grade 5–6 students read. Add it if a
  teacher asks for it.

**Alternatives:**
- **ElevenLabs** — rejected: proprietary (ADR-015 hardened), metered, and its timestamp advantage buys a
  feature this age band does not need.
- **Web Speech API `SpeechSynthesis`** — the previous decision. Free and zero-dependency, but OS voice
  quality on Android and Windows is poor and `onboundary` support is inconsistent.
- **XTTS-v2** — better multilingual coverage; Coqui Public Model License is restrictive. Revisit only if
  Filipino narration becomes a requirement.

---

## ADR-021 — Classroom sharing and peer reflection

**Status:** Accepted (2026-07-10) · **depends on ADR-017** · **instruments ADR-008's RQ5**

**Context:** Student authors need a reason to care beyond seeing their own book once. The proposed
answer — share the book and let classmates respond — is also, unexpectedly, the study's best measurement
instrument (ADR-008 amendment b).

The rejected framing was "tell the author whether their story is good." Scoring a ten-year-old's story is
pedagogically hostile, and automated narrative-quality assessment is a separate literature that would
dilute the ablation. The author-facing benefit must be **formative, not evaluative**.

**Decision:**

1. **Sharing is classroom-scoped and teacher-gated.** A book enters the gallery only after the owner
   approves it (ADR-017).
2. **Peer reflection is a fixed, closed set of prompts** — *who was the story about? what happened?
   what did you learn?* Fixed prompts, not free-form rating, keep feedback kind and make it comparable
   across readers. The first two double as the **RQ5 comprehension instrument**.
3. **Reflections are child-authored input.** They route through the existing `input_gate` node — PII
   redaction and text moderation, unchanged (ADR-011 mechanism 5). No new moderation surface, no new node.
4. **The author sees a Story Map, not a score.** A read-only page derived from the existing Story Memory:
   *"you wrote 3 characters, in 2 places, and 5 things happened."* Zero new models, zero new generation,
   zero new moderation surface. The honest feedback signal is classmates' answers, which come from humans.

**Consequences:**
- The sharing feature and the comprehension *measure* are **independent**. RQ5 needs a reader, a book, and
  a questionnaire — that is the Tier-1 rating harness (Phase 3). **If sharing slips, the research does not.**
- Reflections are stored per (book, reader) and are classroom-scoped under the same RLS policy.
- Fixed prompts + moderation + teacher visibility are three layers between a child author and an unkind
  comment. All three are required; none alone is sufficient.

**Alternatives:**
- **Automated story-quality scoring / "is your story good enough?"** — rejected. Hostile to the child,
  and a second research contribution that would dilute the first.
- **"What happens next?" continuation** — deferred to Phase 4. It is the strongest motivational feature
  available and nearly free at the UI layer, but it means cross-story character reuse, canonical-reference
  reuse, and new RLS thinking. It buys the research nothing. Second on the de-scope ladder.
- **Free-form peer comments** — rejected. Uncomparable across readers, and the unkindness surface is
  unbounded.
- **Public sharing** — see ADR-017.

---

## ADR-022 — Selectable art-style presets (three, prompt-fragment based)

**Status:** Accepted (2026-07-10) · **amends ADR-007**

**Acceptance condition (binding).** The presets must not read as generic AI art, must look creative, and must
hold character identity across scenes. See "The aesthetic constraint" below — it is a design requirement with
a measurement attached, not a preference.

**Context:** ADR-007 froze v1 to a single fixed art style and named selectable styles a "clean Future Work
item" (ROADMAP Phase 4). The product owner now wants **at least three presets**, because letting the author
choose how their story looks is one of the few places this product gives a child ownership rather than
output — and author benefit is a stated product goal (PRD §2).

The question raised was whether a preset should be driven by a **prompt fragment** or by a **reference image
in that art style.** ADR-007 already answers it, and the answer was easy to miss: **style is carried by the
canonical character reference.** The char-ref is generated once *in* the chosen style; every scene is a
reference-conditioned edit of that image, so it inherits identity and style through the same mechanism. The
style fragment is belt-and-suspenders. **A preset is therefore a different constant, not a different
mechanism.** Nothing in the pipeline shape changes.

**Decision:**

- A preset is a **named prompt fragment in config** — `style_presets: dict[str, str]`, three entries, one of
  which is today's constant. **No new node, no new model, no new API call, no additional image.**
- **Style is chosen once, before canonical-reference generation, and frozen for the life of the storybook.**
  A style that can change mid-book breaks regeneration: a targeted retry would re-draw one page in a new
  style, and `wrong_style` would fire on a correct image.
- **Story Memory gains `style_preset`.** This is a contract change (CLAUDE.md §2): schema, affected specs,
  and every consumer move in the same change.
- **The judge only ever compares a reference against a scene within one preset.** It never compares across
  styles. So `wrong_style` keeps its meaning, and the fine-tune's training data is not split three ways —
  it gains visual diversity within a single task.
- **Reject the style-exemplar-image route** (IP-Adapter / style-transfer from a reference artwork).

**Why the exemplar image is rejected, in order of weight:**

1. **Provenance.** An art-style exemplar has to come from somewhere. Scraped artwork is a copyright and
   ethics problem in a child-facing product whose defensibility rests on an open-weight, clean-provenance
   argument (ADR-015). A *generated* exemplar is a prompt fragment with extra steps.
2. **Redundancy.** The char-ref already anchors style. A second style-conditioning image adds a channel that
   duplicates one we have.
3. **Unverified substrate.** Conditioning `qwen-image-edit-2511` on *two* images (character + style exemplar)
   is not something Phase 0.5 probes or ADR-001 records. It would add a new unknown for no gain.
4. Extra cost and latency on every image.

**Choosing the three.** Style presets must be visually distinct *and* identity-preserving. Strong line and
silhouette carry identity across scenes; heavy texture and photorealism destroy it — and non-human characters
are the fragile case (ADR-001).

- Recommended: **(1) flat gouache storybook** (today's constant), **(2) bold ink outline with cel shading**,
  **(3) soft watercolour with a visible ink line.**
- **Do not offer photorealistic or 3D-render styles.** Highest identity drift, uncanny on invented creatures,
  and photoreal imagery of child-authored characters worsens the moderation surface for no pedagogical gain.

**The aesthetic constraint — and the tension inside it.**

"Looks AI-generated" is not vague; it is a specific and nameable default that diffusion models fall into:
airbrushed gradients, plastic sheen, hyper-saturation, symmetrical perfection, glow and bokeh, uniform
over-detail. The antidote is equally specific — **name a traditional medium and its physical artifacts**:
paper grain, visible brush and ink edges, a limited palette, deliberate asymmetry, flat fills rather than
gradients. Prompt fragments state the medium; they do not state "beautiful," "8k," or "highly detailed."

**But this pulls directly against consistency, and that must be said out loud.** Painterly texture and
imperfection are what defeat the AI look. Strong line and flat silhouette are what preserve identity across
scenes (ADR-001; non-human characters are the fragile case). Maximize one and you erode the other.

**The resolution is why the recommended three are what they are:** put *identity* in the line and *character*
in the fill. An ink line holds the silhouette, the eye count, the scarf; a watercolour wash or gouache
texture kills the airbrushed sheen. Styles that carry identity *in the texture* — impressionist, painterly,
photorealistic — are the ones to refuse.

**This is measured, not asserted.** Probe 1's blind scoring sheet gains one item alongside identity:
*"Does this read as a hand-illustrated children's book, or as AI art?"* It does **not** gate — the kill
criterion stays on identity — but a preset that scores badly is re-authored or dropped before a child sees
it, and the number goes in the paper.

**Consequences:**

- **Phase 0.5 gains a secondary arm:** run Quill (the invented chimera) through all three presets.
  ~20 extra images, ~$0.80. **It does not gate.** The kill criterion stays on the primary style — but a
  preset that cannot hold Quill is deleted before a child ever sees it, not after.
- Three presets are three substrate risks. This measures them instead of assuming them.
- **RQ2 is unaffected.** The ablation is within-story paired — same story, same seed, same preset, ON vs OFF
  — so style is held constant inside every comparison. Record the preset per story; report the distribution.
- Tier-1 raters will see mixed styles across stories. Report preset as a covariate. **Do not claim a preset
  effect** — N is nowhere near enough, and it is not an RQ.
- ⚠️ **Fine-tune.** Training data now spans three styles. Because every pair is within-style, this is
  diversity rather than a three-way split. **Do not attempt per-preset results.** No power.
- PRD flow gains a style-picker step before generation: three large sample cards, not a dropdown.
- Marginal cost: **zero.** Presets are strings.

**Alternatives:**

- **Keep one fixed style** (ADR-007 as written) — simplest and cheapest. Rejected: it removes the clearest
  author-agency affordance in the product, at near-zero implementation cost to keep.
- **Style exemplar image / IP-Adapter** — rejected above.
- **Style LoRA** — ADR-016 trigger (b) still governs: only if raters flag style drift. Not now, and a preset
  is not a reason to revisit it.
- **Let the child describe any style freely** — rejected. An unbounded style space destroys the meaning of
  `wrong_style`, makes the judge's training distribution unbounded, and makes moderation unpredictable.

**Open questions:**

- The three exact prompt fragments. Author them, then probe them in Phase 0.5's secondary arm.
- Does the teacher lock one preset per classroom, or does each child choose? A product question (ADR-017's
  teacher-owner model makes either possible). Not blocking; decide at Phase 2.
