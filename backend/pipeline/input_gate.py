import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from datetime import datetime, timezone
from uuid import UUID, uuid5

from app.config import settings
from app.moderation_policy import TEACHER_MODERATION_CRITERIA
from contracts.story_memory import ClassifierEvidence, ModerationResult, ReviewContext, StoryMemory
from providers import classify_text_backstop, classify_text_primary, redact_pii

log = logging.getLogger(__name__)


def has_text_clearance(state: StoryMemory) -> bool:
    """Teacher permission applies only to the exact processed text, never an error."""
    clearance, text, moderation = state.input.moderation_clearance, state.input.redacted_text, state.input.moderation
    return bool(state.moderation_context.mode == "teacher_review_v1" and clearance and text is not None
        and moderation and "moderation_error" not in moderation.categories
        and clearance.subject_version == hashlib.sha256(text.encode("utf-8")).hexdigest())


def input_gate(state: StoryMemory) -> dict:
    text = state.input.raw_text
    review_mode = state.moderation_context.mode == "teacher_review_v1"
    evidence = []
    primary_time = datetime.now(timezone.utc)
    primary_model, backstop_model = settings.moderation_primary_model, settings.moderation_backstop_model
    # Review-mode intake already processed this text before persistence. Synthetic
    # corpus callers explicitly opt out of rewriting. Neither skips moderation.
    skip_redaction = state.input.synthetic_no_pii or review_mode

    # Steps 1 & 2 are independent — run concurrently (spec §4a).
    with ThreadPoolExecutor(max_workers=2) as pool:
        primary_fut = pool.submit(copy_context().run, classify_text_primary, text)
        redact_fut = None if skip_redaction else pool.submit(copy_context().run, redact_pii, text)

        try:
            primary_safe, categories = primary_fut.result()
        except Exception as exc:
            # Primary OOM/load error → backstop-only path; log the failure, don't skip moderation.
            log.warning("input_gate: primary classifier failed (%s) — falling back to backstop", exc)
            primary_safe = None  # None = primary errored, not "passed"
            categories = []

        redacted_text = text if skip_redaction else redact_fut.result()

    def record(layer, safe, categories, checked_at):
        if review_mode:
            # Classifier categories are free text, not a closed vocabulary. Privacy
            # processing must succeed before they become checkpointed review evidence.
            try:
                categories = [redact_pii(category) for category in categories]
            except Exception as exc:
                raise RuntimeError("moderation_error") from exc
            evidence.append(ClassifierEvidence(
                layer=layer, model_id=primary_model if layer == "primary" else backstop_model,
                instruction_version=f"text_{layer}_v1", checked_at=checked_at,
                outcome="error" if safe is None else "safe" if safe else "flagged",
                categories=categories,
            ))
        return categories

    categories = record("primary", primary_safe, categories, primary_time)

    def result(passed: bool, categories: list[str] | None = None) -> dict:
        """The ONLY way this node writes `input`. `input` has no reducer, so the return
        REPLACES the model outright — `model_copy` carries `word_count` and `truncated`
        (set in `worker/run_job.py`) forward. Every path used to build a fresh `Input(...)`
        instead, which reset both to their pydantic defaults on every job the pipeline has
        ever run. One constructor so a fifth path cannot reintroduce it.
        """
        changes = {
            "input": state.input.model_copy(update={
                "redacted_text": redacted_text,
                "moderation": ModerationResult(passed=passed, categories=categories or []),
            })
        }
        if review_mode and not passed and "moderation_error" not in (categories or []):
            subject_version = hashlib.sha256(redacted_text.encode("utf-8")).hexdigest()
            changes["moderation_context"] = state.moderation_context.model_copy(update={
                "review": ReviewContext(
                    review_id=uuid5(UUID(state.story_id), f"story_text:input:{subject_version}:{state.moderation_context.generation_epoch}"),
                    kind="story_text", subject_id="input", subject_version=subject_version,
                    return_node="optional_themes" if state.moderation_context.theme_ids else "analyze",
                    criteria=list(TEACHER_MODERATION_CRITERIA),
                    classifier_evidence=evidence,
                ),
            })
        return changes

    if primary_safe is False:
        if review_mode:
            evidence.append(ClassifierEvidence(layer="backstop", model_id=backstop_model,
                instruction_version="text_backstop_v1", outcome="not_called"))
        # Primary flagged — no backstop call needed (spec §4a step 3).
        log.info("input_gate: primary flagged (categories=%s)", categories)
        return result(False, categories)

    # Primary passed or errored → always call backstop.
    try:
        backstop_time = datetime.now(timezone.utc)
        backstop_safe, backstop_categories = classify_text_backstop(text)
    except Exception as exc:
        log.error("input_gate: backstop error — hard fail per ADR-025 (%s)", exc)
        # Raised here, as `char_ref_mod` and `output_mod` do, never returned as a failed result for
        # the router to raise on. LangGraph keeps a node's write even when the router after it
        # raises, so a resumed thread had nothing left to run: B5 smoke (2026-09-16) hit a Groq 429,
        # and the resume "completed" with no characters and quarantined the story.
        raise RuntimeError("moderation_error") from exc

    backstop_categories = record("backstop", backstop_safe, backstop_categories, backstop_time)
    if not backstop_safe:
        log.info("input_gate: backstop flagged (categories=%s)", backstop_categories)
        return result(False, backstop_categories)

    return result(True)
