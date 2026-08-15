import httpx
import openai
from rq.timeouts import JobTimeoutException

from worker.run_worker import HardJobTimeout


def classify_failure_reason(exc: BaseException) -> str:
    if isinstance(exc, (HardJobTimeout, JobTimeoutException)):
        return "worker_stopped"

    msg = str(exc)

    # Exact sentinels
    if msg == "content_flagged":
        return "child_text"
    if msg == "ref_flagged":
        return "character_safety"
    if msg == "output_moderation_failed":
        return "scene_safety"
    if msg == "moderation_error":
        return "service_busy"
    if msg == "worker_stopped":
        return "worker_stopped"
    if "image budget exceeded" in msg:
        return "book_limit"

    # Explicit provider quota/credit limits
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None and exc.response.status_code == 402:
        return "service_limit"

    if isinstance(exc, openai.RateLimitError):
        code = getattr(exc, "code", None)
        body = getattr(exc, "body", None)
        body_code = body.get("error", {}).get("code") if isinstance(body, dict) else None
        if "insufficient_quota" in (code, body_code):
            return "service_limit"
        return "service_busy"

    # Transient service failures
    if isinstance(exc, (TimeoutError, httpx.TimeoutException, httpx.NetworkError)):
        return "service_busy"

    # `providers.py` calls through the OpenAI SDK, which wraps a dropped connection in its own
    # type rather than re-raising the httpx error — without these two, a network blip reaches the
    # child as "Something interrupted your story" instead of "the service is busy" (spec §3).
    if isinstance(exc, (openai.APIConnectionError, openai.InternalServerError)):
        return "service_busy"

    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        if exc.response.status_code == 429 or exc.response.status_code >= 500:
            return "service_busy"

    # Fallback
    return "system_error"
