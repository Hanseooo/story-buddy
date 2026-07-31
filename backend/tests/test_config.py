from app.config import STYLE_PRESETS, settings


def test_style_presets_has_exactly_three_keys():
    assert set(STYLE_PRESETS.keys()) == {"cel", "comic", "gouache"}


def test_cel_preset_equals_default_style_fragment():
    assert STYLE_PRESETS["cel"] == settings.default_style_fragment
