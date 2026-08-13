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
     Unlike `generate_scene` this node never raises — see §4. Finalization is now conditional on
     `passed or verdict is None or len(attempts) >= 2` — a checked failure with one attempt is left
     unfinalized so `route_after_check` can send it to `regenerate`.
  2. `final_image_ref` is written by **this node only**. `generate_scene` stops writing it (§3).
     Unchanged and still true after `regeneration-controller` — `regenerate` deliberately does not
     write it.
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

**`route_after_check` is now built** — see `regeneration-controller` §3. It wraps `route_next_scene`:
an unfinalized scene with attempts routes to `regenerate`; everything else falls through to
`route_next_scene`. The `consistency_check` registration is re-pointed to `route_after_check` in the
same change, with a plain `add_edge("regenerate", "consistency_check")` completing the retry loop.

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
    subjects_unique: bool = True                 # §4.4 — asked after anatomy, before text
    text_free: bool = True                       # lettering-suppression §4.1 — asked after uniqueness, BEFORE failure_reasons
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
   - `same_character`, `anatomy_intact`, `style_match`, `subjects_unique`, `text_free` → `all(...)`
   - `attributes_present`, `failure_reasons` → union, deduped; `failure_reasons` emitted in
     `FailureReason` **declaration order**, which is the order `correct_prompt` iterates
   - `differences_observed` → `"\n".join(f"{name}: {v.differences_observed}")`
6. `passed = same_character and anatomy_intact and text_free and not (GATING_REASONS & reasons)`
   (`False` when unchecked).
7. Partial-return the scene with the last attempt updated and
   `final_image_ref = attempt.image_ref`.

**The judge scores against the reference, not the description.** A `Character` whose
`ref_verdict.matches_description is False` is judged against anyway. ADR-028 deliberately ships the
best-of reference and `generate_scene` conditions every scene on it; consistency means *matches the
reference this image was drawn from*. Judging against anything else would fail every scene of a
book whose reference happened to be off-spec — punishing the scenes for the reference's fault.

### The pass rule

`same_character and anatomy_intact and text_free and not (GATING_REASONS & failure_reasons)`. These
are the four failures a child notices: wrong character, three arms, a word on the page they cannot
read and the app never speaks (CC-6), or a character whose colour and build changed between pages.
`style_match` and `subjects_unique` are recorded, folded, and available to `regeneration-controller`'s
ranking, but do **not** gate (ADR-007, §4.4).

#### `GATING_REASONS` — the identity-attribute gate (2026-08-13)

```python
GATING_REASONS = frozenset({FailureReason.wrong_colour, FailureReason.wrong_body_feature})
```

Prod job `483056e0` shipped `s3` with `['wrong_colour', 'wrong_clothing']` and `s4` with
`['wrong_colour', 'wrong_body_feature', 'wrong_clothing', 'wrong_style']`, **both `passed=True`**.
The judge had already found the dragon off-model and the gate had no term for it, because a green
dragon is still `same_character=True`. The one retry ADR-010 pays for was never spent on the
failure the judge had in hand.

Colour and body features are what a child uses to recognise a **non-human** character across pages.
The dragon has no face to fail `different_face` on and no clothes to fail `wrong_clothing` on, so
before this change the entire seven-value `FailureReason` set was inert for it.

