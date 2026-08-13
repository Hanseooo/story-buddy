"""The only module that names a model vendor (CLAUDE.md §1, ADR-001, ADR-002).

Text + VLM judge go through OpenRouter (OpenAI-compatible). Images go through fal.ai.
Deterministic tests mock these functions; nothing here runs in CI (MASTER_SPEC §6).
"""
import hashlib
import json
import logging
import random
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
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

# 23b3dca set this to 0 to stop the SDK sleeping on a large `Retry-After`. The SDK cannot do that:
# it honours the header only when `0 < retry_after <= 60` (`openai/_base_client.py:781`) and
# otherwise falls through to backoff capped at `MAX_RETRY_DELAY = 8.0`. What zero actually bought
# was a dead book on every transient upstream 429 — routine on OpenRouter's free shared pool, and
# what killed prod job beb4ebff on 2026-08-11: `segment` raised ~1s after `analyze` succeeded, on a
# 429 whose own body asked for a 30s wait. No node carries a LangGraph `RetryPolicy`, so this
# constant is the pipeline's only tolerance for a transient upstream blip.
MAX_RETRIES = 2

# OpenRouter's `provider` object has NO input-modality filter — verified 2026-08-11 against
# https://openrouter.ai/docs/features/provider-routing. `require_parameters` selects providers that
# support the top-level request PARAMETERS (`response_format`), not `messages` content types, so a
# text-only deployment of a vision-capable model passes that filter and then 400s on the image.
# `/models/{id}/endpoints` reports no per-endpoint modalities either, so an explicit allowlist is
# the only mechanism there is. Prod job f4d0fd74 (2026-08-11) died on scene s5 this way: DeepInfra
# and Parasail both 429'd on the shared pool, OpenRouter fell through to Venice, and Venice's fp8
# deployment answered "Image content is not supported by this model." A 400 is not retryable, so
# MAX_RETRIES cannot cover it.
#
# Allowlist rather than an `ignore: ["venice"]` blocklist: this is the safety path, so a provider
# added later should be excluded until someone checks it serves images. Keyed per model and read
# only by `judge` — mistral-small-3.2 is also `text_model`, where Venice is a fine route, and
# gemma-3-27b-it serves five providers (none of them Venice), so pinning it would shrink its pool
# for nothing. Re-check with: curl .../api/v1/models/{id}/endpoints
VISION_PROVIDERS: dict[str, list[str]] = {
    "mistralai/mistral-small-3.2-24b-instruct": ["deepinfra", "parasail"],
}

# The same mechanism for the OTHER axis `require_parameters` does not cover: whether the provider
# HONOURS the schema it agreed to accept. Prod row 558afb6d (2026-08-12) is the case — Parasail
# answered `analyze` with a 200 in 363ms carrying `{'species': 'location', ...}` in four fields
# declared `str | None`, the character sub-schema's shape copied into its location/object siblings.
# `species` appears nowhere in `StoryAnalysis` except `ExtractedDescription`, and constrained
# decoding cannot emit those tokens at all, so that answer was never grammar-constrained.
#
# Deliberately NOT the same list as VISION_PROVIDERS above, for the same model. Parasail serves an
# image and cannot honour a strict schema; Venice is the exact reverse (ADR-002 Instance 3). Keyed
# per call site, which is the rule ADR-002 already states — this is the first case where the two
# lists actually diverge, so the rule is now load-bearing rather than decorative.
#
# ponytail: two providers, not one. Dropping to `["deepinfra"]` would be the cautious read, but the
# shared free pool 429s often enough to have killed prod job beb4ebff, and MAX_RETRIES is the only
# tolerance there is. Venice is unmeasured for fidelity rather than known-good — the re-ask in
# `_chat` is what covers that, and it is why this list does not have to be right first time.
TEXT_PROVIDERS: dict[str, list[str]] = {
    "mistralai/mistral-small-3.2-24b-instruct": ["deepinfra", "venice"],
}

