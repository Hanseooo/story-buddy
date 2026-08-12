import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from presidio_analyzer import RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from pydantic import BaseModel, ValidationError

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
    # Subset, not equality: this call passes no model, so it resolves through settings.text_model
    # and picks up whatever TEXT_PROVIDERS holds for it — which is a property of the developer's
    # environment, exactly like the model literal the comment below warns about. The pin has its
    # own tests; the flag is what this one is for.
    assert kwargs["extra_body"]["provider"]["require_parameters"] is True
    assert kwargs["response_format"] is _Caption
    # The wiring is the assertion — `structured_text` defaults to settings.text_model. Pinning a
    # literal here made the test fail for anyone with TEXT_MODEL set in .env, which is a property
    # of the developer's environment, not of the code under test. test_config.py owns defaults.
    assert kwargs["model"] == providers.settings.text_model


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


def test_vision_judge_pins_providers_because_openrouter_cannot_filter_by_modality():
    """Prod job f4d0fd74 (2026-08-11) died at `output_mod` on scene s5 with a 400:
    `Image content is not supported by this model.` from Venice. DeepInfra and Parasail had both
    429'd on the shared pool, so OpenRouter fell through to Venice, whose fp8 deployment of
    mistral-small-3.2 is text-only. A 400 is not retryable, so `MAX_RETRIES` cannot cover it.

    `require_parameters` does NOT cover this: it selects providers that support the top-level
    request *parameters* (`response_format`), not `messages` content types. Verified against
    https://openrouter.ai/docs/features/provider-routing on 2026-08-11 — the `provider` object has
    no input-modality filter at all, and `/models/.../endpoints` reports no per-endpoint
    modalities either. An explicit allowlist is the only mechanism available.
    """
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(_Caption(caption="hi"))
        providers.judge(
            "is it safe", ["https://scene.png"], _Caption,
            model="mistralai/mistral-small-3.2-24b-instruct",
        )

    assert parse.call_args.kwargs["extra_body"] == {
        "provider": {"require_parameters": True, "only": ["deepinfra", "parasail"]}
    }


def test_text_calls_route_around_the_provider_that_ignored_the_schema():
    """Prod row 558afb6d (2026-08-12), the fourth instance of ADR-002's class and the first where
    the model choice is not the culprit.

    `analyze` asked for `StoryAnalysis` and got a 200 back in 363ms carrying
    `{'species': 'location', ...}` in four fields declared `str | None` — the character
    sub-schema's shape copied into its location/object siblings. `species` exists nowhere in that
    schema except `ExtractedDescription`, and a grammar-constrained decoder cannot emit those
    tokens at all, so the answer was not constrained. OpenRouter's activity log names the route:
    `mistralai/mistral-small-3.2-24b-instruct` served by **Parasail**
    (`gen-1786523891-ZW5XHaXPUfbTXdd0cIF3`).

    `TEXT_MODEL` was the intended default and `require_parameters` was sent, as it is on every
    OpenRouter call. Neither is a defence: acceptance is a routing-table flag, fidelity is a
    property of how the provider decodes.
    """
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(_Caption(caption="hi"))
        providers.structured_text("prompt", _Caption, model="mistralai/mistral-small-3.2-24b-instruct")

    only = parse.call_args.kwargs["extra_body"]["provider"]["only"]
    assert "parasail" not in only


def test_only_models_that_need_pinning_are_pinned():
    """The allowlist is per-model on purpose. gemma-3-27b-it serves the image backstop AND the
    consistency judge across five providers, none of them Venice — pinning it would buy nothing
    and make 429s likelier by shrinking its pool.

    ~~And mistral-small-3.2 is also `text_model`, where Venice is a perfectly good route: the pin
    belongs to the call that sends an image, not to the model name.~~ **Amended 2026-08-12.** The
    principle held; the conclusion that only the image call needed a pin did not. Both call sites
    now pin the same model, and to *different* lists — Parasail can serve an image and cannot honour
    a strict schema, Venice is the exact reverse. That asymmetry is the per-call-site rule with
    teeth, so it is asserted rather than described.
    """
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(_Caption(caption="hi"))
        providers.judge("compare", ["https://ref.png"], _Caption, model="google/gemma-3-27b-it")
        gemma_body = parse.call_args.kwargs["extra_body"]

        providers.judge("compare", ["https://ref.png"], _Caption,
                        model="mistralai/mistral-small-3.2-24b-instruct")
        vision_only = parse.call_args.kwargs["extra_body"]["provider"]["only"]

        providers.structured_text("prompt", _Caption, model="mistralai/mistral-small-3.2-24b-instruct")
        text_only = parse.call_args.kwargs["extra_body"]["provider"]["only"]

    assert gemma_body == {"provider": {"require_parameters": True}}
    assert vision_only != text_only
    assert "parasail" in vision_only and "parasail" not in text_only


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


