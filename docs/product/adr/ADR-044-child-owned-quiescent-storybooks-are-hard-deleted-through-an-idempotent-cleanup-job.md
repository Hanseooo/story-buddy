# ADR-044 — Child-owned quiescent storybooks are hard-deleted through an idempotent cleanup job

**Status:** Accepted (2026-08-24; owner approved) · **resolves D-J** · **amends ADR-006's data lifecycle** ·
**amends ADR-021's approved-gallery lifetime** · **constrains ADR-005/029/030** without changing the
generation graph, reveal semantics, or observability provider

## Context

The student bookshelf retains every job, including failed attempts. Failed cards are collapsed under
*Didn't finish*, but the child cannot remove them. D-J left three decisions open: who authorizes deletion,
whether deletion is hard or soft given the metrics stored on `jobs`, and whether a deleted row remains visible
to the teacher.

A `jobs` row is not the whole storybook. One job can leave child-derived data in four active stores:

1. the `jobs` row, including `input_text`, pages, review state, cost/outcome metrics, and trace URL;
2. every object under `storybook-images/{job_id}/`, including canonical references, rejected draws, moderated
   retries, and final pages that `jobs.pages` alone cannot enumerate;
3. LangGraph's `checkpoints`, `checkpoint_blobs`, and `checkpoint_writes`, keyed by
   `thread_id = job_id` and containing serialized `StoryMemory`;
4. the Langfuse trace whose ID is `job_id` without hyphens and which may have been published by the worker.

Deleting only the Postgres row would therefore revoke normal RLS reads while leaving the most expensive and
most complete copies behind. Supabase Storage also requires deletion through its Storage API; deleting
`storage.objects` metadata with SQL can orphan the underlying object.

Deletion can also race generation. The application does not persist the RQ job ID, and removing a `queued` or
`running` row does not stop the worker, provider spend, uploads, checkpoint writes, or trace publication. Even a
freshly written `complete` or `failed` status is not proof of quiescence today: `run_job.py` publishes the
Langfuse trace in `finally` after writing that status.

## Decision

### 1. The child may delete only their own storybook

`DELETE /jobs/{job_id}` is an authenticated FastAPI endpoint. It derives the caller from the bearer token and
accepts only a row whose `profile_id` equals that caller's profile ID. A missing or foreign job returns `404`,
preserving the existing non-disclosure posture.

The browser receives no `DELETE` policy on `jobs` or `storage.objects`. The endpoint and cleanup worker use the
existing server-side service-role boundary. Teachers retain approve/reject controls and do not gain individual
storybook deletion. Guardian-request deletion of an entire student's account and data remains a separate
`data-deletion` workflow because it has a larger consent, account, classroom, and provider-retention scope.

Deleting an approved book removes it from the classroom gallery and teacher views. No audit copy of the child
story remains merely because a teacher previously approved it.

### 2. Deletion is permanent, not a hidden-row soft delete

The operation removes the child-derived storybook from all four active stores above. It also removes the
per-job operational/research metrics stored directly on `jobs`. Research convenience is not a lawful reason to
retain a deleted child's record; consented research artifacts must use their separately approved, frozen,
de-identified lifecycle.

The delete operation does not touch `research_pairs`, `annotations`, or the `private_assets/research/` prefix.
Those artifacts have no job foreign key and are governed by their own consent and withdrawal process.

Supabase backups, processor logs, and upstream provider retention cannot be synchronously erased by this
endpoint. Product and consent copy must describe deletion from StoryBuddy-controlled active stores and the
applicable backup/processor retention periods rather than promise instantaneous erasure from every historical
copy. Existing storybook URLs can remain signed for up to one hour; removing the underlying object ends future
origin reads, while already cached bytes remain subject to the client/CDN cache lifetime.

### 3. Only quiescent jobs are deletable

The `jobs.status` constraint gains `deleting`. The row also gains nullable `worker_finished_at` as the explicit
quiescence marker.

Every generation entrypoint clears `worker_finished_at` before work can resume. Every normal, interrupted, or
failed worker exit—including the RQ hard-failure callback—sets it only after all checkpoint, row, and Langfuse
work has stopped. This marker is worker lifecycle state; it does not enter `StoryMemory`.

Deletion is accepted only when:

- `status` is `complete`, `failed`, or `awaiting_confirm`; and
- `worker_finished_at` is non-null.