# The only bound on a call's TOTAL duration. Prod job d83721d9 (2026-08-11) proved `timeout=60.0`
# is not one: a judge request blocked 14m05s and never raised. httpx expands a scalar timeout to
# connect/read/write/pool, and each is PER-OPERATION — the read value bounds the gap between chunks,
# not the request — so a provider that trickles, or a write that stalls mid-upload on ~4 MB of
# base64, can outlive it indefinitely. httpx exposes no total-duration option, so the clock has to
# live outside the call. That stall ended only when RQ's 900s SIGALRM landed at 18:35:50 and the
# SDK's `except Exception` swallowed it as retryable (18:35:52), spending two more paid fal images
# past the deadline before the horse was killed.
#
# 120s against observed judge latencies of 1.2-1.8s (OpenRouter, same run) leaves ~60x of headroom,
# and still covers MAX_RETRIES' worst case: the SDK caps backoff at MAX_RETRY_DELAY = 8.0.
# ponytail: one number for text and vision alike. Split it per call site only if a real judge
# latency ever lands near it — right now nothing is within two orders of magnitude.
CALL_TIMEOUT_SECONDS = 120.0

T = TypeVar("T", bound=BaseModel)


def _bounded(model: str, call):
    """Run `call` on a worker thread and give up on it after `CALL_TIMEOUT_SECONDS`.

    Wraps the whole SDK call, so the bound covers `MAX_RETRIES`' attempts together rather than
    resetting per attempt.

    `TimeoutError` is deliberately an ordinary `Exception`: `consistency_check.judge_attempt`
    catches that and returns `[]`, which means *unchecked*, so a stalled judge costs one verdict
    and the book still ships (ADR-025). A `BaseException` would sail past that handler and kill the
    whole book to save one page.

    ponytail: the abandoned thread is never reclaimed — it holds a socket until the process exits,
    and the pool is not reused as `shutdown(wait=False)` leaves it. That is the price of bounding
    something httpx will not. Move to an async client if stalls ever become frequent enough for the
    leak to matter; at one stall per book it does not.
    """
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        # NOT `with ThreadPoolExecutor(...)`: its `__exit__` calls `shutdown(wait=True)`, which
        # joins the very thread this is abandoning and re-hangs the worker on the way out.
        return pool.submit(call).result(timeout=CALL_TIMEOUT_SECONDS)
    except TimeoutError as exc:
        # `Future.result` raises a bare, messageless TimeoutError, and `run_job`'s handler writes
        # `str(exc)` into the row's `error` — the only account of the failure anyone gets later.
        raise TimeoutError(
            f"{model} did not answer within {CALL_TIMEOUT_SECONDS:.0f}s (call abandoned)"
        ) from exc
    finally:
        pool.shutdown(wait=False)


def structured_text(prompt: str, schema: type[T], model: str | None = None) -> T:
    """Strict `json_schema` structured output, validated into `schema`."""
    resolved = model or settings.text_model
    return _chat(
        OPENROUTER_BASE_URL,
        settings.openrouter_api_key,
        resolved,
        prompt,
        schema,
        # Only this function sends a strict schema without an image, so only this function reads
        # the fidelity allowlist — `judge` has its own, and they disagree on purpose.
        providers=TEXT_PROVIDERS.get(resolved),
    )


def judge(prompt: str, image_urls: list[str], schema: type[T], model: str | None = None) -> T:
    """Multimodal structured verdict over reference + scene images (ADR-004, ADR-018).

    Field order in `schema` is load-bearing: `differences_observed` must precede
    `same_character` so the judge reasons before it scores.
    """
    content = [{"type": "text", "text": prompt}]
    content += [{"type": "image_url", "image_url": {"url": url}} for url in image_urls]
    resolved = model or settings.vlm_judge_model
    return _chat(
        settings.judge_base_url,
        settings.judge_api_key or settings.openrouter_api_key,
        resolved,
        content,
        schema,
        # Only this function sends images, so only this function pins providers.
        providers=VISION_PROVIDERS.get(resolved),
    )


