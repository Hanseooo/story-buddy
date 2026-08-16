# Feature Spec — spend-and-retry-economics

**Status:** approved · **Phase:** 2 · **Owner surfaces:** `backend/app/config.py`,
`backend/pipeline/segment.py`, `backend/pipeline/consistency_check.py`,
`backend/pipeline/output_mod.py`, `frontend/app/s/[profileId]/write/page.tsx`

**Derived from:** `pipeline-consistency-docket.md` S5 · **Rationale:** proposed ADR-037;
ADR-010, ADR-012, ADR-024, ADR-025, ADR-028; docket BC-1…BC-18

> Trade book length for one more corrected scene attempt while making the paid-image breaker
> truthful. The product accepts at most 300 words and 10 scenes; each scene may use three
> consistency attempts and one output-moderation redraw; every structurally permitted draw is
> funded inside a 55-image ceiling.

## 1. Purpose

Give a concretely failed scene one additional corrected attempt while reducing the graph's
structurally possible worst-case paid-image spend from 60 to 55. The trade is a shorter input and
page ceiling, plus correction of an existing accounting hole: `output_mod` can buy a softened
redraw but currently discards its `paid` result, does not increment `cost.image_count`, and checks
no breaker.

This is a product-policy change, not evidence that a third attempt improves visual consistency.
BC-1 still forbids a population-level consistency claim, and no paid run is part of this spec.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `scenes[].attempts`, `scenes[].final_image_ref`, `scenes[].moderation_status`,
  `cost.image_count`, and the existing story input.
- **Writes:** `scenes[].attempts` through the existing `regenerate` and `output_mod` paths;
  `scenes[].final_image_ref` through `consistency_check` and `output_mod`; `cost.image_count`
  through the existing `Cost` block.
- **No contract change:** retry allowance remains derived from `len(scene.attempts)`. No cursor,
  retry-budget field, judge-call counter, or schema-version bump is added.

**Invariants**

1. A scene has at most three consistency-checked attempts: the initial draw plus two corrected
   retries.
2. A pass finalizes immediately. An unchecked attempt also finalizes immediately and never buys a
   blind redraw.
3. A concrete failure on attempt 1 or 2 remains unfinalized and routes to `regenerate`; a concrete
   failure on attempt 3 finalizes the best-ranked attempt.
4. Attempt 3 corrects from the immutable clean `Scene.prompt` base plus only the latest (attempt 2)
   checked attempt's verdict (amended by visual-prompt-reliability), avoiding prompt accumulation
   while keeping the 55-image budget and cost arithmetic unchanged.
5. Output moderation retains exactly one softened redraw. Its paid draw is counted, breaker-bound,
   and never bypasses moderation.
6. `IMAGE_BUDGET` funds every structurally permitted paid draw; legal retry paths do not compete
   for an intentionally undersized shared pool.
7. `MAX_STORY_WORDS = 300`, `MAX_SCENES = 10`, `IMAGE_BUDGET = 55`, and
   `RECURSION_LIMIT = 87` are one coupled policy.

## 3. Position in the system map

The graph shape is unchanged:

```text
input_gate → analyze → segment → char_bible → char_ref_mod → reveal
  → generate_scene → consistency_check
      ├─ concrete failure, attempts < 3 → regenerate → consistency_check
      └─ pass, unchecked, or attempts = 3 → output_mod → next scene / compose
```

- `segment` keeps the existing structured extraction and deterministic merge. Both the prompt and
  repair use `MAX_SCENES`; no story-length function or second pagination policy is added.
- `consistency_check` keeps the existing pass predicate, `_rank`, and conditional edge. Only the
  finalization threshold and attempt-denominator log move from 2 to 3.
- `regenerate` keeps its node shape and uses the immutable clean `Scene.prompt` base (amended by
  visual-prompt-reliability). A second visit naturally writes attempt 3 using only attempt 2's
  verdict.
- `output_mod` keeps its in-node one-redraw safety loop. The redraw adds an image, not a graph
  super-step.
- No node, graph edge, router label, provider, model, or reference slot is added.

## 4. Behavior & edge cases

### 4.1 Input and page ceilings

`MAX_STORY_WORDS` moves from 800 to **300** in both existing enforcement surfaces:

- The frontend disables submission above 300 words and shows its existing `Too long!` state.
- The backend remains authoritative. A direct, stale, or bypassed request above 300 words is
  clamped by the existing paragraph → sentence → hard-cut policy, with the retains-half floor and
  `truncated=true` unchanged.
- No summarization is introduced. The frontend requires the child to shorten visible over-cap text
  rather than silently discarding the ending.

`MAX_SCENES` moves from 15 to **10**. The segmentation prompt interpolates the shared constant
instead of carrying a stale literal, and deterministic repair merges to the same ceiling.
`MIN_SCENES = 3` and `MIN_SCENE_WORDS = 12` are unchanged.

