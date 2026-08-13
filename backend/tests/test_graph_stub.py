"""The one test proving the graph is wired at all.

`StoryMemory` carries no `stage` — job status lives on the job row (ADR-023 Decision 3) — and
with four pass-through stubs a graph that runs every node and one that runs none produce nearly
identical state. `stream_mode="updates"` yields exactly one chunk per node execution, keyed by
node name, in order, INCLUDING nodes that return {}. That is the replacement for `stage`.
"""
from contracts.story_memory import CURRENT_SCHEMA_VERSION, FailureReason, Input, RefVerdict, StoryMemory
from pipeline.analyze import StoryAnalysis
from pipeline.consistency_check import SceneVerdict
from pipeline.graph import build_graph
from pipeline.segment import ExtractedScene, SceneSegmentation

EXPECTED_ORDER = [
    "input_gate",
    "analyze",
    "segment",
    "char_bible",
    "char_ref_mod",
    "reveal",
    "generate_scene",
    "consistency_check",
    "output_mod",
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
        lambda units, chars, timeline, locs=None: SceneSegmentation(scenes=[
            ExtractedScene(start=0, end=len(units) - 1, characters_present=[])
        ]),
    )
    monkeypatch.setattr(
        "pipeline.generate_scene.generate_and_store",
        lambda prompt, story_id, scene_id, attempt_n, ref_paths: (f"stub/{scene_id}-{attempt_n}.png", True),
    )
    # regenerate.py does `from ... import generate_and_store`, binding it into ITS namespace at
    # import time — patching only pipeline.generate_scene would leave the retry path live.
    monkeypatch.setattr(
        "pipeline.regenerate.generate_and_store",
        lambda prompt, story_id, scene_id, attempt_n, ref_paths: (f"stub/{scene_id}-{attempt_n}.png", True),
    )
    monkeypatch.setattr(
        "pipeline.consistency_check.judge_attempt",
        lambda image_path, subjects: [],   # unchecked — every path still finalizes
    )
    monkeypatch.setattr(
        "pipeline.char_bible.mint_reference",
        lambda description, name, style_fragment, story_id, char_id, n=1: (
            f"{story_id}/ref-{char_id}-{n}.png",
            RefVerdict(differences_observed="none", matches_description=True, attributes_present=["dog"]),
            2,
        ),
    )
    monkeypatch.setattr("pipeline.graph.reveal", lambda state: {})   # no interrupt in stub runs
    monkeypatch.setattr("pipeline.input_gate.classify_text_primary", lambda text: (True, []))
    monkeypatch.setattr("pipeline.input_gate.classify_text_backstop", lambda text: (True, []))
    monkeypatch.setattr("pipeline.input_gate.redact_pii", lambda text: text)
    monkeypatch.setattr("pipeline.char_ref_mod.classify_image_primary", lambda url: True)
    monkeypatch.setattr("pipeline.char_ref_mod.classify_image_backstop", lambda url: True)
    monkeypatch.setattr("pipeline.char_ref_mod.get_signed_url", lambda path: f"https://signed/{path}")
    monkeypatch.setattr("pipeline.output_mod.classify_image_primary", lambda url: True)
    monkeypatch.setattr("pipeline.output_mod.classify_image_backstop", lambda url: True)
    monkeypatch.setattr("pipeline.output_mod.get_signed_url", lambda path: f"https://signed/{path}")


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
    assert character.canonical_ref_image == "test-job-4/ref-c0-1.png"
    assert character.ref_verdict.matches_description is True
    assert character.ref_moderation_status == "passed"   # char_ref_mod sets this
    assert result["cost"].image_count == 3           # 2 from mint_reference + 1 from generate_scene


