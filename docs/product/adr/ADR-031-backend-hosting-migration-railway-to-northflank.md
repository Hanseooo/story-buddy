# ADR-031 — Backend Hosting Migration: Railway to Northflank

**Status:** Accepted · **supersedes ADR-009** (Railway, Phase 0)

**Context:** The initial infrastructure design placed the backend (FastAPI, RQ Worker, Redis) on Railway. However, Northflank offers better deployment mechanics, specifically the ability to define a single Docker image and deploy multiple distinct services (API and Worker) from it using different command overrides, along with finer control over networking and resources.

**Decision:** Migrate backend hosting from **Railway to Northflank**.

**Consequences:**
- The deployment process now utilizes a unified `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` Docker image for both FastAPI web and RQ worker services.
- Northflank configuration requires two services pointing to the same repository and Dockerfile, differentiating them by overriding the startup command (e.g. `python -m worker.run_worker` for the LangGraph worker).
- Supabase region considerations (Singapore) still hold, though now relative to Northflank's region options.

**Alternatives:**
- **Stay on Railway** — rejected in favor of Northflank's Docker handling and service orchestration.
- **Render, Fly.io, DigitalOcean App Platform** — previously evaluated in ADR-009 and rejected/deprioritized.
