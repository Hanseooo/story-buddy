import inspect
import logging
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.config import MAX_SCENES, MIN_SCENE_WORDS, MIN_SCENES
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Character, Input, Location, Scene, StoryMemory, StoryObject
from pipeline.segment import (
    SEGMENTATION_PROMPT,
    ExtractedScene,
    ExtractedVisualDirection,
    SceneSegmentation,
    _merge_extracted,
    merge_thin,
    render_visual_direction,
    repair,
    segment,
    segment_scenes,
    split_sentences,
)


def _direction(
    key_action: str = "The visible subject performs the described action.",
    pose_expression: str | None = None,
    viewpoint: str = "wide view",
    framing: str = "wide shot",
) -> ExtractedVisualDirection:
    return ExtractedVisualDirection(
        key_action=key_action,
        pose_expression=pose_expression,
        viewpoint=viewpoint,
        framing=framing,
    )


def test_split_sentences_on_period():
    assert split_sentences("Hello. World.") == ["Hello.", "World."]

def test_split_sentences_on_exclamation():
    assert split_sentences("Hello! World.") == ["Hello!", "World."]

def test_split_sentences_on_question():
    assert split_sentences("Hello? World.") == ["Hello?", "World."]

def test_split_sentences_on_ellipsis():
    assert split_sentences("Hello… World.") == ["Hello…", "World."]

def test_split_sentences_on_newline():
    assert split_sentences("Hello.\nWorld.") == ["Hello.", "World."]

def test_split_sentences_drops_whitespace_only_units():
    assert split_sentences("Hello.   World.") == ["Hello.", "World."]

def test_split_sentences_empty_string():
    assert split_sentences("") == []

def test_split_sentences_whitespace_only():
    assert split_sentences("   ") == []

def test_split_sentences_single_sentence_no_split():
    assert split_sentences("A dog runs in a field.") == ["A dog runs in a field."]


# --- D-G guard ---

def test_extracted_scene_has_no_id_field():
    """D-G: ids minted node-side; LLM schema carries none."""
    assert "scene_id" not in ExtractedScene.model_fields


def test_extracted_scene_has_no_object_events():
    assert "object_events" not in ExtractedScene.model_fields


# --- Provider seam ---

def test_segment_scenes_passes_numbered_units_and_schema_to_provider():
    units = ["The dog ran.", "He found a ball."]
    stub = SceneSegmentation(scenes=[ExtractedScene(start=0, end=1, characters_present=[], visual_direction=_direction("A dog runs."))])
    with patch("pipeline.segment.structured_text", return_value=stub) as mock_provider:
        segment_scenes(units, [], [], [], [])
    prompt, schema = mock_provider.call_args.args
    assert "0: The dog ran." in prompt
    assert "1: He found a ball." in prompt
    for concept in ("montage", "split panel", "duplicate character", "impossible pose"):
        assert concept in prompt
    assert schema is SceneSegmentation


def test_segment_scenes_returns_parsed_wrapper_unchanged():
    units = ["A story."]
    stub = SceneSegmentation(scenes=[ExtractedScene(start=0, end=0, characters_present=[], visual_direction=_direction("A dog runs."))])
    with patch("pipeline.segment.structured_text", return_value=stub):
        result = segment_scenes(units, [], [], [], [])
    assert result is stub


# --- Direction validation and rendering tests ---

def test_extracted_visual_direction_accepts_all_four_fields():
    direction = ExtractedVisualDirection(
        key_action="Leo builds a toy robot.",
        pose_expression="smiling cheerfully",
        viewpoint="front view",
        framing="medium shot",
    )
    assert direction.key_action == "Leo builds a toy robot."
    assert direction.pose_expression == "smiling cheerfully"
    assert direction.viewpoint == "front view"
    assert direction.framing == "medium shot"


