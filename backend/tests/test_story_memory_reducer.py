"""ADR-024 requires verifying the reducer against the pinned LangGraph before relying on it.
This is version-sensitive behaviour, not a given — if a LangGraph bump breaks it, it breaks here
rather than silently dropping scene writes in production.
"""
from langgraph.graph import END, StateGraph

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, Scene, StoryMemory


def _state(scenes: list[Scene]) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x"),
        scenes=scenes,
    )


def _build(node):
    graph = StateGraph(StoryMemory)
    graph.add_node("n", node)
    graph.set_entry_point("n")
    graph.add_edge("n", END)
    return graph.compile()


def test_reducer_fires_on_a_partial_return():
    """The node returns ONE scene; the other two must survive."""
    def n(state: StoryMemory) -> dict:
        return {"scenes": [state.scenes[1].model_copy(update={"final_image_ref": "p.png"})]}

    app = _build(n)
    result = app.invoke(_state([Scene(scene_id=f"s{i}", text_excerpt=str(i)) for i in range(3)]))

    assert [s.scene_id for s in result["scenes"]] == ["s0", "s1", "s2"]
    assert result["scenes"][1].final_image_ref == "p.png"
    assert result["scenes"][0].final_image_ref is None


def test_reducer_appends_a_new_scene_id_through_the_graph():
    def n(state: StoryMemory) -> dict:
        return {"scenes": [Scene(scene_id="s1", text_excerpt="1")]}

    app = _build(n)
    result = app.invoke(_state([Scene(scene_id="s0", text_excerpt="0")]))
    assert [s.scene_id for s in result["scenes"]] == ["s0", "s1"]


def test_invoke_returns_a_dict_of_model_values():
    """Documented because it bites: invoke() returns a dict, NOT a StoryMemory —
    but the values inside are still model instances. `result["scenes"][0].caption`, never
    `result.scenes`. Consumers in worker/run_job.py depend on this."""
    app = _build(lambda state: {})
    result = app.invoke(_state([Scene(scene_id="s0", text_excerpt="0", caption="hi")]))

    assert isinstance(result, dict)
    assert result["scenes"][0].caption == "hi"
