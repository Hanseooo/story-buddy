# Feature Spec — prompt-optimizer

**Status:** built · c0e73d4–6850321 · **Phase:** 1 · **Owner:** `backend/pipeline/prompt_optimizer.py` — **pure helpers, not a graph node**
**Derived from:** MASTER_SPEC §2 (system map, node-I/O table), §3 (frozen contract)
**Rationale:** ADR-004 (`FailureReason` closed set), ADR-007 (style rides the reference), ADR-010
(targeted-retry correction), ADR-022 (style fragment content rules)

> Two pure functions that turn a scene into an image-generation prompt, and a failed attempt's
> `failure_reasons` into a corrected one. No LLM call, no new node, no contract change —
> `Scene.prompt` and `FailureReason` already exist, frozen since `story-memory-contract` / ADR-023.

## 1. Purpose

Build the text prompt `generate_scene` sends to the image model: present characters' appearance
descriptions + visible objects + rendered visual direction + location setting + the frozen style
fragment (`SCENE_PROMPT_VERSION = 2`). Per ADR-040, narrative text excerpt and character notes are
excluded from positive scene prompt construction. Separately, build the ADR-010 corrected prompt a
future targeted-retry node uses after a failed consistency check, by turning the judge's
`failure_reasons` into emphasis clauses.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `Scene.characters_present` (joined against `state.characters` for appearance axes of
  `CharacterDescription`), `state.style.prompt_fragment`, `Location`, `Scene.objects_present`,
  `state.objects`, `Scene.visual_direction`; `correct_prompt` additionally reads
  `Attempt.failure_reasons`.
- **Writes:** nothing itself. `generate_scene` writes the return value into `Scene.prompt` (the field
  already exists; no schema change, no `schema_version` bump).
- **Invariants:**
  1. `build_prompt` always includes the style fragment (ADR-007: style rides the reference; the
     fragment is belt-and-suspenders on top of that).
  2. `build_prompt` never fabricates content beyond present characters' populated appearance axes
     (species, colours, body_features, clothing — omitting narrative notes per ADR-040), visible
     objects, rendered visual direction, the scene's location, and the style fragment.
  3. `correct_prompt` never drops content from the prior prompt — it only appends emphasis clauses.

## 3. Position in the system map

Not a node. Per MASTER_SPEC §2 line 162 and the capstone mapping, Prompt Optimizer is a node
*input*, not a node of its own.

```
input_gate ──► analyze ──► segment ──► char_bible ──► generate_scene ──► consistency_check ──► ...
                                                          ▲
                                              build_prompt (this spec, wired here)
```

- `generate_scene` calls `build_prompt` for the first attempt — **wired in this spec**, replacing the
  `scene.caption or scene.text_excerpt` line (`pipeline/generate_scene.py:27`, the `# ponytail:
  text-to-image, no character reference yet` stub).
- `correct_prompt` is called by `regenerate` (the node built in `regeneration-controller`, Part 2). `FailureReason` was **not** touched — it remains frozen at 7 values (ADR-028); the two new boolean params drive corrections outside those 7 without adding an 8th enum value.
- No conditional edge. No contract change.

## 4. Behavior & edge cases

```python
def build_prompt(
    characters_present: list[str],
    characters: list[Character],
    style_fragment: str | None,
    location: Location | None = None,
    objects_present: list[str] | None = None,
    objects: list[StoryObject] | None = None,
    visual_direction: str | None = None,
) -> str
def correct_prompt(prompt: str, failure_reasons: list[FailureReason], characters: list[Character], style_fragment: str | None, same_character: bool = True, anatomy_intact: bool = True, text_free: bool = True) -> str
```

(Corrected during implementation: `build_prompt` needs `characters_present` to do its own
characters_present → characters join per §4's own prose and the §6 node-level test, which passes
the full unfiltered roster; `correct_prompt` needs `style_fragment` to restate it for `wrong_style`.)

### `style_prohibitions` / `filtered_description` / `filtered_location` / `filtered_object` / `permitted_words` (ADR-035)

Helpers exported because pipeline nodes share them. `filtered_object` applies the same style-prohibition word filtering to `StoryObject.description` while leaving `obj.name` untouched.