def _chat(
    base_url: str, api_key: str, model: str, content, schema: type[T],
    providers: list[str] | None = None,
) -> T:
    """`provider.require_parameters` is load-bearing: without it OpenRouter may route to a
    provider that lacks structured output and silently downgrade to loose JSON (ADR-002).
    Self-hosted vLLM rejects the unknown field, so it is sent only to OpenRouter — which is also
    why `providers` is dropped on that path: ADR-019's vLLM has no provider routing to constrain.
    """
    prefs = {"require_parameters": True}
    if providers:
        prefs["only"] = providers
    extra_body = {"provider": prefs} if base_url == OPENROUTER_BASE_URL else {}
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=60.0, max_retries=MAX_RETRIES)
    try:
        return _one_answer(client, model, content, schema, extra_body)
    except ValueError as exc:
        # Every way a provider can break its own grammar arrives here as a `ValueError`: pydantic's
        # `ValidationError` subclasses it, and the two raises in `_one_answer` are ValueErrors
        # already. `MAX_RETRIES` cannot cover any of them — it is keyed on HTTP status, and a
        # provider that ignores the schema answers 200.
        #
        # One re-ask, not a loop: a provider that cannot honour the schema will not learn to on the
        # fourth attempt, and every attempt is billed. A stall is deliberately NOT retried —
        # `_bounded` raises `TimeoutError`, which is an `OSError` and does not land here, so the
        # worst case against the 900s job deadline stays one `CALL_TIMEOUT_SECONDS`, not two.
        _log.warning("%s broke its own response schema; re-asking once. %s", model, exc)
        return _one_answer(client, model, content, schema, extra_body)


def _one_answer(client: OpenAI, model: str, content, schema: type[T], extra_body: dict) -> T:
    """One request, validated. Raises `ValueError` (or a `ValidationError`, which is one) whenever
    the provider returns something the declared grammar should have made unproducible."""
    completion = _bounded(
        model,
        lambda: client.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": content}],
            response_format=schema,
            extra_body=extra_body,
        ),
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


def text_to_image(prompt: str, seed: int | None = None, negative_extra: str = "") -> bytes:
    """Standalone image — the canonical character reference (ADR-001), and `generate_scene`'s
    no-reference fallback.

    `negative_extra` exists because those two callers want opposite backgrounds: a reference must
    have none and a scene is nothing but. It is APPENDED to `NEGATIVE_PROMPT`, never a
    replacement — the lettering terms apply to every image this project draws.
    """
    negative = f"{NEGATIVE_PROMPT}, {negative_extra}" if negative_extra else NEGATIVE_PROMPT
    return _run_fal(settings.fal_image_model, {"prompt": prompt, "negative_prompt": negative}, seed)


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


# Every style preset used to end "no speech bubbles, no captions, no lettering"
# (`app/config.py:85`, commit 416ea33), and prod still shipped a gouache page of smeared
# pseudo-lettering on 2026-08-13, then a cel page with chat bubbles. Qwen-Image renders text *by
# design*, so a `no <term>` clause in the tail of the positive prompt competes with the thing the
# model is best at. The negative prompt is the channel that was never used: `_run_fal` sent
# `output_format` and nothing else, so every scene and every canonical reference this project has
# drawn had an empty one.
#
# Those tails are now GONE from the fragments (`app/config.py:74`) rather than merely duplicated
# here — while they stood, this list was subtracting terms the positive prompt kept re-asserting
# three clauses later. This is the sole statement of the ban.
#
# Verified against both endpoints' openapi (2026-08-13): `fal-ai/qwen-image` and
# `fal-ai/qwen-image-edit-2511` each declare `negative_prompt: str`. Unlike REFERENCE_FIELD this
# needs no loud guard — an endpoint without the field drops it silently and lands back on the
# behaviour above, which degrades rather than breaks.
NEGATIVE_PROMPT = (
    "text, letters, words, writing, signage, labels, captions, subtitles, "
    "watermark, signature, speech bubbles, speech balloons, comic panels"
)


