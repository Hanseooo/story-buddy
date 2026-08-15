# Feature Spec — self-refusal-fallback

**Status:** draft — **⏸ DEFERRED 2026-08-02, do not build** · **Phase:** 2 · **Owner node:** *none — a cross-cutting helper,* `backend/pipeline/refusal.py`

> **Deferred, with the spec kept.** This fires only when the model *falsely* refuses a safe story.
> Open-weight models refuse least (ADR-011), Qwen-Image-Edit ships no safety filter at all, and the
> current behavior already fails closed. So the trigger may not exist in this stack. The four reopen
> conditions live in `DECISION_BACKLOG.md`'s `self-refusal-fallback` row — the sharpest one is a job
> failing with `parsed is None` on a story that **passed** the input gate. Reopening is a build, not a
> design session; §8's spike is the first step, not a precondition for keeping this file.
**Derived from:** MASTER_SPEC §2 · **Rationale:** PRD §13.4 (mechanism 4), ADR-011 mech. 4, ADR-025 D1,
`ethics_and_safety.md` Stage 4 · **Scope frozen:** `DECISION_BACKLOG.md`, 2026-08-02

> Not one node. Like `prompt-optimizer` (pure helpers) and `input-gate-hardening` (API boundary +
> `providers.py`), this spec owns a **seam**, not a graph position. It adds no node, no edge, no
> super-step, and amends no ADR.

## 1. Purpose

The model **declines** a benign prompt — a child's dragon fight, a monster under the bed — and the job
dies. PRD §13.4 promises *"a scary-but-innocent story must not dead-end."* Today it does: every refusal
surfaces as a hard failure and the whole book is lost (ADR-025 D1). This spec makes a refusal survivable
by softening the prompt once and retrying, and it does so **without** softening genuine provider errors,
which must still fail loudly.

**Explicitly not this spec:** `output_mod`'s soften-and-retry. That is the *opposite* trigger — the model
complied and a classifier flagged the result — and it already shipped with `moderation-stack`
(`output_mod.py`, its own `_soften_prompt`). It is not redesigned here.
See `moderation-stack.md` §8 for the corrected ownership note.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** nothing. Every function here is pure or wraps a `providers.py` call.
- **Writes:** nothing. `contracts/` is **untouched** — no `schema_version` bump, no new field.
- **Invariants:**
  1. A softened prompt **never drops content** from the original — it prepends/appends framing only,
     the same invariant `correct_prompt` holds (`prompt-optimizer` invariant 3).
  2. A refusal is retried **at most once** per call site. There is no ladder, no loop, no recursion.
  3. A non-refusal provider failure is re-raised **unchanged**, preserving ADR-025's taxonomy exactly.

## 3. Position in the system map

No position. Four existing effect boundaries gain a wrapper; the graph topology is unchanged:

| Call site | Provider call | Refusal today |
|---|---|---|
| `analyze.extract_entities` | `structured_text` | hard fail (`analyze.py:83-85`) |
| `segment.segment_scenes` | `structured_text` | hard fail (`scene-segmentation.md` §7) |
| `char_bible._draw_reference` | `text_to_image` | hard fail (`char_bible.py:117-119`) |
| `generate_scene.generate_and_store` | `edit_image` / `text_to_image` | hard fail |

⚠️ The two image rows are **gated on the §8 probe** and are not built in the first cut. Reason in §8.

## 4. Behavior & edge cases

### 4a. Detection — `providers.py`

Refusal detection is vendor-shaped, so it lives in the one module allowed to name a vendor
(ADR-003, ADR-015). Policy does not.

```
class RefusalError(RuntimeError):
    """The model declined to answer. Distinct from a provider failure (ADR-025)."""
```

In `_chat`, **before** the existing `message.parsed is None` check:

```
if message.refusal:                      # OpenAI SDK populates this on .parse()
    raise RefusalError(message.refusal)
```

Ordering is load-bearing. A refusal also leaves `parsed is None`, so checking `parsed` first would
class every refusal as a hard failure — which is precisely today's bug. `message.refusal` is the
narrow signal; `parsed is None` keeps its current meaning (provider returned nothing parsable) and
keeps raising `ValueError`.

### 4b. Policy — `pipeline/refusal.py`

Two functions, no state, no I/O:

```
def soften(prompt: str) -> str
def retry_on_refusal(call, prompt: str)
```

`soften` prepends a framing clause that names the register rather than deleting the peril — the child's
dragon stays in the story:

> *"This is a gentle, age-appropriate children's storybook illustration. Any conflict or peril is
> cartoonish, bloodless and non-frightening."*

