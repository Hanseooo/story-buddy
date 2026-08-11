import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from langgraph.types import Command

from app.config import RECURSION_LIMIT, STYLE_PRESETS
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Scene
from worker.run_job import _run_with_progress, _stage_string, resume_storybook_job, run_storybook_job


@pytest.fixture(autouse=True)
def mock_langfuse_handler():
    with patch("worker.run_job.CallbackHandler") as mock, patch("worker.run_job.Langfuse"):
        yield mock


def _fake_supabase(style_preset_id: str | None = None, truncated: bool = False) -> MagicMock:
    fake = MagicMock()
    select_chain = fake.table.return_value.select.return_value.eq.return_value.single.return_value
    select_chain.execute.return_value.data = {
        "input_text": "A dog runs in a field.",
        "style_preset_id": style_preset_id,
        "truncated": truncated,
        "classroom_id": "00000000-0000-0000-0000-000000000001",
        "profile_id": "00000000-0000-0000-0000-000000000002",
    }
    return fake


def _fake_graph() -> MagicMock:
    graph = MagicMock()
    final_state = {
        "scenes": [
            Scene(
                scene_id="s0",
                text_excerpt="A dog runs in a field.",
                caption="stub caption",
                final_image_ref="job-1/scene-1.png",
            )
        ]
    }
    graph.stream.return_value = iter([
        ("updates", {"compose": {}}),
        ("values", final_state),
    ])
    return graph


def test_run_storybook_job_updates_row_on_success():
    fake_supabase = _fake_supabase()
    fake_checkpointer_cm = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    update_calls = fake_supabase.table.return_value.update.call_args_list
    final_update = update_calls[-1][0][0]
    assert final_update["status"] == "complete"
    assert final_update["pages"] == [
        {"scene_id": "s0", "caption": "stub caption", "image_path": "job-1/scene-1.png"}
    ]
    assert final_update["image_count"] == 0
    assert final_update["regen_count"] == 0
    assert final_update["ref_retry_count"] == 0
    assert final_update["scenes_total"] == 1
    assert final_update["scenes_passed"] == 0
    assert final_update["scenes_failed"] == 0
    assert final_update["scenes_unchecked"] == 1
    assert final_update["usd_estimate"] == 0.0


def test_run_storybook_job_writes_trace_url_before_streaming():
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-trace-1")

    update_calls = fake_supabase.table.return_value.update.call_args_list
    # The second update call should be writing langfuse_trace_url (first is running)
    trace_update = update_calls[1][0][0]
    assert "langfuse_trace_url" in trace_update
    assert "jobtrace1" in trace_update["langfuse_trace_url"]

    # Verify callbacks were passed to stream config
    config = fake_graph.stream.call_args.args[1]
    assert "callbacks" in config
    assert len(config["callbacks"]) == 1


def test_run_storybook_job_writes_pages_in_scene_order():
    """spec §7: pages has one entry per scene, in result["scenes"] order — not sorted, not reversed."""
    fake_supabase = _fake_supabase()
    fake_checkpointer_cm = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = MagicMock()
    fake_graph = MagicMock()
    final_state = {
        "scenes": [
            Scene(scene_id="s0", text_excerpt="x", caption="first", final_image_ref="job-1/s0-1.png"),
            Scene(scene_id="s1", text_excerpt="y", caption="second", final_image_ref="job-1/s1-1.png"),
        ]
    }
    fake_graph.stream.return_value = iter([
        ("updates", {"compose": {}}),
        ("values", final_state),
    ])

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    final_update = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final_update["pages"] == [
        {"scene_id": "s0", "caption": "first", "image_path": "job-1/s0-1.png"},
        {"scene_id": "s1", "caption": "second", "image_path": "job-1/s1-1.png"},
    ]


def test_run_storybook_job_constructs_story_memory_from_job_row():
    """story_id = job_id; classroom_id/profile_id come from the job row (0008 columns)."""
    fake_supabase = _fake_supabase()
    fake_checkpointer_cm = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    initial_state = fake_graph.stream.call_args.args[0]
    assert initial_state.schema_version == CURRENT_SCHEMA_VERSION
    assert initial_state.story_id == "job-1"
    assert initial_state.classroom_id == "00000000-0000-0000-0000-000000000001"
    assert initial_state.profile_id == "00000000-0000-0000-0000-000000000002"
    assert initial_state.input.raw_text == "A dog runs in a field."


