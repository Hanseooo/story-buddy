"""One teacher-requested same-intent picture, using its existing moderation slot."""

from app.config import MAX_SCENE_MOD_REPLACEMENTS, check_image_budget, settings
from contracts.story_memory import Attempt, StoryMemory
from pipeline.generate_scene import generate_and_store
from pipeline.prompt_optimizer import referenced_characters
from pipeline.char_bible import replace_reference
from pipeline.char_ref_mod import MAX_MOD_REDRAWS, require_reference_clearance


def reference_replacement_disabled_reason(state: StoryMemory, subject_id: str, image_count: int = 0) -> str | None:
    char = next((c for c in state.characters if c.char_id == subject_id), None)
    if not char or not char.canonical_ref_image or not char.ref_generation_prompt:
        return "replacement_source_unavailable"
    if any(s.attempts or s.final_image_ref for s in state.scenes):
        return "dependent_scenes_exist"
    if state.cost.ref_mod_retry_count >= MAX_MOD_REDRAWS:
        return "replacement_already_used"
    try:
        check_image_budget(max(state.cost.image_count, image_count))
    except RuntimeError:
        return "image_budget_exhausted"
    return None


def replacement_disabled_reason(state: StoryMemory, kind: str, subject_id: str, image_count: int = 0) -> str | None:
    if kind == "character_reference":
        return reference_replacement_disabled_reason(state, subject_id, image_count)
    if kind == "scene_image":
        return scene_replacement_disabled_reason(state, subject_id, image_count)
    return "replacement_source_unavailable"


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
            or review.kind not in ("scene_image", "character_reference") or review.resolution != "replace" or not review.replacement):
        raise RuntimeError("invalid_moderation_replacement")
    reason = replacement_disabled_reason(state, review.kind, review.subject_id)
    if reason:
        raise RuntimeError(reason)
    if review.kind == "character_reference":
        return replace_reference(state, review.subject_id)
    require_reference_clearance(state)
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
