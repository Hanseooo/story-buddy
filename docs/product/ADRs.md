# StoryBuddy — Architecture Decision Records

Each ADR is intentionally short and revisitable. Format: Status · Context · Decision · Consequences · Alternatives.

---

## ADR-001 — Image generation model: Nano Banana (hosted)

**Status:** Accepted

**Context:** The core research problem is character consistency across scenes, including non-human characters. This is the module every other module depends on. Budget is small; timeline is ~1 month solo.

**Decision:** Use **Nano Banana (Gemini 2.5 Flash Image family; Nano Banana 2 Lite as the default variant)** via the hosted Gemini API, using reference-conditioned generation on an auto-generated canonical character image.

**Consequences:** Character consistency is a built-in feature (its headline capability); ~$0.034–0.039/image (~$0.55–0.70/book); minimal infra; SynthID watermark on outputs (useful provenance). Dependency on Google's API and its content policy (mitigated by the self-refusal fallback, ADR-011).

**Alternatives:** Open-source (SDXL/FLUX/Qwen-Image + IP-Adapter/InstantID/LoRA) — rejected for MVP: reliable consistency on stylized/non-human characters needs per-character LoRA training (infeasible at runtime), requires GPU infra that can exceed the whole budget, and turns the core contribution into weeks of infra work. Kept as Future Work for a privacy-preserving on-device variant. GPT image model — pricier, consistency not its focus. Nano Banana Pro — reserve for the rare book needing legible in-image text.

---

## ADR-002 — Text/orchestration model: Gemini (with local-model privacy variant deferred)

**Status:** Accepted

**Context:** Story analysis, segmentation, prompt-building, and the VLM-judge need a capable LLM/VLM. A local open model (e.g., Gemma) would keep the child's text on-device — a real privacy advantage for a kids' product — but adds serving/ops burden and is weaker at reliable structured extraction and vision judging.

**Decision:** Use **Gemini** (Flash tier for pipeline nodes; Gemini vision for the judge) in the MVP.

**Consequences:** Single ecosystem/billing, strong structured output, fast to ship. The child's text transits Google (mitigated by PII redaction, ADR-011).

**Alternatives:** Local Gemma for all text + Nano Banana only for pixels (hybrid) — deferred to Future Work as a privacy enhancement; revisit if a capable GPU is available. Chosen against for MVP to avoid ops burden on a solo one-month build.

---

## ADR-003 — Pipeline as a deterministic LangGraph state machine (not an autonomous agent)

**Status:** Accepted

**Context:** The pipeline is a fixed sequence with only two real branch points (moderation pass/fail, consistency pass/fail). An autonomous "orchestrator agent" that decides routing adds nondeterminism, cost, and debugging difficulty, and harms research reproducibility.

**Decision:** Model the pipeline as an explicit **LangGraph state machine** with defined nodes and conditional edges only where genuinely needed. Call the Gemini SDK directly.

**Consequences:** Deterministic, debuggable, reproducible (matters for the ablation). Built-in checkpointing (see ADR-005). No autonomous-agent overhead.

**Alternatives:** Autonomous agent orchestrator — rejected (nondeterminism, cost, reproducibility). Plain Python without LangGraph — viable but loses checkpointing/persistence and graph structure for free.

---

## ADR-004 — Consistency via VLM-as-judge control loop; human ratings as headline metric

**Status:** Accepted

**Context:** Whole-image CLIP embeddings are dominated by background/pose/scale and degrade on stylized and non-human characters — unreliable both as a control signal and as an eval metric. Using the same automated score to drive regeneration *and* report results is circular.

**Decision:** Use a **VLM-as-judge** (Gemini vision) as the runtime control signal: given the reference + a generated scene, return a structured verdict (same character? attributes present? style match?) plus **failure reasons**. Use **human ratings as the headline research metric**; report **VLM–human agreement** as a secondary result that validates the automated metric. For multiple characters, verify **each character separately** against its own reference (max 2 canonical refs, v1).

**Consequences:** Robust on non-human/stylized characters; interpretable failures enable *targeted* regeneration (ADR-010); no circularity in the paper; a bonus publishable result (metric validation).

**Alternatives:** CLIP/face-embedding similarity as primary — rejected (fragile here, circular). May still be reported as an additional descriptive number if desired.

---

## ADR-005 — Async job architecture: FastAPI + RQ worker + Redis + LangGraph checkpointing

**Status:** Accepted

**Context:** A storybook takes ~1–3 minutes to generate — impossible inside a request/response cycle. A stall must not re-generate already-good (already-paid-for) scenes.

**Decision:** `POST /storybooks` creates a job row and returns `job_id` immediately. A **separate RQ worker** (Redis broker) runs the LangGraph pipeline, **checkpointing to Supabase Postgres after each scene** (`langgraph-checkpoint-postgres`). Frontend tracks progress via **Supabase Realtime** on the job row. Resumability: a stall at scene N resumes from N.

