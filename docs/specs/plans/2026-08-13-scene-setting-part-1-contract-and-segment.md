# Scene Setting & Subject Binding — Part 1: Contract + `analyze` + `segment` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the two additive Story Memory fields, teach `analyze` to describe locations by what is permanently there, and make `segment` mint `scenes[].location_id` and stop emitting duplicate `char_id`s.

**Architecture:** Three files change. `contracts/story_memory.py` gains `Scene.location_id` and `VlmVerdict.subjects_unique` — both `Optional`/defaulted, so **no `schema_version` bump** (`story-memory-contract.md` §8; precedent `VlmVerdict.anatomy_intact`). `analyze.EXTRACTION_PROMPT` gains one sentence. `segment` gains a boundary field `ExtractedScene.location_name`, a location roster in `SEGMENTATION_PROMPT`, a name → `loc_id` mapping with carry-forward, and a `char_id` dedup — plus `location_name` propagation through **all eight** `ExtractedScene(...)` construction sites.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, ruff, uv. No new dependencies.

**Source spec:** `docs/specs/scene-setting-and-subject-binding.md` (§2, §4.1, §4.3, §6 tests 1–7 and 22).

**Sibling plans:** Part 2 (`prompt_optimizer` + `generate_scene`), Part 3 (`consistency_check`). Part 1 must land first — Parts 2 and 3 both read fields this part creates.

## Global Constraints

- Backend commands run from `backend/`: `uv run ruff check .` and `uv run pytest`. Never bare `pip`/`poetry`; never `python` without `uv run`.
- **No `schema_version` bump.** `CURRENT_SCHEMA_VERSION` stays `1`. Both new fields are additive with defaults.
- **`VlmVerdict` field order is load-bearing** (ADR-004, enforced on the wire by `providers._assert_field_order`). `subjects_unique` is declared **LAST**, after `anatomy_intact`. No existing field moves.
- **No new graph node and no new edge** (ADR-003). `backend/pipeline/graph.py` must be untouched by all three parts.
- Deterministic tests only: every `providers.py` call is mocked. Never assert on generated content quality.
- Behavior change → the module's spec in `docs/specs/` is updated **in the same change** (AGENTS.md).
- Surgical changes only: do not reformat, rename, or "improve" adjacent code. `ruff format` is **not** adopted in this repo.
- Every test must be seen **failing first** before its implementation is written.
- Commit after each task.

---

## File Structure

| File | Responsibility after this part |
|---|---|
| `backend/contracts/story_memory.py` | +`Scene.location_id`, +`VlmVerdict.subjects_unique`. Nothing else. |
| `backend/tests/test_story_memory.py` | +4 contract assertions (defaults, order, old-blob deserialization). |
| `backend/pipeline/analyze.py` | +1 sentence in `EXTRACTION_PROMPT`. `ExtractedLocation.description` stays `str \| None`. |
| `backend/tests/test_analyze_node.py` | +1 assertion that the sentence is in the prompt. |
| `backend/pipeline/segment.py` | +`ExtractedScene.location_name`, location roster in the prompt, 8 constructor sites propagating it, name→`loc_id` map + carry-forward, `char_id` dedup. |
| `backend/tests/test_segment_node.py` | +8 constructor-site assertions, +merge rule, +5 node-level location tests, +2 dedup tests, +1 roster-in-prompt test; 3 `segment_scenes` call sites updated for the new arg. |
| `docs/specs/story-analyzer.md` | Records the new extraction sentence. |
| `docs/specs/scene-segmentation.md` | Records `location_name`, carry-forward, dedup. |

---

## Task 1: Contract — two additive fields

**Files:**
- Modify: `backend/contracts/story_memory.py:113-123` (`VlmVerdict`), `:134-144` (`Scene`)
- Test: `backend/tests/test_story_memory.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Scene.location_id: Optional[str]` (written by `segment` in Task 5, read by `generate_scene` in Part 2); `VlmVerdict.subjects_unique: bool` defaulting to `True` (written by `consistency_check` in Part 3).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_story_memory.py`:

```python
# --- scene-setting-and-subject-binding §2: two additive fields, no schema_version bump ---

