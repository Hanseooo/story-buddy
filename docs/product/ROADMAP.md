# StoryBuddy — Implementation Roadmap

**Approach:** Walking skeleton → vertical slices → hardening. Riskiest assumptions first. Solo build, agentic-tooling-assisted (Claude Code). Ethics/consent track runs in parallel from Day 1.
**Companion docs:** PRD v2, ADRs.

---

## Guiding principles

1. **Prove integration before depth.** The place a 1-month estimate dies is integration (async jobs, model wiring, storage). Get one story end-to-end through the real infrastructure before making any single module smart.
2. **Riskiest-first.** Validate that Nano Banana holds *your* characters consistent and that the VLM-judge actually catches failures in Phase 1, not Phase 4.
3. **Instrument from Day 1.** LangSmith/Langfuse tracing is your research dataset — turn it on in the skeleton.
4. **Exit criteria, not calendar.** Each phase has a definition of done. Estimates are guidance for a focused solo dev.

---

## Phase 0 — Scaffolding & Walking Skeleton  *(~week 1)*

**Goal:** one hardcoded story flows end-to-end through real infrastructure and produces one real slideshow. Ugly is fine. Nothing is smart yet.

- Repo, monorepo layout (`/frontend`, `/backend`, `/docs`), env/secrets management.
- Provision: Supabase (DB + Auth + Storage + Realtime), Railway (FastAPI + RQ worker + Redis), Vercel (Next.js).
- FastAPI `POST /storybooks` → creates job row → returns `job_id`. RQ worker picks it up.
- LangGraph graph with **stub nodes** (analyze → segment → char-ref → generate → check → compose), Postgres checkpointer wired.
- **Thin real calls:** one Gemini text call, one Nano Banana image call, one image written to Supabase Storage with a signed URL.
- Next.js: auth stub, "write story" box, processing view subscribed to the job row via Realtime, slideshow that renders the stored image + a caption.
- LangSmith/Langfuse tracing + Sentry on from the first commit.

**Exit criteria:** Type a hardcoded story → job runs on the worker → one Nano Banana image lands in Storage → slideshow shows it live via Realtime. The pipe is real end-to-end.

**De-risks:** async job architecture, model + storage wiring, Realtime progress — the integration risks, retired first.

---

## Phase 1 — Core Pipeline Intelligence  *(~weeks 2–3; the research core)*

**Goal:** the pipeline actually works on a *clean* story you control, and the consistency loop is real. This is where the contribution lives.

- **Story Analyzer** — Gemini structured output (`response_schema`) + Pydantic. Entity + coreference extraction tolerant of messy kid text.
- **Scene Segmentation** — select up to 10–15 scenes; **floor behavior** for short stories (≥3, never invent content).
- **Character Bible + canonical reference image** — generate ≤2 canonical characters in the fixed style.
- **Style Constant** — author the fixed style fragment + optional style-anchor image once (config, not a module).
- **Prompt Optimizer** — compose scene + character bible + style constant + story memory into a structured generation prompt.
- **Image Generator** — reference-conditioned Nano Banana calls (condition on canonical ref(s)).
- **Consistency Checker (VLM-as-judge)** — Gemini vision: reference + scene → structured verdict (same character? attributes present? style match?) + failure reasons.
- **Regeneration controller** — one targeted, prompt-corrected retry using the judge's failure reasons; best-of fallback; capped. Seed control for reproducibility.

**Exit criteria:** A clean multi-scene, multi-character story produces a coherent, character-consistent storybook, and you can point to a case where the VLM-judge caught an off-model image and the targeted retry fixed it. Traces show per-scene verdicts, regen counts, and cost.

**⚠️ Highest-risk phase.** If character consistency or the judge underperforms here, you learn it now — with three weeks of runway — not at evaluation.

---

## Phase 2 — Safety, Accounts & Robustness  *(~week 4)*

**Goal:** safe for a real child, and survives messy input.

- **Moderation stack:** input text (OpenAI moderation) → PII redaction (Presidio) → output image moderation (Vision SafeSearch / Gemini safety) on every image **including the canonical reference before reveal**.
- **Model self-refusal fallback** (soften-and-retry → gentle reframe).
- **Length guard** — word cap + truncate-at-scene-boundary (no summarization); repeated-failure off-ramp (N=3).
- **Auth & profiles** — Supabase Auth (parent) + kid profiles + **RLS policies** (data isolation). Signed URLs.
- **Parent dashboard/library** (shadcn/ui) + **parent review gate** before export.
- **Export** — HTML template → PDF (Playwright/WeasyPrint).
- **Rate limiting** (`slowapi`) + per-profile daily cap + cost circuit-breaker.
- **Data deletion path** for parents.
- **Kid-flow polish** — cartoon-pop components, Lottie wait states, Motion micro-interactions, **read-aloud (TTS) captions**, kid-appropriate failure states.

**Exit criteria:** A stranger's child could use the happy path safely; messy/short/over-length/mild-peril stories all degrade gracefully; a parent can sign up, see only their own library, export a PDF, and delete data.

---

## Phase 3 — Evaluation Instrumentation & Study Prep  *(~weeks 5–6, overlaps testing window)*

**Goal:** everything needed to run the study and get defensible numbers.

- **Ablation switch** — a `condition` flag runs pipeline-ON vs pipeline-OFF (no reference/checker/regeneration) on the same story + seed.
- **Story corpus** assembled and provenance documented (real/realistic kid stories, not builder-clean).
- **Tier-1 harness** — blind rating interface (coherence, consistency, illustration quality, completeness); IRR annotation guide for "major plot points."
- **Tier-2 harness** — Fun Toolkit (Smileyometer + Again-Again), story-fidelity item, behavioral logging (completion, time-on-task, repeat-starts, retries).
- **Metrics export** — pull generation time, image/regen counts, cost, VLM scores from tracing; compute VLM–human agreement.
- Ethics submission finalized/approved (started Day 1).

**Exit criteria:** You can run one full ablation study session end-to-end and export a clean metrics table.

---

## Phase 4 — Full Features / Future Work  *(post-MVP, as time allows / paper "future work")*

Named in the paper; built only if time permits: kid-uploaded reference; selectable art styles; multi-language; teacher/classroom tier; public sharing; **on-device/open-source privacy-preserving generation** (local Gemma for text + OSS image + per-character LoRA).

---

## Parallel track (Day 1 → study) — Ethics & Research

Runs alongside all phases: ethics/consent documentation (PH Data Privacy Act + university board), parental consent forms, story-corpus sourcing, recruitment plan. **Tier 1 is designed to stand alone**, so a Tier-2 clearance delay cannot sink the capstone.

---

## Dependency map (what blocks what)

```
Phase 0 skeleton ──► Phase 1 pipeline ──► Phase 3 ablation/eval
       │                   │
       └──► Phase 2 safety+accounts ──► Phase 3 study prep
Ethics track ───────────────────────────► Study (Phase 3)
```

Image model choice (ADR-001) is settled up front because nearly every module depends on it. LangGraph shape + Story Memory schema are frozen before Phase 1 (expensive to rework).

---

## Schedule risk flags

- **Phase 1 is the crumple zone.** If consistency/judge quality is weak, it eats time. Mitigation: it's early, and the fallback (best-of) means "imperfect but shippable" is always available.
- **Read-aloud + full moderation stack** are easy to under-scope; both are in Phase 2 deliberately.
- **The async job system + dual-end moderation** are the two most likely "1-month" schedule-killers — Phase 0 and Phase 2 retire them on purpose.
- **Ethics latency** is the one thing you cannot compress by coding faster — hence Day-1 start and Tier-1 insurance.
