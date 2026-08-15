# ADR-015 — Open-weight model mandate: what "open source" means here

**Status:** Accepted (2026-07-10) · **hardened 2026-07-10b** · **drives the revision of ADR-001, ADR-002, ADR-011**

> **Hardening (2026-07-10b).** The project owner has ruled out **proprietary models entirely** — not
> merely as primaries, but as backstops and accessories. An audit of the stack against that rule
> removes exactly two things: **OpenAI `omni-moderation-latest`** (ADR-011's backstop → replaced by
> IBM Granite Guardian, Apache-2.0 — **subsequently re-routed to `openai/gpt-oss-safeguard-20b`, also
> Apache-2.0 open weights, when Granite proved not routable on OpenRouter; ADR-011 revised 2026-07-21c**)
> and **ElevenLabs TTS** (→ replaced by an open TTS model — Kokoro-82M
> originally, **Chatterbox (MIT) via hosted inference as of ADR-020's 2026-07-17 revision**). Everything else
> already complies: fal.ai and OpenRouter are *hosted inference of open weights* — and the revised narration
> path is the same mechanism; Modal (ADR-019) is infrastructure; LangSmith and Sentry are services, not models.
> Gemma is open-weight (though not OSI-licensed) and therefore survives this ADR's own definition.
>
> The moderation replacement is an unambiguous **upgrade**: meta-llama/llama-guard-4-12b covers 119 languages where Llama
> Guard's Filipino performance was unmeasured. The narration replacement is a deliberate trade, not a free
> win: dropping ElevenLabs removed a *proprietary* dependency, but the expressive open successor (ADR-020,
> revised) is served via a hosted vendor with a small metered cost — open weights, not zero cost. The Kokoro
> CPU fallback preserves the zero-cost, in-infrastructure path when it is wanted.
>
> A downstream benefit the paper should claim: an open-weight, self-hostable pipeline carries **no
> per-seat vendor cost**, which is the difference between a tool a well-funded private school buys and
> one a provincial public school can run. The mandate arrived as a constraint; it is now part of the
> significance (SDG 4).

**Context:** An external requirement (project supervision) directs StoryBuddy to use open-source
models rather than proprietary hosted ones. The phrase is ambiguous, and **the ambiguity is
load-bearing** — three readings imply three different systems:

1. **Open-weight** — the weights are published; who runs them is a separate question.
2. **Self-hosted** — we run the weights on infrastructure we control.
3. **On-device** — the weights run on the user's machine; their data never leaves it.

Reading 1 costs a model swap. Reading 2 adds a GPU service and its ops. Reading 3 rewrites the
deployment (ADR-005, ADR-009) and is currently listed as Future Work (PRD §5.2).

**Decision:**

- **"Open source" is interpreted as "open weight."** A model qualifies if its weights are publicly
  downloadable under a license permitting our use. **Prefer OSI-approved licenses** (Apache-2.0, MIT).
  Community licenses (Meta, Gemma) are accepted only where nothing better exists, and are named
  as such in the adopting ADR.
- **Hosting is orthogonal to openness.** v1 runs on **hosted inference of open weights**
  (fal.ai for images, OpenRouter for text/VLM). Because the weights are open, **self-hosting is
  permanently available to us and never required** — that availability is what satisfies the mandate.
- **StoryBuddy is academic and will not be commercialized.** Non-commercially-licensed weights
  (the FLUX.1-dev family) are therefore *permissible as fallbacks*, but never as the primary choice,
  so the paper can describe an OSI-clean stack.
- **On-device execution remains Future Work** — but it is now *reachable* rather than hypothetical:
  the same weights run quantized on a 12GB consumer GPU.

**Consequences:**

- ADR-003, ADR-005, ADR-006, ADR-007, ADR-009, ADR-010, ADR-012, ADR-013, ADR-014 are **unaffected**.
  The worker calls an HTTP API; only the URL and the payload change.
- Cost is comparable: ~$60–110/month at 200 books/month, dominated by image generation (PRD §15).
- **We now own three responsibilities Google previously owned:** output-image safety filtering
  (ADR-011), watermark/provenance (a real gap — ADR-001), and seed-determinism verification (CC-7).
- Model access is consolidated behind `backend/providers.py` — four thin functions, one implementation
  each. Swapping a model is an env var; swapping a provider is one file. This is not a plugin framework.
- ⚠️ **This ADR does not deliver a privacy guarantee.** The child's text still transits a third party
  (OpenRouter → upstream host). Do not claim privacy preservation in the paper. That claim requires
  reading 3, which is Future Work.
- The research contribution (PRD §3) is **unchanged**: the contribution is the pipeline, not the model.
  Open weights are an implementation constraint, and a substrate the pipeline should survive.

**Alternatives:**

- **Self-host from day 1** — rejected: relocates rather than removes the GPU dependency (drivers, CUDA,
  cold starts, autoscaling, hardware failure) onto a solo dev with a 1-month build. Northflank offers no GPU
  outside its Enterprise plan (ADR-009), so it would also mean a fourth deployment target.
- **On-device / local inference** — rejected for v1: the available hardware is a consumer 8–16GB GPU
  (minutes per image at 1024px, quantized). Fine for prototyping and for demonstrating self-hostability;
  not viable for serving a deployed product or a timed user study.
- **Keep the proprietary stack** — precluded by the mandate.

**Operating assumption (2026-07-10):** the project owner judges that *hosted inference of open weights*
satisfies the requirement, and the build proceeds on that basis. This is **an assumption, not a
supervisor confirmation.** It is cheap to hold and expensive to discover wrong late, so:

- **Confirm it explicitly at the next supervisor checkpoint**, before Phase 2 hardening.
- If it turns out the mandate means *self-hosted*, this ADR is void: the fix is a GPU service and its
  ops (consequences above), and it costs days, not weeks — the pipeline code is unchanged, because
  every vendor call is already isolated in `backend/providers.py`. That isolation is the insurance
  premium for this assumption, and it is why `providers.py` exists.
- If the mandate means *on-device*, the deployment story changes and Phase 4 is promoted. That is a
  scope conversation, not a refactor.
