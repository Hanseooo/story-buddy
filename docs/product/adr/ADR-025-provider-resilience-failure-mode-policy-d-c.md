# ADR-025 — Provider resilience & failure-mode policy (D-C)

**Status:** Accepted (2026-07-22) · resolves **D-C** · gives ADR-024's loop invariant its failure exit ·
defines the backend pattern for CC-3 and CC-9 · amended 2026-08-11

**Amendment (2026-08-11) — Decision 1 was silently reverted in code for three weeks.**

Commit `23b3dca` set `max_retries=0` on all three `OpenAI(...)` clients in `providers.py`, on the stated
premise that "if OpenRouter sends a `Retry-After: 600`, the worker will silently sleep for 10 minutes".
That premise is false against the pinned SDK: `openai/_base_client.py:781` honours the header **only** when
`0 < retry_after <= 60`, and otherwise falls through to exponential backoff capped at
`MAX_RETRY_DELAY = 8.0` (`openai/_constants.py:14`). A 600-second header is ignored. The SDK cannot produce
the sleep the commit was written to prevent — the hang being chased then was almost certainly the Postgres
pooler constraint later recorded as ADR-033.

What `0` did produce was the removal of the pipeline's **only** retry, since no node carries a LangGraph
`RetryPolicy` either. Prod job `beb4ebff` (2026-08-11) died on it: `segment` raised
`openai.RateLimitError` ~1 second after `analyze` succeeded, on a 429 whose own body carried
`retry_after_seconds: 29.8` and `limit_source: upstream_provider_shared_pool` — OpenRouter had already
tried DeepInfra and Venice and found the free shared pool saturated on both. A single ~30s wait would very
likely have cleared it. Instead the book died after `input_gate`, `redact_pii` and `analyze` were paid for,
and the child was shown "the machine got stuck".

Restored to `MAX_RETRIES = 2`, named as a module constant in `providers.py` carrying this history, and
pinned by `test_every_llm_client_retries_transient_failures` — which asserts **every** construction site,
because the two moderation clients are separate `OpenAI(...)` calls and drifted independently once already.

Two things this amendment does **not** claim to fix:

- **Worst-case latency is now real.** `_chat` has a 60s timeout, so a call whose every attempt times out can
  burn ~180s of timeout plus ≤120s of backoff before raising. That fits inside the 900s RQ job timeout
  (`ca2479c`) for one call, not for several in the same book. Untested against the free tier under sustained
  saturation; if books start dying on the RQ timeout instead of on a 429, this is the first suspect.
- **Retrying does not leave the shared pool.** `limit_source: upstream_provider_shared_pool` with
  `is_byok: false` is a property of running on free routing, and `provider.require_parameters: true`
  (ADR-002) narrows the eligible provider set further, which makes saturation *more* likely, not less.
  Retries buy tolerance for a blip; they do not buy capacity. The cause is removed by credits or a BYOK
  provider key, which is a spending decision and deliberately not made here.

Decision 5's enum (`{moderation_input, provider_error, system_error}`) also remains unbuilt — `run_job.py`
maps every non-`content_flagged` exception to `machine`, so a "we're busy, try again" 429 is presented to
the child identically to a genuine defect. Known drift, deliberately not fixed in the same change.

**Context:** The provider *layer* exists (ADR-015, `providers.py`) but its resilience did not. `providers.py`
had no retry/backoff/rate-limit handling and one hardcoded `httpx` timeout (`60.0`); CC-3 (cost
circuit-breaker) and CC-9 (failure screens) were principles with **no backend pattern**. ADR-024 finalized
the per-scene loop and explicitly handed D-C four things: the provider-failure → scene-finalization
guarantee, the moderation fail-branch policy, worker idempotency, and the failure policy behind
`recursion_limit`. This ADR settles the **Phase-1 teeth** and the failure-state **contract**; the four
Phase-2 mechanisms it leans on (the N=3 moderation off-ramp — PRD §11.4; the per-classroom daily cap; the
self-refusal soften-and-retry, ADR-011 mech. 4; the kid-flow failure *screen*) are **deferred to their named
specs**, with any cross-cutting contract field they need frozen here so Phase 2 need not reopen this ADR.

**Decision:**

1. **Provider resilience — transient-vs-hard taxonomy + retry.** Taxonomy: *transient* = connection error,
   timeout, HTTP 429, 5xx → retry with bounded exponential backoff; *hard* = 4xx (400/401/403/422),
   `message.parsed is None`, field-order violation (ADR-004) → fail fast, no retry; *content-refusal* (a model
   refusing a benign scene) is **not** a resilience concern → handed to `self-refusal-fallback` (Phase 2,
   ADR-011 mech. 4). Mechanism: the text/judge path uses the **`openai` SDK's own retry/backoff** — a free,
   MIT-licensed protocol client pointed at OpenRouter, **not** an OpenAI-model dependency (ADR-015; the SDK is
   in the same bucket as OpenRouter/fal — "hosted inference of open weights") — by setting explicit `timeout`
   and `max_retries` on the client, replacing the invisible SDK defaults (~10-min timeout, 2 retries) that are
   wrong for a kid-facing latency budget. The two fal/httpx calls (`fal_client.subscribe`, the image-download
   `httpx.get` — the only genuinely bare paths) get **one small transient-only retry helper** in `providers.py`.
   **No new dependency** (tenacity is only a transitive dep and is deliberately not adopted); resilience stays
   inside the four thin functions (ADR-015 — "not a plugin framework").

