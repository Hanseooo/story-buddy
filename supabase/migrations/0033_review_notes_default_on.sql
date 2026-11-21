-- ADR-081 amendment (owner, 2026-11-21): student notes are on by default.
-- New classrooms start on. Existing classrooms are switched on once; a teacher can still turn them off.
begin;
alter table public.classrooms alter column review_notes_enabled set default true;
update public.classrooms set review_notes_enabled = true where review_notes_enabled = false;
commit;
