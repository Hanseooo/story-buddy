from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from contracts.job_state import SceneCaption
import providers


def _fake_completion(parsed, content: str = ""):
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(parsed=parsed, content=content))]
    return completion


def test_structured_text_requires_provider_parameters():
    """Without require_parameters, OpenRouter silently downgrades strict json_schema (ADR-002)."""
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(SceneCaption(caption="hi"))
        providers.structured_text("prompt", SceneCaption)

    kwargs = parse.call_args.kwargs
    assert kwargs["extra_body"] == {"provider": {"require_parameters": True}}
    assert kwargs["response_format"] is SceneCaption
    assert kwargs["model"] == "qwen/qwen3-32b"


def test_structured_text_raises_when_nothing_parsed():
    with patch("providers.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.parse.return_value = _fake_completion(None)
        with pytest.raises(ValueError):
            providers.structured_text("prompt", SceneCaption)


def test_judge_sends_images_as_multimodal_content():
    """The judge is only ever called with reference + scene. A text-only call is a broken judge."""
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(SceneCaption(caption="hi"))
        providers.judge("compare", ["https://ref.png", "https://scene.png"], SceneCaption)

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


def test_judge_omits_openrouter_flag_when_self_hosted():
    """vLLM rejects OpenRouter's `provider` field; the swap to Modal is config-only (ADR-019)."""
    with patch("providers.OpenAI") as mock_openai, \
         patch.object(providers.settings, "judge_base_url", "https://x.modal.run/v1"):
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(SceneCaption(caption="hi"))
        providers.judge("compare", ["https://ref.png"], SceneCaption)

    assert parse.call_args.kwargs["extra_body"] == {}


def test_edit_image_passes_references_and_seed_and_returns_bytes():
    fal = MagicMock()
    fal.subscribe.return_value = {"images": [{"url": "https://fal.example/x.png"}], "seed": 7}
    response = MagicMock(content=b"png-bytes")

    with patch("providers._fal", return_value=fal), \
         patch("providers.httpx.get", return_value=response) as mock_get:
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


def test_text_to_image_omits_seed_when_not_given():
    fal = MagicMock()
    fal.subscribe.return_value = {"images": [{"url": "https://fal.example/x.png"}], "seed": 1}

    with patch("providers._fal", return_value=fal), \
         patch("providers.httpx.get", return_value=MagicMock(content=b"png")):
        providers.text_to_image("a fox")

    assert "seed" not in fal.subscribe.call_args.kwargs["arguments"]
