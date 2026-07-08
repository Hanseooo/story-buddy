from contracts.job_state import JobState


def compose(state: JobState) -> JobState:
    state["stage"] = "compose"
    return state
