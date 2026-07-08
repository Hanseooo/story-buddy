from contracts.job_state import JobState


def char_bible(state: JobState) -> JobState:
    state["stage"] = "char_bible"
    return state
