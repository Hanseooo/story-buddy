# prompt-optimizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `backend/pipeline/prompt_optimizer.py` — two pure functions, `build_prompt` and
`correct_prompt` — and wire `build_prompt` into `generate_scene.py`, replacing its stub prompt line.

**Architecture:** Not a graph node. Two pure, deterministic string-construction functions plus one
module-level `FailureReason → clause template` dict, imported by `generate_scene` (today) and by the
unbuilt `regeneration-controller` (later, out of scope here). No LLM call, no contract change, no new
graph edge.

**Tech Stack:** Python 3.12, Pydantic (`contracts/story_memory.py`), pytest — same as every other
`backend/pipeline/` module.

## Global Constraints

- No `backend/contracts/` change. `Scene.prompt`, `Attempt.prompt`, and `FailureReason` already exist
  and are frozen (spec §2, ADR-023, ADR-028).
- Both functions are pure — no provider calls, no mocks in their tests (spec §6, following
  `char_bible.reference_prompt`'s precedent).
- `build_prompt` always includes the style fragment; falls back to `settings.default_style_fragment`
  when `style_fragment is None` (spec §4, matching `char_bible`).
- `build_prompt` never invents character detail beyond what `CharacterDescription` populated (spec
  invariant 2).
- `correct_prompt` never drops content from the prior prompt — only appends emphasis clauses (spec
  invariant 3).
- `correct_prompt`'s axis-based clauses (`wrong_colour`, `wrong_species`, `wrong_body_feature`,
  `wrong_clothing`) fill from **every** character passed in, joining multiple values — the
  attribution ceiling documented in spec §4 (`VlmVerdict` carries no per-character breakdown).
- Backend verify must be green and shown: `uv run ruff check . && uv run pytest` from `backend/`.
- `regeneration-controller` (unbuilt) is `correct_prompt`'s only future caller — do not wire it into
  any node in this change (spec §8).

### Spec-signature corrections (approved by the user before this plan was written)

The spec's §4 code snippet under-specifies both functions relative to its own prose and §6 tests.
This plan implements the corrected signatures below — **the spec's snippet should be corrected to
match in the same change** (Task 4):

