"""The supervisor-side failure report (prod job d83721d9, 2026-08-11).

RQ runs `execute_failure_callback` in exactly two places — inside `perform_job`
(`rq/worker/base.py:1585`, i.e. the work horse) and in `StartedJobRegistry.cleanup` for jobs that
have already expired. Neither fires when `monitor_work_horse` reaps a SIGKILLed horse, so nothing
updated the `jobs` row and the child's screen polled "Still going!" forever.
"""
import logging
from unittest.mock import MagicMock, patch

from rq import Worker

from worker.run_worker import _ReportingWorker, _report_failed, main

KILLED = "Work-horse terminated unexpectedly; waitpid returned None; "


def _fake_job(job_id: str = "job-1") -> MagicMock:
    return MagicMock(args=[job_id], id="rq-1")


def _update(fake: MagicMock) -> MagicMock:
    return fake.table.return_value.update


def test_killed_work_horse_marks_the_row_failed():
    fake = MagicMock()
    with patch("worker.run_worker.get_supabase_client", return_value=fake):
        _report_failed(_fake_job(), KILLED)

    fake.table.assert_called_once_with("jobs")
    payload = _update(fake).call_args.args[0]
    assert payload["status"] == "failed"
    # ADR-025 D5's machine bucket. Only `moderation_router` may blame the child (issue #27).
    assert payload["failure_reason"] == "machine"
    assert "Work-horse terminated" in payload["error"]
    _update(fake).return_value.in_.return_value.eq.return_value.execute.assert_called_once()


def test_it_only_writes_rows_that_are_still_in_flight():
    """`run_job`'s own `except` writes a precise error when the horse lives long enough to raise.
    This path must never overwrite that, nor a `complete` row, nor an `awaiting_confirm` pause."""
    fake = MagicMock()
    with patch("worker.run_worker.get_supabase_client", return_value=fake):
        _report_failed(_fake_job(), KILLED)

    _update(fake).return_value.in_.assert_called_once_with("status", ["queued", "running"])
    _update(fake).return_value.in_.return_value.eq.assert_called_once_with("id", "job-1")


def test_a_job_with_no_args_is_skipped_rather_than_guessed_at():
    fake = MagicMock()
    with patch("worker.run_worker.get_supabase_client", return_value=fake):
        _report_failed(MagicMock(args=[], id="rq-1"), KILLED)
    fake.table.assert_not_called()


def test_a_reporting_failure_never_takes_down_the_worker(caplog):
    """This runs in the parent process. Raising here would kill the worker that is supposed to
    pick up the next book — strictly worse than the stuck row it exists to prevent."""
    with patch("worker.run_worker.get_supabase_client", side_effect=RuntimeError("supabase down")):
        with caplog.at_level(logging.ERROR):
            _report_failed(_fake_job(), KILLED)   # must not raise
    assert "supabase down" in caplog.text


def test_handle_job_failure_still_runs_rqs_own_bookkeeping():
    """Registry cleanup, failed-job accounting and status are all RQ's — we only add a row write."""
    job = _fake_job()
    worker = MagicMock(spec=_ReportingWorker)
    with patch.object(Worker, "handle_job_failure") as super_call, \
         patch("worker.run_worker._report_failed") as report:
        _ReportingWorker.handle_job_failure(worker, job, "queue", None, KILLED)

    super_call.assert_called_once()
    report.assert_called_once_with(job, KILLED)


def test_main_installs_the_reporting_worker_off_win32():
    with patch("worker.run_worker.sys.platform", "linux"), \
         patch("worker.run_worker.Redis"), patch("worker.run_worker.Queue"), \
         patch("worker.run_worker._ReportingWorker") as worker_class:
        main()

    worker_class.assert_called_once()
    worker_class.return_value.work.assert_called_once()
