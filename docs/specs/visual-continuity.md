# Feature Spec — visual continuity

**Status:** approved · **Phase:** 2 · **Owner nodes:**
`backend/pipeline/analyze.py`, `segment.py`, `char_bible.py`, `prompt_optimizer.py`,
`consistency_check.py`, `regenerate.py`
**Derived from:** MASTER_SPEC §§2–6 · **Rationale:** observed job
`3cc05c4b-f6ef-4427-8dba-96af0a14a4e1`, ADR-004, ADR-010, ADR-023, ADR-024,
ADR-028, ADR-034

> **Declared cross-node spec.** One visual fact must survive entity extraction, scene planning,
> prompt construction, judging, and correction. Splitting that chain into five specs would leave
> no single owner for continuity. No new graph node or edge is added.

---

## 1. Purpose

Make a character, their recurring possessions, and their intended action remain recognizable from
the story through every generated page. This is a targeted product-quality fix driven by concrete
failures, not a corpus-level research claim.

The motivating job provides four distinct failures:

1. `analyze` persisted the Shadow Wizard only as `species="wizard"`, with empty `colours`,
   `body_features`, and `clothing`. The reference image invented the face, age, hat, robe, cape,
   and palette; none became textual canon.
2. `char_bible`'s judge described the reference as young and cheerful rather than dark or imposing,
   but returned `contradictions=[]`. ADR-034's derived gate therefore accepted it.
3. Later scenes rendered the same role as materially different people: an old bearded hooded man,
   a younger clean-shaven hooded figure, and another bearded pointed-hat wizard. One incorrect
   version passed the scene judge because it matched the category “wizard,” not the instance.
4. `analyze` correctly extracted Ana's wooden sword into `objects[]`, but no downstream production
   code reads that collection. The sword has no continuity channel.

The same trace also placed the inert bright crystal in both `characters[]` and `objects[]`, consuming
one of the three character slots. The fix must distinguish an actor from a prop before images are
drawn.

**Explicitly out:** setting consistency (docket S4), more reference views, more than one scene
retry, a higher image budget, model replacement, UI for reviewing text-only side characters, and a
paid corpus baseline. Model choice is revisited only if this complete-data path fails the targeted
acceptance check in §7.

---

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

Four additive fields, all defaulted and declared last on their models. Old checkpoints deserialize;
there is no `schema_version` bump (ADR-023 additive-field convention).

```python
class StoryObject(BaseModel):
    obj_id: str
    name: str
    description: Optional[str] = None
    owner_char_id: Optional[str] = None       # NEW — ordinary/initial holder, not immutable

class Scene(BaseModel):
    ...
    objects_present: list[str] = Field(default_factory=list)  # NEW — visible obj_ids
    visual_direction: Optional[str] = None                    # NEW — illustration contract

class Attempt(BaseModel):
    ...
    scene_contradictions: Optional[list[str]] = None  # NEW — None=unchecked, []=checked clean
```

`CharacterDescription` does not change shape. Its existing `species`, `colours`, `body_features`,
and `clothing` fields become a complete frozen visual profile instead of a sparse extraction.
`notes` remains narrative metadata and never counts as a visual discriminator.

### Reads and writes

- **`analyze`** reads `input.redacted_text`; writes complete `characters[]`, mutually exclusive
  `objects[]`, stable object descriptions, and `owner_char_id`.
- **`segment`** reads the entity rosters and redacted story; writes
  `scenes[].characters_present`, `objects_present`, and `visual_direction`.
- **`prompt_optimizer`** reads those fields plus character/object canon; writes nothing.
- **`generate_scene`** continues to own `scenes[].prompt`; its call shape is unchanged.
- **`consistency_check`** writes `Attempt.vlm_verdict`, `failure_reasons`,
  `scene_contradictions`, `passed`, and `Scene.final_image_ref`.
- **`regenerate`** reads the stored contradictions and appends their correction to the existing
  attempt prompt.

### Invariants

1. Every rostered character has a physical kind plus at least three stable visual discriminators
   spanning at least two of `colours`, `body_features`, and `clothing`. A humanoid also has a
   non-empty clothing description. Story-stated facts are never replaced.