2. **Provider-failure → scene-finalization guarantee (the loop invariant's teeth).** `generate_scene` either
   sets `final_image_ref` **or raises** once retries are exhausted; the raise propagates out of the graph to
   `run_job.py`'s top-level `except` → job `failed`. The pipeline **never** ships a placeholder or partial book.
   This extends ADR-010, whose placeholder rejection was about a *slightly-off* image — a hard provider failure
   means *no* image, so failing the job cleanly is the honest outcome (a provider outage is all-or-nothing
   anyway). `recursion_limit` (ADR-024) remains the backstop for a *logic* bug — a scene that never finalizes
   *without* raising — not for the provider-outage case.

3. **Worker idempotency / at-least-once re-pay.** Accepted in Phase 1 and documented. LangGraph checkpoints
   after every node (ADR-024), so the re-pay window is the milliseconds between a fal call returning and the
   checkpoint commit — a rare crash, cents of cost, capped by the per-book breaker (4). Sanctioned upgrade path
   (owned by `image-generator`, optional): on resume, skip the fal call if the deterministic Storage asset path
   already exists.

4. **Per-book cost circuit-breaker (CC-3, per-book half).** A **count-based** breaker on the `cost.image_count`
   contract field (§3): trip → job `failed` when it exceeds `max_scenes × 2 + prelude` — the same bound
   `recursion_limit` derives from (ADR-024), so the domain-level and graph-level backstops share **one number**.
   No pricing table (a breaker catches *runaways*, not accounting drift); `usd_estimate` stays a best-effort
   observability field (CC-5). The per-classroom **daily cap** (PRD §14) is deferred to Phase 2 `rate-limiting`
   — it needs auth (ADR-017). Tier-A testable (MASTER_SPEC §6 already lists "cost circuit-breaker").

5. **Failure-state contract (CC-9 — the field the Phase-2 UI reads).** The `jobs` table gains a `failure_reason`
   enum column — `{moderation_input, provider_error, system_error}`, documented **extensible** (Phase 2 adds
   `off_ramp`, etc.). `run_job.py`'s `except` maps the taxonomized exception to it. The raw `error` string
   becomes **dev-only** (Sentry/logs) and is **never rendered to a child** — it can carry internals or
   un-redacted PII. The kid-flow UI branches on `failure_reason`, never on `error`. ADR-024's char-ref
   moderation fail-branch routes to **one terminal failure node** that stamps this field (the single terminal
   fail target ADR-024 specified); the classifier itself and the N=3 off-ramp remain `moderation-stack` /
   `self-refusal-fallback` (Phase 2).

**Consequences:**
- Every Phase-1 node inherits one resilience policy instead of reinventing it; the loop invariant (ADR-024) now
  has a defined failure exit (raise → job `failed`), not only the `recursion_limit` trip.
- **Consequences to build** (not this decision session — CLAUDE.md §1): the `providers.py` client-config +
  retry helper; the `failure_reason` migration; the count breaker in the loop. Each lands against its module
  spec with Tier-A tests (MASTER_SPEC §6: cost circuit-breaker and N=3 off-ramp are already listed there).
- A hard provider outage fails the whole book (product call, 2026-07-22) — reversible if partial books are
  later wanted; that would need a `failed`-page UI and per-scene real/placeholder tracking, deliberately not
  built now.
- CC-3 and CC-9 gain a backend pattern; MASTER_SPEC §5 now points them at this ADR.

**Alternatives:**
- **tenacity on all four provider functions** — rejected: promotes a transitive dep to a direct one for what
  ~10 lines cover, and double-retries the SDK path unless `max_retries=0` is also set; splits retry policy
  across a decorator library and SDK config.
- **USD-based cost breaker** — rejected: a price-per-model table that drifts and is provider-specific, for a
  breaker whose only job is catching a runaway loop; a count is sufficient and pricing-free.
- **Ship partial books on provider failure** — rejected (2026-07-22): contradicts ADR-010's no-broken-page
  rule and adds Phase-1 state/UI for a rare case.
- **Idempotency key / content-addressed dedup now** — deferred: the re-pay window is milliseconds and the cost
  is cents; the Storage-existence skip is the cheap upgrade if it ever matters.
- **Parse the `error` string for the UI** — rejected: fragile and leaks internals/PII to a child; the enum is
  the contract.
