# Feature Spec — storybook deletion

**Status:** draft · **Phase:** 2 · **Owners:** `backend/app/main.py`, `backend/worker/`,
`frontend/app/s/[profileId]/`, `supabase/migrations/`
**Derived from:** MASTER_SPEC §§2, 5–7 · **Rationale:** ADR-044, ADR-006, ADR-005,
ADR-029, ADR-030

> This is a cross-cutting lifecycle feature, not a LangGraph node. It specifies deletion of one
> child-owned storybook. Guardian-request account deletion, classroom deletion cleanup, and expiry
> of abandoned pauses remain in the broader `data-deletion` feature.

## 1. Purpose

Let a child permanently delete one of their own finished, failed, or paused storybooks without
allowing cross-account deletion, racing an active worker, or leaving StoryBuddy-controlled copies
in Storage, LangGraph checkpoints, Langfuse, or the `jobs` table.

Deletion is asynchronous because those stores cannot be changed atomically. Acceptance immediately
makes the book unavailable to non-owner readers and every normal product reader; the owner retains
row access only to observe the pending tombstone. An idempotent cleanup job removes each active copy
and deletes the `jobs` row last.

## 2. Scope and non-goals

### In scope

- A child-facing delete control for the child's own `complete`, `failed`, or `awaiting_confirm` job.
- Authenticated `DELETE /jobs/{job_id}` authorization and compare-and-set lifecycle transition.
- A durable quiescence barrier covering normal exits, pauses, raised failures, and RQ hard failures.
- Idempotent cleanup of all first-party storybook data in the four stores named in §5.
- Pending/retry UI and removal from student, peer, teacher, gallery, reader, and metrics surfaces.
- Deterministic tests plus live Supabase/RLS/Storage verification.

### Out of scope

- Cancelling a `queued` or `running` generation.
- Teacher-initiated per-book deletion.
- Guardian-request deletion of a student account or classroom.
- Automatic expiry/reaping of abandoned `awaiting_confirm` jobs or naming S4's swept-pause status.
- Deleting separately consented `research_pairs`, `annotations`, or `private_assets/research/` data.
- Promising immediate erasure from Supabase backups, CDN/client caches, processor logs, or upstream
  provider retention systems.
- A generic deletion framework, store registry, new queue, or new dependency.

## 3. Data contract and lifecycle

The next available migration widens the `jobs.status` check with `deleting` and adds:

```sql
worker_finished_at timestamptz null
```

`worker_finished_at` is worker lifecycle state, not Story Memory. No field or schema-version change
is made under `backend/contracts/`.

| Current state | `worker_finished_at` | Delete result | Next state |
|---|---:|---|---|
| `complete`, `failed`, `awaiting_confirm` | non-null | `202` and enqueue cleanup | `deleting` |
| `deleting` | non-null | `202` and safely re-enqueue cleanup | `deleting` |
| `queued`, `running` | any | `409`; enqueue nothing | unchanged |
| allowed state | null | `409`; enqueue nothing | unchanged |
| missing or foreign row | any | `404`; enqueue nothing | — |

Invariants:

1. `worker_finished_at` is null before any worker may produce data for the job.
2. The finish-marker update is the worker's last write: it runs only after all other row,
   checkpoint, Storage, and Langfuse work by that worker has stopped. The RQ hard-failure path sets
   it only after the work horse is dead.
3. Generation and resume entrypoints clear it. The confirm compare-and-set changes
   `awaiting_confirm → queued` and clears it in the same update.
4. If confirm enqueue fails, rollback restores `awaiting_confirm` and a non-null finish timestamp;
   no worker started, so the row is quiescent again.
5. Confirm and delete issue competing compare-and-set updates from `awaiting_confirm`. Only one may
   change the row or enqueue work.
6. Cleanup is allowed to act only on a row currently in `deleting`. A missing row is an idempotent
   success; any other status is a no-op failure and no child data is removed.
7. A `deleting` row never returns to a readable story state. The `jobs` row is deleted only after
   every other active store reports success.

### Existing-row rollout

An unconditional SQL backfill is forbidden: a legacy `complete` or `failed` status can still race
the worker's final Langfuse publication. Release uses one controlled cutover:

