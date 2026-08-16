# Feature Spec — pose, viewpoint, and scene composition

**Status:** built · **Phase:** 2  
**Owners:** `backend/pipeline/prompt_optimizer.py`, `backend/pipeline/consistency_check.py`,
`backend/pipeline/regenerate.py`  
**Derived from:** `pipeline-consistency-docket.md` S3 · `visual-continuity.md` §4  
**Rationale:** ADR-004, ADR-010, ADR-023, ADR-028, ADR-034; docket BC-1…BC-12

> Preserve the story's requested composition when a canonical reference shows only one view.
> References define appearance; `Scene.visual_direction` defines action, pose, crop, expression,
> movement, and viewpoint. This spec changes prompt semantics and failed-attempt selection, not the
> pipeline shape.

## 1. Purpose

A scene may correctly show a character from behind, in profile, foreshortened, or partly occluded
even though its canonical reference uses the default slight-angle view. The generator and identity
judge must not treat that viewpoint difference as permission to override the story or as proof that
the character changed.

S3 makes story fidelity the selection priority while retaining the existing identity gate, one
corrected retry, and best-of fallback. It adds no pose catalogue, view detector, reference image,
model call, or budget term.

## 2. Scope and chosen mechanism

### In

1. Keep the existing required free-text `Scene.visual_direction` as the sole pose/viewpoint source.
2. Make the existing identity-judge prompt explicitly viewpoint- and natural-occlusion-tolerant.
3. Preserve the requested composition on every corrected retry.
4. Rank scene-constraint fidelity before identity when choosing between two failed attempts.
5. Version the changed identity prompt and keep measurements separated by version.

### Out

- Character appearance and invented attributes — S2 / `visual-continuity.md` own them.
- Setting consistency — S4.
- Draw, page, recursion, or reference-count economics — S5.
- Additional front/side/rear canonical references — rejected for S3; ADR-004 keeps the ≤2 cap.
- A structured pose taxonomy, pose parser, view classifier, dedicated direction checker, new node,
  provider call, or model swap.
- Reworking `REFERENCE_PROMPT` or `REFERENCE_NEGATIVE`; their slight-angle framing is settled.
- Claiming that the incumbent judge reliably detects movement direction.

## 3. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `Scene.visual_direction`, `Scene.prompt`, `Scene.attempts`,
  `Attempt.vlm_verdict`, `Attempt.failure_reasons`, and `Attempt.scene_contradictions`.
- **Writes:** no new fields. Existing `Attempt` verdict fields and `Scene.final_image_ref` continue
  to be written by `consistency_check` exactly as before.
- **Schema:** unchanged. `StoryMemory`, `Scene`, `Attempt`, `VlmVerdict`, and the seven-value
  `FailureReason` enum gain nothing.
- **Invariants:**
  1. Every newly segmented scene has one non-blank `visual_direction` before a paid draw.
  2. References define appearance only; `visual_direction` defines scene composition.
  3. A natural viewpoint difference or occlusion is not, by itself, an identity, anatomy, or
     attribute failure.
  4. A retry may correct a defect but may not replace the requested composition.
  5. `passed` still requires every applicable identity and scene-constraint gate to be clean.
  6. At most one corrected scene retry occurs; the second attempt finalizes through best-of.

## 4. Position in the system

No node or edge changes:

```text
segment → generate_scene → consistency_check
                            ├─ pass/finalize → output_mod
                            └─ concrete failure → regenerate → consistency_check → finalize
```

- `segment` remains the sole author of `Scene.visual_direction`.
- `build_prompt` remains a pure helper used by `generate_scene`.
- `correct_prompt` remains a pure helper used by `regenerate`.
- `consistency_check` retains both existing judge calls and the existing conditional edge.
- `graph.py`, `providers.py`, `app/config.py`, and `backend/contracts/` are untouched.

## 5. Behavior

### 5.1 Composition authority

`Scene.visual_direction` is authored during segmentation (from the transient structured direction rendered into a single string) and persisted as a single required string field. `build_prompt` emits prompt blocks in the visual-only contract order (`SCENE_PROMPT_VERSION = 2`, ADR-040):

1. reference roll and `REFERENCE_CLAUSE`;
2. text-only character descriptions (appearance axes only);
3. cast-count and non-human guards;
4. visible objects;
5. `Visual direction: <visual_direction>`;
6. setting (`Setting: <name> - <description>`);
7. style (`style_fragment`).

