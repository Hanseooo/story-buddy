import logging
from concurrent.futures import ThreadPoolExecutor

from contracts.story_memory import ModerationResult, StoryMemory
from providers import classify_text_backstop, classify_text_primary, redact_pii

log = logging.getLogger(__name__)


def input_gate(state: StoryMemory) -> dict:
    text = state.input.raw_text

    # Steps 1 & 2 are independent — run concurrently (spec §4a).
    with ThreadPoolExecutor(max_workers=2) as pool:
        primary_fut = pool.submit(classify_text_primary, text)
        redact_fut = pool.submit(redact_pii, text)

        try:
            primary_safe, categories = primary_fut.result()
        except Exception as exc:
            # Primary OOM/load error → backstop-only path; log the failure, don't skip moderation.
            log.warning("input_gate: primary classifier failed (%s) — falling back to backstop", exc)
            primary_safe = None  # None = primary errored, not "passed"
            categories = []

        redacted_text = redact_fut.result()

    def result(passed: bool, categories: list[str] | None = None) -> dict:
        """The ONLY way this node writes `input`. `input` has no reducer, so the return
        REPLACES the model outright — `model_copy` carries `word_count` and `truncated`
        (set in `worker/run_job.py`) forward. Every path used to build a fresh `Input(...)`
        instead, which reset both to their pydantic defaults on every job the pipeline has
        ever run. One constructor so a fifth path cannot reintroduce it.
        """
        return {
            "input": state.input.model_copy(update={
                "redacted_text": redacted_text,
                "moderation": ModerationResult(passed=passed, categories=categories or []),
            })
        }

    if primary_safe is False:
        # Primary flagged — no backstop call needed (spec §4a step 3).
        log.info("input_gate: primary flagged (categories=%s)", categories)
        return result(False, categories)

    # Primary passed or errored → always call backstop.
    try:
        backstop_safe, backstop_categories = classify_text_backstop(text)
    except Exception as exc:
        log.error("input_gate: backstop error — hard fail per ADR-025 (%s)", exc)
        # "moderation_error" category signals the router to raise RuntimeError("moderation_error").
        return result(False, ["moderation_error"])

    if not backstop_safe:
        log.info("input_gate: backstop flagged (categories=%s)", backstop_categories)
        return result(False, backstop_categories)

    return result(True)