def test_extracted_visual_direction_accepts_null_pose_expression():
    direction = ExtractedVisualDirection(
        key_action="Leo builds a toy robot.",
        pose_expression=None,
        viewpoint="front view",
        framing="medium shot",
    )
    assert direction.pose_expression is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("key_action", "   "),
        ("viewpoint", ""),
        ("framing", " \t "),
        ("pose_expression", "   "),
    ],
)
def test_extracted_visual_direction_rejects_blank_fields(field, value):
    payload = {
        "key_action": "Leo builds a robot.",
        "pose_expression": None,
        "viewpoint": "front view",
        "framing": "medium shot",
        field: value,
    }
    with pytest.raises(ValidationError):
        ExtractedVisualDirection.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("key_action", "Leo builds\na robot."),
        ("pose_expression", "smiling\rcheerfully"),
        ("viewpoint", "front\nview"),
        ("framing", "medium\r\nshot"),
    ],
)
def test_extracted_visual_direction_rejects_newlines(field, value):
    payload = {
        "key_action": "Leo builds a robot.",
        "pose_expression": None,
        "viewpoint": "front view",
        "framing": "medium shot",
        field: value,
    }
    with pytest.raises(ValidationError):
        ExtractedVisualDirection.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("key_action", 'Leo says "hello" to his robot.'),
        ("key_action", "Leo says “hello” to his robot."),
        ("key_action", "Leo says ”hello” to his robot."),
        ("pose_expression", 'looking "surprised"'),
        ("pose_expression", "looking “surprised”"),
        ("viewpoint", 'front "hero" view'),
        ("framing", '“close-up” shot'),
    ],
)
def test_extracted_visual_direction_rejects_straight_and_curly_quotes(field, value):
    payload = {
        "key_action": "Leo builds a robot.",
        "pose_expression": None,
        "viewpoint": "front view",
        "framing": "medium shot",
        field: value,
    }
    with pytest.raises(ValidationError):
        ExtractedVisualDirection.model_validate(payload)


def test_extracted_visual_direction_preserves_ordinary_apostrophe():
    direction = ExtractedVisualDirection(
        key_action="Leo's toy robot stands on the table.",
        pose_expression="Leo's expression is bright",
        viewpoint="front view",
        framing="medium shot",
    )
    assert direction.key_action == "Leo's toy robot stands on the table."
    assert direction.pose_expression == "Leo's expression is bright"


def test_render_visual_direction_emits_structured_moment_and_exact_markers():
    direction = ExtractedVisualDirection(
        key_action="Leo raises his hand in greeting.",
        pose_expression="smiling cheerfully,",
        viewpoint="front-facing eye-level view",
        framing="medium close-up",
    )
    rendered = render_visual_direction(direction)
    assert rendered == (
        "Leo raises his hand in greeting. smiling cheerfully, "
        "Viewpoint: front-facing eye-level view. Framing: medium close-up."
    )
    assert rendered.count("Viewpoint:") == 1
    assert rendered.count("Framing:") == 1
    assert rendered.count("Leo raises his hand") == 1


def test_render_visual_direction_omits_pose_expression_when_none():
    direction = ExtractedVisualDirection(
        key_action="Leo raises his hand in greeting.",
        pose_expression=None,
        viewpoint="front-facing eye-level view",
        framing="medium close-up",
    )
    rendered = render_visual_direction(direction)
    assert rendered == (
        "Leo raises his hand in greeting. "
        "Viewpoint: front-facing eye-level view. Framing: medium close-up."
    )
    assert rendered.count("Viewpoint:") == 1
    assert rendered.count("Framing:") == 1


def test_render_visual_direction_has_no_relations_argument():
    assert "relations" not in inspect.signature(render_visual_direction).parameters


# --- repair pure tests ---

def _r(start: int, end: int, chars=None, location=None, **overrides) -> ExtractedScene:
    vd = overrides.pop("visual_direction", None)
    if vd is None:
        vd = _direction()
    elif isinstance(vd, dict):
        vd = ExtractedVisualDirection(**vd)
    elif isinstance(vd, str):
        vd = _direction(key_action=vd)
    return ExtractedScene(
        start=start,
        end=end,
        characters_present=chars or [],
        location_name=location,
        visual_direction=vd,
        **overrides,
    )



def test_repair_sorts_out_of_order_ranges():
    result = repair([_r(3, 4), _r(0, 2)], 5)
    assert result[0].start == 0
    assert result[1].start == 3


def test_repair_de_overlaps_in_favour_of_earlier_scene():
    result = repair([_r(0, 3), _r(2, 4)], 5)
    assert result[0].end == 3
    assert result[1].start == 4
    assert result[1].end == 4


def test_repair_closes_interior_gap_by_extending_preceding_end():
    result = repair([_r(0, 1), _r(3, 4)], 5)
    assert result[0].end == 2   # gap [2] attaches to preceding scene


def test_repair_closes_leading_gap():
    result = repair([_r(2, 4)], 5)
    assert result[0].start == 0


def test_repair_closes_trailing_gap():
    result = repair([_r(0, 2)], 5)
    assert result[0].end == 4