2. `characters[]` contains actors: entities that speak, decide, move intentionally, or perform an
   action. An inert prop exists only in `objects[]`. A personified object is a character, not both.
3. `characters_present` means the intended visible cast only. Mentioned, remembered, or off-screen
   characters are excluded.
4. `objects_present` contains known `obj_id`s only and has no duplicates.
5. `visual_direction` is non-empty on every generated scene and names subject, action, target or
   movement direction where applicable, and viewpoint.
6. A canonical reference defines appearance only. Its pose, crop, expression, and viewpoint never
   override `visual_direction`.
7. A scene-level failure gates only through a non-empty structured contradiction list. `None`
   means the composition check was unavailable; `[]` means it completed cleanly. No separate
   overall score or free-text rationale can contradict the branch condition.
8. One real verdict may buy the existing one corrected redraw. Judge failure never buys an
   unguided resample.

---

## 3. Position in the system map

The graph remains byte-for-byte the same:

`analyze → segment → char_bible → char_ref_mod → reveal → generate_scene → consistency_check →
[regenerate] → consistency_check → output_mod`

No node, edge, router label, image call, retry, or reference slot is added. ADR-003 and ADR-024 are
unchanged. Model IDs remain sourced only from `backend/app/config.py`; this spec does not swap them.

The only new provider work is one scene-composition judge call per attempt inside
`consistency_check`'s existing effect helper. The current per-reference identity calls remain
one-per-character as required by ADR-004.

---

## 4. Behavior and edge cases

### 4.1 Complete character canon in `analyze`

`EXTRACTION_PROMPT` stops saying “leave them empty rather than inventing details.” It instead makes
two sources explicit:

1. Copy visual facts the story states without alteration.
2. Fill only missing axes once, with neutral, child-safe, non-stereotyped details that make the
   character visually distinct from the rest of the roster.

The physical `species`/kind must not be a job title. A human Shadow Wizard is physically human;
“shadow wizard” remains the name/role. A valid filled profile could therefore carry a stable age
band and face shape in `body_features`, a fixed palette in `colours`, and an exact hat/robe/cape in
`clothing`.

The strict node-local extraction schema enforces invariant 1. The persisted contract stays
backward-compatible and permissive; only newly extracted production data must be complete.

Entity classification follows agency, not grammar:

| Entity | Collection |
|---|---|
| Ana acts and decides | `characters[]` |
| A talking kettle acts and decides | `characters[]` |
| The bright crystal restores light but has no intent | `objects[]` |
| Ana's wooden sword | `objects[]`, `owner_char_id="c0"` |

The existing three-character cap and two-reference cap remain. Every capped-in character receives
text canon; only the first two may also receive reference images.

### 4.2 Stable object canon

`StoryObject.description` becomes a physical description suitable for repeated rendering, not only
a narrative relation. `owner_char_id` is mapped from a node-local `owner_name`; an unknown owner is
a semantic boundary error, not silently set to null. Truly unowned props keep `None`.

`owner_char_id` names the ordinary or initial holder. A transfer does not rewrite the global object;
scene planning carries the temporary holder locally and states it in `visual_direction`.

### 4.3 Visible cast and visual direction in `segment`

`ExtractedScene` gains node-local fields:

```python
objects_present: list[str] = []
object_events: list[ExtractedObjectEvent] = []
visual_direction: str

class ExtractedObjectEvent(BaseModel):
    object_name: str
    action: Literal["acquire", "release"]
    holder_name: str
```

The object list and events carry roster names at the LLM boundary and are mapped to ids by the
node. `holder_name` makes a transfer unambiguous: release from one holder, then acquire by the
other. Unknown names, an empty direction, or a direction that names a character outside the visible cast fails before
`char_bible`, so no fal image has been purchased.

The current unconditional exact-name recovery is removed: a name appearing in an excerpt does not
prove that the character should be visible. The structured `characters_present` decision is the
authority. All `ExtractedScene` repair and merge paths must preserve the four new local fields.

`visual_direction` is short and literal, not prose improvement. For the motivating final beat it
must say the equivalent of:

