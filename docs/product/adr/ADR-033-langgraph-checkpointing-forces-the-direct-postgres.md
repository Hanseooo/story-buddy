# ADR-033 — LangGraph checkpointing forces the direct Postgres connection (5432), not Supabase's transaction pooler (6543)

**Status:** Accepted (2026-08-11) · **constrains ADR-005** (LangGraph checkpointing) and **ADR-006**
(Supabase as the datastore). Neither decision changes; this records the port they are reachable on and why
the cheaper one is unavailable.

**Context:** Supabase exposes the same database on two ports through Supavisor. **6543 is transaction mode** —
a connection is handed back to the pool at the end of every transaction, so thousands of clients share a
small number of server connections. **5432 is the session-mode / direct connection** — the client holds one
server connection for the life of the session. Transaction mode is the one a small container is supposed to
want: it is what makes a 0.2 vCPU / 512 MB worker (the same Northflank free-tier budget ADR-032 was written
against) cheap to scale.

The RQ worker checkpoints the graph to that database. `backend/worker/run_job.py:152` (and `:183` for the
resume entrypoint) opens the checkpointer as:

```python
with PostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
```

**The constraint, read out of the library rather than inferred.** `PostgresSaver.from_conn_string` is
`from_conn_string(cls, conn_string, *, pipeline: bool = False)` and its whole body is:

```python
with Connection.connect(
    conn_string, autocommit=True, prepare_threshold=0, row_factory=dict_row
) as conn:
```

(`langgraph/checkpoint/postgres/__init__.py:64-83`.) Two facts follow, and the second is the one that is
easy to get backwards:

1. **`prepare_threshold` is hardcoded and not on the signature.** The only knob `from_conn_string` exposes
   is `pipeline`. There is no keyword, no env var, and no `**kwargs` passthrough — the value cannot be
   changed by configuration.
2. **`prepare_threshold=0` does not mean "no prepared statements". It means *prepare everything,
   immediately*.** psycopg3's semantics: *"If it is set to 0, every query is prepared the first time it is
   executed. If it is set to `None`, prepared statements are disabled on the connection"*
   (`psycopg/_connection_base.py:391-403`; the branch is `psycopg/_preparing.py:63`, where only `None`
   short-circuits to `Prepare.NO`). So the value LangGraph forces is the **most** aggressive setting
   available, and the value pgbouncer/Supavisor transaction mode requires — `None` — is precisely the one
   `from_conn_string` makes unreachable.

Server-side prepared statements are per **server** connection. In transaction mode the client's next
statement can land on a different server connection than the one that ran `PREPARE`, so the checkpointer's
own writes fail — `prepared statement "_pg3_0" does not exist`, or `already exists` when a recycled
connection is reused. This is not tunable from our side: it is a property of pooling transactions, and
LangGraph opts into the incompatible setting on our behalf.

**What was tried.** Pointing `SUPABASE_DB_URL` at 6543 and letting the checkpointer run. There is no
configuration fix — see (1). The remaining escapes are all code changes: construct a `psycopg.Connection`
ourselves with `prepare_threshold=None` and pass it to the `PostgresSaver(conn)` constructor (which *does*
accept a connection or a pool), or switch to a `ConnectionPool` we configure. Both mean the worker owns
connection lifecycle that the library currently owns, for a pooler we are not otherwise constrained to use.

**Decision:** **Run the worker's checkpointer over the direct connection on port 5432.**
`SUPABASE_DB_URL` names 5432; 6543 is not used by this service. Keep `PostgresSaver.from_conn_string` as
written — the library's default is correct *for* a session-mode connection, and hand-rolling the connection
to reach a pooler we do not need is a seam the worker should not own.

**Consequences:**
- **Connection count, which is the whole cost of this decision.** A direct connection is held for the entire
  graph run, not per statement — the `with` block in `run_job.py` wraps `_run_with_progress`, so the
  connection lives as long as the job (RQ `job_timeout=900`, `app/main.py:110` / `:154`). Direct connections
  are a small fixed ceiling on a Supabase free/micro instance, where the pooler's are effectively unbounded.
- **This is survivable only because the worker is single-process.** `worker/run_worker.py` runs one
  `Worker`/`SimpleWorker` over one `storybook` queue with no concurrency setting, so **one job at a time →
  at most one direct connection at a time**. The 0.2 vCPU / 512 MB budget that makes the container feel
  cramped is also what keeps this decision safe.
- ⚠️ **Therefore: scaling the worker horizontally is now a database decision, not just a hosting one.**
  N worker replicas (or any move to a concurrent worker class) is N held direct connections against a fixed
  ceiling, and the failure mode is `FATAL: too many connections` on job start — a job that fails before it
  writes a checkpoint, so there is nothing to resume from. Check the instance's `max_connections` before
  raising replicas, and revisit this ADR at that point rather than after the first outage.
- **The API service is unaffected.** FastAPI talks to Supabase over PostgREST/HTTPS (`supabase-py`), not
  psycopg; the direct connection is the worker's alone. Nothing else in the repo opens one except
  `backend/tests/test_rls_isolation.py`, which points at a local Supabase.
- **`checkpointer.setup()` still runs on every job** and creates `checkpoints`, `checkpoint_blobs`,
  `checkpoint_writes` on first use (`supabase/migrations/0008_authorization_surface.sql:171` guards against
  them; `auth-authorization-surface.md` §48). Unchanged by the port, noted so the two are not confused.

**Alternatives:**
- **Transaction pooler (6543) with a hand-built connection** — construct `psycopg.Connection.connect(...,
  prepare_threshold=None)` and pass it to `PostgresSaver(conn)`. Rejected for now: it moves connection
  lifecycle, autocommit and row-factory decisions out of the library and into `run_job.py` for a benefit
  (pooled connections) the current single-worker shape does not need. **This is the first thing to reach for
  when the previous consequence bites** — it is a contained change, not a redesign.
- **Session pooler (5432 via the Supavisor host)** — behaves like the direct connection for our purposes
  (one server connection per session), so it neither causes the problem nor solves the connection-count one.
  Available as an IPv4 reachability workaround, not as a fix.
- **`AsyncPostgresSaver`** — same hardcoded `prepare_threshold=0` in its own `from_conn_string`
  (`postgres/aio.py`). Not an escape; the pipeline is synchronous anyway.
- **Move checkpoints off Supabase** to a Postgres we configure — rejected: a second datastore for one
  connection-string flag, against ADR-006, and the checkpoints are classroom-scoped data that belongs with
  the rest of it.
- **Drop Postgres checkpointing for an in-memory saver** — rejected outright. Checkpoint/resume is a
  critical path (ADR-005); ADR-029's reveal `interrupt()` is not resumable without it.

⚠️ **One honest qualification.** The mechanism above is verified in code — the hardcoded
`prepare_threshold=0`, psycopg's semantics for `0` vs `None`, the single-worker shape, the 900 s timeout.
**The port migration itself leaves no trace in this repo**: `SUPABASE_DB_URL` is blank in
`backend/.env.example`, the value lives only in Northflank's environment, and `git log -S "6543"` /
`-S "prepare_threshold"` return nothing outside `uv.lock` hashes and a deleted Phase-0 plan doc. This ADR
is therefore the *only* record that 6543 was tried and abandoned. Do not delete it and re-derive it from a
production incident.