def test_repair_total_coverage():
    """Invariant 2: every index in range(n) appears in exactly one output range."""
    import random
    random.seed(42)
    for n in [1, 5, 10, 20]:
        scenes = [_r(random.randint(0, n - 1), random.randint(0, n - 1))
                  for _ in range(max(1, random.randint(0, 10)))]
        result = repair(scenes, n)
        covered: set[int] = set()
        for s in result:
            for idx in range(s.start, s.end + 1):
                assert idx not in covered, f"index {idx} covered twice in n={n}"
                covered.add(idx)
        assert covered == set(range(n)), f"missing indices in n={n}: {set(range(n)) - covered}"


def test_extracted_scene_requires_nonblank_visual_direction():
    with pytest.raises(ValidationError):
        ExtractedScene(start=0, end=0, characters_present=[], visual_direction="   ")


def test_segment_scenes_passes_the_object_roster_and_new_schema_to_provider():
    units = ["Ana lifts the sword."]
    characters = [Character(char_id="c0", name="Ana")]
    objects = [
        StoryObject(
            obj_id="obj0",
            name="wooden sword",
            description="a short wooden sword with a red cord grip",
            owner_char_id="c0",
        )
    ]
    result = SceneSegmentation(
        scenes=[
            ExtractedScene(
                start=0,
                end=0,
                characters_present=["Ana"],
                objects_present=["wooden sword"],
                visual_direction=_direction(
                    key_action="Ana faces right and lifts the sword.",
                    viewpoint="medium view",
                    framing="medium shot",
                ),
            )
        ]
    )
    with patch("pipeline.segment.structured_text", return_value=result) as provider:
        segment_scenes(units, characters, [], [], objects)

    prompt, schema = provider.call_args.args
    assert "wooden sword" in prompt
    assert "object_events" not in prompt
    assert "visual_direction" in prompt
    assert schema is SceneSegmentation


@pytest.mark.parametrize("transform", ["repair", "merge_thin"])
def test_scene_transform_preserves_explicit_objects_and_direction(transform):
    first = _r(
        0,
        0,
        chars=["Ana"],
        objects_present=["wooden sword"],
        visual_direction="Ana acquires the sword facing right.",
    )
    if transform == "repair":
        result = repair([first], 2)[0]
        assert result.objects_present == ["wooden sword"]
        assert result.visual_direction.key_action == "Ana acquires the sword facing right."
    else:
        second = _r(
            1,
            1,
            chars=["Ana"],
            objects_present=["wooden sword"],
            visual_direction="Ana runs right in a wide view.",
        )
        third = _r(2, 2)
        fourth = _r(3, 3)
        units = ["Short.", "Also short.", "Third scene is long enough.", "Fourth scene is long enough."]
        result = merge_thin([first, second, third, fourth], units)[0]
        assert result.objects_present == ["wooden sword"]
        assert result.visual_direction.key_action == "Ana runs right in a wide view."


def test_repair_rejects_an_empty_model_scene_list_instead_of_inventing_direction():
    with pytest.raises(ValueError, match="no usable scene"):
        repair([], 2)


def test_repair_clamps_out_of_bounds_indices():
    result = repair([_r(-5, 100)], 5)
    assert result[0].start == 0
    assert result[0].end == 4


def test_repair_merges_18_ranges_to_10_retaining_later_characters():
    # 18 single-unit scenes alternating alice / bob
    scenes = [_r(i, i, ["alice"] if i % 2 == 0 else ["bob"]) for i in range(18)]
    result = repair(scenes, 18)
    assert len(result) == 10
    # total coverage
    covered: list[int] = []
    for s in result:
        covered.extend(range(s.start, s.end + 1))
    assert sorted(covered) == list(range(18))
    # merged scenes retain the later scene's characters
    assert all(s.characters_present in (["alice"], ["bob"]) for s in result)


def test_merge_extracted_retains_later_scene_moment_and_cast():
    a = _r(
        0,
        0,
        chars=["Ana"],
        objects_present=["toy"],
        visual_direction=_direction(
            key_action="Ana walks away.",
            pose_expression="looking back",
            viewpoint="rear view",
            framing="wide shot",
        ),
    )
    b = _r(
        1,
        1,
        chars=["Maya"],
        objects_present=["sword"],
        visual_direction=_direction(
            key_action="Maya raises the sword.",
            pose_expression="shouting victoriously",
            viewpoint="low-angle front view",
            framing="close-up",
        ),
    )
    merged = _merge_extracted(a, b)
    assert merged.start == 0
    assert merged.end == 1
    assert merged.characters_present == ["Maya"]
    assert merged.objects_present == ["sword"]
    assert merged.visual_direction.key_action == "Maya raises the sword."
    assert merged.visual_direction.pose_expression == "shouting victoriously"
    assert merged.visual_direction.viewpoint == "low-angle front view"
    assert merged.visual_direction.framing == "close-up"


