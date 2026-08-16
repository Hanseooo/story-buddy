# Feature Spec — visual-prompt reliability

**Status:** built (deterministic implementation complete; Tier-B product trace unverified pending paid runs) · **Phase:** 2 · **Owner surfaces:** `backend/pipeline/analyze.py`,
`segment.py`, `prompt_optimizer.py`, `generate_scene.py`, `regenerate.py`
**Derived from:** `pipeline-consistency-docket.md` S3–S5 · MASTER_SPEC §§2, 3, 5, 6
**Rationale:** ADR-004, ADR-010, ADR-013, ADR-023, ADR-024, ADR-025, ADR-028, ADR-037,
ADR-039, ADR-040 · production job `9517f79c-9f9d-46c6-958a-2213c054316c` (2026-08-16)

> **Declared deviation from “one spec = one module.”** This spec owns one artifact class: the
> positive prompt sent to the scene image model. The bad instruction can enter through entity
> extraction or scene segmentation, is assembled by `prompt_optimizer`, stored by `generate_scene`,
> and carried into paid retries by `regenerate`. Splitting those edits into independent specs would
> leave invalid intermediate states in which a clean builder still receives contradictory source data, or clean
> source data is re-contaminated by retry accumulation.

> **Decision resolved:** ADR-040 accepts D-M and removes `CharacterDescription.notes` from newly
> assembled scene prompts. This spec is no longer architecturally blocked, but remains a draft until
> owner review; no implementation plan or code change proceeds before that approval.

---

## 1. Purpose and evidence

Make each paid scene draw receive one short, coherent, visual-only description of one drawable
moment. Preserve the child's full post-redaction words as the printed caption while preventing
dialogue, narrative roles, duplicate actor/object identities, competing viewpoints, and prior
attempt corrections from accumulating in the image prompt.

The motivating five-page comic run completed with `image_count=19`, `regen_count=10`, and
`pages=5 passed=1 failing=4`. Its fal prompts showed all of the following in production:

1. quoted dialogue in both `visual_direction` and the verbatim excerpt, followed by generated
   speech bubbles despite the shared negative prompt;
2. one actor represented twice — character `Leo` and object `the robot (Leo)` — which produced the
   persistent relation `the robot (Leo) is held by Andres`;
3. multiple actions and viewpoints packed into one scene direction;
4. correction prompts growing from approximately 1,862 to 2,704 to 3,902 characters because
   attempt 3 appended its correction to attempt 2's already-corrected prompt;
5. judge contradiction prose restated verbatim to the generator, including tautologies such as
   `Andres is holding Leo, rather than holding Leo`.

This is a targeted product reproduction, not a population-level quality result. The three-story
Tier-B check in §7 measures whether the fix generalizes far enough to retain; it does not create a
capstone efficacy claim.

### 1.1 Success criteria

For every newly generated scene:

- Fal receives one visual authority, rendered from structured scene direction plus typed
  character/object/location data.
- No `Scene.text_excerpt`, quoted dialogue, or narrative `CharacterDescription.notes` reaches the
  positive scene prompt.
- The direction describes one key drawable moment and one camera setup while permitting front,
  profile, rear, overhead, foreshortened, and partially occluded views when the story calls for them.
- An explicit actor alias cannot survive simultaneously in `characters[]` and `objects[]`.
- Every retry starts from the immutable original `Scene.prompt` and adds only the most recent
  checked attempt's corrections.
- Caption fidelity, graph shape, model/provider choice, attempt count, and paid-image budget do not
  change.

### 1.2 Out of scope

- A fourth scene attempt or any change to `MAX_SCENE_ATTEMPTS` (ADR-037).
- A ranking change, scalar quality score, aesthetic judge, or new `FailureReason` (ADR-028).
- Treating `different_face` as an automatic failure. Rear/profile/occluded views must not be pushed
  toward front-facing reference poses.
- Replacing the pre-registered runtime judge model or changing Objective 4 labels.
- Changing `Scene.caption`, rewriting the child's prose, or deleting dialogue from the book.
- A language-specific speech-verb blacklist. It would miss Taglish and future languages while
  falsely rejecting ordinary prose.
