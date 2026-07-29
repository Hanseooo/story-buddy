"""The one test proving the graph is wired at all.

`StoryMemory` carries no `stage` — job status lives on the job row (ADR-023 Decision 3) — and
with four pass-through stubs a graph that runs every node and one that runs none produce nearly
identical state. `stream_mode="updates"` yields exactly one chunk per node execution, keyed by
node name, in order, INCLUDING nodes that return {}. That is the replacement for `stage`.
"""
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory
from pipeline.analyze import StoryAnalysis
from pipeline.graph import build_graph
from pipeline.segment import ExtractedScene, SceneSegmentation

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


STUB_ANALYSIS = StoryAnalysis.model_validate(
    {
        "characters": [{"name": "the orange dog", "description": {"species": "dog"}}],
        "locations": [{"name": "a field"}],
        "objects": [],
        "timeline": [{"order": 0, "summary": "A dog runs."}],
    }
)


def _mock_call_points(monkeypatch):
    # One patch point per node (MASTER_SPEC §6 rule 1)
    monkeypatch.setattr("pipeline.analyze.extract_entities", lambda text: STUB_ANALYSIS)
    monkeypatch.setattr(
        "pipeline.segment.segment_scenes",
        lambda units, chars, timeline: SceneSegmentation(scenes=[
            ExtractedScene(start=0, end=len(units) - 1, characters_present=[])
        ]),
    )
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
    assert result["scenes"][0].caption == "A dog runs in a field."
    assert result["scenes"][0].final_image_ref == "stub/path.png"


def test_analyze_roster_survives_the_graph(monkeypatch):
    """Spec §6: patch the single helper and assert the roster reaches the end of the run.
    `analyze` runs before `segment`, so a roster that is dropped by a reducer or overwritten
    by a later node shows up here and nowhere else."""
    _mock_call_points(monkeypatch)
    app_graph = build_graph()

    result = app_graph.invoke(
        _initial_state("test-job-3"), config={"configurable": {"thread_id": "test-job-3"}}
    )

    assert [c.char_id for c in result["characters"]] == ["c0"]
    assert result["characters"][0].name == "the orange dog"
    assert result["characters"][0].description.species == "dog"
    assert [loc.loc_id for loc in result["locations"]] == ["loc0"]
    assert result["objects"] == []
    assert [e.order for e in result["timeline"]] == [0]