def test_merge_extracted_explicit_later_location_wins():
    a = _r(0, 0, location="the beach")
    b = _r(1, 1, location="the hill")
    merged = _merge_extracted(a, b)
    assert merged.location_name == "the hill"


def test_merge_extracted_later_null_location_falls_back_to_earlier():
    a = _r(0, 0, location="the beach")
    b = _r(1, 1, location=None)
    merged = _merge_extracted(a, b)
    assert merged.location_name == "the beach"


def test_direction_source_provenance_is_transient_and_not_in_model_fields():
    assert "_direction_source" not in ExtractedScene.model_fields
    unmerged = _r(0, 0)
    assert getattr(unmerged, "_direction_source", "unmerged") == "unmerged"
    merged = _merge_extracted(_r(0, 0), _r(1, 1))
    assert getattr(merged, "_direction_source", None) == "retained-later-merge"


# --- thin-scene floor (#31) ---

def _units(*counts: int) -> list[str]:
    """One unit per count, each exactly `count` words long."""
    return [" ".join(["word"] * c) for c in counts]


def _words(scene: ExtractedScene, units: list[str]) -> int:
    return sum(len(units[i].split()) for i in range(scene.start, scene.end + 1))


def test_merge_thin_folds_away_a_scene_too_thin_to_draw():
    """#31: prod job d83721d9 drew a page from `"Ana decided to help."` — 4 words, no subject
    appearance, no setting, no action — and the image model invented one."""
    units = _units(4, 17, 15, 4, 16, 12)     # the prod story, title line first
    result = merge_thin([_r(i, i) for i in range(6)], units)
    assert all(_words(s, units) >= MIN_SCENE_WORDS for s in result)


def test_merge_thin_stops_before_the_book_runs_out_of_pages():
    """A story of nothing but short sentences is what a 6-year-old writes. It still gets pages."""
    units = _units(*([3] * 10))
    assert len(merge_thin([_r(i, i) for i in range(10)], units)) == MIN_SCENES


def test_merge_thin_leaves_a_one_page_story_alone():
    """Below the floor with no neighbour to merge into: return it, do not spin."""
    assert len(merge_thin([_r(0, 0)], _units(5))) == 1


def test_merge_thin_keeps_every_sentence_on_exactly_one_page():
    units = _units(4, 2, 30, 3, 20, 1, 9)
    covered: list[int] = []
    for s in merge_thin([_r(i, i) for i in range(7)], units):
        covered.extend(range(s.start, s.end + 1))
    assert covered == list(range(7))


def test_merge_thin_retains_later_scene_characters():
    units = _units(2, 3, 20, 20)
    result = merge_thin(
        [_r(0, 0, ["alice"]), _r(1, 1, ["bob"]), _r(2, 2), _r(3, 3)], units
    )
    assert result[0].characters_present == ["bob"]


def test_merge_thin_leaves_a_book_of_full_pages_untouched():
    scenes = [_r(i, i) for i in range(4)]
    assert merge_thin(scenes, _units(20, 20, 20, 20)) == scenes


# --- §6 test 4: location_name survives all EIGHT ExtractedScene construction sites ---
# One assertion per site. A missed site silently drops the field on exactly the messy stories
# that need repair most, and no pre-existing test would catch it.

def test_location_name_survives_the_clamp_site():
    assert repair([_r(-5, 100, location="the beach")], 5)[0].location_name == "the beach"


def test_location_name_survives_the_de_overlap_site():
    result = repair([_r(0, 3, location="the beach"), _r(2, 4, location="the hill")], 5)
    assert result[1].start == 4                      # this one WAS reconstructed by de-overlap
    assert result[1].location_name == "the hill"


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
    """11 single-unit scenes → exactly one merge, and ties go to the earliest pair, so scenes
    0 and 1 fuse."""
    scenes = [_r(i, i) for i in range(11)]
    scenes[1] = _r(1, 1, location="the hill")

    result = repair(scenes, 11)

    assert len(result) == 10
    assert result[0].location_name == "the hill"     # `b.location_name or a.location_name`