- The output-moderation replacement gap. D-N owns the dedicated ADR for checking a safe replacement
  once without buying another redraw.
- New nodes, edges, provider call sites, dependencies, persisted fields, or schema-version bumps.
  An invalid structured answer may activate `structured_text`'s existing single re-ask; the valid
  path adds no call.

---

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `input.redacted_text`; `characters[]`; `objects[]`; `locations[]`; `timeline[]`;
  `Scene.text_excerpt`, `caption`, `characters_present`, `objects_present`, `location_id`,
  `visual_direction`, `prompt`, and `attempts[]`; `style.prompt_fragment`.
- **Writes:** the existing `characters[]`, `objects[]`, and `scenes[]` outputs from `analyze` and
  `segment`; `generate_scene` continues writing the original builder result to `Scene.prompt` and
  `Attempt.prompt`; `regenerate` continues appending one `Attempt`.
- **Does not add or change:** any Pydantic contract field, reducer, id convention, enum, model id,
  provider seam, graph edge, or database schema.

### Invariants

1. `Scene.text_excerpt` remains a gap-free verbatim slice of redacted source text.
2. `Scene.caption == Scene.text_excerpt` remains byte-for-byte true (ADR-013).
3. `Scene.visual_direction` remains the sole persisted composition authority.
4. `Scene.prompt` is the immutable clean base prompt for all attempts in that scene.
5. `Attempt.prompt` records the exact prompt used for that attempt.
6. Attempt 1 uses `Scene.prompt`; attempts 2 and 3 each use `Scene.prompt + latest correction`, never
   another attempt's prompt.
7. Reference images define appearance only. They never force front-facing pose, reference crop,
   expression, or viewing angle onto a scene.
8. The structured segmentation result cannot persist a blank direction and exposes exactly one
   `key_action`, `viewpoint`, and `framing` field for a scene. A compound action inside the one
   string remains a model-adherence risk measured in §7; structure cannot prove semantic atomicity.
9. A named/personified actor and an inert object are mutually exclusive roster entries.
10. No paid image call occurs before the existing analyzer/segmenter structured boundaries validate.

Legacy checkpoints retain their already-persisted `Scene.prompt` and `Attempt.prompt`; this change
does not rewrite or redraw them on resume (CC-10).

---

## 3. Position in the system map

No graph change:

```text
input_gate → analyze → segment → char_bible → char_ref_mod → reveal
           → generate_scene → consistency_check ⇄ regenerate → output_mod
```

The prompt data flow becomes:

```text
redacted story
  ├─ analyze → mutually-exclusive character/object canon
  └─ segment → one structured drawable moment → Scene.visual_direction

Scene.visual_direction + typed canon + setting + style
  └─ build_prompt → Scene.prompt → attempt 1
                              └─ + latest verdict only → attempt 2 or 3

Scene.text_excerpt ─────────────────────────────────────→ printed caption only
```

`generate_scene` remains the only caller that creates the base scene prompt. `regenerate` remains
the only corrected-retry node. `consistency_check` and its composition-first `_rank` are unchanged.

---

## 4. Behavior and edge cases

### 4.1 Actor/object exclusivity at `analyze`

The extraction prompt continues using agency as the boundary:

- a subject that acts, decides, speaks, or is personified belongs in `characters[]`;
- an inert prop belongs in `objects[]`;
- the same entity must not appear in both, even when one name contains an explanatory alias.

The existing `StoryAnalysis` boundary normalizer widens only to **explicit aliases**:

1. drop an object whose case-insensitive name equals a character name;
2. strip the trailing parenthetical alias when it equals a character name after trimming whitespace
   and case-folding — `the robot (Leo)` becomes `the robot`;
3. drop the object if stripping leaves no name or leaves another character duplicate;
4. do not use fuzzy substring or species matching. `Leo's toy`, `Leo's robot kit`, and a generic
   inert `toy robot` remain valid objects.

