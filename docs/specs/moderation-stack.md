# Feature Spec — moderation-stack

**Status:** draft · **Phase:** 2 · **Owner:** three gate nodes:
`backend/pipeline/input_gate.py`, `backend/pipeline/char_ref_mod.py`, `backend/pipeline/output_mod.py`
**Derived from:** MASTER_SPEC §2 (system map) · **Rationale:** ADR-011c, ADR-004 (amendment b),
ADR-017, ADR-025

> One spec covers all three nodes because they share the same ADR, the same two-classifier design
> philosophy, and the same conditional-edge pattern (ADR-024: "two pure routers — moderation,
> consistency"). Each node has its own file. The stub `input_gate` added in Phase 1 is replaced
> by the real implementation here; `char_ref_mod` and `output_mod` are new files.

## 1. Purpose

Enforce ADR-011's three-layer safety mandate: (1) text input is safe for a child to submit and
PII is redacted before any downstream use, (2) the canonical character reference image is safe
before scene generation uses it, (3) every output scene image is safe before it reaches compose.
No unmoderated content ever reaches a child. Ordering is non-negotiable: input text → char-ref →
output image.

## 2. Contract slice

### 2a. `input_gate`
- **Reads:** `input.raw_text`
- **Writes:** `input.moderation` (`ModerationResult`), `input.redacted_text` (always set, even on
  flag — the teacher sees the redacted version regardless)
- **Invariant:** `input.redacted_text` is never `None` after this node runs.
  `input.moderation.passed` is the signal the moderation router reads.

### 2b. `char_ref_mod`
- **Reads:** `characters[].canonical_ref_image` (durable Storage path)
- **Writes:** `characters[].ref_moderation_status` (`"passed"` | `"flagged"`)
- **Invariant:** every character has `ref_moderation_status = "passed"` before `generate_scene` runs.

### 2c. `output_mod`
- **Reads:** `scenes[].final_image_ref` (durable Storage path for the scene being checked)
- **Writes:** `scenes[].moderation_status` (`"passed"` | `"flagged"`)
- **Invariant:** no scene with `moderation_status != "passed"` is passed to `compose`.

## 3. Position in the system map

```
input_gate ──(pass)──► analyze → ... → char_bible → char_ref_mod ──(pass)──► generate_scene
    │                                                     │
 (fail)                                               (fail)
    │                                                     │
 job fails                                            job fails

generate_scene → consistency_check → [regenerate] → output_mod ──(pass)──► compose
                                                         │
                                                      (fail)
                                                         │
                                               [one soften-and-retry]
                                                         │
                                               (still fail) → job fails
```

The `moderation_router` (a pure router per ADR-024) reads `input.moderation.passed` after
`input_gate` and `characters[].ref_moderation_status` after `char_ref_mod`. `output_mod` owns
its own one-retry loop and its own fail edge. The `consistency_router` is a separate concern
(owned by the consistency-checker spec).

## 4. Behavior & edge cases

### 4a. `input_gate`

1. Run `Qwen3Guard-Gen 0.6B` (CPU-resident on the worker) on `input.raw_text`.
2. Run `Presidio` (with custom Filipino recognizers — `input-gate-hardening` spec) on
   `input.raw_text` → `input.redacted_text`. Steps 1 and 2 are independent; run concurrently
   (both must complete before the edge fires).
3. If Qwen3Guard-Gen flags: set `input.moderation = ModerationResult(passed=False, categories=[...])`.
   Router fires → job `failed`. No backstop call needed when the primary already flags.
4. If Qwen3Guard-Gen passes: call `gpt-oss-safeguard-20b` via OpenRouter (one call per story,
   not per scene — cost is noise). If the backstop flags: same fail path.
5. Both pass → `input.moderation = ModerationResult(passed=True)` → router continues to `analyze`.

**Edge cases:**
- Qwen3Guard-Gen OOM / load error: catch → route to backstop only; log the primary failure.
  Never silently skip moderation entirely — the gate always requires at least one complete pass.
- Backstop OpenRouter timeout / 4xx / 5xx: treat as a hard error per ADR-025 (not a soft skip).
  Fail the job with `failure_reason = "moderation_error"`.
- Input over the hard word cap (ADR-012): `length-guard` truncates before `input_gate` runs;
  `input_gate` always sees the final text.
- Abuse disclosure (e.g., a child describing harm done to them): flag it. The text is unsafe to
  proceed with — the child needs adult intervention, not a storybook. Flagging correctly routes
  to the teacher. This is not a false-positive case.

### 4b. `char_ref_mod`

1. Download each character's `canonical_ref_image` via a short-TTL signed URL.
2. Run `Falconsai/nsfw_image_detection` (ViT-base 86M, CPU-resident) — specialist sexual-content gate.
3. Run `gemma-3-27b-it` with the image safety rubric via OpenRouter — covers violence, gore,
   dangerous content. **Never the fine-tuned judge** (ADR-004 amendment b; the fine-tuned model
   never touches the safety path).
4. Either classifier flagging → `ref_moderation_status = "flagged"` → router fails → job `failed`.
   Character-reference content should never be genuinely harmful; a flag here is almost certainly
   the image model misbehaving, not a borderline creative case.
5. All characters pass → router continues to `generate_scene`.

**Edge cases:**
- Image download fails: one retry per ADR-025's transient-error policy, then hard fail.
- Gemma OpenRouter error: hard fail (not a skip). The safety path has no "proceed without one
  of the two checks" fallback.

### 4c. `output_mod`

1. Load `scene.final_image_ref` from Storage (signed URL, short TTL).
2. Same two-classifier check as `char_ref_mod` (Falconsai ViT + Gemma safety rubric).
3. Pass → `scene.moderation_status = "passed"` → continue to `compose`.
4. Fail → `scene.moderation_status = "flagged"` → invoke one soften-and-retry on the prompt
   (`self-refusal-fallback` spec strategy) → generate a new image → re-run moderation on it.
5. Still flagged after retry → `scene.moderation_status = "failed"` → job `failed` with
   `failure_reason = "output_moderation_failed"`. No partial book (ADR-025).

**Edge case:**
- If `final_image_ref` is None (consistency loop produced nothing): the `regeneration-controller`
  owns this case; `output_mod` only runs on a resolved `final_image_ref`.

## 5. Cross-cutting checklist

- [x] **CC-1 Moderation ordering** — this spec enforces the input → char-ref → output ordering.
  Each gate is a separate node; the graph topology makes out-of-order execution impossible.
- [x] **CC-2 PII redaction** — `input_gate` writes `input.redacted_text` (always). All
  downstream nodes that write captions or export excerpts must read `redacted_text`, not `raw_text`.
- [x] **CC-3 Cost control** — text backstop is 1 call/story. Image classifiers are CPU-resident.
  Moderation cost is negligible but should be logged for the paper's cost accounting.
- [x] **CC-4 Security** — all image checks fetch via short-TTL signed URL; no raw paths leave
  the worker. No moderation result is stored as a URL.
- [x] **CC-5 Observability** — log classifier name, verdict, and latency per call. A MISS is a
  named tracing event (not a silent counter) so it's findable in LangSmith.
- [ ] **CC-6 Accessibility** — N/A (pipeline nodes). The kid-appropriate failure message is the
  `kid-flow-ui` spec's concern.
- [ ] **CC-7 Reproducibility** — moderation gates are deterministic given fixed model weights.
  No seed coupling.
- [ ] **CC-8 Kid vs parent design** — N/A (pipeline nodes).
- [x] **CC-9 Failure states** — all fail paths set `jobs.failure_reason` via the ADR-025 enum
  (`"content_flagged"` / `"moderation_error"` / `"output_moderation_failed"`). Teacher sees a
  reason; the job row is never left in a silent broken state.
- [x] **CC-10 Checkpointing** — LangGraph checkpoints after each node. A worker crash mid-
  moderation resumes from the last checkpoint, not from scratch.

## 6. Deterministic tests (CI)

All classifier calls mocked (`backend/providers.py` seam):

- **`input_gate`:**
  - Primary flags → `moderation.passed = False`; router emits "fail" without calling backstop.
  - Primary passes, backstop flags → `moderation.passed = False`.
  - Both pass → `moderation.passed = True`.
  - Primary OOM / error → backstop-only path fires (primary's error is logged, not raised).
  - Backstop error → job failure (not a silent skip).
  - `redacted_text` is always populated (mock Presidio returns a fixed redacted string);
    verify it is set even when moderation fails.
- **`char_ref_mod`:**
  - One character's Falconsai flags → router emits "fail".
  - All characters pass both classifiers → router emits "pass".
  - Gemma error on char-ref → hard fail (no "proceed without one check" path).
- **`output_mod`:**
  - First check fails → soften-and-retry is triggered (verify the retry call fires).
  - Retry passes → `moderation_status = "passed"`.
  - Retry also fails → `moderation_status = "failed"` → job failed.
- **All nodes:** images fetched via signed URL (mock the URL-minting call to return a fixture
  URL); verify no raw Storage path is passed directly to a classifier.

## 7. Eval / quality checks

**Pre-Phase-2 gate:** Phase 0.5 probe 4 (`spikes/phase_05.py moderation`) must show no combined
miss in either direction before Phase 2 entry (ROADMAP §0.5). See probe output for per-model
breakdown — if only the backstop caught a harmful case, the backstop is load-bearing and must
not be marked optional.

**Post-Phase-2:** maintain a living fixture set in `tests/fixtures/moderation_cases.py` (Filipino
and Taglish cases, both directions). Feed it to the real classifiers in an offline nightly run
(not CI). Extend the set as production finds edge cases the probe missed.

## 8. Linked decisions & open questions

- **ADR-011c** — the two-classifier design, CPU-resident primary, OpenRouter backstop, and
  ordering constraint this spec implements.
- **ADR-004 (amendment b)** — the fine-tuned judge never sits on the safety path.
- **ADR-025** — hard-error policy: no partial book on moderation failure; `failure_reason` enum
  contract for CC-9.
- **`input-gate-hardening` spec** (2026-08-02; absorbed the former `filipino-pii-recognizers` stub) —
  owns the custom Presidio recognizers this spec depends on. Shipping with stock Presidio is
  permissible only with an explicit `# ponytail: stock Presidio, Filipino names leak` comment
  and a filed spec. ⚠️ It also changes `redact_pii`'s **output form** for person entities from
  `<PH_PERSON>` placeholders to consistent pseudonyms, because `analyze` and `segment` build the
  story *from* `redacted_text`. CC-2 is unchanged; the replacement token is not.
- **`self-refusal-fallback` spec** — owns the soften-and-retry strategy `output_mod` invokes.
- **`input-gate-hardening` spec** (also owns the former `length-guard` row) — clamps at
  `POST /storybooks`, before the job is queued; this spec's assumption that `input_gate` always sees
  final text is satisfied literally.
- **`kid-flow-ui` spec** — owns the kid-appropriate teacher-facing failure message.
- **Open — output moderation failure granularity:** this spec chooses "fail the whole job" on a
  flagged scene (consistent with ADR-025's no-partial-book rule). An alternative — silently drop
  the scene and compose the rest — contradicts ADR-025. Confirm before build.
- **Open — backstop routing error policy:** this spec treats a backstop routing error as a hard
  job failure. Alternative: proceed on primary-only if the backstop is unreachable (not the same
  as a "pass" verdict from the backstop). Decide at build time with a new ADR amendment if needed.
- **Open — `config.py` field shape for a CPU-resident primary:** `moderation_model` currently
  holds `meta-llama/llama-guard-4-12b` (the ADR-011c-demoted fallback) because the real primary
  is not an OpenRouter id, and `moderation_backstop_model` is unset so the Phase-0.5 probe stays
  opt-in. Both are commented in place. **This spec owns fixing them** — decide the field shape
  (local weights path vs. model id, one field or two) when building `input_gate`.
- **Open — worker RAM at Phase 2 entry:** Presidio+spaCy (~200 MB), Falconsai ViT (~350 MB),
  Qwen3Guard-Gen 0.6B (~1.2 GB) are all CPU-resident. ROADMAP warns to check the Railway plan
  tier at the *start* of Phase 2, not the end. Budget these before writing the first line of code.