1. stop new story submissions and drain the `storybook` RQ queue;
2. stop every old worker and verify the queue has no queued/started jobs and Postgres has no
   `queued`/`running` rows;
3. apply the migration and backfill `worker_finished_at` only for existing `complete`, `failed`, and
   `awaiting_confirm` rows while no worker process can write;
4. deploy the marker-aware web/worker code, then resume submissions.

If any quiescence check fails, do not backfill or expose deletion. Existing null-marker rows remain
safely non-deletable (`409`) until the controlled cutover succeeds.

## 4. API and UI behavior

### 4.1 API contract

`DELETE /jobs/{job_id}` uses the existing bearer-token dependency and server-side service-role
client. Browser clients receive no `DELETE` policy on `jobs` or `storage.objects`.

- The lookup is scoped to `id = job_id` and `profile_id = auth user id`. Missing and foreign IDs
  both return `404` to avoid disclosing another child's job.
- The endpoint atomically transitions an eligible row to `deleting`, preserving the
  `worker_finished_at` proof, then enqueues `worker.delete_storybook.delete_storybook_job(job_id)`
  on the existing `storybook` RQ queue.
- Success returns `202` with `{"status": "deleting"}`.
- A repeated request for `deleting` returns the same response and may enqueue the same cleanup again.
- An ineligible or non-quiescent row returns `409` with no enqueue.
- If enqueue raises or its result is uncertain, the endpoint returns `503` and leaves the row in
  `deleting`. It must not roll back: the task may already exist, and retrying DELETE is safe.
- CORS adds `DELETE`; no new route or server action is added to Next.js.

### 4.2 Child experience

- Complete, failed, and paused cards expose a keyboard-accessible delete button separate from the
  card link. `paused` is the frontend bucket for persisted `status='awaiting_confirm'`; it is not a
  sixth database status. Queued/running cards do not expose delete.
- The existing `ConfirmDialog` asks for irreversible confirmation and states that approved books
  also disappear from the class gallery. Cancel changes nothing.
- After `202`, the card becomes a non-navigable `Deleting…` pending card. Reader and process routes
  that observe `deleting` show the same pending state with a return-to-bookshelf action; they never
  render captions, images, retry, confirm, or review actions.
- While a pending tombstone exists, the child surface reselects that job every two seconds while the
  page is active. A missing row removes the card. If it still exists after ten seconds, the card
  offers `Try deleting again`, which repeats the same DELETE request; polling continues while the
  page remains active.
- `404` after a retry means cleanup already finished and removes the card. `409` keeps the original
  book state and explains that a book still being made cannot be deleted yet. On `503` or an
  uncertain response, the client reselects the row: `deleting` enters pending UI; any other status
  preserves the original book. Other errors follow the same reselect rule and offer retry; raw
  backend errors are never shown.

### 4.3 Other read surfaces

At the `deleting` transition:

- peer gallery, teacher review/books, and research metrics queries exclude the row;
- teacher review mutations can no longer approve/reject it;
- `useJob.classify` has an explicit deletion-pending result instead of falling through to failure;
- child bookshelf Realtime handles the `deleting` update, while the bounded reselect above—not a
  filtered DELETE subscription—confirms final removal.

## 5. Cleanup saga and data blast radius

`delete_storybook_job(job_id)` performs the following ordered, idempotent steps:

1. **Supabase Storage:** recursively list every object beneath the literal `{job_id}/` folder in
   private bucket `storybook-images`, paginating until exhausted. Remove file paths through the
   Storage API in batches supported by the installed SDK/service. Folder entries are traversed, not
   passed to `remove`. Never derive inventory from `jobs.pages`.
2. **LangGraph checkpoints:** open the existing direct Postgres connection and call the installed
   `PostgresSaver.delete_thread(job_id)`, covering `checkpoints`, `checkpoint_blobs`, and
   `checkpoint_writes` for `thread_id = job_id`.
3. **Langfuse:** delete trace ID `job_id` without hyphens through the installed Langfuse API. A
   missing trace is success; another API failure stops the saga.
