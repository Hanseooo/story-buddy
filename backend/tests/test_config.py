from app.config import IMAGE_BUDGET, MAX_SCENES, RECURSION_LIMIT, STYLE_PRESETS, settings


def test_style_presets_has_exactly_three_keys():
    assert set(STYLE_PRESETS.keys()) == {"cel", "comic", "gouache"}


def test_cel_preset_equals_default_style_fragment():
    assert STYLE_PRESETS["cel"] == settings.default_style_fragment


def test_recursion_limit_derives_from_max_scenes_at_four_visits_per_scene():
    """ADR-024's formula: max_scenes × 4 + fixed_prelude. The ×4 is generate_scene,
    consistency_check, regenerate, consistency_check — the deepest a single scene can go."""
    assert RECURSION_LIMIT == MAX_SCENES * 4 + 9


def test_recursion_limit_shares_its_prelude_term_with_image_budget():
    """ADR-025 D4: the domain-level and graph-level backstops share ONE number.
    The prelude is 9 in both, deliberately generous today (it is really 5) to leave
    headroom for ADR-029's Phase-2 `reveal` node."""
    assert RECURSION_LIMIT - MAX_SCENES * 4 == IMAGE_BUDGET - MAX_SCENES * 2


def test_moderation_primary_model_is_qwen3_guard_gen():
    assert settings.moderation_primary_model == "Qwen/Qwen3-Guard-Gen-0.6B"


def test_moderation_backstop_model_is_gpt_oss_safeguard():
    assert settings.moderation_backstop_model == "openai/gpt-oss-safeguard-20b"


def test_moderation_backstop_image_model_is_gemma():
    assert settings.moderation_backstop_image_model == "google/gemma-3-27b-it"
