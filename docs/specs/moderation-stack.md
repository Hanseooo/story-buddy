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
- **Writes:** `scenes[].moderation_status` (`"passed"` | `"failed"`)
- **Invariant:** no scene with `moderation_status != "passed"` is passed to `compose`.
- ⚠️ The written values are `"passed"` / `"failed"`, **not** `"flagged"` — this line and §4c step 4
  said `"flagged"` and no code ever wrote it. A first-check flag is a transient state inside one
  node call (it triggers the soften-and-retry and is resolved before the node returns), so it never
  reaches the contract. `char_ref_mod` is the one that really does persist `"flagged"` (§2b).

## 3. Position in the system map

```
input_gate ──(pass)──► analyze → ... → char_bible → char_ref_mod ──(pass)──► generate_scene
    │                                                     │
 (fail)                                               (fail)
    │                                                     │
 job fails                                            job fails

        ┌──────────────────── more scenes to draw ─────────────────────┐
        │                                                             │
generate_scene → consistency_check → [regenerate] → output_mod ──(pass)──► compose
                                                         │           (book complete)
                                                      (fail)
                                                         │
                                               [one soften-and-retry]
                                                         │
                                               (still fail) → job fails
```

`output_mod` sits **inside** the scene loop (2026-08-13, §4c): one scene is screened as soon as it
finalizes, before the next is drawn. `route_after_output_mod` therefore returns to
`route_next_scene` rather than to `compose` directly, and `compose` is reached only when every
scene is both drawn and screened.

The `moderation_router` (a pure router per ADR-024) reads `input.moderation.passed` after
`input_gate` and `characters[].ref_moderation_status` after `char_ref_mod`. `output_mod` owns
its own one-retry loop and its own fail edge. The `consistency_router` is a separate concern
(owned by the consistency-checker spec).

## 4. Behavior & edge cases

### 4a. `input_gate`

1. Run `meta-llama/llama-guard-4-12b` (OpenRouter API on the worker) on `input.raw_text`.
2. Run `Presidio` (with custom Filipino recognizers — `input-gate-hardening` spec) on
   `input.raw_text` → `input.redacted_text`. Steps 1 and 2 are independent; run concurrently
   (both must complete before the edge fires).
3. If meta-llama/llama-guard-4-12b flags: set `input.moderation = ModerationResult(passed=False, categories=[...])`.
   Router fires → job `failed`. No backstop call needed when the primary already flags.
4. If meta-llama/llama-guard-4-12b passes: call `gpt-oss-safeguard-20b` via OpenRouter (one call per story,
   not per scene — cost is noise). If the backstop flags: same fail path.
5. Both pass → `input.moderation = ModerationResult(passed=True)` → router continues to `analyze`.

**Edge cases:**
- meta-llama/llama-guard-4-12b OOM / load error: catch → route to backstop only; log the primary failure.
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
2. Run `settings.moderation_primary_image_model` — `mistralai/mistral-small-3.2-24b-instruct` since
   2026-08-11 (~~`qwen/qwen3-vl-32b-instruct`~~ before that; ADR-002 amendment), OpenRouter API — the
   primary sexual-content gate.
3. Run `gemma-3-27b-it` with the image safety rubric via OpenRouter — covers violence, gore,
   dangerous content. **Never the fine-tuned judge** (ADR-004 amendment b; the fine-tuned model
   never touches the safety path).
4. Either classifier flagging → `ref_moderation_status = "flagged"` → router fails → job `failed`.
   Character-reference content should never be genuinely harmful; a flag here is almost certainly
   the image model misbehaving, not a borderline creative case. **A primary flag short-circuits
   step 3** — a second opinion cannot change a flag, exactly as §4a step 3 already specifies for
   `input_gate`.
5. All characters pass → router continues to `generate_scene`.

**Edge cases:**
- Image download fails: one retry per ADR-025's transient-error policy, then hard fail.
- **Primary image guard error: degrade to backstop-only; log the failure. Never skip moderation.**
  ~~hard fail~~ — amended 2026-08-11, see below.
- Gemma (backstop) OpenRouter error: hard fail (not a skip). The backstop has nothing behind it, so
  an error there means the image is genuinely unchecked. This is the "proceed without one of the two
  checks" fallback that does not exist.