> The Shadow Wizard is seen from behind fleeing away from Ana toward the forest; Ana remains behind
> facing him.

That instruction is distinct from the verbatim caption, which remains `text_excerpt` under ADR-013.

### 4.4 Object lifecycle

`segment` walks final scenes in order with an active-holder map:

1. Start with objects explicitly visible in the scene and active objects whose holder is visible.
2. Process `object_events` in narrative order. `acquire` sets/replaces the holder and makes the
   object visible when that holder is visible. `release` keeps the object visible in that beat,
   then clears the holder only when the named releaser is its current holder.
3. Persist the deduplicated `obj_id` list and carry the resulting holder map into the next scene.

A transfer is an ordered release followed by acquisition by the recipient in the same scene. The node appends
the current holder relation to `visual_direction`, so later prompts do not depend on the object's
global initial owner.

An owned item remains active while its holder is off-screen but is not rendered there. An unowned
prop appears only when explicitly requested. If a story starts with “Ana has a sword,” its first
visible scene is the acquisition point; the sword is not back-projected into an earlier scene.

### 4.5 Prompt composition

`build_prompt` emits blocks in this order:

1. Numbered reference roll, with each referenced character's complete textual profile folded into
   the same sentence.
2. Complete textual profiles for visible characters without a reference.
3. Exact visible-cast count and names.
4. Visible object descriptions.
5. `Visual direction: ...`.
6. The existing setting line.
7. Verbatim `text_excerpt`.
8. Style fragment.

Current holder relations are appended deterministically to `visual_direction` by `segment`; the
global `owner_char_id` is never reused after a transfer. The roll gains one fixed sentence:
reference images define appearance, not pose, crop, expression,
or viewing angle; the visual direction controls those scene properties. This removes the direct
conflict between the front/slight-angle reference and a character correctly shown fleeing.

### 4.6 Reference and scene judging

`char_bible` already judges a reference against `CharacterDescription`. With complete profiles,
its contradiction list now has concrete age, face, palette, and clothing claims to check. ADR-034
remains the branch rule: `not ref_verdict.contradictions`; `matches_description` stays an instrument.

`consistency_check` retains its per-reference identity calls. It adds one node-local
`SceneConstraintVerdict` call against the scene image and text constraints:

```python
class SceneConstraintVerdict(BaseModel):
    differences_observed: str
    contradictions: list[str] = Field(default_factory=list)
```

The prompt checks:

- every expected visible character appears exactly once;
- no unrequested character appears;
- text-only characters match their frozen profiles;
- every `objects_present` item appears with its frozen appearance and current holder;
- the action, direction, and viewpoint match `visual_direction`.

Each contradiction must name the subject and violated requirement. The list alone gates and is
persisted as `Attempt.scene_contradictions`: `None` is unavailable/unparseable; `[]` is checked
clean. This preserves the distinction across checkpoints rather than only in logs.

For scenes with referenced characters, the combined pass predicate is the existing
identity/anatomy/text/attribute predicate **and** `scene_contradictions == []`. For a scene with no
reference-bearing character, identity is not applicable and a clean composition verdict may pass
the attempt on its own. If an applicable judge is unavailable, the attempt is unchecked rather
than passed. The closed seven-value `FailureReason` enum is untouched.

### 4.7 Corrected retry and best-of

`correct_prompt` appends every available concrete contradiction after existing
identity/anatomy/text corrections. A concrete failure from one check may still guide the existing
retry when the other check is unavailable; the unavailable check itself never buys a redraw. The
function never changes the reference list and never creates a second retry.

Best-of ranks in this order:

1. any checked signal over no checked signal;
2. `same_character`;
3. `anatomy_intact`;
4. `text_free`;
5. no identity-bearing attribute failure;
6. no scene contradictions;
7. fewer scene contradictions;
8. `subjects_unique`;
9. `style_match`.

Identity and malformed anatomy remain more important than pose or accessory correctness. When both
attempts fail the new gate, fewer concrete violations wins; ties keep the corrected attempt under
ADR-010's existing prior.

### 4.8 Failure behavior

