from app.config import (
    IMAGE_BUDGET,
    MAX_SCENES,
    MAX_STORY_WORDS,
    MIN_STORY_WORDS,
    RECURSION_LIMIT,
    STYLE_PRESETS,
    SUPER_STEP_PRELUDE,
    settings,
)


def test_style_presets_has_exactly_three_keys():
    assert set(STYLE_PRESETS.keys()) == {"cel", "comic", "gouache"}


def test_cel_preset_equals_default_style_fragment():
    assert STYLE_PRESETS["cel"] == settings.default_style_fragment


def test_recursion_limit_derives_from_max_scenes_and_the_super_step_prelude():
    """ADR-024's ×4 formula, corrected prelude: 6 linear steps + 3 retry cycles of 3
    (char_bible, char_ref_mod, reveal) = 15 (spec §4.13)."""
    assert SUPER_STEP_PRELUDE == 15
    assert RECURSION_LIMIT == MAX_SCENES * 4 + SUPER_STEP_PRELUDE


def test_recursion_limit_and_image_budget_no_longer_share_a_prelude_term():
    """Spec §4.13: the two backstops are different units and were only ever coincidentally
    equal at 9. Raising one in sympathy with the other would weaken a cost guard."""
    assert RECURSION_LIMIT - MAX_SCENES * 4 != IMAGE_BUDGET - MAX_SCENES * 2


def test_image_budget_is_unchanged_by_the_reveal_prelude():
    assert IMAGE_BUDGET == MAX_SCENES * 2 + 9


def test_moderation_primary_model_is_llama_guard():
    assert settings.moderation_primary_model == "meta-llama/llama-guard-4-12b"


def test_moderation_backstop_model_is_gpt_oss_safeguard():
    assert settings.moderation_backstop_model == "openai/gpt-oss-safeguard-20b"


def test_moderation_backstop_image_model_is_gemma():
    assert settings.moderation_backstop_image_model == "google/gemma-3-27b-it"


def test_min_story_words_is_five():
    assert MIN_STORY_WORDS == 5


def test_max_story_words_is_eight_hundred():
    assert MAX_STORY_WORDS == 800


def test_settings_has_no_dev_classroom_id():
    """spec §9 test 14: sentinel is retired."""
    assert not hasattr(settings, "dev_classroom_id")


def test_settings_has_no_dev_profile_id():
    """spec §9 test 14: sentinel is retired."""
    assert not hasattr(settings, "dev_profile_id")
