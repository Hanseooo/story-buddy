# Feature Spec — prompt-optimizer

**Status:** built · c0e73d4–6850321 · **Phase:** 1 · **Owner:** `backend/pipeline/prompt_optimizer.py` — **pure helpers, not a graph node**
**Derived from:** MASTER_SPEC §2 (system map, node-I/O table), §3 (frozen contract)
**Rationale:** ADR-004 (`FailureReason` closed set), ADR-007 (style rides the reference), ADR-010
(targeted-retry correction), ADR-022 (style fragment content rules)

> Two pure functions that turn a scene into an image-generation prompt, and a failed attempt's
> `failure_reasons` into a corrected one. No LLM call, no new node, no contract change —
> `Scene.prompt` and `FailureReason` already exist, frozen since `story-memory-contract` / ADR-023.

## 1. Purpose

Build the text prompt `generate_scene` sends to the image model: scene text + present characters'
descriptions + the frozen style fragment. Separately, build the ADR-010 corrected prompt a future
targeted-retry node uses after a failed consistency check, by turning the judge's `failure_reasons`
into emphasis clauses.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

- **Reads:** `Scene.text_excerpt`, `Scene.characters_present` (joined against `state.characters` for
  `CharacterDescription`), `state.style.prompt_fragment`; `correct_prompt` additionally reads
  `Attempt.failure_reasons`.
- **Writes:** nothing itself. `generate_scene` writes the return value into `Scene.prompt` (the field
  already exists; no schema change, no `schema_version` bump).
- **Invariants:**
  1. `build_prompt` always includes the style fragment (ADR-007: style rides the reference; the
     fragment is belt-and-suspenders on top of that).
  2. `build_prompt` never fabricates content beyond `text_excerpt`, the present characters'
     populated description axes, **and the scene's location** (`Location.name`, plus
     `Location.description` when populated — widened by `scene-setting-and-subject-binding.md` §2).
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
def build_prompt(text_excerpt: str, characters_present: list[str], characters: list[Character], style_fragment: str | None, location: Location | None = None) -> str
def correct_prompt(prompt: str, failure_reasons: list[FailureReason], characters: list[Character], style_fragment: str | None, same_character: bool = True, anatomy_intact: bool = True) -> str
```

(Corrected during implementation: `build_prompt` needs `characters_present` to do its own
characters_present → characters join per §4's own prose and the §6 node-level test, which passes
the full unfiltered roster; `correct_prompt` needs `style_fragment` to restate it for `wrong_style`.)

### `style_prohibitions` / `filtered_description` / `permitted_words` (ADR-035)

Three pure helpers, exported because `char_bible` and `reveal` share them.

`style_prohibitions(style_fragment)` reads the words the active fragment forbids off its own
`no <term>` clauses — `comic` yields `{gradients, glow}`, `cel` yields
`{gradients, glossy, highlights, airbrushing}`. **Derived, never hand-listed**, so ADR-022 keeps sole
ownership of the fragments and a new preset arrives carrying its own prohibitions. This is why the
objection that killed the species word-list (`char_bible.py:74-77`) does not apply: that list is
open-ended, this one is closed by the fragment.

`filtered_description(description, style_fragment)` returns a transient copy with those words removed.

- **Three list axes word-level, plus `notes` all-or-nothing.** Never `species` (`analyze` makes it
  required precisely so acceptance can never be vacuous — ADR-035 limit 4).
- **Word-level** on the list axes: `"glowing eyes"` → `"eyes"`. An entry is dropped only if nothing
  survives, so a real subject fact is never discarded to remove a rendering one.
- **All-or-nothing on `notes`** (`_kept_whole`, ADR-035 amendment 2026-08-12b): one forbidden word
  drops the whole string. `notes` is a sentence, not a noun phrase, so the word-level rule would leave
  a mangled fragment; and since ADR-034 took `notes` out of the judge prompt, dropping it cannot make
  acceptance vacuous. It reaches the draw prompt (`char_bible.py:275`) and the scene prompt
  (`_describe`), which is why the carve-out had to go.
- **Prefix match in both directions**, floored at 4 characters — `"glowing"`/`"glow"` and
  `"gradient"`/`"gradients"` match, `"glove"`/`"glow"` does not.
- **Transient.** `StoryMemory` keeps the child's words verbatim; only the rendered text drops them.
  No contract change, and the filter is reversible if the style changes.

It **removes, never invents**, so invariant 2 below is untouched.

`permitted_words(value, style_fragment)` applies the same word-level rule to ONE string, and exists
for exactly one caller: `reveal._chips`, on the `species` axis (ADR-035 amendment, 2026-08-12).
`None` passes through; a value with nothing left returns `""`, which `_chips` drops as falsy.

**The distinction is describing versus offering, and it is the whole point of the split.**
`filtered_description` governs what the prompts *say* and leaves `species` alone — that carve-out is
what stops acceptance going vacuous. `permitted_words` governs what the child is *offered*, where a
forbidden species is a button that cannot work. Without it the two "never filter" carve-outs
(`species`, `notes`) composed into a bypass: a species chip became `char_bible._mint_targeted`'s
`notes` and put `"glowing orb"` back into a draw prompt under `"no glow"` on a fresh job. Do not
"simplify" this by folding `species` into `filtered_description`.

### `build_prompt`

Renders, for each character in `characters` whose `char_id` is in `characters_present`, the same
populated description axes `char_bible.reference_prompt` uses (`species`, `colours`, `body_features`,
`clothing`, `notes`) — consistent phrasing across the canonical reference and every scene prompt —
**each passed through `filtered_description` first (ADR-035)**. Then appends the verbatim
`text_excerpt` and the style fragment. `style_fragment=None` falls back to
`settings.default_style_fragment`, the same fallback `char_bible` already uses.

The filter is what stopped this function asserting an attribute the style clause in the same payload
forbade. Prod job `b9506307` emitted `the star - star; glowing; tiny` above a fragment ending
`no glow`, and the reference obeyed the fragment — so the scene's own noun described something
Image 2 visibly was not, and the edit model drew a second star (issue #23's `s1`). **`text_excerpt`
is not filtered**: ADR-013 freezes it verbatim, so a story that says "a tiny glowing star" still
says so.

### The image roll, guard clauses and `Setting:` line (issues #23, #32, scene-setting-and-subject-binding.md)

When at least one present character has a `canonical_ref_image`, `build_prompt` prefixes the prompt
with a roll naming each image in `referenced_characters` order and **folding that character's
description into the same sentence** — `"Image 1 is Ana - girl; red; jeans. Image 2 is the star -
tiny."` — followed by `REFERENCE_CLAUSE`. The fold is the D2 fix
(`scene-setting-and-subject-binding.md` §4.2): the reference image and its attributes are one
sentence rather than two blocks the model has to associate. A referenced character does **not** also
get a separate description line; a present character with no reference still does, below the roll.