The existing reference clause remains the governing rule: reference images define appearance, not
pose, crop, expression, or viewing angle; `Visual direction` controls those properties. The
setting-line and visual-direction-before-setting ordering are unchanged. Per ADR-040, narrative text
excerpts are omitted from positive scene prompts.

### 5.2 Viewpoint-tolerant identity judgment

`consistency_check.JUDGE_PROMPT_VERSION` increments from **3 to 4**. Version 4 must state, before
the structured verdict questions, that:

- rear, profile, foreshortened, and partially occluded views can depict the same character;
- pose, crop, expression, and viewing angle are not identity differences by themselves;
- the comparison uses visible evidence only;
- a feature naturally hidden by the requested viewpoint is not a missing body part, visible
  contradiction, or reason to emit `wrong_body_feature`, `different_face`, or `character_absent`;
- a visible substitution, visible attribute contradiction, or genuinely malformed, merged,
  missing, or duplicated anatomy still fails normally.

The wire schema and ADR-004 order remain byte-for-byte unchanged: free-text reasoning first, then
the existing booleans/lists in schema order, with `failure_reasons` last. The model remains
`settings.vlm_judge_model`; BC-4 forbids a swap during this docket.

Counts from prompt v3 and v4 are never pooled (BC-6, ADR-034). Objective 4's preregistration already
requires recording the shipped `JUDGE_PROMPT_VERSION` at evaluation time; no held-out evaluation
has occurred, so this version boundary is recorded rather than silently crossing series.

### 5.3 Composition-preserving correction

`correct_prompt` keeps all existing defect clauses and its no-op rule. When at least one correction
is appended, it appends one fixed preservation clause **last**:

> Preserve the Visual direction exactly: do not change the requested action, movement direction,
> pose, crop, expression, or viewing angle.

This applies to generic identity correction, boolean-driven correction, structured failure reasons,
and scene-constraint contradictions. Centralizing it once prevents a later correction path from
silently becoming composition-destructive. A call with no correction still returns the original
prompt byte-identically.

The base prompt still carries the original `Visual direction`; no second pose value is passed to
`correct_prompt`, stored on `Attempt`, or reconstructed during regeneration.

### 5.4 Composition-first best-of

The pass predicate and retry decision do not change. Only `_rank`'s final-attempt preference changes.
Its lexicographic order becomes:

1. any checked signal over a fully unchecked attempt;
2. no scene contradictions;
3. fewer scene contradictions;
4. `same_character`;
5. `anatomy_intact`;
6. `text_free`;
7. no identity-bearing `GATING_REASONS`;
8. `subjects_unique`;
9. `style_match`.

Therefore a composition-clean attempt beats an identity-clean attempt that contradicts the story.
When both attempts are equally clean or equally contradicted on composition, the existing identity
axes break the tie. Known-clean composition beats unavailable composition. Between unavailable
composition and a confirmed contradiction, the existing behavior remains: unavailable outranks
known-bad.

This ordering is a product priority, not a claim that the scene judge is accurate. If the scene
judge misses the same direction error on both attempts, identity may still decide the tie.

### 5.5 Failure behavior and edge cases

| Case | Behavior |
|---|---|
| Blank or missing `visual_direction` | Existing pre-draw `ValueError`; no fal spend. |
| Rear/profile view hides a face or limb | Judge compares visible evidence and does not call natural occlusion a defect. |
| View changes but a visible character is genuinely substituted | Existing identity gate fails and buys the one corrected retry. |
| First attempt is composition-clean but identity-failed; retry is identity-clean but composition-wrong | First attempt wins best-of. |
| Both attempts have composition contradictions | Fewer contradictions wins; identity breaks an equal-count tie. |
| Composition judge unavailable on one attempt | It cannot count as clean; existing unknown-vs-known-bad ordering remains. |
| Identity judge unavailable | Existing unchecked semantics; no invented verdict and no fatal job failure. |
| Both judges unavailable | Fully unchecked and lowest-ranked, as today. |
| Direction judge returns clean on a visually wrong direction | Accepted instrument limitation; S3 does not add a checker or claim detection. |
| No correction is required | `correct_prompt` returns the original prompt byte-identically. |