**Consequences:** A 3-service deployment (web + worker + Redis), not one. Robust, resumable, cost-safe. Free-tier worker spin-down must be avoided before demos/study (keep-warm or paid tier).

**Alternatives:** Celery (heavier), ARQ (async-native; adopt later if concurrency needed), Postgres-backed queue to drop Redis (viable simplification — revisit if Redis feels like overhead). Websockets instead of Realtime — more work for the same result.

---

## ADR-006 — Supabase for Auth + DB + Storage + Realtime

**Status:** Accepted

**Context:** Need parent accounts, kid profiles, generated-image storage, live progress, and strict data isolation for a children's product — fast, solo.

**Decision:** Use **Supabase** for Postgres (app data + LangGraph checkpoints), **Auth** (parent accounts; kid profiles as linked rows), **Storage** (images + PDFs via signed URLs), and **Realtime** (job progress). Enforce **Row-Level Security** so a parent can only access their own account's data.

**Consequences:** Large portion of the stack handled by one service; RLS gives DB-layer data isolation (correct design + strong paper point). Vendor dependency on Supabase.

**Alternatives:** Roll-your-own auth/storage — more control, much more work, weaker safety story. Firebase — comparable but less Postgres/RLS-native.

---

## ADR-007 — Style as a fixed constant carried by the character reference

**Status:** Accepted

**Context:** v1 uses a single fixed art style. Generating a "style bible" per story is unnecessary, and style drift across images is a real risk with text-only prompting.

**Decision:** Author the style **once** as a constant: a hand-tuned prompt fragment + optional fixed style-anchor image. Because the canonical character reference is generated *in that style*, every scene conditions on that reference and inherits **both identity and style**; the style fragment is belt-and-suspenders.

**Consequences:** "Style Bible Generator" collapses into config; character and style consistency ride the same mechanism; cleaner consistency evaluation. Selectable styles become a clean Future Work item.

**Alternatives:** Per-story generated style, selectable styles, fine-tuned/LoRA style — all deferred; unnecessary complexity for a single fixed v1 style.

---

## ADR-008 — Evaluation: comparative ablation, self-sufficient Tier 1, enrichment Tier 2

**Status:** Accepted

**Context:** Absolute satisfaction scores show the *artifact* is decent but not that the *pipeline* caused it. Child self-report is noisy; ethics clearance for child subjects can slip.

**Decision:** Spine = **blind comparative ablation** (pipeline-ON vs pipeline-OFF, same corpus + seed). **Tier 1 (adults)** carries the core claims and needs no special clearance. **Tier 2 (children)** is enrichment: Fun Toolkit (Smileyometer + Again-Again), a story-fidelity item, and behavioral logging. Use a **real/realistic story corpus** with documented provenance; define **inter-rater reliability** for plot-point annotation.

**Consequences:** Defensible causal claim; capstone survives a Tier-2 delay; bonus VLM–human agreement result. More upfront design than a satisfaction survey.

**Alternatives:** Single-tier absolute ratings — rejected (no causal claim). Builder-authored clean stories — rejected (measures best-case only).

---

## ADR-009 — Hosting: Vercel (frontend) + Railway (backend), Singapore region

**Status:** Accepted

**Context:** Solo dev; a 3-service backend (web + worker + Redis); user base in the Philippines.

**Decision:** **Next.js on Vercel** (SSR for the parent-facing landing page). **FastAPI + RQ worker + Redis on Railway**, Singapore (ap-southeast) region. Render or Fly.io are acceptable equivalents; DigitalOcean App Platform is not preferred for the worker+queue shape.

**Consequences:** Good solo DX; low regional latency; free-tier spin-down must be handled before demos/study.

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

**Status:** Accepted

**Context:** Child users require moderation of input and output; a child narrating real life will include PII; the image model itself may refuse legitimate mild-peril scenes. One provider does not cover all of this.

**Decision:** (1) **Input text** — OpenAI moderation endpoint. (2) **PII** — Presidio redaction on input before storage/captioning/export. (3) **Output images** — Vision SafeSearch (or Gemini safety) on **every** image, **including the canonical reference before the reveal**. (4) **Model self-refusal fallback** — soften-and-retry, then a gentle reframe. Ordering: input gate → char-ref moderation → output moderation.

**Consequences:** No unmoderated generated image reaches a child; PII kept out of stored/exported content; scary-but-innocent stories don't dead-end. Several dependencies to wire.

**Alternatives:** Single-provider moderation — insufficient coverage. Relying on the image model's built-in safety alone — misses PII and produces dead-ends on self-refusal.

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