def test_run_storybook_job_tolerates_a_run_that_produced_no_scenes():
    """A graph that errored past the DB write must not crash the worker with IndexError —
    the row gets an empty pages array and the failure is visible, not a stack trace in the queue."""
    fake_supabase = _fake_supabase()
    fake_checkpointer_cm = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = MagicMock()
    fake_graph = MagicMock()
    fake_graph.stream.return_value = iter([
        ("updates", {"compose": {}}),
        ("values", {"scenes": []}),
    ])

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-3")

    final_update = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final_update["pages"] == []


def test_run_storybook_job_marks_failed_on_exception():
    fake_supabase = _fake_supabase()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", side_effect=RuntimeError("db down")):
        try:
            run_storybook_job("job-2")
            assert False, "expected RuntimeError to propagate"
        except RuntimeError:
            pass

    update_calls = fake_supabase.table.return_value.update.call_args_list
    failed_update = update_calls[-1][0][0]
    assert failed_update["status"] == "failed"
    assert "db down" in failed_update["error"]
    assert "pages" not in failed_update


# --- style-presets spec: worker resolution (tests 6–7) ---

def test_run_storybook_job_resolves_gouache_style_preset():
    """Given style_preset_id='gouache', StoryMemory.style carries the correct preset and fragment."""
    fake_supabase = _fake_supabase(style_preset_id="gouache")
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    state = fake_graph.stream.call_args.args[0]
    assert state.style.style_preset_id == "gouache"
    assert state.style.prompt_fragment == STYLE_PRESETS["gouache"]


def test_run_storybook_job_defaults_style_to_cel_when_preset_is_null():
    """Given style_preset_id=None in the jobs row, StoryMemory.style defaults to 'cel'."""
    fake_supabase = _fake_supabase(style_preset_id=None)
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    state = fake_graph.stream.call_args.args[0]
    assert state.style.style_preset_id == "cel"
    assert state.style.prompt_fragment == STYLE_PRESETS["cel"]


def test_run_storybook_job_passes_the_recursion_limit_to_invoke():
    """Spec §6 regression: without this, LangGraph's default of 25 super-steps applies and a
    13-scene book dies with GraphRecursionError before it ever reaches compose."""
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    config = fake_graph.stream.call_args.args[1]
    assert config["recursion_limit"] == RECURSION_LIMIT
    assert config["configurable"]["thread_id"] == "job-1"


# --- input-gate-hardening spec: Input.word_count / Input.truncated (§2) ---

def test_run_storybook_job_populates_word_count_and_truncated_from_the_row():
    fake_supabase = _fake_supabase(truncated=True)
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    state = fake_graph.stream.call_args.args[0]
    assert state.input.word_count == 6  # "A dog runs in a field." — six words
    assert state.input.truncated is True


def test_run_storybook_job_defaults_truncated_false_when_not_truncated():
    fake_supabase = _fake_supabase(truncated=False)
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    state = fake_graph.stream.call_args.args[0]
    assert state.input.truncated is False


# --- kid-flow-pause-lifecycle spec: _finish / interrupt / resume (§4.8, §4.10) ---

def _fake_interrupt_graph(payload: dict) -> MagicMock:
    interrupt = SimpleNamespace(value=payload)
    graph = MagicMock()
    graph.stream.return_value = iter([
        ("values", {}),
        ("updates", {"__interrupt__": [interrupt]}),
    ])
    return graph


def test_run_storybook_job_writes_awaiting_confirm_and_reveal_on_interrupt():
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    reveal_payload = {"characters": [{"char_id": "c0", "chips": ["orange sock"]}], "taps_left": 3}
    fake_graph = _fake_interrupt_graph(reveal_payload)

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    final_update = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final_update["status"] == "awaiting_confirm"
    assert final_update["current_stage"] == "reveal"
    assert final_update["reveal"] == reveal_payload
    assert "pages" not in final_update


def test_run_storybook_job_clean_invoke_writes_no_reveal_key():
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    final_update = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert "reveal" not in final_update
    assert final_update["status"] == "complete"


def test_run_storybook_job_raises_and_marks_failed_when_interrupt_has_no_usable_payload():
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    fake_graph = MagicMock()
    fake_graph.stream.return_value = iter([
        ("values", {}),
        ("updates", {"__interrupt__": []}),
    ])

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        try:
            run_storybook_job("job-1")
            assert False, "expected an exception"
        except Exception:
            pass

    final_update = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final_update["status"] == "failed"
    assert "reveal" not in final_update