# --- transient-failure tolerance ---

def test_every_llm_client_retries_transient_failures():
    """Prod job beb4ebff (2026-08-11): `segment` died ~1s after `analyze` finished, on a 429 whose
    own body said `retry_after_seconds: 29.8` and `limit_source: upstream_provider_shared_pool`.
    Nothing waited. There is no `RetryPolicy` on any node in `pipeline/graph.py` either, so a
    single transient upstream blip on any of ~30 calls kills a book after its upstream work is
    already paid for.

    Retries were disabled in 23b3dca to stop the SDK sleeping on a large `Retry-After`, but the SDK
    cannot do that: `_base_client.py:781` honours the header only when `0 < retry_after <= 60` and
    otherwise falls through to backoff capped at `MAX_RETRY_DELAY = 8.0`. Worst case is two 60s
    waits, inside the 900s job timeout from ca2479c.

    Asserted for every construction site, not just `_chat`: the moderation clients are separate
    `OpenAI(...)` calls and drifted independently once already.
    """
    for call in (
        lambda: providers.structured_text("prompt", _Caption),
        lambda: providers.classify_text_primary("A dog runs."),
        lambda: providers.classify_text_backstop("A dog runs."),
    ):
        with patch("providers.OpenAI") as mock_openai:
            completions = mock_openai.return_value.chat.completions
            completions.parse.return_value = _fake_completion(_Caption(caption="hi"))
            completions.create.return_value.choices = [MagicMock(message=MagicMock(content="safe"))]
            call()

        assert mock_openai.call_args.kwargs["max_retries"] > 0


# --- schema-violation tolerance ---
#
# `MAX_RETRIES` above cannot cover this class at all: it is the SDK's transport-level retry, keyed
# on HTTP status. A provider that ignores the grammar answers **200**, and the failure happens
# client-side while parsing a response the SDK considers a success.


def _schema_violation() -> ValidationError:
    """What `completions.parse` raises when the body does not match the schema.

    Shaped like prod row 558afb6d: an object where a `str` was declared.
    """
    try:
        _Caption.model_validate({"caption": {"species": "location", "colours": []}})
    except ValidationError as exc:
        return exc
    raise AssertionError("the schema accepted an object where it declares a str")


def test_a_schema_violating_answer_is_re_asked_once():
    """The pin removes the one provider known to do this; this removes the whole class.

    Both are needed. The pin is per `(model, provider)` and every list in this module is an
    incomplete measurement — nobody has established that the providers left on it decode any more
    faithfully than the one taken off. And the pin cannot protect the judge, which keeps Parasail
    allowlisted because it can serve an image (`VISION_PROVIDERS`).
    """
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.side_effect = [_schema_violation(), _fake_completion(_Caption(caption="hi"))]
        result = providers.structured_text("prompt", _Caption)

    assert result.caption == "hi"
    assert parse.call_count == 2


def test_an_answer_with_its_fields_out_of_order_is_re_asked_too():
    """ADR-002 Instance 2 is the same cause wearing a different symptom: the provider emitted
    tokens the declared grammar should have made unproducible. It hard-failed a book at
    `char_ref_mod` — the child-facing safety gate.

    `_assert_field_order` stays a raise, not a warning (ADR-002 says so explicitly). Re-asking
    before that raise reaches the pipeline does not soften it; the second violation still kills
    the job, as the test below asserts.
    """
    ordered = '{"differences_observed": "none", "same_character": true}'
    backwards = '{"same_character": true, "differences_observed": "none"}'
    verdict = _Verdict(differences_observed="none", same_character=True)
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.side_effect = [
            _fake_completion(verdict, content=backwards),
            _fake_completion(verdict, content=ordered),
        ]
        result = providers.judge("compare", ["https://ref.png"], _Verdict)

    assert result.same_character is True
    assert parse.call_count == 2


def test_two_violations_in_a_row_still_fail_the_job():
    """One re-ask, not a loop. A provider that cannot honour the schema will not learn to on the
    fourth attempt, and every attempt is billed."""
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.side_effect = [_schema_violation(), _schema_violation()]
        with pytest.raises(ValidationError):
            providers.structured_text("prompt", _Caption)

    assert parse.call_count == 2


def test_an_answer_that_validates_costs_exactly_one_call():
    """The spend guard. Every call here is billed, and `analyze`/`segment`/`char_bible` alone put
    ~30 of them behind one book."""
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(_Caption(caption="hi"))
        providers.structured_text("prompt", _Caption)

    assert parse.call_count == 1


