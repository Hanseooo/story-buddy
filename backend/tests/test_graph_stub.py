"""The one test proving the graph is wired at all.

`StoryMemory` carries no `stage` — job status lives on the job row (ADR-023 Decision 3) — and
with four pass-through stubs a graph that runs every node and one that runs none produce nearly
identical state. `stream_mode="updates"` yields exactly one chunk per node execution, keyed by
node name, in order, INCLUDING nodes that return {}. That is the replacement for `stage`.
"""
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
from pipeline.graph import build_graph

EXPECTED_ORDER = [
    "input_gate",
    "analyze",
    "segment",
    "char_bible",
    "generate_scene",
    "consistency_check",
    "compose",
]


def _initial_state(story_id: str) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id=story_id,
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A dog runs in a field."),
    )


def _mock_call_points(monkeypatch):
    monkeypatch.setattr("pipeline.analyze.caption_for", lambda text: "stub caption")
    monkeypatch.setattr("pipeline.segment.caption_for", lambda text: "stub caption")
    monkeypatch.setattr(
        "pipeline.generate_scene.generate_and_store",
        lambda prompt, story_id: "stub/path.png",
    )


def test_stub_graph_runs_all_nodes_in_order(monkeypatch):
    _mock_call_points(monkeypatch)
    app_graph = build_graph()

    ran = [
        next(iter(chunk))
        for chunk in app_graph.stream(
            _initial_state("test-job"),
            config={"configurable": {"thread_id": "test-job"}},
            stream_mode="updates",
        )
    ]

    assert ran == EXPECTED_ORDER


def test_stub_graph_full_run_with_real_call_points_mocked(monkeypatch):
    _mock_call_points(monkeypatch)
    app_graph = build_graph()

    result = app_graph.invoke(
        _initial_state("test-job-2"), config={"configurable": {"thread_id": "test-job-2"}}
    )

    # invoke() returns a dict; the values inside are still model instances.
    assert result["input"].redacted_text == "A dog runs in a field."
    assert result["input"].moderation.passed is True
    assert [s.scene_id for s in result["scenes"]] == ["s0"]
    assert result["scenes"][0].caption == "stub caption"
    assert result["scenes"][0].final_image_ref == "stub/path.png"