def test_resume_storybook_job_invokes_with_a_command_and_never_builds_story_memory():
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph), \
         patch("worker.run_job.StoryMemory") as fake_story_memory_cls:
        resume_storybook_job("job-9", {"action": "confirm"})

    fake_story_memory_cls.assert_not_called()
    streamed_arg = fake_graph.stream.call_args.args[0]
    assert isinstance(streamed_arg, Command)
    assert streamed_arg.resume == {"action": "confirm"}
    config = fake_graph.stream.call_args.args[1]
    assert config["configurable"]["thread_id"] == "job-9"
    assert config["recursion_limit"] == RECURSION_LIMIT


def test_resume_storybook_job_sets_status_running_before_invoking():
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        resume_storybook_job("job-9", {"action": "confirm"})

    first_update = fake_supabase.table.return_value.update.call_args_list[0][0][0]
    assert first_update["status"] == "running"


# ── job-failure-reason spec §7 assertions ────────────────────────────────────


def _fake_raising_graph(exc_msg: str) -> MagicMock:
    graph = MagicMock()
    graph.stream.side_effect = RuntimeError(exc_msg)
    return graph


def test_failure_reason_is_child_text_when_content_flagged():
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=_fake_raising_graph("content_flagged")):
        try:
            run_storybook_job("job-x")
        except RuntimeError:
            pass
    final = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final["failure_reason"] == "child_text"


def test_failure_reason_is_machine_for_moderation_error():
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=_fake_raising_graph("moderation_error")):
        try:
            run_storybook_job("job-x")
        except RuntimeError:
            pass
    final = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final["failure_reason"] == "machine"


def test_failure_reason_is_machine_for_ref_flagged():
    # ref_flagged is what moderation_router raises for a flagged canonical reference —
    # something the machine drew, not the child's text (spec §4.2).
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=_fake_raising_graph("ref_flagged")):
        try:
            run_storybook_job("job-x")
        except RuntimeError:
            pass
    final = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final["failure_reason"] == "machine"


def test_failure_reason_is_machine_for_output_moderation_failed():
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=_fake_raising_graph("output_moderation_failed")):
        try:
            run_storybook_job("job-x")
        except RuntimeError:
            pass
    final = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final["failure_reason"] == "machine"


def test_failure_reason_is_machine_for_arbitrary_provider_error():
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=_fake_raising_graph("HTTPError: 503 fal.ai")):
        try:
            run_storybook_job("job-x")
        except RuntimeError:
            pass
    final = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final["failure_reason"] == "machine"


def test_resume_entrypoint_also_writes_failure_reason():
    # Both entrypoints must write failure_reason — spec §7 "Every raise path writes some failure_reason".
    fake_supabase = _fake_supabase()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = MagicMock()
    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_cm), \
         patch("worker.run_job.build_graph", return_value=_fake_raising_graph("content_flagged")):
        try:
            resume_storybook_job("job-x", {"action": "confirm"})
        except RuntimeError:
            pass
    final = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final["failure_reason"] == "child_text"


def test_resume_storybook_job_marks_failed_on_exception_and_writes_no_pages():
    fake_supabase = _fake_supabase()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", side_effect=RuntimeError("db down")):
        try:
            resume_storybook_job("job-9", {"action": "confirm"})
            assert False, "expected RuntimeError to propagate"
        except RuntimeError:
            pass

    failed_update = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert failed_update["status"] == "failed"
    assert "pages" not in failed_update


# ── _stage_string unit tests (spec §7 pure assertions) ───────────────────────


def _scene(final_image_ref=None):
    return SimpleNamespace(final_image_ref=final_image_ref)


def test_stage_string_non_scene_node_returns_node():
    assert _stage_string("analyze", None) == "analyze"
    assert _stage_string("compose", {"scenes": [_scene("p")]}) == "compose"


def test_stage_string_scene_node_before_segment_returns_node():
    # No scenes yet — just return the node name
    assert _stage_string("generate_scene", None) == "generate_scene"
    assert _stage_string("generate_scene", {"scenes": []}) == "generate_scene"


