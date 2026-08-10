"""The only module that names a model vendor (CLAUDE.md §1, ADR-001, ADR-002).

Text + VLM judge go through OpenRouter (OpenAI-compatible). Images go through fal.ai.
Deterministic tests mock these functions; nothing here runs in CI (MASTER_SPEC §6).
"""
import json
import logging
from collections import Counter
from functools import lru_cache
from typing import TypeVar

import fal_client
import httpx
from openai import OpenAI
from pydantic import BaseModel

from app.config import settings
from app.db import get_supabase_client

_log = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

T = TypeVar("T", bound=BaseModel)


def structured_text(prompt: str, schema: type[T], model: str | None = None) -> T:
    """Strict `json_schema` structured output, validated into `schema`."""
    return _chat(
        OPENROUTER_BASE_URL,
        settings.openrouter_api_key,
        model or settings.text_model,
        prompt,
        schema,
    )


def judge(prompt: str, image_urls: list[str], schema: type[T], model: str | None = None) -> T:
    """Multimodal structured verdict over reference + scene images (ADR-004, ADR-018).

    Field order in `schema` is load-bearing: `differences_observed` must precede
    `same_character` so the judge reasons before it scores.
    """
    content = [{"type": "text", "text": prompt}]
    content += [{"type": "image_url", "image_url": {"url": url}} for url in image_urls]
    return _chat(
        settings.judge_base_url,
        settings.judge_api_key or settings.openrouter_api_key,
        model or settings.vlm_judge_model,
        content,
        schema,
    )


def _chat(base_url: str, api_key: str, model: str, content, schema: type[T]) -> T:
    """`provider.require_parameters` is load-bearing: without it OpenRouter may route to a
    provider that lacks structured output and silently downgrade to loose JSON (ADR-002).
    Self-hosted vLLM rejects the unknown field, so it is sent only to OpenRouter.
    """
    extra_body = {"provider": {"require_parameters": True}} if base_url == OPENROUTER_BASE_URL else {}
    completion = OpenAI(base_url=base_url, api_key=api_key, timeout=60.0, max_retries=0).chat.completions.parse(
        model=model,
        messages=[{"role": "user", "content": content}],
        response_format=schema,
        extra_body=extra_body,
    )
    message = completion.choices[0].message
    if message.parsed is None:
        raise ValueError(f"{model} returned no parsable structured output")
    _assert_field_order(message.content or "", schema, model)
    return message.parsed


