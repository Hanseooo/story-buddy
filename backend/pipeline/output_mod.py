import logging

from contracts.story_memory import Attempt, StoryMemory
from pipeline.generate_scene import generate_and_store
from providers import classify_image_backstop, classify_image_primary, get_signed_url

log = logging.getLogger(__name__)


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

        signed_url = get_signed_url(scene.final_image_ref)

        try:
            passed = _check_image(signed_url)
        except Exception as exc:
            log.error("output_mod: scene_id=%s classifier error (%s)", scene.scene_id, exc)
            raise RuntimeError("moderation_error") from exc

        if passed:
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
        retry_url = get_signed_url(retry_path)

        try:
            retry_passed = _check_image(retry_url)
        except Exception as exc:
            log.error("output_mod: scene_id=%s retry classifier error (%s)", scene.scene_id, exc)
            raise RuntimeError("moderation_error") from exc

        if retry_passed:
            log.info("output_mod: scene_id=%s retry passed", scene.scene_id)
            updated_scenes.append(scene.model_copy(update={
                "final_image_ref": retry_path,
                "moderation_status": "passed",
                "attempts": [*scene.attempts, Attempt(image_ref=retry_path, prompt=softened, passed=True)],
            }))
        else:
            log.error("output_mod: scene_id=%s still flagged after retry — route_after_output_mod will fail job", scene.scene_id)
            updated_scenes.append(scene.model_copy(update={
                "final_image_ref": retry_path,
                "moderation_status": "failed",
                "attempts": [*scene.attempts, Attempt(image_ref=retry_path, prompt=softened, passed=False)],
            }))

    return {"scenes": updated_scenes}
