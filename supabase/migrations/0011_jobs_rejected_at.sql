-- 0011_jobs_rejected_at.sql
-- spec: docs/specs/teacher-review-and-approval.md §4.1, §4.4

-- 1. Add rejected_at and mutual-exclusion constraint
alter table jobs add column rejected_at timestamptz;

alter table jobs add constraint jobs_review_exclusive
  check (approved_at is null or rejected_at is null);

-- 2. Remove the RLS write path that is now replaced by FastAPI
--    Amendments to S1-7 and S3-8 (spec §4.4)
revoke update (approved_at) on public.jobs from authenticated;
drop policy "teachers approve jobs" on public.jobs;
