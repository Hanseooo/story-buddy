# Feature Spec — moderation-stack

**Post-defense amendment:** §9 records the moderation-calibration interviews. The 2026-10-27
technical completion in §9.9 supplies concrete contracts and project policy, explicitly accepted
with ADR-080 on 2026-10-27 (“accept all”). Synthetic-only, feature-off implementation is authorized.
Ticket 05's scene hold and enabling contracts are implemented; §§1–8 describe baseline behavior. Tickets 06–15, audit 01 and real-child release review
remain outstanding. Owner acceptance does not establish externally validated policy or efficacy.

**Status:** amendment accepted (2026-10-27), ticket 05 implemented, successors pending · **Phase:** 2 · **Owner:** three gate nodes:
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
  Fail the job with `failure_reason = "moderation_error"`. The node raises it (2026-09-16) rather
  than writing `categories=["moderation_error"]` for the router: a written result survives in the
  checkpoint, so a resume skipped the backstop and ended with an empty story.
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
4. Either classifier flagging → `ref_moderation_status = "flagged"` and `canonical_ref_image`
   cleared → router redraws once, then fails (`reference-moderation-retry.md` §4.2;
   `MAX_MOD_REDRAWS = 1`). Character-reference content should never be genuinely harmful; a flag
   here is almost certainly the image model misbehaving, not a borderline creative case — which
   is exactly what a redraw is for. **A primary flag short-circuits step 3** — a second opinion
   cannot change a flag, exactly as §4a step 3 already specifies for `input_gate`.
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

⚠️ **A reveal retry re-moderates only the characters whose reference actually changed** — since
`reference-moderation-retry.md` §4.1, `char_ref_mod` skips a character already marked `"passed"`.
That optimisation is a **CC-1 safety hole** unless every path that overwrites `canonical_ref_image`
also clears `ref_moderation_status`, and both now do: `char_bible`'s targeted mode
(`kid-flow-pause-lifecycle.md` §4.7) and its untargeted mint
(`reference-moderation-retry.md` §4.3). A status describes the image that was in
`canonical_ref_image` when it was written; overwriting the image without clearing the status would
route an unmoderated image straight to a child. **Anything that adds a third write path to
`canonical_ref_image` must clear the status too, or delete the skip.**

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

