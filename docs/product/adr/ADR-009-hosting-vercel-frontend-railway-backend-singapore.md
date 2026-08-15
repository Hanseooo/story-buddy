# ADR-009 — Hosting: Vercel (frontend) + Railway (backend), Singapore region

**Status:** Superseded by ADR-031

**Context:** Solo dev; a 3-service backend (web + worker + Redis); user base in the Philippines.

**Decision:** **Next.js on Vercel** (SSR for the public landing page). **FastAPI + RQ worker + Redis on Railway**, Singapore (ap-southeast) region. Render or Fly.io are acceptable equivalents; DigitalOcean App Platform is not preferred for the worker+queue shape.

**Amendment (2026-07-10):** ADR-019 adds a **fourth deployment target** — a scale-to-zero GPU
container serving the fine-tuned judge. It is deliberately the *last* thing built and the *first*
thing cut (ROADMAP de-scope ladder); dropping it returns the judge to OpenRouter with an env-var
change and costs only the "faster and cheaper product" claim, not RQ6.

**Consequences:** Good DX; low regional latency; free-tier spin-down must be handled before demos/study.
Worker RAM is still a real budget, not an afterthought: Presidio+spaCy, the NSFW ViT, and the CPU text gate
all resident in one container (~2–3 GB). **Narration moved to a hosted TTS call (ADR-020, revised)**, so
Kokoro is now the *fallback* rather than a resident requirement — it only adds to this budget if kept warm.
Check the plan tier before Phase 2, not after.

**Alternatives:** Render (fine), Fly.io (more control/ops), DO App Platform (clunkier here), DO droplet (full control, most ops).
