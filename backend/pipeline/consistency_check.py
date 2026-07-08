from contracts.job_state import JobState


def consistency_check(state: JobState) -> JobState:
    state["stage"] = "consistency_check"
    return state