def test_scene_location_id_defaults_to_none():
    """Set by `segment`, consumed by `build_prompt`. A story that names no location leaves it
    None on every scene, which is byte-identical to today's behaviour."""
    assert Scene(scene_id="s0", text_excerpt="x").location_id is None


def test_vlm_verdict_subjects_unique_defaults_to_true():
    """CC-10: a scene judged BEFORE this change reads as non-duplicated. Same shape
    `anatomy_intact` had at its own introduction."""
    assert VlmVerdict(differences_observed="d", same_character=True).subjects_unique is True


def test_vlm_verdict_declares_subjects_unique_last():
    """ADR-004's reason-then-score order is enforced on the wire by
    `providers._assert_field_order`. The new field is appended; nothing above it moves."""
    assert list(VlmVerdict.model_fields) == [
        "differences_observed",
        "same_character",
        "attributes_present",
        "style_match",
        "anatomy_intact",
        "subjects_unique",
    ]


def test_a_checkpoint_blob_written_before_this_change_still_deserializes():
    """§6 test 22 / CC-10: both fields are additive with defaults, so a checkpoint that predates
    them resumes with the documented values rather than raising."""
    blob = _minimal().model_dump()
    blob["scenes"] = [
        {
            "scene_id": "s0",
            "text_excerpt": "x",
            "attempts": [
                {
                    "image_ref": "job-1/s0-1.png",
                    "vlm_verdict": {"differences_observed": "d", "same_character": True},
                }
            ],
        }
    ]

    restored = StoryMemory.model_validate(blob)

    assert restored.scenes[0].location_id is None
    assert restored.scenes[0].attempts[0].vlm_verdict.subjects_unique is True


def test_the_two_additive_fields_do_not_bump_the_schema_version():
    """§2: `story-memory-contract.md` §8 permits additive defaulted fields without a bump."""
    assert CURRENT_SCHEMA_VERSION == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_story_memory.py -k "location_id or subjects_unique or checkpoint_blob_written_before" -v`
Expected: FAIL — `AttributeError: 'Scene' object has no attribute 'location_id'` and `'VlmVerdict' object has no attribute 'subjects_unique'`.

- [ ] **Step 3: Write the minimal implementation**

In `backend/contracts/story_memory.py`, inside `VlmVerdict`, append after `anatomy_intact`:

```python
    subjects_unique: bool = True       # scene-setting-and-subject-binding §4.4: each character
                                       # drawn exactly once. Declared LAST so ADR-004's order above
                                       # is untouched. Additive → no schema_version bump. Recorded
                                       # and RANKED (ADR-010) but does NOT gate — `passed` stays
                                       # `same_character and anatomy_intact`. Gating is blocked on a
                                       # measured duplicate rate and issue #26 (spec §8.1).
```

In `Scene`, add after `characters_present`:

```python
    location_id: Optional[str] = None                            # set by `segment`, consumed by `build_prompt`
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_story_memory.py -v`
Expected: PASS, whole file green.

- [ ] **Step 5: Mirror the fields into the contract spec if it enumerates them**

Run: `cd backend && grep -n "anatomy_intact" ../docs/specs/story-memory-contract.md`

If the file enumerates `VlmVerdict`'s fields (it names `anatomy_intact` as the additive-field precedent), add `subjects_unique` and `Scene.location_id` beside it in the same style, pointing at `scene-setting-and-subject-binding.md`. If the grep returns nothing, skip this step and say so.

- [ ] **Step 6: Lint and commit**

```bash
cd backend && uv run ruff check . && uv run pytest
git add backend/contracts/story_memory.py backend/tests/test_story_memory.py docs/specs/story-memory-contract.md
git commit -m "feat(contracts): add Scene.location_id and VlmVerdict.subjects_unique (additive)"
```

---

## Task 2: `analyze` — describe locations by what is permanently there

**Files:**
- Modify: `backend/pipeline/analyze.py:71-86` (`EXTRACTION_PROMPT`)
- Modify: `docs/specs/story-analyzer.md`
- Test: `backend/tests/test_analyze_node.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: no signature change. `ExtractedLocation.description` **stays `str | None`** — making it required would force invention, contradicting the same prompt's rule for character axes.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_analyze_node.py`:

