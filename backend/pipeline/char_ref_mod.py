import logging

from contracts.story_memory import StoryMemory
from providers import classify_image_backstop, classify_image_primary, get_signed_url

log = logging.getLogger(__name__)


def char_ref_mod(state: StoryMemory) -> dict:
    updated = []
    for char in state.characters:
        if char.canonical_ref_image is None:
            # No ref drawn (char_bible skipped or species-only char) — nothing to moderate.
            updated.append(char.model_copy(update={"ref_moderation_status": "passed"}))
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
        try:
            primary_safe = classify_image_primary(signed_url)
        except Exception as exc:
            log.warning(
                "char_ref_mod: char_id=%s primary classifier failed (%s) — falling back to backstop",
                char.char_id, exc,
            )
            primary_safe = None  # None = primary errored, not "passed"

        if primary_safe is False:
            # No backstop call needed — a second opinion cannot change a flag (spec §4a step 3).
            log.error("char_ref_mod: char_id=%s flagged by primary", char.char_id)
            updated.append(char.model_copy(update={"ref_moderation_status": "flagged"}))
            continue  # moderation_router reads this and raises content_flagged

        try:
            backstop_safe = classify_image_backstop(signed_url)
        except Exception as exc:
            # The backstop has nothing behind it, so an error here means genuinely unchecked.
            log.error("char_ref_mod: char_id=%s backstop error — hard fail per ADR-025 (%s)", char.char_id, exc)
            raise RuntimeError("moderation_error") from exc

        if not backstop_safe:
            log.error(
                "char_ref_mod: char_id=%s flagged by backstop (primary=%s)",
                char.char_id, primary_safe,
            )
            updated.append(char.model_copy(update={"ref_moderation_status": "flagged"}))
            continue

        log.info("char_ref_mod: char_id=%s passed", char.char_id)
        updated.append(char.model_copy(update={"ref_moderation_status": "passed"}))

    return {"characters": updated}
