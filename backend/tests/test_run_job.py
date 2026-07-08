from unittest.mock import MagicMock, patch

from worker.run_job import run_storybook_job


def test_run_storybook_job_updates_row_on_success():
    fake_supabase = MagicMock()
    select_chain = fake_supabase.table.return_value.select.return_value.eq.return_value.single.return_value
    select_chain.execute.return_value.data = {"input_text": "A dog runs in a field."}

    fake_checkpointer_cm = MagicMock()
    fake_checkpointer = MagicMock()
    fake_checkpointer_cm.__enter__.return_value = fake_checkpointer

    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {
        "caption": "stub caption",
        "image_path": "job-1/scene-1.png",
        "stage": "compose",
    }

    with patch("worker.run_job.get_supabase_client", return_value=fake_supabase), \
         patch("worker.run_job.PostgresSaver.from_conn_string", return_value=fake_checkpointer_cm), \
         patch("worker.run_job.build_graph", return_value=fake_graph):
        run_storybook_job("job-1")

    update_calls = fake_supabase.table.return_value.update.call_args_list
    final_update = update_calls[-1][0][0]
    assert final_update["status"] == "complete"
    assert final_update["caption"] == "stub caption"
    assert final_update["image_path"] == "job-1/scene-1.png"


def test_run_storybook_job_marks_failed_on_exception():
    fake_supabase = MagicMock()
    select_chain = fake_supabase.table.return_value.select.return_value.eq.return_value.single.return_value
    select_chain.execute.return_value.data = {"input_text": "A dog runs in a field."}

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
