# ADR-030 — Observability provider switch: LangSmith to Langfuse

**Status:** Accepted · **amends ADR-014** (LangSmith, 2026-07-22)

**Context:** The research team needs to evaluate per-model USD costs (e.g., "cost for the image model vs cost for the judge") to manage the project budget and analyze generation runs. LangSmith reports token counts only, meaning accurate USD cost tracking would require building and maintaining custom pricing instrumentation inside `providers.py`.

**Decision:** Switch the tracing backend from **LangSmith to Langfuse cloud**.

**Consequences:**
- Langfuse maintains a built-in model pricing table and computes per-model USD costs automatically from token counts. This directly serves the research team's needs with zero custom instrumentation.
- Langfuse is open-source with a generous cloud free tier that fits the project's academic budget.
- The integration moves from LangSmith's zero-code environment variable setup to an explicit code setup (instantiating a `CallbackHandler` per job in `run_job.py`). This is a minor wiring increase but completely acceptable.
- Tool A's evaluation methodology (running offline scripts over exported traces) is entirely unchanged. 
- The research metrics dashboard can predictably link directly to a trace using the format `https://cloud.langfuse.com/project/{id}/traces/{job_id}`.

**Alternatives:**
- **Stay with LangSmith** — rejected. It would force us to manually track token usage and maintain a pricing table in code to calculate costs, duplicating functionality that Langfuse provides natively.
