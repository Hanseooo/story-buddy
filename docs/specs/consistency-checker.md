# Feature Spec — consistency-checker

**Status:** built · b8f357f–13ef224 · **Phase:** 1 · **Owner node:** `backend/pipeline/consistency_check.py`
**Derived from:** MASTER_SPEC §2 (system map, node-I/O table), §3 (frozen contract), §5 (CC registry), §6 (test seam)
**Rationale:** ADR-003 (conditional edges only at real branch points), ADR-004 (VLM-as-judge,
reason-then-score, each character judged separately), ADR-010 (best-of, never a broken page),
ADR-024 (partial return, sequential per-scene loop, pure routers), ADR-025 (resilience posture),
ADR-028 (`anatomy_intact`, the closed 7-value `FailureReason` set)

> Turns `consistency_check` from a pass-through stub into the node that judges each scene image
> against its canonical character references, and **closes ADR-024's per-scene loop**. No
> `contracts/` change — every field it writes already exists.

## 1. Purpose

Judge the scene image `generate_scene` just produced against the canonical reference each present
character was drawn from, record the verdict on the `Attempt`, and finalize the scene. This is
where ADR-004's control signal actually fires, and where ADR-024's loop invariant — *exactly one
scene finalizes per pass* — gets its teeth.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `scenes[]` (`scene_id`, `attempts[]`, `final_image_ref`, `characters_present`);
  `characters[]` (`char_id`, `name`, `canonical_ref_image`).
- **Writes:** on the **last** `Attempt` only — `vlm_verdict`, `failure_reasons`, `passed`; plus
  `scenes[].final_image_ref`.
- **Invariants:**
  1. Exactly one scene is finalized per invocation, or the node returns `{}` (nothing left to do).
     Unlike `generate_scene` this node never raises — see §4.
  2. `final_image_ref` is written by **this node only**. `generate_scene` stops writing it (§3).
  3. Only the last `Attempt` is judged and mutated. Earlier attempts are never rewritten.
  4. `vlm_verdict is None` means **unchecked**, never "checked and clean."
  5. Each character is judged against **its own** reference in a **separate** `providers.judge`
     call (ADR-004). ≤2 calls per attempt, since ADR-004 caps references at 2 per book.
  6. `cost` is not touched — `Cost` counts images and this node buys none.

## 3. Position in the system map

This spec owns the loop wiring `image-generator` §8 handed it.

```
char_bible ────────────┐
                       ├──► route_next_scene ─ a scene remains ──► generate_scene
consistency_check ─────┘         └─ none remain ──► compose             │
        ▲                                                               │
        └───────────────────────── (direct edge) ────────────────────────┘
```

**One router, two registrations.** `route_next_scene` is a pure label-returning function
(ADR-024 Decision 4) registered via `add_conditional_edges` on **both** `char_bible` and
`consistency_check`. Sitting at the loop head it also handles ADR-024's empty-`scenes[]` case
(segment produced none) → straight to `compose`.

**`route_after_check` is deliberately not built.** ADR-024 specifies it as
`"regenerate" if not finalized and retry budget remains, else loop back`. This node always
finalizes — pass, fail, or unchecked — so today that router would have exactly one outcome.
`regeneration-controller` introduces the branch *and* the node it points at, and re-points the
`consistency_check` registration in the same change; a one-outcome router built now would be
edited identically. Named here so the omission is a decision, not an oversight.

### `generate_scene` gives up `final_image_ref`

`generate_scene.py` currently sets `final_image_ref` with a `# ponytail: provisional` comment
naming this spec as the change it was waiting for. That write is **removed here**, and it is
load-bearing for loop position: both nodes select *the first scene whose `final_image_ref is
None`*. `generate_scene` appends an `Attempt` and leaves the scene unfinalized; `consistency_check`
finds the **same** scene, judges its last attempt, and finalizes it. No cursor, no second
selection rule (ADR-024 Decision 3).

`docs/specs/image-generator.md` is corrected in the same change (§9).

## 4. Behavior & edge cases

### Judge boundary schema — node-local

`StoryMemory` stores `VlmVerdict` and `Attempt.failure_reasons` as *separate* fields, so the
combined judge shape is not embedded in the contract. Per ADR-023's D-F rule it therefore lives
beside its node, in `consistency_check.py`:

```python
class SceneVerdict(BaseModel):
    differences_observed: str                    # FIRST — ADR-004 reason-then-score
    same_character: bool
    attributes_present: list[str] = []
    style_match: bool = False
    anatomy_intact: bool = True
    failure_reasons: list[FailureReason] = []    # LAST — the closed 7 (ADR-028)
```

Field order mirrors `VlmVerdict` exactly, then appends. `providers._assert_field_order` enforces
it on the wire; mapping to `VlmVerdict` is a field-subset copy. `FailureReason` is imported from
`contracts/` — it has one home (ADR-028) and this node must not restate it.

