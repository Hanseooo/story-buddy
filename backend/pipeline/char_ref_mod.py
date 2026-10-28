import logging
import hashlib
from datetime import datetime, timezone
from uuid import UUID, uuid5

from app.config import settings
from app.moderation_policy import TEACHER_MODERATION_CRITERIA
from contracts.story_memory import ClassifierEvidence, ReviewContext, StoryMemory
from providers import (
    IMAGE_BACKSTOP_INSTRUCTION_VERSION, IMAGE_PRIMARY_INSTRUCTION_VERSION, ModerationEvidenceError,
    classify_image_backstop, classify_image_primary, download_book_image, get_signed_url,
)

log = logging.getLogger(__name__)

# The cap on `char_bible → char_ref_mod → char_bible` cycles, enforced in `moderation_router`
# (spec §4.2). Lives here and is imported by graph.py, mirroring reveal.MAX_RETRY_TAPS.
# 1, because a second flag on an independently drawn image is evidence, not noise (spec §8 q4).
MAX_MOD_REDRAWS = 1


def require_reference_clearance(state: StoryMemory) -> None:
    """ADR-080: consumers accept only exact classifier/teacher-cleared references."""
    if state.moderation_context.mode == "teacher_review_v1" and any(
        c.canonical_ref_image and c.ref_moderation_status not in ("passed", "teacher_allowed")
        for c in state.characters
    ):
        raise RuntimeError("unmoderated_reference")


def char_ref_mod(state: StoryMemory) -> dict:
    updated = []
    reviewing = state.moderation_context.mode == "teacher_review_v1"
    for index, char in enumerate(state.characters):
        if char.canonical_ref_image is None:
            # No ref drawn (char_bible skipped or species-only char) — nothing to moderate.
            updated.append(char.model_copy(update={"ref_moderation_status": "passed"}))
            continue

        if char.ref_moderation_status == "passed" or (reviewing and char.ref_moderation_status == "teacher_allowed"):
            # Already screened and the ref has not changed — do not re-bill the classifiers.
            # All mint/replacement paths clear this status when they overwrite the image, which is what
            # makes the skip safe rather than a CC-1 hole (`moderation-stack.md` §4b).
            updated.append(char)
            continue

        # One retry on signed-URL failure (ADR-025 transient policy).
        for attempt in range(2):
            try:
                signed_url = get_signed_url(char.canonical_ref_image)
                break
            except Exception as exc:
                if attempt == 1:
                    raise RuntimeError(
                        f"char_ref_mod: failed to sign URL for {char.canonical_ref_image}"
                    ) from exc

        # Posture and call order both mirror `input_gate` (2026-08-11). The two nodes cited the
        # same ADR-025 and read it in opposite directions; this one was the stricter, which was
        # backwards — `input_gate` screens UNTRUSTED child text, this screens an image we
        # generated from text that already passed it. What degrades is the call count, never the
        # gate: the backstop always runs and can always flag.
        evidence = []
        primary_reasons = []
        checked_at = datetime.now(timezone.utc)
        try:
            primary_safe = (classify_image_primary(signed_url, reasons=primary_reasons)
                            if reviewing else classify_image_primary(signed_url))
        except ModerationEvidenceError:
            raise
        except Exception as exc:
            log.warning(
                "char_ref_mod: char_id=%s primary classifier failed (%s) — falling back to backstop",
                char.char_id, exc,
            )
            primary_safe = None  # None = primary errored, not "passed"

        if reviewing:
            evidence.append(ClassifierEvidence(
                layer="primary", model_id=settings.moderation_primary_image_model,
                instruction_version=IMAGE_PRIMARY_INSTRUCTION_VERSION,
                outcome="error" if primary_safe is None else "safe" if primary_safe else "flagged",
                checked_at=checked_at, reason=primary_reasons[0] if primary_reasons else None,
            ))
        if primary_safe is False:
            if reviewing:
                evidence.append(ClassifierEvidence(
                    layer="backstop", model_id=settings.moderation_backstop_image_model,
                    instruction_version=IMAGE_BACKSTOP_INSTRUCTION_VERSION, outcome="not_called",
                ))
                return _hold_reference(state, updated, index, evidence)
            # No backstop call needed — a second opinion cannot change a flag (spec §4a step 3).
            log.error(
                "char_ref_mod: char_id=%s flagged by primary — cleared, ref_mod_retry_count=%d",
                char.char_id, state.cost.ref_mod_retry_count,
            )
            updated.append(char.model_copy(
                update={"ref_moderation_status": "flagged", "canonical_ref_image": None}
            ))
            continue  # cleared → char_bible re-mints it if moderation_router grants the budget

        backstop_reasons = []
        checked_at = datetime.now(timezone.utc)
        try:
            backstop_safe = (classify_image_backstop(signed_url, reasons=backstop_reasons)
                             if reviewing else classify_image_backstop(signed_url))
        except Exception as exc:
            # The backstop has nothing behind it, so an error here means genuinely unchecked.
            log.error("char_ref_mod: char_id=%s backstop error — hard fail per ADR-025 (%s)", char.char_id, exc)
            raise RuntimeError("moderation_error") from exc

        if reviewing:
            evidence.append(ClassifierEvidence(
                layer="backstop", model_id=settings.moderation_backstop_image_model,
                instruction_version=IMAGE_BACKSTOP_INSTRUCTION_VERSION,
                outcome="safe" if backstop_safe else "flagged", checked_at=checked_at,
                reason=backstop_reasons[0] if backstop_reasons else None,
            ))
        if not backstop_safe:
            if reviewing:
                return _hold_reference(state, updated, index, evidence)
            log.error(
                "char_ref_mod: char_id=%s flagged by backstop (primary=%s) — cleared, ref_mod_retry_count=%d",
                char.char_id, primary_safe, state.cost.ref_mod_retry_count,
            )
            updated.append(char.model_copy(
                update={"ref_moderation_status": "flagged", "canonical_ref_image": None}
            ))
            continue

        log.info("char_ref_mod: char_id=%s passed", char.char_id)
        updated.append(char.model_copy(update={"ref_moderation_status": "passed"}))

    return {"characters": updated}


def _hold_reference(state: StoryMemory, updated: list, index: int, evidence: list[ClassifierEvidence]) -> dict:
    char = state.characters[index]
    version = hashlib.sha256(download_book_image(char.canonical_ref_image)).hexdigest()
    review = ReviewContext(
        review_id=uuid5(UUID(state.story_id),
                        f"character_reference:{char.char_id}:{version}:{state.moderation_context.generation_epoch}"),
        kind="character_reference", subject_id=char.char_id, subject_version=version,
        return_node="char_ref_mod", classifier_evidence=evidence, criteria=list(TEACHER_MODERATION_CRITERIA),
        replacement=bool(state.cost.ref_mod_retry_count),
    )
    return {
        "characters": [*updated, char.model_copy(update={"ref_moderation_status": "flagged"}),
                       *state.characters[index + 1:]],
        "moderation_context": state.moderation_context.model_copy(update={"review": review}),
    }
