import logging

from contracts.story_memory import Attempt, StoryMemory
from pipeline.generate_scene import generate_and_store
from providers import classify_image_backstop, classify_image_primary, get_signed_url

log = logging.getLogger(__name__)


def _check_image(image_url: str) -> bool:
    """True if the image is safe. Posture mirrors `char_ref_mod` (spec §4b, aligned with
    `input_gate` on 2026-08-11): a PRIMARY classifier error degrades to backstop-only, a primary
    flag short-circuits, and a BACKSTOP error propagates — the callers turn that into
    `moderation_error`, which is still correct because the backstop has nothing behind it.

    §4c step 2 always said "same two-classifier check as `char_ref_mod`", but 44489cb aligned
    `input_gate` and `char_ref_mod` and missed this node, which left it hard-failing on ANY
    classifier exception. That made it the strictest gate in the pipeline while screening the
    least risky thing — an image we drew, from text `input_gate` passed, from a reference
    `char_ref_mod` passed — at the point where every scene has already been paid for.

    Prod job f4d0fd74 died exactly there: scene s5, OpenRouter 400 from Venice
    ("Image content is not supported by this model"), five scenes already moderated clean.
    """
    try:
        primary_safe = classify_image_primary(image_url)
    except Exception as exc:
        log.warning("output_mod: primary classifier failed (%s) — falling back to backstop", exc)
        primary_safe = None  # None = primary errored, not "passed"

    if primary_safe is False:
        # A second opinion cannot change a flag (spec §4a step 3).
        return False

    return classify_image_backstop(image_url)


def _soften_prompt(prompt: str) -> str:
    # ponytail: stock softening — prepend safety qualifier. Owned here, not by `self-refusal-fallback`
    # (that spec covers the model *refusing*; this is the model complying and the classifier flagging).
    # Upgrade path: if flagged scenes survive this retry in practice, borrow that spec's softener.
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
