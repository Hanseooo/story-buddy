"""The one test proving the graph is wired at all.

`StoryMemory` carries no `stage` — job status lives on the job row (ADR-023 Decision 3) — and
with four pass-through stubs a graph that runs every node and one that runs none produce nearly
identical state. `stream_mode="updates"` yields exactly one chunk per node execution, keyed by
node name, in order, INCLUDING nodes that return {}. That is the replacement for `stage`.
"""
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, RefVerdict, StoryMemory
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
        input=Input(raw_text="A dog runs in a field. The dog barks."),
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
        lambda prompt, story_id, scene_id, attempt_n, ref_paths: (f"stub/{scene_id}-{attempt_n}.png", True),
    )
    monkeypatch.setattr(
        "pipeline.consistency_check.judge_attempt",
        lambda image_path, subjects: [],   # unchecked — every path still finalizes
    )
    monkeypatch.setattr(
        "pipeline.char_bible.mint_reference",
        lambda description, name, style_fragment, story_id, char_id: (
            f"{story_id}/ref-{char_id}.png",
            RefVerdict(differences_observed="none", matches_description=True, attributes_present=["dog"]),
            2,
        ),
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
    assert result["input"].redacted_text == "A dog runs in a field. The dog barks."
    assert result["input"].moderation.passed is True
    assert [s.scene_id for s in result["scenes"]] == ["s0"]
    assert result["scenes"][0].caption == "A dog runs in a field. The dog barks."
    assert result["scenes"][0].final_image_ref == "stub/s0-1.png"


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


def test_char_bible_references_survive_the_graph(monkeypatch):
    """Spec §6: patch the single helper and assert the references survive
    input_gate → analyze → segment → char_bible. `characters` has no reducer, so a later node
    replacing the list shows up here and nowhere else."""
    _mock_call_points(monkeypatch)
    app_graph = build_graph()

    result = app_graph.invoke(
        _initial_state("test-job-4"), config={"configurable": {"thread_id": "test-job-4"}}
    )

    character, = result["characters"]
    assert character.canonical_ref_image == "test-job-4/ref-c0.png"
    assert character.ref_verdict.matches_description is True
    assert character.ref_moderation_status is None   # Phase-2 owner, not this node
    assert result["cost"].image_count == 3           # 2 from mint_reference + 1 from generate_scene


def test_two_scene_run_loops_once_per_scene_and_reaches_compose(monkeypatch):
    """The ADR-024 loop-termination test, and the reason route_next_scene is worth testing.

    Two scenes must produce two generate_scene/consistency_check pairs, both finalized, exactly
    two attempts total, and a run that terminates at compose rather than spinning to
    recursion_limit.
    """
    _mock_call_points(monkeypatch)
    monkeypatch.setattr(
        "pipeline.segment.segment_scenes",
        lambda units, chars, timeline: SceneSegmentation(scenes=[
            ExtractedScene(start=0, end=0, characters_present=[]),
            ExtractedScene(start=1, end=len(units) - 1, characters_present=[]),
        ]),
    )
    app_graph = build_graph()

    ran = [
        next(iter(chunk))
        for chunk in app_graph.stream(
            _initial_state("test-job-loop"),
            config={"configurable": {"thread_id": "test-job-loop"}},
            stream_mode="updates",
        )
    ]
    result = app_graph.invoke(
        _initial_state("test-job-loop"), config={"configurable": {"thread_id": "test-job-loop"}}
    )

    assert ran == [
        "input_gate", "analyze", "segment", "char_bible",
        "generate_scene", "consistency_check",
        "generate_scene", "consistency_check",
        "compose",
    ]
    assert [s.final_image_ref for s in result["scenes"]] == ["stub/s0-1.png", "stub/s1-1.png"]
    assert sum(len(s.attempts) for s in result["scenes"]) == 2
