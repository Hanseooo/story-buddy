"""Pause on checkpointed moderation evidence without repeating provider calls."""

from langgraph.types import interrupt

from contracts.story_memory import StoryMemory


def moderation_review(state: StoryMemory) -> dict:
    review = state.moderation_context.review
    if review is None or review.resolution is not None:
        raise RuntimeError("invalid moderation review state")
    interrupt({"kind": "moderation_review", "review_id": str(review.review_id)})
    raise RuntimeError("moderation review resolution is not available")
