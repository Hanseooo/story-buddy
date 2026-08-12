# Scene Setting & Subject Binding — Part 2: `prompt_optimizer` + `generate_scene` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fold each reference image's attributes into its own roll sentence, add a whole-canvas subject count and a non-human anatomy guard on the scene path, emit a `Setting:` line from the scene's location, and stop `referenced_characters` from sending one image as two subjects.

**Architecture:** Two files change. `prompt_optimizer.build_prompt` gains a `location: Location | None` parameter and a new block order: folded roll → plain lines for reference-less present characters → the two guard clauses → `Setting:` → `text_excerpt` → style fragment. Both guard clauses sit **outside** `REFERENCE_CLAUSE`, because the roll and its clause are omitted entirely on the text-to-image path and both guards must still apply there. `generate_scene` resolves `scene.location_id` against `state.locations` and passes it through — two lines, no new effect.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, ruff, uv. No new dependencies.

**Source spec:** `docs/specs/scene-setting-and-subject-binding.md` (§4.2, §4.3, §6 tests 8–17).

**Depends on Part 1:** `Scene.location_id` must exist. Do not start until Part 1's exit criteria are met.

## Global Constraints

- Backend commands run from `backend/`: `uv run ruff check .` and `uv run pytest`.
- **Invariant 1 unchanged:** `build_prompt` always includes the style fragment.
- **Invariant 2 widens:** never invents detail beyond `text_excerpt`, the present characters' populated description axes, **and the scene's location**. This restatement is mandatory in `docs/specs/prompt-optimizer.md` — leaving it unwidened makes the spec lie.
- **Invariant 4 holds:** `referenced_characters` stays the single source of roll order across `generate_scene`, `regenerate` and `output_mod`. The **relative order of survivors is unchanged**; `dict.fromkeys` preserves first-seen order, so `"Image N is X"` still names `ref_paths[N-1]` on all three consumers.
- `location` is the **fifth** parameter of `build_prompt` and is **defaulted to `None`**, so the existing four-positional-arg calls in `test_regenerate_node.py` and `test_output_mod_node.py` stay call-compatible.
- **Zero new image calls, zero new judge calls.** `IMAGE_BUDGET` is untouched and cannot trip.
- **No new graph node and no new edge.** `backend/pipeline/graph.py` stays untouched.
- `regenerate.py` and `output_mod.py` are **not touched** — both wrap the stored prompt string and neither calls `build_prompt`. Their *tests* are updated, because they build a real prompt to pin the roll/`ref_paths` agreement.
- Deterministic tests only; every `providers.py` call is mocked.
- Every test must be seen **failing first**.

---

## File Structure

| File | Responsibility after this part |
|---|---|
| `backend/pipeline/prompt_optimizer.py` | +`filtered_location`, +`SUBJECT_COUNT_CLAUSE`, +`NON_HUMAN_CLAUSE`, +`_names`, folded roll, `location` parameter; `referenced_characters` deduplicates. |
| `backend/pipeline/generate_scene.py` | Resolves `scene.location_id` → `Location` and passes it to `build_prompt`. |
| `backend/tests/test_prompt_optimizer.py` | +10 new tests (§6 8–17); 1 pre-existing roll assertion updated. |
| `backend/tests/test_generate_scene_node.py` | +2 new tests; 1 pre-existing `assert_called_once_with` updated for the new arg. |
| `backend/tests/test_regenerate_node.py`, `backend/tests/test_output_mod_node.py` | Roll assertions updated to the folded shape. |
| `docs/specs/prompt-optimizer.md`, `docs/specs/image-generator.md` | Behavior changed → updated in the same change. |

---

## Task 1: `filtered_location` — ADR-035 surface 5

**Files:**
- Modify: `backend/pipeline/prompt_optimizer.py` (add after `filtered_description`, ~`:110`)
- Test: `backend/tests/test_prompt_optimizer.py`

**Interfaces:**
- Consumes: existing `style_prohibitions(style_fragment) -> set[str]` and `_filter_axis(values, forbidden) -> list[str]`.
- Produces: `filtered_location(location: Location | None, style_fragment: str | None) -> Location | None` — used by `build_prompt` in Task 4.

**Why it is a fifth ADR-035 surface:** a location description reaches the draw prompt exactly the way a character description does, and asserting `"glowing cave"` under a fragment ending `no glow` puts the prompt at war with itself — the same failure ADR-035 closed for character axes. The **name** is never filtered: it is what the child called the place, and it is the only thing left when the description is null.

- [ ] **Step 1: Write the failing tests**

Add `Location` to the `contracts.story_memory` import and `filtered_location` to the `pipeline.prompt_optimizer` import at the top of `backend/tests/test_prompt_optimizer.py`, then append:

