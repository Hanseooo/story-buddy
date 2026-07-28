# StoryBuddy System Architecture

This document details the system architecture of StoryBuddy, outlining the key components, their interactions, and the engineering rationale driving these design decisions. The architecture is designed to support a robust, cost-effective, and research-grade AI picture book generator specifically tailored for classroom use.

## 1. High-Level Architecture Overview

StoryBuddy employs a decoupled, asynchronous three-tier architecture to handle long-running generative AI tasks reliably.

- **Next.js Frontend**: Serves as the user interface for both students and teachers.
- **FastAPI Backend & RQ Worker**: Manages job queuing and executes the intensive AI pipeline.
- **Supabase**: Centralizes the database, authentication, file storage, and real-time pub/sub capabilities.

The core generation flow is completely asynchronous. Because generating a storybook can take 1–3 minutes, the request never runs synchronously. The frontend issues a `POST /storybooks` request to the FastAPI backend, which immediately creates a job row in Supabase and returns a job ID. A separate RQ (Redis Queue) worker pulls the job and runs the generative pipeline. As the worker progresses, the frontend subscribes to updates on the job row via Supabase Realtime, enabling a seamless live progress experience without long-polling or HTTP timeouts.

## 2. Next.js Frontend

The frontend is built using Next.js (React), styled with Tailwind CSS and shadcn/ui. 

**Rendering Strategy & State Management:**
- **Server-Side Rendering (SSR):** Used exclusively for the public-facing landing page to ensure optimal SEO for discovering the product.
- **Client Components & Direct Data Access:** The authenticated application (both the student flow and teacher dashboard) relies on client-side rendering. Rather than routing CRUD operations through a custom backend API, the frontend reads and writes standard application data directly to Supabase. This approach is secured by Row-Level Security (RLS) policies, providing an instant, Single-Page Application (SPA) feel with zero server round-trip latency per navigation.

**Design Language:**
The UI accommodates two distinct audiences through varied design languages: a vibrant "cartoon-pop" interface for students (optimized for accessibility and engagement) and a calmer, denser, information-rich interface for the teacher dashboard.

## 3. FastAPI Backend & Worker Setup

The backend logic is strictly reserved for the heavy lifting of story generation.

- **Web Service:** A lightweight FastAPI application running on Railway that accepts storybook generation requests and enqueues them.
- **RQ Worker & Redis Broker:** A separate worker service processes the generative LangGraph pipeline. Running this asynchronously isolates long-running model inference from web traffic.
- **Checkpointing and Resumability:** The worker checkpoints pipeline state to Postgres after every completed scene. If a generation job stalls, fails, or is interrupted, it resumes from the exact scene it left off. This prevents wasteful re-generation of already-completed scenes, tightly controlling API costs.

## 4. LangGraph Orchestration

StoryBuddy's core generative pipeline is implemented as a **deterministic state machine** using LangGraph, explicitly avoiding autonomous AI agents.

**Pipeline Flow:**
The process is modeled as a directed graph with explicit nodes:
1. **Input Gate:** Validates text, enforces limits, and runs safety/PII moderation.
2. **Analyze & Segment:** Extracts characters, locations, and narrative arcs, chunking the text into discrete scenes.
3. **Character Bible:** Generates canonical reference images for the identified characters.
4. **Generate Scene:** Conditionally edits the canonical references to fit the scene narrative and art style.
5. **Consistency Check & Regenerate:** A Vision-Language Model (VLM) evaluates the generated scene for character consistency. If it fails, the pipeline performs one targeted regeneration using the VLM's extracted failure reasons, eventually falling back to the "best-of" attempt.
6. **Compose & Export:** Assembles the approved scenes, renders the final HTML template, and exports to PDF.

**Manuscript's ten logical modules ↔ implementation nodes:** the capstone manuscript describes the pipeline
as ten logical modules. They reconcile with the six flow groups above (and the frozen node graph in
`MASTER_SPEC.md` §2, ADR-003/022) as follows — no node is added or renamed here:

| Manuscript module | Implemented as |
|---|---|
| Input Moderation | `input_gate` node |
| Story Analyzer | `analyze` node |
| Scene Segmentation | `segment` node |
| Story Memory Manager | the `StoryMemory` Pydantic contract — every node reads/writes through it, not a node itself |
| Character Bible | `char_bible` node |
| Style Preset | config chosen before generation and frozen (`style.style_preset_id`) — an input to `generate_scene`, not its own node (ADR-007, ADR-022) |
| Prompt Optimizer | folded into `generate_scene`'s prompt construction — a node input, not a separate node |
| AI Scene Generation | `generate_scene` node |
| Consistency Judge & Targeted Regeneration | `consistency_check` + `regenerate` nodes |
| Picture Book Composition | `compose` / `export` nodes |

