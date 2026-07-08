from contracts.job_state import JobState


def segment(state: JobState) -> JobState:
    state["stage"] = "segment"
    return state
