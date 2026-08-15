# Feature Spec — setting-consistency

**Status:** approved · **Phase:** 2 · **Owner nodes:** `backend/pipeline/analyze.py`,
`backend/pipeline/consistency_check.py`  
**Derived from:** `pipeline-consistency-docket.md` S4 · **Rationale:** ADR-002, ADR-010,
ADR-023, ADR-025, ADR-034, ADR-035; docket BC-1…BC-12

> Give every recurring location one frozen textual identity, then use the existing scene-constraint
> judge and retry path when a generated page contradicts its permanent features. This spec adds no
> location image, node, provider call, contract field, retry allowance, or budget term.

## 1. Purpose

Make the same story location recognizable across pages without creating a second class of reference
image. `analyze` freezes one permanent textual canon per location; the existing scene prompt uses it,
and the existing scene-constraint verdict gates concrete violations of it.

This is targeted product hardening, not a population-level consistency study. BC-1 forbids a
corpus-level rate, and this spec makes no visual-quality claim without a named reproduced defect.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `input.redacted_text`; `locations[]`; `scenes[].location_id`; the current attempt's
  `prompt` and `image_ref`.
- **Writes:** `locations[].description` through the existing `analyze` partial return;
  `scenes[].attempts[].scene_contradictions`, `passed`, and `final_image_ref` through the existing
  `consistency_check` partial return.
- **No contract change:** persisted `Location.description` stays `Optional[str]` so old checkpoints
  deserialize. The stricter requirement belongs only to `analyze.ExtractedLocation`, the transient
  LLM-boundary type.

**Invariants**

1. `Location.name + Location.description` is the sole persisted location canon.
2. Every location extracted by new production code has a non-empty canonical description.
3. The canon preserves story-stated facts and fills missing detail once with neutral, child-safe,
   permanent visual features.
4. Weather, lighting, time of day, action, damage, and other temporary state are not canon.
5. A scene may vary temporary conditions without changing the persisted canon.
6. A concrete contradiction of a permanent setting feature gates through the existing
   `scene_contradictions` path.
7. No location image, provider call, retry allowance, contract field, location cap, or budget term
   is added.

## 3. Position in the system map

`input_gate → analyze → segment → … → generate_scene → consistency_check`

- `analyze` creates the frozen textual location canon during its existing structured extraction
  call.
- `segment` keeps the location behavior already specified by
  `scene-setting-and-subject-binding.md`: a null location inherits the previous scene; a null first
  scene takes `locations[0]` when one exists; a story with no locations leaves all location ids
  null.
- `build_prompt` keeps the S3-approved order: `Visual direction → Setting → excerpt → style`.
  ADR-035's transient `filtered_location` projection still filters the description but never the
  name. The later excerpt is authoritative for temporary conditions.
- `consistency_check` keeps its one existing scene-constraint judge call and one existing
  consistency pass/fail edge. No graph edge or node is added.
- `regenerate` needs no setting-specific branch: it already appends concrete
  `scene_contradictions` to the corrected prompt, then appends the composition-preservation clause.

## 4. Behavior & edge cases

### 4.1 Frozen textual canon

`ExtractedLocation.description` changes from `str | None` to a required, non-blank `str`. The
transient boundary validator rejects blank or whitespace-only values; the persisted contract stays
permissive for checkpoint compatibility.

`analyze.EXTRACTION_PROMPT` requires the model to:

1. copy every stated permanent fact without alteration;
2. fill missing detail once with neutral, child-safe features that make the place visually
   recognizable; and
3. exclude weather, lighting, time of day, action, damage, and other temporary state.

The description remains one free-text field. S4 adds no structured location axes or provenance
metadata: the existing field is sufficient for the only two consumers, `build_prompt` and the
scene-constraint judge.

Locations remain uncapped. A textual location adds no image or judge call, so the existing
`analyze` comment remains true: locations are not a CC-3 image-spend lever.

### 4.2 Legitimate change across scenes

The canon describes stable identity such as layout, landmarks, materials, and recurring colours.
The excerpt may state a temporary variation such as night, rain, storm damage, or changed lighting.
That later, scene-specific statement controls the page without mutating `Location.description`.

The prompt order does not change. `Visual direction` continues to own action, movement, pose,
crop, expression, and viewpoint under S3; the excerpt owns story-stated transient setting changes.

### 4.3 Setting gate

`SCENE_CONSTRAINT_PROMPT` explicitly tells the existing scene-constraint judge:

- when a `Setting:` line exists, check its name and permanent description against the page;
- report only concrete violations of stated permanent features as contradictions; and
- do not report weather, lighting, time, damage, or other temporary differences when the later
  excerpt supports them.

The result uses the existing `SceneConstraintVerdict.contradictions` list. No location-specific
boolean or persisted field is added. A non-empty list already makes `composition_clean=False`,
sets `passed=False`, and leaves the first attempt unfinalized so the existing consistency branch
routes once to `regenerate`.

`correct_prompt` already appends the contradictions. The existing S3 composition-preservation
clause stays last, so a setting correction may not rewrite the requested action or viewpoint.
After the second failed attempt, ADR-010's existing composition-first best-of rule prefers fewer
total scene contradictions and finalizes the page.

Because the judged instruction changes, `SCENE_CONSTRAINT_PROMPT_VERSION` increments from **2 to
3**. Per BC-6, results from v2 and v3 are never pooled. `JUDGE_PROMPT_VERSION` and
`settings.vlm_judge_model` do not change.

### 4.4 Failure and compatibility cases