def _run_fal(endpoint: str, arguments: dict, seed: int | None) -> bytes:
    if seed is not None:
        arguments = {**arguments, "seed": seed}
    # Defaults first so `arguments` can override either one; no caller does today.
    result = _fal().subscribe(
        endpoint,
        arguments={"output_format": "png", "negative_prompt": NEGATIVE_PROMPT, **arguments},
    )
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
    """A classifier that did not answer is a broken classifier, not a guilty child.

    `""` used to fall through `startswith("safe")` as `unsafe`, so a truncated or empty
    completion became `content_flagged` → `failure_reason='child_text'` → "let's change a few
    words." Raising instead routes it where `kid-flow-failure-semantics.md` §4.1 already puts a
    dead classifier: primary → backstop-only, backstop → `moderation_error` → machine → `retry`.
    Still fail-closed; only the blame moves off the child.
    """
    if not response.startswith(("safe", "unsafe")):
        raise RuntimeError(f"guard returned no verdict: {response[:80]!r}")
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


# Bucketed because assignment used to be positional: the Nth name detected got pool[N], so a boy
# became "Ana" and the caption kept saying "he". The redacted text is what every downstream stage
# reads — cast list, canonical character reference, scene prompts — so a pronoun that contradicts
# the name is a consistency defect, not a cosmetic one.
_PSEUDONYM_POOLS = {
    "feminine": ["Ana", "Maya", "Elena", "Lily", "Sophie", "Chloe", "Lucy", "Nora"],
    "masculine": ["Ben", "Daniel", "Leo", "Miguel", "Andres", "Nico", "Teo", "Jack"],
    "neutral": ["Jordan", "Alex", "Casey", "Taylor", "Ariel", "Jamie", "Alexis", "Riley"],
}

_MASCULINE_PRONOUNS = {"he", "him", "his", "himself"}
_FEMININE_PRONOUNS = {"she", "her", "hers", "herself"}
# Deliberately NOT evidence: `they/them/their` takes a plural antecedent ("Joe and Grace ... They
# were always playing together"), and `it/its` never discriminates. Both stop the scan instead of
# voting, so a window never runs past one character's pronouns into the next character's.
_STOP_PRONOUNS = {"they", "them", "their", "theirs", "themselves", "it", "its", "itself"}
_WORD_RE = re.compile(r"[A-Za-z']+")
_PRONOUN_WINDOW = 12  # tokens after a mention; wider starts crossing into the next sentence's subject


def _infer_gender(text: str, name: str) -> str:
    """Nearest pronoun after each mention of `name`, gendered vote wins, ties go neutral.

    Measured on the donated sample stories (2026-08-13): 4 right, 0 wrong, 3 abstentions. It
    fails by abstaining to the neutral pool, which is the direction that cannot misgender a child's
    character. Full coreference would need a model `en_core_web_sm` does not ship.
    """
    words = [w.casefold() for w in _WORD_RE.findall(text)]
    target = _WORD_RE.findall(name.casefold())
    votes = set()
    for i in range(len(words) - len(target) + 1):
        if words[i : i + len(target)] != target:
            continue
        for word in words[i + len(target) : i + len(target) + _PRONOUN_WINDOW]:
            if word in _STOP_PRONOUNS:
                break
            if word in _MASCULINE_PRONOUNS:
                votes.add("masculine")
                break
            if word in _FEMININE_PRONOUNS:
                votes.add("feminine")
                break
    return votes.pop() if len(votes) == 1 else "neutral"