Two further clauses sit **outside** `REFERENCE_CLAUSE`, because the roll and its clause are omitted
entirely on the text-to-image path and both guards must apply there too:

- `SUBJECT_COUNT_CLAUSE` — `"This illustration contains exactly N characters: Ana and the star."`
  A whole-canvas count, computed **after** the missing-`char_id` filter, singular at `N == 1`.
- `NON_HUMAN_CLAUSE` — wording from `char_bible.REFERENCE_PROMPT`, emitted unconditionally for the
  reason `char_bible` gives: branching on species needs a word list that is wrong the first time a
  child writes something not on it, and the clause is a no-op for a person.

Both are omitted when no present character survives the filter — all three blocks would reference
nothing.

A `Setting: <name> - <description>` line follows the guards and precedes `text_excerpt`, so on a
conflict the excerpt is the later and more specific assertion. `location=None` emits no line at all.
`filtered_location` is ADR-035 **surface 5**: the description is word-filtered against the style
fragment's own prohibitions; the **name** never is.

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

Two module-level constants close the holes where reason clauses alone append nothing (making the retry a pure resample, which ADR-010 rejects):

- `IDENTITY_CLAUSE = "the characters must match the reference images exactly"` — fires when `same_character=False` and `failure_reasons` is empty (i.e. the judge named the failure but gave no reason; anatomy is outside the frozen 7 so it has no FailureReason entry).
- `ANATOMY_CLAUSE = "anatomy must be correct: no merged, missing or duplicated body parts"` — fires when `anatomy_intact=False` (ADR-028 froze anatomy out of `FailureReason`; this is the only correction available).

Both params default to `True` so the four-positional-arg signature stays call-compatible.

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

### Edge cases

| Case | Behavior |
|---|---|
| **Empty `characters_present`** | `build_prompt` returns a character-free prompt: `text_excerpt` + style fragment only. Valid — `char_bible`'s and `segment`'s precedent is scenes may be unreferenced. |
| **`char_id` in `characters_present` not found in `state.characters`** | Skipped, logged. Same posture as `segment`'s "name not in roster" case — this function may not extend the roster. |
| **`style_fragment is None`** | Falls back to `settings.default_style_fragment`, matching `char_bible`. |
| **No present character has a canonical reference** | Image roll *and* the #32 binding sentence are both omitted — the text-to-image path sends no images to bind a name to. The semantic duplicate is therefore unaddressed on that path; with no reference, "twice" is barely defined. |
| **A character's name is a common noun the excerpt also uses** (`"the star"` in *"found a tiny glowing star"*) | The binding sentence ties the name to the reference and `_describe` suppresses the redundant species. `text_excerpt` is untouched either way — ADR-013 freezes it verbatim, so rewriting the prose to disambiguate is not available. |
| **`species` is an exact token of `name`** (`"the star"` / `"star"`) | Dropped from the description line, which floors to `"the star"` (or `"the star - tiny"` if another axis is populated). Exact token match, so `"the retriever"` / `"golden retriever"` keeps its species — the degenerate case this removes is identity, not resemblance. |
| **Two characters share a name** | `segment` maps one name to a list of `char_id`s, so the roll can read `"Image 1 is the star. Image 2 is the star."` and the binding sentence is correspondingly ambiguous. Pre-existing and not worsened here; no observed occurrence. |
| **Empty `failure_reasons`** | `correct_prompt` returns `prompt` unchanged when both booleans are `True`. With `same_character=False` it appends `IDENTITY_CLAUSE`; with `anatomy_intact=False` it appends `ANATOMY_CLAUSE`. |
| **Multiple `failure_reasons` on one attempt** | All matching clauses appended, in enum-declaration order, no duplicates even if a reason repeats. |
| **Every value on an axis is style-forbidden** (e.g. `colours == ["glowing"]` under `comic`) | ADR-035 filters it to empty, and the row below then applies — the clause appends with nothing rendered. Deliberate: restating the forbidden attribute is what made `wrong_colour` answer "match the reference's exact colours: glowing" (issue #24). |
| **A description axis referenced by a clause is empty** (e.g. `wrong_colour` but `colours == []`) | The clause still appends with an empty list rendered — this function does not invent colours that `analyze`/`char_bible` never captured; a thin description stays thin, same posture as `char_bible` §4's "species-only description" case. |

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
