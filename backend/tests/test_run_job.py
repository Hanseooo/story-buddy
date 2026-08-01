from unittest.mock import MagicMock, patch

from app.config import RECURSION_LIMIT, STYLE_PRESETS
from contracts.story_memory import CURRENT_SCHEMA_VERSION, Scene
from worker.run_job import run_storybook_job


def _fake_supabase(style_preset_id: str | None = None) -> MagicMock:
    fake = MagicMock()
    select_chain = fake.table.return_value.select.return_value.eq.return_value.single.return_value
    select_chain.execute.return_value.data = {
        "input_text": "A dog runs in a field.",
        "style_preset_id": style_preset_id,
    }
    return fake


def _fake_graph() -> MagicMock:
    graph = MagicMock()
    # invoke() returns a dict whose values are model instances (verified against langgraph 1.2.8).
    graph.invoke.return_value = {
        "scenes": [
            Scene(
                scene_id="s0",
                text_excerpt="A dog runs in a field.",
                caption="stub caption",
                final_image_ref="job-1/scene-1.png",
            )
        ]
    }
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
    assert final_update["caption"] == "stub caption"
    assert final_update["image_path"] == "job-1/scene-1.png"


def test_run_storybook_job_constructs_story_memory_with_dev_provenance():
    """ADR-023 amendment 2026-07-22b: the worker is the supplier. story_id = job_id
    (one job = one story); classroom/profile are Phase-1 sentinels swapped at this one site."""
    fake_supabase = _fake_supabase()
    fake_checkpointer_cm = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = MagicMock()
    fake_graph = _fake_graph()

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    initial_state = fake_graph.invoke.call_args.args[0]
    assert initial_state.schema_version == CURRENT_SCHEMA_VERSION
    assert initial_state.story_id == "job-1"
    assert initial_state.classroom_id == "dev-classroom"
    assert initial_state.profile_id == "dev-profile"
    assert initial_state.input.raw_text == "A dog runs in a field."


def test_run_storybook_job_tolerates_a_run_that_produced_no_scenes():
    """A graph that errored past the DB write must not crash the worker with IndexError —
    the row gets nulls and the failure is visible, not a stack trace in the queue."""
    fake_supabase = _fake_supabase()
    fake_checkpointer_cm = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = MagicMock()
    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {"scenes": []}

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-3")

    final_update = fake_supabase.table.return_value.update.call_args_list[-1][0][0]
    assert final_update["caption"] is None
    assert final_update["image_path"] is None


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

    state = fake_graph.invoke.call_args.args[0]
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

    state = fake_graph.invoke.call_args.args[0]
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

    config = fake_graph.invoke.call_args.kwargs["config"]
    assert config["recursion_limit"] == RECURSION_LIMIT
    assert config["configurable"]["thread_id"] == "job-1"