def test_two_scene_run_loops_once_per_scene_and_reaches_compose(monkeypatch):
    """The ADR-024 loop-termination test, and the reason route_next_scene is worth testing.

    Two scenes must produce two generate_scene/consistency_check pairs, both finalized, exactly
    two attempts total, and a run that terminates at compose rather than spinning to
    recursion_limit.

    Since 2026-08-13 this is also where the moderation granularity is visible: `output_mod` appears
    once per scene, right after that scene finalizes, instead of once at the end. That ordering IS
    the fix for prod job 4f7698d5 — the gate can now fail on the first bad image rather than after
    every image in the book has been paid for.
    """
    _mock_call_points(monkeypatch)
    monkeypatch.setattr(
        "pipeline.segment.segment_scenes",
        lambda units, chars, timeline, locs=None: SceneSegmentation(scenes=[
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
        "char_ref_mod", "reveal",
        "generate_scene", "consistency_check", "output_mod",
        "generate_scene", "consistency_check", "output_mod",
        "compose",
    ]
    assert [s.final_image_ref for s in result["scenes"]] == ["stub/s0-1.png", "stub/s1-1.png"]
    assert sum(len(s.attempts) for s in result["scenes"]) == 2


def _judge_returning(*, same: bool, anatomy: bool = True) -> SceneVerdict:
    return SceneVerdict(
        differences_observed="d",
        same_character=same,
        attributes_present=[],
        style_match=True,
        anatomy_intact=anatomy,
        failure_reasons=[FailureReason.different_face] if not same else [],
    )


def _two_scenes(monkeypatch):
    monkeypatch.setattr(
        "pipeline.segment.segment_scenes",
        lambda units, chars, timeline, locs=None: SceneSegmentation(scenes=[
            ExtractedScene(start=0, end=0, characters_present=[]),
            ExtractedScene(start=1, end=len(units) - 1, characters_present=[]),
        ]),
    )


def test_a_failing_scene_retries_once_then_passes_and_the_run_reaches_compose(monkeypatch):
    """Spec §6: three attempts total, both scenes finalized, cost.regen_count == 1."""
    _mock_call_points(monkeypatch)
    _two_scenes(monkeypatch)

    # Keyed on the PATH, not a call counter: this test streams once and invokes once, so a
    # counter would carry across both runs and the second would never see a failure.
    monkeypatch.setattr(
        "pipeline.consistency_check.judge_attempt",
        lambda image_path, subjects: [_judge_returning(same=not image_path.endswith("s0-1.png"))],
    )
    app_graph = build_graph()

    ran = [
        next(iter(chunk))
        for chunk in app_graph.stream(
            _initial_state("test-job-retry"),
            config={"configurable": {"thread_id": "test-job-retry"}},
            stream_mode="updates",
        )
    ]
    result = app_graph.invoke(
        _initial_state("test-job-retry-2"),
        config={"configurable": {"thread_id": "test-job-retry-2"}},
    )

    assert ran == [
        "input_gate", "analyze", "segment", "char_bible",
        "char_ref_mod", "reveal",
        "generate_scene", "consistency_check", "regenerate", "consistency_check", "output_mod",
        "generate_scene", "consistency_check", "output_mod",
        "compose",
    ]
    assert sum(len(s.attempts) for s in result["scenes"]) == 3
    assert all(s.final_image_ref is not None for s in result["scenes"])
    assert result["scenes"][0].final_image_ref == "stub/s0-2.png"   # attempt 2 won on its own score
    assert result["cost"].regen_count == 1


def test_a_book_whose_every_judge_call_fails_still_reaches_compose(monkeypatch):
    """The ADR-010 best-of termination test: four attempts, both scenes finalized, never a
    broken page and never an infinite loop. `len(attempts) >= 2` is what bounds it."""
    _mock_call_points(monkeypatch)
    _two_scenes(monkeypatch)
    monkeypatch.setattr(
        "pipeline.consistency_check.judge_attempt",
        lambda image_path, subjects: [_judge_returning(same=False)],
    )
    app_graph = build_graph()

    result = app_graph.invoke(
        _initial_state("test-job-allfail"),
        config={"configurable": {"thread_id": "test-job-allfail"}},
    )

    assert sum(len(s.attempts) for s in result["scenes"]) == 4
    assert all(s.final_image_ref is not None for s in result["scenes"])
    assert all(a.passed is False for s in result["scenes"] for a in s.attempts)
    assert result["cost"].regen_count == 2
    # Tie on every ranking term → attempt 2, the `reversed` behaviour, end to end.
    assert [s.final_image_ref for s in result["scenes"]] == ["stub/s0-2.png", "stub/s1-2.png"]


def test_route_next_scene_routes_to_output_mod_when_all_scenes_have_final_image_ref():
    """Spec §3: route_next_scene goes to output_mod (not compose) when the scene loop is done."""
    from pipeline.graph import route_next_scene
    from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, ModerationResult, Scene, StoryMemory

    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A story.", redacted_text="A story.", moderation=ModerationResult(passed=True)),
        scenes=[
            Scene(scene_id="s0", text_excerpt="text", final_image_ref="job-1/s0-1.png"),
            Scene(scene_id="s1", text_excerpt="text", final_image_ref="job-1/s1-1.png"),
        ],
    )
    assert route_next_scene(state) == "output_mod"


def test_route_next_scene_routes_to_generate_scene_when_scenes_unfinished():
    """route_next_scene still routes to generate_scene while the loop is in progress."""
    from pipeline.graph import route_next_scene
    from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, ModerationResult, Scene, StoryMemory

    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A story.", redacted_text="A story.", moderation=ModerationResult(passed=True)),
        scenes=[Scene(scene_id="s0", text_excerpt="text", final_image_ref=None)],
    )
    assert route_next_scene(state) == "generate_scene"