```python
# --- ADR-035 surface 5: location descriptions (§6 test 15) ---

def test_filtered_location_drops_a_forbidden_word_from_the_description():
    """Same word-level rule as `_filter_axis`: the forbidden rendering property goes, the real
    subject fact stays."""
    filtered = filtered_location(
        Location(loc_id="loc0", name="the cave", description="glowing cave"), COMIC
    )
    assert filtered.description == "cave"


def test_filtered_location_never_touches_the_name():
    """The name is what the child called the place, and it is the whole `Setting:` line when the
    description is null. Filtering it could empty the line entirely."""
    filtered = filtered_location(
        Location(loc_id="loc0", name="the glowing cave", description="glowing cave"), COMIC
    )
    assert filtered.name == "the glowing cave"


def test_filtered_location_drops_a_description_with_nothing_left():
    filtered = filtered_location(
        Location(loc_id="loc0", name="the cave", description="glowing"), COMIC
    )
    assert filtered.description is None


def test_filtered_location_leaves_a_permitted_description_alone():
    location = Location(loc_id="loc0", name="the beach", description="golden sand, palm trees")
    assert filtered_location(location, COMIC) == location


def test_filtered_location_passes_none_through():
    assert filtered_location(None, COMIC) is None


def test_filtered_location_handles_a_null_description():
    location = Location(loc_id="loc0", name="the beach")
    assert filtered_location(location, COMIC) == location
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_prompt_optimizer.py -k filtered_location -v`
Expected: FAIL at import — `ImportError: cannot import name 'filtered_location'`.

- [ ] **Step 3: Write the minimal implementation**

In `backend/pipeline/prompt_optimizer.py`, add `Location` to the contracts import:

```python
from contracts.story_memory import Character, CharacterDescription, FailureReason, Location
```

and add after `filtered_description`:

```python
def filtered_location(location: Location | None, style_fragment: str | None) -> Location | None:
    """Pure, transient — ADR-035 surface 5. A location description reaches the draw prompt the way
    a character description does, so `"glowing cave"` under a fragment ending `no glow` puts the
    prompt at war with itself. Word-level, like the list axes.

    The NAME is deliberately never filtered: it is what the child called the place, and when the
    description is null it is the entire `Setting:` line. Removes, never invents, so invariant 2
    is untouched.
    """
    if location is None or location.description is None:
        return location
    forbidden = style_prohibitions(style_fragment)
    if not forbidden:
        return location
    kept = _filter_axis([location.description], forbidden)
    return location.model_copy(update={"description": kept[0] if kept else None})
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_prompt_optimizer.py -k filtered_location -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check .
git add backend/pipeline/prompt_optimizer.py backend/tests/test_prompt_optimizer.py
git commit -m "feat(prompt-optimizer): filter location descriptions (ADR-035 surface 5)"
```

---

## Task 2: The roll fold — the whole D2 fix

**Files:**
- Modify: `backend/pipeline/prompt_optimizer.py:188-219` (`build_prompt`)
- Test: `backend/tests/test_prompt_optimizer.py`, `backend/tests/test_regenerate_node.py:214`, `backend/tests/test_output_mod_node.py:123`

**Interfaces:**
- Consumes: existing `_describe(description, name) -> str`, `filtered_description`, `referenced_characters`.
- Produces: the roll sentence shape `f"Image {n} is {_describe(...)}."`. `_describe` is **unchanged**.

**Why:** today the roll (`"Image 1 is Ana."`) and the attribute line (`"Ana - girl; red; jeans"`) are separate blocks the model must associate, and a model that fails to associate them dresses one subject in another's attributes. Folded, each reference image and its attributes are one sentence. This is a **net token reduction** — the only change in this spec that reduces prompt dilution rather than adding to it, and the only one reversible inside a single function.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_prompt_optimizer.py`:

