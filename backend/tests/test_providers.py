from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

import providers


def _fake_completion(parsed, content: str = ""):
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(parsed=parsed, content=content))]
    return completion


class _Caption(BaseModel):
    """Local throwaway schema. Provider tests must not import a pipeline node —
    the dependency runs backwards (spec §9)."""
    caption: str


def test_structured_text_requires_provider_parameters():
    """Without require_parameters, OpenRouter silently downgrades strict json_schema (ADR-002)."""
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(_Caption(caption="hi"))
        providers.structured_text("prompt", _Caption)

    kwargs = parse.call_args.kwargs
    assert kwargs["extra_body"] == {"provider": {"require_parameters": True}}
    assert kwargs["response_format"] is _Caption
    assert kwargs["model"] == "qwen/qwen3-32b"


def test_structured_text_raises_when_nothing_parsed():
    with patch("providers.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.parse.return_value = _fake_completion(None)
        with pytest.raises(ValueError):
            providers.structured_text("prompt", _Caption)


def test_judge_sends_images_as_multimodal_content():
    """The judge is only ever called with reference + scene. A text-only call is a broken judge."""
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(_Caption(caption="hi"))
        providers.judge("compare", ["https://ref.png", "https://scene.png"], _Caption)

    content = parse.call_args.kwargs["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "compare"}
    assert [part["image_url"]["url"] for part in content[1:]] == ["https://ref.png", "https://scene.png"]


class _Verdict(BaseModel):
    differences_observed: str
    same_character: bool


def test_chat_rejects_fields_emitted_out_of_schema_order():
    """Pydantic validates order-insensitively, so reason-then-score dies silently without
    the raw-text order guard (ADR-004 amendment)."""
    raw = '{"same_character": true, "differences_observed": "none"}'
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(
            _Verdict(differences_observed="none", same_character=True), content=raw
        )
        with pytest.raises(ValueError, match="schema order"):
            providers.judge("compare", ["https://ref.png", "https://scene.png"], _Verdict)


def test_chat_accepts_fields_in_schema_order():
    raw = '{"differences_observed": "none", "same_character": true}'
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(
            _Verdict(differences_observed="none", same_character=True), content=raw
        )
        verdict = providers.judge("compare", ["https://ref.png", "https://scene.png"], _Verdict)
    assert verdict.same_character is True


class _Verdict3(BaseModel):
    differences_observed: str
    failure_reason: str
    same_character: bool


def test_chat_accepts_when_early_value_quotes_a_later_field_name():
    """Regression (D-D): the old substring scan false-triggered on 3+ field verdicts when an early
    field's value quoted a later field's name. Parsed-key-order reads real keys and is immune."""
    raw = (
        '{"differences_observed": "mentions \\"same_character\\" here", '
        '"failure_reason": "none", "same_character": true}'
    )
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(
            _Verdict3(differences_observed="x", failure_reason="none", same_character=True),
            content=raw,
        )
        verdict = providers.judge("compare", ["https://ref.png"], _Verdict3)
    assert verdict.same_character is True


def test_judge_omits_openrouter_flag_when_self_hosted():
    """vLLM rejects OpenRouter's `provider` field; the swap to Modal is config-only (ADR-019)."""
    with patch("providers.OpenAI") as mock_openai, \
         patch.object(providers.settings, "judge_base_url", "https://x.modal.run/v1"):
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(_Caption(caption="hi"))
        providers.judge("compare", ["https://ref.png"], _Caption)

    assert parse.call_args.kwargs["extra_body"] == {}


def test_edit_image_passes_references_and_seed_and_returns_bytes():
    """The endpoint is pinned, not read from the ambient default: this asserts Qwen's `image_urls`
    mapping, and without the pin a `FAL_IMAGE_EDIT_MODEL` line in a developer's `.env` fails it
    (2026-07-29, Phase-0.5 Run 3). Unit tests must not depend on local env."""
    fal = MagicMock()
    fal.subscribe.return_value = {"images": [{"url": "https://fal.example/x.png"}], "seed": 7}
    response = MagicMock(content=b"png-bytes")

    with patch("providers._fal", return_value=fal), \
         patch("providers.httpx.get", return_value=response) as mock_get, \
         patch.object(providers.settings, "fal_image_edit_model", "fal-ai/qwen-image-edit-2511"):
        image_bytes = providers.edit_image("a fox", ["https://ref/1.png"], seed=7)

    assert image_bytes == b"png-bytes"
    endpoint, = fal.subscribe.call_args.args
    assert endpoint == "fal-ai/qwen-image-edit-2511"
    assert fal.subscribe.call_args.kwargs["arguments"] == {
        "output_format": "png",
        "prompt": "a fox",
        "image_urls": ["https://ref/1.png"],
        "seed": 7,
    }
    mock_get.assert_called_once()


def test_edit_image_renames_reference_field_per_endpoint():
    """OmniGen2 calls it `input_image_urls`. fal drops unknown keys silently, so sending Qwen's
    name here would degrade every scene to text-to-image with no error (pre-flight 2026-07-29)."""
    fal = MagicMock()
    fal.subscribe.return_value = {"images": [{"url": "https://fal.example/x.png"}], "seed": 1}

    with patch("providers._fal", return_value=fal), \
         patch("providers.httpx.get", return_value=MagicMock(content=b"png")), \
         patch.object(providers.settings, "fal_image_edit_model", "fal-ai/omnigen-v2"):
        providers.edit_image("a fox", ["https://ref/1.png"])

    arguments = fal.subscribe.call_args.kwargs["arguments"]
    assert arguments["input_image_urls"] == ["https://ref/1.png"]
    assert "image_urls" not in arguments


def test_edit_image_refuses_endpoint_with_unverified_reference_field():
    """A new fallback rung must fail loudly, not silently ignore the reference (ADR-001)."""
    with patch.object(providers.settings, "fal_image_edit_model", "fal-ai/some-new-rung"), \
         pytest.raises(ValueError, match="reference-image field name unknown"):
        providers.edit_image("a fox", ["https://ref/1.png"])


def test_text_to_image_omits_seed_when_not_given():
    fal = MagicMock()
    fal.subscribe.return_value = {"images": [{"url": "https://fal.example/x.png"}], "seed": 1}

    with patch("providers._fal", return_value=fal), \
         patch("providers.httpx.get", return_value=MagicMock(content=b"png")):
        providers.text_to_image("a fox")

    assert "seed" not in fal.subscribe.call_args.kwargs["arguments"]


# --- redact_pii ---

def test_redact_pii_returns_string():
    """Smoke test: redact_pii returns a string (real Presidio is an integration concern)."""
    with patch("providers._presidio", return_value=(MagicMock(analyze=lambda **kw: []), MagicMock(anonymize=lambda **kw: MagicMock(text="clean text")))):
        from providers import redact_pii
        result = redact_pii("My name is Juan dela Cruz")
    assert isinstance(result, str)


# --- classify_text_primary ---

def test_classify_text_primary_returns_safe_tuple():
    mock_tokenizer = MagicMock()
    mock_tokenizer.apply_chat_template.return_value = MagicMock(shape=MagicMock(__getitem__=lambda s, i: 5))
    mock_tokenizer.decode.return_value = "safe"
    mock_model = MagicMock()
    mock_model.generate.return_value = [[0] * 10]

    with patch("providers._qwen3_guard", return_value=(mock_tokenizer, mock_model)):
        from providers import classify_text_primary
        safe, categories = classify_text_primary("A dog runs in a field.")

    assert isinstance(safe, bool)
    assert isinstance(categories, list)


def test_classify_text_primary_unsafe_response_is_not_safe():
    mock_tokenizer = MagicMock()
    mock_tokenizer.apply_chat_template.return_value = MagicMock(shape=MagicMock(__getitem__=lambda s, i: 5))
    mock_tokenizer.decode.return_value = "unsafe\nS1: Violence"
    mock_model = MagicMock()
    mock_model.generate.return_value = [[0] * 10]

    with patch("providers._qwen3_guard", return_value=(mock_tokenizer, mock_model)):
        from providers import classify_text_primary
        safe, categories = classify_text_primary("graphic violence")

    assert safe is False
    assert len(categories) > 0


# --- classify_text_backstop ---

def test_classify_text_backstop_returns_safe_tuple():
    with patch("providers.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="safe"))
        ]
        from providers import classify_text_backstop
        safe, categories = classify_text_backstop("A happy dog story.")

    assert safe is True
    assert categories == []


def test_classify_text_backstop_parses_unsafe_with_categories():
    with patch("providers.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="unsafe\nviolence, gore"))
        ]
        from providers import classify_text_backstop
        safe, categories = classify_text_backstop("graphic violence")

    assert safe is False
    assert "violence" in categories


# --- classify_image_primary ---

def test_classify_image_primary_returns_true_for_normal():
    with patch("providers.httpx") as mock_httpx, \
         patch("providers._falconsai") as mock_falconsai, \
         patch("PIL.Image.open", return_value=MagicMock()):
        mock_httpx.get.return_value.content = b"fake-image-bytes"
        mock_falconsai.return_value.return_value = [{"label": "normal", "score": 0.99}, {"label": "nsfw", "score": 0.01}]
        from providers import classify_image_primary
        result = classify_image_primary("https://example.com/image.png")
    assert result is True


def test_classify_image_primary_returns_false_for_nsfw():
    with patch("providers.httpx") as mock_httpx, \
         patch("providers._falconsai") as mock_falconsai, \
         patch("PIL.Image.open", return_value=MagicMock()):
        mock_httpx.get.return_value.content = b"fake-image-bytes"
        mock_falconsai.return_value.return_value = [{"label": "nsfw", "score": 0.95}, {"label": "normal", "score": 0.05}]
        from providers import classify_image_primary
        result = classify_image_primary("https://example.com/bad.png")
    assert result is False


# --- classify_image_backstop ---

def test_classify_image_backstop_returns_true_when_safe():
    with patch("providers.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.parse.return_value.choices = [
            MagicMock(message=MagicMock(parsed=MagicMock(is_safe=True), content='{"safety_reasoning":"ok","is_safe":true}'))
        ]
        from providers import classify_image_backstop
        result = classify_image_backstop("https://example.com/image.png")
    assert result is True


# --- input-gate-hardening spec: ph_recognizers registration + caching (§4b, §4c) ---
# Real Presidio — same rationale as test_ph_recognizers.py: registration/caching can't be
# meaningfully verified against a mock of the thing being registered into.

def test_presidio_registers_ph_recognizers():
    from providers import _presidio
    _presidio.cache_clear()
    analyzer, _ = _presidio()
    supported = {entity for r in analyzer.registry.recognizers for entity in r.supported_entities}
    assert {"PH_PERSON", "PH_MOBILE", "PH_ADDRESS", "PH_TIN", "PH_SSS", "PH_PHILHEALTH"} <= supported


def test_presidio_is_cached_across_calls():
    from providers import _presidio
    _presidio.cache_clear()
    first = _presidio()
    second = _presidio()
    assert first is second