def test_stage_string_scene_node_mid_loop():
    # 2 scenes done, 5 total → k = min(2+1, 5) = 3
    scenes = [_scene("p"), _scene("p"), _scene(None), _scene(None), _scene(None)]
    assert _stage_string("generate_scene", {"scenes": scenes}) == "generate_scene:3/5"


def test_stage_string_scene_node_on_last_scene():
    # All 3 done → k = min(3+1, 3) = 3 (capped, not 4)
    scenes = [_scene("p"), _scene("p"), _scene("p")]
    assert _stage_string("output_mod", {"scenes": scenes}) == "output_mod:3/3"


def test_stage_string_all_scene_node_names_produce_counter():
    scenes = [_scene("p"), _scene(None)]
    for node in ("generate_scene", "consistency_check", "regenerate", "output_mod"):
        result = _stage_string(node, {"scenes": scenes})
        assert result == f"{node}:2/2", f"Expected counter for {node}, got {result}"


# ── _run_with_progress spec §7 assertions ────────────────────────────────────


def _stream_graph_complete(final_state: dict) -> MagicMock:
    """Mock whose .stream() yields a complete-path sequence."""
    graph = MagicMock()
    graph.stream.return_value = iter([
        ("updates", {"analyze": {}}),
        ("values", {"scenes": []}),
        ("updates", {"compose": {}}),
        ("values", final_state),
    ])
    return graph


def _stream_graph_interrupt(interrupt_value: dict) -> MagicMock:
    """Mock whose .stream() yields an interrupt-path sequence."""
    interrupt = SimpleNamespace(value=interrupt_value)
    graph = MagicMock()
    graph.stream.return_value = iter([
        ("values", {}),
        ("updates", {"__interrupt__": [interrupt]}),
    ])
    return graph


def test_run_with_progress_complete_path_returns_same_as_invoke():
    """spec §7: hands _finish a result equal to what invoke() returns on complete path."""
    final_state = {
        "scenes": [
            Scene(scene_id="s0", text_excerpt="x", caption="c", final_image_ref="job-1/s0.png")
        ]
    }
    graph = _stream_graph_complete(final_state)
    fake_sb = MagicMock()

    result = _run_with_progress(fake_sb, "job-1", graph, {}, {"configurable": {"thread_id": "job-1"}})

    # Must equal the final "values" payload — no __interrupt__ key
    assert result == final_state
    assert "__interrupt__" not in result


def test_run_with_progress_interrupt_path_returns_interrupt_dict():
    """spec §7: interrupt path hands _finish {**latest, "__interrupt__": [...]}."""
    reveal_payload = {"characters": [], "taps_left": 3}
    graph = _stream_graph_interrupt(reveal_payload)
    fake_sb = MagicMock()

    result = _run_with_progress(fake_sb, "job-1", graph, {}, {"configurable": {"thread_id": "job-1"}})

    assert "__interrupt__" in result
    assert result["__interrupt__"][0].value == reveal_payload


def test_run_with_progress_only_writes_current_stage():
    """spec §7: progress writes update current_stage only — no status, pages, or reveal."""
    final_state = {"scenes": []}
    graph = _stream_graph_complete(final_state)
    fake_sb = MagicMock()

    _run_with_progress(fake_sb, "job-1", graph, {}, {"configurable": {"thread_id": "job-1"}})

    for call in fake_sb.table.return_value.update.call_args_list:
        payload = call.args[0]
        assert set(payload.keys()) == {"current_stage"}, (
            f"Progress write must only set current_stage, got: {set(payload.keys())}"
        )


def test_run_with_progress_does_not_write_same_stage_twice():
    """spec §7: same stage string is not written twice in a row."""
    graph = MagicMock()
    # Two consecutive "updates" for the same node — only one DB write should fire
    graph.stream.return_value = iter([
        ("updates", {"analyze": {}}),
        ("values", {"scenes": []}),
        ("updates", {"analyze": {}}),   # duplicate node — same stage
        ("values", {"scenes": []}),
    ])
    fake_sb = MagicMock()

    _run_with_progress(fake_sb, "job-1", graph, {}, {"configurable": {"thread_id": "job-1"}})

    update_calls = fake_sb.table.return_value.update.call_args_list
    stages = [c.args[0]["current_stage"] for c in update_calls]
    assert stages == list(dict.fromkeys(stages)), f"Duplicate stage write detected: {stages}"