```python
# --- §4.2 D2: the roll fold (§6 tests 8-11) ---

def test_the_roll_folds_the_description_into_the_image_sentence():
    """§6 test 8. Today the roll and the attribute line are two unbound blocks; folded, each
    reference image and its attributes are one sentence."""
    ana = _char("c0", "Ana", species="girl", colours=["red"], clothing=["jeans"])
    ana.canonical_ref_image = "job-123/ref-c0-1.png"

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "Image 1 is Ana - girl; red; jeans." in prompt


def test_the_roll_of_a_character_with_no_populated_axes_is_byte_identical_to_before():
    """§6 test 9. `_describe` floors to the bare name, so `"Image 1 is Ana."` is unchanged."""
    ana = _char("c0", "Ana")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "Image 1 is Ana." in prompt


def test_a_present_character_with_no_reference_keeps_a_plain_line_below_the_roll():
    """§6 test 10. It has no image number to fold into, so it keeps the description line it has
    always had — and the line must appear AFTER the roll, not before it."""
    ana = _char("c0", "Ana", species="girl")                 # no canonical reference
    star = _char("c1", "the star", body_features=["tiny"])
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    prompt = build_prompt("Ana held the star.", ["c0", "c1"], [ana, star], FRAG)

    assert "Image 1 is the star - tiny." in prompt
    assert prompt.index("Image 1 is") < prompt.index("Ana - girl")


def test_a_referenced_character_is_described_once_and_only_in_the_roll():
    """The fold REPLACES the separate attribute line — emitting both would restore the two
    unbound blocks this change exists to remove, at double the tokens."""
    ana = _char("c0", "Ana", species="girl")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert prompt.count("Ana - girl") == 1


def test_the_roll_order_still_matches_referenced_characters_order():
    """§6 test 11 / invariant 4. `generate_scene`, `regenerate` and `output_mod` all index
    `ref_paths` against this roll, so a reorder here silently lies on three nodes."""
    ana = _char("c0", "Ana", species="girl")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"
    star = _char("c1", "the star", body_features=["tiny"])
    star.canonical_ref_image = "job-123/ref-c1-1.png"
    characters = [ana, star]

    prompt = build_prompt("She held it up.", ["c1", "c0"], characters, FRAG)
    order = [c.name for c in referenced_characters(["c1", "c0"], characters)]

    assert order == ["the star", "Ana"]
    assert prompt.index("Image 1 is the star") < prompt.index("Image 2 is Ana")


def test_the_reference_clause_still_follows_the_roll():
    """The clause is the antecedent-supplier for the generic "one of these characters" binding;
    the fold must not detach it from the roll."""
    ana = _char("c0", "Ana", species="girl")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "Image 1 is Ana - girl. Use them only as references" in prompt
```

Then update the **one** pre-existing test that asserts the unfolded roll,
`test_build_prompt_names_each_reference_image_by_index` (`test_prompt_optimizer.py:67-78`):

```python
def test_build_prompt_names_each_reference_image_by_index():
    """Issue #23: the payload sent prose plus ANONYMOUS image_urls, so the edit model composited
    both references into the canvas instead of using them as identity conditioning. Since
    scene-setting-and-subject-binding §4.2 each name carries its own attributes (the roll fold)."""
    ana = _char("c0", "Ana", species="girl")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"
    star = _char("c1", "the star", species="star")
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    prompt = build_prompt("She held it toward the sky.", ["c0", "c1"], [ana, star], FRAG)

    assert "Image 1 is Ana - girl." in prompt
    assert "Image 2 is the star." in prompt      # species repeats the name → dropped (issue #32)
```

And the two cross-node roll pins, which build a **real** prompt:

`backend/tests/test_regenerate_node.py:214` — the helper `_char` gives every character
`species="dog", colours=["orange"]`, so the fold reads:

```python
    assert "Image 1 is the dog - orange." in store.call_args.args[0]
    assert "Image 2 is the star - dog; orange." in store.call_args.args[0]
    assert store.call_args.args[4] == ["job-1/ref-c0.png", "job-1/ref-c2.png"]
```

`backend/tests/test_output_mod_node.py:123` — its local `_char` gives `species="dog"` and no
colours:

```python
    assert "Image 1 is the dog." in mock_gen.call_args.args[0]
    assert "Image 2 is the star - dog." in mock_gen.call_args.args[0]
    assert mock_gen.call_args.args[4] == ["job-1/ref-c0.png", "job-1/ref-c2.png"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_prompt_optimizer.py tests/test_regenerate_node.py tests/test_output_mod_node.py -k "roll or image_index or ref_paths_agree" -v`
Expected: FAIL — the roll still reads `"Image 1 is Ana."` with the attributes in a separate block.

- [ ] **Step 3: Write the minimal implementation**

Replace the body of `build_prompt` in `backend/pipeline/prompt_optimizer.py` (keep the signature as it is for now — Task 4 adds the `location` parameter):

```python
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

    # `dict.fromkeys` mirrors segment's dedup (§4.3) so a checkpoint written before that change
    # cannot reproduce a doubled subject on resume. Order-preserving — invariant 4.
    present: list[Character] = []
    for char_id in dict.fromkeys(characters_present):
        character = by_id.get(char_id)
        if character is None:
            log.warning("build_prompt: char_id %s not found in characters, skipping", char_id)
            continue
        present.append(character)

    # Omitted entirely on the text-to-image path (`generate_scene:55-57` sends no images), where
    # naming images that were never sent would be a lie the model has to reconcile.
    referenced = referenced_characters(characters_present, characters)
    referenced_ids = {character.char_id for character in referenced}

    # §4.2 THE ROLL FOLD — the whole D2 fix. The image and its attributes are ONE sentence, so the
    # model has nothing left to associate. Net token reduction: the separate attribute line for a
    # referenced character is not emitted below. A character with no populated axes yields
    # "Image 1 is Ana." — byte-identical to before the fold.
    roll = [
        " ".join(
            f"Image {n} is "
            f"{_describe(filtered_description(character.description, style), character.name)}."
            for n, character in enumerate(referenced, 1)
        )
        + " "
        + REFERENCE_CLAUSE
    ] if referenced else []

    # ADR-035 surface 3. Issue #23's `s1`: this line asserted "glowing" while `style` below
    # forbade it and the reference obeyed `style`, so the edit model saw the scene's noun
    # describing something Image 2 visibly was not, and drew a second one.
    descriptions = [
        _describe(filtered_description(character.description, style), character.name)
        for character in present
        if character.char_id not in referenced_ids
    ]

    return "\n\n".join([*roll, *descriptions, text_excerpt, style])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_prompt_optimizer.py tests/test_regenerate_node.py tests/test_output_mod_node.py -v`
