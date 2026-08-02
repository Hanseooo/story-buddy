import logging

from app.db import get_supabase_client
from contracts.story_memory import Attempt, StoryMemory
from pipeline.generate_scene import BUCKET, generate_and_store
from providers import classify_image_backstop, classify_image_primary

log = logging.getLogger(__name__)


def _get_signed_url(path: str) -> str:
    resp = get_supabase_client().storage.from_(BUCKET).create_signed_url(path, expires_in=300)
    return resp["signedURL"]


def _check_image(image_url: str) -> bool:
    """True if both classifiers pass."""
    return classify_image_primary(image_url) and classify_image_backstop(image_url)


def _soften_prompt(prompt: str) -> str:
    # ponytail: stock softening — prepend safety qualifier; self-refusal-fallback spec owns the full strategy
    return f"child-safe, gentle, age-appropriate illustration, no violence or inappropriate content: {prompt}"


def output_mod(state: StoryMemory) -> dict:
    updated_scenes = []
    for scene in state.scenes:
        if scene.final_image_ref is None:
            # Regeneration controller owns unresolved refs (spec §4c edge case).
            updated_scenes.append(scene)
            continue

        signed_url = _get_signed_url(scene.final_image_ref)
        if _check_image(signed_url):
            log.info("output_mod: scene_id=%s passed", scene.scene_id)
            updated_scenes.append(scene.model_copy(update={"moderation_status": "passed"}))
            continue

        # One soften-and-retry (spec §4c step 4).
        log.info("output_mod: scene_id=%s flagged — softening and retrying", scene.scene_id)
        softened = _soften_prompt(scene.prompt or "")

        by_id = {c.char_id: c for c in state.characters}
        ref_paths = [
            by_id[cid].canonical_ref_image
            for cid in scene.characters_present
            if cid in by_id and by_id[cid].canonical_ref_image
        ]

        retry_n = len(scene.attempts) + 1
        retry_path, _ = generate_and_store(softened, state.story_id, scene.scene_id, retry_n, ref_paths)
        retry_url = _get_signed_url(retry_path)

        if _check_image(retry_url):
            log.info("output_mod: scene_id=%s retry passed", scene.scene_id)
            updated_scenes.append(scene.model_copy(update={
                "final_image_ref": retry_path,
                "moderation_status": "passed",
                "attempts": [*scene.attempts, Attempt(image_ref=retry_path, prompt=softened, passed=True)],
            }))
        else:
            log.error("output_mod: scene_id=%s still flagged after retry — failing job", scene.scene_id)
            raise RuntimeError("output_moderation_failed")

    return {"scenes": updated_scenes}