```python
def test_extraction_prompt_asks_for_permanent_location_detail():
    """§4.1 D1: a location description that names weather or time of day contradicts the
    excerpt of every OTHER page set in the same place, because one description repeats onto
    all of them."""
    from pipeline.analyze import EXTRACTION_PROMPT

    assert (
        "Describe each location by what is permanently there — not the weather, the time of "
        "day, or what happens there." in EXTRACTION_PROMPT
    )


def test_extracted_location_description_stays_optional():
    """§4.1: required would force invention, contradicting the same prompt's rule for character
    axes ("leave them empty rather than inventing details"). Null degrades the setting line to
    name-only, which is still better than today's nothing."""
    from pipeline.analyze import ExtractedLocation

    assert ExtractedLocation(name="the beach").description is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_analyze_node.py -k "permanent_location or description_stays_optional" -v`
Expected: FAIL on the first test with `assert ... in EXTRACTION_PROMPT`. The second passes already — it is a pin, not a change.

- [ ] **Step 3: Write the minimal implementation**

In `backend/pipeline/analyze.py`, replace the line

```python
Locations and objects: whatever the story mentions.
```

with

```python
Locations and objects: whatever the story mentions. Describe each location by what is permanently
there — not the weather, the time of day, or what happens there.
```

⚠️ The assertion above matches a single-line string. Keep the sentence on **one** line inside the prompt (the prompt is a plain `"""..."""` literal, so a line break inside it becomes a real newline in the string). If ruff's line-length rule objects, split the assertion in the test instead of the prompt — do **not** reflow the prompt text.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_analyze_node.py -v`
Expected: PASS.

- [ ] **Step 5: Update `docs/specs/story-analyzer.md`**

Find the section describing `EXTRACTION_PROMPT` / the locations rule and add:

```markdown
`EXTRACTION_PROMPT` asks for locations to be described by **what is permanently there** — not the
weather, the time of day, or what happens there (`scene-setting-and-subject-binding.md` §4.1).
`ExtractedLocation.description` stays `str | None`: requiring it would force invention, which
contradicts the same prompt's rule for character axes. A null description degrades the downstream
`Setting:` line to name-only.
```

- [ ] **Step 6: Lint and commit**

```bash
cd backend && uv run ruff check . && uv run pytest
git add backend/pipeline/analyze.py backend/tests/test_analyze_node.py docs/specs/story-analyzer.md
git commit -m "feat(analyze): ask for permanent location detail in EXTRACTION_PROMPT"
```

---

## Task 3: `segment` — `location_name` survives all eight constructor sites

**Files:**
- Modify: `backend/pipeline/segment.py:20-24` (`ExtractedScene`), `:66-137` (`repair`), `:140-175` (`merge_thin`)
- Test: `backend/tests/test_segment_node.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `ExtractedScene.location_name: str | None = None` — read by Task 4's node mapping.

**Why this task comes before the node mapping:** `repair` reconstructs **every** scene in its clamp step, so a node-level location test would fail for the wrong reason if propagation is not in place first.

**The eight sites** (spec §4.1, current line numbers): `:76` clamp, `:89` de-overlap, `:97` floor, `:103` leading gap, `:109` interior gap, `:113` trailing gap, `:133` `MAX_SCENES` merge, `:170` `merge_thin`. The floor site constructs with `characters_present=[]` and correctly gets `location_name=None` — carry-forward supplies `locations[0]` later.

- [ ] **Step 1: Write the failing tests**

First, update the existing `_r` helper in `backend/tests/test_segment_node.py:75-76`:

```python
def _r(
    start: int, end: int, chars: list[str] | None = None, location: str | None = None
) -> ExtractedScene:
    return ExtractedScene(
        start=start, end=end, characters_present=chars or [], location_name=location
    )
```

Then append this block (place it after the existing `repair` tests):

```python
# --- §6 test 4: location_name survives all EIGHT ExtractedScene construction sites ---
# One assertion per site. A missed site silently drops the field on exactly the messy stories
# that need repair most, and no pre-existing test would catch it.

def test_location_name_survives_the_clamp_site():
    assert repair([_r(-5, 100, location="the beach")], 5)[0].location_name == "the beach"


def test_location_name_survives_the_de_overlap_site():
    result = repair([_r(0, 3, location="the beach"), _r(2, 4, location="the hill")], 5)
    assert result[1].start == 4                      # this one WAS reconstructed by de-overlap
    assert result[1].location_name == "the hill"