### Effect boundary

One module-level helper per node (MASTER_SPEC §6 "The node test seam"). The Storage downloads live
**inside** it, same shape as `char_bible.mint_reference` and `generate_scene.generate_and_store`.

```python
def judge_attempt(image_path: str, subjects: list[tuple[str, str]]) -> list[SceneVerdict]:
    """(character name, reference path) → one SceneVerdict each, in subject order.

    Returns [] for empty subjects AND for any judge/Storage failure — both mean *unchecked*,
    and the node treats them identically, so distinguishing them here would buy nothing.
    """
```

Images are passed as base64 data URIs, never signed URLs (CC-4), ordered `[reference, scene]` with
the prompt naming which is which. This inherits `char_bible._data_uri`'s recorded body-size risk
(~1.9 MB per encoded 1024² PNG, and this call sends two) — if OpenRouter rejects the body on the
first real call, the fix is a shared signed-URL helper in `app/db.py`, a deliberate change for both
nodes at once, not a hotfix here.

### Happy path

1. Select the first `Scene` whose `final_image_ref is None` (ADR-024 — no cursor). None → `{}`.
2. Take `scene.attempts[-1]`. No attempts → log and return `{}`. Unreachable in the linear flow
   (`generate_scene` either appended one or raised), so this is a guard, not a path.
3. Build subjects: each `char_id` in `characters_present` that resolves to a `Character` carrying a
   `canonical_ref_image`, as `(name, canonical_ref_image)`.
4. `judge_attempt(attempt.image_ref, subjects)`.
5. **Fold, worst-wins** (`[]` → skip to 6 with `vlm_verdict=None`):
   - `same_character`, `anatomy_intact`, `style_match` → `all(...)`
   - `attributes_present`, `failure_reasons` → union, deduped; `failure_reasons` emitted in
     `FailureReason` **declaration order**, which is the order `correct_prompt` iterates
   - `differences_observed` → `"\n".join(f"{name}: {v.differences_observed}")`
6. `passed = same_character and anatomy_intact` (`False` when unchecked).
7. Partial-return the scene with the last attempt updated and
   `final_image_ref = attempt.image_ref`.

**The judge scores against the reference, not the description.** A `Character` whose
`ref_verdict.matches_description is False` is judged against anyway. ADR-028 deliberately ships the
best-of reference and `generate_scene` conditions every scene on it; consistency means *matches the
reference this image was drawn from*. Judging against anything else would fail every scene of a
book whose reference happened to be off-spec — punishing the scenes for the reference's fault.

### The pass rule

`same_character and anatomy_intact`. These are the two failures a child notices: it is the wrong
character, or it has three arms. `style_match` is recorded, folded, and available to
`regeneration-controller`'s ranking, but does **not** gate — ADR-007 puts style on the reference,
and `correct_prompt`'s `wrong_style` clause only re-appends the fragment the prompt already
carries, so a retry spent on style is close to a pure resample. Consequence, stated rather than
hidden: a genuinely off-style page can ship.

### Edge cases

| Case | Behavior |
|---|---|
| **No `characters_present`, or none carry a reference** | `judge_attempt` returns `[]` → unchecked, finalized, logged. This is exactly `generate_scene`'s `text_to_image` branch; there is no reference to judge identity against. |
| **`char_id` present but absent from `state.characters`** | Skipped, logged. Same posture as `generate_scene` and `build_prompt` — this node may not extend the roster. |
| **A `judge` call raises after ADR-025 retries** | Unchecked, finalized, `WARNING` with `exc_info`. `char_bible`'s deliberate asymmetry: the artifact exists and is paid for, only the *check* failed. Never a job failure. |
| **Storage download of the scene or a reference raises** | Same as above. Failing a job over a check would violate ADR-010's shippable-page rule for a reason unrelated to the page. |
| **The attempt fails the gate** | Finalized anyway **today** — with no `regenerate` node, ADR-010's best-of degenerates to the single attempt, which is still a real image and still better than a placeholder. `regeneration-controller` inserts the branch ahead of finalization. |
| **Two attempts already exist** | Cannot occur yet. ADR-028's lexicographic best-of ranking (`same_character` → `anatomy_intact` → `style_match`) is **not** built here — the backlog assigns the best-of *rule* to `regeneration-controller`, which is also the only thing that can produce a second attempt. |
| **A reference with a failing `ref_verdict`** | Judged against normally (above). |

### ⚠️ The anatomy correction gap

`FailureReason` is frozen permanently at 7 and ADR-028 explicitly excluded anatomy from it —
anatomy is a property of the rendering, not of identity. So an **anatomy-only** failure gates the
attempt while producing `failure_reasons == []`, `correct_prompt` appends no clause, and the
resulting retry is a pure resample — precisely what ADR-010 rejects as "not refinement."

