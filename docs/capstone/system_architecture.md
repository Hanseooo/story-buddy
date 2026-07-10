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

**Why Not Autonomous Agents?**
Autonomous orchestrator agents introduce non-determinism, unpredictable loops, and high costs. A fixed LangGraph state machine ensures debuggability, bounds worst-case generation costs, and is critically important for the academic ablation study (comparing the pipeline turned "ON" vs. "OFF" under controlled conditions).

**The Frozen Data Contract:**
Every node communicates through a strictly versioned Pydantic model (`StoryMemory`). Enforcing strict JSON-schema structured output ensures that LLMs cannot inject malformed data that could derail downstream pipeline steps.

## 5. Supabase Setup

Supabase acts as the infrastructural backbone for application state and security.

- **Database (Postgres):** Stores application metadata, user profiles, and LangGraph job checkpoints. 
- **Authentication & RLS:** Employs a teacher-gated model. Teachers own classrooms and create student profiles (nicknames and avatars); students never supply PII or sign up themselves. Strict Row-Level Security ensures data isolation—teachers and students can only access data within their designated classroom.
- **Storage:** Securely hosts generated images, final PDF storybooks, and pre-rendered narration audio (`Kokoro-82M` MP3s) via signed URLs.
- **Realtime:** Pushes state changes from the Postgres job rows directly to the frontend to drive progress bars.

## 6. Rationale Behind Key Architectural Choices

### The Open-Weight Mandate
A core academic requirement for StoryBuddy is the reliance on open-weight models rather than proprietary black-boxes. 
- **Models:** Text parsing uses `qwen/qwen3-32b`, image generation utilizes `Qwen-Image-Edit`, and the VLM consistency judge is a **prompted `gemma-3-27b-it`**. A fine-tuned `Qwen2.5-VL-7B` is a *candidate replacement* for that judge, evaluated in Phase 2.5 and shipped only if it clears its gate (as documented in `docs/capstone/model_finetuning.md` in the repository).
- **Reasoning:** Leveraging open weights guarantees that the infrastructure remains fully self-hostable. It ensures the academic claims of the paper are tied to a transparent, replicable stack that imposes no ongoing vendor lock-in or per-seat licensing costs—an essential factor for deployment in resource-constrained public schools.

### Safety and Moderation
Rather than relying on proprietary filters, StoryBuddy integrates robust open classifiers directly into the worker:
- **Input text** is screened by `Qwen3Guard-Gen` and IBM `Granite Guardian`.
- **Output images** are evaluated by an NSFW ViT and a safety rubric running on `gemma-3-27b-it`. 
This guarantees independence between filters and prevents unsafe or off-topic content from reaching a child.

### VLM-as-Judge Control Loop
Standard metrics like CLIP image embeddings fail at evaluating non-human and stylized characters. StoryBuddy addresses this by integrating a Vision-Language Model directly into the loop as a judge. The shipped judge is a **prompted `gemma-3-27b-it`**; the fine-tuned `Qwen2.5-VL-7B` replaces it only on passing the Phase 2.5 gate. The loop's architecture is identical either way — the judge is a swappable part behind two environment variables. 
- **Reason-then-Score Schema:** The judge is forced to output explicit failure reasons (e.g., missing scarf, wrong color) before issuing a binary pass/fail verdict.
- **Targeted Regeneration:** These reasons feed back into the prompt for exactly one retry, making regeneration purposeful rather than a random re-roll, maximizing the chance of producing a consistent character.

### Teacher-Gated Setting over Public Networks
The system inherently rejects a public "social network" model. By tightly scoping sharing features to the classroom and placing the teacher as the mandatory reviewer for published storybooks, StoryBuddy complies with strict data privacy laws for minors while enabling a safe environment for peer reflection—a key instrument in measuring reader comprehension for the study.