def test_graph_has_char_ref_mod_and_output_mod_nodes():
    """Task 6 integration: both new nodes are registered in the compiled graph."""
    from pipeline.graph import build_graph
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert "char_ref_mod" in node_names
    assert "output_mod" in node_names


def test_route_reveal_returns_try_again_under_the_cap():
    from pipeline.graph import route_reveal
    from contracts.story_memory import Cost, ReferenceRetry

    state = _initial_state("job-1")
    state.reference_retry = ReferenceRetry(char_id="c0", attribute="orange sock")
    state.cost = Cost(ref_retry_count=2)
    assert route_reveal(state) == "try_again"


def test_route_reveal_returns_confirm_at_the_cap():
    """The trust boundary, pinned: a resume payload is client-supplied, so the cap is enforced
    here, not only in a future UI (spec §3)."""
    from pipeline.graph import route_reveal
    from contracts.story_memory import Cost, ReferenceRetry, Input, ModerationResult, Scene

    state = _initial_state("job-1")
    state.reference_retry = ReferenceRetry(char_id="c0", attribute="orange sock")
    state.cost = Cost(ref_retry_count=3)
    state.input = Input(raw_text="x", redacted_text="x", moderation=ModerationResult(passed=True))
    state.scenes = [Scene(scene_id="s0", text_excerpt="x", final_image_ref=None)]
    assert route_reveal(state) == "generate_scene"


def test_route_reveal_with_no_reference_retry_defers_to_route_next_scene():
    from pipeline.graph import route_reveal
    from contracts.story_memory import Input, ModerationResult, Scene

    state = _initial_state("job-1")
    state.input = Input(raw_text="x", redacted_text="x", moderation=ModerationResult(passed=True))
    state.scenes = [Scene(scene_id="s0", text_excerpt="x", final_image_ref="job-1/s0-1.png")]
    assert route_reveal(state) == "output_mod"


def test_moderation_router_with_scenes_present_routes_to_reveal():
    from pipeline.graph import moderation_router
    from contracts.story_memory import Input, ModerationResult, Scene

    state = _initial_state("job-1")
    state.input = Input(raw_text="x", redacted_text="x", moderation=ModerationResult(passed=True))
    state.scenes = [Scene(scene_id="s0", text_excerpt="x")]
    assert moderation_router(state) == "reveal"


def test_graph_has_a_reveal_node():
    from pipeline.graph import build_graph
    graph = build_graph()
    assert "reveal" in graph.get_graph().nodes.keys()