**Why Not Autonomous Agents?**
Autonomous orchestrator agents introduce non-determinism, unpredictable loops, and high costs. A fixed LangGraph state machine ensures debuggability, bounds worst-case generation costs, and keeps the pipeline's behavior reproducible for the eval harness (Objectives 3–5).

**The Frozen Data Contract:**
Every node communicates through a strictly versioned Pydantic model (`StoryMemory`). Enforcing strict JSON-schema structured output ensures that LLMs cannot inject malformed data that could derail downstream pipeline steps.

## 5. Supabase Setup

Supabase acts as the infrastructural backbone for application state and security.

- **Database (Postgres):** Stores application metadata, user profiles, and LangGraph job checkpoints. 
- **Authentication & RLS:** Employs a **teacher-issued account** model (ADR-017). A teacher creates the classroom and issues each student account — nickname plus an initial password — and the child then logs in and operates the app directly, authoring their own story. There is **no self-serve signup, no email on a student account, and no code that works outside a teacher-created classroom**; password reset is teacher-initiated only. Because the child enters free text, their input routes through input moderation and PII redaction on the same path as any other text (ADR-011) — the account carries no PII, but the *story* may, and redaction rather than non-collection is what handles it. Every generated book is manually reviewed by the teacher before it becomes visible to peers. Strict Row-Level Security ensures data isolation—teachers and students can only access data within their designated classroom.
- **Storage:** Securely hosts generated images, final PDF storybooks, and pre-rendered narration audio (expressive open-weight TTS MP3s — `Chatterbox`, ADR-020) via signed URLs.
- **Realtime:** Pushes state changes from the Postgres job rows directly to the frontend to drive progress bars.

## 6. Rationale Behind Key Architectural Choices

### The Open-Weight Mandate
A core academic requirement for StoryBuddy is the reliance on open-weight models rather than proprietary black-boxes. 
- **Models:** Text parsing uses `qwen/qwen3-32b`, image generation utilizes `Qwen-Image-Edit`, and the VLM consistency judge shipped in Phases 1–2 is a **prompted `gemma-3-27b-it`**. In Phase 2.5, a `Qwen2.5-VL-7B` fine-tuned with QLoRA is evaluated as the study's **Objective 4** — its character-consistency classification performance (precision, recall, F1; F1 primary) against human-established reference labels is a core evaluation objective in its own right, not contingent on deployment. Whether it *replaces* the prompted judge in the shipped product is a separate build decision, gated on matching the incumbent (as documented in `docs/capstone/model_finetuning.md` and `docs/specs/judge-finetune.md` §7.5).
- **Reasoning:** Leveraging open weights guarantees that the infrastructure remains fully self-hostable. It ensures the academic claims of the paper are tied to a transparent, replicable stack that imposes no ongoing vendor lock-in or per-seat licensing costs—an essential factor for deployment in resource-constrained public schools.

### Safety and Moderation
Rather than relying on proprietary filters, StoryBuddy integrates robust open classifiers directly into the worker:
- **Input text** is screened by `Qwen3Guard-Gen` (primary, worker CPU) and `gpt-oss-safeguard-20b`
  (backstop, via OpenRouter) — two independent open-weight classifiers, both Apache-2.0. *(IBM Granite
  Guardian was the originally named backstop; it is not routable on OpenRouter — ADR-011, revised
  2026-07-21c.)*
- **Output images** are evaluated by an NSFW ViT and a safety rubric running on `gemma-3-27b-it`. 
This guarantees independence between filters and prevents unsafe or off-topic content from reaching a child.

### VLM-as-Judge Control Loop
Standard metrics like CLIP image embeddings fail at evaluating non-human and stylized characters. StoryBuddy addresses this by integrating a Vision-Language Model directly into the loop as a judge. The shipped judge is a **prompted `gemma-3-27b-it`**. A `Qwen2.5-VL-7B` fine-tuned with QLoRA is evaluated against human-established reference labels as **Objective 4** — that evaluation runs and is reported regardless of outcome. Separately, it replaces the prompted judge in production only if it also clears the Phase 2.5 *deployment* gate (non-inferiority against the incumbent, no recall regression). The loop's architecture is identical either way — the judge is a swappable part behind two environment variables. 
- **Reason-then-Score Schema:** The judge is forced to output explicit failure reasons (e.g., missing scarf, wrong color) before issuing a binary pass/fail verdict.
- **Targeted Regeneration:** These reasons feed back into the prompt for exactly one retry, making regeneration purposeful rather than a random re-roll, maximizing the chance of producing a consistent character.

### Teacher-Gated Setting over Public Networks
The system inherently rejects a public "social network" model. By tightly scoping sharing features to the classroom and placing the teacher as the mandatory reviewer for published storybooks, StoryBuddy complies with strict data privacy laws for minors. The classroom gallery is display-only — the approved storybook is the only peer-visible artifact.
