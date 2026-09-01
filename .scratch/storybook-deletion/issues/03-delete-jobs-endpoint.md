# 03 — `DELETE /jobs/{job_id}` endpoint

**Source spec:** `docs/specs/storybook-deletion.md` §4.1, §3 lifecycle table, §9.7–13
**Implementation plan:** required — write `docs/specs/plans/storybook-deletion-03-endpoint.md` first, then a lighter agent implements it.
**Blocked by:** 01, 02
**Status:** ready-for-agent

## What to build

An authenticated owner can ask the backend to delete one of their own quiescent storybooks and get an
immediate accepted-for-deletion answer, while every other caller and every in-flight book is refused
without disclosing anything.

Uses the existing bearer-token dependency and the server-side service-role client; the lookup is
scoped to `id = job_id AND profile_id = auth user id`.

| Situation | Response |
|---|---|
| eligible status (`complete`/`failed`/`awaiting_confirm`) + non-null marker | `202 {"status":"deleting"}`, one CAS win, one cleanup enqueued |
| already `deleting` | same `202`; may enqueue the same cleanup again |
| `queued`, `running`, or null marker | `409`, nothing enqueued |
| missing **or** foreign row | `404` (identical — no cross-account disclosure) |
| enqueue raises or is uncertain | `503`, row left in `deleting`, **no rollback** — the task may already exist and retrying DELETE is safe |

The CAS preserves the `worker_finished_at` proof. CORS adds `DELETE`. No new Next.js route or server
action. Endpoint metrics distinguish accepted, ineligible, unauthorized/not-found, enqueue-failed and
repeated requests.

## Acceptance criteria

- [ ] Missing and foreign IDs return `404`; neither updates nor enqueues.
- [ ] `queued`, `running`, or a null finish marker returns `409` and enqueues nothing.
- [ ] Each eligible status with a marker wins one CAS, returns `202`, and enqueues one cleanup.
- [ ] A second DELETE on `deleting` returns `202` and may enqueue the same job again.
- [ ] Confirm/delete races produce exactly one winning transition and one enqueue.
- [ ] Enqueue failure returns `503`, leaves the row `deleting`, and a retry can enqueue.
- [ ] CORS preflight permits DELETE only from the configured frontend origin.
- [ ] Queue and Supabase calls are mocked; `uv run ruff check . && uv run pytest` green, output shown.