# Spec §4c enumerates exactly what redaction does: persons pseudonymize, structured identifiers
# hard-redact. Everything else spaCy's NER guesses — ORGANIZATION, LOCATION, DATE_TIME, NRP — is
# narrative, not identity. Handing those to the anonymizer's default operator punched holes in the
# child's prose: prod job e94cc400 (2026-08-11) titled a story "The Lost Little Star", spaCy called
# it an ORGANIZATION, and "<ORGANIZATION> upon a time" reached a book caption. That is the exact
# outcome §4c forbids when it argues redaction output *is* the narrative.
#
# Allowlist, not denylist: a Presidio upgrade that ships a new free-text recognizer must not
# silently start eating captions again. A new *identifier* recognizer has to be added here — the
# safe direction to fail, since an unlisted identifier is caught by the §2 totality test.
_PERSON_ENTITIES = {"PERSON", "PH_PERSON"}
_IDENTIFIER_ENTITIES = {
    # ph_recognizers.py (§4b)
    "PH_MOBILE", "PH_ADDRESS", "PH_TIN", "PH_SSS", "PH_PHILHEALTH",
    # Presidio's built-in pattern/checksum recognizers — all structured, none narrative
    "CREDIT_CARD", "CRYPTO", "EMAIL_ADDRESS", "IBAN_CODE", "IP_ADDRESS", "MAC_ADDRESS",
    "MEDICAL_LICENSE", "PHONE_NUMBER", "UK_NHS", "URL", "US_BANK_NUMBER",
    "US_DRIVER_LICENSE", "US_ITIN", "US_PASSPORT", "US_SSN",
}
_REDACTED_ENTITIES = _PERSON_ENTITIES | _IDENTIFIER_ENTITIES


_DETERMINERS = {"a", "an", "the"}


def _after_determiner(text: str, start: int) -> bool:
    """A first name is never preceded by an article. spaCy tagged "bush" PERSON at 0.85 in
    "coming from behind a bush" (prod sample, 2026-08-13) and the caption shipped a character
    called Cielo. Chosen over a title-case test, which dropped this same false positive but also
    dropped genuinely lowercase names ("juan and sam") — a privacy regression this one avoids."""
    before = text[:start].rstrip()
    return bool(before) and before.split()[-1].casefold().strip("\"'“”‘’(") in _DETERMINERS


def _missed_mentions(text: str, names: list[str], existing: list) -> list:
    """Spans for mentions the NER missed. spaCy tagged "Grace" PERSON once and ORGANIZATION
    twice in the same story, so only a third of her mentions were replaced and the book ended up
    with Ana, Ben *and* Grace — one child's character split into two. Once a string is a person
    anywhere in the text it is a person everywhere in it.

    Case-sensitive on purpose: matching "Grace" against the noun "grace" would put a stand-in
    name in the middle of the child's prose."""
    from presidio_analyzer import RecognizerResult

    spans = [(r.start, r.end) for r in existing]
    extra = []
    for name in dict.fromkeys(names):
        for match in re.finditer(rf"\b{re.escape(name)}\b", text):
            if any(match.start() < end and start < match.end() for start, end in spans):
                continue
            if _after_determiner(text, match.start()):
                continue
            extra.append(RecognizerResult("PERSON", match.start(), match.end(), 0.85))
            spans.append((match.start(), match.end()))
    return extra


