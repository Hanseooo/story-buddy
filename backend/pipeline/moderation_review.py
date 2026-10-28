"""Pause on checkpointed moderation evidence without repeating provider calls."""

from langgraph.types import interrupt

from contracts.story_memory import StoryMemory


def moderation_review(state: StoryMemory) -> dict:
    review = state.moderation_context.review
    if review is None or review.resolution is not None:
        raise RuntimeError("invalid moderation review state")
    decision = interrupt({"kind": "moderation_review", "review_id": str(review.review_id)})
    if (not isinstance(decision, dict) or decision.get("action") != "allow"
            or decision.get("review_id") != str(review.review_id)
            or decision.get("subject_version") != review.subject_version
            or decision.get("generation_epoch", -1) <= state.moderation_context.generation_epoch
            or review.kind != "scene_image"):
        raise RuntimeError("invalid_moderation_decision")
    scene = next(s for s in state.scenes if s.scene_id == review.subject_id)
    if not scene.final_image_ref or not any(a.image_ref == scene.final_image_ref for a in scene.attempts):
        raise RuntimeError("invalid_moderation_subject")
    return {"scenes": [scene.model_copy(update={
        "moderation_status": "teacher_allowed",
        "attempts": [a.model_copy(update={"safety_eligibility": "teacher_allowed"})
                     if a.image_ref == scene.final_image_ref else a for a in scene.attempts],
    })], "moderation_context": state.moderation_context.model_copy(update={
        "generation_epoch": decision["generation_epoch"],
        "review": review.model_copy(update={"resolution": "allow"}),
    })}
