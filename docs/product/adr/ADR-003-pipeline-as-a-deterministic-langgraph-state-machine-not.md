# ADR-003 — Pipeline as a deterministic LangGraph state machine (not an autonomous agent)

**Status:** Accepted

**Context:** The pipeline is a fixed sequence with only two real branch points (moderation pass/fail, consistency pass/fail). An autonomous "orchestrator agent" that decides routing adds nondeterminism, cost, and debugging difficulty, and harms research reproducibility.

**Decision:** Model the pipeline as an explicit **LangGraph state machine** with defined nodes and conditional edges only where genuinely needed. Call model APIs directly through `backend/providers.py` — no agent framework in between.

**Consequences:** Deterministic, debuggable, reproducible (matters for pre-registration and the judge classification evaluation, Objective 4). Built-in checkpointing (see ADR-005). No autonomous-agent overhead.

**Alternatives:** Autonomous agent orchestrator — rejected (nondeterminism, cost, reproducibility). Plain Python without LangGraph — viable but loses checkpointing/persistence and graph structure for free.