def test_a_stalled_call_is_not_re_asked():
    """`_bounded` already spent CALL_TIMEOUT_SECONDS finding out. Re-asking would double the worst
    case against the 900s job deadline to buy a second wait on a provider that is not answering —
    and a stall is not evidence of a schema the provider cannot honour, which is what this retry
    is for.
    """
    release = threading.Event()
    with patch("providers.OpenAI") as mock_openai, \
         patch.object(providers, "CALL_TIMEOUT_SECONDS", 0.2):
        parse = MagicMock(side_effect=_blocking_parse(release))
        mock_openai.return_value.chat.completions.parse = parse
        try:
            with pytest.raises(TimeoutError):
                providers.structured_text("prompt", _Caption)
        finally:
            release.set()

    assert parse.call_count == 1


# --- wall-clock bound ---

def _blocking_parse(release: threading.Event):
    """A `.parse` that hangs the way prod job d83721d9's did — no bytes, no error, no end."""
    def parse(**kwargs):
        release.wait()
        return _fake_completion(_Caption(caption="hi"))
    return parse


def test_a_hung_call_is_abandoned_at_the_wall_clock():
    """Prod job d83721d9 (2026-08-11): one `/chat/completions` blocked 14m05s under `timeout=60.0`.

    Timeline from the OpenRouter generation IDs, which are unix seconds:
      18:20:50  job dequeued, RQ deadline = +900s
      18:21:46  consistency_check s1 opens (Langfuse latency: 14m19s; s0 was 9.42s)
      18:35:50  RQ's SIGALRM — exactly the 900s mark
      18:35:52  "Retrying request to /chat/completions in 0.449936 seconds"
      18:35:53  gen-1786473353, the FIRST OpenRouter generation of the whole gap

    The call did not time out, it was interrupted: 845s elapsed and nothing fired. httpx expands
    scalar `timeout=60.0` to connect/read/write/pool=60 and every one of those is PER-OPERATION —
    a read timeout bounds the gap between chunks, not the request. httpx has no total-duration
    option, so bounding it needs a clock outside the call.
    """
    release = threading.Event()
    with patch("providers.OpenAI") as mock_openai, \
         patch.object(providers, "CALL_TIMEOUT_SECONDS", 0.2):
        mock_openai.return_value.chat.completions.parse = _blocking_parse(release)
        started = time.monotonic()
        try:
            with pytest.raises(TimeoutError):
                providers.structured_text("prompt", _Caption)
            elapsed = time.monotonic() - started
        finally:
            release.set()

    # The bound is the point. A `with ThreadPoolExecutor(...)` block would pass the `raises` above
    # and then join the hung thread on `__exit__`, reproducing the exact hang this test forbids.
    assert elapsed < 5, f"call was not abandoned: returned after {elapsed:.1f}s"


def test_the_timeout_is_catchable_by_the_pipelines_own_handlers():
    """Load-bearing: `consistency_check.judge_attempt` catches `Exception` and returns [], which
    means *unchecked* — the page still finalizes and the book still ships (ADR-025). A bound that
    raised `BaseException` would sail past that handler and kill the book instead of one verdict."""
    assert issubclass(TimeoutError, Exception)


def test_the_timeout_says_which_model_hung():
    """`run_job`'s `except` writes `str(exc)` into the row's `error`, and that string is all anyone
    gets after the fact. A bare `TimeoutError()` from `Future.result` carries no message at all."""
    release = threading.Event()
    with patch("providers.OpenAI") as mock_openai, \
         patch.object(providers, "CALL_TIMEOUT_SECONDS", 0.2):
        mock_openai.return_value.chat.completions.parse = _blocking_parse(release)
        try:
            with pytest.raises(TimeoutError, match="gemma-hangs-a-lot"):
                providers.structured_text("prompt", _Caption, model="gemma-hangs-a-lot")
        finally:
            release.set()


def test_a_call_that_answers_is_untouched_by_the_bound():
    """The wrapper must be transparent — same parsed object, same kwargs reaching the SDK."""
    with patch("providers.OpenAI") as mock_openai:
        parse = mock_openai.return_value.chat.completions.parse
        parse.return_value = _fake_completion(_Caption(caption="hi"))
        result = providers.structured_text("prompt", _Caption)

    assert result.caption == "hi"
    assert parse.call_args.kwargs["response_format"] is _Caption


# --- redact_pii ---

def test_redact_pii_returns_string():
    """Smoke test: redact_pii returns a string (real Presidio is an integration concern)."""
    with patch("providers._presidio", return_value=(MagicMock(analyze=lambda **kw: []), MagicMock(anonymize=lambda **kw: MagicMock(text="clean text")))):
        from providers import redact_pii
        result = redact_pii("My name is Juan dela Cruz")
    assert isinstance(result, str)


# --- classify_text_primary ---

