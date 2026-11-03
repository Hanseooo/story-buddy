-- ADR-082 / magic-pencil ticket 11 (AC-18, AC-22). A teacher replacement of a held page pencil result
-- re-runs the edit once. The log row keeps the replaced picture here; non-null means the use's one
-- replacement slot is spent. Only a flagged result is replaceable, so a set value also records that
-- the replaced picture was flagged. Apply after 0030.
begin;
alter table public.job_picture_records add column replaced_path text;
commit;
