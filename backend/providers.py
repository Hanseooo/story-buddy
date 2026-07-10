"""The only module that names a model vendor (CLAUDE.md §1, ADR-001, ADR-002).

Text + VLM judge go through OpenRouter (OpenAI-compatible). Images go through fal.ai.
Deterministic tests mock these functions; nothing here runs in CI (MASTER_SPEC §6).
"""
from typing import TypeVar

import fal_client
import httpx
from openai import OpenAI
from pydantic import BaseModel

from app.config import settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

T = TypeVar("T", bound=BaseModel)


def structured_text(prompt: str, schema: type[T], model: str | None = None) -> T:
    """Strict `json_schema` structured output, validated into `schema`.

    `provider.require_parameters` is load-bearing: without it OpenRouter may route to a
    provider that lacks structured output and silently downgrade to loose JSON (ADR-002).
    """
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key)
    completion = client.chat.completions.parse(
        model=model or settings.text_model,
        messages=[{"role": "user", "content": prompt}],
        response_format=schema,
        extra_body={"provider": {"require_parameters": True}},
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError(f"{model or settings.text_model} returned no parsable structured output")
    return parsed


def text_to_image(prompt: str, seed: int | None = None) -> bytes:
    """Standalone image — used for the canonical character reference (ADR-001)."""
    return _run_fal(settings.fal_image_model, {"prompt": prompt}, seed)


def edit_image(prompt: str, image_urls: list[str], seed: int | None = None) -> bytes:
    """Reference-conditioned image. The mechanism character consistency rests on (ADR-007)."""
    return _run_fal(settings.fal_image_edit_model, {"prompt": prompt, "image_urls": image_urls}, seed)


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