Expected: PASS, all three files green.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check .
git add backend/pipeline/prompt_optimizer.py backend/tests/test_prompt_optimizer.py backend/tests/test_regenerate_node.py backend/tests/test_output_mod_node.py
git commit -m "feat(prompt-optimizer): fold each reference's attributes into its roll sentence (D2)"
```

---

## Task 3: The two guard clauses — subject count and non-human anatomy

**Files:**
- Modify: `backend/pipeline/prompt_optimizer.py` (constants near `REFERENCE_CLAUSE`, `~:180`; `build_prompt`)
- Test: `backend/tests/test_prompt_optimizer.py`

**Interfaces:**
- Consumes: the `present` list built in Task 2 (post missing-`char_id` filter).
- Produces: module constants `SUBJECT_COUNT_CLAUSE` (a `.format` template taking `n`, `plural`, `names`) and `NON_HUMAN_CLAUSE` (a fixed string); helper `_names(names: list[str]) -> str`.

**Both clauses sit OUTSIDE `REFERENCE_CLAUSE`.** The roll and its clause are omitted entirely on the text-to-image path (`prompt_optimizer.py:212-217`) and both guards must apply there too — placing them inside would make them silently inert on every reference-less scene.

`NON_HUMAN_CLAUSE` is emitted **unconditionally**, for the same reason `char_bible` made its version unconditional: branching on species needs a word list that is wrong the first time a child writes something not on it, and the clause is a no-op for a person.

`SUBJECT_COUNT_CLAUSE` is a **whole-canvas** count, structurally different from the per-character *"draw each character exactly once"* already inside `REFERENCE_CLAUSE`.

- [ ] **Step 1: Write the failing tests**

Add `NON_HUMAN_CLAUSE` and `SUBJECT_COUNT_CLAUSE` to the `pipeline.prompt_optimizer` import, then append to `backend/tests/test_prompt_optimizer.py`:

```python
# --- §4.2 D2: the two guard clauses (§6 tests 12-14) ---

def _referenced(char_id: str, name: str, **kwargs) -> Character:
    character = _char(char_id, name, **kwargs)
    character.canonical_ref_image = f"job-123/ref-{char_id}-1.png"
    return character


def test_the_subject_count_clause_names_every_present_character():
    ana = _referenced("c0", "Ana", species="girl")
    star = _referenced("c1", "the star", body_features=["tiny"])

    prompt = build_prompt("She held it up.", ["c0", "c1"], [ana, star], FRAG)

    assert "This illustration contains exactly 2 characters: Ana and the star." in prompt


def test_both_guard_clauses_appear_on_the_reference_path():
    """§6 test 12, first half."""
    ana = _referenced("c0", "Ana", species="girl")

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "This illustration contains exactly 1 character: Ana." in prompt
    assert NON_HUMAN_CLAUSE in prompt


def test_both_guard_clauses_appear_on_the_text_to_image_path():
    """§6 test 12, second half — the load-bearing half. The roll and REFERENCE_CLAUSE are omitted
    when no character has a reference, so a guard placed INSIDE the clause would be silently inert
    on every reference-less scene."""
    ana = _char("c0", "Ana", species="girl")               # no canonical reference

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "Image 1" not in prompt
    assert "This illustration contains exactly 1 character: Ana." in prompt
    assert NON_HUMAN_CLAUSE in prompt


def test_the_count_reads_one_character_singular():
    """§6 test 13, second half: no `1 characters`."""
    ana = _referenced("c0", "Ana", species="girl")

    prompt = build_prompt("Ana waved.", ["c0"], [ana], FRAG)

    assert "1 characters" not in prompt


def test_the_count_is_computed_after_the_missing_char_id_filter():
    """§6 test 13, first half. A char_id absent from `characters` is already warned + skipped, so
    counting before the filter asserts a number the prompt does not name."""
    ana = _referenced("c0", "Ana", species="girl")

    prompt = build_prompt("Ana waved.", ["c0", "ghost-id"], [ana], FRAG)

    assert "This illustration contains exactly 1 character: Ana." in prompt
    assert "ghost-id" not in prompt