def test_classify_text_primary_returns_safe_tuple():
    with patch("providers.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="safe"))
        ]
        from providers import classify_text_primary
        safe, categories = classify_text_primary("A dog runs in a field.")

    assert isinstance(safe, bool)
    assert isinstance(categories, list)


def test_classify_text_primary_unsafe_response_is_not_safe():
    with patch("providers.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="unsafe\nS1: Violence"))
        ]
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
    with patch("providers.judge") as mock_judge:
        mock_judge.return_value = MagicMock(is_safe=True)
        from providers import classify_image_primary
        result = classify_image_primary("https://example.com/image.png")
    assert result is True


def test_classify_image_primary_returns_false_for_nsfw():
    with patch("providers.judge") as mock_judge:
        mock_judge.return_value = MagicMock(is_safe=False)
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


# --- input-gate-hardening spec: pseudonymized person redaction (§4c) ---


def _fake_presidio(results):
    """Fake analyzer (canned results, no spaCy load) + REAL AnonymizerEngine, so these tests
    exercise the actual operator wiring without needing en_core_web_sm."""
    analyzer = MagicMock()
    analyzer.analyze = lambda **kwargs: results
    return analyzer, AnonymizerEngine()


def test_redact_pii_pseudonymizes_repeated_name_consistently():
    text = "Si Maria ay pumunta sa bukid. Tinawag ni Maria si Juan."
    first_maria = text.index("Maria")
    second_maria = text.index("Maria", first_maria + 1)
    juan = text.index("Juan")
    results = [
        RecognizerResult(entity_type="PH_PERSON", start=first_maria, end=first_maria + 5, score=0.85),
        RecognizerResult(entity_type="PH_PERSON", start=second_maria, end=second_maria + 5, score=0.85),
        RecognizerResult(entity_type="PH_PERSON", start=juan, end=juan + 4, score=0.85),
    ]
    with patch("providers._presidio", return_value=_fake_presidio(results)):
        from providers import redact_pii
        result = redact_pii(text)

    assert result.count("Ana") == 2
    assert "Ben" in result
    assert "Maria" not in result
    assert "Juan" not in result


def test_redact_pii_different_names_get_different_stand_ins():
    text = "Si Pedro at si Rosario ay magkaibigan."
    pedro = text.index("Pedro")
    rosario = text.index("Rosario")
    results = [
        RecognizerResult(entity_type="PH_PERSON", start=pedro, end=pedro + 5, score=0.85),
        RecognizerResult(entity_type="PH_PERSON", start=rosario, end=rosario + 7, score=0.85),
    ]
    with patch("providers._presidio", return_value=_fake_presidio(results)):
        from providers import redact_pii
        result = redact_pii(text)

    assert "Pedro" not in result
    assert "Rosario" not in result
    assert "Ana" in result
    assert "Ben" in result


def test_redact_pii_two_calls_do_not_share_a_mapping():
    text = "Si Marcos ang pangalan niya."
    marcos = text.index("Marcos")
    results = [RecognizerResult(entity_type="PH_PERSON", start=marcos, end=marcos + 6, score=0.85)]
    with patch("providers._presidio", return_value=_fake_presidio(results)):
        from providers import redact_pii
        first_result = redact_pii(text)
        second_result = redact_pii(text)

    # Same input, fresh mapping each call — both independently land on the pool's first entry.
    assert first_result == second_result
    assert "Ana" in first_result


def test_redact_pii_hard_redacts_structured_identifiers_not_pseudonyms():
    text = "Ang TIN ko ay 123-456-789."
    tin = text.index("123-456-789")
    results = [RecognizerResult(entity_type="PH_TIN", start=tin, end=tin + 11, score=0.6)]
    with patch("providers._presidio", return_value=_fake_presidio(results)):
        from providers import redact_pii
        result = redact_pii(text)

    assert "123-456-789" not in result
    assert "<PH_TIN>" in result


def test_redact_pii_returns_text_unchanged_when_no_entities():
    with patch("providers._presidio", return_value=_fake_presidio([])):
        from providers import redact_pii
        result = redact_pii("Walang laman dito.")
    assert result == "Walang laman dito."


def test_presidio_is_cached_across_calls():
    """@lru_cache(maxsize=1) — two calls must return the same tuple without constructing twice.
    Imports are lazy inside _presidio, so we patch at their source modules."""
    from providers import _presidio

    _presidio.cache_clear()
    try:
        with patch("presidio_analyzer.AnalyzerEngine"), \
             patch("presidio_analyzer.nlp_engine.SpacyNlpEngine"), \
             patch("presidio_anonymizer.AnonymizerEngine") as mock_anon, \
             patch("ph_recognizers.ph_recognizers", return_value=[]):
            first = _presidio()
            second = _presidio()
            mock_anon.assert_called_once()  # lru_cache: constructor fired exactly once
        assert first is second
    finally:
        _presidio.cache_clear()