| Case | Behavior |
|---|---|
| Story names no locations | No `Setting:` line and no setting requirement; existing behavior. |
| Old checkpoint has `description=None` | It still deserializes; `build_prompt` emits the location name only. |
| ADR-035 filters the whole description | The name survives and becomes the complete setting requirement. |
| New extraction omits, nulls, or blanks a description | Strict boundary validation fails before any image purchase; ADR-025 handles the provider failure. |
| Scene omits a location | Existing carry-forward policy applies; S4 does not reopen it. |
| Excerpt legitimately changes temporary conditions | The judge is instructed not to call the supported difference a contradiction. |
| Permanent setting mismatch on attempt 1 | Existing contradiction gate buys a corrected redraw. |
| Permanent setting mismatch on attempt 2 | Buys the second corrected redraw (ADR-037; was best-of finalization when S4 was written). |
| Permanent setting mismatch on attempt 3 | Existing best-of finalizes the attempt with fewer total contradictions. |
| Scene-constraint judge fails | Existing unchecked semantics apply: no speculative setting retry and no false pass. |

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-2 PII redaction** — `analyze` continues to read `input.redacted_text`; the frozen canon
  is derived only after the input gate.
- [x] **CC-3 Cost control** — no new image-call or judge-call site and no larger retry allowance.
  Locations stay uncapped because the artifact is text, so S5 receives no S4 budget term. A newly
  detected setting contradiction can make the already-budgeted scene redraw occur more often; that
  typical-case increase is unmeasured, while the existing per-book ceiling is unchanged.
- [x] **CC-5 Observability** — the existing per-scene log records `scene_contradictions`, pass,
  finalization, best-of, and `scene_constraint_prompt_version`; the stored attempt prompt contains
  the exact `Setting:` constraint judged.
- [x] **CC-10 Checkpointing / resumability** — no contract field changes; old nullable descriptions
  remain readable, while newly extracted locations are strict only at the transient boundary.
- [ ] **CC-7 Reproducibility** — unchanged and unsatisfied: the existing text and judge calls expose
  no seed. Prompt version 3 prevents silent pooling but does not make calls deterministic.
- [ ] CC-1, CC-4, CC-6, CC-8, CC-9 — untouched. S4 changes no moderation edge, asset access,
  frontend surface, or job-failure taxonomy.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Every provider call is mocked. Tests assert the contract and control flow, never whether a model
draws a recognizable place.

### `analyze`

1. `ExtractedLocation` rejects a missing, null, blank, or whitespace-only description.
2. `EXTRACTION_PROMPT` requires preservation of stated facts, one-time neutral permanent detail,
   and exclusion of temporary conditions.
3. A valid extracted description reaches `Location.description` unchanged.
4. The persisted `Location` contract still accepts `description=None`.
5. Locations remain uncapped and no new call is made.

### `consistency_check`

6. `SCENE_CONSTRAINT_PROMPT_VERSION == 3` and the prompt distinguishes permanent requirements from
   excerpt-supported temporary conditions.
7. A setting contradiction in the existing composition verdict makes the first attempt fail and
   remain unfinalized, buying the existing redraw.
8. An empty contradiction list leaves an otherwise clean attempt passed and finalized.
9. The final setting failure finalizes through the existing best-of rule; the attempt with fewer
   total contradictions wins. *(The retry cap that decides which attempt is final belongs to
   ADR-037 / `spend-and-retry-economics.md`, not to S4 — S4 only requires that the gate fires and
   that best-of decides the last one. That cap moved 2 → 3 on 2026-08-15.)*
10. A scene-constraint judge outage buys no retry and is not recorded as a pass.
11. `judge_attempt` still makes exactly one composition call per scene attempt; no
    location-specific call exists.

### Existing behavior guards

12. Prompt order remains `Visual direction → Setting → excerpt → style`.
13. Null-location carry-forward and leading-location seeding remain unchanged.
14. `filtered_location` can reduce a description to name-only but never filters the name.

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

None for S4. No paid provider or fal call is required, and this spec makes no claim that visual
setting consistency improved. Under BC-1, a later check may report pass/fail only against a named,
reproduced setting defect; it may not report a population-level consistency rate.

## 8. Linked decisions & residual risks

**Depends on:** ADR-002 (strict structured output); ADR-010 (one corrected retry and best-of);
ADR-023 (transient boundary schema stays beside its node; no Story Memory change); ADR-025 (provider
failure semantics); ADR-034 (contradiction-list-derived gates); ADR-035 (transient style filtering);
docket BC-1, BC-4, BC-6, and S3's frozen prompt composition.

**No new ADR:** S4 adds no artifact class, graph edge, contract field, model, provider, retry, or
budget policy. `docs/product/DECISION_BACKLOG.md` contains no setting-consistency row to close.

**Residual risks:**

- Text conformance is weaker than direct image-to-image place comparison.
- The judge checks each page against the canon, not one page against another.
- A hallucinated but permanent detail can become canon because S2's chosen freeze-once posture is
  inherited without provenance metadata.
- A false setting contradiction can spend the existing one redraw.
- Strict extraction turns a provider schema violation into an early failed job. This is deliberate:
  failing before image spend is safer than persisting an unusable canon.

## 9. Definition of done

1. The owner approves this written spec.
2. The docket records the spec path and the owner confirms S4's binding-constraint extract.
3. Implementation changes only the behavior named in §§4.1 and 4.3; every changed line traces to
   this spec.
4. All §6 deterministic assertions exist and pass with model calls mocked.
5. `story-analyzer.md` and `consistency-checker.md` are updated in the implementation change;
   any other affected spec found by repository grep is updated in the same change.
6. Backend lint and tests pass using the exact AGENTS.md commands.
7. No visual-quality claim is made without the Tier B evidence BC-1 requires.
