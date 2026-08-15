import logging
import sys

from redis import Redis
from rq import Queue, SimpleWorker, Worker
from rq.timeouts import JobTimeoutException, UnixSignalDeathPenalty

from app.config import settings
from app.db import get_supabase_client

log = logging.getLogger(__name__)


class HardJobTimeout(BaseException):
    """The job deadline, as an exception this pipeline cannot swallow by accident (issue #33).

    RQ's own `JobTimeoutException` is an ordinary `Exception`, and this pipeline is built out of
    handlers whose job is to catch `Exception` and KEEP GOING — correctly so:

      - `consistency_check.py:87` and `char_bible.py:225` return "unchecked" rather than kill a
        paid-for artifact. That ADR-025 asymmetry is deliberate; do not fix it there.
      - `generate_scene.py:48` swallows around a storage probe and then falls through to a PAID
        `edit_image`/`text_to_image` call.
      - `openai/_base_client.py:1059` treats it as a transient upstream failure and retries.

    So the deadline has to be something none of them can see. Deriving from `BaseException` is the
    only mechanism that works without auditing — and re-auditing forever — every `except Exception`
    in the graph.

    Prod job d83721d9 (2026-08-11) is the case: SIGALRM landed at 18:35:50 exactly on the 900s
    deadline, the OpenAI SDK caught it and retried 2s later, and the job ran 77 more seconds and
    drew TWO more paid fal images before the horse was SIGKILLed at 18:37:07.

    Not caught in `run_job` — see `_report_failed`. `perform_job`'s bare `except:`
    (`rq/worker/base.py:1576`) catches this, so RQ's registry bookkeeping and the row write below
    both still run; only the precise one-line message is traded for the full traceback.
    """


class _HardDeathPenalty(UnixSignalDeathPenalty):
    """`rq/worker/base.py:1548` calls `death_penalty_class(timeout, JobTimeoutException, job_id=...)`
    — it hardcodes the exception positionally. Overriding *that* argument is the whole mechanism.

    Only that one. RQ arms this same class for a second, unrelated purpose:
    `monitor_work_horse` (`rq/worker/worker_classes.py:87`) wakes the PARENT every
    `job_monitoring_interval` (30s) with `HorseMonitorTimeoutException` and catches only that on
    line 90. Prod job 4e1de7c3 (2026-08-12) is the case: substituting there too raised a
    `BaseException` nothing in the supervisor loop catches, so the worker quit 30 seconds into
    the job — every job — while the horse was still drawing.
    """

    def __init__(self, timeout, exception=JobTimeoutException, **kwargs):
        if exception is JobTimeoutException:
            exception = HardJobTimeout
        super().__init__(timeout, exception, **kwargs)


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
            {"status": "failed", "error": exc_string, "failure_reason": "worker_stopped"}
        ).in_("status", ["queued", "running"]).eq("id", job.args[0]).execute()
    except Exception:
        # Raising here would kill the parent that is meant to pick up the next book — strictly
        # worse than the stuck row this exists to prevent.
        log.exception("run_worker: could not mark job %s failed after horse death", job.args[0])


class _ReportingWorker(Worker):
    """The forking worker, plus the row write RQ gives no callback for.

    `SimpleWorker` (win32/dev) deliberately does not get this: it runs jobs in-process, so there is
    no horse to orphan and `run_job`'s own `except` always runs. It keeps RQ's ordinary deadline
    too — `TimerDeathPenalty` raises into a thread that has no fal spend behind it, and prod is
    where the money burns.
    """

    # ponytail: the deadline is the only bound that survives a stalled provider. `_bounded`
    # (providers.py:71) caps a single LLM call at 120s but nothing caps `_fal()` or PostgresSaver.
    death_penalty_class = _HardDeathPenalty

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
