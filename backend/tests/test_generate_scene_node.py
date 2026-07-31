import pytest
from unittest.mock import MagicMock, patch

from app.config import IMAGE_BUDGET
from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Cost,
    Input,
    RefVerdict,
    Scene,
    Style,
    StoryMemory,
)
from pipeline.generate_scene import _fal_ref_url, generate_and_store, generate_scene


def _make_supabase(*, has_existing: bool = False) -> MagicMock:
    """Storage mock. has_existing=True → download returns bytes (asset found).
    has_existing=False → download raises (asset not found, proceed to generate)."""
    fake = MagicMock()
    if has_existing:
        fake.storage.from_.return_value.download.return_value = b"existing-bytes"
    else:
        fake.storage.from_.return_value.download.side_effect = Exception("not found")
    return fake


def _state(
    scenes: list[Scene],
    characters: list[Character] | None = None,
    style: Style | None = None,
    cost: Cost | None = None,
) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-123",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x"),
        characters=characters or [],
        style=style or Style(),
        scenes=scenes,
        cost=cost or Cost(),
    )


# --- _fal_ref_url (lru_cache — clear before and after to avoid test cross-contamination) ---

def test_fal_ref_url_downloads_from_storage_and_uploads_to_fal():
    _fal_ref_url.cache_clear()
    fake_supabase = MagicMock()
    fake_supabase.storage.from_.return_value.download.return_value = b"ref-bytes"

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.upload_reference", return_value="https://fal/ref.png") as mock_upload:
        url = _fal_ref_url("job-1/ref-c0.png")

    assert url == "https://fal/ref.png"
    mock_upload.assert_called_once_with(b"ref-bytes")
    _fal_ref_url.cache_clear()


def test_fal_ref_url_memoizes_so_a_second_call_skips_download_and_upload():
    """Spec §6: two calls for the same path perform one download and one upload_reference."""
    _fal_ref_url.cache_clear()
    fake_supabase = MagicMock()
    fake_supabase.storage.from_.return_value.download.return_value = b"ref-bytes"

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.upload_reference", return_value="https://fal/ref.png") as mock_upload:
        url1 = _fal_ref_url("job-1/ref-c0.png")
        url2 = _fal_ref_url("job-1/ref-c0.png")

    assert url1 == url2 == "https://fal/ref.png"
    assert fake_supabase.storage.from_.return_value.download.call_count == 1
    mock_upload.assert_called_once()
    _fal_ref_url.cache_clear()


# --- generate_and_store (providers + Supabase mocked) ---

def test_generate_and_store_uploads_image_bytes_and_returns_paid_true():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.text_to_image", return_value=b"fake-png-bytes"), \
         patch("pipeline.generate_scene._fal_ref_url"):
        path, paid = generate_and_store("a friendly dog", "job-123", "s0", [])

    assert path == "job-123/s0.png"
    assert paid is True
    fake_supabase.storage.from_.assert_called_with("storybook-images")
    fake_supabase.storage.from_.return_value.upload.assert_called_once()


def test_generate_and_store_reuses_existing_storage_asset():
    """CC-10: a re-executed super-step is free."""
    fake_supabase = _make_supabase(has_existing=True)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.edit_image") as mock_edit, \
         patch("pipeline.generate_scene.text_to_image") as mock_text:
        path, paid = generate_and_store("a dog", "job-1", "s0", [])

    assert path == "job-1/s0.png"
    assert paid is False
    mock_edit.assert_not_called()
    mock_text.assert_not_called()


def test_generate_and_store_calls_edit_image_when_refs_given():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene._fal_ref_url", side_effect=lambda p: f"https://fal/{p}"), \
         patch("pipeline.generate_scene.edit_image", return_value=b"img-bytes") as mock_edit, \
         patch("pipeline.generate_scene.text_to_image") as mock_text:
        path, paid = generate_and_store("a dog", "job-1", "s0", ["ref-c0.png"])

    assert path == "job-1/s0.png"
    assert paid is True
    mock_edit.assert_called_once_with("a dog", ["https://fal/ref-c0.png"])
    mock_text.assert_not_called()


def test_generate_and_store_calls_text_to_image_when_no_refs():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.text_to_image", return_value=b"img-bytes") as mock_text, \
         patch("pipeline.generate_scene.edit_image") as mock_edit:
        path, paid = generate_and_store("a dog", "job-1", "s0", [])

    assert path == "job-1/s0.png"
    assert paid is True
    mock_text.assert_called_once_with("a dog")
    mock_edit.assert_not_called()


# --- generate_scene (generate_and_store patched — the node seam) ---