def _assert_field_order(raw: str, schema: type[BaseModel], model: str) -> None:
    """Reason-then-score is load-bearing (ADR-004): a provider that emits fields out of schema
    order voids the mitigation, and Pydantic validates order-insensitively — only the emitted
    JSON key order shows it. `json.loads` preserves document order (D-D), so this reads real keys
    rather than substring-scanning, immune to a value that quotes a field name. Verdict fields must
    serialize under their Python names (no aliases) or the check silently finds nothing to compare.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return  # no raw JSON object echoed — same blind spot as before, can't verify order
    if not isinstance(parsed, dict):
        return
    emitted = [k for k in parsed if k in schema.model_fields]
    if emitted != [name for name in schema.model_fields if name in emitted]:
        raise ValueError(
            f"{model} emitted structured-output fields out of schema order (ADR-004 reason-then-score)"
        )


def text_to_image(prompt: str, seed: int | None = None) -> bytes:
    """Standalone image — used for the canonical character reference (ADR-001)."""
    return _run_fal(settings.fal_image_model, {"prompt": prompt}, seed)


# fal endpoints disagree on what the reference-image field is called, and fal **silently ignores
# unknown arguments** — a wrong name does not raise, it degrades every reference-conditioned call to
# plain text-to-image. Caught in the ADR-001 rung-1 pre-flight (2026-07-29): OmniGen2 names it
# `input_image_urls`, and sending Qwen's `image_urls` returned a confident, well-formed image of an
# entirely different character with the reference ignored. Escalating the fallback ladder is
# therefore NOT a pure env change, as ADR-001 assumed — it needs a row here. Verify against
# https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=<endpoint> before adding one.
REFERENCE_FIELD = {
    "fal-ai/qwen-image-edit-2511": "image_urls",
    "fal-ai/omnigen-v2": "input_image_urls",
}


def edit_image(prompt: str, image_urls: list[str], seed: int | None = None) -> bytes:
    """Reference-conditioned image. The mechanism character consistency rests on (ADR-007)."""
    endpoint = settings.fal_image_edit_model
    if endpoint not in REFERENCE_FIELD:
        raise ValueError(
            f"{endpoint}: reference-image field name unknown. Add it to REFERENCE_FIELD after "
            "checking fal's openapi. Failing loudly is deliberate — an unrecognised key is dropped "
            "silently, so the alternative is every scene quietly ignoring its character reference."
        )
    return _run_fal(endpoint, {"prompt": prompt, REFERENCE_FIELD[endpoint]: image_urls}, seed)


def upload_reference(image_bytes: bytes) -> str:
    """fal needs reference images as URLs, not bytes."""
    return _fal().upload(image_bytes, content_type="image/png")


def _fal() -> fal_client.SyncClient:
    return fal_client.SyncClient(key=settings.fal_key)


def _run_fal(endpoint: str, arguments: dict, seed: int | None) -> bytes:
    if seed is not None:
        arguments = {**arguments, "seed": seed}
    result = _fal().subscribe(endpoint, arguments={"output_format": "png", **arguments})
    response = httpx.get(result["images"][0]["url"], timeout=60.0)
    response.raise_for_status()
    return response.content


# ---------------------------------------------------------------------------
# Moderation providers — CPU-resident primaries + OpenRouter backstops
# All lazy-loaded to avoid importing GB-sized weights at import time.
# ---------------------------------------------------------------------------

_STORAGE_BUCKET = "storybook-images"


def get_signed_url(path: str) -> str:
    resp = get_supabase_client().storage.from_(_STORAGE_BUCKET).create_signed_url(path, expires_in=300)
    return resp["signedURL"]


def _parse_guard_response(response: str) -> tuple[bool, list[str]]:
    safe = response.startswith("safe")
    categories = [c.strip() for c in response.split("\n", 1)[1].split(",") if c.strip()] if not safe and "\n" in response else []
    return safe, categories

@lru_cache(maxsize=1)
def _presidio():
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import SpacyNlpEngine
    from presidio_anonymizer import AnonymizerEngine

    from ph_recognizers import ph_recognizers

    nlp_engine = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": "en_core_web_sm"}])
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
    for recognizer in ph_recognizers():
        analyzer.registry.add_recognizer(recognizer)
    return analyzer, AnonymizerEngine()


_PSEUDONYM_POOL = ["Ana", "Ben", "Cielo", "Dado", "Elena", "Fabio"]


def _pseudonymizer():
    """Fresh mapping per call — caching this would leak names between stories (spec §4c)."""
    mapping: dict[str, str] = {}

    def assign(value: str) -> str:
        key = value.casefold()
        if key not in mapping:
            mapping[key] = _PSEUDONYM_POOL[len(mapping) % len(_PSEUDONYM_POOL)]
        return mapping[key]

    return assign


def redact_pii(text: str) -> str:
    """Presidio PII redaction (CC-2). Persons pseudonymized so the story survives with a
    protagonist an illustrator can draw; structured identifiers hard-redact (spec §4c).
    en_core_web_sm must be downloaded before first call."""
    from presidio_anonymizer.entities import OperatorConfig

    analyzer, anonymizer = _presidio()
    results = analyzer.analyze(text=text, language="en")
    # CC-5: log entity-type counts only — never the detected values (ADR-025 D5).
    _log.info("pii_redaction entity_counts=%s", dict(Counter(r.entity_type for r in results)))

    # Pre-populate the mapping in reading order: the anonymizer calls the lambda right-to-left
    # (to avoid offset shifts), so without this the last name in the text would get pool[0].
    assign = _pseudonymizer()
    _PERSON_ENTITIES = {"PERSON", "PH_PERSON"}
    for r in sorted(results, key=lambda r: r.start):
        if r.entity_type in _PERSON_ENTITIES:
            assign(text[r.start : r.end])

    person = OperatorConfig("custom", {"lambda": assign})
    return anonymizer.anonymize(
        text=text, analyzer_results=results,
        operators={"PERSON": person, "PH_PERSON": person},
    ).text


# ADR-032: Local Qwen3Guard removed to prevent OOM.


# Guard prompt template — verify against https://huggingface.co/Qwen/Qwen3-Guard-Gen-0.6B
# before deploying. The model outputs "safe" or "unsafe\n<categories>" in its response.
_GUARD_SYSTEM = (
    "You are a content safety classifier for a children's education platform (ages 5–12). "
    "Classify the user message as 'safe' or 'unsafe'. "
    "If unsafe, list the violated categories on the next line."
)


def classify_text_primary(text: str) -> tuple[bool, list[str]]:
    """Primary text guard via OpenRouter (ADR-032). Returns (is_safe, categories)."""
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key, timeout=30.0, max_retries=0)
    completion = client.chat.completions.create(
        model=settings.moderation_primary_model,
        messages=[{"role": "system", "content": _GUARD_SYSTEM}, {"role": "user", "content": text}],
        max_tokens=100,
    )
    response = (completion.choices[0].message.content or "").strip().lower()
    return _parse_guard_response(response)


def classify_text_backstop(text: str) -> tuple[bool, list[str]]:
    """gpt-oss-safeguard-20b via OpenRouter. Returns (is_safe, categories)."""
    prompt = (
        "You are a content safety classifier for a children's education platform (ages 5–12). "
        "Classify the following text as 'safe' or 'unsafe'.\n"
        "If unsafe, list violated categories on the next line.\n\n"
        f"Text: {text}"
    )
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key, timeout=30.0, max_retries=0)
    completion = client.chat.completions.create(
        model=settings.moderation_backstop_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
    )
    response = (completion.choices[0].message.content or "").strip().lower()
    return _parse_guard_response(response)


# ADR-032: Local Falconsai ViT removed to prevent OOM.

def classify_image_primary(image_url: str) -> bool:
    """Primary NSFW image guard via API (ADR-032). Returns True if safe."""
    prompt = (
        "You are a content safety classifier for a children's education platform. "
        "Analyze the provided image and determine if it contains any NSFW (Not Safe For Work) content, "
        "such as nudity, sexual content, or explicit material. "
        "Explain your reasoning, then classify it."
    )
    verdict = judge(prompt, [image_url], _ImageSafetyVerdict, model=settings.moderation_primary_image_model)
    return verdict.is_safe


class _ImageSafetyVerdict(BaseModel):
    # Reason-before-score per ADR-004.
    safety_reasoning: str
    is_safe: bool


def classify_image_backstop(image_url: str) -> bool:
    """gemma-3-27b-it via OpenRouter — violence, gore, dangerous content check."""
    prompt = (
        "You are reviewing an image for a children's educational storybook platform (ages 5–12). "
        "Assess whether the image is safe for children. "
        "Flag: violence, gore, sexual content, frightening imagery, dangerous activities."
    )
    verdict = judge(prompt, [image_url], _ImageSafetyVerdict, model=settings.moderation_backstop_image_model)
    return verdict.is_safe