#### The two gates read ADR-025 the same way now (amended 2026-08-11)

`input_gate` (§4a) and `char_ref_mod` cited the same ADR-025 and implemented **opposite** postures:
on a *primary* classifier error `input_gate` degraded to backstop-only, while `char_ref_mod` raised
`moderation_error` and failed the book.

**The asymmetry was backwards on the risk.** `input_gate` screens **untrusted child-supplied text**;
`char_ref_mod` screens an image *we* generated from text that already passed `input_gate`. The node
downstream of the safer input has no business being the stricter of the two. Worse, it failed the
job **after the reference draws were already paid for** (up to 6 per book, §4.13 of
`character-bible`), and on the Northflank free tier an OpenRouter blip is routine rather than
exceptional — ADR-032's whole reason for moving these classifiers off local models.

`char_ref_mod` now mirrors §4a exactly: primary error → backstop-only; primary flag → short-circuit;
backstop error → hard fail. **What degrades is the call count, never the gate** — the backstop always
runs and can always flag, which is the invariant `test_primary_error_still_lets_the_backstop_flag`
pins. The short-circuit also removes an unconditional second call per character: a 2-character book
spent 4 classifier calls where 2 can decide it, pure waste on 0.2 vCPU / 512 MB.

⚠️ **A reveal retry re-moderates every character on the row, not only the redrawn one** — `char_ref_mod`
iterates `state.characters` unconditionally and has no skip on `ref_moderation_status == "passed"`. The
obvious optimisation — skip a character already marked `"passed"` — is a **CC-1 safety hole** unless
`char_bible`'s targeted mode also clears `ref_moderation_status` on the character it overwrote (it does:
`kid-flow-pause-lifecycle.md` §4.7). A status describes the image that was in `canonical_ref_image` when
it was written; overwriting the image without clearing the status would route an unmoderated image
straight to a child.

### 4c. `output_mod`

