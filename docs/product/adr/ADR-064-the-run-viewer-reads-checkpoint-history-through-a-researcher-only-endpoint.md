# ADR-064 — The run viewer reads checkpoint history through a researcher-only endpoint

**Status:** Accepted (2026-10-09) · settles the open questions in issue #104 · adds one backend
route and widens one account's read access (the adjudicator) · no migration · no `StoryMemory` or
`contracts/` change · extends ADR-033 (checkpoint store) and ADR-006 (signed URLs) to a new reader

**Context:**

Issue #104 asks for a page per run that shows what Langfuse shows, laid out for a reader: the path
through the graph, the story, the references, every page attempt with its verdict, moderation, cost
and timing. #104 left four questions open. This ADR settles them.

What the code says, checked on 2026-10-09:

- **`jobs` holds counts only.** `0013_jobs_research_metrics.sql` adds `image_count`, `regen_count`,
  `ref_retry_count`, `scenes_*`, `usd_estimate`, `langfuse_trace_url`. No verdict, prompt, image
  path or reference lives on the row.
- **The full run state is the LangGraph checkpoint thread.** `run_job.py` runs the graph under
  `PostgresSaver` with `thread_id = job_id`, in the same Supabase Postgres (ADR-033). The latest
  checkpoint is the whole `StoryMemory`: per-scene `attempts` with `vlm_verdict` and
  `failure_reasons`, `final_image_ref`, characters with `canonical_ref_image` and `ref_verdict`,
  `input.moderation`, per-scene `moderation_status`, and `cost`. Nothing in the repo deletes
  checkpoints.
- **The history gives the path.** On the installed `langgraph 1.2.8` /
  `langgraph-checkpoint-postgres 3.1.0`, checkpoint metadata no longer carries `writes`. But
  `get_state_history` returns one snapshot per step, and `snapshot.next` in step order is the
  sequence of nodes that ran, loops included. The gap between consecutive `created_at` values is
  each step's duration. Checked on a throwaway looping graph
  (`gen → check → gen → check → gen → check`, eight snapshots, every visit present).
- **The checkpoint is LangGraph's own binary format.** Python reads it through the compiled graph.
  Reading it from Next.js would mean re-implementing LangGraph's serializer in TypeScript.
- **Langfuse is the other copy, and a worse one here.** Langfuse Cloud's free Hobby plan gives
  30 days of data access and 30 API requests per minute (langfuse.com/pricing, read 2026-10-09).
  The project's plan was not checked. The September audit
  (`docs/capstone/pipeline-gate-audit-2026-09.md`) found `input.raw_text` in trace state.
- **Every `jobs` row is a real app run under a student profile.** `build_corpus` never writes
  `jobs`, and no column marks a run as synthetic. Corpus pairs that annotators label come from
  bundles, not from `jobs`, so a run page cannot show an annotator the verdict on a pair they label.
- **Researchers read approved jobs only.** `0008_authorization_surface.sql`:
  `researchers read approved jobs … using (auth_role() = 'researcher' and approved_at is not null)`.
  A teacher can approve only a `complete` job (`app/review.py`, 422 otherwise), so no failed run is
  ever readable under that rule.
- **Signed URLs last 300 seconds.** `providers.get_signed_url` hard-codes `expires_in=300`.

**Decision:**

1. **Data source: checkpoint history, read by the backend.** A new FastAPI route
   `GET /research/runs/{job_id}` opens `PostgresSaver` on `settings.supabase_db_url`, builds the
   graph with it, and reads `get_state_history({"configurable": {"thread_id": job_id}})`. It
   returns a projection, not the checkpoint: the latest `StoryMemory` minus the excluded fields
   below, plus the step list (`node`, `started_at`, `duration_ms`) derived from the history.
   Langfuse is not called.

2. **Access, decided on the server for every request.**
   - Signed out → 401.
   - `role = 'researcher'` and `is_adjudicator = true` → any job.
   - `role = 'researcher'` otherwise → only jobs with `approved_at is not null`, the 0008 rule
     unchanged. Anything else → 403 with a reason the page can show.
   - Any other role → 403.
   The widening is one account, the adjudicator, so failed and unapproved runs can be inspected.
   It is enforced in the route, which uses the service-role client as every backend route does.
   RLS on `jobs` is not changed.

3. **Excluded from every response:** `input.raw_text`, `profile_id`, `classroom_id`, and
   `jobs.input_text` (which the route never selects). The story text shown is
   `input.redacted_text`; page text is `scene.text_excerpt`, which downstream nodes build from
   redacted text.

4. **Images:** the route signs every storage path it returns. `get_signed_url` gains an optional
   `expires_in` argument; existing callers keep 300 s, and this route passes 3600 s, so a page left
   open during a demo keeps its images.

5. **Model IDs are shown as not recorded.** `StoryMemory` does not store them, and today's
   `app/config.py` values are not evidence of what an old run used. Prompt versions are shown only
   where the state records them (`ref_verdict_prompt_version`).

6. **The run list stays public, counts only.** `/research/metrics` keeps reading `jobs` server-side.
   A run's title is sent to the browser only when the viewer could open that run under rule 2;
   otherwise the row shows the short id. A title is redacted (ADR-059) but can still identify a
   donated story (issue #108).

**Consequences:**

- Every past run that has a checkpoint thread is viewable, with no backfill and no migration.
- The detail page needs the backend up. The list does not.
- Checkpoint threads now have a reader, so they cannot be pruned or moved without changing this
  route. That ties the run viewer to the Supabase plan question in #102: checkpoints count toward
  database size.
- One request loads every checkpoint in a thread (one full `StoryMemory` per step). Inferred, not
  measured: a run of about 60 steps reads a few megabytes. If that proves slow, the route can read
  only the latest state plus checkpoint metadata. The response shape stays the same.
- The adjudicator can read unapproved child stories, redacted. That is a deliberate exception to the
  0008 consent rule for one account, recorded here.
- The Langfuse link stays, behind #103's warning modal and env flag. On a Hobby plan it stops
  resolving after 30 days whatever the page does.

**Alternatives considered:**

- **Snapshot a redacted run record onto `jobs` at run end.** Readable from Next.js directly and
  survives a checkpoint purge. Rejected: a migration, empty for every past run unless backfilled,
  and the node path would need recording separately.
- **Langfuse API from the Next.js server.** Rejected: 30-day data access on the free plan, a rate
  limit, Langfuse secret keys in the frontend environment, an outside service on defense day, and
  it reads traces known to hold raw story text.
- **Decode the checkpoint tables in Next.js.** Rejected: couples the frontend to LangGraph's
  private serialization format.
- **Approved jobs only, for every researcher.** Rejected: failed runs cannot be approved, and they
  are the main reason to open a run.
- **All researchers read all jobs.** Rejected: reverses the 0008 consent rule for every annotator
  account.
