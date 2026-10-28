"""Pause on checkpointed moderation evidence without repeating provider calls."""

import hashlib

from langgraph.types import interrupt

from contracts.story_memory import ModerationClearance, StoryMemory
from pipeline.optional_themes import has_bound_theme_review


def moderation_review(state: StoryMemory) -> dict:
    review = state.moderation_context.review
    if review is None or review.resolution is not None:
        raise RuntimeError("invalid moderation review state")
    decision = interrupt({"kind": "moderation_review", "review_id": str(review.review_id)})
    if (not isinstance(decision, dict) or decision.get("action") not in ("allow", "replace")
            or decision.get("review_id") != str(review.review_id)
            or decision.get("subject_version") != review.subject_version
            or decision.get("generation_epoch", -1) <= state.moderation_context.generation_epoch
            or review.kind not in ("scene_image", "character_reference", "story_text", "optional_themes")
            or (review.kind in ("story_text", "optional_themes") and decision.get("action") != "allow")):
        raise RuntimeError("invalid_moderation_decision")
    replacing = decision["action"] == "replace"
    context = state.moderation_context.model_copy(update={
        "generation_epoch": decision["generation_epoch"],
        "review": review.model_copy(update={"resolution": decision["action"], "replacement": replacing}),
    })
    if review.kind == "optional_themes":
        if not has_bound_theme_review(state):
            raise RuntimeError("invalid_moderation_subject")
        return {"moderation_context": context.model_copy(update={"accepted_theme_ids": review.criteria})}
    if review.kind == "story_text":
        text = state.input.redacted_text
        policy_version = decision.get("policy_version")
        if (text is None or review.subject_id != "input"
                or hashlib.sha256(text.encode("utf-8")).hexdigest() != review.subject_version
                or not isinstance(policy_version, str) or not policy_version):
            raise RuntimeError("invalid_moderation_subject")
        return {"input": state.input.model_copy(update={"moderation_clearance": ModerationClearance(
            subject_version=review.subject_version, review_id=review.review_id, policy_version=policy_version,
        )}), "moderation_context": context}
    if review.kind == "character_reference":
        char = next((c for c in state.characters if c.char_id == review.subject_id), None)
        if not char or not char.canonical_ref_image:
            raise RuntimeError("invalid_moderation_subject")
        return {"characters": [c.model_copy(update={
            "ref_moderation_status": None if replacing else "teacher_allowed",
        }) if c.char_id == char.char_id else c for c in state.characters], "moderation_context": context}
    scene = next(s for s in state.scenes if s.scene_id == review.subject_id)
    if not scene.final_image_ref or not any(a.image_ref == scene.final_image_ref for a in scene.attempts):
        raise RuntimeError("invalid_moderation_subject")
    return {"scenes": [scene.model_copy(update={
        "moderation_status": None if replacing else "teacher_allowed",
        "attempts": [a.model_copy(update={"safety_eligibility": "excluded" if replacing else "teacher_allowed"})
                     if a.image_ref == scene.final_image_ref else a for a in scene.attempts],
    })], "moderation_context": context}
