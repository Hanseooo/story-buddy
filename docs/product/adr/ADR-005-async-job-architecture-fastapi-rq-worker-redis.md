# ADR-005 — Async job architecture: FastAPI + RQ worker + Redis + LangGraph checkpointing

**Status:** Accepted

**Context:** A storybook takes ~1–3 minutes to generate — impossible inside a request/response cycle. A stall must not re-generate already-good (already-paid-for) scenes.

**Decision:** `POST /storybooks` creates a job row and returns `job_id` immediately. A **separate RQ worker** (Redis broker) runs the LangGraph pipeline, **checkpointing to Supabase Postgres after each scene** (`langgraph-checkpoint-postgres`). Frontend tracks progress via **Supabase Realtime** on the job row. Resumability: a stall at scene N resumes from N.

**Consequences:** A 3-service deployment (web + worker + Redis), not one. Robust, resumable, cost-safe. Free-tier worker spin-down must be avoided before demos/study (keep-warm or paid tier).

**Alternatives:** Celery (heavier), ARQ (async-native; adopt later if concurrency needed), Postgres-backed queue to drop Redis (viable simplification — revisit if Redis feels like overhead). Websockets instead of Realtime — more work for the same result.