This boundary normalization keeps the valid prop while ensuring the actor alias cannot reach
`segment`. Other structural schema failures still use `providers.structured_text`'s existing
single schema re-ask; no node-local retry is added.

**Known ceiling:** an implicit alias such as character `Leo` plus object `the robot`, with no name
link, cannot be proven identical deterministically. A semantic fuzzy matcher would create false
merges and is not justified by one reproduction. The Tier-B fixtures include one implicit-alias
story and record whether the extraction prompt alone handles it; a miss is evidence for a future
decision, not permission to guess in this build.

### 4.2 One structured drawable moment at `segment`

The node-local LLM boundary replaces its free-form `visual_direction: str` with a transient
structured value containing exactly:

- `key_action`: one visible action with its subject and target when applicable;
- `pose_expression`: visible pose/expression needed to communicate the moment, nullable;
- `viewpoint`: one camera direction relative to the subject/action;
- `framing`: one crop/shot scale.

These fields are node-local and are deterministically rendered into the existing contract string:

```text
<key_action> <pose_expression when present> Viewpoint: <viewpoint>. Framing: <framing>.
<current valid object-holder relations>
```

The extraction prompt must:

1. choose the single most important drawable moment covered by the scene range;
2. convert speech into visible action, gesture, expression, or reaction without reproducing the
   words — `Leo says “Hello!”` may become `Leo stands awake and raises one hand in greeting while
   Andres reacts with surprise`;
3. choose story-appropriate pose and viewpoint. Running away normally shows a rear or rear
   three-quarter view; it must not be rewritten as forward-facing merely to resemble a reference;
4. keep only details that can be seen in one still frame;
5. leave sequential or non-simultaneous actions to the verbatim caption rather than creating a
   montage, split panel, duplicate character, or impossible pose;
6. never request written words, quoted dialogue, speech bubbles, captions, labels, or readable
   signage.

The transient boundary rejects blank fields, newlines, and literal quote characters in its visual
fields. It deliberately does **not** maintain an English/Taglish list of speech verbs. Semantic
phrases such as `Ana explains` can still slip through a model-authored field; the shared Fal negative
prompt and the existing `text_free` judge remain defence in depth, while §7 measures the residual.

#### Coverage versus one moment

The image does not have to depict every sentence in a multi-sentence caption. “Important detail”
means any fact required to identify the selected moment correctly: participating visible subjects,
the action and target, current object holder, setting, and story-required pose/viewpoint. Facts from
earlier or later moments remain in the caption and are not forced into the same frame.

`characters_present`, `objects_present`, holder state, and `location_id` stay structured beside the
direction. Character appearance comes from typed description axes and canonical images, not from
the direction. This prevents the direction from becoming a second character bible.

#### Repair and merge behavior

`repair` and `merge_thin` may combine source ranges after the model returns them. Concatenating both
directions would recreate the defect this spec removes. When two extracted scenes merge:

- retain the later scene's structured drawable moment as the page image;
- retain the later scene's visible cast and visible objects so subjects belonging only to the
  discarded earlier moment are not summoned into the frame;
- retain ordered object events from both ranges, because an earlier acquire/release can determine
  the later moment's valid holder relation;
- use the later scene's explicit location, falling back to the earlier location only when the later
  one is null;
- let the combined verbatim caption retain both moments.

The later-moment rule is deterministic and favors the result/climax of a short sequence. It can
omit a visually stronger earlier beat; adding a second “choose the merged moment” LLM call is
rejected because it adds cost, latency, and another failure boundary for a defensive repair path.
The three-story check records any visibly poor merge choice.

### 4.3 Visual-only base prompt

`build_prompt` emits these blocks in this order:

1. numbered reference-image roll containing each referenced character's `name`, `species`,
   `colours`, `body_features`, and `clothing` only;
2. reference-use clause;
3. unreferenced visible characters using the same appearance-only projection;
4. whole-canvas subject count and non-human guard;
5. visible objects and stable physical descriptions;
6. the one `Visual direction` rendered by `segment`;
7. setting name and permanent description;
8. style fragment.