4. **Postgres job row:** delete `jobs.id = job_id AND status = 'deleting'` last. If a concurrent
   cleanup already removed it, a re-read that confirms absence is success. Zero affected rows while
   the row still exists is a failure; the task must not silently claim completion.

Missing objects, checkpoint threads, and traces count as already removed. After each Storage batch,
the task continues listing from the folder rather than trusting stale offsets over a shrinking list.
Any non-idempotent error stops the task and raises so RQ records the failure. The `deleting` tombstone
remains and a repeated endpoint call may restart the whole sequence safely.

The cleanup owns these current copies:

| Store | Child-derived data removed |
|---|---|
| `jobs` | input text, reveal, pages, review fields, failure details, cost/outcome metrics, trace URL |
| `storybook-images/{job_id}/` | canonical refs, rejected/superseded draws, moderation retries, final pages |
| LangGraph checkpoint tables | serialized `StoryMemory`, blobs, pending writes |
| Langfuse | prompts, model outputs, spans, published trace |

It deliberately does not touch `research_pairs`, `annotations`, or `private_assets/research/`.
Any future storybook-owned asset (narration and export are cut — ADR-058) may not ship until this table and cleanup sequence
are amended to cover their storage locations.

## 6. Authorization and RLS

The migration keeps direct browser mutation server-only and changes read policies so acceptance
revokes access immediately:

- The child's existing own-job SELECT policy continues to expose their `deleting` tombstone,
  including its row fields, until cleanup finishes. Product surfaces render only pending status;
  this temporary owner read is the deliberate cost of observing/retrying without a new status API.
- Peer, teacher, and researcher `jobs` SELECT policies require `status <> 'deleting'`.
- Every `storybook-images` SELECT policy, including the owner's, requires the owning job to have
  `status <> 'deleting'`. Browser roles cannot mint a new signed URL after acceptance. The existing
  service-role signer is not user-callable and remains internal to generation; the quiescence
  barrier proves no generation caller is alive before deletion can win.
- Teacher approval/rejection requires `status <> 'deleting'` in both `USING` and `WITH CHECK`.
- No authenticated or anonymous `DELETE` policy is added to `jobs` or `storage.objects`.
- Service-role endpoint and worker credentials remain backend-only.

Already-issued signed URLs can live for the frontend's current one-hour TTL; deleting the underlying
object ends future origin reads, but already cached bytes follow client/CDN cache behavior. Product
and consent copy must describe deletion from StoryBuddy-controlled active stores and disclose
applicable backup and processor retention instead of claiming instantaneous erasure everywhere.

## 7. Failure handling and observability

- Each cleanup attempt logs job ID, current step, outcome, and remaining object count where known.
  It never logs story text, prompts, captions, signed URLs, or object bytes.
- Endpoint metrics distinguish accepted, ineligible, unauthorized/not-found, enqueue-failed, and
  repeated requests. Cleanup metrics distinguish success and failure by store.
- Deleting the Langfuse trace and `jobs` row intentionally removes per-job observability and cost
  metrics. No metrics-only tombstone or deletion ledger is added.
- A worker-finish marker write failure fails closed: the book remains non-deletable until repaired;
  it is never guessed quiescent from elapsed time.
- A cleanup failure after partial removal never restores the book or rolls `status` back.
- If repeated user retries prove inadequate, ADR-044's escape hatch requires a new decision for a
  scheduled reaper/durable cleanup queue and its alert owner.

## 8. Cross-cutting checklist (MASTER_SPEC §5)

- [ ] CC-1 Moderation ordering — N/A; deletion adds no generated-content path.
- [x] CC-2 PII redaction — removes persisted redacted and any checkpointed input; logs contain no
  content. It does not claim deletion from backups/processors.
- [x] CC-3 Cost control — queued/running deletion is rejected, so this feature cannot pretend to
  cancel paid work. It adds no provider call or new service.
- [x] CC-4 Security — owner-scoped FastAPI authorization, no browser DELETE policy, immediate RLS
  revocation, private Storage, and cross-classroom non-disclosure (§6).
- [x] CC-5 Observability — step/result logs and aggregate attempt metrics, while the deleted job's
  trace and row metrics are intentionally erased (§7).