`retry_on_refusal(call, prompt)` runs `call(prompt)`; on `RefusalError` logs, then runs
`call(soften(prompt))` once and returns it. A second `RefusalError` propagates → job `failed`, per
ADR-025. Anything that is not a `RefusalError` propagates immediately, unsoftened.

### 4c. The "gentle reframe" is copy, not a third attempt

PRD §13.4 reads *"soften-and-retry the prompt, **then** a gentle 'let's imagine that part a little
differently.'"* The quoted string is **kid-facing copy**, not a further generation — so the ladder is
one softened retry, then a failure screen. `kid-flow-ui` owns the copy; `ethics_and_safety.md` Stage 4's
looser phrasing ("the system gently reframes the request") is the same mechanism described from the
child's side. `USER_FLOW.md` §6 was corrected to match on 2026-08-02.

This reading is also the cheap one: a third attempt would be a third **paid image draw** per scene and
would break ADR-025 D4's budget (§5, CC-3). If a second automated attempt is ever wanted, it is an ADR,
not a spec edit — it changes a frozen cost bound.

**Edge cases**

| Case | Behavior |
|---|---|
| Softened retry also refused | Propagates. Job `failed`. No partial book (ADR-025, ADR-010). |
| Provider error that is *not* a refusal | Re-raised unchanged. **Never softened** — softening a 503 wastes a call and masks the real fault. |
| `parsed is None` with no `refusal` | Still `ValueError`, still a hard failure. Unchanged. |
| Refusal on the *softened* text at `analyze` | The story is likely genuinely unsafe and the input gate missed it. Correct outcome is a hard fail, not a third softening. |
| Refusal during `char_bible`'s 3-draw loop | The wrapper sits **inside** the loop on one `text_to_image` call, so a refused draw costs one extra draw, not a lost character. The ADR-028 draw cap is unchanged (a softened retry is the same draw, not a new one). |

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [ ] **CC-1 Moderation ordering** — N/A. Adds no gate and no node; ordering is untouched.
- [ ] **CC-2 PII redaction** — N/A. Operates on prompts already built from `redacted_text`.
- [x] **CC-3 Cost control** — text-side: at most **+1 call** per refusing boundary, and refusals are rare
  by construction (both text boundaries run *after* the input gate has passed the story).
  ⚠️ **Image-side changes a frozen number.** A softened image retry is a paid draw that
  `cost.image_count` does not currently see: `generate_and_store` returns `paid: bool`, so any retry
  inside it is invisible to ADR-025 D4's breaker. Building the image half therefore requires
  (a) `generate_and_store` returning a **paid count**, not a bool, and (b) `IMAGE_BUDGET` moving from
  `MAX_SCENES * 2 + 9` to `MAX_SCENES * 3 + 9`. Both are `config.py`/spec-level changes — ADR-025 froze
  the *mechanism*, not the constant — but they must land in the same change as the wrapper or the
  breaker silently under-counts.
- [ ] **CC-4 Security** — N/A. No new I/O, no URL handling.
- [x] **CC-5 Observability** — one `log.warning` per refusal naming the call site and the model, and one
  `log.info` on a softened retry that succeeds. Refusal rate is the metric that tells us whether the
  image half of this spec is needed at all (§8), so it must be findable in Langfuse, not a silent
  counter.
- [ ] **CC-6 Accessibility** — N/A (pipeline helper). The kid-facing reframe copy is `kid-flow-ui`.
- [x] **CC-7 Reproducibility** — `soften` is pure and deterministic; the same refusal always produces the
  same softened prompt. No seed coupling.
- [ ] **CC-8 Kid vs parent design** — N/A.
- [x] **CC-9 Failure states** — a twice-refused job fails with a named reason. ⚠️ `jobs.failure_reason`
  has no `model_refused` value and **no spec owns the column** — see `job-failure-reason` in the backlog.
  Until it lands, the reason is a log line only. This spec does **not** claim that column.
- [x] **CC-10 Checkpointing** — the retry is in-super-step. A crash between the refusal and the retry
  resumes the whole node from its last checkpoint and re-runs the original call, which is the existing
  behavior for every node. `generate_and_store`'s Storage-exists skip still holds.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Against the `providers.py` seam (MASTER_SPEC §6 "the node test seam"), all model calls mocked:

**`providers._chat` detection**
- `message.refusal` set → raises `RefusalError` (**not** `ValueError`), even though `parsed is None`.
- `message.refusal` empty and `parsed is None` → still raises `ValueError`. Regression guard on 4a's
  check ordering.