`queued` and `running` return `409`. Cancellation is a separate feature: it would require storing or deriving the
RQ job identity and adding cooperative stop checks around paid provider calls. A job whose worker has not proved
quiescence is not deleted by guessing that enough time has passed.

Confirm and delete use competing compare-and-set updates from `awaiting_confirm`. Exactly one can win: confirm
moves the row back to `queued` and clears the marker; delete moves it to `deleting`. The loser returns the current
state and enqueues nothing.

### 4. Cleanup is an idempotent RQ saga, and the row is deleted last

After the authorization and compare-and-set succeed, FastAPI enqueues one deletion task on the existing RQ/Redis
infrastructure and returns `202`. Repeating the request for a row already in `deleting` is safe and may re-enqueue
the same cleanup; missing resources count as already removed.

The cleanup task performs these steps:

1. list every object under the literal `{job_id}/` prefix in `storybook-images`, paginate, and remove it through
   the Storage API in supported batches;
2. call the installed `PostgresSaver.delete_thread(job_id)` to remove checkpoints, blobs, and pending writes;
3. delete the Langfuse trace through the installed `client.api.trace.delete()` API, treating a missing trace as
   success;
4. delete the `jobs` row only after the other active stores report success.

The task never derives the object inventory from `jobs.pages`, because that array excludes reference images and
superseded attempts. If cleanup fails partway, the `deleting` row remains as a retryable tombstone and normal
read surfaces render it as deletion pending rather than as a usable or failed book. The endpoint never rolls the
row back to a readable state after external data has been removed.

No generic storage-cleanup framework or provider interface is added. The volatility is the set of first-party
storybook stores; this ADR names the current four explicitly. A future narration or export feature must add its
own storybook assets to this cleanup before it can ship.

## Consequences

- A child gets an irreversible delete control for completed, failed, and paused books, with a confirmation step
  and a visible pending state while cleanup runs.
- A child cannot use deletion as cancellation. In-flight books must first reach a quiescent allowed state.
- Approved books disappear for peers, teachers, and researchers when their owner deletes them.
- Per-job image counts, scene outcomes, dollar estimates, and trace links are intentionally lost. Aggregate or
  study data cannot depend on mutable operational rows if it must survive a participant's deletion request.
- `worker_finished_at` becomes the single proof that no producer can recreate data after cleanup starts. Status
  alone remains a presentation/lifecycle value, not a concurrency barrier.
- The cleanup is not transactionally atomic across Supabase Storage, Postgres, and Langfuse. The `deleting`
  tombstone and idempotent steps make partial progress recoverable without restoring already-deleted content.
- Student bookshelf, per-job reader/process pages, teacher review, gallery, research metrics, Realtime handling,
  RLS tests, worker lifecycle tests, and data-cleanup tests all enter the implementation blast radius.
- Automated expiry of abandoned `awaiting_confirm` rows, full student/account deletion, retention periods,
  backup expiry, and processor-contract verification remain in the broader `data-deletion` feature. This ADR
  does not silently decide them.

## Alternatives

- **Soft-delete the row and retain data/metrics.** Rejected: it hides rather than erases child-derived content,
  still needs a purge policy, and widens every query and RLS rule while failing the user's plain-language
  expectation of deletion.
- **Delete only the `jobs` row.** Rejected: Storage objects, full StoryMemory checkpoints, and Langfuse traces
  survive as inaccessible orphans.
- **Let the browser delete through RLS.** Rejected: the client cannot atomically authorize and coordinate
  Storage, checkpoint, trace, and row cleanup. It would also reverse the existing server-only write boundary.
- **Permit deletion of queued/running jobs.** Rejected for this feature: no stored RQ identity or cooperative
  cancellation contract exists, so deletion would not stop generation or spend.
- **Give teachers the same per-book delete control.** Rejected: review/reject already handles classroom curation;
  guardian-request erasure must delete the student's complete data set, not let an individual-book button pose as
  that workflow.
- **Keep a metrics-only tombstone.** Rejected: the metrics and trace identifier are still linkable to the deleted
  job, and the research project already has separate consented artifact paths.

## Escape hatch

If measured deletion latency or repeated partial cleanup makes user-triggered retries insufficient, write a new
ADR for a scheduled reaper or durable cleanup queue, including its deployment owner and failure alerting. If the
product later needs true in-flight cancellation, write a separate ADR that stores the RQ identity and defines
cooperative cancellation at every paid/provider boundary. Do not weaken hard deletion or expose direct client
delete policies as an implementation shortcut.
