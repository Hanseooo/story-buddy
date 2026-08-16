import logging
import pytest
from unittest.mock import MagicMock, patch

from app.config import IMAGE_BUDGET, settings
from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Cost,
    Input,
    Location,
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
    updated_scenes = [
        s.model_copy(update={"visual_direction": "The subject performs an action."})
        if not s.visual_direction
        else s
        for s in scenes
    ]
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-123",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x"),
        characters=characters or [],
        style=style or Style(),
        scenes=updated_scenes,
        cost=cost or Cost(),
    )


# --- _fal_ref_url (short-lived signed URL per fal request) ---

def test_fal_ref_url_returns_the_signed_url_for_its_reference_path():
    with patch(
        "pipeline.generate_scene.get_signed_url", return_value="https://supabase/ref.png"
    ) as mock_signed_url:
        url = _fal_ref_url("job-1/ref-c0.png")

    assert url == "https://supabase/ref.png"
    mock_signed_url.assert_called_once_with("job-1/ref-c0.png")


def test_fal_ref_url_does_not_cache_expiring_signed_urls():
    with patch(
        "pipeline.generate_scene.get_signed_url",
        side_effect=["https://supabase/ref-1.png", "https://supabase/ref-2.png"],
    ) as mock_signed_url:
        url1 = _fal_ref_url("job-1/ref-c0.png")
        url2 = _fal_ref_url("job-1/ref-c0.png")

    assert url1 == "https://supabase/ref-1.png"
    assert url2 == "https://supabase/ref-2.png"
    assert mock_signed_url.call_count == 2


# --- generate_and_store (providers + Supabase mocked) ---

def test_generate_and_store_uploads_image_bytes_and_returns_paid_true():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.text_to_image", return_value=b"fake-png-bytes"), \
         patch("pipeline.generate_scene._fal_ref_url"):
        path, paid = generate_and_store("a friendly dog", "job-123", "s0", 1, [])

    assert path == "job-123/s0-1.png"
    assert paid is True
    fake_supabase.storage.from_.assert_called_with("storybook-images")
    fake_supabase.storage.from_.return_value.upload.assert_called_once()


def test_generate_and_store_reuses_existing_storage_asset():
    """CC-10: a re-executed super-step is free. Now per-ATTEMPT, not per-scene."""
    fake_supabase = _make_supabase(has_existing=True)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.edit_image") as mock_edit, \
         patch("pipeline.generate_scene.text_to_image") as mock_text:
        path, paid = generate_and_store("a dog", "job-1", "s0", 1, [])

    assert path == "job-1/s0-1.png"
    assert paid is False
    mock_edit.assert_not_called()
    mock_text.assert_not_called()


def test_generate_and_store_calls_edit_image_when_refs_given():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene._fal_ref_url", side_effect=lambda p: f"https://fal/{p}"), \
         patch("pipeline.generate_scene.edit_image", return_value=b"img-bytes") as mock_edit, \
         patch("pipeline.generate_scene.text_to_image") as mock_text:
        path, paid = generate_and_store("a dog", "job-1", "s0", 1, ["ref-c0.png"])

    assert path == "job-1/s0-1.png"
    assert paid is True
    mock_edit.assert_called_once_with("a dog", ["https://fal/ref-c0.png"])
    mock_text.assert_not_called()


def test_generate_and_store_calls_text_to_image_when_no_refs():
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.text_to_image", return_value=b"img-bytes") as mock_text, \
         patch("pipeline.generate_scene.edit_image") as mock_edit:
        path, paid = generate_and_store("a dog", "job-1", "s0", 1, [])

    assert path == "job-1/s0-1.png"
    assert paid is True
    mock_text.assert_called_once_with("a dog")
    mock_edit.assert_not_called()


def test_generate_and_store_gives_two_attempts_of_one_scene_distinct_paths():
    """The prerequisite for ADR-010 best-of (spec §4). At a shared per-scene path the CC-10
    exists-skip would find attempt 1, return paid=False, and hand back attempt 1's OWN bytes —
    so attempt 2 is never drawn and best-of ranks an image against itself."""
    fake_supabase = _make_supabase(has_existing=False)

    with patch("pipeline.generate_scene.get_supabase_client", return_value=fake_supabase), \
         patch("pipeline.generate_scene.text_to_image", return_value=b"img-bytes"):
        path1, _ = generate_and_store("a dog", "job-1", "s0", 1, [])
        path2, _ = generate_and_store("a corrected dog", "job-1", "s0", 2, [])

    assert path1 == "job-1/s0-1.png"
    assert path2 == "job-1/s0-2.png"
    assert path1 != path2


