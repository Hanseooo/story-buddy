from contracts.job_state import JobState, SceneCaption
from providers import structured_text


def caption_for(text: str) -> str:
    result = structured_text(
        f"Write one short, kid-friendly caption (max 20 words) for this story: {text}",
        SceneCaption,
    )
    return result.caption


def analyze(state: JobState) -> JobState:
    state["caption"] = caption_for(state["input_text"])
    state["stage"] = "analyze"
    return state