1. Load `scene.final_image_ref` from Storage (signed URL, short TTL).
2. Same two-classifier check as `char_ref_mod` (`moderation_primary_image_model` + Gemma safety rubric).
3. Pass → `scene.moderation_status = "passed"` → continue to `compose`.
4. Fail → `scene.moderation_status = "flagged"` → invoke one soften-and-retry on the prompt
   (`self-refusal-fallback` spec strategy) → generate a new image → re-run moderation on it. The
   retry's `ref_paths` comes from `prompt_optimizer.referenced_characters` — ⚠️ **the same list
   `build_prompt` numbered the image roll off, not a copy of the rule.** `_soften_prompt` prepends, so
   the softened prompt still asserts *"Image 2 is the star"* against whatever this node sends to fal
   (issue #23).
5. Still flagged after retry → `scene.moderation_status = "failed"` → job `failed` with
   `failure_reason = "output_moderation_failed"`. No partial book (ADR-025).

⚠️ **Step 0, added 2026-08-13: this node runs once per finalized scene, not once per book.** It
skips any scene already `"passed"`, and `route_next_scene` sends a freshly-finalized, unscreened
scene here before `generate_scene` draws the next one. Granularity resolved — see §8.

⚠️ **CC-5, added 2026-08-13: the flag log names the classifier.** `_check_image` returns a label
(`"primary"` / `"backstop (primary said safe)"` / `"backstop (primary errored)"`) instead of a
bare bool, and `providers.classify_image_{primary,backstop}` log `is_safe` plus the truncated
`safety_reasoning` that ADR-004's reason-before-score ordering already makes the model produce and
that both callers previously discarded. The third label is the one that matters: it distinguishes
two classifiers agreeing from the backstop deciding alone while the primary 429s on OpenRouter's
shared free pool, which is the difference between a real flag and a degraded gate.

**Edge cases:**
- If `final_image_ref` is None (consistency loop produced nothing): the `regeneration-controller`
  owns this case; `output_mod` only runs on a resolved `final_image_ref`.
- **Primary image guard error: degrade to backstop-only; log the failure. Never skip moderation.**
- Backstop error: hard fail with `moderation_error`. Nothing sits behind the backstop, so an error
  there means the image is genuinely unchecked.

#### All three gates read ADR-025 the same way now (amended 2026-08-11, second pass)

Step 2 above has always said *"same two-classifier check as `char_ref_mod`"*, but the alignment
that produced §4b's amendment reached `input_gate` and `char_ref_mod` and **stopped there**.
`output_mod._check_image` was left as `primary and backstop` inside one `try`, so **any** classifier
exception raised `moderation_error` and failed the book.

That left the strictest gate in the pipeline guarding the least risky thing. `output_mod` screens an
image *we* drew, from text `input_gate` passed, from a canonical reference `char_ref_mod` passed —
and it is the **last** gate, so it fails after every scene has been drawn, judged, possibly
regenerated, and paid for. Prod job `f4d0fd74` (2026-08-11) died there on scene **s5** of 7, with
s0–s4 already moderated clean, on an OpenRouter 400 from a text-only provider endpoint (ADR-002
amendment, Instance 3). The provider pinning that landed with it makes that specific 400 unlikely;
this posture is what stops the *next* transient from doing the same thing.

The rule is now uniform across all three gates: **primary error → backstop-only; primary flag →
short-circuit; backstop error → hard fail.** What degrades is the call count, never the gate.

⚠️ The short-circuit is worth more here than in §4b: `output_mod` runs **per scene**, and a
soften-and-retry doubles it, so a 7-scene book spent up to 28 classifier calls against a pool that
is already returning 429s on 0.2 vCPU / 512 MB.

⚠️ **The posture now lives in three nodes and is pinned by three near-identical test trios**
(`test_input_gate_node.py`, `test_char_ref_mod_node.py`, `test_output_mod_node.py`). It drifted once
already, silently, and the spec sentence binding them was not enough to prevent it. If a fourth
classifier gate is ever added, extract the posture into one shared helper rather than writing it a
fourth time.

## 5. Cross-cutting checklist

- [x] **CC-1 Moderation ordering** — this spec enforces the input → char-ref → output ordering.
  Each gate is a separate node; the graph topology makes out-of-order execution impossible.
- [x] **CC-2 PII redaction** — `input_gate` writes `input.redacted_text` (always). All
  downstream nodes that write captions or export excerpts must read `redacted_text`, not `raw_text`.
- [x] **CC-3 Cost control** — text backstop is 1 call/story. Image classifiers are OpenRouter API.
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
- **`char_ref_mod`:** (mirrors the `input_gate` list above since 2026-08-11 — §4b)
  - One character's primary image guard (`moderation_primary_image_model`) flags → router emits "fail".
  - All characters pass both classifiers → router emits "pass".
  - Primary error → backstop-only path fires (primary's error is logged, not raised).
  - Primary error **and** backstop flags → still `"flagged"`. The degraded path must not become a
    bypass; this is the test that makes the one above safe to keep.
  - Primary flags → backstop is **not called** (short-circuit).
  - Gemma (backstop) error on char-ref → hard fail (no "proceed without one check" path).
- **`output_mod`:** (mirrors the `input_gate` list above since 2026-08-11 — §4c)
  - First check fails → soften-and-retry is triggered (verify the retry call fires).
  - Retry passes → `moderation_status = "passed"`.
  - Retry also fails → `moderation_status = "failed"` → job failed.
  - Primary error → backstop-only path fires (primary's error is logged, not raised).
  - Primary error **and** backstop flags → still `"failed"`. The degraded path must not become a
    bypass; this is the test that makes the one above safe to keep.
  - Primary flags → backstop is **not called** (short-circuit), on the retry check as well as the first.
  - Backstop error → hard fail with `moderation_error` (no "proceed without one check" path).
  - The retry's `ref_paths` agrees with the numbered image roll the softened prompt carries, on a
    scene mixing a referenced and an unreferenced character (issue #23).
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

⚠️ **Owed run (2026-08-13): the backstop image rubric was narrowed and has not been re-measured.**
It read *"Flag: violence, gore, sexual content, frightening imagery, dangerous activities"* — and
"frightening imagery" is the genre. Prod job 4f7698d5 lost an 8-scene book on s2, a girl walking up
to the *"big, scary house"* that IS the story, from text `input_gate` had already passed;
`_soften_prompt` cannot rescue that, because prepending "child-safe, gentle" does not remove the
scary house, so the retry flagged too. The primary image rubric is NSFW-only and has no category
that a scary house could trip, which is what identifies the backstop as the classifier that fired.
The hard categories are unchanged; the frightening clause is now qualified ("likely to genuinely
distress a young child") and paired with an explicit do-not-flag list for ordinary storybook
atmosphere. **A loosened safety rubric is exactly what this fixture set exists to catch — run it
against the real classifiers before this is trusted, and add a mild-peril case in both directions.**

There is nothing to run it with yet, and that is the finding. `moderation_cases.py` is the
Post-Phase-2 item above and has not been built; `spikes/phase_05.py moderation` exists but is
text-only, so no probe in this repo can exercise an image rubric in either direction. The narrowed
rubric therefore ships on reasoning alone. **Blocking on Phase 2 entry:** an image arm — a handful
of rendered scenes with expected verdicts (spooky house, dark forest, startled child on the
must-not-flag side; genuine gore and injury on the must-flag side), fed to
`classify_image_primary` and `classify_image_backstop`. Until then the pre-Phase-2 gate in this
section is only half satisfied: it clears the text path and says nothing about the image path.
(`spikes/phase_05.py:434` also still reads `settings.moderation_model`, renamed to
`moderation_primary_model`, so the text arm does not currently run either — separate fix.)

## 8. Linked decisions & open questions

- **ADR-011c** — the two-classifier design, OpenRouter API primary, OpenRouter backstop, and
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
- **`self-refusal-fallback` spec** — ⚠️ **does not own** `output_mod`'s soften-and-retry (corrected
  2026-08-02). That spec covers the model *declining* a prompt; `output_mod`'s retry is the opposite
  trigger — the model complied and a classifier flagged the result. `output_mod` ships its own stock
  softener (`_soften_prompt`, `# ponytail`-marked) and owns it. If that softener proves weak in practice,
  `output_mod` may adopt `self-refusal-fallback`'s; nothing here is blocked on that spec.
- **`input-gate-hardening` spec** (also owns the former `length-guard` row) — clamps at
  `POST /storybooks`, before the job is queued; this spec's assumption that `input_gate` always sees
  final text is satisfied literally.
- **`kid-flow-ui` spec** — owns the kid-appropriate teacher-facing failure message.
- **Resolved 2026-08-13 — output moderation failure granularity.** This spec chose "fail the whole
  job" on a flagged scene (consistent with ADR-025's no-partial-book rule), noted "confirm before
  build", and was built unconfirmed. **Confirmed, with a correction: the verdict stays, the timing
  moves.** Failing the book is still right — a partial book still contradicts ADR-025 and the
  alternative was never taken. What was wrong was screening at the *end*, which meant the gate
  could only ever fire once every scene had been drawn, judged, possibly regenerated, and paid for.
  Prod job 4f7698d5 (2026-08-12) died on s2 of 8 and took 11 fal images down with it; f4d0fd74
  (2026-08-11) died on s5 of 7. Both stop two images in under §4c step 0. The safety posture is
  untouched — only the bill for enforcing it.
- **Open — backstop routing error policy:** this spec treats a backstop routing error as a hard
  job failure. Alternative: proceed on primary-only if the backstop is unreachable (not the same
  as a "pass" verdict from the backstop). Decide at build time with a new ADR amendment if needed.
- **Open — `config.py` field shape for a OpenRouter API primary:** `moderation_model` currently
  holds `meta-llama/llama-guard-4-12b` (the ADR-011c-demoted fallback) because the real primary
  is not an OpenRouter id, and `moderation_backstop_model` is unset so the Phase-0.5 probe stays
  opt-in. Both are commented in place. **This spec owns fixing them** — decide the field shape
  (local weights path vs. model id, one field or two) when building `input_gate`.
- **Open — worker RAM at Phase 2 entry:** Presidio+spaCy (~200 MB), qwen/qwen3-vl-32b-instruct (~350 MB),
  meta-llama/llama-guard-4-12b (~1.2 GB) are all OpenRouter API. ROADMAP warns to check the Northflank plan
  tier at the *start* of Phase 2, not the end. Budget these before writing the first line of code.