## 6. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-3 Cost control** — no new draw, judge call, retry, reference, or budget term.
- [x] **CC-5 Observability** — existing logs retain `visual_direction`, judge prompt versions,
  verdict axes, contradictions, and selected attempt. Version 4 creates an explicit series boundary.
- [x] **CC-7 Reproducibility** — prompt v4 is a module constant; counts never cross prompt versions.
- [x] **CC-10 Checkpointing / resumability** — no state shape or graph change; old checkpoints
  retain their existing `visual_direction` and attempts.
- [ ] **CC-1, CC-2, CC-4, CC-6, CC-8, CC-9** — N/A. Moderation, PII, storage/security, UI, and
  failure-screen behavior are untouched.

## 7. Deterministic tests (Tier A)

All provider calls remain mocked. Tests assert policy, never generated-image quality.

### `backend/tests/test_consistency_check_node.py`

1. `JUDGE_PROMPT_VERSION == 4`.
2. The identity prompt states viewpoint tolerance and natural-occlusion semantics before its
   verdict questions while preserving ADR-004 field order.
3. A composition-clean/identity-failed attempt outranks a composition-failed/identity-clean one.
4. Fewer scene contradictions wins; identity is the next tie-breaker.
5. Fully unchecked remains below any checked attempt.
6. Known-clean, unavailable, and known-bad composition retain the order declared in §5.4.

### `backend/tests/test_regenerate_node.py` and `test_prompt_optimizer.py`

7. Generic identity, boolean, reason-based, and scene-contradiction corrections append the
   composition-preservation clause last.
8. A no-op correction remains byte-identical.
9. Existing tests continue proving `visual_direction` is required and occupies its current block
   position; no prompt block is reordered.

### Verification commands

From `backend/`:

```bash
uv run ruff check .
uv run pytest
```

From `frontend/`:

```bash
pnpm lint
pnpm test
```

## 8. Eval / quality checks (Tier B)

None for S3. The owner chose deterministic verification only.

No provider or fal call is part of this spec's definition of done. S3 may claim that the prompt,
retry, and ranking policy changed as specified; it may **not** claim that pose/viewpoint quality or
direction-detection accuracy improved. BC-1 forbids a population-level rate, and no targeted rerun
is required here.

Known evidence remains unchanged: the incumbent scene judge missed the observed movement-direction
defect 4/4 across prompt versions 1 and 2. That limitation is reported, not reworded away.

## 9. Linked decisions and residual risks

- **ADR-004:** reason-then-score and ≤2 canonical references remain frozen.
- **ADR-010:** one corrected retry and best-of fallback remain frozen.
- **ADR-023:** no Story Memory contract change.
- **ADR-028:** `MAX_DRAWS = 3` and the seven-value `FailureReason` enum remain frozen.
- **ADR-034 / BC-6:** prompt wording changes require a version bump; series do not cross versions.
- **BC-4:** the incumbent prompted `gemma-3-27b-it` remains fixed for this docket.
- **Objective 4 preregistration:** evaluation records whichever shipped prompt version exists at
  evaluation time; this spec does not edit endpoints, thresholds, datasets, or the judge model.

Residual risks:

1. Prompt v4 is not validated against real images; viewpoint tolerance may reduce true identity
   failures as well as false ones.
2. Composition-first ranking is only as good as the scene judge's contradictions. Its known
   movement-direction blindness can still let an unfaithful retry win an apparent tie.
3. No machine-readable pose/view field exists. That is deliberate; add one only if free-text
   `visual_direction` becomes demonstrably uninspectable.
4. A multi-view bible may outperform prompt semantics, but belongs to a future accepted ADR plus S5
   economics, not this session.

## 10. Blast radius and definition of done

Implementation is limited to the three existing owner modules and their existing tests. Known live
documentation assertions that must be updated with the same behavior are:

- `docs/specs/prompt-optimizer.md`
- `docs/specs/consistency-checker.md`
- `docs/specs/regeneration-controller.md`
- `docs/specs/visual-continuity.md` §4.7
- `docs/specs/story-memory-contract.md`
- `docs/specs/lettering-suppression.md`
- `docs/specs/scene-setting-and-subject-binding.md`
- `AGENTS.md` validation notes

The last four are documentation-only updates; no additional code module changes. This list is a
known-hit floor, not a substitute for the required repository grep. Before completion, grep for the
old prompt version and identity-first rank order, update every live assertion, run §7's commands,
and delete the completed disposable implementation plan. No Tier-B result is required or claimed.
