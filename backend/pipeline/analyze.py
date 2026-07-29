from pydantic import BaseModel

from contracts.story_memory import StoryMemory
from providers import structured_text


class SceneCaption(BaseModel):
    caption: str


def caption_for(text: str) -> str:
    result = structured_text(
        f"Write one short, kid-friendly caption (max 20 words) for this story: {text}",
        SceneCaption,
    )
    return result.caption


def analyze(state: StoryMemory) -> dict:
    # ponytail: stub — the `story-analyzer` spec fills this in (characters, locations, objects,
    # timeline) and mints c/loc/obj ids per §2.1. Deliberately not started: DECISION_BACKLOG.
    # `caption_for` lives here per D-F (transient wrapper beside its node); `segment` calls it.
    return {}