The 300-word cap does not mathematically prove that a story has at most ten visual beats. The
deterministic merge is still the actual ceiling; 300 words only limits how dense those merged pages
can become. At the joint maximum, the mean is 30 caption words per scene.

### 4.2 Third consistency attempt

The finalization rule becomes conceptually:

```python
finalize = passed or not concrete_failure or len(scene.attempts) >= 3
```

The existing `concrete_failure` definition remains authoritative. Therefore:

| Result | Behavior |
|---|---|
| Attempt 1 passes or is unchecked | Finalize immediately; no retry. |
| Attempt 1 concretely fails | Generate corrected attempt 2. |
| Attempt 2 passes or is unchecked | Finalize immediately. |
| Attempt 2 concretely fails | Generate corrected attempt 3. |
| Attempt 3 passes | Finalize attempt 3. |
| Attempt 3 concretely fails | Finalize best-of across all three attempts. |

There is no stop-on-non-improvement rule. One redraw that fails to improve `_rank` does not prove
that the final bounded corrected attempt is useless. Passing and unchecked results remain the only
early exits.

Best-of keeps the existing lexicographic `_rank`. `max(reversed(...), key=_rank)` already handles
three attempts and continues to make the newest corrected attempt win an exact tie. No scalar score
or new failure reason is added.

`regenerate` uses the immutable `Scene.prompt` as the clean base for both retries (amended by
visual-prompt-reliability). Attempt 3 therefore contains the clean base prompt plus only the
correction derived from attempt 2's verdict, avoiding prompt accumulation and contradictory
instruction growth while exact duplicate contradictions are deduplicated in first-seen order.

### 4.3 Paid-image accounting and formulas

The current scene coefficient omits a real paid path. Per scene, the structural maximum is:

```text
1 initial draw
+ 2 consistency redraws
+ 1 output-moderation redraw
= 4 paid images per scene
```

The fixed image prelude remains **15**:

```text
6  canonical-reference draws (2 references × MAX_DRAWS 3)
+3 child reveal taps
+6 one reference-moderation redraw cycle (2 references × MAX_DRAWS 3)
=15 images
```

Therefore:

```python
IMAGE_BUDGET = MAX_SCENES * 4 + 15   # 10 * 4 + 15 = 55
```

`output_mod` checks the breaker before calling `generate_and_store`, retains the returned `paid`
boolean, and returns `cost.image_count + 1` only when fal was actually called. A Storage reuse adds
the attempt but not the paid count, matching `generate_scene` and `regenerate`.

The graph-depth coefficient becomes **7**:

```text
generate_scene → consistency_check
→ regenerate → consistency_check
→ regenerate → consistency_check
→ output_mod
= 7 super-steps per scene
```

The fixed super-step prelude remains **17**, so:

```python
RECURSION_LIMIT = MAX_SCENES * 7 + SUPER_STEP_PRELUDE   # 10 * 7 + 17 = 87
```

The 15-image and 17-super-step preludes remain deliberately unequal because they count different
units. `output_mod`'s internal redraw changes the image coefficient but adds no super-step.

### 4.4 Failure and compatibility cases

| Case | Behavior |
|---|---|
| Frontend text exceeds 300 words | Submission disabled; child edits the visible story. |
| Direct request exceeds 300 words | Existing boundary-aware backend clamp; stored text is the clamped text. |
| Segmentation extracts more than 10 scenes | Existing deterministic smallest-neighbour merge reduces to 10. |
| Attempt 2 is worse than attempt 1 | Attempt 3 is still allowed after a concrete failure; best-of retains the strongest result. |
| Attempt 2 is unchecked | Finalize immediately; no blind attempt 3. |
| All three attempts concretely fail | Finalize best-of; never a placeholder. |
| Image breaker is reached | Raise before another provider call; job fails with no partial book. |
| Output moderation redraw is reused from Storage | `paid=False`; `image_count` does not increase. |
| Output moderation redraw passes | Replace `final_image_ref`, persist the attempt, mark moderation passed, and count the paid draw. |
| Output moderation redraw fails | Preserve the flagged attempt for audit, clear `final_image_ref`, mark failed, and fail the whole job. |

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-1 Moderation ordering** — unchanged. Every finalized scene still passes `output_mod`
  before the next scene or `compose`; the newly counted softened redraw is re-moderated before use.
- [x] **CC-3 Cost control** — the breaker now counts all paid fal paths and structurally funds the
  full legal maximum of 55 images. Judge and classifier calls remain absent from `Cost`; they do not
  weaken the paid-image breaker, and adding a contract counter without a consumer is YAGNI.
- [x] **CC-5 Observability** — consistency logs use `attempt=n/3`; existing per-regeneration logs
  expose each corrected prompt; `output_mod` logs whether its redraw was paid or reused and the
  resulting image count.
