from contracts.story_memory import Scene, StoryMemory
from pipeline.analyze import caption_for


def segment(state: StoryMemory) -> dict:
    # ponytail: one scene per story. The real segmenter splits into pages and mints s0..sN;
    # this mints s0 only. scene_id convention: §2.1.
    text = state.input.redacted_text or state.input.raw_text
    return {"scenes": [Scene(scene_id="s0", text_excerpt=text, caption=caption_for(text))]}
