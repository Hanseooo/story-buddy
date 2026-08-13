import logging

from contracts.story_memory import StoryMemory
from providers import classify_image_backstop, classify_image_primary, get_signed_url

log = logging.getLogger(__name__)

# The cap on `char_bible → char_ref_mod → char_bible` cycles, enforced in `moderation_router`
# (spec §4.2). Lives here and is imported by graph.py, mirroring reveal.MAX_RETRY_TAPS.
# 1, because a second flag on an independently drawn image is evidence, not noise (spec §8 q4).
MAX_MOD_REDRAWS = 1


def char_ref_mod(state: StoryMemory) -> dict:
    updated = []
    for char in state.characters:
        if char.canonical_ref_image is None:
            # No ref drawn (char_bible skipped or species-only char) — nothing to moderate.
            updated.append(char.model_copy(update={"ref_moderation_status": "passed"}))
            continue

        if char.ref_moderation_status == "passed":
            # Already screened and the ref has not changed — do not re-bill the classifiers.
            # Both mint paths clear this status when they overwrite the image, which is what
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
            log.error(
                "char_ref_mod: char_id=%s flagged by primary — cleared, ref_mod_retry_count=%d",
                char.char_id, state.cost.ref_mod_retry_count,
            )
            updated.append(char.model_copy(
                update={"ref_moderation_status": "flagged", "canonical_ref_image": None}
            ))
            continue  # cleared → char_bible re-mints it if moderation_router grants the budget

        try:
            backstop_safe = classify_image_backstop(signed_url)
        except Exception as exc:
            # The backstop has nothing behind it, so an error here means genuinely unchecked.
            log.error("char_ref_mod: char_id=%s backstop error — hard fail per ADR-025 (%s)", char.char_id, exc)
            raise RuntimeError("moderation_error") from exc

        if not backstop_safe:
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