⚠️ **The step-4 retry image ships without a consistency verdict (#78, traced 2026-09-04).**
`route_next_scene` sends a scene onward once it has a `final_image_ref` and a `moderation_status`
— it never routes back to `consistency_check` — so the softened redraw is delivered having been
moderated but never judged for character consistency. The regenerate loop, ADR-046's clean-base
retry and the `generate_scene` correction path all re-enter `consistency_check` and are **not**
affected; ADR-046/047/049/050 do not close this one, because none of them touch `output_mod`.

The trace found one thing that was outright wrong and one that is a standing decision:

- **Fixed here.** The retry attempt was recorded `Attempt(..., passed=True)`. `passed` is the
  consistency verdict — it sits beside `vlm_verdict` — and `compose.outcome()` reads it first, so
  an unjudged page was reported **`passed`** in the CC-5 provenance record. It is now `passed=False`
  with no verdict, which `outcome()` already classifies as **`unchecked`**: the category that exists
  for exactly this.
- **Open, and an ADR decision, not an inline one.** Whether an unjudged image should be delivered at
  all is a routing change — it would have to preserve ADR-003 deterministic routing, the bounded
  retry budget, `check_image_budget()` accounting (ADR-025 D4), the per-scene moderation order, and
  AGENTS.md's `RECURSION_LIMIT` arithmetic. Not decided here. The residual is now visible in the
  record instead of hidden behind a verdict that was never issued.

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
  named tracing event (not a silent counter) so it's findable in Langfuse.
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
(`spikes/phase_05.py` now reads `settings.moderation_primary_model` and the configured backstop
after moderation-calibration ticket 04, 2026-10-26. Its import check passes; the paid text probe
has not been rerun. This direct `structured_text` probe is not production-path evidence.)

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
- ~~**Open — `config.py` field shape for a OpenRouter API primary.**~~ Resolved: `moderation_model`
  no longer exists. `backend/app/config.py` has four fields, all OpenRouter model ids:
  `moderation_primary_model` (`meta-llama/llama-guard-4-12b`), `moderation_backstop_model`
  (`openai/gpt-oss-safeguard-20b`), `moderation_primary_image_model`
  (`mistralai/mistral-small-3.2-24b-instruct` since 2026-08-11) and
  `moderation_backstop_image_model` (`google/gemma-3-27b-it`). (Issue #28, 2026-10-09.)
- **Open — worker RAM at Phase 2 entry:** since ADR-032, only Presidio+spaCy (`en_core_web_sm`,
  about 200 MB) stays resident in the worker. Every classifier is an OpenRouter API call and uses no
  worker RAM; the local ViT and the local text gate were removed (`backend/providers.py`, the
  ADR-032 markers). The 2026-08-02 text listed resident sizes for models that are remote. (Issue #28,
  corrected 2026-10-09.)

## 9. Moderation calibration and teacher-held stories

**Readiness:** Accepted for synthetic-only, feature-off implementation (2026-10-27). The owner
explicitly accepted §9.9, ADR-080 and the audit-dependency exception. §9.9 takes precedence over
earlier interview statements that contracts remain undefined. Ticket 02 is complete as a spec;
ticket 05 is ready, with successors following their predecessor dependencies. Audit 01 remains
open. Changed classifier prompts, paid replay, production enablement and real-child use remain
unauthorized by this acceptance; evidence and external release-review gates still apply.

### 9.1 Purpose and scope

A child should not lose their writing or repeatedly restart a book solely because an automated
safety check requests review. Hold at the first flag, let the classroom teacher inspect the
material in context, and resolve the hold through an explicit allow, replacement-picture or stop
decision. Explain the criteria and distinguish shared safety from optional classroom preferences.
The teacher applies a written policy; automated categories are advisory, not unconditional vetoes.
This does not authorize genuinely prohibited material.

Intended users are the child author and classroom teacher. Researcher inspection is the accepted
ADR-079 companion change and grants no teacher authority. The documented audience is Grade 5–6,
ages 10–12 (PRD §4; RESEARCH_PROTOCOL §11), now explicitly selected for the proposed policy.
Current moderation prompts still say ages 5–12: verified drift to correct in a separately
authorized implementation. Its causal effect on false alarms is unmeasured. No existing school
policy or educator/ethics reviewer was identified; §9.5.1 is an agreed proposal, not a validated
rubric (OD-01).

**Verified existing constraints:** title checks in backend/app/main.py reject before a job exists;
input_gate fails flagged text; char_ref_mod clears a flagged reference and permits a capped redraw;
output_mod softens/redraws once before failing a still-flagged scene. Reveal is the only current
interrupt. BookReviewDialog assumes completed job.pages and editorial ReviewDecision actions.
None of these interfaces already supports the proposed holds. The hosted worker revision for the
candidate run has not been established.

**Scope boundary:** rank 2 owns criteria, first-flag holds, inspection/resolution and necessary child
waiting/recovery. Rank 3 owns comments, highlights, editorial feedback and its revision workflow.
Rank 4 owns appearance/custom prompts and child-directed redraws; rank 5 owns general pipeline
speed. Ranks 1, 6, 7 and 8 retain onboarding, roster views, AI-assisted editorial review and story
construction quality. Safety release never implies classroom-sharing approval. Reuse story/picture
inspection where appropriate, without building future comment infrastructure or duplicating content.

**End-to-end acceptance journeys:**

- **J-01:** submit → first title/text/reference/scene safety flag → durable hold → child leaves and
  returns → teacher inspects/allows exact content → continue without replaying completed paid work;
  later generated assets still receive moderation.
- **J-02:** inspect held picture → request replacement preserving scene intent, references and style
  within budget → new safety and scene-consistency checks → continue under existing selection
  limits on clearance or create a new hold at its first safety flag.
- **J-03:** teacher or child cancels stop confirmation → hold unchanged; confirms stop → run ends without
  deleting writing → child returns to bookshelf and can reuse writing via existing new submission.
- **J-04:** enable optional themes → new submission captures settings → check submitted text once →
  group detected enabled themes into one review before paid generation → teacher accepts → no
  repeated optional-theme holds on unchanged submission; later image safety flags still hold.
- **J-05:** ordinary researcher opens failed/unapproved run under ADR-079 → existing full projected
  viewer → no release/resume/editorial/moderation authority.
- **J-06:** teacher discovers mistaken clearance → withdraw safety clearance → affected content
  hidden from child/gallery, further generation blocked, story returns to teacher review → no
  automatic restoration of gallery approval. Prior exposure cannot be undone.

These are future acceptance outcomes, not executed tests.

### 9.2 User stories and acceptance criteria

#### US-01 — Teacher help at the first flag

As a child author, I want a flagged submission to wait for my teacher, so that I do not have to
diagnose the classifier or restart my work.

Applies: SH-01, SH-03, SH-05, SH-07, SH-10, SH-12.

- **AC-01:** When a title, story text, character reference or scene picture first receives a safety
  flag, hold before any automatic moderation redraw and before advancing generation past that hold.
  Show neutral teacher-help status rather than a failed-story verdict or moderation category.
  Generated flagged pictures stay hidden from the child pending authorized release.
- **AC-02:** When shared and applicable optional checks pass, continue without this extra teacher
  decision. Service errors/missing verdicts follow SH-01, not a fabricated safety flag. Final-book
  sharing approval remains separate.

#### US-02 — Leave and return without losing the writing

As a child author, I want to leave a waiting story and return later, so that teacher availability
does not trap me on a progress screen.

Applies: SH-03, SH-04, SH-05, SH-08, SH-11.

- **AC-03:** Leaving offers an in-app bookshelf exit and does not cancel the hold. The bookshelf
  identifies waiting stories and provides a return route. Reload/return on an authorized device
  loads persisted current state before observing subsequent updates.
- **AC-04:** If no teacher acts for hours or days, waiting remains honest: no new automatic review
  deadline, fake countdown or time-based release. Existing lifecycle/deletion/access rules apply;
  missing or inaccessible content instead has an honest unavailable state and exit.

#### US-03 — Inspect the story and pictures in context

As a classroom teacher, I want the story and available pictures together, so that I can judge
the actual material rather than an isolated flag label.

Applies: SH-02, SH-03, SH-08, SH-09, SH-11.

- **AC-05:** In existing classroom Books, find held submissions in a distinct **Needs your help**
  queue, not a separate moderation dashboard. Opening one shows safety actions distinctly from
  completed-book approval. Queue details are OD-06; complete states are SH-08.
- **AC-06:** Show the privacy-processed title/story and available references/scene pictures,
  including the exact held candidate. Distinguish not-yet-generated from unavailable/signing-failed
  pictures. Never generate extra pictures just to fill the preview.
- **AC-07:** Initially hide flagged pictures from teachers behind a warning and **Show picture
  to review**. Keep story context and the recorded reason available. Reveal is teacher-only and
  does not release. If the exact picture cannot load, allowing it is unavailable; offer read
  recovery rather than automatically generating a replacement.

#### US-04 — Understand the criteria and the reason for this hold

As a teacher, I want a criteria reference and a per-hold explanation, so that I understand the
general policy and its application to this submission.

Applies: SH-01, SH-03, SH-05, SH-06, SH-08.

- **AC-08:** **Review criteria** distinguishes shared safety from optional classroom preferences.
  Completed criteria define scope, triggering conditions, permitted exceptions, contextual boundary
  examples and documented basis. Agreed boundaries are §9.5.1; complete rubric text,
  educator/source review and validation remain OD-01;
  preset names alone are not the rubric or evidence of accuracy.
- **AC-09:** Each hold shows the applicable criterion, shared-safety versus optional origin,
  recorded explanation and applicable submission settings. Missing reasoning is explicitly
  unavailable, never invented. Historical models/settings are shown only when recorded; today's
  configuration is not evidence of an older call. Persistence/versioning remains OD-03.

#### US-05 — Resolve safety without approving publication

As a teacher, I want to allow, replace or stop the held content, so that I can resolve a flag
without granting unrelated sharing or editing permissions.

Applies: SH-01, SH-02, SH-03, SH-07, SH-08, SH-09, SH-11.

- **AC-10:** If the teacher determines the exact held title/story/picture meets the written policy,
  allow it to continue. Do not require rewriting text solely to appease a classifier. No automated
  category has an unconditional veto. Privacy processing, provider restrictions, authorization
  and checks on later generated assets remain binding. After inspection, require an explicit
  confirmation that the exact content meets the named criterion; record the teacher, exact
  content/version, criterion and policy version. No mandatory written justification. An uncertain
  teacher leaves it held, returns later, requests a permitted replacement or stops; no new second-
  reviewer service. Release/withdrawal contracts remain OD-02/OD-03.
- **AC-11:** Once a teacher accepts an optional theme, the same unchanged submission does not
  repeatedly hold solely for that theme. New shared-safety flags still hold their exact content.
  Optional themes are checked in submitted text once, grouped before paid generation (AC-14),
  not screened again in each picture. Theme identity/version rules remain OD-04.
- **AC-12:** A teacher-requested replacement respects existing image/spend limits and undergoes
  moderation. Its first flag returns it to review. Exhausted budget disables replacement with an
  explanation, while inspection/leaving/permitted non-generation decisions remain available.
  Preserve scene intent, approved references and style; do not use the existing generic
  safety-softened prompt or add teacher-written creative instructions. A replacement scene gets
  a fresh consistency judgment with its actual result recorded, using established selection and
  attempt limits. Safety clearance does not imply consistency. Never silently reselect a rejected
  picture. No extra budget or unbounded retries. Exhausted-attempt selection, exact routing and
  provider-refusal recovery remain OD-05; this does not introduce a scene judge for references.
- **AC-13:** **Stop this story** requires confirmation. Cancelling leaves the hold unchanged.
  Available to the classroom teacher and the child author of a held story; leaving is a distinct
  action that keeps waiting. Confirming ends this run without deleting writing, subject to the
  existing lifecycle. Child stop and teacher release must reconcile to one current outcome.
  Confirmed deletion remains a separate destructive action under the existing deletion lifecycle,
  extended to held stories without a new retention exemption (OD-08). The child
  gets neutral stopped-story copy, a bookshelf exit and access to the existing new-submission path
  to reuse writing. No teacher reopen or picture carry-over guarantee. Exact recovery copy and
  transfer/navigation-failure behavior remain OD-07, not a new epic 3 revision workflow.
- **AC-19:** **Withdraw safety clearance** lets the classroom teacher correct a mistaken release.
  Hide affected content from child and gallery views, block further generation, and return the
  story to teacher review while preserving writing and decision history. A provider call already
  running may finish; its result must not bypass the withdrawal. Do not claim prior exposure was
  undone. Withdrawal does not automatically restore previous gallery approval on a later release.
  Exact authorization, withdrawal/resume races, asset access and publication-state contracts
  remain OD-02/OD-03; no new emergency administrator workflow is implied.

#### US-06 — Request extra classroom review without weakening safety

As a teacher, I want understandable optional review switches, so that I can request additional
review without changing the shared safety requirements.

Applies: SH-01, SH-02, SH-03, SH-06, SH-08, SH-10.

- **AC-14:** Provide the three agreed optional themes: **mild suspense/spooky settings**;
  **non-graphic fighting, arguments or bullying within a story**; and **sadness, loss or separation**.
  All start off. Enabling one requests extra review, not automatic rejection or an unsafe label.
  Check only submitted text, once, and group all detected enabled themes into one teacher review
  before paid image generation. Acceptance covers those themes for that unchanged submission.
  Do not add per-picture optional-theme screening: a theme introduced only visually does not
  independently trigger optional review, but every picture still receives shared-safety checks.
  Exact definitions, exceptions, detector and versioning remain OD-01/OD-04.
- **AC-15:** Turning a switch off removes only that extra classroom review request; explain that
  shared safety checks still apply. No blanket lenient mode, alternate shared rubric or free-text
  custom flags. Capture settings per submission: later changes affect new submissions only.
  They do not change existing settings, silently release a hold or start paid generation.
  Shared-policy changes follow SH-06; incident containment beyond individual withdrawal remains OD-11.

#### US-07 — Researcher inspection of failed and unapproved runs

As a researcher, I want the existing full projected viewer for failed/unapproved runs, so that
I can investigate rather than infer causes from summary labels.

Applies: SH-02, SH-03, SH-06, SH-09.

- **AC-16:** Apply accepted ADR-079 and the access amendment in
  [research-run-browser](research-run-browser.md), specifically §§2, 4, 5.1, 5.4, 6 and 8.
  Those sections are authoritative for researcher title/link eligibility, every-run access,
  exclusions, signed images, failure states, Langfuse controls and acceptance evidence. This
  companion change's implementation/verification status is recorded in ticket 03; it grants no
  teacher decision authority.

#### US-08 — Evidence rather than assumed moderation accuracy

As the project owner, I want measured results distinguished from hypotheses, so that the spec
and defense do not claim improvements that have not been demonstrated.

Applies: SH-06, SH-07, SH-10.

- **AC-17:** Before claiming calibration works, report per-layer flags, false alarms, unsafe misses,
  errors and agreement with denominators on a labelled replay set. Classifier disagreement is not
  ground truth. Preserve historical versions/results and distinguish new measurements from the
  evaluated corpus. Replay labels/adjudication, cost estimate and go/no-go remain OD-09.
- **AC-18:** Treat run 314fafc9 only as the evidence in §9.5 until relevant classifiers, pictures
  and errors are inspected. Missing evidence is a limitation, not a diagnosis. Saving this draft
  while investigation is paused does not complete or waive the audit.

### 9.3 Shared behavior

- **SH-01 — Safety versus extra review:** applicable shared safety checks still run. A teacher
  may overturn an automated flag against the written policy, not authorize prohibited material.
  Optional preferences cannot disable shared checks, privacy processing or provider restrictions.
  Failed/malformed/missing verdicts are service conditions; teacher release cannot pretend a
  missing check passed. Retain either classifier's flag as sufficient for a hold, including the
  existing short-circuit behavior; no agreement vote, tie-breaker or new category routing.
  Existing primary-error/backstop fallback is not redesigned here. Use one shared policy with
  role-specific instructions: text checks apply text criteria, image checks their assigned visual
  criteria, and teachers see the same definitions/exceptions. Check every affected prompt and
  criteria reference when that policy changes; do not claim each classifier covers all categories.
- **SH-02 — Authority and exact subject:** recheck teacher/classroom ownership on each decision
  and resume. Bind the decision to the exact held subject/version; inspection changes nothing.
  Duplicate/stale/conflicting requests cannot release a replacement or duplicate paid work.
  Reconcile current state and explain if the story changed. Researchers inspect only. Exact
  response/status/transition contracts remain OD-03.
- **SH-03 — Private content:** privacy checks must succeed before new review material is retained
  or sent downstream; never persist unchecked fallback content after a privacy failure. Keep
  assets private and use authorized reads/signed URLs. No raw child text, credentials or diagnostic
  errors in child-facing copy. Privacy-safe title/reference retention and interaction with existing
  input storage remain OD-03; the current raw jobs row is not assumed to meet that new boundary.
  Researcher response exclusions remain authoritative in AC-16's referenced source.
- **SH-04 — Persistence/lifecycle:** leaving does not cancel. No new expiry or time-based release.
  Existing deletion/retention still apply; never resurrect deleted content. Old failed runs do not
  automatically become resumable holds. Missing-checkpoint resume follows the existing failure
  approach: no automatic restart/re-charge; explain the failure, preserve available writing and
  offer the existing new-submission route. Exact state/copy, deletion compatibility and access:
  OD-03/OD-07/OD-08.
- **SH-05 — Audience-appropriate status:** children see neutral waiting/stopped recovery copy,
  never categories, classifier reasoning or jobs.error. Teachers see review criteria/evidence.
  Read/service/generation failures must not blame the child's writing or imply an unrecorded verdict.
- **SH-06 — Verifiable history:** distinguish existing code, supplied metadata, agreed changes,
  proposals and hypotheses. Missing evidence stays unavailable. Persist the policy/settings
  evidence approved under OD-03; never reconstruct an old call from today's configuration.
  Preserve historical research provenance and version wording changes under project rules.
  Future checks and releases use the current shared policy; earlier decisions retain their
  original policy versions. Updating policy alone neither rescans nor withdraws earlier releases,
  rewrites history, nor launches paid work. Optional settings remain captured per submission.
  A discovered risk affecting earlier releases requires a separately authorized response (OD-11).
- **SH-07 — Spend/recovery:** retain named existing limits and check_image_budget before paid
  generation. No extra budget, unbounded redraws, extra preview draw or automatic full-book
  restart. Release/replacement/resume preserves completed work and avoids duplicate paid
  requests; reconcile ambiguous responses rather than blindly replaying. Reads never generate.
  Investigation defaults to $0; paid calls require a separately approved cost.
- **SH-08 — Complete interactions:** reuse existing design-system/native patterns. Provide
  in-app close/back exits. Distinguish loading, queue-empty, missing content, service failure and
  pending decisions; offer safe reload/retry and retain readable context after failure. Disable
  competing decisions while pending without trapping users. Named controls, visible focus and
  keyboard activation are required; dialogs support Escape/close and restore focus to the opener.
  Cancelled stop confirmation changes nothing. Phone layouts keep actions available and avoid
  pointer-only gestures. Precise new layout/copy/focus transitions remain OD-06/OD-07.
- **SH-09 — Editorial separation/reuse:** safety release does not approve sharing, alter editorial
  timestamps or imply a comment. Editorial actions do not silently change safety decisions.
  Use the same story/scene identities and reuse fitting reading presentation; do not duplicate
  content for future feedback. Rank 3 may extend inspection without redefining safety records.
  No comment schema, generic extension framework or bulk/AI-assisted editorial approval is added.
- **SH-10 — Rollout:** the whole conflicting feature initially ships disabled under the parent
  roadmap. The optional switches independently default off when it is enabled. Ethics re-review
  precedes real-child use. The ordinary rollout switch stops new holds for new submissions,
  which use established moderation behavior; existing holds remain resolvable by teachers.
  Switching off does not release, discard or restart them. This is not an emergency containment
  switch. Setting name/ownership and behavior for in-flight submissions remain OD-10.
- **SH-11 — Honest asynchronous outcomes:** claim saved/started only after durable success.
  HTTP/network/queue failures or ambiguous responses preserve available context, show an error and
  reconcile before retry. No silent reroll on worker/checkpoint failure. After deletion or access
  withdrawal, deny the decision/resume without generating.
- **SH-12 — Existing bounds:** retain input/title validation and named length, scene and spend
  limits. Empty/invalid input uses existing validation/recovery; valid maximum-size input is not
  rejected merely because holds are added. Export/narration, story rewriting, provider/model
  swaps and consistency scoring remain outside scope except OD-05's replacement-path interaction.

### 9.4 Edge cases

| Case | Expected behavior | Home |
| --- | --- | --- |
| Empty/invalid title or too-short story | Existing validation/recovery; no fabricated safety hold | SH-12 |
| Single-scene or maximum permitted input | Same hold/resume within existing bounds | AC-01, SH-07, SH-12 |
| Flagged title before a job exists | Intended private hold; representation not approved | AC-01, SH-03, OD-03 |
| No characters/references | Do not invent reference content or require an empty review | AC-06, OD-03 |
| Picture not generated yet | Distinguish from missing; no extra preview draw | AC-06 |
| Flagged reference path currently cleared | Retain exact candidate privately; no invented historical picture | AC-06, OD-03 |
| Teacher opens a flagged picture | Warning then explicit reveal; no child access | AC-07 |
| Link expired/picture cannot load | Reload/read recovery; allow disabled; no automatic redraw | AC-07, SH-07 |
| Primary classifier errors | Existing fallback, recorded error rather than false primary pass | SH-01, SH-06 |
| Backstop error/unrecognized verdict | Service recovery; no unsafe label or bypass of missing check | AC-02, SH-01, SH-11 |
| Reasoning unavailable | Say unavailable rather than inventing a reason | AC-09 |
| Provider refuses before image exists | No picture to release; exact recovery remains open | SH-01, OD-05 |
| Teacher uncertain about policy | Leave held; return later, permitted replacement or stop; no new second reviewer | AC-10 |
| Mistaken release of genuinely unsafe content | Withdraw clearance: hide affected content, block generation, return to review; prior exposure cannot be undone | AC-19, OD-02/OD-03 |
| Provider call finishes after withdrawal | Result cannot bypass withdrawal; exact race/access contract still required | AC-19, OD-03 |
| Double click/two tabs/lost response | One winning transition/generation; reconcile before retry | SH-02, SH-07, SH-11 |
| Old decision after replacement | Cannot release newer candidate; refresh current state | SH-02 |
| Replacement passes or flags | New scene-consistency judgment; safety flag holds exact candidate, otherwise established selection limits apply | AC-12, OD-05 |
| Later scene gets new safety flag | New hold despite earlier allow/theme acceptance | AC-10, AC-11 |
| Budget exhausted | Replacement disabled with explanation; permitted other actions remain | AC-12 |
| Accepted optional theme recurs | No repeat hold solely for that theme/unchanged submission | AC-11, OD-04 |
| Multiple optional themes | One grouped review from one submitted-text check before paid generation | AC-11, AC-14 |
| Optional theme appears only in a generated picture | No optional-image screening; shared image-safety checks still apply | AC-14 |
| Switch changes mid-run/hold | Original submission settings retained; no silent release/spend | AC-15 |
| Shared-policy update | Current policy at future checks/releases; preserve old decisions; no automatic rescan/withdrawal | SH-06, OD-11 |
| Teacher absent for days | Honest waiting and exit/return; existing lifecycle applies | AC-03, AC-04 |
| Close/Escape/navigate away | Inspection closure makes no decision; exit/focus works | SH-02, SH-08 |
| Cancel/confirm stop | No change / end run without deleting writing | AC-13 |
| Child stops held story while teacher releases | Confirmed child stop retains writing; reconcile to one outcome, never blindly resume | AC-13, SH-02, OD-03 |
| Child deletes held story | Separate destructive confirmation and existing cleanup lifecycle; no resurrection | AC-13, SH-04, OD-08 |
| Attempt to reopen stopped run | No teacher reopen; reuse writing in new submission | AC-13 |
| Queue/read/decision request fails | Distinct error, retained context and safe retry/reconcile | SH-08, SH-11 |
| Empty queue or changed item while inspecting | Honest current/empty state; no stale decision/trapped dialog | SH-02, SH-08, OD-06 |
| Missing checkpoint | Honest failure, available writing retained, existing new-submission route; no silent restart/re-charge | SH-04, SH-07, OD-03/OD-07 |
| Reload or another authorized device | Load persisted state before observing updates | AC-03 |
| Ownership/access withdrawn or story/classroom deleted | Recheck, deny unauthorized writes, do not resurrect | SH-02, SH-04 |
| Student removed during review | Deny child access/resume; classroom owner may inspect but cannot resume for inactive/moved author | §9.9.5; OD-08 implementation |
| Ordinary rollout switch disabled while holds exist | Existing holds remain teacher-resolvable; new submissions use established moderation | SH-10, OD-10 |
| Legacy failure or missing historical evidence | No automatic conversion or inferred verdict | AC-18, SH-04, SH-06 |
| Sharing/export/rank 3 comments | Separate permissions; no new export/comment behavior | SH-09, SH-12 |
| Phone/keyboard/assistive technology | Named native controls, focus/close and readable states | SH-08, OD-06 |

### 9.5 Design decisions, rationale and evidence

**Agreed rationale:** first-flag holds avoid asking children to diagnose classifier results.
Contextual inspection lives in Books. Optional themes start off to avoid extra interruptions;
one acceptance avoids repeated per-page review. Captured settings make behavior predictable.
Replacement protects progress without custom creative controls. Stop ends a run, not the writing.
These are discussed UX reasons, not measured workload or false-alarm improvements.

#### 9.5.1 Agreed draft policy boundaries (resumed Q1–Q14)

These are owner-selected requirements for a future ages-10–12 rubric, not a complete or
educator/ethics-approved policy. No existing school policy or reviewer was identified. Complete
criteria, language-specific boundary examples, source review and validation remain OD-01.
One shared policy supplies role-specific classifier instructions and the teacher reference.
An automated category can be mistaken; genuinely prohibited content cannot be authorized by
teacher confirmation. Text and pictures are judged separately; fiction alone is no exemption.

| Subject | Agreed boundary |
| --- | --- |
| Ordinary story conflict | Allow non-graphic fictional conflict, spooky situations, suspense and loss; they may trigger an enabled optional classroom theme. Graphic injury, actionable harmful instructions and encouragement of harm trigger shared safety. |
| Dangerous acts | Distinguish narrative depiction from encouragement/instruction. Non-graphic depiction can pass; actionable instructions, encouragement and challenges to copy trigger shared safety. Judge visual framing separately: cautionary text cannot excuse an encouraging picture. |
| Sexual content | Prohibit sexual acts, sexualized depictions and erotic detail. Ordinary affection, non-sexual body references and age-appropriate factual discussion are not violations by themselves. |
| Visual exposure | Prohibit exposed genitals, clearly exposed buttocks and bare breasts in generated pictures, including non-sexual contexts. Ordinary swimwear, changing behind a screen and covered caregiving can pass if they meet the other criteria. |
| Bullying and prejudice | Permit non-graphic critical depiction. Encouragement of targeted abuse, dehumanization or violence violates shared safety. Ordinary bullying can trigger the enabled optional theme. |
| Explicit discriminatory slurs | Exclude from content cleared for generation or child display even when quoted critically. Indirect narration can pass. Wording crossing this boundary cannot be released unchanged; revision uses a new child submission, not teacher rewriting. |

These boundaries are not exhaustive. Unaddressed categories and ambiguous cases need complete
definitions and review before rollout; they are not implicitly allowed. An uncertain teacher
leaves the content held (AC-10). This draft does not establish measured detection accuracy.

#### 9.5.2 UX priority and limits (resumed Q15–Q19; owner-confirmed recap)

Prioritize one understandable child wait/return/stop experience and contextual teacher review in
Books. Group optional themes before paid generation, preserve writing, and reuse existing native
controls and lifecycle patterns. No second-reviewer service, mandatory written release rationale,
per-picture optional-theme screening, generic workflow framework or new creative controls.
Required failure states, privacy, exact-content decisions and spend safeguards remain in scope.
Routine implementation follows established patterns; unresolved safety/contracts are not removed
to simplify the UX. The owner authorized this documentation amendment, not implementation.

**Responsibilities/data flow:** existing title submission, input_gate, char_ref_mod and output_mod
are moderation entry points. Worker/checkpointer owns generation/resume; the teacher resolves
an exact held subject; child surfaces project safe status; the research route projects private
state under ADR-079. Follow MASTER_SPEC §§2–6, StoryMemory conventions and existing authorization.
The initial interview did not define node, endpoint, status or field contracts. The 2026-10-27
accepted design in §9.9 now defines them. BookReviewDialog's completed-page/editorial
assumptions prevent drop-in reuse; §9.9.7 reuses reading presentation while keeping safety and
editorial decision authority distinct, without scaffolding for rank 3.

**ADR boundaries:** ADR-079 is accepted only for researcher access. Discussion gates for ADR-011,
ADR-003, child-safety rules and ADR-059 were opened, and the moderation amendments are now accepted in ADR-080 (2026-10-27).
Teacher-review-and-approval §4.8/§4.10 and invariants 8, 9, 11 conflict with teacher flag inspection,
child-visible waiting and teacher recovery. Amend safety-hold aspects narrowly; editorial feedback
in §§12–13 remains rank 3. ADR-025/lifecycle amendments may be needed once OD-03 is settled.
No frozen ADR is silently superseded.

**Verified evidence and limits:**

- Owner SQL: job 314fafc9-4020-4114-9a75-25a0c8059d47 is failed/scene_safety, unapproved,
  created 2026-10-24 01:22:35.226904+00; last published progress is consistency_check:1/1.
  Current code maps output_moderation_failed to scene_safety; deployed revision is unverified.
  Progress text does not identify a rejecting classifier.
- Owner checkpoint inventory: root history through step 15; latest checkpoint
  1f1cf4b1-69fd-69b5-800f-bec6ac0d6cc1 at 2026-10-24T01:34:43.426741+00:00.
  Accumulated channel names are not verdicts or proof of completed node execution. State,
  relevant pictures, classifier reasoning and worker errors remain uninspected.
- Local text prompts lack project policy definitions/boundary examples. Official safeguard
  guidance recommends definitions, allowed/disallowed criteria and examples; Meta documents a
  general taxonomy and customizable prompts. Neither supplies a validated Grade 5–6 storybook
  policy. Provider-side formatting and causal effects have not been observed.
- Empty/unrecognized guard responses now raise; the historical empty-response refusal bug is
  already fixed. Mocked code-path tests are not accuracy measurements. The initial audit found
  the old phase_05 probe reading removed settings.moderation_model; ticket 04's separate fix now
  uses settings.moderation_primary_model. That setting fix does not supply a production-path
  image replay harness or establish moderation accuracy.
- Historical B6 observations and limits live in audit ticket 01. They do not establish this run's
  cause. Primary-safe/backstop-unsafe alone is not a false alarm: image classifiers cover different
  risks. Checkpoint intervals can include human waiting and do not isolate classifier latency.

### 9.6 Verification

**Accepted verification seams — §9.9/ADR-080 (2026-10-27):**

1. Teacher/child public UI and authenticated HTTP commands into the real compiled graph/worker,
   mocking provider/network calls only at the outer boundary. New hold commands do not exist in
   code; §9.9.3 defines the proposed contract. Observe J-01–J-04 and J-06, durable
   resume, exact-subject authorization, privacy, no duplicate charges and preserved earlier scenes.
2. Existing GET /research/runs/{job_id} plus research/metrics list/detail, following the
   separate research-run-browser §8 and ADR-079. This seam already exists.

**Existing precedents, not evidence of this feature:** backend/tests/test_input_gate_node.py,
test_char_ref_mod_node.py, test_output_mod_node.py, test_run_job.py and test_research_runs.py;
frontend/components/FailureScreen.test.tsx and the classroom Books tests. Existing output_mod
tests assert automatic soften/retry: future authorized changes must replace those expectations
with first-flag hold assertions, not delete/loosen coverage. No standalone BookReviewDialog.test.tsx
was found during synthesis; it is not a confirmed existing seam.

**Required future evidence:** J-01–J-06; authorization, stale/duplicate decisions, failed resume,
budget limits, private-field exclusions and every §9.4 state; desktop/phone and keyboard
inspection/reveal/stop/return/withdrawal. Include child-stop versus teacher-release and in-flight
generation versus withdrawal, current-policy release with historical provenance, ordinary-switch
draining of existing holds, grouped text-only optional reviews before paid draws, and fresh
consistency results for replacement scenes without unsafe fallback selection. Policy boundary
examples in §9.5.1 need labelled real-payload evaluation, not assertions about generated content in
mocked CI. Tests fail for the intended reason before implementation and follow
the repository's limited main/failure-path policy without new infrastructure. Real sanitized
payloads and hand-derived expectations are required. Mocked CI cannot establish fuzzy quality.
Real classifier comparison needs OD-09 and separate cost approval.

When implementation is separately authorized, commands from their own directories are:

- Backend: uv run ruff check . and uv run pytest.
- Frontend: pnpm lint, pnpm build and pnpm test, using the documented CI placeholders where
  appropriate. Hosted RLS/role/asset checks and real-provider checks need access; report skips.

**Actual results:** documentation diff/reference/coverage checks are reported on delivery.
No application tests, hosted checks, classifier calls or replay campaign have run for this proposed
behavior. Writing the spec establishes no improved false-alarm/miss rate, reduced teacher workload,
safe historical restart, implemented behavior or rollout readiness.

### 9.7 Decision register, readiness and sources

| ID | Design disposition (2026-10-27) | Remaining gate |
| --- | --- | --- |
| OD-01 | Owner-accepted criteria/confirmation in §9.9.6; optional definitions in §9.9.7 | Identified educator/ethics review and labelled validation before real-child use/adopting changed classifier prompts; no external approval supplied |
| OD-02 | Exact allow/withdraw commands, whole-book scope, guarded access and editorial reset in §§9.9.3–9.9.5 | Accepted; implement/verify |
| OD-03 | Concrete fields, states, interrupt, transactions, dispatch and checkpoint recovery in §§9.9.1–9.9.5 | Accepted; implement/verify; proposed fields are not installed |
| OD-04 | Theme definitions, one detector, hash/settings identity and grouped acceptance in §9.9.7 | Accepted; implement/verify |
| OD-05 | Existing redraw allowance, fresh-only replacement selection and failure/refusal outcomes in §9.9.4 | D-N resolved by accepted ADR-080; implement/verify |
| OD-06 | Queue ordering/count/default, layout, reveal, actions and focus in §9.9.7 | Accepted; implement/verify |
| OD-07 | Child waiting/stopped copy and draft transfer/failure recovery in §9.9.7 | Accepted; implement/verify |
| OD-08 | Quiescence, held/stopped deletion, private-record cleanup and removed-author access in §9.9.5 | ADR-080 accepted; implement ADR-044 prerequisites and held-state extension; institutional retention/consent review before real-child use |
| OD-09 | Audit 01 remains open: actual run evidence, labelled replay/adjudication, denominators and cost/go-no-go have not been supplied | Accepted exception permits synthetic-only, feature-off build work; no accuracy claim or adoption of changed classifier instructions without evidence |
| OD-10 | ADR-080 and exact rollout contract in §9.9.8 accepted on 2026-10-27 | Educator/ethics review and hosted verification before real-child enablement |
| OD-11 | Emergency/bulk historical rescanning explicitly excluded in §9.9.8; individual withdrawal is specified | Separately authorize any incident response when an actual risk is identified; does not block this scoped design |
| OD-12 | Concrete commands and selected verification seams in §§9.9.3/9.9.8 | Design/seams accepted; fresh implementation evidence required; no separate product interview |

**Readiness:** the owner explicitly accepted §9.9, ADR-080 and the synthetic-only, feature-off
build exception on 2026-10-27 (“accept all”). Ticket 02 is done as a specification handoff;
ticket 05 is ready and 06–15 follow predecessor-implementation dependencies. Do not repeat the
conflict/design acceptance question. Audit 01 remains open for calibration evidence; real-child
release review remains separate and cannot be satisfied by mocked tests or owner acceptance.
Recording this verdict changes documentation only, not application code, schema or deployment.

**Sources:**

- Owner's han-grill discussion Q1–Q21 and han-to-spec request;
  [epic decisions](../../.scratch/ptd-moderation-calibration/map.md).
- Owner's resumed han-grill Q1–Q19, UX-priority instruction, confirmed recap and subsequent
  request to amend this specification (2026-10-26). Resumed question numbers are distinct from
  the earlier Q1–Q21; §9.8 maps them separately.
- [Audit 01](../../.scratch/ptd-moderation-calibration/issues/01-audit-moderation-false-alarms.md)
  and [spec ticket 02](../../.scratch/ptd-moderation-calibration/issues/02-grill-moderation-spec.md).
- [Parent roadmap](../../.scratch/post-technical-defense/map.md);
  [rank 3 scope](../../.scratch/ptd-review-feedback/map.md).
- MASTER_SPEC §§2–6; PRD_v2 §4; RESEARCH_PROTOCOL §11; story-memory-contract;
  teacher-review-and-approval §§4.8, 4.10, 5, 12–13; kid-flow-pause-lifecycle;
  story-titles; lifecycle decisions including ADR-044.
- [ADR-079](../product/adr/ADR-079-researchers-can-inspect-failed-and-unapproved-runs.md)
  and [research-run-browser access amendment](research-run-browser.md).
- [Safeguard guide](https://developers.openai.com/cookbook/articles/gpt-oss-safeguard-guide),
  [Meta model card](https://huggingface.co/meta-llama/Llama-Guard-4-12B/blob/main/README.md),
  [Meta prompt format](https://dev.meta.ai/llama/docs/model-cards-and-prompt-formats/llama-guard-4).
  These support interface guidance, not validated child-story criteria or measured efficacy.

### 9.8 Source-to-contract coverage

Bare Q numbers below refer to the initial interview; R-Q numbers refer to the resumed interview.

| Source requirement | Explicit home |
| --- | --- |
| Q1: open conflicts, investigate instead of assuming | AC-17–18; SH-06; OD-01–03, OD-09–10 |
| Q2/Q10/Q11: exact image/text release under policy, no category veto | AC-10; SH-01–03; OD-01–03 |
| Q3 and supplied SQL: candidate evidence, not diagnosed false alarm | AC-18; §9.5; OD-09 |
| Q4/accepted ADR-079: full researcher viewer including failed/unapproved | AC-16; research-run-browser §§2, 4, 5.1, 5.4, 6, 8 |
| Q5: automatic hold, child leave/return without lost writing | AC-01, AC-03–04; SH-04–05 |
| Q6: first flag before automatic redraw | AC-01; SH-07 |
| Q7: title flags, privacy before retention | AC-01, AC-06; SH-03; OD-03 |
| Q8: no new deadline, existing lifecycle | AC-04; SH-04; OD-08 |
| Q9: replacement, budget, moderation, no creative prompts | AC-12; SH-07; OD-05 |
| Q12/B1/Q14: predefined extra review, no safety-disable/free-text rules | AC-14–15; SH-01 |
| Q13: criteria reference plus per-hold explanation | AC-08–09; SH-06; OD-01/OD-03 |
| Q15: three themes, avoid excessive strictness | AC-14; §9.5 rationale; OD-01/OD-04 |
| Q16: one theme acceptance, contextual inspection | AC-06, AC-11; SH-09; OD-04 |
| Roadmap/forward compatibility, no epic 3 overlap | §9.1; SH-09; §9.5 responsibilities |
| Q17: Books/Needs your help queue | AC-05; OD-06 |
| Q18: confirmed stop, retain writing, new submission, no reopen | AC-13; SH-04/SH-08; OD-07 |
| Q19: warning/reveal, unavailable picture cannot be allowed | AC-07; SH-08 |
| Q20: optional defaults off, separate feature default | AC-14; SH-10; OD-10 |
| Q21: per-submission settings, no silent release/spend | AC-15; SH-06; OD-03/OD-11 |
| Edge-case review request | §9.4; every case has an existing AC, SH or OD home |
| Project safety/privacy/auth/spend/recovery/full UI rules | SH-01–12; §9.4; §9.6; OD-01–03/OD-08–12 |
| Initial synthesis: spec only, pause discovery and implementation | Draft status; §9.6 actual results; §9.7 readiness |
| R-Q1–2: ages 10–12; no existing school policy/reviewer | §9.1 audience; §9.5.1; OD-01 |
| R-Q3/8/11–14: contextual conflict/danger, sexualization/exposure and prejudice/slur boundaries | §9.5.1; AC-08/AC-10; OD-01 |
| R-Q4/9: explicit criterion confirmation, decision record, no mandatory justification/escalation service | AC-10; SH-02/SH-06; OD-02/OD-03 |
| R-Q5/7: either flag holds, shared policy with role-specific instructions | SH-01; §9.5.1 |
| R-Q6: withdraw mistaken clearance, contain further exposure, no automatic gallery reapproval | AC-19; J-06; §9.4; OD-02/OD-03 |
| R-Q10: current shared policy for future checks/releases, historical provenance, no automatic rescan | SH-06; OD-11 |
| R-Q15: confirmed child stop retains writing; deletion remains separate | AC-13; J-03; §9.4; OD-03/OD-08 |
| R-Q16: ordinary disable drains existing holds; no emergency containment promise | SH-10; §9.4; OD-10/OD-11 |
| R-Q17–18: same-intent replacement, fresh scene-consistency check, no new image budget or unsafe fallback | AC-12; J-02; §9.6; OD-05 |
| R-Q19: one text-only optional-theme check, grouped review before paid generation | AC-11/AC-14; J-04; §9.4; OD-04 |
| UX-priority instruction, confirmed recap and amendment request | §9.5.2; §9.7 readiness; no implementation or accepted-ADR changes |

### 9.9 Technical completion proposal (2026-10-27)

**Status: accepted (2026-10-27), scene-hold slice implemented (ticket 05, 2026-10-28).** The owner explicitly said “accept all” to
this design, [ADR-080](../product/adr/ADR-080-teacher-held-moderation-and-exact-content-clearance.md)
and synthetic-only, feature-off implementation while audit 01 remains open. This completes
ticket 02's specification handoff. It supersedes earlier statements that contracts or acceptance
are pending. No audit result or educator/ethics approval is implied. ADR-080 governs its scoped
amendments. Ticket 05 implements the default-off scene hold and its enabling privacy, persistence,
worker and product-delivery contracts. Later teacher actions and other subject kinds remain
specified, not implemented. The implementation record below distinguishes them.

#### 9.9.1 Chosen approach and ownership

Use a dedicated, effect-free `moderation_review` node in
`backend/pipeline/moderation_review.py`. Classifier nodes return evidence through StoryMemory;
pure routers enter this node instead of raising on an actual flag in teacher-review mode.
The node calls `interrupt()` with only a kind and review ID. It never classifies, draws, uploads,
or writes outside its partial return. The worker distinguishes this interrupt from the existing
child `reveal`; it must not write teacher evidence into `jobs.reveal`.

This adds a moderation branch to ADR-003/024 and a human pause alongside ADR-029's reveal.
Reusing/generalizing `reveal` would mix child and teacher contracts. A separate workflow engine
would duplicate checkpoint/resume ownership. Neither is selected. FastAPI, RQ, the existing direct
Postgres connection, Storage and Realtime remain the only services.

One job has one unresolved review at a time. Several enabled optional themes can share one review.
Multiple flagged references are reviewed sequentially in character order, without redrawing or
rechecking already-cleared exact references. The worker owns graph/checkpoint transitions; the
database owns current status, authorization, decisions and the generation fence. State contains
the review snapshot needed by nodes, not a second mutable copy of job status.

#### 9.9.2 Exact proposed data contract

Append defaulted fields, retaining `CURRENT_SCHEMA_VERSION = 1` and legacy loading:

| Location | Proposed field/type | Meaning |
| --- | --- | --- |
| `StoryMemory` | `moderation_context: ModerationContext` with default factory | `mode: Literal['baseline','teacher_review_v1']='baseline'`; `theme_ids: list[str]=[]`, `settings_version: int=0`, `policy_version: str \| None=None`; `generation_epoch: int=0` as worker snapshot; optional `review: ReviewContext`; `optional_themes_checked: bool=False`, `detected_themes: list[ThemeDetection]=[]`, `accepted_theme_ids: list[str]=[]` |
| `ReviewContext` embedded in StoryMemory | `review_id: UUID`, `kind: Literal['title','story_text','character_reference','scene_image','optional_themes']`, `subject_id: str`, `subject_version: str`, `criteria: list[str]`, `return_node: str`, `replacement: bool=False`, `resolution: Literal['allow','replace'] \| None=None` | Server-created review snapshot. Subject version is SHA-256 of exact privacy-processed UTF-8 text or immutable image bytes, not a signed URL. No client-selected routing. |
| `Input` | `moderation_clearance: ModerationClearance \| None=None` | Exact processed-story hash, allowing review ID and decision policy version; separate from the actual classifier verdict |
| `Character` | `ref_generation_prompt: str \| None=None` | Exact most recent reference prompt, including any tapped emphasis, recorded by every reference-mint path in this mode |
| `Attempt` | `safety_eligibility: Literal['unreviewed','cleared','teacher_allowed','excluded']='unreviewed'` | Separate from consistency `passed`; excluded candidates can never win best-of in this mode |
| `Scene` | `moderation_replacement_count: int=0` | One existing output-moderation replacement allowance, consumed by an actual replacement draw |

`ReviewContext` also embeds `classifier_evidence: list[ClassifierEvidence]` with a default factory.
Each `ClassifierEvidence` has `layer: Literal['primary','backstop']`, `model_id: str`,
`instruction_version: str`, `outcome: Literal['safe','flagged','error','not_called']`,
`checked_at: datetime | None`, `categories: list[str]` and `reason: str | None`.
Use null/empty values when a layer supplies no reason; record the actual call/error, not its
exception body. The worker constructs the private subject projection from this evidence and the
exact text/image/prompt already present in the same checkpoint. Never fetch a newer candidate to
fill an older review. A title's equivalent evidence is captured directly by its pre-graph intake.

`ModerationClearance` embeds `subject_version: str`, `review_id: UUID`, `policy_version: str`.
`ThemeDetection` embeds `theme_id` (one of the three IDs in §9.9.7) and a privacy-processed
`reason: str`. List defaults use `Field(default_factory=list)`, not shared mutable defaults.

`ModerationContext.policy_version` is optional for baseline/legacy state and required for newly
created teacher-review jobs. Settings are immutable for a submission. `ReviewContext.return_node`
must be one of the existing graph node names or `END`, saved by the server from the paused graph,
never supplied by a teacher. A title remains job metadata; it does not become pipeline input.
The database epoch is authoritative; the worker refreshes its state snapshot at entry/resume.
Mint first-flag review IDs deterministically with UUIDv5 under the job UUID from
`kind:subject_id:subject_version:generation_epoch`; projection retries therefore use the same
review ID and cannot increment the epoch twice. Withdrawal uses its committed request UUID as
the new review ID, so repeated withdrawal delivery also repairs the same review.

Proposed database additions, to be made by the implementation's next free numbered migration
(highest currently on disk is `0021`; do not reserve/reuse a number in this spec):

| Surface | Proposed contract |
| --- | --- |
| `jobs` | Add `moderation_mode text not null default 'baseline'`, `generation_epoch bigint not null default 0`; widen status with `awaiting_teacher`, `stopped`, and ADR-044's `deleting`; implement nullable `worker_finished_at` from ADR-044. `moderation_settings_snapshot jsonb not null default '{}'` privately processed, server-written policy/theme/version metadata captures intake settings across queue delays and global switch changes. It contains no evidence or secret. |
| `job_moderation_reviews` | UUID primary key; `job_id` FK `ON DELETE CASCADE`; `kind`, `subject_id`, `subject_version`, private `subject jsonb`, `criteria text[]`, `policy_version`, `settings_snapshot jsonb`, `classifier_evidence jsonb`, `checkpoint_id text`, `return_node text`, `created_at`, nullable `withdraws_review_id`; one undecided row per job |
| Decision columns on that row | Nullable `decision: allow/replace/stop`, `actor_id`, `decided_at`, `decision_policy_version`, `confirmed_criteria text[]`, `request_id UUID`, `decision_epoch bigint`; a decided record is immutable |
| Dispatch columns on that row | `dispatch_state: pending/queued/consumed/failed`, nullable `dispatch_kind: resume/anchor_withdrawal`, nullable `dispatch_error_code`; these describe delivery, not a second safety verdict |
| `classrooms` | Add `moderation_theme_ids text[] not null default '{}'` restricted to the three IDs in §9.9.7, and `moderation_settings_version bigint not null default 0` |

The private subject stores exact redacted text or immutable image path/hash, the source prompt
and reference paths needed for a same-intent replacement, and scene/character ID when applicable.
Classifier evidence records each attempted layer's configured model ID, instruction version,
`safe/flagged/error/not_called`, supplied category/reason if available, and call time. Never infer
a missing reason or earlier model from today's config. Preserve the existing primary short circuit
and primary-error fallback. Historical missing fields remain unavailable.

Enable RLS on the new table and deny all browser-role reads/writes, including researchers.
Expose only authorized FastAPI projections. There is no new browser UPDATE on `jobs`; classroom
theme writes use the teacher endpoint. Uniqueness covers `(job_id, request_id)` for non-null
requests; changed content creates a new review, never edits an old subject/version. Review records
are operational child-derived data, deleted with the job, not a permanent research audit store.

#### 9.9.3 State transitions, commands and dispatch

Existing `queued`, `running`, `awaiting_confirm`, `complete`, `failed` remain. `awaiting_teacher`
means teacher help is required, including withdrawn clearance. `stopped` is terminal and distinct
from a classifier/service failure. Neither status alone proves worker quiescence.

| Event | Preconditions | Atomic database outcome | Worker outcome |
| --- | --- | --- | --- |
| First actual flag | Teacher-review job; classifier node's evidence checkpoint is durable | Insert undecided review, increment epoch, set `awaiting_teacher`; publish no flagged image in `pages/reveal` | Finish at review interrupt; mark quiescent last |
| Allow | Owner teacher, matching open review/version/epoch/current policy; exact subject inspectable; quiescent | Record immutable `allow`, advance epoch, set `queued`, clear finish marker, dispatch `pending` | Resume exact checkpoint, apply explicit teacher clearance, follow saved continuation |
| Replace | Same authority/version/quiescence; picture; allowance and image budget available | Record `replace`, advance epoch, set `queued`, clear marker, dispatch `pending` | Draw one replacement; new checks; no release of old candidate |
| Stop | Owner teacher or active child author; matching open review/epoch; quiescent; confirmation | Record `stop`, advance epoch, set `stopped`; no dispatch | No continuation; writing remains |
| Withdraw | Owner teacher; previous `allow` for that exact currently selected or dependency subject; not stopped/deleting/failed; no other open review | New open review referencing old clearance, advance epoch, set `awaiting_teacher`, clear sharing timestamps | Fence old worker; anchor new review after it quiesces |
| Delete | Child owner; allowed terminal/pause status; non-null finish marker | ADR-044 CAS to `deleting`, advance epoch; all reads denied except owner tombstone | Existing four-store cleanup, plus cascading private review rows |

Use a database transaction with `SELECT ... FOR UPDATE` on the job for each transition, review
record and sharing change. A server-only SQL function or the existing direct connection may own
that transaction; no externally callable security-definer shortcut or service key in a browser.
Recheck active profile, classroom membership and owner in this transaction and at worker start.
`/confirm` cannot release `awaiting_teacher`. Editorial approval additionally requires `complete`
and no open safety review. Withdrawal intentionally clears `approved_at` and `rejected_at`; later
safety clearance leaves the book editorially pending. Previous safety decisions remain recorded.

Proposed endpoints (all use existing bearer authentication and no-store responses):

| Endpoint | Request / response |
| --- | --- |
| `GET /teacher/moderation-policy` | Teacher-only current policy ID, audience, named criteria/definitions/exceptions and optional-theme definitions, from the shared policy data source; no child/job evidence |
| `GET /teacher/classrooms/{classroom_id}/moderation-reviews` | Owner-only list: review/job IDs, display title, author nickname, hold time and readiness; no image URLs or evidence in list. Oldest hold first, then review UUID. |
| `GET /teacher/jobs/{job_id}/moderation-review` | Owner-only detail: exact subject/version, redacted story context, recorded criteria/evidence/settings, current policy version, epoch, available actions with disabled reasons; no flagged-picture URL until explicit reveal |
| `POST /teacher/jobs/{job_id}/moderation-review/reveal` | `{review_id, subject_version}`; owner-only authenticated image response under §9.9.5; no state mutation or automatic allow |
| `POST /teacher/jobs/{job_id}/moderation-review/decision` | `{review_id, subject_version, expected_epoch, request_id, action: allow/replace/stop, policy_version, confirmed_criteria, confirmed: true}`; allow requires all displayed criteria confirmed under current policy; stop requires confirmation; replace has no custom prompt |
| `POST /teacher/jobs/{job_id}/moderation-review/withdraw` | `{clearance_review_id, subject_version, expected_epoch, request_id, confirmed: true}`; returns new review ID/current state; available from the teacher book detail after an allow |
| `POST /jobs/{job_id}/stop` | Active child author only; `{review_id, expected_epoch, request_id, confirmed: true}`; same held-stop transition, no arbitrary running cancellation |
| `PATCH /teacher/classrooms/{classroom_id}/moderation-settings` | Owner-only `{expected_version, theme_ids}`; atomically increment version; response is saved IDs/version; feature-off disables editing, not reading saved settings |

Decision/withdraw/stop success returns `{job_id, status, generation_epoch, review_id,
dispatch_state}` with `202` for queued continuation or withdrawal awaiting quiescence, `200` for
settled stop or idempotent replay. `401` unauthenticated; `403` wrong role; `404` foreign/missing
job/classroom; `409` stale epoch/version, non-quiescent review, policy changed, unavailable
checkpoint or invalid current state; `422` malformed request or unavailable replacement budget.
Responses contain stable codes and authorized current state, never raw request values or
`jobs.error`. A repeated request ID with the same body returns its existing outcome; reuse with
a different body is `409 request_conflict`. Conflicting requests serialize: first committed
decision wins. A child stop losing to an allow receives current running/queued state and neutral
copy; it does not cancel a now-running book.

Commit a pending dispatch with the decision before enqueueing RQ. Use a deterministic RQ ID from
job/review/decision epoch. Redis error or ambiguous response leaves that durable decision pending,
not rolled back to a second open decision. Show **Continue story** retry of the same request;
explicit retry rechecks state and enqueues only that pending continuation. Reads never enqueue.
Do not add a scheduler or generic outbox. Worker completion marks dispatch consumed. Repeated
queue delivery must acquire one session-level per-job Postgres advisory lock, validate epoch and
checkpoint progress, then no-op if stale/consumed. Duplicate requests must not create duplicate
workers paying for the same continuation. The existing accepted provider-success/upload-crash
window in ADR-025 is not an exactly-once billing guarantee; report ambiguous spend honestly.

Withdrawal commits `dispatch_kind='anchor_withdrawal'` with its new open review, using the same
pending/enqueue/retry mechanism to schedule the serialized control worker. If the previous worker
already quiesced, anchor immediately under the lock; otherwise let it finish/fence, then anchor.
Until anchoring/quiescence succeeds, allow/replace/stop are disabled with **Finishing the current
step** and an explicit retry for a failed dispatch. A queued old-epoch worker is harmless: its
entry check must return before any effects. All old-epoch writes, including failure/status and
finish-marker writes, must be conditional; they cannot overwrite a newer hold or deletion.

#### 9.9.4 Checkpoints, fencing and replacement routing

A review becomes actionable only after its evidence checkpoint and review projection are durable
and the worker's final quiescence write has succeeded. A crash before projection is repaired by an
explicit retry that reads that existing checkpoint/review identity, not by re-running classifiers.
The worker's last write sets `worker_finished_at` after all checkpoint, Storage and tracing work.
Deletion/stop/resume compete on status, epoch and this marker. Do not infer quiescence from time.
If the checkpoint cannot be found or validated, keep content private, transition to `failed`
with the existing machine-failure classification, preserve available writing and offer new
submission. Never rebuild StoryMemory to resume a historical failed run.

For each provider call in this mode, check active profile/classroom, current epoch and no open
review before starting a paid effect; recheck after completion, before another provider call,
and before publishing pages, reveal, completion or sharing. A withdrawal commits immediately even
if a call is in flight. That call may finish; its output stays private and cannot advance the old
epoch. Record incurred image cost before quiescence. No further paid call may start under that
epoch. Check every loop-internal draw, not only worker stream events.

After withdrawal quiesces, the serialized worker reads the latest checkpoint and its saved next
node (or `END` for a completed book), validates retained subject bytes, and injects the new
`moderation_context.review` snapshot through
`graph.update_state(..., as_node='moderation_review')`. The review node's pure router sends
unresolved review state back to `moderation_review`, scheduling its interrupt without re-running
the interrupted generation node. Only a worker holding the per-job lock may do this. Preserve
existing `reveal` as a continuation if withdrawal interrupted that pause. This uses the installed
LangGraph `update_state/as_node` seam; prove scheduling with the real compiled graph before build
completion. On allow, return to the saved next node; `END` restores completed pages only after all
current safety eligibility and epoch checks. A withdrawal while a node has incomplete effects
and no safe checkpoint recovery fails honestly rather than blindly paying again.

Normal first-flag continuation is simpler: story text → `analyze`; character reference →
`char_ref_mod` to check remaining references, then existing child `reveal`; scene → `output_mod`
to advance the normal scene loop. Title review uses a private pre-graph record with no checkpoint;
allow initializes a **new, never-started** graph once at `input_gate`, not a failed-run restart.
Optional text review continues to `analyze` after recording all detected enabled themes. Teacher
clearance is stored as `teacher_allowed` for exact content, never forged into a classifier pass.
The worker constructs resume data only from a committed matching decision, not the request body.
The review node validates it against the state snapshot, returns `resolution='allow'/'replace'`,
and writes the applicable clearance/eligibility. Its router sends an unresolved review to itself,
`replace` to `moderation_replace`, and `allow` to the saved continuation. Retain that most recent
resolved context until another review replaces it; it is not the decision-history store.
For text, retain the actual `ModerationResult` and make the router consult
`input.moderation_clearance` against the exact processed hash, so a later reference hold cannot
erase the prior text clearance. Withdrawal clears the affected graph clearance at anchoring;
the authoritative database fence already denies delivery/work before that point.
For references/scenes add `teacher_allowed` to the moderation-status vocabulary in this mode;
every reveal, generation and compose consumer must recognize it explicitly.

`moderation_replace` in `backend/pipeline/moderation_replace.py` owns the single replacement draw:

- Scene: exclude the teacher-rejected candidate from selection, preserve earlier attempts/history,
  append a fresh attempt using the recorded scene intent, approved refs/style and the source prompt,
  clear `final_image_ref`, and increment the scene moderation-replacement count and paid cost.
  Route to the existing `consistency_check`, then `output_mod`. In replacement mode the checker
  judges only the fresh candidate, finalizes it with its real passing/failing/unchecked result, and
  never routes to `regenerate` or selects an earlier candidate. This resolves D-N using the existing
  degraded-quality policy: a safety-cleared replacement may ship with failing/unchecked consistency,
  accurately reported. Teacher safety clearance is not a quality verdict.
- The replacement uses the **one existing output-moderation redraw slot**, not another consistency
  attempt. Total scene draws stay at `settings.max_scene_attempts + 1`; read the setting at call
  time. Existing `IMAGE_BUDGET` remains unchanged. Disable replace after this slot is spent or when
  `check_image_budget` fails. A second safety flag creates a new review with allow/stop, not another
  draw. Existing consistency loops before the original selection retain their limits.
- Reference: use the existing one-per-book moderation-redraw allowance
  (`cost.ref_mod_retry_count < MAX_MOD_REDRAWS`) and one fresh draw with its recorded description,
  style and any original tapped emphasis. Use existing reference-judge behavior to record the new
  ref verdict; then `char_ref_mod`. No scene-consistency judge is added to references.
- A provider refusal with no returned picture is the existing provider failure, not a releasable
  safety flag. Fail honestly, retain writing, no automatic softened retry, substitute or third draw.
  Existing classifier error/fallback policy is retained; missing/error is not teacher-overridable.

The graph adds exactly two node files. Bound recursion separately from image cost: for feature
mode derive a named step bound in `app/config.py` from the unchanged draw/retry caps plus the
review/replacement edges, with a no-provider worst-path graph test. Keep baseline
`RECURSION_LIMIT = 87` unchanged; do not pretend its existing arithmetic covers new nodes.
Indefinite human waiting does not occupy a worker or require an unbounded running invocation.

#### 9.9.5 Privacy, delivery, withdrawal and lifecycle

In teacher-review mode authorize first, clamp/validate, then successfully `redact_pii` on title
and story **before** insertion, RQ arguments, checkpoints, tracing or classification. Store only
privacy-processed story in `jobs.input_text`; even `Input.raw_text` receives that processed text
for these jobs. Keep the existing title-redaction acknowledgement before persistence. On privacy
failure persist neither review nor job. Baseline behavior is unchanged by the rollout switch;
this narrowly scopes the new intake path rather than declaring existing raw storage safe.

Title classification remains synchronous. A flag creates a private title review and an
`awaiting_teacher` job containing only a neutral display title until clearance; a service failure
returns a retryable error with no held job. Snapshot optional settings and feature mode at intake;
checking text in `input_gate` cannot proceed past an unresolved title. New title/story classifier
calls consume processed text. Source writing retained for recovery is the privacy-processed
submission, not a newly retained original-PII copy.

Current browser Storage policies allow all images under an author's job UUID; hiding an `<img>`
is insufficient. For **all teacher-review jobs**, deny direct browser-role Storage SELECT/signing
of that prefix. Retain service-role provider access and the private bucket. Child and classroom
peer reads use proposed `GET /jobs/{job_id}/images/{asset_id}`: a server-defined asset ID bound to
an exact selected reference/page, never an arbitrary Storage path. Authenticate, check current
membership/job state/epoch and exact safety eligibility, fetch internally through `providers.py`,
and recheck immediately before returning bytes. No redirect or bearer Storage URL to children.
Use `Cache-Control: private, no-store`; browser fetch with the existing bearer token and render a
temporary blob URL, revoked on state change/unmount. Internal provider Storage reads still use
signed URLs. This is the narrowly proposed ADR-006 delivery amendment, not a new media service.

While held, no generated picture or partial book is child/peer-readable. After reference release,
only exact cleared references can reach the existing child reveal. Completed pages require all
selected subjects cleared and no open review. Peer/gallery/PDF additionally require current
editorial approval, active membership and no withdrawal/deletion. PDF rechecks at response time.
Review reveal requires the owner teacher and exact current review; expose guarded bytes only
after explicit reveal. Previously revealed content may remain on that teacher's review screen
while a decision fails, but a changed subject starts hidden again. ADR-079 researcher inspection
continues through its authenticated projected endpoint, with the same private-field exclusions;
it grants no teacher commands and no browser Storage policy.

Withdrawal is whole-book containment: hide all generated pictures from normal child/peer readers,
remove it from gallery/export immediately for new authorized requests, invalidate child blob URLs
on Realtime/refetch/visibility return, clear editorial approval, and hold generation. This safely
covers downstream pictures derived from a withdrawn reference or text. For such a withdrawal,
allow may restore the same exact subject under current policy; if it violates policy, stop/new
submission is the recovery. Replacing a reference after scenes exist is unavailable in this
initial scope, because silently using dependent scenes would be incorrect and redrawing them
would exceed the approved replacement. Scene replacement after completion may replace that
scene only within its remaining slot. Stop and inspection remain available without paid work.
Bytes already seen/downloaded, or a response already delivered before withdrawal, cannot be
recalled. The design guarantees denial of subsequent requests, not erasure of prior exposure.

For teacher-review jobs, leave `jobs.error` null or a content-free stable failure code; browser
row access must not expose raw exception bodies even through an explicit `select('*')`.
Do not publish Langfuse traces for teacher-review jobs. Strip raw text, private review evidence
and signed URLs from public metrics, errors and trace links; retain private authenticated
research inspection. This is a scoped exception to public tracing under ADR-030; existing D-R
remains open for baseline jobs. New record explanations containing free text must pass redaction
before persistence. A privacy failure is a service failure, never an evidence fallback.

Implement ADR-044's finish marker in ticket 05; that accepted design is
not currently implemented. Quiescent `awaiting_teacher` and `stopped` join its allowed deletion
states. Until deletion exists, do not show a false-working delete control. Ticket 08 verifies
compatibility with the specified deletion flow; it does not take on building the previously
unbuilt general deletion feature. Real-child release requires the applicable erasure/consent
workflow to be in place. Removed students lose
all product/command/image access immediately through current profile checks; owner teachers may
still inspect existing classroom records, but cannot allow/replace/resume for an inactive or
moved author. Do not transfer a hold to a different classroom or invent a retention exemption.
Existing account/classroom deletion and consent withdrawal rules remain applicable; no new TTL.

#### 9.9.6 Complete provisional criteria and teacher copy

The policy ID is `teacher_review_policy_v1`. This is **owner-accepted project policy requiring
educator/ethics review before real-child use**, not a claim that an external institution has
approved it. It applies equally to English, Filipino and Taglish for Grade 5–6/ages 10–12.
Assess meaning and visible evidence in context, not keywords, genre, species or language alone.
The six agreed rows in §9.5.1 remain binding. Add these definitions to make every release auditable:

| Criterion ID | Prohibited / hold boundary | Permitted contextual boundary |
| --- | --- | --- |
| `sexual_content` | Sexual acts, erotic detail, sexualized pose/focus, sexual coercion or exploitation, including fictional/animal characters | Ordinary affection and age-appropriate non-erotic factual body discussion; never an exemption for prohibited exposure |
| `exposure` | Visible genitals, clearly exposed buttocks or bare breasts in generated images | Ordinary swimwear, covered caregiving and changing behind a screen, with no sexualization |
| `graphic_harm` | Gore, visible organs, dismemberment, graphic wounds or prolonged graphic suffering, including animals | Non-graphic conflict/injury, danger, loss and rescue without graphic detail |
| `harm_instruction` | Actionable steps, encouragement or celebratory framing inviting imitation of violence, self-harm, dangerous challenges, weapon-making or abuse | Non-actionable, non-graphic narrative depiction, prevention, seeking help and recovery |
| `targeted_abuse` | Encouraged bullying, credible threats, dehumanization or violence toward a person/group, including discriminatory attacks | Clearly critical non-graphic depiction, standing up to bullying, reconciliation and indirect narration of prejudice |
| `discriminatory_slur` | Explicit discriminatory slurs in material cleared for generation/display, including critical quotation | Indirect narration without reproducing the slur; revised wording is a new child submission |
| `exploitation` | Encouraging grooming, coercion, sexual exploitation, trafficking or abuse of a child/person/animal; instructions facilitating it | Non-graphic prevention/help-seeking or a critical reference without exploitative detail |
| `substances` | Instructions encouraging a child to obtain, prepare, misuse or conceal intoxicants, drugs or poisons | Non-graphic critical depiction, refusal, prevention or recovery without instructions/encouragement |
| `adult_detail` | Explicit non-discriminatory sexual/abusive language or non-educational adult sexual detail intended for child presentation | Ordinary disagreement, mild exclamations, factual non-erotic discussion and emotional expression |
| `privacy` | Structured personal identifiers not successfully redacted, contact solicitation or exposing someone's private information | Successfully privacy-processed fictional narrative; cannot override a failed privacy process |

Threatening/encouraging visual framing is assessed independently of a cautionary caption. An
automated label is evidence, not a category veto. Teacher allow means the exact subject **does
not cross** the applicable prohibited boundary; it never grants an exception to that boundary.
For a broad/unknown classifier label show the applicable full criterion checklist and require
confirmation against that checklist after contextual inspection. Show **The recorded reason is
unavailable** when none was supplied; do not invent a model explanation or make an unknown label
an automatic veto. Uncertain teachers can leave, replace when permitted or stop. Service errors,
privacy failure, missing pictures and provider refusals are not teacher-clearable flags.

Teacher confirmation: **I have reviewed this exact [text/picture]. It meets the displayed safety
criteria.** Show criterion definitions/current policy before confirmation, require checked
confirmation, and record the confirmed criteria. No mandatory written explanation. On policy
change, refetch current criteria and ask confirmation again; no silent decision migration.
During ticket 13, put policy definitions/version in the proposed data-only
`backend/app/moderation_policy.py`: one shared source imported by provider instructions and the
teacher criteria endpoint, with no policy service/interface. Text primary/backstop apply the
textual criteria; image primary retains sexual-content/exposure screening; image backstop applies
all applicable visible criteria. Both pictures' framing and text remain subject to shared policy.
Role-specific instructions derive from that source during separately authorized calibration.
Preserve existing primary/backstop responsibilities/models and strict validation;
do not pretend replacing prompt wording has measured efficacy. Audit 01 owns labelled boundary
examples and false-alarm/miss measurement before adopting changed classifier instructions.

#### 9.9.7 Optional themes, queue and recovery UX

Theme detector: one strict structured-output call via `providers.py` using the existing configured
text-analysis model, after shared text safety clears and before `analyze`/paid images. Its validated
response is `{matches: list[ThemeDetection]}` with unique enabled IDs only, no extra keys and
privacy-processed reasons; do not accept unrecognized/disabled IDs as a pass. Persist its
instruction version `optional_themes_v1`, model ID and detected enabled IDs once for the exact
privacy-processed story hash and captured classroom settings version. If no themes are enabled,
skip the call. On error/malformed output use an honest service failure, not an empty detection or
teacher override. No new provider, model setting, free-text rule or per-picture detector.

| ID | Trigger when enabled | Non-trigger |
| --- | --- | --- |
| `spooky_suspense` | Narrative fear, threatening suspense, frightening supernatural encounters or deliberately spooky settings | Friendly magic/creatures or darkness with no fear/threat/suspense |
| `story_conflict` | Physical fighting, hostile arguments or bullying between story characters, without requiring graphic harm | Friendly competition, respectful disagreement or merely describing a past resolved disagreement |
| `loss_separation` | Narrative sadness about death/loss, grief, abandonment or separation from an important person/animal | Brief disappointment or a routine goodbye with no sadness/loss/separation theme |

All detected enabled IDs share one review for that story hash/settings version. Allow confirms
those optional themes together; it is not a shared-safety exception. A title safety hold remains
separate. Newly generated picture themes do not retrigger this text-only detector. A changed story
or settings capture belongs to a new job; no edit-in-place or theme acceptance copied across jobs.

Books retains its existing editorial tabs and default **Needs review**. Add **Needs your help (N)**
as a distinct queue tab, count unresolved reviews once per job, oldest first. With no holds it
shows **No stories need your help** and a return to Books. No automatic dialog opening, queue
jump or next-story auto-advance after a safety action. Preserve the inspected context while a
request is pending/error; after success show its actual outcome and **Back to Needs your help**.
Detail layout: title/author/status, privacy-processed story, available pictures in story order,
criteria/reason, then actions. On phones use one column and normal page scrolling, not nested
scroll regions. Reuse reader/picture presentation and native checkbox/buttons; safety actions
remain distinct from `ReviewDecision` and completed-book approval.

Flagged pictures start behind **This picture needs your review** and **Show picture to review**.
Allow stays disabled until the exact image has loaded after explicit reveal. Loading, unavailable,
signing/read errors, no generated pictures, stale review, non-quiescent withdrawal and exhausted
budget each have their own message. **Try loading again** only retries the read. Escape/close
leaves the review unchanged and restores opener focus; Enter activates the focused control and
never bypasses confirmation. Stop confirmation initially focuses **Keep waiting**; confirm is
**Stop this story**. Withdrawal confirms its whole-book hiding and sharing-reset consequence.
No auto-submit on checkbox change. Focus the outcome heading after a committed decision and the
error summary after a failed one. Use established tokens, 44px targets and visible focus.

Child waiting: **Your story is saved. Your teacher will help it continue.** Actions **Back to my
books** and secondary **Stop this story**. Bookshelf label **Waiting for your teacher** opens that
same persisted process route. Stop confirmation: **Stop making this book? Your writing will stay
saved.** Actions **Keep waiting** / **Stop this story**. Stopped: **This book has stopped. Your
writing is saved.** Actions **Back to my books** / **Use my writing**. No category or diagnostic.

**Use my writing** transfers the saved privacy-processed text and cleared display title into the
existing new-story form through an author-only, tab-local `sessionStorage` handoff keyed by job
ID. It never submits/charges automatically, overwrites an existing draft without confirmation,
or copies pictures/old clearances. Remove the handoff after successful consumption, sign-out or
access loss. On storage/navigation failure keep the stopped page and offer selectable saved
writing with a **Copy writing** action and clear copy-failure feedback. Never claim transfer
success before the new form has consumed it. This is draft recovery, not teacher rewriting.

#### 9.9.8 Rollout and verification contract

Proposed server setting: `settings.enable_teacher_moderation_review: bool = False` in
`backend/app/config.py`, controlled by the deployment owner as
`ENABLE_TEACHER_MODERATION_REVIEW`. No independently authoritative frontend flag. Snapshot it
once when an authorized submission enters intake; persist `moderation_mode` with the job. A
request already captured as teacher-review finishes in that mode even if the global switch flips
before insertion. New requests after disabling use baseline; every existing teacher-review job
continues with its captured mode and existing holds remain inspectable/resolvable. A missing
review schema/config dependency is a service failure, never a silent downgrade to baseline.
Publish mode/available capabilities through authorized responses so UI follows the server.

Current shared policy is used by future checks/releases; historical evidence retains its version.
Policy update alone causes no rescan, withdrawal or spend. Bulk/emergency rescanning remains out
of scope under OD-11, not a blocker for implementing individual withdrawal. An identified actual
risk must be escalated to the owner for a separately authorized containment response.

The owner accepted ADR-080, this design and the build exception on 2026-10-27 (“accept all”).
Ticket 02 is complete as a specification handoff; ticket 05 and dependency-ordered successors
are authorized for synthetic-only, feature-off implementation. Audit 01 stays open and remains
required before adopting changed classifier criteria/prompts or making calibration claims.
No paid replay, production enablement or real-child use is authorized. Real-child enablement
additionally requires the
project owner to identify the educator/ethics reviewer, obtain and record review/consent changes,
confirm institutional handling of retained flagged material and withdrawal limits, and verify
hosted RLS/asset/lifecycle behavior. No external reviewer or approval has been supplied. The
accepted synthetic-only build scope does not claim those release gates met.

The verification seams in §9.6 are selected for this proposal: authenticated HTTP/UI into the
real graph, plus existing researcher projection; provider/network calls mocked only at the outer
boundary. Test new transitions red first with real sanitized payload fixtures, hand-derived
expectations and existing infrastructure. Reuse current relevant tests rather than multiplying
one-test-per-field unit suites. Required observations by implementation slice:

| Slice | Main observation | Critical failure/race observation |
| --- | --- | --- |
| 05 | Durable first scene flag → hidden image → child leaves/reloads same hold | Direct Storage access denied; baseline remains unchanged; unsafe interrupt never projects into reveal |
| 06–08 | Owner inspects/reveals, allows once or confirmed stop retains writing | Foreign/stale decision denied; duplicate dispatch and child-stop/allow race make no second paid continuation |
| 07 withdrawal | Running or complete release withdrawn → whole-book containment | In-flight result/old epoch cannot publish or spend again; old sharing approval stays cleared |
| 09–10 | One replacement → actual fresh verdict → safety clearance or new hold | Rejected original cannot win; exhausted slot/budget and provider refusal do not buy another draw |
| 11–12 | Privacy-processed text/title hold and exact-content allow | Privacy failure persists nothing; missing checkpoint never restarts; pre-graph title starts once only |
| 13–15 | Current criteria reference and grouped enabled text themes before paid work | Detector errors are not passes; same story/theme/settings acceptance is not repeated; switch-off drains captured holds |
| Lifecycle | Quiescent held/stopped job follows ADR-044 cleanup across all stores | Delete/allow/withdraw race cannot resurrect; removed author cannot resume or fetch pictures |

Run existing backend/frontend pre-merge commands for each implemented slice; prove graph
`update_state` scheduling, bounded steps, database transaction behavior, RLS and guarded assets
against a disposable local/hosted stack before calling those contracts verified. Do not label a
stubbed database race test as proof of transactional isolation. No paid replay, deployment, code,
migration or accepted-ADR change is part of finishing this documentation proposal.

**External technical basis:** Supabase documents private-bucket access through authenticated
requests or signed URLs and the limits of signed-link revocation. The guarded-delivery design is
our inference for this withdrawal requirement, not a hosted verification result. Sources:
[Storage access control](https://supabase.com/docs/guides/storage/security/access-control),
[private asset delivery](https://supabase.com/docs/guides/storage/serving/downloads).

### 9.10 Ticket 05 implementation record (2026-10-28)

The scene-image slice and its enabling contracts are built. The setting remains false by
default. This is synthetic-only implementation evidence, not calibration, deployment or
real-child release approval. Tickets 06–15 retain their own acceptance criteria.

- Migration `0022_teacher_moderation_hold.sql` records captured mode/settings, generation epoch,
  quiescence marker and private immutable review subjects. Browser roles cannot read reviews or
  feature-job Storage objects, including through existing researcher policies.
- `app/moderation_hold.py` transactionally projects an unresolved checkpoint into one review and
  `awaiting_teacher`. Authorized `/jobs/{job_id}/state`, `/images/{asset_id}` and
  `/reconcile-hold` routes expose neutral state, selected cleared image bytes and explicit
  checkpoint-only recovery. Teacher inspection/decision routes belong to 06–09.
- `worker/run_job.py::run_review_storybook_job` serializes execution with an advisory lock,
  fences provider/publication work by epoch and current membership, disables public tracing,
  distinguishes child reveal from moderation review, and writes the final marker after closing
  the checkpointer. A hard death before projection or before the finish marker is repairable
  without repeating moderation or drawing. A timeout cannot abandon an SDK thread and then
  report quiescence. The supervisor marks only the expected epoch after reaping the horse.
- Feature intake processes title/story before persistence. Failure stores nothing. Captured
  policy/settings survive a switch-off during intake or queue delay. Text, reference and title
  flags retain baseline outcomes until their own tickets.
- Child process/bookshelf/reader surfaces recognize the persisted hold, offer an in-app exit and
  hide the held picture. Product image consumers use abortable, noncached guarded bytes for
  feature jobs. Baseline signing and soften-and-retry remain intact.
- `TEACHER_REVIEW_RECURSION_LIMIT = 88` adds the single terminal review pause to the unchanged
  capped baseline path. A no-provider graph test reaches a last-scene hold after ten scenes and
  thirty consistency attempts. Ticket 09 must account for its replacement edges when built.

Verification uses disposable local PostgreSQL with synthetic auth/Storage schemas and all
migrations, real PostgresSaver checkpoints, and SQL browser roles. The integration test drives
authenticated HTTP intake, the fresh worker graph, guarded reference read, HTTP confirm and the
first flagged scene. Separate injected projection failure and supervisor death cases prove
checkpoint-only repair, duplicate delivery and epoch stability. Direct browser-role Storage
selection and private review reads are denied. Component tests prove neutral leave/reload and
explicit recovery without image signing or a new submission.

Backend lint passed. The full backend suite produced 1,542 passes, 89 skips, six deselections
and six existing PDF failures because the local WeasyPrint native library is unavailable.
Frontend lint and production build passed; the full unit suite produced 731 passes and one skip
across 77 files. Standards and specification reviews found no remaining concrete blocker.
The broader existing RLS suites produce 48 passes and the same 16 failures on this branch and
the unchanged base against the synthetic stack. This does not verify hosted Supabase
Storage/PostgREST/Realtime behavior. Phone-width visual browser verification is unrun because
the session exposes no browser. These limits remain explicit release checks, alongside the
educator/ethics/consent gates in §9.9.8.

### 9.11 Ticket 06 implementation (2026-10-28)

The owner-only Books inspection slice is implemented for the accepted synthetic-only,
default-off scope. Books keeps **Needs review** as its default editorial tab and adds a distinct
**Needs your help** queue. Its authenticated list counts each unresolved held job once and orders
by hold time, then review UUID. Empty/error states include an in-app return or read-only retry.

`backend/app/moderation_hold.py` implements §9.9.3's list/detail/reveal routes. Detail projects
processed story/title and ordered reference/scene descriptors from the pinned checkpoint, never
Storage paths or bearer URLs. Missing checkpoint/picture context stays distinct from a scene not
yet drawn. The additional owner-only
`GET /teacher/jobs/{job_id}/moderation-review/images/{asset_id}` context-picture route requires
`review_id` and `subject_version` query parameters. It accepts only an available server-selected
reference/scene descriptor. The held descriptor is readable only by the explicit reveal POST.
Both picture routes use internal signed Storage reads, current owner/review/epoch checks before
and after download, and `Cache-Control: private, no-store`. Reveal additionally verifies the
downloaded bytes against the recorded subject hash. Inspection performs no writes or generation.

`NeedsHelpQueue` provides a native full-screen scrolling dialog with processed writing, missing
content states, a warning before reveal, image-read retry, and temporary blob URLs. Refresh,
visibility return and job Realtime changes refetch current detail and hide/revoke old pictures.
Escape/close restores the opener, or the stable queue when that item has disappeared. Safety
decisions and criteria/explanation copy remain the separate follow-on tickets.

Verification: the existing real-graph/disposable-Postgres synthetic hold test now checks owner
list/detail/reveal, child and other-teacher denial, no leaked paths/URLs, exact bytes, read failure
with retained writing and an unchanged review decision. Books tests use a captured response from
that integration run and cover explicit reveal, image failure, Escape and detached-opener focus.
Desktop/phone browser verification is unrun: the in-app browser is unavailable and the browser
inventory is empty. Hosted Storage/Realtime delivery and owner sign-in remain release checks.
No feature setting, classifier prompt or real-child enablement changed.

Final local checks: `uv run ruff check .` passed; `uv run pytest` with disposable
`TEST_MODERATION_DB_URL` produced 1,542 passes, 89 skips, six deselections and six existing PDF
failures (`503` instead of the expected response because WeasyPrint cannot load native libraries).
The same six failures are recorded on the ticket 05 base. The four targeted hold integration
cases pass, including available context bytes, stale-version denial and ownership revoked during
download. Frontend lint and production build/typecheck pass; the Books file passes all 29 tests.
Unrestricted `pnpm test` discovery stalled, including a retry excluding generated caches.
`pnpm exec vitest run app components lib utils middleware.test.ts --maxWorkers=2 --reporter=dot`
then passed all 77 source test files and 734 tests. No source tests were excluded. Both review
axes are clear after the failing-first detached-opener regression and focus fallback fix.

### 9.12 Ticket 13 implementation (2026-10-28)

`backend/app/moderation_policy.py` is the data-only source for the accepted provisional
criteria, optional-theme boundaries, policy version, audience and validation caveat in
§§9.9.6–9.9.7. `GET /teacher/moderation-policy` checks the stored teacher role and returns
private, no-store data. Existing owner-only review detail now includes subject kind, captured
criteria/policy/settings and classifier evidence, alongside the current policy version.
Nothing is added to child or Realtime projections.

Image classifiers retain their boolean result and existing prompts. In teacher-review mode
they additionally return privacy-processed reasoning to `output_mod`, which checkpoints it in
the existing evidence fields before hold projection. Model IDs are captured before each call.
Reasoning privacy failure stops processing as a service error and cannot trigger primary-error
fallback. Baseline calls do not request reasoning capture. Missing historical reasoning remains
missing; reads do not reconstruct it from current configuration or logs.

Books' Needs your help queue and inspection offer a native, keyboard-reachable **Review criteria**
disclosure with loading, retry, close and Escape/focus recovery. Inspection shows the recorded
origin, criteria, policy/settings, classifier outcome, labels, model/instruction version, time
and explanation; missing evidence is labelled unavailable. Current definitions are clearly
separate from the submission's captured evidence. No decision controls or theme detector are added.

Verification: provider reasoning redaction, node capture/missing reasoning and call-time model
identity, privacy-failure containment, real graph/Postgres projection and authorized policy/detail
reads are covered. Frontend fixtures were captured from that synthetic integration run. The Books
file passes all 30 tests. Backend lint and frontend lint/build/typecheck pass. The full backend
suite reports 1,545 passes, 89 skips, six smoke deselections and the same six pre-existing native
WeasyPrint/PDF failures recorded in §9.11. Unrestricted and explicit-source frontend fork runs
stalled and were stopped. The complete source suite then passed all 77 files and 735 tests using
`pnpm exec vitest run app components lib utils middleware.test.ts --maxWorkers=2 --pool=threads --reporter=dot`.
Browser/phone inspection remains unrun: browser inventory is empty and the in-app browser is
unavailable. Hosted delivery and educator/ethics/real-child gates remain unchanged.
Both requested independent review agents hit the account usage limit without returning findings.
Local Standards/Spec review corrected the policy fixture's audience string; independent review
remains uncompleted.

### 9.13 Ticket 07 implementation (2026-10-28)

Synthetic-only, captured `teacher_review_v1` scene-picture allow and whole-book withdrawal
implement §§9.9.3–9.9.5. Intake remains disabled by default. Other subjects and replacement
remain later tickets; stopped-run recovery is recorded in §9.14. Allow requires the current owner, active author, matching review/hash/epoch,
current policy and explicit confirmation of every recorded criterion. The retained checkpoint
and exact image bytes must still exist. An immutable decision commits with its pending dispatch
before unique RQ delivery. Explicit retries reuse that command; reads never enqueue.

The serialized worker reads committed decisions, resumes the pinned evidence checkpoint, and
sets only the selected attempt's safety eligibility and scene status to `teacher_allowed`.
Consistency verdicts and classifier evidence remain unchanged. Completed scenes are not redrawn;
later scenes are independently moderated and can create another hold. The persisted job image
count includes the held checkpoint's draws. Normal image-budget checks remain in place.

Withdrawal is available for current selected picture clearances from teacher book detail.
It immediately advances the epoch, hides all pages/reveal and clears both editorial timestamps.
The control worker waits for the old worker's per-job lock, validates retained bytes and safe
checkpoint progress, clears the affected graph eligibility and anchors a new review through the
real `update_state(as_node='moderation_review')` seam. Migration
`0023_anchor_withdrawn_clearance.sql` permits only the initial checkpoint/continuation attachment
to an undecided withdrawal; evidence and decided records stay immutable. Re-allow can restore a
completed book through `END`, without restoring sharing approval. Editorial writes for these
jobs use the same job-row transaction as withdrawal. An incomplete paid effect fails honestly
instead of replaying it, with incurred image count retained.

The teacher must explicitly reveal and load the held picture before confirmation. Pending,
unknown-response, retry and durable-success states preserve context and focus the outcome.
Withdrawal confirms whole-book hiding and sharing reset, initially focuses Keep clearance, and
has an explicit delivery retry. Existing child progress/review subscriptions observe the status
transition without receiving policy or private evidence. Browser and hosted verification remain
unrun: no browser is connected and the in-app browser is unavailable. No paid replay, prompt
calibration, feature enablement or real-child release is included.

Verification (synthetic data, mocked provider boundaries, disposable Postgres on localhost):

- `uv run ruff check .`: passed.
- `uv run pytest tests/test_teacher_hold.py tests/test_run_job.py tests/test_graph_stub.py tests/test_main.py tests/test_review.py -q`: 150 passed.
  Real graph/SQL scenarios cover concurrent same-request commands, stale/version/access denial,
  Redis outage and durable retry after reload, later holds, withdrawal/re-allow through `END`,
  stale editorial writes, killed control delivery, committed-but-unapplied later clearance,
  ownership loss before its pure replay, missing post-commit checkpoints and in-flight paid
  effects. New failure cases were observed red before their corresponding fixes.
- `uv run pytest`: 1,548 passed, 89 skipped, six smoke deselections and the same six native
  WeasyPrint/PDF failures recorded in §§9.11–9.12. Representative output:
  `assert 503 == 200` and `PDF download failed (OSError)` in `tests/test_pdf_export.py`.
  Local failure output is retained in `.scratch/ticket07-backend-final.txt`; no PDF test was
  skipped, removed or loosened. Credential/local-Supabase-dependent skips remain unchanged.
- `pnpm lint` and `pnpm build`: passed, with CI placeholder public Supabase values for build.
  The build includes TypeScript checking. Intermediate `pnpm exec tsc --noEmit` also passed.
- `pnpm test --pool=threads --maxWorkers=2` stalled during unrestricted discovery and was
  stopped. The complete source command
  `pnpm exec vitest run app components lib utils middleware.test.ts --maxWorkers=2 --pool=threads --reporter=dot`
  passed all 77 files and 738 tests. The Books file passes all 33 tests, including refresh-safe
  same-command retry, loaded-picture/criterion gates, withdrawal focus and current-state replay.
- Migration 0023 applied successfully to the disposable database. Hosted application is unrun.
- Both Standards and Spec review agents re-reviewed the fixes and report zero unresolved
  findings. Browser/phone UI, hosted access, paid providers and real-child enablement are unrun.

Owner-delegated boundary decision (2026-10-28): preserve one open review. While a different
picture is held, the whole book is already hidden and generation paused; earlier-clearance
withdrawal is unavailable. The teacher view says so and offers leaving it waiting, without
requiring an uncertain allow. No second review queue or new review-state contract is introduced.
This differs from an already-committed later allow: that decision has closed its database review,
so the control worker applies only its pure review node, stopping before its paid continuation,
before anchoring withdrawal of the earlier picture.

### 9.14 Ticket 08 implementation (2026-10-28)

The existing teacher decision route now accepts confirmed `stop`; active child authors use
`POST /jobs/{job_id}/stop` with the accepted review/epoch/request identity. Both serialize on
the job row, recheck stored authority, require an undecided matching hold and worker quiescence,
record an immutable stop, advance the epoch once and set terminal `stopped` without dispatch.
Idempotent retries return current state. A losing stop returns `409` with authorized current
status and cannot cancel a released story. Stop retains processed writing and incurred spend.
It does not implement general deletion or teacher reopening.

Books and the child process route share native stop confirmation with Keep waiting initially
focused, Escape/cancel restoring the opener, and no write before confirmation. Unknown responses
offer same-request retry and current-state reconciliation. Teacher inspection hides old pictures
and decision controls after stop. The child bookshelf labels stopped runs **Writing saved**;
process and direct book routes show the accepted neutral stopped copy and bookshelf exit.

Author-only `GET /jobs/{job_id}/state` adds the open `review_id` for held-stop identity and
`saved_writing: {text, title}` only for that author's stopped teacher-review job. No private
evidence or asset path enters this response. Use my writing stores those processed fields in
tab-local `sb.stopped.{profileId}.{jobId}` and opens the existing writing form's `?reuse=` route.
The form rechecks current access through the same API, shows loading/retry and an explicit use
action, confirms replacement of any existing draft, and consumes the handoff without submitting.
Root-mounted cleanup survives reload, clears on sign-out, and rechecks retained handoffs on
visibility return. Lost access clears the handoff. Storage/navigation failure keeps selectable
writing and Copy writing with honest copy-failure feedback on the stopped page.

Synthetic verification: stop API tests were observed failing before implementation. Real
graph/disposable-Postgres cases cover teacher/child stop, duplicate same-request commands,
non-quiescence, removed-author denial, retained writing/image count, stale-worker fencing,
reopen denial and concurrent child-stop/teacher-allow serialization. UI tests use a stopped
response captured from that integration run and cover cancel/Escape/focus, lost-response retry,
storage failure, existing-draft replacement and reload/sign-out/access-loss cleanup. Review
findings about cleanup after reload and loading state are resolved; both Standards and Spec
re-reviews report zero unresolved findings.

Checks: `uv run ruff check .` passes. Targeted
`uv run pytest tests/test_teacher_hold.py tests/test_main.py -q` passes 74 tests. Full
`uv run pytest` with disposable `TEST_MODERATION_DB_URL` reports 1,551 passes, 89 skips, six
smoke deselections and the same six native WeasyPrint/PDF failures recorded in §§9.11–9.13.
Representative failure: `assert 503 == 200` and `PDF download failed (OSError)` in
`tests/test_pdf_export.py`; full output is in `.scratch/ticket08-backend-full.txt`. No PDF test
was skipped, removed or loosened. Credential/local-Supabase-dependent skips remain unchanged.
Frontend lint, production build/typecheck and the 113 targeted Books/process/write/cleanup tests
pass after review fixes. Unrestricted discovery reported a withdrawal-replay test failure before
stalling; that test passes in targeted checks and the complete serial source run. The two-worker
source run also stopped producing progress and was stopped. The complete source command
`pnpm exec vitest run app components lib utils middleware.test.ts --pool=threads --maxWorkers=1 --reporter=verbose`
passes all 78 files and 742 tests, with no source tests excluded. Full output is in
`.scratch/ticket08-frontend-serial.txt`. Browser/phone verification is unrun: browser inventory is empty and
creating an in-app browser returns `Browser is not available: iab`. Hosted delivery, paid
providers and real-child release are unrun. The feature remains disabled by default.