def test_the_floor_site_constructs_with_no_location_name():
    """The whole-story floor invents a range; it must not invent a location either. Carry-forward
    supplies `locations[0]` at the node."""
    assert repair([_r(9, 3, location="the beach")], 5)[0].location_name is None


def test_location_name_survives_the_leading_gap_fill_site():
    assert repair([_r(2, 4, location="the beach")], 5)[0].location_name == "the beach"


def test_location_name_survives_the_interior_gap_fill_site():
    result = repair([_r(0, 1, location="the beach"), _r(3, 4, location="the hill")], 5)
    assert result[0].end == 2                        # the interior gap closed onto scene 0
    assert result[0].location_name == "the beach"


def test_location_name_survives_the_trailing_gap_fill_site():
    result = repair([_r(0, 2, location="the beach")], 5)
    assert result[0].end == 4                        # the trailing gap closed onto scene 0
    assert result[0].location_name == "the beach"


def test_location_name_survives_the_max_scenes_merge_site():
    """16 single-unit scenes → exactly one merge, and ties go to the earliest pair, so scenes
    0 and 1 fuse."""
    scenes = [_r(i, i) for i in range(16)]
    scenes[1] = _r(1, 1, location="the hill")

    result = repair(scenes, 16)

    assert len(result) == 15
    assert result[0].location_name == "the hill"     # `a.location_name or b.location_name`


def test_location_name_survives_the_merge_thin_site():
    units = _units(2, 3, 20, 20)
    result = merge_thin(
        [_r(0, 0, location="the beach"), _r(1, 1, location="the hill"), _r(2, 2), _r(3, 3)], units
    )
    assert result[0].location_name == "the beach"


# --- §6 test 5: the merge rule itself ---

def test_a_merge_takes_the_first_scenes_location_when_both_have_one():
    """`a.location_name or b.location_name` — the earlier scene wins, which is the same
    earlier-scene-wins policy de-overlap already uses."""
    scenes = [_r(i, i) for i in range(16)]
    scenes[0] = _r(0, 0, location="the beach")
    scenes[1] = _r(1, 1, location="the hill")

    assert repair(scenes, 16)[0].location_name == "the beach"


def test_merge_thin_takes_the_first_scenes_location_when_both_have_one():
    units = _units(2, 3, 20, 20)
    result = merge_thin(
        [_r(0, 0, location="the beach"), _r(1, 1, location="the hill"), _r(2, 2), _r(3, 3)], units
    )
    assert result[0].location_name == "the beach"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_segment_node.py -k "location_name or floor_site" -v`
Expected: FAIL — `ExtractedScene` has no field `location_name`; Pydantic raises on the unexpected kwarg in `_r`.

- [ ] **Step 3: Write the minimal implementation**

In `backend/pipeline/segment.py`, add the field to `ExtractedScene`:

```python
class ExtractedScene(BaseModel):
    start: int                        # inclusive index into the numbered units
    end: int                          # inclusive
    characters_present: list[str]     # Character.name values — node maps to char_ids
    location_name: str | None = None  # Location.name value — node maps to a loc_id, null → inherit
```

Then thread `location_name` through every reconstruction in `repair`:

```python
            clamped.append(ExtractedScene(
                start=start, end=end,
                characters_present=s.characters_present, location_name=s.location_name,
            ))
```

```python
            deoverlapped.append(ExtractedScene(
                start=new_start, end=s.end,
                characters_present=s.characters_present, location_name=s.location_name,
            ))
```

The floor site is left **as it is** — it constructs with `characters_present=[]` and no
`location_name`, which defaults to `None`:

```python
        return [ExtractedScene(start=0, end=n - 1, characters_present=[])]
```

```python
        deoverlapped[0] = ExtractedScene(
            start=0, end=first.end,
            characters_present=first.characters_present, location_name=first.location_name,
        )
```

```python
            deoverlapped[i] = ExtractedScene(
                start=curr.start, end=nxt.start - 1,
                characters_present=curr.characters_present, location_name=curr.location_name,
            )
```

```python
        deoverlapped[-1] = ExtractedScene(
            start=last.start, end=n - 1,
            characters_present=last.characters_present, location_name=last.location_name,
        )