- `message.refusal` empty and `parsed` set → returns normally, no behavior change.

**`refusal.soften`** (pure)
- Output **contains the original prompt verbatim** (invariant 1).
- Idempotent in effect: softening twice does not stack duplicate framing.

**`refusal.retry_on_refusal`**
- Call succeeds first time → called **once**, no softening. Guards against paying twice on the happy path.
- First call raises `RefusalError`, second succeeds → called **twice**, second argument is
  `soften(prompt)`, softened result returned.
- Both calls raise `RefusalError` → `RefusalError` propagates, called exactly **twice** (no third).
- Call raises `ValueError` / `httpx.HTTPError` → propagates immediately, called **once**, `soften`
  never invoked (invariant 3).

**Wiring**
- `analyze.extract_entities` with a refusing-then-succeeding mock → returns a `StoryAnalysis`, job
  does not fail. This is the assertion that PRD §13.4 is true.
- `segment.segment_scenes` — same shape.

No test asserts on generated content (MASTER_SPEC §6).

## 7. Eval / quality checks (Tier B)

**N/A for correctness** — the retry either happens or it doesn't, and §6 covers that. But one number
must be **measured, not assumed**: the observed refusal rate per boundary over the Phase-0.5 corpus,
from the CC-5 log events. It decides §8's open question and it is the only evidence that this spec
was worth building. It rides on existing tracing exports; no new instrument.

## 8. Linked decisions & open questions

**Depends on**
- **PRD §13.4 / ADR-011 mech. 4** — the mechanism, and the promise this closes.
- **ADR-025 D1** — the transient/hard taxonomy this *extends* with a third class (refusal). ADR-025 is
  **not amended**: it explicitly classes content-refusal as "not a resilience concern" and hands it
  here, which is exactly what this does.
- **ADR-025 D4** — the cost breaker the image half moves (CC-3).
- **ADR-028** — `char_bible`'s 3-draw cap, unchanged by §4's edge-case table.

**Open / flagged, not guessed**

1. ⚠️ **How does fal signal a refusal — and does it ever?** Unknown, and it is the load-bearing
   unknown for half this spec. `_run_fal` reads `result["images"][0]["url"]`; a refusal might raise,
   return zero images, or — worst — return a compliant-looking image of something else, exactly the
   silent-degradation failure `REFERENCE_FIELD` was written to prevent. Worse, ADR-011's own warning
   says open image models refuse **less** and Qwen-Image-Edit ships **no built-in safety filter**, so
   the image half may have **no trigger at all** and would ship as dead code.
   **Resolution: probe before building.** One rung-1 pre-flight in `backend/spikes/`, same pattern as
   ADR-001's 2026-07-29 reference-field probe: send ~10 mild-peril prompts, record what comes back.
   - No refusals observed → **build the text half only**, and record the image half as YAGNI here.
   - Refusals observed → the probe defines the detection predicate, and CC-3's `IMAGE_BUDGET` and
     paid-count changes land with it.
2. ⚠️ **Is `message.refusal` populated through OpenRouter?** It is part of the OpenAI structured-outputs
   contract and the SDK models it on `.parse()`, but the text path is OpenRouter fronting Qwen, and
   `_chat` already carries a comment about OpenRouter silently downgrading behavior a provider does
   not support (`require_parameters`, ADR-002). If upstream never emits `refusal`, 4a's check never
   fires and the text half is inert — failing *closed*, i.e. exactly today's behavior, so it is safe
   but useless. Cheap to settle: assert it in the same spike as Q1, on a prompt the text model will
   actually decline. If it is absent, the fallback is a substring predicate over `message.content`,
   which is why detection was put behind a named exception in `providers.py` rather than inlined at
   the call sites.
3. **`jobs.failure_reason` has no `model_refused` value.** Unowned — `job-failure-reason` in the
   backlog owns the column (CC-9). Not blocking: a twice-refused job fails correctly today, it just
   fails anonymously.
4. **`output_mod._soften_prompt` duplication.** Once `refusal.soften` exists there are two softeners
   with different triggers and near-identical text. Deliberately **left duplicated** for now: they are
   three lines each and may need to diverge (one placates a generator, the other placates a
   classifier). Collapse only if they prove identical in practice — `moderation-stack` §8 records the
   same upgrade path from its side.

---

*Skipped: a soften **ladder**, a per-book refusal budget, a `RefusalError` subclass per provider, and
any `contracts/` change. Add the ladder when the probe shows one softening is measurably insufficient;
add the budget when the image half is built and CC-3's paid-count lands.*