This is recorded, not solved. Inventing an 8th enum value here would reopen a closed-set decision
that Objective 4's F1 is computed over. Handed to `regeneration-controller` (§8).

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-5 Observability** — one line per scene: `scene_id`, subject count, `checked|unchecked`,
      `same_character`, `anatomy_intact`, `style_match`, `failure_reasons`, `passed`. A wrong
      character in the finished book traces to a specific scene, a specific attempt, and the
      verdict that let it through.
- [x] **CC-10 Checkpointing / resumability** — no effects beyond state, so a re-executed super-step
      re-judges and re-finalizes to the same result at the cost of one judge call. Because the node
      finalizes, a resume never re-enters `generate_scene` for an already-paid scene.
- [ ] **CC-3 Cost control** — *partial.* No image spend, so `IMAGE_BUDGET` is untouched. But judge
      calls are **uncounted**: `Cost` has `image_count`, `regen_count`, `usd_estimate` and no judge
      counter, so this node's ≤2 calls per scene and `char_bible`'s ≤3 per reference are both
      invisible. Pre-existing gap, widened here, not closed — a `Cost` field is a `contracts/`
      change and belongs in one deliberate pass, not smuggled into a node build.
- [ ] **CC-4 Security** — *partial.* Durable Storage paths are read and persisted, never signed
      URLs. But a child's generated scene and character reference are sent as base64 to OpenRouter.
      Same posture as `char_bible`; noted, not closed.
- [ ] **CC-9 Failure states** — this node deliberately produces no failure state: every path
      finalizes. The unchecked case is a `WARNING`, invisible to the child. Correct for a quality
      signal (ADR-004: the judge is a signal, not an oracle), and the reason it is unticked rather
      than N/A is that nothing surfaces "this page was never verified" to a teacher.
- [ ] **CC-7 Reproducibility (seed)** — **not satisfied.** No seed is passed and none is available;
      inherited from `image-generator`, blocked on Probe 2 (`PHASE_05_RESULTS.md`), which does not
      gate Phase 1.
