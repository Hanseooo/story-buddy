# 09 — Live Supabase verification and spec close-out

**Source spec:** `docs/specs/storybook-deletion.md` §10, §14
**Implementation plan:** not required — execute the checklist directly.
**Blocked by:** 05, 06, 07, 08
**Status:** ready-for-agent

## What to build

Proof, against a real non-production Supabase project, that the deletion feature actually behaves as
the migrations and mocked tests claim — because migrations here are hand-applied and local tests
cannot prove remote project state.

Run against disposable rows and assets only. **Never against real child, study or production data.**

1. Rehearse the stopped-worker/drained-queue cutover; prove legacy terminal rows are backfilled while
   legacy/injected non-quiescent rows are not.
2. Apply the generated migration; confirm its entry plus the status constraint and column definitions.
3. Seed two classrooms; child, peer, teacher and researcher users; one approved quiescent job; nested
   test objects under its exact UUID prefix; and a sibling prefix.
4. Prove the RLS matrix with real JWTs and prove no direct DELETE policy exists.
5. Accept deletion through FastAPI; prove browser Storage signing fails immediately for every role.
6. Run cleanup; verify the job row, the exact Storage prefix, the checkpoint thread and the test
   Langfuse trace are absent while the sibling prefix and separate research rows/assets remain.
7. Repeat DELETE/cleanup around each injected partial failure and each concurrent duplicate attempt;
   confirm eventual convergence.
8. Record backup, CDN/cache, Supabase, Langfuse and model-provider retention statements — feeds
   ticket 10.

Close-out: flip `docs/specs/storybook-deletion.md` to `built` and delete the disposable
implementation plans under `docs/specs/plans/`.

## Acceptance criteria

- [ ] All eight steps executed against a non-production project, with actual output recorded.
- [ ] All four active stores proven empty for a disposable live job; sibling and research data survive.
- [ ] Retry converges after failure at any cleanup step; the row is always removed last.
- [ ] Backend and frontend pre-merge verification green, output shown.
- [ ] Spec status is `built`; disposable plans deleted.
