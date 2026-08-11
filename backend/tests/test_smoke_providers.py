"""Does every model named in `app/config.py` actually work with the provider we call it through?

Nothing else in this suite can answer that. Every other test mocks `providers`, correctly — but
that means the suite is green for a deployment that cannot complete a single job. Three separate
production outages in one week were all this class:

  * `qwen/qwen3-32b` accepted `response_format` and emitted prose (prod job af068baf)
  * `llama-guard-3-8b` had been retired by the provider — 404 on every moderation call
  * `moderation_primary_image_model` pointed at a model with no vision support

Run before any deploy that changes a model name, a base URL, or a provider:

    uv run pytest -m "smoke and not smoke_image"   # text, judge, moderation — six pings
    uv run pytest -m smoke                         # the above plus one paid fal.ai draw

Deselected by default (`addopts` in pyproject.toml) — these hit real APIs and cost real money.
The `smoke` half is a rounding error on ~10-token prompts. The `smoke_image` half is one image;
the pipeline itself draws up to 6 reference images per job before it reaches a single page, so a
smoke run is a fraction of one real job. Split anyway, so the free 90% is never gated on the
paid 10%.

These tests assert the CONTRACT the pipeline depends on, not output quality. A judge that
answers "no" to a matching image is a bad judge; a judge that returns unparsable JSON, or emits
`matches_description` before `differences_observed`, is a broken deployment. Only the second
kind is a failure here — otherwise this file goes red for reasons no deploy can fix, and people
learn to ignore it.
"""
import base64

import pytest
from pydantic import BaseModel

from app.config import settings

pytestmark = pytest.mark.smoke


# 1x1 transparent PNG. The vision models only have to ACCEPT an image; nothing is asked about it.
_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
_PIXEL_URI = "data:image/png;base64," + base64.b64encode(_PIXEL).decode()


def _require_real_keys():
    """`tests/conftest.py` seeds placeholder credentials so the mocked suite can import. Those
    reach OpenRouter as a 401, which would read as "the model is broken" — the one wrong
    conclusion this file exists to prevent."""
    if settings.openrouter_api_key.startswith("test-"):
        pytest.skip("placeholder credentials — smoke tests need the real .env")


@pytest.fixture(autouse=True)
def _keys():
    _require_real_keys()


class _Colour(BaseModel):
    """Deliberately trivial. A model that cannot fill this cannot do structured output at all,
    which is precisely the qwen3-32b failure — it is not a test of intelligence."""
    colour: str


def test_text_model_honours_structured_output():
    from providers import structured_text

    result = structured_text("Name one colour. Answer with the colour only.", _Colour)
    assert result.colour.strip(), f"{settings.text_model} returned an empty structured field"


class _SmokeVerdict(BaseModel):
    """Mirrors the reason-then-score shape of `RefVerdict`/`VlmVerdict` (ADR-004) so the wire
    ordering `providers._assert_field_order` enforces is exercised, not just structured output."""
    differences_observed: str
    matches_description: bool


def test_judge_model_accepts_an_image_and_keeps_reason_before_score():
    """`judge` raises if the provider emits fields out of schema order, so reaching the assert at
    all is most of the signal — a provider that reorders voids ADR-004 silently in production."""
    from providers import judge

    verdict = judge("Describe this image, then say whether it matches 'a blank square'.",
                    [_PIXEL_URI], _SmokeVerdict)
    assert isinstance(verdict.matches_description, bool)


def test_both_text_moderation_models_pass_benign_text():
    """Benign input is the only case with one correct answer. A flag here means the model is
    retired, wrongly named, or not a guard model — all deployment failures, none of them taste."""
    from providers import classify_text_backstop, classify_text_primary

    primary_safe, _ = classify_text_primary("A little girl finds a lost star and helps it home.")
    backstop_safe, _ = classify_text_backstop("A little girl finds a lost star and helps it home.")

    assert primary_safe is True, f"{settings.moderation_primary_model} flagged a benign story"
    assert backstop_safe is True, f"{settings.moderation_backstop_model} flagged a benign story"


def test_both_image_moderation_models_accept_an_image():
    """Returns bool, so a vision-less model cannot fail "safely" — it errors, which is the point.
    The verdict itself is not asserted: a 1x1 pixel is not a meaningful moderation subject."""
    from providers import classify_image_backstop, classify_image_primary

    assert isinstance(classify_image_primary(_PIXEL_URI), bool)
    assert isinstance(classify_image_backstop(_PIXEL_URI), bool)


@pytest.mark.smoke_image
def test_image_model_returns_bytes():
    """The one paid call. `char_bible` hardcodes PNG in `_data_uri`, so the magic number is
    checked — a provider silently switching to JPEG would break the judge, not the draw, and
    would surface as an unexplained verdict failure rather than an image failure."""
    from providers import text_to_image

    image = text_to_image("a plain grey circle on a white background")
    assert image[:8] == b"\x89PNG\r\n\x1a\n", f"{settings.fal_image_model} did not return a PNG"
