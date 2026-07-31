# Feature Spec — prompt-optimizer

**Status:** draft · **Phase:** 1 · **Owner:** `backend/pipeline/prompt_optimizer.py` — **pure helpers, not a graph node**
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
  2. `build_prompt` never fabricates content beyond `text_excerpt` and the present characters'
     populated description axes — it does not invent detail `analyze`/`char_bible` didn't produce.
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
- `correct_prompt` has **no caller yet**. `regeneration-controller` (unbuilt; next-but-one in roadmap
  order after `image-generator`) wires it in when that spec lands. Named here so it isn't reinvented
  differently there (ADR-010 already dictates its shape).
- No conditional edge. No contract change.

## 4. Behavior & edge cases

```python
def build_prompt(text_excerpt: str, characters: list[Character], style_fragment: str | None) -> str
def correct_prompt(prompt: str, failure_reasons: list[FailureReason], characters: list[Character]) -> str
```

### `build_prompt`

Renders, for each character in `characters` whose `char_id` is in `characters_present`, the same
populated description axes `char_bible.reference_prompt` uses (`species`, `colours`, `body_features`,
`clothing`, `notes`) — consistent phrasing across the canonical reference and every scene prompt. Then
appends the verbatim `text_excerpt` and the style fragment. `style_fragment=None` falls back to
`settings.default_style_fragment`, the same fallback `char_bible` already uses.

### `correct_prompt`

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
| **Empty `failure_reasons`** | `correct_prompt` returns `prompt` unchanged. Should never be invoked this way by its future caller, but no crash either way. |
| **Multiple `failure_reasons` on one attempt** | All matching clauses appended, in enum-declaration order, no duplicates even if a reason repeats. |
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
- **Wiring `correct_prompt` into a graph path** → `regeneration-controller` (unbuilt). This spec
  defines and tests the function; it has no caller until that spec lands.
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
