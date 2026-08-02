import logging

from app.db import get_supabase_client
from contracts.story_memory import StoryMemory
from pipeline.generate_scene import BUCKET
from providers import classify_image_backstop, classify_image_primary

log = logging.getLogger(__name__)


def _get_signed_url(path: str) -> str:
    resp = get_supabase_client().storage.from_(BUCKET).create_signed_url(path, expires_in=300)
    return resp["signedURL"]


def char_ref_mod(state: StoryMemory) -> dict:
    updated = []
    for char in state.characters:
        if char.canonical_ref_image is None:
            # No ref drawn (char_bible skipped or species-only char) — nothing to moderate.
            updated.append(char.model_copy(update={"ref_moderation_status": "passed"}))
            continue

        # One retry on signed-URL failure (ADR-025 transient policy).
        signed_url = None
        for attempt in range(2):
            try:
                signed_url = _get_signed_url(char.canonical_ref_image)
                break
            except Exception as exc:
                if attempt == 1:
                    raise RuntimeError(
                        f"char_ref_mod: failed to sign URL for {char.canonical_ref_image}"
                    ) from exc

        primary_safe = classify_image_primary(signed_url)
        backstop_safe = classify_image_backstop(signed_url)

        if not (primary_safe and backstop_safe):
            log.error(
                "char_ref_mod: char_id=%s flagged (primary=%s backstop=%s)",
                char.char_id, primary_safe, backstop_safe,
            )
            raise RuntimeError("content_flagged")

        log.info("char_ref_mod: char_id=%s passed", char.char_id)
        updated.append(char.model_copy(update={"ref_moderation_status": "passed"}))

    return {"characters": updated}