def test_location_name_survives_the_merge_thin_site():
    units = _units(2, 3, 20, 20)
    result = merge_thin(
        [_r(0, 0, location="the beach"), _r(1, 1, location="the hill"), _r(2, 2), _r(3, 3)], units
    )
    assert result[0].location_name == "the hill"


# --- §6 test 5: the merge rule itself ---

def test_a_merge_takes_the_later_scenes_location_when_both_have_one():
    """`b.location_name or a.location_name` — the later scene wins."""
    scenes = [_r(i, i) for i in range(11)]
    scenes[0] = _r(0, 0, location="the beach")
    scenes[1] = _r(1, 1, location="the hill")

    assert repair(scenes, 11)[0].location_name == "the hill"


def test_merge_thin_takes_the_later_scenes_location_when_both_have_one():
    units = _units(2, 3, 20, 20)
    result = merge_thin(
        [_r(0, 0, location="the beach"), _r(1, 1, location="the hill"), _r(2, 2), _r(3, 3)], units
    )
    assert result[0].location_name == "the hill"



# --- Node helpers ---

def _state(
    raw: str = "The dog ran. He found a ball.",
    redacted: str | None = None,
    characters: list | None = None,
    timeline: list | None = None,
    locations: list | None = None,
    objects: list | None = None,
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
        objects=objects or [],
    )



def _char(char_id: str, name: str) -> Character:
    return Character(char_id=char_id, name=name)


_STUB_SEG = SceneSegmentation(scenes=[
    _r(0, 0, chars=["the dog"]),
    _r(1, 1, chars=[]),
])


# --- Node tests ---

def test_segment_mints_zero_based_scene_ids():
    """D-G §2.1: ids are s0, s1, ... minted by list position."""
    with patch("pipeline.segment.segment_scenes", return_value=_STUB_SEG):
        result = segment(_state(characters=[_char("c0", "the dog")]))
    assert [s.scene_id for s in result["scenes"]] == ["s0", "s1"]