| Failure | Behavior |
|---|---|
| Incomplete character profile | fail before any image draw |
| Unknown scene character/object or owner | fail before any image draw |
| Missing/invalid visual direction | fail before any image draw |
| Reference judge finds contradictions | existing in-node redraw, cap 3 |
| All three references contradict canon | ADR-028 best-of fallback reaches moderated reveal |
| Scene constraint list non-empty | existing one corrected redraw |
| Identity or composition judge unavailable | unchecked; ship current artifact; no blind redraw |
| Second attempt still fails | finalize existing best-of rule extended by §4.7 |

Changing ADR-028's fallback is deliberately not hidden inside this feature. If the owner wants a
terminal failure instead of reveal after three bad references, that is a separate ADR session.

### 4.9 Observability and prompt versions

- Clarify the character-reference prompt to check every frozen visual detail and increment its
  version from 4 to 5.
- Keep the existing per-reference identity prompt at version 3 unless its wording changes. Add a
  separate scene-constraint prompt at version 1.
- Log roster ids, visible cast, visible object ids, visual direction, scene contradictions, judge
  availability, retry number, winning attempt, all three prompt versions, and model ids.
- Never log raw pre-redaction story text.

---

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-1 Moderation ordering** — graph unchanged; references and scenes are still moderated
  before reveal/output.
- [x] **CC-2 PII redaction** — `analyze` and `segment` consume redacted text; new profiles and
  directions never read raw input.
- [x] **CC-3 Cost control** — zero new image calls and no retry increase. One new judge call per
  attempt is added; judge calls remain absent from `Cost`, an explicit residual risk.
- [x] **CC-5 Observability** — canon, cast, objects, direction, contradictions, versions, and winner
  are traceable without raw text.
- [x] **CC-7 Reproducibility** — fixed structured state improves within-run provenance; provider
  seed reproducibility remains unverified and no new claim is made.
- [x] **CC-9 Failure states** — semantic boundary failures occur before image spend and use the
  existing job-failure surface.
- [x] **CC-10 Checkpointing** — additive fields have defaults; node partial-return and scene reducer
  conventions remain unchanged.
- [ ] CC-4, CC-6, CC-8 — untouched.

---

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

All provider calls mocked. Generated-content quality is never asserted in CI.

### Contract

1. Old blobs lacking all four additive fields deserialize to `None`/empty lists, with
   `Attempt.scene_contradictions is None` rather than a false clean result.
2. New fields round-trip, remain declared last, and do not change `CURRENT_SCHEMA_VERSION`.

### `analyze`

3. Story-stated details survive unchanged while missing visual axes are filled.
4. A new character meets the discriminator floor; narrative `notes` do not satisfy it.
5. A humanoid with no clothing fails the strict extraction boundary.
6. An inert crystal appears only in `objects[]`; a personified talking object appears only in
   `characters[]`.
7. A new object requires a stable physical description; `owner_name="Ana"` maps to
   `owner_char_id="c0"`; an unknown owner fails.
8. The three-character and two-reference caps are unchanged.

### `segment`

9. A merely mentioned off-screen character is absent from `characters_present`.
10. A visibly acting character is mapped to its known `char_id`.
11. Unknown character/object names and empty visual direction fail before downstream work.
12. Acquisition makes an owned object visible; later owner-visible scenes carry it forward.
13. An off-screen owner hides but does not deactivate the item.
14. Release names its holder, shows the item in the release scene, and removes it afterward.
15. Release-plus-acquire transfers the item and carries it with the recipient on later scenes.
16. Unowned props do not carry forward.
17. All repair/merge constructors preserve object events and visual direction.

### `prompt_optimizer`

18. Prompt block order matches §4.5.
19. Referenced and text-only characters both carry complete profiles.
20. The exact visible cast excludes off-screen mentions.
21. Object description and current holder appear on every active scene.
22. The reference-pose sentence and visual direction both appear, with direction later.

### `consistency_check`

23. One composition call runs per attempt, including a scene with no reference images.
24. Concrete contradictions flip `passed` false and persist verbatim.
25. Empty contradictions do not alter the existing identity/anatomy/text predicate when identity
   applies; with no referenced character, a clean composition check may pass the attempt.
