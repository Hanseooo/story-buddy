import httpx
import openai
from worker.failure_classifier import classify_failure_reason
from worker.run_worker import HardJobTimeout
from rq.timeouts import JobTimeoutException


def test_classify_exact_sentinels():
    assert classify_failure_reason(Exception("content_flagged")) == "child_text"
    assert classify_failure_reason(Exception("ref_flagged")) == "character_safety"
    assert classify_failure_reason(Exception("output_moderation_failed")) == "scene_safety"
    assert classify_failure_reason(Exception("moderation_error")) == "service_busy"
    assert classify_failure_reason(RuntimeError("image budget exceeded: 12 >= 12 (ADR-025)")) == "book_limit"


def test_classify_service_busy():
    assert classify_failure_reason(TimeoutError("connection timed out")) == "service_busy"
    assert classify_failure_reason(httpx.ConnectTimeout("timeout")) == "service_busy"
    assert classify_failure_reason(httpx.NetworkError("network fail")) == "service_busy"

    request = httpx.Request("GET", "https://api.openai.com")
    response_500 = httpx.Response(500, request=request)
    assert classify_failure_reason(httpx.HTTPStatusError("500 Internal Server Error", request=request, response=response_500)) == "service_busy"

    response_429 = httpx.Response(429, request=request)
    assert classify_failure_reason(httpx.HTTPStatusError("429 Too Many Requests", request=request, response=response_429)) == "service_busy"

    assert classify_failure_reason(openai.InternalServerError("500 Internal Error", response=response_500, body=None)) == "service_busy"
    assert classify_failure_reason(openai.RateLimitError("429 Rate Limit", response=response_429, body=None)) == "service_busy"


def test_classify_service_limit():
    request = httpx.Request("GET", "https://api.openai.com")
    response_402 = httpx.Response(402, request=request)
    assert classify_failure_reason(httpx.HTTPStatusError("402 Payment Required", request=request, response=response_402)) == "service_limit"

    response_429 = httpx.Response(429, request=request)
    rate_limit_quota = openai.RateLimitError(
        "429 Insufficient Quota",
        response=response_429,
        body={"error": {"code": "insufficient_quota"}},
    )
    assert classify_failure_reason(rate_limit_quota) == "service_limit"


def test_classify_prose_never_selects_service_limit():
    """Spec §4: only an explicit provider response may say the allowance ran out.

    A message is not a response. Every string below is a plausible thing an unrelated defect can
    print, and each one used to tell a child "The story-making allowance has run out."
    """
    assert classify_failure_reason(Exception("HTTP 402 Insufficient credits")) == "system_error"
    assert classify_failure_reason(ValueError("job 402f1c3a produced no pages")) == "system_error"
    assert classify_failure_reason(RuntimeError("insufficient_quota")) == "system_error"


def test_classify_worker_stopped():
    assert classify_failure_reason(HardJobTimeout()) == "worker_stopped"
    assert classify_failure_reason(JobTimeoutException()) == "worker_stopped"
    assert classify_failure_reason(Exception("worker_stopped")) == "worker_stopped"


def test_classify_system_error():
    assert classify_failure_reason(ValueError("bad value")) == "system_error"
    assert classify_failure_reason(KeyError("missing key")) == "system_error"
    assert classify_failure_reason(Exception("random error")) == "system_error"


def test_classify_config_and_model_defects_are_system_error():
    """Spec §4: 401/403, a response-token ceiling, and malformed structured output are OUR bugs."""
    request = httpx.Request("GET", "https://api.openai.com")
    for status in (401, 403):
        response = httpx.Response(status, request=request)
        exc = httpx.HTTPStatusError(f"{status} error", request=request, response=response)
        assert classify_failure_reason(exc) == "system_error"

    assert classify_failure_reason(ValueError("finish_reason=length: max output tokens reached")) == "system_error"
    assert classify_failure_reason(ValueError("model returned unparseable JSON")) == "system_error"