It does **not** emit:

- `Scene.text_excerpt` or `Scene.caption`;
- `CharacterDescription.notes`;
- a second action/viewpoint restatement;
- model-authored dialogue or correction history.

The function signature drops `text_excerpt`; the caller and deterministic tests change together.
No fallback re-adds it when the visual direction is sparse: a sparse/invalid direction fails at the
segment boundary before image spend.

ADR-040 resolves D-M and amends ADR-039 on this exact surface. The motivating prompt described Andres as
`The protagonist, a child who builds a robot`, which is narrative role/action rather than visual
identity and duplicates facts already owned by the selected moment. Visually meaningful facts must
live in the typed appearance axes, as ADR-039 requires for canonical references and ADR-040 now
requires for scene prompts.

### 4.4 Clean-base corrected retries

`regenerate` always sets:

```text
base_prompt = scene.prompt
corrected_prompt = correct_prompt(base_prompt, latest_attempt_verdict_only)
```

It never uses `last.prompt` as the base. The latest attempt contributes its current:

- structured `failure_reasons`;
- `same_character`, `anatomy_intact`, and `text_free` booleans;
- scene contradictions.

Earlier corrections are intentionally not carried. If a problem disappeared from the latest
attempt, repeating it is unnecessary; if it returned, the latest judge names it again. This avoids
free-text history aggregation and preserves the existing immutable `Scene.prompt` contract meaning.

`correct_prompt` continues appending at most one clause per current structured reason, the existing
boolean clauses, current scene contradictions, and one composition-preservation clause. Exact
duplicate current contradiction strings are deduplicated in first-seen order before rendering; no
semantic/fuzzy deduplication is attempted.

**Tradeoff:** a previously fixed issue may return when the latest judge misses it. Carrying all raw
history avoids forgetting but recreates contradictory growth. The three-story check compares
attempt trajectories and is the evidence gate for revisiting this choice.

### 4.5 Angle and identity behavior

This spec does not change the identity judge or `_rank`:

- natural rear, profile, foreshortened, cropped, and partially occluded views remain valid;
- a naturally hidden face/body feature is not a reason to force the character front-facing;
- a visible substitution, wrong visible attribute, or malformed anatomy still fails normally;
- `different_face` with `same_character=True` stays raw diagnostic evidence, not an automatic gate;
- composition-first best-of remains, so a story-correct running-away pose can beat a prettier but
  front-facing contradiction.

The Tier-B set deliberately contains multiple angles. Any future ranking change requires its own
evidence and ADR; it is not bundled into prompt cleanup.

### 4.6 Failure and edge-case table

| Case | Required behavior |
|---|---|
| Exact character/object duplicate | Boundary normalization drops the duplicate object. |
| `the robot (Leo)` plus character `Leo` | Boundary normalization keeps the object as `the robot`. |
| `Leo's toy` plus character `Leo` | Valid object; possession is not identity. |
| Implicit alias `Leo` / `the robot` | Prompt guidance only; logged Tier-B ceiling, no fuzzy merge. |
| Story contains direct dialogue | Caption preserves it; image prompt receives only visible action/reaction. |
| A sign's exact wording matters to the plot | Wording remains in caption; image may depict an unmarked sign only if the selected moment needs it. |
| Several sequential actions share one page | Later/key moment is illustrated; no montage or duplicate actor. |
| Two actions are genuinely simultaneous | One may be the key action and the other a pose/reaction, but not a second independent beat. |
| Running away / looking back | Rear or rear-three-quarter view is allowed and preferred over a contradictory front view. |
| Close-up hides a held object | The selected moment must choose framing that can show every required visible relation; otherwise choose a different key moment. |
| Scene has no characters | Valid; prompt uses objects, direction, setting, and style without subject-count guards. |
| Scene has no canonical references | Existing text-to-image path; same visual-only prompt. |
| Empty or malformed direction | Boundary re-ask once, then hard failure before Fal spend. |
| Direction contains literal quotes | Boundary validation failure and existing one re-ask. |
| Direction semantically says “speaks” without quotes | May pass; negative prompt + `text_free` gate cover it; Tier-B records residual leakage. |
| Merge combines different locations | Later selected moment owns the location; fall back to the earlier location only when the later one is null. |
| Latest judge is unavailable | Existing unchecked finalization; no regeneration and therefore no correction prompt. |
| Latest failure prose is tautological or malformed | Passed through once as today after exact deduplication; prompt-length logging exposes it. A semantic rewriter would be a new model call and is out of scope. |
| Attempt 3 fails | Existing best-of chooses among three attempts; no fourth draw. |
| Old checkpoint resumes | Reuses stored prompt/attempts; no silent prompt migration or redraw. |
| Output moderation replaces the winner | Existing behavior until D-N resolves; explicitly not claimed fixed by S1. |