26. Composition-judge failure persists `None`, stays unchecked when applicable, and buys no blind
   retry; a concrete failure from another available check may still guide the existing retry.
27. `_rank` prefers no contradictions, then fewer contradictions, after the existing gating axes.
28. The seven-value `FailureReason` enum remains byte-for-byte unchanged.

### `regenerate` and graph

29. The correction prompt appends every named violation and preserves references.
30. Only one corrected attempt is possible.
31. Graph nodes, edges, `IMAGE_BUDGET`, `RECURSION_LIMIT`, and their formulas are unchanged.

---

## 7. Targeted quality verification (Tier B — never CI)

This feature intentionally skips S1's corpus harness. It proves or disproves the reported defect,
not a population-wide improvement.

1. Re-score the five checked-in `sample-dataset/` images against one human's labels. This spends
   judge calls but no fal images. The accepted clean result must not describe a contradiction; the
   old/young/hood/hat/beard changes must be named when they violate the frozen profile.
2. Run the exact Ana/Shadow Wizard story from trace
   `3cc05c4b-f6ef-4427-8dba-96af0a14a4e1` once after implementation.
3. The owner manually checks:
   - one frozen Shadow Wizard appearance survives every visible page;
   - Ana's sword persists from acquisition until release/end;
   - the bright crystal exists only as an object;
   - only intended visible characters appear;
   - the final wizard is visibly fleeing away from Ana;
   - any failed requirement produces a specific stored contradiction.

A single targeted pass permits “the reported defect is fixed.” It does not permit a percentage,
general consistency claim, or research result. If it fails, inspect the named boundary first; only
then consider a configured model swap.

---

## 8. Linked decisions and residual risks

**Depends on:** ADR-003 (no new edges), ADR-004 (per-character reference comparisons), ADR-010
(one corrected retry and best-of), ADR-023/024 (additive contract and partial returns), ADR-028
(three reference draws and closed `FailureReason`), ADR-034 (contradiction-derived reference gate),
ADR-035 (style filtering applies to invented profiles and object descriptions).

**No new ADR required by this design.** The contract fields are additive with defaults; graph shape,
retry counts, provider, model IDs, and artifact caps remain frozen. The change still spans more than
three modules, so this approved spec is the explicit human architecture gate required by AGENTS.md.

Residual risks:

1. **The analyzer may invent a weak canon.** The strict discriminator floor prevents emptiness, not
   poor taste. The moderated reveal remains the human correction point for referenced characters;
   text-only side characters have no new UI in this scope.
2. **One more VLM call per attempt.** It is not an image-budget term, but judge calls remain
   uncounted by `Cost` (CC-3). Close that only when cost/latency proves material.
3. **The judge remains fallible.** A contradiction-only branch removes boolean/prose disagreement;
   it cannot force visual understanding. The fixed-image rescore in §7 is the cheap model gate.
4. **Reference fallback can still conflict with canon.** ADR-028 deliberately ships best-of after
   three failed draws. Changing that is a separate ADR.
5. **No external-validity claim.** The donated corpus remains untouched for research evaluation.
6. **Exact original story required.** The targeted rerun must copy the trace input; reconstructing it
   from the timeline would test a different request.

---

## 9. Definition of done

- [ ] This written spec is reviewed and approved by the owner.
- [ ] The pipeline-consistency docket records the confirmed constraints and replacement of paid S1.
- [ ] Relevant existing specs are updated with the same behavior during implementation:
  `story-memory-contract`, `story-analyzer`, `scene-segmentation`, `prompt-optimizer`,
  `consistency-checker`, and `regeneration-controller`.
- [ ] All §6 tests are written failing first, then pass.
- [ ] From `backend/`: `uv run ruff check . && uv run pytest` passes.
- [ ] From `frontend/`: `pnpm lint && pnpm test` passes, proving the untouched client remains green.
- [ ] §7 fixed-image rescore and one exact-story rerun are completed and reported honestly.
- [ ] Repo-wide greps confirm the old sparse-description rule, prompt order, rank tuple, and object
  non-use are not still asserted elsewhere.
- [ ] The completed implementation plan is deleted after build + green verification, per artifact
  hygiene.
