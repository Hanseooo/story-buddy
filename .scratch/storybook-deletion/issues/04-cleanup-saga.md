# 04 — Ordered idempotent cleanup task

**Source spec:** `docs/specs/storybook-deletion.md` §5, §7, §9.19–26
**Implementation plan:** required — write `docs/specs/plans/storybook-deletion-04-cleanup-saga.md` first, then a lighter agent implements it.
**Blocked by:** 01
**Status:** ready-for-agent

## What to build

A background task that, given a job ID, removes every StoryBuddy-controlled copy of that storybook in
a fixed order and can be re-run any number of times, from any point of partial failure, without harm.

Ordered steps, on the existing `storybook` RQ queue, with no new dependency, queue or store registry:

1. **Storage** — recursively list every object beneath the literal `{job_id}/` folder in the private
   `storybook-images` bucket, paginating until exhausted; remove file paths in SDK-supported batches.
   Folder entries are traversed, never passed to `remove`. Inventory is **never** derived from
   `jobs.pages`. After each batch, continue listing from the folder rather than trusting a stale
   offset over a shrinking list.
2. **LangGraph checkpoints** — existing direct Postgres connection, `PostgresSaver.delete_thread(job_id)`.
3. **Langfuse** — delete trace ID `job_id` with hyphens stripped. Missing trace = success; any other
   API failure stops the saga.
4. **Postgres job row** — last, constrained by `id = job_id AND status = 'deleting'`.

Guards: the task may act only on a row currently in `deleting`; a missing row is idempotent success;
any other status is a no-op failure that removes no child data. A zero-row final delete counts as
success only after a re-read confirms absence — a still-present row fails the task. Any
non-idempotent error stops the task and raises so RQ records the failure; the tombstone remains and a
repeated DELETE can restart the sequence.

Logs carry job ID, step, outcome and remaining object count where known — never story text, prompts,
captions, signed URLs or object bytes. Cleanup metrics distinguish success and failure by store.

Verify against the installed SDKs before writing adapters: Storage list/remove response shapes and
batch limit, `PostgresSaver.delete_thread` behavior, Langfuse missing-trace error shape.

## Acceptance criteria

- [ ] Refuses a present row whose status is not `deleting`; a missing row is a no-op success.
- [ ] Nested/paginated inventory deletes every `{job_id}/` file, including refs and superseded attempts, and never touches a sibling prefix.
- [ ] Removing from a shrinking folder does not skip a page; supported batch sizes are honored.
- [ ] Checkpoint deletion receives exactly `job_id`; Langfuse deletion receives the hyphenless ID.
- [ ] Missing resources are success; a failure at each step leaves the row and prevents later steps.
- [ ] Row deletion occurs last and is constrained by both ID and `status='deleting'`.
- [ ] Concurrent duplicate cleanups treat a final zero-row delete as success only after confirming absence.
- [ ] Re-running after each partial-failure point completes without error or duplicate side effects.
- [ ] `research_pairs`, `annotations` and `private_assets/research/` are untouched.
- [ ] All Storage/checkpointer/Langfuse/Supabase calls mocked; `uv run ruff check . && uv run pytest` green, output shown.