- [x] CC-6 Accessibility — separate 44px delete target, native dialog semantics through the existing
  component, keyboard operation, focus handling, explicit pending/error text.
- [ ] CC-7 Reproducibility — N/A; no model output or seed.
- [x] CC-8 Student vs teacher design — delete/pending UI exists only in the student Cobalt Playroom
  surface; teacher surfaces silently lose the child-owned row.
- [x] CC-9 Failure states = success states — failed books receive the same delete control and pending
  care as completed books; cleanup errors remain retryable and kid-legible.
- [x] CC-10 Checkpointing/resumability — quiescence prevents resurrection; thread deletion is explicit
  and idempotent; partial cleanup resumes from current external state.

## 9. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

### Migration and RLS

1. `deleting` satisfies the status check; `worker_finished_at` is nullable and defaults null.
2. Owner can SELECT a deleting tombstone but cannot DELETE the row directly.
3. Classmates, teacher, and researcher cannot SELECT a deleting job, including an approved one.
4. No student, peer, teacher, or researcher can SELECT its Storage objects after the transition.
5. Teacher approve/reject against deleting affects zero rows.
6. Existing isolation cases for every non-deleting status remain green.

### Endpoint

7. Missing and foreign IDs return `404`; neither updates nor enqueues.
8. `queued`, `running`, or a null finish marker returns `409` and enqueues nothing.
9. Each eligible status with a finish marker wins one CAS, returns `202`, and enqueues one cleanup.
10. A second DELETE on `deleting` returns `202` and may enqueue the same job again.
11. Confirm/delete races produce exactly one winning transition and one enqueue.
12. Delete enqueue failure returns `503`, leaves `deleting`, and a retry can enqueue.
13. CORS preflight permits DELETE only from the configured frontend origin.
14. Existing terminal rows receive a marker only under the stopped-worker/drained-queue rollout;
    a null legacy marker remains non-deletable.

### Worker lifecycle

15. Fresh and resume entrypoints clear `worker_finished_at` before setting/running graph work.
16. Complete, pause, caught failure, and hard work-horse failure set it only after final trace work.
17. Confirm clears it in the CAS; confirm enqueue rollback restores a non-null marker.
18. A finish-marker write failure never makes the row deletable.

### Cleanup

19. Cleanup refuses a present row whose status is not `deleting`; a missing row is a no-op success.
20. Nested/paginated Storage inventory deletes every `{job_id}/` file, including refs and superseded
    attempts, and never touches a sibling prefix.
21. Removing from a shrinking folder does not skip a page; supported batches are honored.
22. Checkpoint deletion receives exactly `job_id`; Langfuse deletion receives the hyphenless ID.
23. Missing resources are success. A failure at each step leaves the row and prevents later steps.
24. Row deletion occurs last and is constrained by both ID and `status='deleting'`.
25. Concurrent duplicate cleanups treat a final zero-row delete as success only after confirming the
    row is absent; a still-present row fails the task.
26. Re-running after each partial-failure point completes without error or duplicate side effects.

### Frontend

27. Only complete, failed, and `paused` (`awaiting_confirm`) cards expose delete; clicking it does not
    follow the card link.
28. Cancel changes nothing; confirm calls authenticated FastAPI DELETE once.
29. `202` renders non-navigable pending UI; reselecting a missing row removes it.
30. Pending retry repeats DELETE; `404` removes the card; `409` restores/explains the original state.
31. `503` or an uncertain response reselects the row and renders pending when it is `deleting`;
    failures remain retryable without raw error text.
32. Reader/process routes cannot render book/retry/confirm content for `deleting`.
33. Teacher, gallery, and metrics surfaces omit deleting rows.

All provider, queue, Storage, checkpointer, Langfuse, and Supabase calls are mocked in deterministic
tests. Live checks are separate and use disposable rows/assets only.

## 10. Live Supabase verification

Because migrations are hand-applied and local tests cannot prove the remote project state, verify in
a non-production Supabase project before release:

1. Rehearse §3's stopped-worker/drained-queue cutover and prove legacy terminal rows are backfilled
   while legacy/injected non-quiescent rows are not.
