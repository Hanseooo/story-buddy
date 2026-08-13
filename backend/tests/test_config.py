import re

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
from pipeline.prompt_optimizer import style_prohibitions
from providers import NEGATIVE_PROMPT


def test_style_presets_has_exactly_three_keys():
    assert set(STYLE_PRESETS.keys()) == {"cel", "comic", "gouache"}


def test_cel_preset_equals_default_style_fragment():
    assert STYLE_PRESETS["cel"] == settings.default_style_fragment


def test_no_preset_utters_a_term_the_negative_prompt_suppresses():
    """The inverse of the assertion that stood here until 2026-08-13, which required every fragment
    to END "no speech bubbles, no captions, no lettering". It was stated on all three after prod
    job d83721d9's s2 lettered a speech balloon — and prod kept lettering them, because a `no
    <term>` clause in a positive prompt competes with what Qwen-Image is best at and loses
    (`providers.NEGATIVE_PROMPT`'s comment). A cel run on 2026-08-13 still came back with chat
    bubbles.

    The ban did not weaken; it moved to the channel that subtracts. What is forbidden here is
    NAMING those things at all, which is the only thing that ever put them on the canvas.

    Same invariant as `test_char_bible_node`'s positive/negative test, and it exists for the same
    reason: that bug came back twice while being fixed.
    """
    terms = [term.strip() for term in NEGATIVE_PROMPT.split(",")]
    for name, fragment in STYLE_PRESETS.items():
        for term in terms:
            assert not re.search(rf"\b{re.escape(term)}\b", fragment, re.I), \
                f"{name} names {term!r}, which its own negative prompt is trying to subtract"


def test_outline_treatment_is_what_separates_the_three_presets():
    """`gouache` asked for "thick confident ink outlines" until 2026-08-13 and the model overrode
    it — the seed-21 picker sample has no keyline anywhere, which is the look the preset is for.
    Left as a clause the model may or may not honour, that coin is flipped ONCE: `char_bible` mints
    the reference from this fragment and every page inherits it, so a whole book comes back outlined
    or not outlined on the same seed. A prod gouache run landed outlined; the sample did not.

    Stating the absence makes the outcome the specification instead of luck, and it is also the only
    axis on which the three presets genuinely differ — strip it and `gouache` is `cel` with grain.
    """
    assert "outlines" in style_prohibitions(STYLE_PRESETS["gouache"])
    assert "outlines" not in style_prohibitions(STYLE_PRESETS["cel"])
    assert "outlines" not in style_prohibitions(STYLE_PRESETS["comic"])


def test_no_preset_asks_for_a_thing_its_own_no_clause_forbids():
    """The self-contradiction case of the test above it. `gouache` shipped one for three weeks in
    the other direction, and a fragment that both names and negates a term hands the model the
    choice — which is the failure mode this whole file keeps re-learning."""
    for name, fragment in STYLE_PRESETS.items():
        asked = ", ".join(
            clause for clause in fragment.split(",")
            if clause.strip().lower().split()[:1] != ["no"]
        )
        for term in style_prohibitions(fragment):
            assert not re.search(rf"\b{re.escape(term)}\b", asked, re.I), \
                f"{name} asks for {term!r} and forbids it in the same fragment"


def test_recursion_limit_derives_from_max_scenes_and_the_super_step_prelude():
    """ADR-024's formula, corrected prelude: 6 linear steps + 3 retry cycles of 3
    (char_bible, char_ref_mod, reveal) = 15 (spec §4.13).

    ×4 → ×5 on 2026-08-13: `output_mod` moved inside the scene loop, so the deepest a single scene
    can go is now generate_scene → consistency_check → regenerate → consistency_check → output_mod.
    Left at ×4, a 15-scene book where every scene regenerates would die on recursion_limit rather
    than on anything real.

    15 → 17 on 2026-08-13: `reference-moderation-retry` closes a char_bible → char_ref_mod →
    char_bible loop that can run once, which is exactly one extra pair of super-steps.
    """
    assert SUPER_STEP_PRELUDE == 17
    assert RECURSION_LIMIT == MAX_SCENES * 5 + SUPER_STEP_PRELUDE


def test_recursion_limit_and_image_budget_no_longer_share_a_prelude_term():
    """Spec §4.13: the two backstops are different units and were only ever coincidentally
    equal at 9. Raising one in sympathy with the other would weaken a cost guard."""
    assert RECURSION_LIMIT - MAX_SCENES * 5 != IMAGE_BUDGET - MAX_SCENES * 2


def test_each_prelude_equals_its_documented_decomposition():
    """§6 test 18. Both constants carry their arithmetic in a comment, and a comment that
    disagrees with its number is worse than no comment. This is what stops them drifting apart.

    The two are DIFFERENT UNITS — images against super-steps — and were only ever coincidentally
    equal at 9. They are asserted separately, and never derived from each other.
    """
    # 6 = 2 refs x 3 draws · 3 = ADR-029 taps · 6 = one moderation redraw cycle, both refs
    assert IMAGE_BUDGET == MAX_SCENES * 2 + (6 + 3 + 6)
    # 6 linear steps · 3 reveal retry cycles of 3 · 2 = one extra char_bible + char_ref_mod pair
    assert SUPER_STEP_PRELUDE == 6 + 3 * 3 + 2


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
