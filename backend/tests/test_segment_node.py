from pipeline.segment import split_sentences

from unittest.mock import patch

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
from pipeline.segment import segment


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