```

```python
        merged_chars = list(dict.fromkeys(a.characters_present + b.characters_present))
        deoverlapped = (
            deoverlapped[:best_idx]
            + [ExtractedScene(
                start=a.start, end=b.end,
                characters_present=merged_chars,
                location_name=a.location_name or b.location_name,
            )]
            + deoverlapped[best_idx + 2:]
        )
```

And in `merge_thin`:

```python
        merged[left : left + 2] = [ExtractedScene(
            start=a.start,
            end=b.end,
            characters_present=list(dict.fromkeys(a.characters_present + b.characters_present)),
            location_name=a.location_name or b.location_name,
        )]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_segment_node.py -v`
Expected: PASS, whole file green (the pre-existing `repair`/`merge_thin` tests must stay green — `location_name` defaults to `None` everywhere they do not set it).

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check .
git add backend/pipeline/segment.py backend/tests/test_segment_node.py
git commit -m "feat(segment): carry location_name through all eight ExtractedScene constructions"
```

---

## Task 4: `segment` — roster, name → `loc_id` mapping, carry-forward

**Files:**
- Modify: `backend/pipeline/segment.py:30-63` (`SEGMENTATION_PROMPT`, `segment_scenes`), `:178-205` (`segment`)
- Test: `backend/tests/test_segment_node.py`

**Interfaces:**
- Consumes: `ExtractedScene.location_name` (Task 3), `Scene.location_id` (Task 1).
- Produces: `segment_scenes(units, characters, timeline, locations) -> SceneSegmentation` — **a fourth required positional parameter**. `segment` writes `scenes[].location_id`.

**Carry-forward rule (spec §4.1), applied over the final scene list in order:**
- `location_name` null → inherit the previous scene's `location_id`
- a name not in the roster → warn, treat as null, so carry-forward fills it
- `s0` null → `locations[0].loc_id` if any, else `None`
- consequence: every scene null → all inherit `locations[0]` (one setting for the book, the honest degradation)

- [ ] **Step 1: Write the failing tests**

Update the existing `_state` helper in `backend/tests/test_segment_node.py:204-218` to accept locations:

```python
def _state(
    raw: str = "The dog ran. He found a ball.",
    redacted: str | None = None,
    characters: list | None = None,
    timeline: list | None = None,
    locations: list | None = None,
) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="t1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text=raw, redacted_text=redacted),
        characters=characters or [],
        timeline=timeline or [],
        locations=locations or [],
    )
```

Add `Location` to the `contracts.story_memory` import at the top of the file, add `import logging`, and append:

```python
_LOCS = [
    Location(loc_id="loc0", name="the beach", description="golden sand"),
    Location(loc_id="loc1", name="the hill", description="tall grass"),
]


def _seg(*locations: str | None) -> SceneSegmentation:
    """One single-unit scene per argument, each carrying that `location_name`."""
    return SceneSegmentation(scenes=[
        ExtractedScene(start=i, end=i, characters_present=[], location_name=name)
        for i, name in enumerate(locations)
    ])


# --- §6 test 1: name → loc_id, unknown name dropped with a warning ---

def test_segment_maps_a_location_name_to_its_loc_id():
    with patch("pipeline.segment.segment_scenes", return_value=_seg("the beach", "the hill")):
        result = segment(_state(locations=_LOCS))

    assert [s.location_id for s in result["scenes"]] == ["loc0", "loc1"]


def test_segment_warns_and_drops_a_location_name_not_in_the_roster(caplog):
    """Same posture as the character path: this node may not extend the roster, and it does not
    raise. Carry-forward then fills the hole."""
    with caplog.at_level(logging.WARNING), \
         patch("pipeline.segment.segment_scenes", return_value=_seg("the beach", "Atlantis")):
        result = segment(_state(locations=_LOCS))

    assert "Atlantis" in caplog.text
    assert result["scenes"][1].location_id == "loc0"


# --- §6 test 2: carry-forward ---

def test_segment_carries_the_previous_scenes_location_forward_over_a_null():
    with patch("pipeline.segment.segment_scenes", return_value=_seg("the hill", None, None)):
        result = segment(_state(raw="One. Two. Three.", locations=_LOCS))

    assert [s.location_id for s in result["scenes"]] == ["loc1", "loc1", "loc1"]


def test_segment_does_not_carry_a_location_backwards():
    """Carry-forward only. A leading null takes `locations[0]`, not the location named later."""
    with patch("pipeline.segment.segment_scenes", return_value=_seg(None, "the hill")):
        result = segment(_state(locations=_LOCS))

    assert [s.location_id for s in result["scenes"]] == ["loc0", "loc1"]


# --- §6 test 3: the s0 floor, and the no-locations case ---

def test_segment_gives_a_null_first_scene_the_first_location():
    with patch("pipeline.segment.segment_scenes", return_value=_seg(None, None)):
        result = segment(_state(locations=_LOCS))

    assert [s.location_id for s in result["scenes"]] == ["loc0", "loc0"]


def test_segment_leaves_every_location_id_none_when_the_story_names_no_location():
    """Edge case: identical to today — no `Setting:` line will be emitted downstream."""
    with patch("pipeline.segment.segment_scenes", return_value=_seg(None, None)):
        result = segment(_state(locations=[]))

    assert [s.location_id for s in result["scenes"]] == [None, None]


# --- the roster reaches the prompt ---

def test_segment_scenes_puts_the_location_roster_in_the_prompt():
    units = ["The dog ran.", "He found a ball."]
    stub = SceneSegmentation(scenes=[ExtractedScene(start=0, end=1, characters_present=[])])
    with patch("pipeline.segment.structured_text", return_value=stub) as mock_provider:
        segment_scenes(units, [], [], _LOCS)

    prompt = mock_provider.call_args.args[0]
    assert "the beach" in prompt
    assert "the hill" in prompt


def test_segment_scenes_says_none_when_the_story_has_no_locations():
    stub = SceneSegmentation(scenes=[ExtractedScene(start=0, end=0, characters_present=[])])
    with patch("pipeline.segment.structured_text", return_value=stub) as mock_provider:
        segment_scenes(["A story."], [], [], [])

    assert "Locations in the story: (none)" in mock_provider.call_args.args[0]


def test_segment_passes_the_state_locations_to_segment_scenes():
    stub = SceneSegmentation(scenes=[ExtractedScene(start=0, end=1, characters_present=[])])
    with patch("pipeline.segment.segment_scenes", return_value=stub) as mock_seg:
        segment(_state(locations=_LOCS))

    assert mock_seg.call_args.args[3] == _LOCS
```

Also update the **two pre-existing** `segment_scenes` call sites for the new fourth argument:
- `test_segment_scenes_passes_numbered_units_and_schema_to_provider` → `segment_scenes(units, [], [], [])`
- `test_segment_scenes_returns_parsed_wrapper_unchanged` → `segment_scenes(units, [], [], [])`

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_segment_node.py -k "location" -v`
Expected: FAIL — `segment_scenes() takes 3 positional arguments but 4 were given`, and `Scene.location_id` is `None` where a `loc0`/`loc1` was asserted.

- [ ] **Step 3: Write the minimal implementation**

In `backend/pipeline/segment.py`, add `Location` to the contracts import:

```python
from contracts.story_memory import Character, Location, Scene, StoryMemory, TimelineEvent
```

Replace `SEGMENTATION_PROMPT` with:

```python
SEGMENTATION_PROMPT = """\
Split this story into picture-book pages (scenes). Return index ranges — do not copy or \
paraphrase any sentence.

Numbered story sentences:
{numbered}

Characters in the story: {roster}

Locations in the story: {locations}

Story plot points:
{plot}

Rules:
- At most 15 scenes.
- Each scene captures a distinct moment or plot point.
- start and end are inclusive sentence indices.
- characters_present lists character names exactly as given above.
- location_name is where the scene happens, named exactly as given above. Leave it null if the \
story does not say.
- Together the scenes must cover every sentence."""
```

Widen `segment_scenes`:

```python
def segment_scenes(
    units: list[str],
    characters: list[Character],
    timeline: list[TimelineEvent],
    locations: list[Location],
) -> SceneSegmentation:
    numbered = "\n".join(f"{i}: {u}" for i, u in enumerate(units))
    roster = ", ".join(c.name for c in characters) if characters else "(none)"
    places = ", ".join(loc.name for loc in locations) if locations else "(none)"
    plot = "\n".join(f"{e.order}. {e.summary}" for e in timeline) if timeline else "(none)"
    result = structured_text(
        SEGMENTATION_PROMPT.format(numbered=numbered, roster=roster, locations=places, plot=plot),
        SceneSegmentation,
    )
    log.info("segment: %d units → %d raw scenes", len(units), len(result.scenes))
    return result
