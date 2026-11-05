-- ADR-082 / magic-pencil code review (2026-11-03, SH-09). A child's page change on a finished book
-- (a version choice or a kept page pencil result) is recorded as one `kind='page'` row per scene, so a
-- teacher withdrawal that rebuilds `jobs.pages` from the checkpoint can put it back. On these rows
-- `before_path` is the checkpoint's picture of that page when the change was made: the change is
-- restored only on a page the rerun did not redraw. Apply after 0031.
begin;
alter table public.job_picture_records drop constraint job_picture_records_kind_check;
alter table public.job_picture_records add constraint job_picture_records_kind_check
  check (kind in ('version','pencil','page'));
commit;