def test_a_present_character_without_a_reference_is_still_counted():
    """§4.2 edge case: it keeps a plain description line and still occupies a subject slot."""
    ana = _char("c0", "Ana", species="girl")               # no reference
    star = _referenced("c1", "the star", body_features=["tiny"])

    prompt = build_prompt("Ana held the star.", ["c0", "c1"], [ana, star], FRAG)

    assert "This illustration contains exactly 2 characters: Ana and the star." in prompt


def test_the_count_names_three_characters_with_a_serial_comma_free_join():
    ana = _referenced("c0", "Ana", species="girl")
    star = _referenced("c1", "the star", body_features=["tiny"])
    bird = _referenced("c2", "the bird", species="bird")

    prompt = build_prompt("They met.", ["c0", "c1", "c2"], [ana, star, bird], FRAG)

    assert "exactly 3 characters: Ana, the star and the bird." in prompt


def test_no_clause_at_all_when_characters_present_is_empty():
    """§6 test 14 / §4.2 edge case: no roll, no count clause, no non-human clause — all three
    would reference nothing."""
    prompt = build_prompt("The waves crashed.", [], [], FRAG)

    assert "Image 1" not in prompt
    assert "This illustration contains exactly" not in prompt
    assert NON_HUMAN_CLAUSE not in prompt
    assert prompt == "\n\n".join(["The waves crashed.", FRAG])


def test_no_clause_at_all_when_every_char_id_is_missing_from_the_roster():
    """The filter can empty the list even when `characters_present` was not empty."""
    prompt = build_prompt("The waves crashed.", ["ghost-id"], [], FRAG)

    assert "This illustration contains exactly" not in prompt
    assert NON_HUMAN_CLAUSE not in prompt


def test_the_guard_clauses_sit_after_the_descriptions_and_before_the_excerpt():
    ana = _char("c0", "Ana", species="girl")

    prompt = build_prompt("Ana waved at the sea.", ["c0"], [ana], FRAG)

    assert prompt.index("Ana - girl") < prompt.index("This illustration contains")
    assert prompt.index(NON_HUMAN_CLAUSE) < prompt.index("Ana waved at the sea.")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_prompt_optimizer.py -k "guard or count or clause_at_all" -v`
Expected: FAIL at import — `ImportError: cannot import name 'NON_HUMAN_CLAUSE'`.

- [ ] **Step 3: Write the minimal implementation**

In `backend/pipeline/prompt_optimizer.py`, add after `REFERENCE_CLAUSE`:

```python
# §4.2. BOTH clauses below sit OUTSIDE REFERENCE_CLAUSE deliberately: the roll and its clause are
# omitted entirely on the text-to-image path (`generate_scene:55-57` sends no images), and both
# guards must apply there too. Inside, they would be silently inert on every ref-less scene.

# A WHOLE-CANVAS count, structurally different from REFERENCE_CLAUSE's per-character "draw each
# character exactly once": that one constrains each subject, this one constrains the canvas. D3(b)
# residual duplication is compositing, and a canvas-level assertion is the only shape that can
# contradict it.
SUBJECT_COUNT_CLAUSE = "This illustration contains exactly {n} character{plural}: {names}."

# Wording from `char_bible.REFERENCE_PROMPT` (prod job 4cb31620 drew "the star" as a smiling mascot
# with arms and legs), scoped to the scene path and closed with "unless described above".
# UNCONDITIONAL, for the reason char_bible gives: branching on species needs a word list that is
# wrong the first time a child writes something not on it, and this is a no-op for a person.
NON_HUMAN_CLAUSE = (
    "If a character is not a person, draw it as the kind of thing it actually is — give it no "
    "human body and no human face unless described above."
)


def _names(names: list[str]) -> str:
    """"Ana" / "Ana and the star" / "Ana, the star and the bird"."""
    if len(names) < 2:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"
```

Then in `build_prompt`, between `descriptions` and the return, add:

```python
    # Emitted only when there is a subject to count — all three clauses would otherwise reference
    # nothing. The count is computed from `present`, i.e. AFTER the missing-char_id filter above,
    # or it asserts a number the prompt does not name.
    guards = ["\n".join([
        SUBJECT_COUNT_CLAUSE.format(
            n=len(present),
            plural="" if len(present) == 1 else "s",
            names=_names([character.name for character in present]),
        ),
        NON_HUMAN_CLAUSE,
    ])] if present else []

    return "\n\n".join([*roll, *descriptions, *guards, text_excerpt, style])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_prompt_optimizer.py -v`
Expected: PASS, whole file green.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check .
git add backend/pipeline/prompt_optimizer.py backend/tests/test_prompt_optimizer.py
git commit -m "feat(prompt-optimizer): add subject-count and non-human guard clauses"
```

---

## Task 4: The `Setting:` line and the `location` parameter

**Files:**
- Modify: `backend/pipeline/prompt_optimizer.py` (`build_prompt` signature and body)
- Test: `backend/tests/test_prompt_optimizer.py`