def test_moderation_router_raises_ref_flagged_not_content_flagged_for_flagged_character():
    """Pins the rename: a flagged canonical reference is machine error, not the child's text (spec §4.2)."""
    import pytest
    from pipeline.graph import moderation_router
    from pipeline.char_ref_mod import MAX_MOD_REDRAWS
    from contracts.story_memory import (
        CURRENT_SCHEMA_VERSION, Character, Cost, Input, ModerationResult, StoryMemory,
    )

    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x", moderation=ModerationResult(passed=True)),
        cost=Cost(ref_mod_retry_count=MAX_MOD_REDRAWS),
    )
    state.characters = [
        Character(char_id="c0", name="the dog", ref_moderation_status="flagged")
    ]
    with pytest.raises(RuntimeError) as exc_info:
        moderation_router(state)
    assert str(exc_info.value) == "ref_flagged"


def _flagged_router_state(mod_retries: int, scenes: bool = True, input_passed: bool = True):
    from contracts.story_memory import (
        CURRENT_SCHEMA_VERSION, Character, Cost, Input, ModerationResult, Scene, StoryMemory,
    )
    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="x", redacted_text="x",
                    moderation=ModerationResult(passed=input_passed,
                                                categories=[] if input_passed else ["S1"])),
        characters=[Character(char_id="c0", name="the dog", ref_moderation_status="flagged")],
        cost=Cost(ref_mod_retry_count=mod_retries),
    )
    if scenes:
        state.scenes = [Scene(scene_id="s0", text_excerpt="x")]
    return state


def test_moderation_router_routes_a_flag_back_to_char_bible_while_budget_remains():
    """§6 test 6 / §4.2. The whole change: a flag with budget left costs one redraw, not the book.
    The label is a real node name, which is what makes the missing path_map at graph.py:112 fine."""
    from pipeline.graph import moderation_router

    assert moderation_router(_flagged_router_state(mod_retries=0)) == "char_bible"


def test_moderation_router_raises_once_the_redraw_budget_is_spent():
    """§6 test 7. MAX_MOD_REDRAWS = 1, so the second flag is terminal — two independent draws
    flagging is evidence, not a coin flip (spec §8 q4)."""
    import pytest
    from pipeline.char_ref_mod import MAX_MOD_REDRAWS
    from pipeline.graph import moderation_router

    with pytest.raises(RuntimeError) as exc_info:
        moderation_router(_flagged_router_state(mod_retries=MAX_MOD_REDRAWS))
    assert str(exc_info.value) == "ref_flagged"


def test_an_input_text_flag_still_wins_over_a_reference_flag():
    """§6 test 10 / CC-1 ordering. The new branch sits AFTER the input.moderation block, so a
    book whose text failed dies as content_flagged — the child's own text, not a machine
    error — even with a flagged character and budget to spare."""
    import pytest
    from pipeline.graph import moderation_router

    with pytest.raises(RuntimeError) as exc_info:
        moderation_router(_flagged_router_state(mod_retries=0, input_passed=False))
    assert str(exc_info.value) == "content_flagged"


def test_moderation_router_still_returns_reveal_when_every_character_passed():
    """§6 test 8: the unchanged happy path, re-pinned because the new branch sits above it."""
    from contracts.story_memory import Character, Input, ModerationResult, Scene
    from pipeline.graph import moderation_router

    state = _initial_state("job-1")
    state.input = Input(raw_text="x", redacted_text="x", moderation=ModerationResult(passed=True))
    state.characters = [Character(char_id="c0", name="the dog", ref_moderation_status="passed")]
    state.scenes = [Scene(scene_id="s0", text_excerpt="x")]
    assert moderation_router(state) == "reveal"


def test_moderation_router_still_returns_analyze_on_the_shared_input_gate_edge():
    """§6 test 9. One function serves both edges; after input_gate there are no characters, so
    the new branch must be unreachable from there."""
    from contracts.story_memory import Input, ModerationResult
    from pipeline.graph import moderation_router

    state = _initial_state("job-1")
    state.input = Input(raw_text="x", redacted_text="x", moderation=ModerationResult(passed=True))
    assert state.characters == []
    assert moderation_router(state) == "analyze"


