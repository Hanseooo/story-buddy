from contracts.job_state import JobState


def analyze(state: JobState) -> JobState:
    state["stage"] = "analyze"
    return state