**Interfaces:**
- Consumes: `filtered_location` (Task 1).
- Produces: `build_prompt(text_excerpt, characters_present, characters, style_fragment, location: Location | None = None) -> str`. `generate_scene` supplies the fifth argument in Task 6.

**Placement is load-bearing:** the setting line is emitted **before** the `text_excerpt`, so the excerpt is the later and more specific assertion when the two conflict (`"that night"` against a sunny description). §4.5.3 records this as *reduced*, not eliminated.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_prompt_optimizer.py`:

```python
# --- §4.1 D1: the Setting line (§6 tests 15-16) ---

def test_build_prompt_emits_a_setting_line_from_the_location():
    location = Location(loc_id="loc0", name="the beach", description="golden sand, palm trees")

    prompt = build_prompt("She ran.", [], [], FRAG, location)

    assert "Setting: the beach - golden sand, palm trees" in prompt


def test_build_prompt_emits_a_name_only_setting_line_when_the_description_is_null():
    """§4.1: `ExtractedLocation.description` stays optional, and name-only is still better than
    today's nothing."""
    prompt = build_prompt("She ran.", [], [], FRAG, Location(loc_id="loc0", name="the beach"))

    assert "Setting: the beach" in prompt
    assert "Setting: the beach -" not in prompt


def test_build_prompt_emits_no_setting_line_without_a_location():
    """§6 test 16 — the default, and the whole behaviour for a story that names no place."""
    prompt = build_prompt("She ran.", [], [], FRAG)

    assert "Setting:" not in prompt


def test_the_setting_line_is_style_filtered_but_keeps_its_name():
    """§6 test 15 through `build_prompt`, not just the helper."""
    location = Location(loc_id="loc0", name="the glowing cave", description="glowing cave")

    prompt = build_prompt("She went in.", [], [], COMIC, location)

    assert "Setting: the glowing cave - cave" in prompt


def test_the_setting_line_precedes_the_text_excerpt():
    """§4.1 edge case: on a conflict ("that night" vs a sunny description) the excerpt must be the
    LATER and more specific assertion. Reduced, not eliminated (§4.5.3)."""
    location = Location(loc_id="loc0", name="the beach", description="golden sand")

    prompt = build_prompt("That night it was dark.", [], [], FRAG, location)

    assert prompt.index("Setting: the beach") < prompt.index("That night it was dark.")


def test_the_setting_line_follows_the_guard_clauses():
    ana = _char("c0", "Ana", species="girl")
    location = Location(loc_id="loc0", name="the beach", description="golden sand")

    prompt = build_prompt("Ana ran.", ["c0"], [ana], FRAG, location)

    assert prompt.index(NON_HUMAN_CLAUSE) < prompt.index("Setting: the beach")


def test_the_style_fragment_is_still_last_with_a_location_present():
    """Invariant 1, pinned against the new block."""
    location = Location(loc_id="loc0", name="the beach", description="golden sand")

    prompt = build_prompt("She ran.", [], [], FRAG, location)

    assert prompt.endswith(FRAG)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_prompt_optimizer.py -k "setting or style_fragment_is_still_last" -v`
Expected: FAIL — `TypeError: build_prompt() takes 4 positional arguments but 5 were given`.

- [ ] **Step 3: Write the minimal implementation**

Change the signature and docstring of `build_prompt`:

```python
def build_prompt(
    text_excerpt: str,
    characters_present: list[str],
    characters: list[Character],
    style_fragment: str | None,
    location: Location | None = None,
) -> str:
    """Pure. Always includes the style fragment (invariant 1); never invents detail beyond
    `text_excerpt`, the present characters' populated description axes, and the scene's location
    (invariant 2, widened by `scene-setting-and-subject-binding.md` §2).

    `location` is defaulted so the four-positional-arg call stays compatible; the one production
    caller (`generate_scene.py:77`) always passes it.
    """
```

Add the setting block just before the return:

```python
    # Emitted BEFORE the excerpt on purpose: when a location description and the excerpt conflict
    # ("that night" against a sunny description), the excerpt is then the later and more specific
    # assertion. Reduced, not eliminated (§4.5.3).
    place = filtered_location(location, style)
    setting = [
        f"Setting: {place.name} - {place.description}" if place.description
        else f"Setting: {place.name}"
    ] if place else []

    return "\n\n".join([*roll, *descriptions, *guards, *setting, text_excerpt, style])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_prompt_optimizer.py -v`
Expected: PASS, whole file green.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check .
git add backend/pipeline/prompt_optimizer.py backend/tests/test_prompt_optimizer.py
git commit -m "feat(prompt-optimizer): emit a Setting line from the scene's location (D1)"
```

---

## Task 5: `referenced_characters` deduplicates — the defensive half of D3(a)

