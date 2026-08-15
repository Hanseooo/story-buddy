# ADR-014 — Observability provider: LangSmith

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
