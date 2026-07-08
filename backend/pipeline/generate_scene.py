from contracts.job_state import JobState


def generate_scene(state: JobState) -> JobState:
    state["stage"] = "generate_scene"
    return state