**Files:**
- Modify: `backend/pipeline/prompt_optimizer.py:141-158`
- Test: `backend/tests/test_prompt_optimizer.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `referenced_characters` returns at most one `Character` per `char_id`, **in unchanged relative order**. All three consumers (`generate_scene`, `regenerate`, `output_mod`) inherit the fix without a line changing in any of them.

**Why here as well as in `segment`:** Part 1 fixed the *source*. A checkpoint written **before** Part 1 still carries a duplicated `char_id` in `characters_present`, and on resume it would hand fal the same Storage path twice, `_fal_ref_url`'s cache would return the same fal URL twice, and the roll would assert *"Image 1 is the star. Image 2 is the star."* — one image presented as two subjects, which is exactly how a second instance at a different scale appears.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_prompt_optimizer.py`:

```python
# --- §4.3 D3(a): the defensive half (§6 test 17) ---

def test_referenced_characters_deduplicates_a_repeated_char_id():
    """§6 test 17. `segment` no longer emits one, but a checkpoint written before that change
    still can — and `_fal_ref_url`'s cache would return the SAME fal URL twice, so the roll would
    say "Image 1 is the star. Image 2 is the star." over a single image."""
    star = _char("c1", "the star")
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    assert [c.char_id for c in referenced_characters(["c1", "c1"], [star])] == ["c1"]


def test_referenced_characters_keeps_the_relative_order_of_the_survivors():
    """Invariant 4: `dict.fromkeys` preserves first-seen order, so removing a duplicate cannot
    reorder the survivors that "Image N is X" is indexed against on three nodes."""
    ana = _char("c0", "Ana")
    ana.canonical_ref_image = "job-123/ref-c0-1.png"
    star = _char("c1", "the star")
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    got = referenced_characters(["c1", "c0", "c1"], [ana, star])

    assert [c.name for c in got] == ["the star", "Ana"]


def test_the_roll_numbers_a_repeated_char_id_only_once():
    """The end-to-end shape of the bug: one image, one number, one subject."""
    star = _char("c1", "the star", body_features=["tiny"])
    star.canonical_ref_image = "job-123/ref-c1-1.png"

    prompt = build_prompt("It shone.", ["c1", "c1"], [star], FRAG)

    assert "Image 1 is the star - tiny." in prompt
    assert "Image 2" not in prompt
    assert "This illustration contains exactly 1 character: the star." in prompt
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_prompt_optimizer.py -k "deduplicates or relative_order or repeated_char_id" -v`
Expected: FAIL — `assert ['c1', 'c1'] == ['c1']`. (The third test's count assertion may already pass, because `build_prompt` dedups `characters_present` for `present` in Task 2; the `"Image 2" not in prompt` assertion is the one that fails.)

- [ ] **Step 3: Write the minimal implementation**

In `referenced_characters`, change the iteration source to a deduplicated one:

```python
    by_id = {character.char_id: character for character in characters}
    return [
        character
        # §4.3 D3(a), defensive half. `segment` no longer emits a duplicate, but a checkpoint
        # written before that change can, and `_fal_ref_url`'s cache would hand fal the same URL
        # twice. `dict.fromkeys` is order-preserving, so the survivors keep their relative order
        # and "Image N is X" still names `ref_paths[N-1]` on all three consumers (invariant 4).
        for char_id in dict.fromkeys(characters_present)
        if (character := by_id.get(char_id)) is not None and character.canonical_ref_image
    ]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_prompt_optimizer.py tests/test_regenerate_node.py tests/test_output_mod_node.py tests/test_generate_scene_node.py -v`
Expected: PASS, all four files green.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check .
git add backend/pipeline/prompt_optimizer.py backend/tests/test_prompt_optimizer.py
git commit -m "fix(prompt-optimizer): deduplicate char_ids in referenced_characters (#23 D3a)"
```

---

## Task 6: `generate_scene` passes the location, and the two specs are updated

**Files:**
- Modify: `backend/pipeline/generate_scene.py:65-90`
- Modify: `docs/specs/prompt-optimizer.md`, `docs/specs/image-generator.md`
- Test: `backend/tests/test_generate_scene_node.py`

**Interfaces:**
- Consumes: `Scene.location_id` (Part 1 Task 1), `build_prompt(..., location)` (Task 4).
- Produces: nothing new downstream. `scenes[].prompt` is the same field with new content.

- [ ] **Step 1: Write the failing tests**

First update the pre-existing signature assertion at `backend/tests/test_generate_scene_node.py:231`:

```python
    build.assert_called_once_with("The dog ran.", ["c0"], [dog], "flat gouache storybook", None)
```

and widen its docstring to name the fifth argument. Then append:

```python
def test_generate_scene_resolves_the_scenes_location_and_passes_it_to_build_prompt():
    """§4.1: `segment` writes `location_id`; this node is the only place it is resolved back to
    the `Location` object `build_prompt` needs."""
    beach = Location(loc_id="loc0", name="the beach", description="golden sand")
    hill = Location(loc_id="loc1", name="the hill", description="tall grass")
    state = _state([Scene(scene_id="s0", text_excerpt="She ran.", location_id="loc1")])
    state = state.model_copy(update={"locations": [beach, hill]})

    with patch("pipeline.generate_scene.build_prompt", return_value="built") as build, \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)):
        generate_scene(state)

    assert build.call_args.args[4] == hill


