import logging
import sys

from redis import Redis
from rq import Queue, SimpleWorker, Worker

from app.config import settings
from app.db import get_supabase_client

log = logging.getLogger(__name__)


def _report_failed(job, exc_string: str) -> None:
    """Write the terminal row for a job whose work horse died without raising.

    `run_job`'s own `except` covers every failure the horse survives long enough to raise. It
    cannot cover a SIGKILL, and RQ has no hook that does: `execute_failure_callback` runs only
    inside `perform_job` (`rq/worker/base.py:1585` — the process that just died) and in
    `StartedJobRegistry.cleanup` for jobs that have already expired, which this one never becomes
    because `handle_job_failure` moves it straight to `FailedJobRegistry`.

    Prod job d83721d9 (2026-08-11) is the case: a judge request stalled 14 minutes, RQ's 900s
    deadline was swallowed by the OpenAI SDK's `except Exception` retry, and the horse was killed
    at 18:37:07. Nothing wrote the row, so it sat at `status='running'` with `failure_reason=NULL`
    — and `frontend/lib/useJob.ts:51` polls that row directly, so the child's screen showed
    "Still going!" with nothing left alive to change it.

    ponytail: covers a dead horse, not a dead container — if the pod itself is OOM-killed this
    parent goes with it. Add an `on_failure=` callback to both `enqueue` sites if that shows up:
    RQ fires those from `StartedJobRegistry.cleanup` once the abandoned job expires.
    """
    if not job.args:
        return
    try:
        # CAS on the in-flight states: `run_job` writes a precise `error` when it can, and this
        # must never overwrite that, a `complete` row, or an `awaiting_confirm` pause.
        get_supabase_client().table("jobs").update(
            {"status": "failed", "error": exc_string, "failure_reason": "machine"}
        ).in_("status", ["queued", "running"]).eq("id", job.args[0]).execute()
    except Exception:
        # Raising here would kill the parent that is meant to pick up the next book — strictly
        # worse than the stuck row this exists to prevent.
        log.exception("run_worker: could not mark job %s failed after horse death", job.args[0])


class _ReportingWorker(Worker):
    """The forking worker, plus the row write RQ gives no callback for.

    `SimpleWorker` (win32/dev) deliberately does not get this: it runs jobs in-process, so there is
    no horse to orphan and `run_job`'s own `except` always runs.
    """

    def handle_job_failure(self, job, queue, started_job_registry=None, exc_string=""):
        super().handle_job_failure(job, queue, started_job_registry, exc_string)
        _report_failed(job, exc_string)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    connection = Redis.from_url(settings.redis_url)
    queue = Queue("storybook", connection=connection)
    worker_class = SimpleWorker if sys.platform == "win32" else _ReportingWorker
    worker = worker_class([queue], connection=connection)
    worker.work()


if __name__ == "__main__":
    main()
