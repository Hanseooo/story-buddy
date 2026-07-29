from unittest.mock import MagicMock, patch

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, Scene, StoryMemory
from pipeline.generate_scene import generate_and_store, generate_scene


def test_generate_and_store_uploads_image_bytes():
    fake_supabase = MagicMock()

    with patch("pipeline.generate_scene.text_to_image", return_value=b"fake-png-bytes"), \
         patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase):
        path = generate_and_store("a friendly dog", "job-123")

    assert path == "job-123/scene-1.png"
    fake_supabase.storage.from_.assert_called_with("storybook-images")
    fake_supabase.storage.from_.return_value.upload.assert_called_once()


def _state(scenes: list[Scene]) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-123",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x"),
        scenes=scenes,
    )


def test_generate_scene_returns_a_partial_scene_update():
    """ADR-024: partial-return, not mutate-and-return. The node returns ONLY the scene it wrote."""
    state = _state([Scene(scene_id="s0", text_excerpt="x", caption="a friendly dog")])

    with patch("pipeline.generate_scene.generate_and_store", return_value="job-123/scene-1.png"):
        result = generate_scene(state)

    assert set(result) == {"scenes"}
    scene, = result["scenes"]
    assert scene.scene_id == "s0"
    assert scene.final_image_ref == "job-123/scene-1.png"
    assert scene.prompt == "a friendly dog"


def test_generate_scene_records_the_attempt_for_provenance():
    """CC-5: Scene.prompt alone loses per-attempt provenance once regeneration corrects it (ADR-010)."""
    state = _state([Scene(scene_id="s0", text_excerpt="x", caption="a friendly dog")])

    with patch("pipeline.generate_scene.generate_and_store", return_value="job-123/scene-1.png"):
        result = generate_scene(state)

    attempt, = result["scenes"][0].attempts
    assert attempt.image_ref == "job-123/scene-1.png"
    assert attempt.prompt == "a friendly dog"


def test_generate_scene_picks_the_first_scene_without_an_image():
    """ADR-024: loop position is derived from `final_image_ref is None` — there is no cursor."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0", caption="done", final_image_ref="already.png"),
        Scene(scene_id="s1", text_excerpt="1", caption="next"),
    ])

    with patch("pipeline.generate_scene.generate_and_store", return_value="job-123/scene-2.png"):
        result = generate_scene(state)

    scene, = result["scenes"]
    assert scene.scene_id == "s1"


def test_generate_scene_is_a_no_op_when_every_scene_has_an_image():
    state = _state([Scene(scene_id="s0", text_excerpt="0", final_image_ref="already.png")])

    with patch("pipeline.generate_scene.generate_and_store") as mock_store:
        result = generate_scene(state)

    assert result == {}
    mock_store.assert_not_called()