def test_segment_text_excerpt_is_verbatim_join_of_source_units():
    """Invariant 3: text_excerpt is sliced from source units, never model prose."""
    seg = SceneSegmentation(scenes=[
        _r(0, 0, chars=[]),
        _r(1, 1, chars=[]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state(raw="The dog ran. He found a ball."))
    assert result["scenes"][0].text_excerpt == "The dog ran."
    assert result["scenes"][1].text_excerpt == "He found a ball."
    # Concatenating all excerpts in order reproduces the source sentences
    all_text = " ".join(s.text_excerpt for s in result["scenes"])
    assert all_text == "The dog ran. He found a ball."


def test_segment_caption_equals_text_excerpt():
    """ADR-013: caption is the child's verbatim text, not a generated string."""
    with patch("pipeline.segment.segment_scenes", return_value=_STUB_SEG):
        result = segment(_state(characters=[_char("c0", "the dog")]))
    for s in result["scenes"]:
        assert s.caption == s.text_excerpt


def test_segment_does_not_mint_a_page_it_cannot_draw():
    """#31 regression, prod job d83721d9: the node applies the floor, not just `repair`.

    The two excerpts asserted absent are the two pages that shipped — the title line and the
    four-word fragment — each drawn by a model with nothing to go on.
    """
    raw = (
        "The Lost Little Star\n"
        "Once upon a time, a little girl named Ana found a tiny glowing star in her backyard. "
        "The star had fallen from the night sky and could not find its way home. "
        "Ana decided to help. "
        "She carried the star to the highest hill in the village and held it up high. "
        "The star floated back into the sky and twinkled brightly, thanking Ana."
    )
    seg = SceneSegmentation(scenes=[_r(i, i) for i in range(6)])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        excerpts = [s.text_excerpt for s in segment(_state(raw=raw))["scenes"]]
    assert "Ana decided to help." not in excerpts
    assert "The Lost Little Star" not in excerpts


def test_segment_maps_roster_names_to_char_ids():
    """Invariant 6: characters_present contains only char_ids from state.characters."""
    seg = SceneSegmentation(scenes=[
        _r(0, 0, chars=["the dog"]),
        _r(1, 1, chars=["the cat"]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state(characters=[_char("c0", "the dog"), _char("c1", "the cat")]))
    assert result["scenes"][0].characters_present == ["c0"]
    assert result["scenes"][1].characters_present == ["c1"]


def test_segment_does_not_add_a_merely_mentioned_offscreen_character():
    raw = SceneSegmentation(
        scenes=[
            ExtractedScene(
                start=0,
                end=0,
                characters_present=["Ana"],
                visual_direction=_direction(
                    key_action="Ana looks sadly out the window.",
                    viewpoint="profile view",
                    framing="medium shot",
                ),
            )
        ]
    )
    state = _state(
        raw="Ana remembered the Shadow Wizard.",
        characters=[Character(char_id="c0", name="Ana"), Character(char_id="c1", name="Shadow Wizard")],
    )
    with patch("pipeline.segment.segment_scenes", return_value=raw):
        scene = segment(state)["scenes"][0]

    assert scene.characters_present == ["c0"]


def test_segment_rejects_an_unknown_visible_character():
    raw = SceneSegmentation(
        scenes=[
            ExtractedScene(
                start=0,
                end=0,
                characters_present=["Ghost"],
                visual_direction=_direction(
                    key_action="Ghost crosses the room.",
                    viewpoint="wide view",
                    framing="wide shot",
                ),
            )
        ]
    )
    with patch("pipeline.segment.segment_scenes", return_value=raw):
        with pytest.raises(ValueError, match="unknown character.*Ghost"):
            segment(_state(raw="Someone crossed the room."))


def test_segment_rejects_direction_naming_a_roster_character_outside_the_cast():
    raw = SceneSegmentation(
        scenes=[
            ExtractedScene(
                start=0,
                end=0,
                characters_present=["Ana"],
                visual_direction=_direction(
                    key_action="Ana watches the Shadow Wizard flee away from her.",
                    viewpoint="wide view",
                    framing="wide shot",
                ),
            )
        ]
    )
    state = _state(
        raw="Ana watched him flee.",
        characters=[Character(char_id="c0", name="Ana"), Character(char_id="c1", name="Shadow Wizard")],
    )
    with patch("pipeline.segment.segment_scenes", return_value=raw):
        with pytest.raises(ValueError, match="outside visible cast"):
            segment(state)


SWORD = StoryObject(
    obj_id="obj0",
    name="wooden sword",
    description="a short wooden sword with a red cord grip",
    owner_char_id="c0",
)


def _segment_objects(raw: SceneSegmentation) -> list[Scene]:
    state = _state(
        raw="One. Two. Three.",
        characters=[_char("c0", "Ana"), _char("c1", "Maya")],
        objects=[SWORD],
    )
    with patch("pipeline.segment.segment_scenes", return_value=raw):
        return segment(state)["scenes"]


def test_segment_keeps_objects_explicit_to_each_scene():
    raw = SceneSegmentation(
        scenes=[
            _r(0, 0, chars=["Ana"], objects_present=["wooden sword"], visual_direction="Ana picks up the sword."),
            _r(1, 1, chars=["Ana"], visual_direction="Ana walks right in a wide view."),
            _r(2, 2, chars=["Ana"], objects_present=["wooden sword"], visual_direction="Ana sets down the sword."),
        ]
    )
    scenes = _segment_objects(raw)
    assert [scene.objects_present for scene in scenes] == [["obj0"], [], ["obj0"]]
    assert all("is held by" not in scene.visual_direction for scene in scenes)


def test_segment_does_not_infer_object_visibility_or_holder_from_owner():
    raw = SceneSegmentation(
        scenes=[
            _r(0, 0, chars=["Ana"], visual_direction="Ana walks right in a wide view."),
            _r(1, 1, chars=["Ana"], visual_direction="Ana looks at the sword."),
        ]
    )
    scenes = _segment_objects(raw)
    assert [scene.objects_present for scene in scenes] == [[], []]
    assert all("is held by" not in scene.visual_direction for scene in scenes)


def test_segment_preserves_explicit_object_interaction_in_key_action():
    raw = SceneSegmentation(
        scenes=[
            _r(
                0,
                0,
                chars=["Ana", "Maya"],
                objects_present=["wooden sword"],
                visual_direction="Ana hands the wooden sword to Maya.",
            ),
            _r(1, 1, chars=["Maya"], visual_direction="Maya walks right."),
        ]
    )
    scenes = _segment_objects(raw)
    assert "Ana hands the wooden sword to Maya." in scenes[0].visual_direction
    assert "is held by" not in scenes[0].visual_direction


def test_unowned_object_explicitly_visible_in_scene_1_and_absent_in_scene_2():
    unowned_sword = StoryObject(
        obj_id="obj1",
        name="magic key",
        description="a golden key",
        owner_char_id=None,
    )
    raw = SceneSegmentation(
        scenes=[
            _r(0, 0, chars=["Ana"], objects_present=["magic key"], visual_direction="Ana finds a key."),
            _r(1, 1, chars=["Ana"], visual_direction="Ana walks away."),
        ]
    )
    state = _state(
        raw="One. Two.",
        characters=[_char("c0", "Ana")],
        objects=[unowned_sword],
    )
    with patch("pipeline.segment.segment_scenes", return_value=raw):
        scenes = segment(state)["scenes"]
    assert [scene.objects_present for scene in scenes] == [["obj1"], []]


def test_segment_empty_roster_gives_empty_characters_present_no_raise():
    """Edge case: roster is empty → every scene gets [] and the node does not raise."""
    seg = SceneSegmentation(scenes=[
        _r(0, 0, chars=[]),
        _r(1, 1, chars=[]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state())  # characters=[]
    for s in result["scenes"]:
        assert s.characters_present == []


def test_segment_prefers_redacted_text():
    """CC-2: segment_scenes receives units from redacted_text, not raw_text."""
    seg = SceneSegmentation(scenes=[_r(0, 1, chars=[])])
    with patch("pipeline.segment.segment_scenes", return_value=seg) as mock_seg:
        segment(_state(raw="raw version. Still raw.", redacted="redacted version. Still redacted."))
    units_arg = mock_seg.call_args.args[0]
    assert all("redacted" in u for u in units_arg)


def test_segment_falls_back_to_raw_text_when_redacted_is_none():
    """CC-2 fallback: uses raw_text when redacted_text is None."""
    seg = SceneSegmentation(scenes=[_r(0, 1, chars=[])])
    with patch("pipeline.segment.segment_scenes", return_value=seg) as mock_seg:
        segment(_state(raw="raw version. Still raw.", redacted=None))
    units_arg = mock_seg.call_args.args[0]
    assert all("raw" in u for u in units_arg)


def test_segment_empty_text_returns_empty_scenes_without_calling_provider():
    """Edge case: empty/whitespace text → {"scenes": []} with no LLM call (spec §4)."""
    with patch("pipeline.segment.segment_scenes") as mock_seg:
        result = segment(_state(raw=""))
    assert result == {"scenes": []}
    mock_seg.assert_not_called()


def test_segment_partial_returns_exactly_scenes_key_and_does_not_mutate_state():
    """ADR-024: partial-return; state is unmutated."""
    state = _state()
    before = state.model_dump()
    seg = SceneSegmentation(scenes=[_r(0, 1, chars=[])])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(state)
    assert set(result.keys()) == {"scenes"}
    assert state.model_dump() == before


# --- Regression guard (spec §4 retirement) ---

def test_caption_for_and_scene_caption_not_in_analyze_module():
    """Guards against LLM caption writer being reintroduced against ADR-013."""
    import pipeline.analyze as analyze_module
    assert not hasattr(analyze_module, "caption_for")
    assert not hasattr(analyze_module, "SceneCaption")


_LOCS = [
    Location(loc_id="loc0", name="the beach", description="golden sand"),
    Location(loc_id="loc1", name="the hill", description="tall grass"),
]


def _seg(*locations: str | None) -> SceneSegmentation:
    """One single-unit scene per argument, each carrying that `location_name`."""
    return SceneSegmentation(scenes=[
        _r(i, i, chars=[], location=name)
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
    stub = SceneSegmentation(scenes=[_r(0, 1, chars=[])])
    with patch("pipeline.segment.structured_text", return_value=stub) as mock_provider:
        segment_scenes(units, [], [], _LOCS, [])

    prompt = mock_provider.call_args.args[0]
    assert "the beach" in prompt
    assert "the hill" in prompt


def test_segment_scenes_says_none_when_the_story_has_no_locations():
    stub = SceneSegmentation(scenes=[_r(0, 0, chars=[])])
    with patch("pipeline.segment.structured_text", return_value=stub) as mock_provider:
        segment_scenes(["A story."], [], [], [], [])

    assert "Locations in the story: (none)" in mock_provider.call_args.args[0]


def test_segment_passes_the_state_locations_to_segment_scenes():
    stub = SceneSegmentation(scenes=[_r(0, 1, chars=[])])
    with patch("pipeline.segment.segment_scenes", return_value=stub) as mock_seg:
        segment(_state(locations=_LOCS))

    assert mock_seg.call_args.args[3] == _LOCS


# --- §6 tests 6 & 7 / spec §4.3 D3(a): one char_id per character, per scene ---

def test_segment_maps_a_repeated_name_to_one_char_id():
    """Path 1: the model returns the same name twice. Sending one reference image as two
    subjects is how a character gets drawn twice, often once smaller."""
    seg = SceneSegmentation(scenes=[
        _r(0, 1, chars=["the dog", "the dog"]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state(characters=[_char("c0", "the dog")]))

    assert result["scenes"][0].characters_present == ["c0"]


def test_segment_maps_two_roster_characters_sharing_a_name_to_one_char_id():
    """Path 2: `analyze` takes `characters[:3]` and never checks for a name collision, so one
    mention used to `.extend` BOTH ids and send two references for one named character."""
    seg = SceneSegmentation(scenes=[
        _r(0, 1, chars=["the dog"]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state(characters=[_char("c0", "the dog"), _char("c1", "the dog")]))

    assert result["scenes"][0].characters_present == ["c0"]


def test_segment_dedup_preserves_first_seen_order_of_the_survivors():
    """Invariant 4: removing a duplicate must not reorder the survivors — the roll index in
    `build_prompt` is asserted against `ref_paths` on three separate nodes."""
    seg = SceneSegmentation(scenes=[
        _r(0, 1, chars=["the cat", "the dog", "the cat"]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state(characters=[_char("c0", "the dog"), _char("c1", "the cat")]))

    assert result["scenes"][0].characters_present == ["c1", "c0"]




def test_the_prompt_asks_for_pronoun_only_beats():
    units = ["The dragon woke.", "He roared."]
    stub = SceneSegmentation(scenes=[_r(0, 1, chars=[])])
    with patch("pipeline.segment.structured_text", return_value=stub) as mock_provider:
        segment_scenes(units, [_char("c0", "the dragon")], [], [], [])

    assert "he, she, it or they" in mock_provider.call_args.args[0]


def test_segmentation_prompt_names_the_shared_scene_ceiling():
    """spend-and-retry-economics §6.3: "the segmentation prompt names the same ceiling".

    The prompt used to carry a literal `15` while `MAX_SCENES` moved underneath it, so the model
    was asked for a ceiling the deterministic merge did not enforce. Pin the interpolation, not
    just the formatted output, or a future edit can re-hardcode the number and still pass.
    """
    assert "{max_scenes}" in SEGMENTATION_PROMPT

    formatted = SEGMENTATION_PROMPT.format(
        numbered="", roster="", locations="", objects="", plot="", max_scenes=MAX_SCENES
    )
    assert f"- At most {MAX_SCENES} scenes." in formatted
    assert "15 scenes" not in formatted


def test_merged_scene_caption_range_remains_merged_redacted_excerpt():
    raw = SceneSegmentation(
        scenes=[
            _r(0, 0, chars=["Ana"], visual_direction=_direction("Ana walks right.")),
            _r(1, 1, chars=["Ana"], visual_direction=_direction("Ana jumps for joy.")),
            _r(2, 2, chars=["Ana"], visual_direction=_direction("Ana sleeps.")),
            _r(3, 3, chars=["Ana"], visual_direction=_direction("Ana wakes up.")),
        ]
    )
    units = ["Ana decided to run.", "She ran fast.", "She went home to rest.", "The sun rose."]
    state = _state(
        raw=" ".join(units),
        characters=[_char("c0", "Ana")],
    )
    with patch("pipeline.segment.segment_scenes", return_value=raw):
        result = segment(state)

    first_scene = result["scenes"][0]
    assert first_scene.text_excerpt == "Ana decided to run. She ran fast."
    assert first_scene.caption == "Ana decided to run. She ran fast."
    assert "Ana jumps for joy" in first_scene.visual_direction


def test_dialogue_remains_in_caption_and_absent_from_rendered_direction():
    raw = SceneSegmentation(
        scenes=[
            _r(
                0,
                0,
                chars=["Leo"],
                visual_direction=_direction(
                    key_action="Leo stands awake and raises one hand in greeting.",
                    pose_expression="smiling cheerfully",
                    viewpoint="front-facing eye-level view",
                    framing="medium shot",
                ),
            )
        ]
    )
    state = _state(
        raw='Leo said, "Hello world! We did it!"',
        characters=[_char("c0", "Leo")],
    )
    with patch("pipeline.segment.segment_scenes", return_value=raw):
        scene = segment(state)["scenes"][0]

    assert scene.text_excerpt == 'Leo said, "Hello world! We did it!"'
    assert scene.caption == 'Leo said, "Hello world! We did it!"'
    assert "Hello world" not in scene.visual_direction
    assert "We did it" not in scene.visual_direction
    assert "Leo stands awake and raises one hand in greeting." in scene.visual_direction