def _story_rng(text: str) -> random.Random:
    """Seeded from the story, never from the clock: the same text must always redact to the same
    names. `run_job.py:219` resumes a durable checkpoint so `input_gate` does not normally re-run,
    but `graph.py:127` falls back to an in-memory checkpointer that dies with the process — one
    re-queued job and a clock-seeded shuffle would rename every character while the images already
    in storage keep the old ones.

    `hashlib`, not `hash()`: Python salts `str.__hash__` with PYTHONHASHSEED, so `hash()` varies
    per worker process and would reintroduce that hazard while passing every test on one machine.
    """
    return random.Random(int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big"))


def _too_similar(candidate: str, blocked: set[str]) -> bool:
    """Prefix containment in either direction — `Alex` must not appear in a book that already has
    an `Alexis`, and a story about `Analyn` must not gain a character called `Ana`. Ordered
    selection could never produce those pairs; a shuffle can. Character binding matches by name,
    so a near-duplicate is a pipeline problem before it is a readability one.

    ponytail: prefix only. `Ana`/`Anna` slips through — edit distance would catch it and costs a
    dependency or a scratch implementation for a pair that has not appeared in a donated story.
    """
    c = candidate.casefold()
    return any(c.startswith(b) or b.startswith(c) for b in blocked)


def _pseudonymizer(text: str, names: list[str]):
    """Fresh mapping per call — caching this would leak names between stories (spec §4c).

    `names` is every detected person, in reading order. Building the whole mapping up front is
    what lets a name's pseudonym depend on the *text* (its pronouns, its hash) rather than on the
    order the anonymizer happens to call back in.
    """
    rng = _story_rng(text)
    pools = {gender: rng.sample(pool, len(pool)) for gender, pool in _PSEUDONYM_POOLS.items()}
    taken = {n.casefold() for n in names}  # a stand-in must not collide with a real character
    mapping: dict[str, str] = {}
    for name in names:
        key = name.casefold()
        if key in mapping:
            continue
        blocked = taken | {p.casefold() for p in mapping.values()}
        candidates = pools[_infer_gender(text, name)] + pools["neutral"]
        # Exhaustion must not wrap: `pool[n % len(pool)]` merged the 7th character into the 1st,
        # silently rewriting who did what. Suffixing is ugly and unmistakably unique — the right
        # trade for a cast this size. ponytail: 16 names is the ceiling before suffixes appear.
        mapping[key] = next(
            (p for p in candidates if not _too_similar(p, blocked)),
            f"{pools['neutral'][0]}{len(mapping) + 1}",
        )
    return lambda value: mapping.get(value.casefold(), value)


def redact_pii(text: str) -> str:
    """Presidio PII redaction (CC-2). Persons pseudonymized so the story survives with a
    protagonist an illustrator can draw; structured identifiers hard-redact (spec §4c).
    en_core_web_sm must be downloaded before first call."""
    from presidio_anonymizer.entities import OperatorConfig

    analyzer, anonymizer = _presidio()
    detected = analyzer.analyze(text=text, language="en")
    results = [
        r for r in detected
        if r.entity_type in _REDACTED_ENTITIES
        and not (r.entity_type in _PERSON_ENTITIES and _after_determiner(text, r.start))
    ]
    # CC-5: log entity-type counts only — never the detected values (ADR-025 D5). `ignored` is
    # the tuning knob for _REDACTED_ENTITIES: a real identifier showing up there is a bug.
    _log.info(
        "pii_redaction entity_counts=%s ignored=%s",
        dict(Counter(r.entity_type for r in results)),
        dict(Counter(r.entity_type for r in detected if r.entity_type not in _REDACTED_ENTITIES)),
    )

    # Reading order matters twice over: the anonymizer calls the operator right-to-left (to avoid
    # offset shifts), and the pool is handed out first-come-first-served.
    ordered = sorted(results, key=lambda r: r.start)
    names = [text[r.start : r.end] for r in ordered if r.entity_type in _PERSON_ENTITIES]
    results += _missed_mentions(text, names, ordered)
    assign = _pseudonymizer(text, names)

    person = OperatorConfig("custom", {"lambda": assign})
    return anonymizer.anonymize(
        text=text, analyzer_results=results,
        operators={"PERSON": person, "PH_PERSON": person},
    ).text


# ADR-032: Local Qwen3Guard removed to prevent OOM.


# `gpt-oss-safeguard-20b` is a REASONING model — its thinking is billed against `max_tokens`, and
# the verdict is the last thing it emits. At 100 it ran out mid-thought on roughly a third of runs
# (measured 2026-08-13: completion_tokens 47…145 on the same 7 stories, nondeterministic per call),
# returning empty content that `_parse_guard_response` read as "unsafe". Sized off the observed 145
# on a 150-word story against ADR-012's 800-word cap. Output tokens are billed as used, so the
# headroom is free on the runs that don't need it — one call per story either way.
_GUARD_MAX_TOKENS = 1024


# Guard prompt template — verify against https://huggingface.co/Qwen/Qwen3-Guard-Gen-0.6B
# before deploying. The model outputs "safe" or "unsafe\n<categories>" in its response.
_GUARD_SYSTEM = (
    "You are a content safety classifier for a children's education platform (ages 5–12). "
    "Classify the user message as 'safe' or 'unsafe'. "
    "If unsafe, list the violated categories on the next line."
)


def classify_text_primary(text: str) -> tuple[bool, list[str]]:
    """Primary text guard via OpenRouter (ADR-032). Returns (is_safe, categories)."""
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key, timeout=30.0, max_retries=MAX_RETRIES)
    completion = client.chat.completions.create(
        model=settings.moderation_primary_model,
        messages=[{"role": "system", "content": _GUARD_SYSTEM}, {"role": "user", "content": text}],
        max_tokens=_GUARD_MAX_TOKENS,
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
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key, timeout=30.0, max_retries=MAX_RETRIES)
    completion = client.chat.completions.create(
        model=settings.moderation_backstop_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=_GUARD_MAX_TOKENS,
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
    _log.info("classify_image_primary: is_safe=%s reasoning=%.300s", verdict.is_safe, verdict.safety_reasoning)
    return verdict.is_safe


class _ImageSafetyVerdict(BaseModel):
    # Reason-before-score per ADR-004.
    safety_reasoning: str
    is_safe: bool


def classify_image_backstop(image_url: str) -> bool:
    """gemma-3-27b-it via OpenRouter — violence, gore, dangerous content check."""
    # "frightening imagery" flagged the genre. Prod job 4f7698d5 (2026-08-12) lost an 8-scene book
    # at the last gate on s2 — a girl walking up to the "big, scary house" that IS the story, whose
    # text `input_gate` had already passed. `_soften_prompt` cannot rescue that: prepending
    # "child-safe, gentle" does not remove the scary house, so the retry flagged too and 11 paid
    # images went in the bin. The primary is NSFW-only (see above), so this rubric was the only one
    # that could have fired.
    #
    # The hard categories are untouched. What is qualified is the one clause that made ordinary
    # narrative tension indistinguishable from harm.
    # ⚠️ UNMEASURED. Spec §7 names `tests/fixtures/moderation_cases.py` as the guard for exactly
    # this, but that set is a Post-Phase-2 item and does not exist yet, and the one probe that does
    # (`spikes/phase_05.py moderation`) is TEXT-only — it cannot exercise an image rubric at all.
    # So this loosening rests on reasoning, not measurement. Build the image arm before Phase 2.
    prompt = (
        "You are reviewing an image for a children's educational storybook platform (ages 5–12). "
        "Assess whether the image is safe for children. "
        "Flag: violence, gore, sexual content, dangerous activities a child might imitate, and "
        "imagery likely to genuinely distress a young child. "
        "Do NOT flag ordinary storybook atmosphere: a spooky house, a dark forest, a worried or "
        "startled character, mild suspense. Children's stories are built out of these, and the "
        "story text this image illustrates has already passed a separate safety gate."
    )
    verdict = judge(prompt, [image_url], _ImageSafetyVerdict, model=settings.moderation_backstop_image_model)
    # ADR-004 makes the model reason before it scores; both callers then discarded the reasoning and
    # kept the bool, so a flag that killed a book left no account of what the classifier saw. Logged
    # here rather than returned: `char_ref_mod` and `output_mod` both call these, and widening the
    # return type would rewrite two nodes and three test files to carry a string neither branches on.
    # ponytail: truncated, not structured — a `ModerationResult` field if it ever needs querying.
    _log.info("classify_image_backstop: is_safe=%s reasoning=%.300s", verdict.is_safe, verdict.safety_reasoning)
    return verdict.is_safe
