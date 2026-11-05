-- ADR-082 / magic-pencil ticket 05 (SH-02, OD-03). An unchosen draw is moderated when the child opens
-- it, while the run is paused, so its outcome is stored here, once. Null means not yet checked; a
-- classifier error stores nothing.
begin;
alter table public.job_picture_records
  add column moderation_status text check (moderation_status in ('passed', 'excluded'));
commit;
