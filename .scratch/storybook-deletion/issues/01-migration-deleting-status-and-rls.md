# 01 — Migration: `deleting` status, `worker_finished_at`, RLS revocation

**Source spec:** `docs/specs/storybook-deletion.md` §3, §6, §9.1–6
**Implementation plan:** required — write `docs/specs/plans/storybook-deletion-01-migration-rls.md` first, then a lighter agent implements it.
**Blocked by:** None — can start immediately.
**Status:** ready-for-agent

## What to build

The database can represent a storybook that has been accepted for deletion, and the moment a row
enters that state every reader except its owner loses access to it — rows and images alike — without
any browser role gaining the ability to delete anything directly.

The next available migration widens the `jobs.status` check with `deleting`, adds a nullable
`worker_finished_at timestamptz`, and rewrites the read/mutation policies so that acceptance is the
revocation. No `backend/contracts/` field or schema-version change.

Policy changes:

- Owner's own-job SELECT keeps exposing the `deleting` tombstone (deliberate — it is how the child
  observes and retries). Product surfaces render only pending status.
- Peer, teacher and researcher `jobs` SELECT require `status <> 'deleting'`.
- Every `storybook-images` SELECT policy, **including the owner's**, requires the owning job to have
  `status <> 'deleting'`, so no browser role can mint a fresh signed URL after acceptance.
- Teacher approve/reject requires `status <> 'deleting'` in both `USING` and `WITH CHECK`.
- No authenticated or anonymous `DELETE` policy is added to `jobs` or `storage.objects`.

This ticket ships schema and policy only. It does **not** backfill existing rows (see 08) and does
not expose deletion to any user.

## Acceptance criteria

- [ ] `deleting` satisfies the status check; `worker_finished_at` is nullable and defaults null.
- [ ] Owner can SELECT a deleting tombstone but cannot DELETE the row directly.
- [ ] Classmates, teacher and researcher cannot SELECT a deleting job, including an approved one.
- [ ] No student, peer, teacher or researcher can SELECT its Storage objects after the transition.
- [ ] Teacher approve/reject against a deleting row affects zero rows.
- [ ] Existing isolation cases for every non-deleting status remain green.
- [ ] `uv run ruff check . && uv run pytest` green from `backend/`, output shown.

## Notes

`supabase/migrations/` is not self-applying — this ticket is a record of intent. Remote proof is
ticket 09's job; do not claim RLS behavior from migration files alone.
