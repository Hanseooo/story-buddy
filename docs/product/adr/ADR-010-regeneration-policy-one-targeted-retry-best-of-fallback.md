# ADR-010 — Regeneration policy: one targeted retry, best-of fallback

**Status:** Accepted

**Context:** Naive regeneration with the same prompt is resampling, not refinement — no reason attempt 2 beats attempt 1 — and every attempt costs money and time.

**Decision:** On a failed consistency check, perform **one regeneration with a prompt corrected using the VLM-judge's failure reasons** (strengthen the missing/incorrect attributes). If it still fails, **keep the higher-scoring image** (best-of), never a broken/placeholder page. Control seeds for reproducibility.

**Consequences:** Retries are meaningful (refinement); bounded worst-case cost/latency (~2 attempts/scene); always a shippable page.

**Alternatives:** Higher retry caps — rejected (linear cost, diminishing returns without correction). Placeholder/skip on failure — rejected (worse kid experience than a slightly-off character).