2. Apply the generated migration and confirm its entry plus the status constraint/column definitions.
3. Seed two classrooms, child/peer/teacher/researcher users, one approved quiescent job, nested test
   objects under its exact UUID prefix, and a sibling prefix.
4. Prove the RLS matrix in §9.2–6 with real JWTs and prove no direct DELETE policy exists.
5. Accept deletion through FastAPI; prove browser Storage signing fails immediately for every role.
6. Run cleanup and verify the job, exact Storage prefix, checkpoint thread, and test Langfuse trace
   are absent while the sibling prefix and separate research rows/assets remain.
7. Repeat DELETE/cleanup around each injected partial failure and concurrent duplicate attempt, and
   confirm eventual convergence.
8. Record backup, CDN/cache, Supabase, Langfuse, and model-provider retention statements in the
   privacy/consent material before making an erasure promise to users.

Do not run this verification against real child, study, or production data.

## 11. Blast radius — implementation change set

| Surface | Required change |
|---|---|
| `supabase/migrations/` | status/marker migration; controlled legacy backfill; RLS/review predicates |
| `backend/app/main.py` | DELETE contract, CORS, CAS/enqueue; confirm marker handling |
| `backend/worker/run_job.py`, `run_worker.py` | finish-marker ordering on every exit |
| `backend/worker/delete_storybook.py` | ordered idempotent cleanup task |
| backend tests | endpoint, lifecycle, cleanup, RLS isolation |
| student bookshelf and `useJob` | delete control, explicit pending state, retry/reselect |
| reader/process pages | deletion-pending branch |
| teacher review, gallery, research metrics | omit deleting rows and mutations |
| frontend tests | control, confirmation, pending, retry, surface exclusion |
| privacy/consent copy | active-store scope and external retention disclosure |

No new dependency, datastore, top-level directory, Story Memory field, client DELETE policy, or
generic cleanup abstraction is permitted.

## 12. Eval / quality checks

N/A. This feature produces no subjective content and feeds no Objective-4 label. Its correctness is
authorization, lifecycle, and deletion completeness, covered by deterministic and live integration
verification.

## 13. Linked decisions and open questions

**Depends on:** ADR-044 (authoritative deletion lifecycle), ADR-006/017 (private Storage and
classroom RLS), ADR-005/033 (RQ and direct checkpoint connection), ADR-029 (pause/confirm race),
ADR-030 (Langfuse trace identity), `auth-authorization-surface.md`, and
`kid-flow-pause-lifecycle.md`.

**Implementation-time verification, not design questions:** confirm the installed Supabase Storage
list/remove response shapes and batch limit, `PostgresSaver.delete_thread` behavior, and Langfuse
missing-trace error shape before writing adapters. Current Supabase guidance still requires deletion
through the Storage API and pagination of list results; no relevant Storage breaking change was
found in the 2026 changelog review.

**Still open elsewhere:** abandoned-pause TTL/status, account/classroom deletion cleanup, provider
and backup retention periods, and whether repeated failures justify ADR-044's scheduled-reaper escape
hatch. None blocks this per-story deletion spec.

## 14. Definition of done

1. Every invariant in §3 is enforced and every test in §9 exists and passes.
2. A deletion accepted during a confirm race cannot be resumed or recreated by a worker.
3. Acceptance immediately revokes non-owner row access and all new Storage access.
4. Retry converges after failure at any cleanup step, and the row is always removed last.
5. All four active stores are proven empty for a disposable live job; sibling/research data survives.
6. Every affected UI has an explicit deletion state; no deleting book remains readable or reviewable.
7. Privacy/consent copy states the limits in §§2 and 6 without promising impossible instant erasure.
8. Backend and frontend pre-merge verification is green and shown with actual output.
9. This spec becomes `built`; the disposable implementation plan is deleted after verification.

**Not done** if deletion is available for an in-flight/unproven job; authorization returns a distinct
foreign-row response; any browser role gains direct DELETE; inventory comes from `pages`; the job row
is removed before Storage/checkpoints/Langfuse; partial failure restores readability; research assets
are swept by prefix coincidence; or remote RLS/Storage behavior is assumed from migration files alone.
