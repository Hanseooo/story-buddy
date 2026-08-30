# 02 — Worker finish-marker lifecycle (quiescence barrier)

**Source spec:** `docs/specs/storybook-deletion.md` §3 invariants 1–4, §9.15–18
**Implementation plan:** required — write `docs/specs/plans/storybook-deletion-02-finish-marker.md` first, then a lighter agent implements it.
**Blocked by:** 01
**Status:** ready-for-agent

## What to build

A durable proof that no worker can still write to a job. `worker_finished_at` is null while a worker
may produce data, and non-null only after that worker has stopped touching the row, checkpoints,
Storage and Langfuse — including when the RQ work horse dies hard.

- Fresh generation and resume entrypoints clear the marker before setting up or running graph work.
- The marker write is the worker's **last** write on every exit: normal completion, pause, raised
  failure, and the RQ hard-failure path (which sets it only after the work horse is dead).
- The confirm compare-and-set changes `awaiting_confirm → queued` and clears the marker in the same
  update. If confirm enqueue fails, rollback restores `awaiting_confirm` **and** a non-null marker —
  no worker started, so the row is quiescent again.
- A marker write failure fails closed: the book stays non-deletable until repaired. Quiescence is
  never guessed from elapsed time.

No deletion behavior ships here. This ticket only makes quiescence provable.

## Acceptance criteria

- [ ] Fresh and resume entrypoints clear `worker_finished_at` before setting or running graph work.
- [ ] Complete, pause, caught failure and hard work-horse failure all set it only after final trace work.
- [ ] Confirm clears it in the CAS; confirm enqueue rollback restores a non-null marker.
- [ ] A finish-marker write failure never makes the row deletable.
- [ ] `uv run ruff check . && uv run pytest` green from `backend/`, output shown.