- `build_prompt` gains a 4th parameter, `characters_present: list[str]`, inserted before
  `characters`. Spec §4 prose ("for each character in `characters` whose `char_id` is in
  `characters_present`") and the §6 node-level test ("`generate_scene` calls `build_prompt` with
  `(scene.text_excerpt, state.characters, ...)`" — the **full**, unfiltered roster) are only
  reconcilable if `build_prompt` itself does the `characters_present` join and skip-logs a missing
  `char_id`, which requires the list as an explicit parameter.
  **Corrected signature:** `build_prompt(text_excerpt: str, characters_present: list[str], characters: list[Character], style_fragment: str | None) -> str`
- `correct_prompt` gains a 4th parameter, `style_fragment: str | None`, appended at the end. The
  `wrong_style` clause is "the style fragment, restated" (spec §4 table) — restating requires the
  actual fragment text, which the 3-arg snippet has no way to supply.
  **Corrected signature:** `correct_prompt(prompt: str, failure_reasons: list[FailureReason], characters: list[Character], style_fragment: str | None) -> str`
- Ordering resolution for `correct_prompt`: spec §4 says "order preserved" (input-list order) but
  the §6 test says "enum-declaration order" for multiple reasons — these only agree once duplicates
  are dropped by construction. This plan iterates `FailureReason` in enum-declaration order and
  includes a clause only if that reason is present in the input list (a set membership check) —
  this produces enum-declaration order **and** collapses duplicates in one pass, satisfying both
  the ordering test and the dedup test without contradiction.

---

## File Structure

- **Create** `backend/pipeline/prompt_optimizer.py` — `build_prompt`, `correct_prompt`, the
  `FAILURE_CLAUSES` dict, and two private helpers (`_describe`, `_joined`). One file, matches the
  "one pipeline module = one file" rule (AGENTS.md) even though this module has no node.
- **Create** `backend/tests/test_prompt_optimizer.py` — pure-function tests for both functions, no
  mocks (mirrors `test_char_bible_node.py`'s pure-function section).
- **Modify** `backend/pipeline/generate_scene.py` — replace the `prompt = scene.caption or
  scene.text_excerpt` line with a `build_prompt(...)` call.
- **Modify** `backend/tests/test_generate_scene_node.py` — existing tests patch `build_prompt` to
  isolate node wiring (matching how `char_bible`'s node tests patch `mint_reference`); one new test
  asserts the exact call `generate_scene` makes to `build_prompt`.
- **Modify** `docs/specs/prompt-optimizer.md` — flip `Status: draft` → `built`, correct the §4
  signatures per the section above.
- **Modify** `docs/product/DECISION_BACKLOG.md`, `docs/WORKFLOW.md`, `AGENTS.md` — finding-change
  grep targets named in spec §9 item 6.

---

### Task 1: `build_prompt` (pure)

**Files:**
- Create: `backend/pipeline/prompt_optimizer.py`
- Test: `backend/tests/test_prompt_optimizer.py`

**Interfaces:**
- Consumes: `contracts.story_memory.Character`, `CharacterDescription` (existing); `app.config.settings.default_style_fragment` (existing).
- Produces: `build_prompt(text_excerpt: str, characters_present: list[str], characters: list[Character], style_fragment: str | None) -> str` — consumed by Task 3 (`generate_scene`). Also produces the private `_describe(description: CharacterDescription, name: str) -> str` helper (module-internal, not exported/reused by Task 2 — `correct_prompt` needs raw per-axis values, not a joined description line).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_prompt_optimizer.py`:

```python
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Character, CharacterDescription
from pipeline.prompt_optimizer import build_prompt

FRAG = "flat cel-shaded cartoon, thick clean black outlines"


def _char(char_id: str, name: str, **description_kwargs) -> Character:
    return Character(char_id=char_id, name=name, description=CharacterDescription(**description_kwargs))


def test_build_prompt_contains_every_populated_axis_for_each_present_character():
    dog = _char("c0", "the orange dog", species="dog", colours=["orange"], body_features=["three eyes"],
                clothing=["a red scarf"], notes="always smiling")
    prompt = build_prompt("The dog ran.", ["c0"], [dog], FRAG)
    for axis in ["dog", "orange", "three eyes", "a red scarf", "always smiling"]:
        assert axis in prompt


def test_build_prompt_always_contains_the_style_fragment():
    prompt = build_prompt("The dog ran.", [], [], FRAG)
    assert FRAG in prompt


def test_build_prompt_falls_back_to_the_default_style_fragment_when_none():
    from app.config import settings

    prompt = build_prompt("The dog ran.", [], [], None)
    assert settings.default_style_fragment in prompt


def test_build_prompt_always_contains_the_verbatim_text_excerpt():
    prompt = build_prompt("The dog ran across the yard.", [], [], FRAG)
    assert "The dog ran across the yard." in prompt


def test_build_prompt_with_empty_characters_present_is_text_excerpt_and_style_only():
    """Spec §4 edge case: valid — segment's and char_bible's precedent is scenes may be unreferenced."""
    prompt = build_prompt("The dog ran.", [], [], FRAG)
    assert prompt == "\n\n".join(["The dog ran.", FRAG])


def test_build_prompt_skips_a_char_id_not_found_in_characters():
    """Spec §4 edge case: same posture as segment's 'name not in roster' case — may not extend
    the roster, does not raise."""
    prompt = build_prompt("The dog ran.", ["c0", "missing-id"], [_char("c0", "the dog", species="dog")], FRAG)
    assert "dog" in prompt
    assert "missing-id" not in prompt


def test_build_prompt_never_invents_detail_for_an_empty_description():
    """Spec invariant 2: a character with no populated axes floors to just its name."""
    bare = _char("c0", "the mystery creature")
    prompt = build_prompt("It appeared.", ["c0"], [bare], FRAG)
    assert "the mystery creature" in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`): `uv run pytest tests/test_prompt_optimizer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.prompt_optimizer'`

- [ ] **Step 3: Write the implementation**

Create `backend/pipeline/prompt_optimizer.py`:

```python
"""Pure prompt-construction helpers (spec `docs/specs/prompt-optimizer.md`).

Two pure functions, no LLM call: `build_prompt` turns a scene into the text `generate_scene` sends
to the image model; `correct_prompt` turns a failed attempt's `failure_reasons` into emphasis
clauses appended to the prior prompt (ADR-010). Neither writes to `StoryMemory` itself — the
caller stores the return value.
"""
import logging

from app.config import settings
from contracts.story_memory import Character, CharacterDescription, FailureReason

log = logging.getLogger(__name__)


def _describe(description: CharacterDescription, name: str) -> str:
    """The populated CharacterDescription axes as one line — same phrasing char_bible's
    reference_prompt uses, so the canonical reference and every scene prompt describe the same
    character consistently."""
    axes = [
        description.species,
        ", ".join(description.colours),
        ", ".join(description.body_features),
        ", ".join(description.clothing),
        description.notes,
    ]
    populated = [axis for axis in axes if axis]
    return f"{name} - {'; '.join(populated)}" if populated else name


def build_prompt(
    text_excerpt: str,
    characters_present: list[str],
    characters: list[Character],
    style_fragment: str | None,
) -> str:
    """Pure. Always includes the style fragment (invariant 1); never invents detail beyond
    `text_excerpt` and the present characters' populated description axes (invariant 2)."""
    style = style_fragment or settings.default_style_fragment
    by_id = {character.char_id: character for character in characters}

    descriptions = []
    for char_id in characters_present:
        character = by_id.get(char_id)
        if character is None:
            log.warning("build_prompt: char_id %s not found in characters, skipping", char_id)
            continue
        descriptions.append(_describe(character.description, character.name))

    return "\n\n".join([*descriptions, text_excerpt, style])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_prompt_optimizer.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/prompt_optimizer.py backend/tests/test_prompt_optimizer.py
git commit -m "feat(pipeline): add build_prompt per prompt-optimizer spec"
```

---

### Task 2: `correct_prompt` (pure) + `FAILURE_CLAUSES`

**Files:**
- Modify: `backend/pipeline/prompt_optimizer.py`
- Test: `backend/tests/test_prompt_optimizer.py`

**Interfaces:**
- Consumes: `contracts.story_memory.FailureReason` (existing, 7-value closed enum); `Character` (Task 1).
- Produces: `correct_prompt(prompt: str, failure_reasons: list[FailureReason], characters: list[Character], style_fragment: str | None) -> str` and the module-level `FAILURE_CLAUSES: dict[FailureReason, str]` — consumed by the unbuilt `regeneration-controller`, not wired anywhere in this plan.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_prompt_optimizer.py`:

```python
from contracts.story_memory import FailureReason
from pipeline.prompt_optimizer import correct_prompt


def test_correct_prompt_wrong_colour_appends_the_documented_clause():
    dog = _char("c0", "the dog", colours=["orange", "white"])
    result = correct_prompt("base prompt", [FailureReason.wrong_colour], [dog], FRAG)
    assert "match the reference's exact colours: orange, white" in result


def test_correct_prompt_wrong_species_appends_the_documented_clause():
    dog = _char("c0", "the dog", species="dog")
    result = correct_prompt("base prompt", [FailureReason.wrong_species], [dog], FRAG)
    assert "the character is a dog, not anything else" in result


def test_correct_prompt_wrong_body_feature_appends_the_documented_clause():
    dog = _char("c0", "the dog", body_features=["three eyes"])
    result = correct_prompt("base prompt", [FailureReason.wrong_body_feature], [dog], FRAG)
    assert "match these body features exactly: three eyes" in result


def test_correct_prompt_wrong_clothing_appends_the_documented_clause():
    dog = _char("c0", "the dog", clothing=["a red scarf"])
    result = correct_prompt("base prompt", [FailureReason.wrong_clothing], [dog], FRAG)
    assert "match this clothing exactly: a red scarf" in result


def test_correct_prompt_wrong_style_restates_the_style_fragment():
    result = correct_prompt("base prompt", [FailureReason.wrong_style], [], FRAG)
    assert FRAG in result


def test_correct_prompt_wrong_style_falls_back_to_the_default_style_fragment():
    from app.config import settings

    result = correct_prompt("base prompt", [FailureReason.wrong_style], [], None)
    assert settings.default_style_fragment in result


def test_correct_prompt_different_face_appends_the_documented_clause():
    result = correct_prompt("base prompt", [FailureReason.different_face], [], FRAG)
    assert "match the reference character's face exactly" in result


def test_correct_prompt_character_absent_appends_the_documented_clause():
    dog = _char("c0", "the dog")
    result = correct_prompt("base prompt", [FailureReason.character_absent], [dog], FRAG)
    assert "make sure the dog is clearly visible in the scene" in result


def test_correct_prompt_multiple_reasons_all_appear_in_enum_declaration_order():
    result = correct_prompt(
        "base prompt", [FailureReason.character_absent, FailureReason.wrong_colour], [], FRAG
    )
    colour_clause = "match the reference's exact colours:"
    absent_clause = "is clearly visible in the scene"
    assert result.index(colour_clause) < result.index(absent_clause)


def test_correct_prompt_a_repeated_reason_produces_its_clause_once():
    result = correct_prompt(
        "base prompt", [FailureReason.different_face, FailureReason.different_face], [], FRAG
    )
    assert result.count("match the reference character's face exactly") == 1


def test_correct_prompt_two_characters_join_both_characters_colours():
    """Guards the attribution-ceiling behavior (spec §4): axis-based clauses fill from EVERY
    character, since VlmVerdict carries no per-character breakdown."""
    a = _char("c0", "the dog", colours=["orange"])
    b = _char("c1", "the cat", colours=["black"])
    result = correct_prompt("base prompt", [FailureReason.wrong_colour], [a, b], FRAG)
    assert "orange, black" in result


def test_correct_prompt_on_empty_failure_reasons_returns_the_prompt_unchanged():
    assert correct_prompt("base prompt", [], [], FRAG) == "base prompt"


def test_correct_prompt_never_alters_the_original_prompt_content():
    result = correct_prompt("base prompt", [FailureReason.wrong_colour], [], FRAG)
    assert result.startswith("base prompt")


def test_correct_prompt_an_empty_axis_still_appends_an_empty_clause():
    """Spec §4 edge case: does not invent colours analyze/char_bible never captured."""
    dog = _char("c0", "the dog", colours=[])
    result = correct_prompt("base prompt", [FailureReason.wrong_colour], [dog], FRAG)
    assert "match the reference's exact colours: " in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_prompt_optimizer.py -v`
Expected: FAIL with `ImportError: cannot import name 'correct_prompt'`

- [ ] **Step 3: Write the implementation**

Append to `backend/pipeline/prompt_optimizer.py`:

```python
def _joined(values) -> str:
    return ", ".join(value for value in values if value)


# ADR-004: the 7-value FailureReason set, frozen permanently per ADR-028.
FAILURE_CLAUSES: dict[FailureReason, str] = {
    FailureReason.wrong_colour: "match the reference's exact colours: {colours}",
    FailureReason.wrong_species: "the character is a {species}, not anything else",
    FailureReason.wrong_body_feature: "match these body features exactly: {body_features}",
    FailureReason.wrong_clothing: "match this clothing exactly: {clothing}",
    FailureReason.wrong_style: "{style_fragment}",
    FailureReason.different_face: "match the reference character's face exactly",
    FailureReason.character_absent: "make sure {name} is clearly visible in the scene",
}


def correct_prompt(
    prompt: str,
    failure_reasons: list[FailureReason],
    characters: list[Character],
    style_fragment: str | None,
) -> str:
    """Pure. Never drops content from `prompt` (invariant 3) — only appends emphasis clauses, one
    per `FailureReason` present in `failure_reasons`, in enum-declaration order, no duplicates.

    Attribution ceiling (spec §4): `VlmVerdict`/`Attempt.failure_reasons` carry no per-character
    breakdown, so axis-based clauses fill from EVERY character in `characters`, joining multiple
    values — over-specifying rather than guessing wrong.
    """
    style = style_fragment or settings.default_style_fragment
    values = {
        "colours": _joined(colour for character in characters for colour in character.description.colours),
        "species": _joined(character.description.species for character in characters),
        "body_features": _joined(
            feature for character in characters for feature in character.description.body_features
        ),
        "clothing": _joined(item for character in characters for item in character.description.clothing),
        "name": _joined(character.name for character in characters),
        "style_fragment": style,
    }
    present = set(failure_reasons)
    clauses = [FAILURE_CLAUSES[reason].format(**values) for reason in FailureReason if reason in present]
    return "\n".join([prompt, *clauses]) if clauses else prompt
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_prompt_optimizer.py -v`
Expected: PASS (all tests in the file, Task 1's 7 + Task 2's 14)

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/prompt_optimizer.py backend/tests/test_prompt_optimizer.py
git commit -m "feat(pipeline): add correct_prompt and FAILURE_CLAUSES per prompt-optimizer spec"
```

---

### Task 3: Wire `build_prompt` into `generate_scene`

**Files:**
- Modify: `backend/pipeline/generate_scene.py:1-28`
- Modify: `backend/tests/test_generate_scene_node.py`

**Interfaces:**
- Consumes: `pipeline.prompt_optimizer.build_prompt` (Task 1).
- Produces: no new interface — `generate_scene(state: StoryMemory) -> dict` keeps its existing partial-return shape (`scenes` key only).

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `backend/tests/test_generate_scene_node.py`:

```python
from unittest.mock import MagicMock, patch

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Input,
    Scene,
    Style,
    StoryMemory,
)
from pipeline.generate_scene import generate_and_store, generate_scene


def test_generate_and_store_uploads_image_bytes():
    fake_supabase = MagicMock()

    with patch("pipeline.generate_scene.text_to_image", return_value=b"fake-png-bytes"), \
         patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase):
        path = generate_and_store("a friendly dog", "job-123")

    assert path == "job-123/scene-1.png"
    fake_supabase.storage.from_.assert_called_with("storybook-images")
    fake_supabase.storage.from_.return_value.upload.assert_called_once()


def _state(scenes: list[Scene], characters: list[Character] | None = None, style: Style | None = None) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-123",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x"),
        characters=characters or [],
        style=style or Style(),
        scenes=scenes,
    )


def test_generate_scene_returns_a_partial_scene_update():
    """ADR-024: partial-return, not mutate-and-return. The node returns ONLY the scene it wrote."""
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="a friendly dog"), \
         patch("pipeline.generate_scene.generate_and_store", return_value="job-123/scene-1.png"):
        result = generate_scene(state)

    assert set(result) == {"scenes"}
    scene, = result["scenes"]
    assert scene.scene_id == "s0"
    assert scene.final_image_ref == "job-123/scene-1.png"
    assert scene.prompt == "a friendly dog"


def test_generate_scene_records_the_attempt_for_provenance():
    """CC-5: Scene.prompt alone loses per-attempt provenance once regeneration corrects it (ADR-010)."""
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="a friendly dog"), \
         patch("pipeline.generate_scene.generate_and_store", return_value="job-123/scene-1.png"):
        result = generate_scene(state)

    attempt, = result["scenes"][0].attempts
    assert attempt.image_ref == "job-123/scene-1.png"
    assert attempt.prompt == "a friendly dog"


def test_generate_scene_picks_the_first_scene_without_an_image():
    """ADR-024: loop position is derived from `final_image_ref is None` — there is no cursor."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="already.png"),
        Scene(scene_id="s1", text_excerpt="1"),
    ])

    with patch("pipeline.generate_scene.build_prompt", return_value="next"), \
         patch("pipeline.generate_scene.generate_and_store", return_value="job-123/scene-2.png"):
        result = generate_scene(state)

    scene, = result["scenes"]
    assert scene.scene_id == "s1"


def test_generate_scene_is_a_no_op_when_every_scene_has_an_image():
    state = _state([Scene(scene_id="s0", text_excerpt="0", final_image_ref="already.png")])

    with patch("pipeline.generate_scene.generate_and_store") as mock_store:
        result = generate_scene(state)

    assert result == {}
    mock_store.assert_not_called()


def test_generate_scene_calls_build_prompt_with_the_scenes_roster_and_style():
    """Spec §6: generate_scene calls build_prompt with (scene.text_excerpt,
    scene.characters_present, state.characters, state.style.prompt_fragment)."""
    dog = Character(char_id="c0", name="the dog", description=CharacterDescription(species="dog"))
    state = _state(
        [Scene(scene_id="s0", text_excerpt="The dog ran.", characters_present=["c0"])],
        characters=[dog],
        style=Style(prompt_fragment="flat gouache storybook"),
    )

    with patch("pipeline.generate_scene.build_prompt", return_value="built") as build, \
         patch("pipeline.generate_scene.generate_and_store", return_value="job-123/scene-1.png"):
        generate_scene(state)

    build.assert_called_once_with("The dog ran.", ["c0"], [dog], "flat gouache storybook")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_generate_scene_node.py -v`
Expected: FAIL — `test_generate_scene_calls_build_prompt_...` errors with `AttributeError` (no
`build_prompt` attribute on `pipeline.generate_scene` to patch yet); the other rewritten tests fail
their `scene.prompt` assertions because the node still builds the prompt from `scene.caption`.

- [ ] **Step 3: Write the implementation**

Replace `backend/pipeline/generate_scene.py:1-28` (everything up to and including the `prompt = ...`
line) — the rest of the function (the `generate_and_store` call and the return block) is unchanged:

```python
from app.db import get_supabase_client
from contracts.story_memory import Attempt, StoryMemory
from pipeline.prompt_optimizer import build_prompt
from providers import text_to_image

BUCKET = "storybook-images"


def generate_and_store(prompt: str, job_id: str) -> str:
    # ponytail: text-to-image, no character reference yet. Phase 1's char_bible node
    # produces the reference and this switches to providers.edit_image (ADR-007).
    image_bytes = text_to_image(prompt)

    path = f"{job_id}/scene-1.png"
    supabase = get_supabase_client()
    supabase.storage.from_(BUCKET).upload(
        path, image_bytes, {"content-type": "image/png", "upsert": "true"}
    )
    return path


def generate_scene(state: StoryMemory) -> dict:
    # ADR-024: loop position is the first scene with no final_image_ref — no cursor field.
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)
    if scene is None:
        return {}

    prompt = build_prompt(
        scene.text_excerpt, scene.characters_present, state.characters, state.style.prompt_fragment
    )
    path = generate_and_store(prompt, state.story_id)
    return {
        "scenes": [
            scene.model_copy(
                update={
                    "prompt": prompt,
                    # CC-5: the attempt carries the prompt THIS draw used; regeneration corrects
                    # Scene.prompt and would otherwise erase the provenance (ADR-010).
                    "attempts": [*scene.attempts, Attempt(image_ref=path, prompt=prompt, passed=True)],
                    "final_image_ref": path,
                }
            )
        ]
    }
```

Note: the DoD asks to remove "the *prompt* half" of the `# ponytail: text-to-image, no character
reference yet` comment. That comment (on `generate_and_store`) is entirely about the
`text_to_image` → `edit_image` swap — it never mentioned the prompt stub, so there is no prompt-half
text to strip. Leave the comment exactly as-is; only the `prompt = ...` line above it changes.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_generate_scene_node.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Run the full backend suite**

Run: `uv run pytest`
Expected: PASS, no regressions in other node tests (`char_bible`, `analyze`, `segment`, etc. are
untouched by this change).

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/generate_scene.py backend/tests/test_generate_scene_node.py
git commit -m "feat(pipeline): wire build_prompt into generate_scene, replacing the caption stub"
```

---

### Task 4: Spec status flip, finding-change grep, final verify

**Files:**
- Modify: `docs/specs/prompt-optimizer.md`
- Modify: `docs/product/DECISION_BACKLOG.md`
- Modify: `docs/WORKFLOW.md`
- Modify: `AGENTS.md`

**Interfaces:** none — documentation only.

- [ ] **Step 1: Get the commit range for Tasks 1–3**

Run: `git log --oneline -5`

Note the three commit hashes from Tasks 1–3 (first and last of the range) — used in Step 2.

- [ ] **Step 2: Update `docs/specs/prompt-optimizer.md`**

Edit line 3 from:
```
**Status:** draft · **Phase:** 1 · **Owner:** `backend/pipeline/prompt_optimizer.py` — **pure helpers, not a graph node**
```
to (substitute the real short hashes from Step 1):
```
**Status:** built · <first-hash>–<last-hash> · **Phase:** 1 · **Owner:** `backend/pipeline/prompt_optimizer.py` — **pure helpers, not a graph node**
```

Edit the §4 code block (lines 54-57) from:
```python
def build_prompt(text_excerpt: str, characters: list[Character], style_fragment: str | None) -> str
def correct_prompt(prompt: str, failure_reasons: list[FailureReason], characters: list[Character]) -> str
```
to:
```python
def build_prompt(text_excerpt: str, characters_present: list[str], characters: list[Character], style_fragment: str | None) -> str
def correct_prompt(prompt: str, failure_reasons: list[FailureReason], characters: list[Character], style_fragment: str | None) -> str
```

Add one sentence directly below that code block explaining the correction (matches "specs that lie
are worse than none", AGENTS.md):
```
(Corrected during implementation: `build_prompt` needs `characters_present` to do its own
characters_present → characters join per §4's own prose and the §6 node-level test, which passes
the full unfiltered roster; `correct_prompt` needs `style_fragment` to restate it for `wrong_style`.)
```

- [ ] **Step 3: Update `docs/product/DECISION_BACKLOG.md`**

Edit line 127 from:
```
- [ ] `prompt-optimizer`
```
to:
```
- [x] `prompt-optimizer`   *(spec **built 2026-07-31** — `docs/specs/prompt-optimizer.md`;
      `pipeline/prompt_optimizer.py` implements `build_prompt` (wired into `generate_scene`, replacing
      the caption stub) and `correct_prompt` (no caller yet — hands off to `regeneration-controller`).
      `contracts/` untouched.)*
```

Edit lines 183 and 188 (the "Recommended next session" block) from:
```
**Build `prompt-optimizer`** — write `docs/specs/prompt-optimizer.md` from `docs/specs/TEMPLATE.md` before any code (AGENTS.md).

**No open decision blocks Phase 1, and the backlog has no open rows.** Tiers 1, 2, 2b, 2c, and 3 are all
resolved. D-I closed 2026-07-31 → ADR-029; it builds in Phase 2 behind the char-ref moderation gate.

After `prompt-optimizer`, in roadmap order: `image-generator`, `consistency-checker`, `regeneration-controller`.
```
to:
```
> ✅ **`prompt-optimizer` is built (2026-07-31).** See `docs/specs/prompt-optimizer.md`.

**Build `image-generator`** — write `docs/specs/image-generator.md` from `docs/specs/TEMPLATE.md` before any code (AGENTS.md).

**No open decision blocks Phase 1, and the backlog has no open rows.** Tiers 1, 2, 2b, 2c, and 3 are all
resolved. D-I closed 2026-07-31 → ADR-029; it builds in Phase 2 behind the char-ref moderation gate.

After `image-generator`, in roadmap order: `consistency-checker`, `regeneration-controller`.
```

- [ ] **Step 4: Update `docs/WORKFLOW.md` §"Right now"**

Edit lines 115-116 from:
```
**Next action: `prompt-optimizer`** — write `docs/specs/prompt-optimizer.md` from `docs/specs/TEMPLATE.md`
before writing any code (AGENTS.md).
```
to:
```
`prompt-optimizer` is **built** (2026-07-31): `backend/pipeline/prompt_optimizer.py` — `build_prompt`
(wired into `generate_scene`, replacing the `scene.caption or scene.text_excerpt` stub) and
`correct_prompt` (no caller yet; hands off to `regeneration-controller`).

**Next action: `image-generator`** — write `docs/specs/image-generator.md` from `docs/specs/TEMPLATE.md`
before writing any code (AGENTS.md).
```

- [ ] **Step 5: Update `AGENTS.md` *Validation Notes***

Append one paragraph after the `character-bible`/`style-presets` paragraphs (before the closing of
that section, i.e. after the current final paragraph ending "Remaining Phase-1 specs:
`consistency-check`, `regeneration-controller`, `compose`."):

```
**`prompt-optimizer` is built (2026-07-31):** `pipeline/prompt_optimizer.py` — `build_prompt` (wired
into `generate_scene`, replacing the `caption`-stub prompt line) and `correct_prompt` (pure, no
caller yet — `regeneration-controller` wires it in when that spec lands). `contracts/` untouched.
Remaining Phase-1 specs: `image-generator`, `consistency-check`, `regeneration-controller`.
```

(This also replaces the now-stale "Remaining Phase-1 specs: `consistency-check`,
`regeneration-controller`, `compose`" sentence at the end of the `style-presets` paragraph — remove
it from there since it's superseded by the sentence above. Also note: `compose` is not a listed spec
in `docs/product/DECISION_BACKLOG.md`'s Phase 1 checklist — leave it out of the remaining-specs list
to match the backlog, don't reintroduce it.)

- [ ] **Step 6: Run the finding-change grep**

Run: `git grep -n "prompt-optimizer" -- docs AGENTS.md`

Confirm every remaining hit is either (a) a durable spec reference that's correct as-is (e.g.
`docs/MASTER_SPEC.md`'s Phase-1 spec list, `docs/specs/scene-segmentation.md`'s hand-off note — these
name the spec, not its status, and don't need edits) or (b) already updated in Steps 2-5. If a hit
still asserts `prompt-optimizer` as undone/next-action outside the four files above, fix it in this
same task.

- [ ] **Step 7: Run full backend verify**

Run (from `backend/`): `uv run ruff check . && uv run pytest`
Expected: both green. Paste the actual output when reporting completion — do not claim done without
showing it (AGENTS.md §4 Verification).

- [ ] **Step 8: Commit**

```bash
git add docs/specs/prompt-optimizer.md docs/product/DECISION_BACKLOG.md docs/WORKFLOW.md AGENTS.md
git commit -m "docs: flip prompt-optimizer to built, correct signatures, update status surface"
```

---

## Self-Review Notes

- **Spec coverage:** §4 `build_prompt` behavior → Task 1. §4 `correct_prompt` + clause table → Task
  2. §3 wiring into `generate_scene` → Task 3. §6 both pure-function test lists → Tasks 1-2. §6
  node-level test → Task 3 Step 1's `test_generate_scene_calls_build_prompt_with_the_scenes_roster_and_style`.
  §9 DoD items 1-3 → Tasks 1-3. §9 DoD item 4 (verify green) → Task 4 Step 7. §9 DoD item 5 (status
  flip) → Task 4 Step 2. §9 DoD item 6 (finding-change grep) → Task 4 Steps 3-6. §8 hand-offs
  (`correct_prompt` uncalled, `image-generator`'s provider swap out of scope) → deliberately not
  built anywhere in this plan; called out in Task 2 and Task 4 Step 3's DECISION_BACKLOG text.
- **Placeholder scan:** no TBD/TODO left in code or test steps; the one open placeholder
  (`<first-hash>–<last-hash>` in Task 4 Step 2) is deliberate — those hashes don't exist until Tasks
  1-3 are committed, and Task 4 Step 1 tells the executor exactly how to get them.
- **Type consistency:** `build_prompt`'s 4-arg signature and `correct_prompt`'s 4-arg signature are
  used identically across Task 1/2's implementation, Task 1/2's tests, and Task 3's
  `generate_scene.py` call site and its test's `build.assert_called_once_with(...)`.