---

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-2 PII redaction** — segmentation and captions continue reading `redacted_text`; no raw
  input is reintroduced into the image prompt.
- [x] **CC-3 Cost control** — no added call site, successful-path call, image call, or changed attempt
  cap. Alias normalization adds no provider call and occurs before Fal spend. `IMAGE_BUDGET=55`
  remains truthful.
- [x] **CC-5 Observability** — see §5.1.
- [x] **CC-7 Reproducibility** — no new seed behavior. Fal seed determinism remains an acknowledged
  unrun probe; the three-story check records prompts and attempt ids rather than claiming causal
  isolation.
- [x] **CC-10 Checkpointing/resumability** — immutable stored base prompt and per-attempt paths remain;
  legacy prompts are not rewritten.
- [ ] **CC-1 Moderation ordering** — unchanged. D-N, not this spec, owns consistency-checking a safe
  moderation replacement.
- [ ] **CC-4 Security** — no new asset, URL, table, or policy.
- [ ] **CC-6 Accessibility** — captions remain complete; narration is unaffected.
- [ ] **CC-8 Kid vs teacher design** — no UI.
- [ ] **CC-9 Failure states** — existing job failure semantics remain.

### 5.1 Observability

Existing logs gain only the fields needed to diagnose this feature:

- `segment`: selected `key_action`, `viewpoint`, `framing`, and whether the scene direction came from
  an unmerged result or retained-later merge;
- `generate_scene`: existing `prompt_len` plus one integer `scene_prompt_version`, bumped whenever
  the positive prompt's meaning or block order changes;
- `regenerate`: `base=scene.prompt`, latest source attempt number, exact correction count,
  deduplicated contradiction count, and final `prompt_len`.

Do not log the child's full excerpt, full prompt, signed URLs, or image bytes. Existing Fal provider
records and stored `Attempt.prompt` remain the authorized detailed provenance.

---

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

All model/provider/image calls are mocked. Tests assert prompt structure and state transitions, not
generated-image quality.

### 6.1 `analyze`

1. Exact same name in both rosters is dropped from `objects[]`.
2. Character `Leo` plus object `the robot (Leo)` yields object `the robot`.
3. Matching is case-insensitive and trims parenthetical whitespace.
4. `Leo's toy`, `Leo's robot kit`, and inert `toy robot` remain valid objects.
5. Alias normalization adds no node retry, provider re-ask, or image call.

### 6.2 `segment`

1. The provider receives explicit one-moment, visual-only, speech-to-visible-action instructions.
2. The transient result requires nonblank `key_action`, `viewpoint`, and `framing`.
3. Literal quote characters and line breaks in visual fields fail validation.
4. The renderer emits exactly one `Viewpoint:` and one `Framing:` marker.
5. Direct-dialogue source text remains byte-identical in `text_excerpt` and `caption`, while rendered
   `visual_direction` contains none of its quoted wording.
6. Character/object id mapping, holder state, ordinary location carry-forward, gap-free coverage,
   and deterministic scene ids remain unchanged.
7. Merging two ranges retains the later structured moment, cast, visible objects, and explicit
   location rather than concatenating/unioning two frames; ordered object events from both survive.