def test_generate_scene_returns_scenes_and_cost_keys():
    """ADR-024: partial-return shape. Cost is always included when a scene is processed."""
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="a friendly dog"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)):
        result = generate_scene(state)

    assert set(result) == {"scenes", "cost"}
    scene, = result["scenes"]
    assert scene.scene_id == "s0"
    assert scene.final_image_ref == "job-123/s0.png"
    assert scene.prompt == "a friendly dog"


def test_generate_scene_records_the_attempt_with_passed_false():
    """CC-5: per-attempt provenance (ADR-010). Attempt.passed=False — only consistency_check writes True."""
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="a friendly dog"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)):
        result = generate_scene(state)

    attempt, = result["scenes"][0].attempts
    assert attempt.image_ref == "job-123/s0.png"
    assert attempt.prompt == "a friendly dog"
    assert attempt.passed is False


def test_generate_scene_picks_the_first_scene_without_an_image():
    """ADR-024: loop position is derived from `final_image_ref is None` — there is no cursor."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="already.png"),
        Scene(scene_id="s1", text_excerpt="1"),
    ])

    with patch("pipeline.generate_scene.build_prompt", return_value="next"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s1.png", True)):
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
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)):
        generate_scene(state)

    build.assert_called_once_with("The dog ran.", ["c0"], [dog], "flat gouache storybook")


def test_generate_scene_uses_scene_id_in_storage_path():
    """Regression: old code hardcoded 'scene-1.png', clobbering every scene in a multi-scene book."""
    state = _state([Scene(scene_id="scene-abc", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/scene-abc.png", True)) as mock_store:
        result = generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "scene-abc", [])
    assert result["scenes"][0].final_image_ref == "job-123/scene-abc.png"


def test_generate_scene_two_successive_invocations_produce_distinct_paths():
    """Regression: old hardcoded scene-1.png made every scene clobber the same Storage object."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0"),
        Scene(scene_id="s1", text_excerpt="1"),
    ])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)):
        result1 = generate_scene(state)

    # Simulate LangGraph applying the partial return before the second invocation
    updated = state.model_copy(update={"scenes": [
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-123/s0.png"),
        Scene(scene_id="s1", text_excerpt="1"),
    ]})

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s1.png", True)):
        result2 = generate_scene(updated)

    path1 = result1["scenes"][0].final_image_ref
    path2 = result2["scenes"][0].final_image_ref
    assert path1 != path2


def test_generate_scene_bumps_cost_image_count_when_paid():
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)):
        result = generate_scene(state)

    assert result["cost"].image_count == 1


def test_generate_scene_does_not_bump_cost_when_asset_reused():
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", False)):
        result = generate_scene(state)

    assert result["cost"].image_count == 0


def test_generate_scene_raises_before_calling_helper_when_image_budget_reached():
    """ADR-025 D4: breaker is evaluated before any fal spend."""
    state = _state(
        [Scene(scene_id="s0", text_excerpt="x")],
        cost=Cost(image_count=IMAGE_BUDGET),
    )

    with patch("pipeline.generate_scene.generate_and_store") as mock_store, \
         pytest.raises(RuntimeError):
        generate_scene(state)

    mock_store.assert_not_called()


def test_generate_scene_collects_refs_only_for_present_characters_with_canonical_images():
    dog = Character(char_id="c0", name="dog", description=CharacterDescription(),
                    canonical_ref_image="job-123/ref-c0.png")
    cat = Character(char_id="c1", name="cat", description=CharacterDescription(),
                    canonical_ref_image=None)
    state = _state(
        [Scene(scene_id="s0", text_excerpt="x", characters_present=["c0", "c1"])],
        characters=[dog, cat],
    )

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)) as mock_store:
        generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "s0", ["job-123/ref-c0.png"])


def test_generate_scene_skips_absent_char_id_when_collecting_refs():
    dog = Character(char_id="c0", name="dog", description=CharacterDescription(),
                    canonical_ref_image="job-123/ref-c0.png")
    state = _state(
        [Scene(scene_id="s0", text_excerpt="x", characters_present=["c0", "ghost-id"])],
        characters=[dog],
    )

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)) as mock_store:
        generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "s0", ["job-123/ref-c0.png"])


def test_generate_scene_includes_ref_even_when_verdict_failed():
    """ADR-028: a failing ref_verdict still ships its reference.
    Filtering it would silently degrade the scene to text-to-image."""
    dog = Character(
        char_id="c0", name="dog", description=CharacterDescription(),
        canonical_ref_image="job-123/ref-c0.png",
        ref_verdict=RefVerdict(differences_observed="wrong color", matches_description=False),
    )
    state = _state(
        [Scene(scene_id="s0", text_excerpt="x", characters_present=["c0"])],
        characters=[dog],
    )

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0.png", True)) as mock_store:
        generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "s0", ["job-123/ref-c0.png"])