def test_generate_scene_passes_none_when_the_scene_has_no_location():
    state = _state([Scene(scene_id="s0", text_excerpt="She ran.")])

    with patch("pipeline.generate_scene.build_prompt", return_value="built") as build, \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)):
        generate_scene(state)

    assert build.call_args.args[4] is None


def test_generate_scene_passes_none_for_a_location_id_absent_from_the_roster():
    """Same posture as every other roster lookup in this pipeline: this node may not extend the
    roster, and it does not raise. The page ships with no `Setting:` line."""
    beach = Location(loc_id="loc0", name="the beach")
    state = _state([Scene(scene_id="s0", text_excerpt="She ran.", location_id="ghost-loc")])
    state = state.model_copy(update={"locations": [beach]})

    with patch("pipeline.generate_scene.build_prompt", return_value="built") as build, \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)):
        generate_scene(state)

    assert build.call_args.args[4] is None
```

Add `Location` to the `contracts.story_memory` import at the top of the file.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_generate_scene_node.py -k "location or build_prompt_with_the_scenes_roster" -v`
Expected: FAIL — `IndexError: tuple index out of range` on `build.call_args.args[4]`, and the updated `assert_called_once_with` reports the four-argument call.

- [ ] **Step 3: Write the minimal implementation**

In `backend/pipeline/generate_scene.py`, replace the `build_prompt` call:

```python
    # §4.1: `segment` wrote the id; this is the one place it is resolved back to the object.
    # A `location_id` absent from the roster resolves to None and the page simply gets no
    # `Setting:` line — the same posture as every other roster lookup in this pipeline.
    location = next((loc for loc in state.locations if loc.loc_id == scene.location_id), None)

    prompt = build_prompt(
        scene.text_excerpt,
        scene.characters_present,
        state.characters,
        state.style.prompt_fragment,
        location,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_generate_scene_node.py -v`
Expected: PASS, whole file green.

- [ ] **Step 5: Update `docs/specs/prompt-optimizer.md`**

Three edits, all required:

1. **Invariant 2 (`prompt-optimizer.md:29`) must be restated to name the location** — leaving it unwidened makes the spec lie:

```markdown
  2. `build_prompt` never fabricates content beyond `text_excerpt`, the present characters'
     populated description axes, **and the scene's location** (`Location.name`, plus
     `Location.description` when populated — widened by `scene-setting-and-subject-binding.md` §2).
```

2. **The signature (`prompt-optimizer.md:53`):**

```python
def build_prompt(text_excerpt: str, characters_present: list[str], characters: list[Character], style_fragment: str | None, location: Location | None = None) -> str
```

3. **The prompt shape section (around `prompt-optimizer.md:120`)** — replace the description of the unfolded roll with:

```markdown
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
```

4. Add the new §6 tests (8–17) to the spec's deterministic-test list.

- [ ] **Step 6: Update `docs/specs/image-generator.md`**

At `image-generator.md:86`, update the `build_prompt` call:

```markdown
3. `build_prompt(scene.text_excerpt, scene.characters_present, state.characters,
   state.style.prompt_fragment, location)` — where `location` is `state.locations` looked up by
   `scene.location_id`, or `None` when the scene has no location or the id is absent from the
   roster (`scene-setting-and-subject-binding.md` §4.1).
```

And add to the edge-case table:

```markdown
| **`location_id` present but absent from `state.locations`** | Resolves to `None`, no `Setting:` line. Same posture as `build_prompt` and `segment` — this node may not extend the roster. |
```

At `image-generator.md:154`, the note about `build_prompt`'s call signature now reads five arguments.

- [ ] **Step 7: Full verify and commit**

```bash
cd backend && uv run ruff check . && uv run pytest
git add backend/pipeline/generate_scene.py backend/tests/test_generate_scene_node.py docs/specs/prompt-optimizer.md docs/specs/image-generator.md
git commit -m "feat(generate-scene): resolve and pass the scene's location to build_prompt"
```

---

## Part 2 exit criteria

- [ ] `cd backend && uv run ruff check . && uv run pytest` — green, output shown.
- [ ] `git diff backend/pipeline/graph.py` is empty.
- [ ] `git diff backend/pipeline/regenerate.py backend/pipeline/output_mod.py` is empty — neither node changed, only their tests.
- [ ] Spec §6 tests **8–17** all exist and pass; every one was seen failing first.
- [ ] `grep -rn "Image 1 is" backend/ docs/` finds no assertion of the **unfolded** roll shape.
- [ ] `docs/specs/prompt-optimizer.md` invariant 2 explicitly names the location.
- [ ] `docs/specs/image-generator.md` records the five-argument `build_prompt` call.

Proceed to Part 3.
