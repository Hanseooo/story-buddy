from pipeline.segment import split_sentences

from unittest.mock import patch

from app.config import MIN_SCENE_WORDS, MIN_SCENES
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Character, Input, StoryMemory
from pipeline.segment import (
    ExtractedScene,
    SceneSegmentation,
    merge_thin,
    repair,
    segment,
    segment_scenes,
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


def test_merge_thin_carries_both_pages_characters():
    units = _units(2, 3, 20, 20)
    result = merge_thin(
        [_r(0, 0, ["alice"]), _r(1, 1, ["bob"]), _r(2, 2), _r(3, 3)], units
    )
    assert set(result[0].characters_present) == {"alice", "bob"}


def test_merge_thin_leaves_a_book_of_full_pages_untouched():
    scenes = [_r(i, i) for i in range(4)]
    assert merge_thin(scenes, _units(20, 20, 20, 20)) == scenes


# --- Node helpers ---

def _state(
    raw: str = "The dog ran. He found a ball.",
    redacted: str | None = None,
    characters: list | None = None,
    timeline: list | None = None,
) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="t1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text=raw, redacted_text=redacted),
        characters=characters or [],
        timeline=timeline or [],
    )


def _char(char_id: str, name: str) -> Character:
    return Character(char_id=char_id, name=name)


_STUB_SEG = SceneSegmentation(scenes=[
    ExtractedScene(start=0, end=0, characters_present=["the dog"]),
    ExtractedScene(start=1, end=1, characters_present=[]),
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
        ExtractedScene(start=0, end=0, characters_present=[]),
        ExtractedScene(start=1, end=1, characters_present=[]),
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
        ExtractedScene(start=0, end=0, characters_present=["the dog"]),
        ExtractedScene(start=1, end=1, characters_present=["the cat"]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state(characters=[_char("c0", "the dog"), _char("c1", "the cat")]))
    assert result["scenes"][0].characters_present == ["c0"]
    assert result["scenes"][1].characters_present == ["c1"]


def test_segment_drops_names_not_in_roster():
    """Invariant 6: a name absent from state.characters is silently dropped."""
    seg = SceneSegmentation(scenes=[
        ExtractedScene(start=0, end=0, characters_present=["the dog", "unknown character"]),
        ExtractedScene(start=1, end=1, characters_present=[]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state(characters=[_char("c0", "the dog")]))
    assert result["scenes"][0].characters_present == ["c0"]


def test_segment_empty_roster_gives_empty_characters_present_no_raise():
    """Edge case: roster is empty → every scene gets [] and the node does not raise."""
    seg = SceneSegmentation(scenes=[
        ExtractedScene(start=0, end=0, characters_present=[]),
        ExtractedScene(start=1, end=1, characters_present=[]),
    ])
    with patch("pipeline.segment.segment_scenes", return_value=seg):
        result = segment(_state())  # characters=[]
    for s in result["scenes"]:
        assert s.characters_present == []


def test_segment_prefers_redacted_text():
    """CC-2: segment_scenes receives units from redacted_text, not raw_text."""
    seg = SceneSegmentation(scenes=[ExtractedScene(start=0, end=1, characters_present=[])])
    with patch("pipeline.segment.segment_scenes", return_value=seg) as mock_seg:
        segment(_state(raw="raw version. Still raw.", redacted="redacted version. Still redacted."))
    units_arg = mock_seg.call_args.args[0]
    assert all("redacted" in u for u in units_arg)


def test_segment_falls_back_to_raw_text_when_redacted_is_none():
    """CC-2 fallback: uses raw_text when redacted_text is None."""
    seg = SceneSegmentation(scenes=[ExtractedScene(start=0, end=1, characters_present=[])])
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
    seg = SceneSegmentation(scenes=[ExtractedScene(start=0, end=1, characters_present=[])])
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
