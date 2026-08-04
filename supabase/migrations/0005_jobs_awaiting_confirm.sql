-- supabase/migrations/0005_jobs_awaiting_confirm.sql
-- kid-flow-pause-lifecycle spec: a job waiting on a human is not `running` — it needs its own
-- status value, not a boolean beside it (spec §4.8), and the reveal projection needs a home.
alter table jobs
  drop constraint if exists jobs_status_check;

alter table jobs
  add constraint jobs_status_check
  check (status in ('queued', 'running', 'awaiting_confirm', 'complete', 'failed'));

alter table jobs
  add column if not exists reveal jsonb not null default '{}';
-- `reveal` inherits 0001's `for select to anon using (true)` policy on `jobs` — no third policy
-- surface is created (spec §6). It stays on the row after the book completes, deliberately: every
-- consumer switches on `status`, never on the presence of `reveal` (spec §4.8).
