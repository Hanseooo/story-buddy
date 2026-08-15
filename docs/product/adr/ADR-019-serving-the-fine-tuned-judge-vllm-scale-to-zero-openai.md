# ADR-019 — Serving the fine-tuned judge: vLLM, scale-to-zero, OpenAI-compatible

**Status:** Accepted (2026-07-10) · **amends ADR-009** (a fourth service) · **serves ADR-018**

**Context:** The fine-tuned judge ships in the live pipeline (ADR-018), and **OpenRouter cannot serve a
custom LoRA.** The judge is called once per scene attempt — roughly 12–24 times per book, inside a flow
that already takes 1–3 minutes.

**Decision:** Merge the LoRA and serve `Qwen2.5-VL-7B` behind **vLLM** on a **scale-to-zero GPU
container** (Modal; RunPod Serverless and Baseten are equivalents). vLLM exposes an **OpenAI-compatible**
endpoint, so `providers.judge()` does not change — only `JUDGE_BASE_URL` and `JUDGE_API_KEY`.

This is the promise of ADR-015 being cashed: *"swapping a model is an env var; swapping a provider is one
file."* Here it is not even one file. The only code concession is that OpenRouter's
`provider.require_parameters` flag is sent **only** to OpenRouter, since vLLM rejects the unknown field.

**Consequences:**
- A fourth deployment target (ADR-009 amended). Cold start ~30–90 s; keep one container warm during study
  sessions (~$1/hr — a three-hour session is pocket change).
- Cost *falls*: ~2,000 judge calls/month at ~3 s each is ~100 GPU-minutes, cheaper than 2,000 Gemma-27B
  API calls (PRD §15).
- **This is the first item on the de-scope ladder.** Dropping it reverts `JUDGE_BASE_URL` to OpenRouter and
  costs only the "faster and cheaper product" claim — Objective 4 survives entirely, evaluated offline. Therefore
  **nothing may hard-depend on this container**, in particular not ADR-011's image moderation.
- The container makes **ShieldGemma 2** affordable as *optional* image-safety hardening (ADR-011).

**Alternatives:**
- **Offline research artifact only** (evaluate the judge in the Tier-B harness; ship prompted Gemma) —
  zero infrastructure, and the **pre-committed fallback** if the schedule compresses.
- **Local GPU behind a tunnel during the study** — free and honest, but the demo and the study then run
  different pipelines. Acceptable emergency posture; say so plainly in the paper if used.
- **HF Inference Endpoints / Fireworks LoRA hosting** — viable; VLM LoRA support is thinner. Revisit only
  if Modal disappoints.
- **CPU inference on the existing worker** — rejected: a 7B VLM on CPU is tens of seconds per call, and
  there are twelve to twenty-four calls per book.