```

In `segment`, pass the locations and map with carry-forward:

```python
    raw = segment_scenes(units, state.characters, state.timeline, state.locations)
```

```python
    name_to_loc = {loc.name: loc.loc_id for loc in state.locations}
    # Carry-forward seed (§4.1): s0 with no location takes locations[0], so a story that names a
    # place once still gets one setting for the whole book rather than none.
    prev_loc: str | None = state.locations[0].loc_id if state.locations else None

    scenes = []
    for i, r in enumerate(repaired):
        excerpt = " ".join(units[r.start : r.end + 1])
        char_ids: list[str] = []
        for name in r.characters_present:
            if name in name_to_ids:
                char_ids.extend(name_to_ids[name])
            else:
                log.warning("segment: name %r not in roster, dropped", name)

        loc_id = name_to_loc.get(r.location_name) if r.location_name else None
        if r.location_name and loc_id is None:
            log.warning("segment: location %r not in roster, dropped", r.location_name)
        if loc_id is None:
            loc_id = prev_loc          # carry-forward, over the FINAL scene list in order
        prev_loc = loc_id

        scenes.append(Scene(
            scene_id=f"s{i}",
            text_excerpt=excerpt,
            caption=excerpt,
            characters_present=char_ids,
            location_id=loc_id,
        ))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_segment_node.py -v`
Expected: PASS, whole file green.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check .
git add backend/pipeline/segment.py backend/tests/test_segment_node.py
git commit -m "feat(segment): map location_name to loc_id with carry-forward"
```

---

## Task 5: `segment` — no duplicate `char_id` in `characters_present`

**Files:**
- Modify: `backend/pipeline/segment.py:189-202`
- Modify: `docs/specs/scene-segmentation.md`
- Test: `backend/tests/test_segment_node.py`

**Interfaces:**
- Consumes: Task 4's mapping loop.
- Produces: invariant 3 — `characters_present` contains no duplicate `char_id`. Part 2 adds the defensive mirror in `referenced_characters` for checkpoints written before this change.

**The two independent paths to a repeated `char_id`** (spec §4.3): the segmentation model returns the same name twice, **or** `analyze` mints two characters sharing a name (it takes `analysis.characters[:3]` and never checks for a collision) so `name_to_ids` maps one name to two ids. The second path is why `dict.fromkeys` alone is not the whole fix — the map itself must collapse to first-seen-wins.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_segment_node.py`:

```python
# --- §6 tests 6 & 7 / spec §4.3 D3(a): one char_id per character, per scene ---