8. A running-away fixture preserves a rear/rear-three-quarter direction; no test requires a face to
   be front-facing.
9. Malformed structured output is rejected before any downstream image helper can run.

### 6.3 `prompt_optimizer` / `generate_scene`

1. `build_prompt` has no `text_excerpt` parameter.
2. The complete prompt contains references, appearance axes, guards, objects, one direction,
   setting, and style in the declared order.
3. The prompt contains neither the verbatim excerpt nor direct-dialogue wording.
4. Narrative `notes` are absent from referenced and unreferenced character descriptions (ADR-040).
5. Typed appearance axes remain present; removing notes cannot make species/colours/body/clothing
   disappear.
6. Reference numbering still matches `ref_paths` for initial, consistency-retry, and moderation
   paths.
7. Text-to-image scenes use the same visual-only layout without fake `Image N` labels.
8. `Scene.prompt` equals the exact attempt-1 prompt and remains unchanged thereafter.

### 6.4 `regenerate`

1. With two prior attempts, attempt 3 uses `scene.prompt`, not attempt 2's prompt, as its base.
2. Only attempt 2's verdict/reasons/contradictions drive attempt 3.
3. A correction present only in attempt 1 does not appear in attempt 3 unless attempt 2 reports it.
4. Exact duplicate current contradictions render once, preserving first-seen order.
5. No semantic/fuzzy contradiction rewriting occurs.
6. Identity, anatomy, lettering, style, and composition clauses still fire on their existing
   conditions.
7. Attempt count, cost increments, per-attempt Storage paths, and finalization ownership remain
   unchanged.

### 6.5 Graph regression

One mocked three-attempt scene proves:

- node/edge order is unchanged;
- attempts 2 and 3 both derive from the same stored base;
- each correction reads only the immediately preceding verdict;
- the graph terminates at three attempts;
- moderation still follows finalization;
- `cost.image_count` and `cost.regen_count` retain current arithmetic.

Full backend verification remains `uv run ruff check . && uv run pytest` from `backend/`.

---

## 7. Tier-B quality check — three targeted stories

Run after deterministic tests, never in CI. This is product validation, not the Objective 4 held-out
evaluation and not evidence that the pipeline is causally superior.

### 7.1 Fixtures

1. **Motivating comic story:** Andres and Leo, direct dialogue, personified robot, held toy, several
   actions, front/profile views.
2. **Human-character story:** two visually distinct humans, direct and indirect speech, one
   multi-action paragraph, front/profile/overhead scenes.
3. **Non-human story:** invented non-human character, an inert object of a similar category, and a
   running-away/rear-view scene.

Use three selected style presets across the set, including comic. Keep story inputs and chosen
style ids fixed in the run record. Do not require seed determinism that has not been proven.

### 7.2 Review every attempt, not only the winner

For each scene record:

- exact attempt id/path and prompt length;
- selected `final_image_ref` / `best_of` attempt;
- identity, anatomy, text-free, style, subject-unique, and scene-contradiction signals;
- whether a human reviewer prefers a non-selected attempt and why;
- whether attempt 2 or 3 improves, preserves, or regresses the visible defect it targeted;
- whether the requested viewpoint is front, profile, rear, overhead, or occluded and whether the
  image follows it;
- whether any speech bubble/readable text appears;
- whether an actor/object duplicate or impossible holder relation appears.

### 7.3 Retention gates

Retain S1 only if all hard product regressions are absent:

1. no prompt contains the raw excerpt, quoted dialogue, narrative notes, or accumulated prior
   correction block;
2. no explicit actor alias survives as a second object;
3. all 3 books complete within existing cost and recursion bounds;
4. all requested rear/profile/overhead scenes remain eligible and are not rewritten front-facing;
5. no selected scene loses an essential visible fact of its chosen key moment because the excerpt
   was removed.

The following are directional observations, not hard statistical gates:

- lettering frequency;
- fraction of retries that outrank predecessors;
- fraction of human-preferred attempts selected by `_rank`;
- prompt-length reduction;
- failing-page count.

If an essential fact is lost, revise the structured direction fields/instructions; do not restore
the raw excerpt as a second prompt authority. If rear/profile views are penalized, inspect judge
reasoning before changing generation toward front-facing poses. If retry outcomes remain near
chance, revisit correction quality before buying a fourth attempt.

---

## 8. Linked decisions, gaps, and implementation gates

### 8.1 Binding decisions

- **ADR-004:** the runtime judge is a control signal, never the research outcome.
- **ADR-010 / ADR-037:** corrected retries and three-attempt cap; no fourth draw.
- **ADR-013:** captions remain post-redaction verbatim excerpts.
- **ADR-023 / ADR-024:** frozen contract, partial returns, existing graph shape.
- **ADR-025:** boundary/provider failure posture and image breaker.
- **ADR-028:** frozen seven-value taxonomy and lexicographic best-of.
- **ADR-039 / ADR-040:** narrative notes define neither canonical identity nor newly assembled
  scene prompts; ADR-040 resolves D-M and amends ADR-039 Decision 4.

### 8.2 Required dedicated decisions

- **D-N — moderation replacement consistency:** decide the graph/state mechanism for judging one
  safe replacement without permitting another redraw or making the flagged original eligible.
  This is S2, not a hidden part of S1.

### 8.3 Known gaps deliberately carried

1. Implicit semantic actor/object aliases remain possible.
2. Semantic speech wording without literal quotes can reach `visual_direction`.
3. The scene-constraint judge remains an unvalidated noisy VLM signal.
4. `different_face=True` can coexist with `same_character=True`; raw output is preserved pending
   angle-aware evidence.
5. Exact duplicate contradiction strings are removable; paraphrased contradictions are not.
6. Later-moment merge choice is a deterministic heuristic, not semantic salience.
7. One structured `key_action` field cannot prevent the model from writing a compound action inside
   that string.
8. A safe moderation replacement remains consistency-unchecked until D-N is implemented.
9. Old checkpoints keep old prompts by design.
10. Fal seed reproducibility remains unproven, so retry improvements cannot be attributed solely to
   wording.

### 8.4 Spec and documentation blast radius at implementation

The implementation change must update, in the same commit, the affected live behavior in:

- `docs/specs/story-analyzer.md`;
- `docs/specs/scene-segmentation.md`;
- `docs/specs/prompt-optimizer.md`;
- `docs/specs/regeneration-controller.md`;
- `docs/specs/lettering-suppression.md`;
- `docs/specs/pose-viewpoint-composition.md`.

ADR-040 governs scene-note removal. ADR-039 and ADR-040 are frozen and are not edited during
implementation.

Executed plans remain historical and are not edited. Grep the repo for `text_excerpt`,
`CharacterDescription.notes`, `last.prompt`, `visual_direction`, `one corrected retry`, and
`attempts) >=` before calling implementation complete.

---

## 9. Definition of done

S1 is done only when:

1. ADR-040 remains the accepted decision resolving D-M and this spec matches it.
2. The user approves this written spec after that resolution.
3. A separate implementation plan is written in `docs/specs/plans/`.
4. Every §6 deterministic assertion exists and passes.
5. Backend pre-merge verification passes with exact output reported.
6. The three-story Tier-B check is run and documented with every attempt/winner trace.
7. All §7.3 hard retention gates pass, or the change is revised/reverted without making a quality
   claim.
8. Every live affected spec in §8.4 is updated in the implementation change.
9. The disposable implementation plan is deleted after build + tests + spec updates are complete.

**Not done** if: Fal still receives the raw excerpt or narrative notes; a retry bases itself on
`last.prompt`; a merge concatenates two moments; a front-facing pose is forced merely to resemble
the reference; an actor alias survives as an object in the motivating pattern; a fourth attempt is
added; moderation or ranking behavior changes inside S1; deterministic tests assert generated
quality; or the three-story run is described as a capstone efficacy finding.