def test_a_run_that_taps_once_visits_char_ref_mod_twice(monkeypatch):
    """Graph-level: the loop-back targets char_bible, so a tap re-enters char_ref_mod before
    reaching a child again (spec §3, CC-1 ordering holds on the retry path)."""
    _mock_call_points(monkeypatch)
    tap_state = {"tapped": False}

    def fake_reveal(state):
        if not tap_state["tapped"]:
            tap_state["tapped"] = True
            from contracts.story_memory import ReferenceRetry
            return {"reference_retry": ReferenceRetry(char_id="c0", attribute="orange sock")}
        return {}

    def fake_char_bible_targeted(state):
        # ponytail: targeted-path stub for graph routing test — real implementation is Task 4
        if state.reference_retry is not None:
            return {
                "characters": [c.model_copy(update={"ref_moderation_status": None}) for c in state.characters],
                "cost": state.cost.model_copy(update={
                    "image_count": state.cost.image_count + 1,
                    "ref_retry_count": state.cost.ref_retry_count + 1,
                }),
                "reference_retry": None,
            }
        from pipeline.char_bible import char_bible as _real
        return _real(state)

    monkeypatch.setattr("pipeline.graph.reveal", fake_reveal)
    monkeypatch.setattr("pipeline.graph.char_bible", fake_char_bible_targeted)
    app_graph = build_graph()

    ran = [
        next(iter(chunk))
        for chunk in app_graph.stream(
            _initial_state("test-job-tap"),
            config={"configurable": {"thread_id": "test-job-tap"}},
            stream_mode="updates",
        )
    ]
    assert ran.count("char_ref_mod") == 2
    assert ran.count("reveal") == 2


def test_a_flagged_reference_is_redrawn_once_and_the_book_reaches_reveal(monkeypatch):
    """§6 test 16. The whole point of the spec, at graph level: flag → redraw → pass → reveal.

    A router-level test cannot substitute for this one. `graph.py:112` registers
    moderation_router with NO path_map, and LangGraph does not validate labels at build time —
    a label that is not a node name is logged as an unknown channel and the graph simply ENDS.
    Only a compiled run proves "char_bible" actually routes.
    """
    _mock_call_points(monkeypatch)
    calls = {"screened": 0}

    def flag_once(state):
        calls["screened"] += 1
        status = "flagged" if calls["screened"] == 1 else "passed"
        return {"characters": [
            c.model_copy(update={
                "ref_moderation_status": status,
                "canonical_ref_image": None if status == "flagged" else c.canonical_ref_image,
            })
            for c in state.characters
        ]}

    monkeypatch.setattr("pipeline.graph.char_ref_mod", flag_once)

    graph = build_graph()
    visited = []
    for chunk in graph.stream(_initial_state("job-1"), {"configurable": {"thread_id": "t-flag"}},
                              stream_mode="updates"):
        visited.extend(chunk.keys())

    assert visited.count("char_bible") == 2
    assert visited.count("char_ref_mod") == 2
    assert "reveal" in visited
    assert visited.index("reveal") > visited.index("char_ref_mod")


def test_a_second_flag_ends_the_book_and_the_graph_does_not_loop_a_third_time(monkeypatch):
    """§6 test 17. MAX_MOD_REDRAWS = 1 is a real cap, not a suggestion. If this hangs or the
    counts climb past 2, the counter is not being persisted across the loop — check that
    char_bible returns `cost` on the redraw pass."""
    import pytest
    _mock_call_points(monkeypatch)
    calls = {"screened": 0}

    def always_flag(state):
        calls["screened"] += 1
        return {"characters": [
            c.model_copy(update={"ref_moderation_status": "flagged", "canonical_ref_image": None})
            for c in state.characters
        ]}

    monkeypatch.setattr("pipeline.graph.char_ref_mod", always_flag)

    graph = build_graph()
    with pytest.raises(RuntimeError) as exc_info:
        list(graph.stream(_initial_state("job-2"), {"configurable": {"thread_id": "t-flag2"}},
                          stream_mode="updates"))

    assert str(exc_info.value) == "ref_flagged"
    assert calls["screened"] == 2      # initial screen + one redraw screen, never a third
