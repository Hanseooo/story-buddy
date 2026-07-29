"""The only module that names a model vendor (CLAUDE.md §1, ADR-001, ADR-002).

Text + VLM judge go through OpenRouter (OpenAI-compatible). Images go through fal.ai.
Deterministic tests mock these functions; nothing here runs in CI (MASTER_SPEC §6).
"""
import json
from typing import TypeVar

import fal_client
import httpx
from openai import OpenAI
from pydantic import BaseModel

from app.config import settings

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
    completion = OpenAI(base_url=base_url, api_key=api_key).chat.completions.parse(
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