def test_segment_maps_a_repeated_name_to_one_char_id():
    """Path 1: the model returns the same name twice. Sending one reference image as two
    subjects is how a character gets drawn twice, often once smaller."""
    seg = SceneSegmentation(scenes=[
        ExtractedScene(start=0, end=1, characters_present=["the dog", "the dog"]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state(characters=[_char("c0", "the dog")]))

    assert result["scenes"][0].characters_present == ["c0"]


def test_segment_maps_two_roster_characters_sharing_a_name_to_one_char_id():
    """Path 2: `analyze` takes `characters[:3]` and never checks for a name collision, so one
    mention used to `.extend` BOTH ids and send two references for one named character."""
    seg = SceneSegmentation(scenes=[
        ExtractedScene(start=0, end=1, characters_present=["the dog"]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state(characters=[_char("c0", "the dog"), _char("c1", "the dog")]))

    assert result["scenes"][0].characters_present == ["c0"]


def test_segment_dedup_preserves_first_seen_order_of_the_survivors():
    """Invariant 4: removing a duplicate must not reorder the survivors — the roll index in
    `build_prompt` is asserted against `ref_paths` on three separate nodes."""
    seg = SceneSegmentation(scenes=[
        ExtractedScene(start=0, end=1, characters_present=["the cat", "the dog", "the cat"]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state(characters=[_char("c0", "the dog"), _char("c1", "the cat")]))

    assert result["scenes"][0].characters_present == ["c1", "c0"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_segment_node.py -k "char_id or first_seen_order" -v`
Expected: FAIL — `assert ['c0', 'c0'] == ['c0']` on the first, `assert ['c0', 'c1'] == ['c0']` on the second, `assert ['c1', 'c0', 'c1'] == ['c1', 'c0']` on the third.

- [ ] **Step 3: Write the minimal implementation**

In `backend/pipeline/segment.py`, replace the list-valued map:

```python
    name_to_ids: dict[str, list[str]] = {}
    for c in state.characters:
        name_to_ids.setdefault(c.name, []).append(c.char_id)
```

with a first-seen-wins map:

```python
    # §4.3 path 2: `analyze` never checks for a name collision, so a list-valued map sent ONE
    # named character's mention out as TWO references. First-seen wins — the roster is already in
    # prominence order, so the first id is the more important character.
    name_to_id: dict[str, str] = {}
    for c in state.characters:
        name_to_id.setdefault(c.name, c.char_id)
```

and inside the scene loop replace the `.extend` branch:

```python
        for name in r.characters_present:
            if name in name_to_id:
                char_ids.append(name_to_id[name])
            else:
                log.warning("segment: name %r not in roster, dropped", name)
```

and dedup at construction (invariant 3), order-preserving:

```python
        scenes.append(Scene(
            scene_id=f"s{i}",
            text_excerpt=excerpt,
            caption=excerpt,
            # §4.3 path 1. `dict.fromkeys` preserves first-seen order, so removing a duplicate
            # cannot reorder the survivors (invariant 4).
            characters_present=list(dict.fromkeys(char_ids)),
            location_id=loc_id,
        ))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_segment_node.py -v`
Expected: PASS, whole file green.

- [ ] **Step 5: Update `docs/specs/scene-segmentation.md`**

Add to the behavior section:

```markdown
### Setting (`scene-setting-and-subject-binding.md` §4.1)

`SEGMENTATION_PROMPT` carries a location roster and `ExtractedScene.location_name`, mapped to
`scenes[].location_id` by the same pattern as the character path (unknown name → warn + treated as
null). Carry-forward runs last, over the final scene list in order: a null inherits the previous
scene's `location_id`; a null `s0` takes `locations[0].loc_id` if the story named any, else `None`.
A story that names no location leaves every `location_id` as `None` — identical to before.

`location_name` propagates through **all eight** `ExtractedScene(...)` constructions (seven in
`repair`, one in `merge_thin`); on a merge, `a.location_name or b.location_name`. The whole-story
floor deliberately constructs with no location, and carry-forward supplies `locations[0]`.

### Invariant: no duplicate `char_id` (`scene-setting-and-subject-binding.md` §4.3)

`characters_present` contains no repeated `char_id`. Two paths produced one: the model naming a
character twice, and `analyze` minting two characters with the same name. The name → id map is
first-seen-wins and the id list is deduplicated with `dict.fromkeys`, which preserves first-seen
order — so removing a duplicate cannot reorder the survivors that `build_prompt`'s image roll and
`generate_scene`'s `ref_paths` are both indexed against.
```

- [ ] **Step 6: Full verify and commit**

```bash
cd backend && uv run ruff check . && uv run pytest
git add backend/pipeline/segment.py backend/tests/test_segment_node.py docs/specs/scene-segmentation.md
git commit -m "fix(segment): deduplicate char_ids in characters_present (#23 D3a)"
```

---

## Part 1 exit criteria

- [ ] `cd backend && uv run ruff check . && uv run pytest` — green, output shown.
- [ ] `git diff backend/pipeline/graph.py` is empty.
- [ ] `CURRENT_SCHEMA_VERSION` is still `1`.
- [ ] `docs/specs/story-analyzer.md` and `docs/specs/scene-segmentation.md` are updated in the same change.
- [ ] Spec §6 tests **1, 2, 3, 4 (eight assertions, one per constructor site), 5, 6, 7, 22** all exist and pass.
- [ ] Every one of them was seen failing first.

Proceed to Part 2.
