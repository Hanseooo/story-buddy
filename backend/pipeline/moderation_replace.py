"""One teacher-requested same-intent scene draw, using the existing moderation slot."""

from app.config import MAX_SCENE_MOD_REPLACEMENTS, check_image_budget, settings
from contracts.story_memory import Attempt, StoryMemory
from pipeline.generate_scene import generate_and_store
from pipeline.prompt_optimizer import referenced_characters


def scene_replacement_disabled_reason(state: StoryMemory, subject_id: str, image_count: int = 0) -> str | None:
    scene = next((s for s in state.scenes if s.scene_id == subject_id), None)
    if not scene or not scene.final_image_ref or not scene.prompt:
        return "replacement_source_unavailable"
    if (scene.moderation_replacement_count >= MAX_SCENE_MOD_REPLACEMENTS
            or len(scene.attempts) >= settings.max_scene_attempts + MAX_SCENE_MOD_REPLACEMENTS):
        return "replacement_already_used"
    try:
        check_image_budget(max(state.cost.image_count, image_count))
    except RuntimeError:
        return "image_budget_exhausted"
    return None


def moderation_replace(state: StoryMemory) -> dict:
    review = state.moderation_context.review
    if (state.moderation_context.mode != "teacher_review_v1" or not review
            or review.kind != "scene_image" or review.resolution != "replace" or not review.replacement):
        raise RuntimeError("invalid_moderation_replacement")
    reason = scene_replacement_disabled_reason(state, review.subject_id)
    if reason:
        raise RuntimeError(reason)
    scene = next(s for s in state.scenes if s.scene_id == review.subject_id)
    refs = [c.canonical_ref_image for c in referenced_characters(scene.characters_present, state.characters)]
    # The original prompt and the same ordered image roll preserve approved intent/style.
    # Refusal propagates. There is no softener or automatic extra draw in this mode.
    check_image_budget(state.cost.image_count)
    path, paid = generate_and_store(scene.prompt, state.story_id, scene.scene_id, len(scene.attempts) + 1, refs)
    return {
        "scenes": [scene.model_copy(update={
            "attempts": [*scene.attempts, Attempt(image_ref=path, prompt=scene.prompt)],
            "final_image_ref": None, "moderation_status": None,
            "moderation_replacement_count": scene.moderation_replacement_count + 1,
        })],
        "cost": state.cost.model_copy(update={"image_count": state.cost.image_count + int(paid)}),
    }
