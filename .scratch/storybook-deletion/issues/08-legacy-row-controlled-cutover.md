# 08 — Controlled cutover and legacy-row backfill

**Source spec:** `docs/specs/storybook-deletion.md` §3 "Existing-row rollout", §9.14
**Implementation plan:** required — write `docs/specs/plans/storybook-deletion-08-cutover.md` first, then a lighter agent implements it.
**Blocked by:** 02, 03, 04
**Status:** ready-for-agent

## What to build

Storybooks that already existed before the finish marker shipped become deletable — but only through a
rollout that proves no worker can still be writing to them. An unconditional SQL backfill is
forbidden: a legacy `complete` or `failed` row can still race a worker's final Langfuse publication.

The release sequence, written down as an executable runbook plus the backfill migration it gates:

1. Stop new story submissions and drain the `storybook` RQ queue.
2. Stop every old worker; verify the queue has no queued/started jobs and Postgres has no
   `queued`/`running` rows.
3. Apply the migration and backfill `worker_finished_at` for existing `complete`, `failed` and
   `awaiting_confirm` rows only, while no worker process can write.
4. Deploy the marker-aware web/worker code, then resume submissions.

If any quiescence check fails: do not backfill, do not expose deletion. Null-marker legacy rows stay
safely non-deletable (`409`) until a controlled cutover succeeds.

## Acceptance criteria

- [ ] A runbook exists with the four steps, their verification commands, and the abort condition.
- [ ] The backfill touches only existing `complete`, `failed` and `awaiting_confirm` rows.
- [ ] Deterministic test: existing terminal rows receive a marker only under the stopped-worker/drained-queue rollout; a null legacy marker remains non-deletable.
- [ ] `uv run ruff check . && uv run pytest` green from `backend/`, output shown.

## Notes

Rehearsal against a real non-production project is ticket 09 step 1 — this ticket writes the sequence
and the migration, it does not prove remote behavior.