- CC-1 (moderation ordering — the output-image gate is `moderation-stack`'s, Phase 2), CC-2 (PII —
  `input_gate`'s, upstream), CC-6, CC-8: N/A.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

**Helper (`judge_attempt`, `providers.judge` + Supabase client mocked):**
- One `judge` call per subject, each with `[reference, scene]` in that order and its own reference.
- Empty subjects → `[]`, with no Storage download and no `judge` call.
- A raising `judge` → `[]`, no propagation.
- A raising Storage download → `[]`, no propagation.

**Node (`consistency_check`, helper patched — the node seam):**
- Two subjects, one failing → folded booleans are `False`; `attributes_present` and
  `failure_reasons` are unioned and deduped; `differences_observed` contains both names.
- `failure_reasons` is emitted in `FailureReason` declaration order regardless of subject order.
- `passed` is `True` only when `same_character and anatomy_intact`; a `style_match is False`
  verdict still passes.
- `[]` from the helper → `vlm_verdict is None`, `failure_reasons == []`, `passed is False`, and
  `final_image_ref` **is still set**.
- Only `attempts[-1]` is mutated; a pre-existing earlier attempt is returned byte-identical.
- `final_image_ref == attempts[-1].image_ref`.
- `{}` when every scene is finalized, and when the selected scene has no attempts.
- A `char_id` absent from `state.characters` is skipped without raising.
- A `Character` whose `ref_verdict.matches_description is False` still contributes a subject.

**Router (`route_next_scene`, pure — no mocks):**
- Unfinalized scene remains → `"generate_scene"`.
- All finalized → `"compose"`. Empty `scenes[]` → `"compose"`.

**Regression (existing files):**
- `test_generate_scene_node.py`: `generate_scene` no longer writes `final_image_ref` — the
  assertion is inverted, not deleted, so the ownership transfer is pinned.
- `graph.py`: a two-scene run reaches `compose` with both scenes finalized and two attempts total.
  This is the ADR-024 loop-termination test and the reason the router is worth a test at all.

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

The verdicts this node writes are the **predictions** side of Objective 4. The human labels come
from `annotation-surface`, whose annotators see only the image pair — never a model prediction
(that spec §2, §4) — and `judge-finetune`'s `build_dataset.py` joins the two on `pair_id` to
measure agreement. This node must not assume the annotation path reads its verdicts; it does not.

**One rule this spec imposes on that join:** an attempt with `vlm_verdict is None` has **no
prediction**, not a negative one. It must be dropped from the agreement denominator rather than
scored as a disagreement, and likewise excluded from any pipeline pass-rate. Counting unchecked
attempts as failures would report the judge's *unavailability* as the pipeline's inconsistency.
Invariant 4 is the machine-readable form of that rule.

No separate instrument is added here.

## 8. Linked decisions & open questions

**Depends on:** ADR-003 (consistency pass/fail is a real branch point — this spec builds the loop
edge and defers the pass/fail branch to `regeneration-controller`) · ADR-004 (VLM-as-judge,
reason-then-score field order, each character judged separately, ≤2 references) · ADR-010 (best-of,
never a broken page) · ADR-023 D-F (node-local sub-schema) · ADR-024 (partial return, pure routers,
loop position from `final_image_ref is None`, loop invariant) · ADR-025 (the check failing is not a
provider failure) · ADR-028 (`anatomy_intact`, `FailureReason` frozen at 7, a failing `ref_verdict`
still ships its reference).

**Hands off — named here, owned elsewhere:**
- **`route_after_check`, the `regenerate` node, ADR-010's one corrected retry, `correct_prompt`
  wiring, and ADR-028's lexicographic best-of ranking** → **`regeneration-controller`**. It
  re-points this node's `add_conditional_edges` registration in the same change.
- **The anatomy correction gap** (⚠️ §4) → **`regeneration-controller`**. An anatomy-only failure
  currently yields no correction clause, making its retry a resample.
- **Output-image moderation (CC-1)** → **`moderation-stack`** (Phase 2).
- **A judge-call counter on `Cost` (CC-3)** → **unowned.** A `contracts/` change covering this node
  and `char_bible` together; flagged rather than absorbed.
- **`recursion_limit`** (ADR-024) → **unowned.** It belongs to `run_job.py`'s invocation, not to a
  node, and ADR-025 Decision 4 already ties it to `IMAGE_BUDGET`'s source number.

**Open:**
- ⚠️ **Two base64 images per call is untested against OpenRouter's body limit.** `char_bible` sends
  one and has not yet run for real either. If it rejects, both nodes need the signed-URL helper at
  once (§4).
- **Judge latency is now on the critical path per scene**, ≤2 calls × 15 scenes. Unmeasured. It
  cannot fail the job (every path finalizes), so this is a latency risk, not a correctness one.
- **The pass rule is a judgement, not a measurement.** `same_character and anatomy_intact` is
  argued from ADR-007 and `correct_prompt`'s mechanics, not from data — no eval has compared gate
  rules. Revisit if the Objective 4 corpus shows `style_match` failures correlate with expert
  rejection (Objective 3).

## 9. Definition of done

Per AGENTS.md *Definition of Done*. This module is done when **all** of the following hold:

1. `backend/pipeline/consistency_check.py` implements §4: `SceneVerdict`, `judge_attempt`, the
   judge prompt, the worst-wins fold, the pass rule, and the finalizing partial return. The
   `# ponytail: stub` comment is removed — this spec is the change it was waiting for.
2. `backend/pipeline/generate_scene.py` no longer writes `final_image_ref`, and its
   `# ponytail: provisional` comment is removed.
3. `backend/pipeline/graph.py` replaces the `char_bible → generate_scene` and
   `consistency_check → compose` edges with two `add_conditional_edges` registrations of
   `route_next_scene`, plus the direct `generate_scene → consistency_check` edge (unchanged).
4. Every §6 assertion exists and passes, in `backend/tests/test_consistency_check_node.py` and the
   named existing files.
5. Backend verify is green and its output is **shown, not claimed**:
   `uv run ruff check . && uv run pytest` from `backend/`.
6. **Status line above flips to `built`** with the commit range (MASTER_SPEC §7).
7. **The finding-change grep is run** and every hit fixed in the same change. Known surface:
   - `docs/specs/image-generator.md` — §2 Writes, §3 "Provisional `final_image_ref`", §8 hand-off,
     §9 item 2 and the *Not done* clause: the hand-off has been taken.
   - `docs/product/DECISION_BACKLOG.md` — tick `consistency-checker`, move *"Recommended next
     session"* to `regeneration-controller`.
   - `docs/WORKFLOW.md` §"Right now".
   - `AGENTS.md` *Validation Notes* **and** *Project Context* — the "Built today" graph line still
     says "linear, **zero conditional edges**" and lists `consistency_check` as a pass-through stub.

**Not done** if: `backend/contracts/` is modified; `FailureReason` gains a value; `route_after_check`
or a `regenerate` node is built; `generate_scene` still writes `final_image_ref`; a judge or Storage
failure raises out of the node; `passed` is `True` when `vlm_verdict is None`; one judge call is
sent for two characters; an earlier `Attempt` is rewritten; or the `regeneration-controller`
hand-offs (the retry branch, the best-of ranking, the anatomy gap) are silently absorbed.
