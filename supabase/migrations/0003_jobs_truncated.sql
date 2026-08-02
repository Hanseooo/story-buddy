-- supabase/migrations/0003_jobs_truncated.sql
-- input-gate-hardening spec: additive, non-breaking nullable-with-default column.
-- Existing rows default to false (nothing was truncated before this column existed).
alter table jobs
  add column if not exists truncated boolean not null default false;