**Excluded, deliberately.** `wrong_clothing` and `wrong_style` both have a live false-positive
story — a sash reading differently under gouache lighting, and `style_match` reading `False` by
construction (issue #24, below) — and the cost of a false gate is a paid redraw.
`wrong_species` and `different_face` need no entry: `same_character` already covers both.

**Not a contract change.** `FailureReason` stays frozen at 7 (ADR-028). This is a *subset of the
existing closed set*, read at the gate, so the F1 measurement Objective 4 computes over that set is
untouched.

**Bounded.** The gate buys the same single retry ADR-010 already caps at one — `finalize` is
`passed or verdict is None or len(attempts) >= 2`. Worst case per book is one extra draw per scene,
already inside `IMAGE_BUDGET` (45; prod job `483056e0` spent 13 on 9 pages).

**Fallback, pre-registered:** if the redraw rate on these two reasons proves unacceptable, demote
them to rank-only — the shape `subjects_unique` and `style_match` already sit in. The `_rank` term
stays either way.

**Why gate on `text_free` here when `subjects_unique` did not (§4.3):** the duplicate rate was unmeasured,
whereas lettering on door/page draws is known non-zero, the artifact is unambiguous, and latency cost is
bounded by ADR-010's existing one-retry cap. **Fallback note (`lettering-suppression.md` §4.6.2):** if the
false-positive rate on texture is bad, demote `text_free` to rank-only — the shape `subjects_unique` already
sits in.

⚠️ **The style question must name what to ignore** (issue #24, 2026-08-11). Asked unscoped —
"whether the art style matches the reference" — the field read `False` on **7 of 7** scenes of prod
job `b9506307`, because the two images being compared differ by construction: the reference is one
character on a plain neutral background (`char_bible.REFERENCE_PROMPT`) and the page is a full
illustration with scenery and a crop. The judge's own `differences_observed` answered about
hair-strand detail, freckle rendering and background — never about drawing technique — so the field
was measuring "are these two images rendered alike", which no scene page can satisfy, and a
constant signal is also a useless third term in `_rank`. `JUDGE_PROMPT` now scopes it to linework,
shading and colouring technique and names background, composition, pose, crop and expression as
ignorable. Numbers and controls: `PHASE_05_RESULTS.md` Probe 3 follow-up.

### Edge cases

| Case | Behavior |
|---|---|
| **No `characters_present`, or none carry a reference** | `judge_attempt` returns `[]` → unchecked, finalized, logged as `unchecked=no_subjects`. This is exactly `generate_scene`'s `text_to_image` branch; there is no reference to judge identity against, so a retry here would be the uncorrected resample ADR-010 rejects. The *upstream* fix is `scene-segmentation` §4.6 name recovery; the residual case is ADR-004's ≤2 reference cap leaving a third character unreferenced. |
| **`char_id` present but absent from `state.characters`** | Skipped, logged. Same posture as `generate_scene` and `build_prompt` — this node may not extend the roster. |
| **A `judge` call raises after ADR-025 retries** | Unchecked, finalized, `WARNING` with `exc_info`. `char_bible`'s deliberate asymmetry: the artifact exists and is paid for, only the *check* failed. Never a job failure. |
| **Storage download of the scene or a reference raises** | Same as above. Failing a job over a check would violate ADR-010's shippable-page rule for a reason unrelated to the page. |
| **The attempt fails the gate** | Left unfinalized (`final_image_ref` stays `None`). `route_after_check` routes to `regenerate`, which draws once with a corrected prompt. `consistency_check` then runs again and finalizes by best-of (see below). |
| **Two attempts already exist** | Finalized by best-of: `max(reversed(updated), key=_rank)` where `_rank` is ADR-028's lexicographic signal (`same_character` → `anatomy_intact` → `text_free` → `attributes_ok` → `subjects_unique` → `style_match`, unchecked sorts last). Iterating in reverse ensures a genuine tie goes to attempt 2 (the corrected prompt is the better prior — ADR-010 calls it refinement, not resampling). |
| **A reference with a failing `ref_verdict`** | Judged against normally (above). |

### The anatomy correction gap — closed

`FailureReason` is frozen permanently at 7 and ADR-028 explicitly excluded anatomy from it —
anatomy is a property of the rendering, not of identity. An **anatomy-only** failure gates the
attempt while producing `failure_reasons == []`. Without a fix, `correct_prompt` would append no
clause and the retry would be a pure resample.

This gap is **closed by `ANATOMY_CLAUSE`** in `regeneration-controller` §4: `correct_prompt` now
accepts `anatomy_intact: bool = True` and appends a fixed anatomy clause when `False`. No 8th enum
value was invented; `FailureReason` stays frozen at 7.

### Uniqueness — measured, not gated (`scene-setting-and-subject-binding.md` §4.4)

`JUDGE_PROMPT` asks, after the anatomy question and before the text question and failure reasons,
whether the named character is drawn **exactly once**. The wording scopes to the **character**, not the noun — "the
stars" in "she looked up at the stars" names no character and stays drawable — and its position in
the prompt matches `subjects_unique`'s position in `SceneVerdict`, because
`providers._assert_field_order` rejects a provider that answers out of order.

- Folded worst-wins: `subjects_unique = all(v.subjects_unique for v in verdicts)`.
- Ranked: `_rank` is
  `(1, same_character, anatomy_intact, text_free, attributes_ok, subjects_unique, style_match)`;
  the unchecked tuple is `(0, 0, 0, 0, 0, 0, 0)`. `attributes_ok` is
  `not (GATING_REASONS & failure_reasons)` — read off `Attempt.failure_reasons`, since `vlm_verdict`
  carries no reason list. It sits **last of the gating axes and ahead of the two record-only ones**.
  Without it the corrected redraw the gate now buys would be invisible to best-of: two attempts
  identical on every boolean tie, and the tie rule keeps attempt 2 whether or not it fixed the colour.
- **Not gated.** `passed` does not read `subjects_unique`. Gating it means more
  regenerations and issue #26 is open and already critical — cost is not the constraint, latency
  is. Precedent for record-and-rank-without-gating is `style_match`, in this same file. Gating is a
  follow-up decision, blocked on a measured duplicate rate and on #26 being closed.
- CC-5: the per-scene log line carries `subjects_unique`, `text_free`, and `judge_prompt_version` (now version 3).

`JUDGE_PROMPT_VERSION` is a module constant (set to **3** after adding the text question), bumped on every wording change. It is deliberately
**not** a persisted `Attempt` field — that would be a third contract change for a problem logs
already make traceable. The underlying gap (this prompt is unversioned in a way `char_bible`'s is
not) deserves its own issue.

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-5 Observability** — one line per scene: `scene_id`, subject count,
      `checked` | `unchecked=no_subjects` | `unchecked=judge_failed`,
      `same_character`, `anatomy_intact`, `style_match`, `failure_reasons`, `passed`. A wrong
      character in the finished book traces to a specific scene, a specific attempt, and the
      verdict that let it through.
- [x] **CC-10 Checkpointing / resumability** — no effects beyond state, so a re-executed super-step
      re-judges and re-finalizes to the same result at the cost of one judge call. Because the node
      finalizes, a resume never re-enters `generate_scene` for an already-paid scene.
- [ ] **CC-3 Cost control** — *partial.* No image spend, so `IMAGE_BUDGET` is untouched. But judge
      calls are **uncounted**: `Cost` has `image_count`, `regen_count`, `usd_estimate` and no judge
      counter, so this node's ≤2 calls per scene and `char_bible`'s ≤3 per reference are both
      invisible. Pre-existing gap, **widened by `regeneration-controller`** — a retried scene costs
      up to 4 judge calls, not 2. Still a `contracts/` change, still unowned.
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
- `passed` is `True` only when `same_character and anatomy_intact and text_free` and no
  `GATING_REASONS` reason is present; a `style_match is False` verdict still passes.
- **Gate (2026-08-13):** `wrong_colour` alone fails and leaves the scene unfinalized (so it buys
  the retry); `wrong_body_feature` alone fails; `wrong_clothing` alone passes; `wrong_style` alone
  passes; a gating reason contributed by **either** subject fails the whole scene; a second attempt
  that still carries one is finalized anyway (ADR-010's cap).
- **Rank (2026-08-13):** an on-colour attempt outranks an off-colour one when every boolean ties;
  `attributes_ok` sits below `text_free` and above `subjects_unique`.
- **CC-5:** a zero-subject page logs `unchecked=no_subjects` and an outage logs
  `unchecked=judge_failed`. **Both** branches are asserted in one test, each also asserting the
  other token is absent — one token alone would pass even if the two had not been separated.
- `[]` from the helper → `vlm_verdict is None`, `failure_reasons == []`, `passed is False`, and
  `final_image_ref` **is still set** (the `verdict is None` term of the three-term finalize rule).
- Only `attempts[-1]` is mutated; a pre-existing earlier attempt is returned byte-identical.
- `final_image_ref == updated[best].image_ref` — on a single attempt this is `attempts[-1].image_ref`
  as before; on two attempts it is the winner of `max(reversed(updated), key=_rank)`.
- `{}` when every scene is finalized, and when the selected scene has no attempts.
- A `char_id` absent from `state.characters` is skipped without raising.
- A `Character` whose `ref_verdict.matches_description is False` still contributes a subject.
- `subjects_unique=False` on any per-character verdict folds to `False`.
- `subjects_unique=False` alone does **not** flip `passed`.
- `_rank` prefers a unique attempt over a duplicated one when the higher keys tie.
- Unchecked ranks below every checked attempt with the widened 5-tuple.


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
  wiring, ADR-028's lexicographic best-of ranking, the anatomy correction gap, and
  `recursion_limit`** → **discharged by `regeneration-controller`** (2026-08-02).
- **Output-image moderation (CC-1)** → **`moderation-stack`** (Phase 2).
- **A judge-call counter on `Cost` (CC-3)** → **unowned.** A `contracts/` change covering this node,
  `char_bible`, and `consistency_check` together; widened by `regeneration-controller`, flagged
  rather than absorbed.

**Open:**
- ⚠️ **Two base64 images per call is untested against OpenRouter's body limit.** `char_bible` sends
  one and has not yet run for real either. If it rejects, both nodes need the signed-URL helper at
  once (§4).
- **Judge latency is now on the critical path per scene**, ≤2 calls × 15 scenes. Unmeasured. It
  cannot fail the job (every path finalizes), so this is a latency risk, not a correctness one.
- **The pass rule is a judgement, not a measurement.** Every term of it — including the
  2026-08-13 `GATING_REASONS` addition — is argued from ADR-007, `correct_prompt`'s mechanics and
  one prod job's logs, not from data. No eval has compared gate rules, and the redraw rate the new
  term will cost is **unmeasured**. Revisit if the Objective 4 corpus shows `style_match` failures correlate with expert
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

**Not done** if: `backend/contracts/` is modified; `FailureReason` gains a value;
`generate_scene` still writes `final_image_ref`; a judge or Storage failure raises out of the node;
`passed` is `True` when `vlm_verdict is None`; one judge call is sent for two characters; an earlier
`Attempt` is rewritten. *(The `regeneration-controller` hand-offs — retry branch, best-of ranking,
anatomy gap, `recursion_limit` — are discharged. CC-3 judge counter remains unowned.)*