# --- generate_scene (generate_and_store patched — the node seam) ---

def test_generate_scene_returns_scenes_and_cost_keys():
    """ADR-024: partial-return shape. Cost is always included when a scene is processed."""
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="a friendly dog"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)):
        result = generate_scene(state)

    assert set(result) == {"scenes", "cost"}
    scene, = result["scenes"]
    assert scene.scene_id == "s0"
    # Ownership transfer (consistency-checker §3): generate_scene appends an Attempt and leaves
    # the scene UNFINALIZED so consistency_check's identical selection rule finds the same scene.
    assert scene.final_image_ref is None
    assert scene.attempts[-1].image_ref == "job-123/s0-1.png"
    assert scene.prompt == "a friendly dog"


def test_generate_scene_records_the_attempt_with_passed_false():
    """CC-5: per-attempt provenance (ADR-010). Attempt.passed=False — only consistency_check writes True."""
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="a friendly dog"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)):
        result = generate_scene(state)

    attempt, = result["scenes"][0].attempts
    assert attempt.image_ref == "job-123/s0-1.png"
    assert attempt.prompt == "a friendly dog"
    assert attempt.passed is False


def test_generate_scene_picks_the_first_scene_without_an_image():
    """ADR-024: loop position is derived from `final_image_ref is None` — there is no cursor."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="already.png"),
        Scene(scene_id="s1", text_excerpt="1"),
    ])

    with patch("pipeline.generate_scene.build_prompt", return_value="next"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s1-1.png", True)):
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
    """Spec §6: generate_scene calls build_prompt with (scene.characters_present,
    state.characters, state.style.prompt_fragment, location, scene.objects_present,
    state.objects, scene.visual_direction)."""
    dog = Character(char_id="c0", name="the dog", description=CharacterDescription(species="dog"))
    state = _state(
        [Scene(scene_id="s0", text_excerpt="The dog ran.", characters_present=["c0"], visual_direction="The dog runs.")],
        characters=[dog],
        style=Style(prompt_fragment="flat gouache storybook"),
    )

    with patch("pipeline.generate_scene.build_prompt", return_value="built") as build, \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)):
        generate_scene(state)

    build.assert_called_once_with(
        ["c0"], [dog], "flat gouache storybook", None, [], [], "The dog runs."
    )


def test_generate_scene_uses_scene_id_in_storage_path():
    """Regression: old code hardcoded 'scene-1.png', clobbering every scene in a multi-scene book."""
    state = _state([Scene(scene_id="scene-abc", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/scene-abc-1.png", True)) as mock_store:
        result = generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "scene-abc", 1, [])
    assert result["scenes"][0].final_image_ref is None
    assert result["scenes"][0].attempts[-1].image_ref == "job-123/scene-abc-1.png"


def test_generate_scene_two_successive_invocations_produce_distinct_paths():
    """Regression: old hardcoded scene-1.png made every scene clobber the same Storage object."""
    state = _state([
        Scene(scene_id="s0", text_excerpt="0"),
        Scene(scene_id="s1", text_excerpt="1"),
    ])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)):
        result1 = generate_scene(state)

    # Simulate LangGraph applying the partial return before the second invocation
    updated = state.model_copy(update={"scenes": [
        Scene(scene_id="s0", text_excerpt="0", final_image_ref="job-123/s0-1.png", visual_direction="Action 0"),
        Scene(scene_id="s1", text_excerpt="1", visual_direction="Action 1"),
    ]})

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s1-1.png", True)):
        result2 = generate_scene(updated)

    path1 = result1["scenes"][0].attempts[-1].image_ref
    path2 = result2["scenes"][0].attempts[-1].image_ref
    assert path1 != path2


def test_generate_scene_bumps_cost_image_count_when_paid():
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)):
        result = generate_scene(state)

    assert result["cost"].image_count == 1


def test_generate_scene_does_not_bump_cost_when_asset_reused():
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", False)):
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
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)) as mock_store:
        generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "s0", 1, ["job-123/ref-c0.png"])


def test_generate_scene_skips_absent_char_id_when_collecting_refs():
    dog = Character(char_id="c0", name="dog", description=CharacterDescription(),
                    canonical_ref_image="job-123/ref-c0.png")
    state = _state(
        [Scene(scene_id="s0", text_excerpt="x", characters_present=["c0", "ghost-id"])],
        characters=[dog],
    )

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)) as mock_store:
        generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "s0", 1, ["job-123/ref-c0.png"])


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
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)) as mock_store:
        generate_scene(state)

    mock_store.assert_called_once_with("p", "job-123", "s0", 1, ["job-123/ref-c0.png"])


def test_generate_scene_passes_attempt_n_of_one_for_a_scene_with_no_attempts():
    """Spec §6: attempt_n is len(scene.attempts) + 1 at BOTH call sites. generate_scene only
    ever sees a scene with no attempts, so it is always 1 here — regenerate is where it is 2."""
    state = _state([Scene(scene_id="s0", text_excerpt="x")])

    with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)) as mock_store:
        generate_scene(state)

    assert mock_store.call_args.args[3] == 1


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

    assert build.call_args.args[3] == hill


def test_generate_scene_passes_none_when_the_scene_has_no_location():
    state = _state([Scene(scene_id="s0", text_excerpt="She ran.")])

    with patch("pipeline.generate_scene.build_prompt", return_value="built") as build, \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)):
        generate_scene(state)

    assert build.call_args.args[3] is None


def test_generate_scene_passes_none_for_a_location_id_absent_from_the_roster():
    """Same posture as every other roster lookup in this pipeline: this node may not extend the
    roster, and it does not raise. The page ships with no `Setting:` line."""
    beach = Location(loc_id="loc0", name="the beach")
    state = _state([Scene(scene_id="s0", text_excerpt="She ran.", location_id="ghost-loc")])
    state = state.model_copy(update={"locations": [beach]})

    with patch("pipeline.generate_scene.build_prompt", return_value="built") as build, \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)):
        generate_scene(state)

    assert build.call_args.args[3] is None


def test_generate_scene_rejects_legacy_scene_with_no_visual_direction():
    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-123",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x"),
        scenes=[Scene(scene_id="s0", text_excerpt="x", visual_direction="")],
    )
    with patch("pipeline.generate_scene.generate_and_store") as mock_store:
        with pytest.raises(ValueError, match="has no visual_direction"):
            generate_scene(state)
    mock_store.assert_not_called()


def test_generate_scene_log_names_configured_image_model_and_prompt_version(caplog):
    state = _state([Scene(scene_id="s0", text_excerpt="x")])
    with caplog.at_level(logging.INFO, logger="pipeline.generate_scene"):
        with patch("pipeline.generate_scene.build_prompt", return_value="p"), \
             patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)):
            generate_scene(state)

    assert settings.fal_image_model in caplog.text
    assert "scene_prompt_version=2" in caplog.text
    assert "prompt_len=" in caplog.text


def test_generate_scene_stores_prompt_byte_for_byte_in_scene_and_attempt():
    state = _state([Scene(scene_id="s0", text_excerpt="x")])
    with patch("pipeline.generate_scene.build_prompt", return_value="exact-prompt-string-123"), \
         patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)) as mock_store:
        result = generate_scene(state)

    scene = result["scenes"][0]
    assert scene.prompt == "exact-prompt-string-123"
    assert scene.attempts[-1].prompt == "exact-prompt-string-123"
    assert mock_store.call_args.args[0] == "exact-prompt-string-123"


def test_generate_scene_text_to_image_branch_receives_no_fake_reference_labels():
    state = _state([
        Scene(
            scene_id="s0",
            text_excerpt="The storm raged.",
            characters_present=[],
            visual_direction="A storm over the sea. Viewpoint: wide. Framing: wide shot.",
        )
    ])
    with patch("pipeline.generate_scene.generate_and_store", return_value=("job-123/s0-1.png", True)) as mock_store:
        generate_scene(state)

    prompt_sent = mock_store.call_args.args[0]
    assert "Image 1" not in prompt_sent
    assert "Image 2" not in prompt_sent
    assert "Use them only as references" not in prompt_sent
    assert mock_store.call_args.args[4] == []