- [x] **CC-6 Accessibility** — the existing live word counter and textual over-cap state remain;
  only the ceiling changes.
- [x] **CC-9 Failure states** — a breaker trip retains ADR-025's whole-job failure posture; raw
  errors remain dev-only.
- [x] **CC-10 Checkpointing / resumability** — retry allowance remains derived from persisted
  attempts; deterministic per-attempt paths extend naturally through `-3.png`; Storage reuse is
  not charged twice.
- [ ] **CC-7 Reproducibility** — unchanged and still limited by unverified provider seed behavior.
- [ ] CC-2, CC-4, CC-8 — untouched. Redaction order, signed-URL/RLS policy, and design language do
  not change.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Every provider and model call is mocked. Tests assert arithmetic and control flow, never image
quality.

### Length and segmentation

1. Frontend word count accepts 300, rejects 301, disables submission over cap, and keeps the
   textual `Too long!` state.
2. Backend `clamp_story` preserves exactly 300 words and clamps 301+ using the existing boundary
   and retains-half rules.
3. `MAX_SCENES == 10`; the segmentation prompt names the same ceiling; deterministic repair emits
   at most ten scenes.
4. `MIN_SCENES` and `MIN_SCENE_WORDS` remain unchanged.

### Consistency and regeneration

5. A concrete failure on attempt 1 remains unfinalized and routes to `regenerate`.
6. A concrete failure on attempt 2 remains unfinalized and routes to `regenerate` again.
7. Pass or unchecked on attempts 1 or 2 finalizes immediately.
8. Attempt 3 finalizes whether it passes or concretely fails.
9. Three-way best-of follows `_rank`; an exact tie selects attempt 3.
10. Attempt 3 corrects from `Scene.prompt` plus attempt 2's verdict only and uses the `-3.png` path.
11. A graph run where every scene fails all three checks terminates with three attempts per scene;
    no fourth attempt is reachable.

### Cost and graph bounds

12. `IMAGE_BUDGET == MAX_SCENES * 4 + 15 == 55`.
13. `RECURSION_LIMIT == MAX_SCENES * 7 + SUPER_STEP_PRELUDE == 87`.
14. The image and super-step preludes remain independently decomposed and unequal.
15. `output_mod` raises before its redraw when the breaker is reached and never calls the helper.
16. A paid moderation redraw increments `image_count`; a reused redraw does not.
17. Both passing and still-flagged moderation redraws persist the paid count.
18. Existing reference, reveal, and reference-moderation retry caps remain unchanged.

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

No paid run is required by this spec, and no visual-quality claim is made. Deterministic tests can
prove that attempt 3 is reachable, bounded, and correctly accounted; they cannot prove it improves
an image.

If separately authorized, the smallest informative paid check is the exact previously observed
story, reported only as whether attempt 3 repaired that named defect. It cannot support a
population-level rate, comparisons across prompt versions, or a research result (BC-1, BC-6).

## 8. Linked decisions and residual risks

**Requires proposed ADR-037:** this policy amends ADR-010 from one corrected retry to two, amends
ADR-012 from the 500–800 range to 300 words, and corrects ADR-025 D4 so its paid-image breaker
includes `output_mod`'s existing redraw. Implementation is blocked until ADR-037 is accepted.

**Depends on:** ADR-024 (derived loop position, pure router, recursion backstop); ADR-028 (closed
failure taxonomy and lexicographic best-of); ADR-029 (three reveal taps); BC-1, BC-4, and BC-6.

**Residual risks:**

- Attempt 3's quality benefit is unmeasured.
- Ten scenes may merge distinct visual beats into denser pages; the 300-word cap limits but does
  not eliminate that risk.
- Cumulative corrections may repeat emphasis. The maximum is two correction layers; deduplicate
  only if a real prompt or output demonstrates harm.
- Judge and classifier calls remain uncounted by `Cost`. Close that only when a concrete budget,
  latency, or reporting consumer exists.
- Existing documentation contains stale `*2 + 9`, 39-, 45-, 15-scene, 800-word, and `attempt=2/2`
  assertions. The implementation change must grep and update every live assertion under the
  repository's finding-change rule; frozen historical prose remains visible and marked superseded.

## 9. Definition of done

1. The owner reviews and approves this written spec and ADR-037.
2. The docket records the spec path and confirmed S5 binding constraints, then marks S5 `DONE`.
3. Implementation changes only the behavior named in §4; no graph, contract, model, provider, or
   dependency change is introduced.
4. All §6 deterministic assertions exist and pass with every model/provider call mocked.
5. Relevant live specs and status surfaces are updated in the implementation change after a
   repo-wide grep for every changed number and formula.
6. Frontend and backend pre-merge verification commands pass and their output is reported.
7. No visual-quality claim is made without separately authorized Tier B evidence.