### Block Ordering and Invariants

`build_prompt` emits prompt blocks in the exact contract order (`SCENE_PROMPT_VERSION = 2`):
1. Reference roll (`Image N is...`) with extended `REFERENCE_CLAUSE`:
   > `"The reference images define appearance, not pose, crop, expression or viewing angle; the Visual direction controls those scene properties."`
2. Text-only character descriptions (unreferenced present characters, appearance axes only)
3. Exact visible cast count and non-human clause (`SUBJECT_COUNT_CLAUSE`, `NON_HUMAN_CLAUSE`)
4. Visible objects block:
   ```text
   Visible objects:
   <name>, <description>
   ```
5. Visual direction block:
   ```text
   Visual direction: <visual_direction>
   ```
6. Setting line (`Setting: <name> - <description>`)
7. Style fragment (`style`)

`generate_scene` requires a non-empty `scene.visual_direction` and logs `image_model=settings.fal_image_model` alongside attempt metrics and `scene_prompt_version=2`.

`referenced_characters` deduplicates `characters_present` order-preservingly, so a checkpoint
written before `segment`'s own dedup cannot send one reference image as two subjects on resume.

`REFERENCE_CLAUSE` closes **two** duplication mechanisms that look identical in the output:

- **Compositing (#23):** given unaddressed references an edit model inlays them into the canvas.
  Answered by *"do not copy, inset, mirror or repeat the reference images inside it, and draw each
  character exactly once."*
- **Semantic (#32):** the scene's own prose summons the thing regardless of what the prompt says
  about the images — prod job `d83721d9`'s `s1` sent `"Image 2 is the star"` and `"found a tiny
  glowing star"` and got both, with `same_character=True` and `anatomy_intact=True`, so the #23
  branch was not involved. Answered by *"When the text below names one of these characters, it is
  referring to that character itself, not to a second thing of the same name."*

The #32 sentence is **generic on purpose** — "one of these characters", never rendered per-name.
References are sent for every `characters_present` character, including ones the excerpt never
names (#23's *"Ana decided to help."* sent two), and asserting an absent character is itself how a
floating extra appears. Leaning on the roll for the antecedent means the sentence can never
introduce a name the roll did not already assert. It also binds the **name**, not the noun class,
so a genuinely separate instance ("she looked up at the stars") stays drawable.

`_describe` additionally drops a `species` that is an exact token of the `name`, so `"the star -
star"` renders as `"the star"` — a definition carries no information and is a second bare assertion
of the same noun. This does **not** breach ADR-035's `species` carve-out: what filtering species
could make vacuous is the *reference* gate, whose subject line is built by `char_bible`'s own
`_describe`. `consistency_check.JUDGE_PROMPT` interpolates `{name}` only, and `correct_prompt`'s
`wrong_species` clause reads `description.species` straight off the contract.

### `correct_prompt`

Four module-level constants close the holes where reason clauses alone append nothing (making the retry a pure resample, which ADR-010 rejects):

- `IDENTITY_CLAUSE = "the characters must match the reference images exactly"` — fires when `same_character=False` and `failure_reasons` is empty (i.e. the judge named the failure but gave no reason; anatomy is outside the frozen 7 so it has no FailureReason entry). It fires a **second** way, as a floor: see *Unfillable clauses* below.
- `ANATOMY_CLAUSE = "anatomy must be correct: no merged, missing or duplicated body parts"` — fires when `anatomy_intact=False` (ADR-028 froze anatomy out of `FailureReason`; this is the only correction available).
- `TEXT_CLAUSE = "every surface in the picture is blank and unmarked"` — fires when `text_free=False` (lettering-suppression §4.4: asserts blankness without naming text, letters, words or writing, which are what summoned text in prior attempts).
- `COMPOSITION_CLAUSE = "Preserve the Visual direction exactly: do not change the requested action, movement direction, pose, crop, expression, or viewing angle."` — fires on every corrected retry (appended last when clauses exist) to preserve requested composition.

All three boolean params default to `True` so the four-positional-arg signature stays call-compatible.

A fixed, module-level dict maps each of the 7 `FailureReason` values (`backend/contracts/story_memory.py`)
to an emphasis-clause template:

| `FailureReason` | Clause |
|---|---|
| `wrong_colour` | "match the reference's exact colours: {colours}" |
| `wrong_species` | "the character is a {species}, not anything else" |
| `wrong_body_feature` | "match these body features exactly: {body_features}" |
| `wrong_clothing` | "match this clothing exactly: {clothing}" |
| `wrong_style` | the style fragment, restated |
| `different_face` | "match the reference character's face exactly" |
| `character_absent` | "make sure {name} is clearly visible in the scene" |

For each `FailureReason` in the input list (order preserved, duplicates collapsed), append the filled
clause to `prompt`. **Attribution ceiling:** `VlmVerdict`/`Attempt.failure_reasons` carry no
per-character breakdown today — a scene with two `characters_present` gives no signal for *which*
character a `wrong_colour` verdict concerns. `correct_prompt` therefore fills axis-based clauses
(`wrong_colour`, `wrong_species`, `wrong_body_feature`, `wrong_clothing`) from **every** character in
`characters`, joining multiple values where more than one is present — over-specifying rather than
guessing wrong. `wrong_style`/`different_face` don't fill from a `CharacterDescription` axis at all, so
this ceiling doesn't touch them. `character_absent` fills `{name}` from every character in
`characters` whose `char_id` isn't yet confirmed present — since that confirmation is
`consistency_check`'s job (unbuilt) and out of scope here, it names all of them. Sharpening this to a
single named character requires the judge to attribute a reason to a `char_id`, which is
`consistency-checker`'s contract decision, not this spec's.

**Unfillable clauses.** A clause whose every `{placeholder}` interpolates to an empty string is
**dropped**, and if that leaves the correction empty, `IDENTITY_CLAUSE` floors it. `_fillable` reads
the placeholders off the template with `string.Formatter().parse`, so the check needs no second
reason→axis dict and a new clause cannot forget to register one; `different_face` parses to no
placeholders and is therefore always fillable.

Why the floor rather than the hollow clause the earlier revision emitted: the judge compares the
image to the **reference**, so it can legitimately return `wrong_colour` for a character whose
`CharacterDescription` records no colours — a thin `analyze` extraction, or ADR-035 filtering the
axis to nothing. `"match the reference's exact colours: "` corrects nothing, and once
`consistency-checker`'s `GATING_REASONS` made `wrong_colour` able to fail a page **on its own**, that
was a whole retry spent on the resample ADR-010 rejects. `IDENTITY_CLAUSE` points the retry at the
reference images, which are already in the payload and do carry the colour. The floor is guarded on
a non-empty `failure_reasons`, so the no-op call still returns `prompt` byte-identical, and it is
evaluated **last**, so a page with anything specific left to say never also gets the generic clause.
Every drop is logged (CC-5) — a thin description that keeps costing redraws should be visible.

### Edge cases

| Case | Behavior |
|---|---|
| **Empty `characters_present`** | `build_prompt` returns a character-free prompt: `text_excerpt` + style fragment only. Valid — `char_bible`'s and `segment`'s precedent is scenes may be unreferenced. |
| **`char_id` in `characters_present` not found in `state.characters`** | Skipped, logged. Same posture as `segment`'s "name not in roster" case — this function may not extend the roster. |
| **`style_fragment is None`** | Falls back to `settings.default_style_fragment`, matching `char_bible`. |
| **No present character has a canonical reference** | Image roll *and* the #32 binding sentence are both omitted — the text-to-image path sends no images to bind a name to. The semantic duplicate is therefore unaddressed on that path; with no reference, "twice" is barely defined. |
| **A character's name is a common noun the excerpt also uses** (`"the star"` in *"found a tiny glowing star"*) | The binding sentence ties the name to the reference and `_describe` suppresses the redundant species. `text_excerpt` is untouched either way — ADR-013 freezes it verbatim, so rewriting the prose to disambiguate is not available. |
| **`species` is an exact token of `name`** (`"the star"` / `"star"`) | Dropped from the description line, which floors to `"the star"` (or `"the star - tiny"` if another axis is populated). Exact token match, so `"the retriever"` / `"golden retriever"` keeps its species — the degenerate case this removes is identity, not resemblance. |
| **Two characters share a name** | No longer reaches here: `segment`'s `name_to_id` has been `setdefault` first-seen-wins since `scene-setting-and-subject-binding` §4.3, so one mention maps to ONE `char_id` and the roll cannot read `"Image 1 is the star. Image 2 is the star."` This row described the pre-§4.3 list-valued map until 2026-08-13. `referenced_characters` keeps a `dict.fromkeys` pass anyway, for checkpoints written before that change. |
| **Empty `failure_reasons`** | `correct_prompt` returns `prompt` unchanged when both booleans are `True`. With `same_character=False` it appends `IDENTITY_CLAUSE`; with `anatomy_intact=False` it appends `ANATOMY_CLAUSE`. |
| **Multiple `failure_reasons` on one attempt** | All matching clauses appended, in enum-declaration order, no duplicates even if a reason repeats. |
| **Every value on an axis is style-forbidden** (e.g. `colours == ["glowing"]` under `comic`) | ADR-035 filters it to empty, and the row below then applies. Restating the forbidden attribute is still refused — that is what made `wrong_colour` answer "match the reference's exact colours: glowing" (issue #24). |
| **A description axis referenced by a clause is empty** (e.g. `wrong_colour` but `colours == []`) | The clause is **dropped**, and `IDENTITY_CLAUSE` floors the correction if nothing else survives. Still no invention — a thin description stays thin, same posture as `char_bible` §4's "species-only description" case — but a hollow clause is not a correction either, and since `GATING_REASONS` this can be a page's only reason. See *Unfillable clauses* above. Said "the clause still appends with an empty list rendered" until 2026-08-13. |

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] CC-3 Cost control — zero marginal cost. No model call; pure string construction.
- [x] CC-5 Observability — `generate_scene` logs the built prompt (or its length) alongside the
      existing per-attempt logging, so a bad image traces to what it was asked for.
- [x] CC-7 Reproducibility — trivially satisfied; both functions are pure and deterministic.
- All other CC items: N/A — no moderation, PII, security, UI, or checkpointing surface. Neither
  function performs an effect, so there is nothing to checkpoint or resume.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Both functions are pure — no provider calls, no mocks needed. Per `char_bible`'s own precedent
("`reference_prompt` and `best_draw` are pure functions, so they are not effect boundaries and need
no mocks"), node-level tests exercise `build_prompt` for real rather than patching it.

**`build_prompt` — no mocks:**
- Contains each populated description axis for every character in `characters_present`.
- Always contains the style fragment; falls back to `settings.default_style_fragment` when
  `style_fragment is None`.
- Empty `characters_present` → prompt is `text_excerpt` + style fragment only, no character content.
- A `char_id` absent from `characters` is skipped without raising.

**The image roll — no mocks (issues #23, #32):**
- Each reference image is named by index, numbered in upload order, so a present character without a
  reference does not consume an image number; the roll is omitted when nothing is referenced.
- The #32 binding sentence is present when a reference was sent and absent when none was.
- A `species` that is an exact token of the `name` is dropped from the description line; the other
  axes survive; a multi-word species the name only partly carries is kept.

**`filtered_description` / `style_prohibitions` / `permitted_words` — no mocks (ADR-035):**
- `style_prohibitions` reads the `no <term>` clauses off `comic` and `cel`; a fragment that forbids
  nothing yields the empty set.
- A style-forbidden colour is dropped; one the active fragment never forbids is kept (per-preset, not
  a blanket ban).
- Word-level removal keeps the rest of the entry (`"glowing eyes"` → `"eyes"`).
- `species` is never touched, even when a forbidden word sits inside it.
- A `notes` carrying a forbidden word is dropped whole, not word-by-word; a `notes` the style permits
  (`"secondary character"`) survives untouched.
- `permitted_words` strips the forbidden word out of a single value (`"glowing orb"` → `"orb"`),
  returns `""` when nothing survives, and passes `None` through.
- Prefix matching works in both directions and does not fire on `"glove"` vs `"glow"`.
- `build_prompt` drops the forbidden attribute from the description line while emitting
  `text_excerpt` verbatim even when the excerpt names that same term (ADR-013 is not amended).
- `correct_prompt` fills `wrong_colour` from the filtered colours only.

**`correct_prompt` — no mocks:**
- Each of the 7 `FailureReason` values, given alone, produces its documented clause appended to the
  input prompt.
- Multiple reasons in one list all appear, in enum-declaration order.
- A repeated reason produces the clause once, not duplicated.
- Two characters in `characters` and one axis-based reason (e.g. `wrong_colour`) → the clause joins
  both characters' colours, guarding the attribution-ceiling behavior in §4.
- Empty `failure_reasons` → returns `prompt` unchanged (identity).
- The original `prompt` content is never truncated or altered — only appended to.
- **Unfillable clauses:** an empty axis drops its clause and floors on `IDENTITY_CLAUSE`; an empty
  axis **beside a filled one** drops its clause and does **not** floor; a style-emptied axis
  (ADR-035, `colours == ["glowing"]` under `comic`) behaves identically to a natively empty one; the
  drop is logged. The order test uses a real character, since an empty roster would now drop both
  its clauses and leave the assertion vacuous.

**Node-level (`generate_scene`):**
- `generate_scene` calls `build_prompt` with `(scene.text_excerpt, state.characters,
  state.style.prompt_fragment)` and stores the return value in both `Scene.prompt` and the new
  `Attempt.prompt` (unchanged behavior from today, just fed a real prompt instead of the stub).

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

N/A. Deterministic text construction. Whether the resulting prompt makes the image model produce a
*good* image is measured downstream, by `image-generator`/`consistency-checker`'s eval legs — not a
separate instrument here.

## 8. Linked decisions & open questions

**Depends on:** ADR-004 (`FailureReason` closed 7-value set, frozen permanently per ADR-028) ·
ADR-007 (style rides the canonical reference; the fragment is belt-and-suspenders) · ADR-010
(one targeted retry, prompt corrected using the judge's failure reasons) · ADR-022 (style fragment
content rules — names a medium and its artifacts, never generic quality words).

**Hands off — named here, owned elsewhere:**
- **Wiring `correct_prompt` into a graph path** → `regeneration-controller` Part 2 (`regenerate` node). This spec defines and tests the function; the caller is built there.
- **The `text_to_image` → `edit_image` swap and reference-image plumbing** → `image-generator`. This
  spec only replaces the *prompt* line in `generate_scene.py`, not the provider call it feeds.

**Open:** none.

## 9. Definition of done

Per AGENTS.md *Definition of Done*. This module is done when **all** of the following hold:

1. `backend/pipeline/prompt_optimizer.py` implements §4 — `build_prompt` and `correct_prompt`, both
   pure, plus the module-level `FailureReason` → clause-template dict.
2. `backend/pipeline/generate_scene.py`'s prompt line is replaced with a call to `build_prompt`; the
   `# ponytail: text-to-image, no character reference yet` comment's *prompt* half is removed (the
   `text_to_image` → `edit_image` half stays, per §8 — that's `image-generator`'s change).
3. Every §6 assertion exists and passes in `backend/tests/test_prompt_optimizer.py` and the updated
   `backend/tests/test_generate_scene_node.py`.
4. Backend verify is green and its output is shown, not claimed:
   `uv run ruff check . && uv run pytest` from `backend/`.
5. **Status line above flips to `built`** with the commit range, per the spec lifecycle
   (MASTER_SPEC §7).
6. **The finding-change grep is run** and every hit fixed in the same change. Known surface:
   - `docs/product/DECISION_BACKLOG.md` — tick the `prompt-optimizer` line and replace the
     *"Recommended next session"* block with `image-generator` as the next action.
   - `docs/WORKFLOW.md` §"Right now".
   - `AGENTS.md` *Validation Notes* — note `prompt-optimizer` built; *Project Context* stub list is
     unaffected (this spec doesn't touch a graph node's stub status).

**Not done** if: any §6 test is skipped; `backend/contracts/` is modified; `correct_prompt` is wired
into a node this spec doesn't own; `build_prompt` invents character detail beyond what
`CharacterDescription` populated; or the `image-generator` hand-off (the provider-call swap) is
silently absorbed into this change instead of being left to its owner.
