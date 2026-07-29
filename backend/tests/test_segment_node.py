from pipeline.segment import split_sentences

from unittest.mock import patch

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Character, Input, StoryMemory, TimelineEvent
from pipeline.segment import ExtractedScene, SceneSegmentation, repair, segment, segment_scenes


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


# --- Provider seam ---

def test_segment_scenes_passes_numbered_units_and_schema_to_provider():
    units = ["The dog ran.", "He found a ball."]
    stub = SceneSegmentation(scenes=[ExtractedScene(start=0, end=1, characters_present=[])])
    with patch("pipeline.segment.structured_text", return_value=stub) as mock_provider:
        segment_scenes(units, [], [])
    prompt, schema = mock_provider.call_args.args
    assert "0: The dog ran." in prompt
    assert "1: He found a ball." in prompt
    assert schema is SceneSegmentation


def test_segment_scenes_returns_parsed_wrapper_unchanged():
    units = ["A story."]
    stub = SceneSegmentation(scenes=[ExtractedScene(start=0, end=0, characters_present=[])])
    with patch("pipeline.segment.structured_text", return_value=stub):
        result = segment_scenes(units, [], [])
    assert result is stub


# --- repair pure tests ---

def _r(start: int, end: int, chars: list[str] | None = None) -> ExtractedScene:
    return ExtractedScene(start=start, end=end, characters_present=chars or [])


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
                  for _ in range(random.randint(0, 10))]
        result = repair(scenes, n)
        covered: set[int] = set()
        for s in result:
            for idx in range(s.start, s.end + 1):
                assert idx not in covered, f"index {idx} covered twice in n={n}"
                covered.add(idx)
        assert covered == set(range(n)), f"missing indices in n={n}: {set(range(n)) - covered}"


def test_repair_empty_input_yields_whole_story_floor():
    result = repair([], 5)
    assert len(result) == 1
    assert result[0].start == 0
    assert result[0].end == 4


def test_repair_clamps_out_of_bounds_indices():
    result = repair([_r(-5, 100)], 5)
    assert result[0].start == 0
    assert result[0].end == 4


def test_repair_merges_18_ranges_to_15_with_union_of_characters():
    # 18 single-unit scenes alternating alice / bob
    scenes = [_r(i, i, ["alice"] if i % 2 == 0 else ["bob"]) for i in range(18)]
    result = repair(scenes, 18)
    assert len(result) == 15
    # total coverage
    covered: list[int] = []
    for s in result:
        covered.extend(range(s.start, s.end + 1))
    assert sorted(covered) == list(range(18))
    # merged scenes must carry both characters (3 pairs merged → at least 1 scene has both)
    merged_pairs = [set(s.characters_present) for s in result]
    assert any("alice" in c and "bob" in c for c in merged_pairs)


def _state(raw: str, redacted: str | None) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="t1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text=raw, redacted_text=redacted),
    )


def test_segment_mints_a_zero_based_scene_id():
    """§2.1: ids are `{prefix}{zero-based-index}`, minted by the node that creates the collection."""
    with patch("pipeline.segment.caption_for", return_value="stub caption"):
        result = segment(_state("A dog runs in a field.", "A dog runs in a field."))

    scene, = result["scenes"]
    assert scene.scene_id == "s0"
    assert scene.caption == "stub caption"
    assert scene.text_excerpt == "A dog runs in a field."


def test_segment_captions_the_redacted_text_not_the_raw_text():
    """CC-2: redacted_text is what downstream nodes consume. Sending raw_text to the model
    leaks exactly the PII the gate removed."""
    with patch("pipeline.segment.caption_for", return_value="x") as mock_caption_for:
        segment(_state("Ana lives on Elm St.", "[NAME] lives on [ADDRESS]."))

    mock_caption_for.assert_called_once_with("[NAME] lives on [ADDRESS].")
