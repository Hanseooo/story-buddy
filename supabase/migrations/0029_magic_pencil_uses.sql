-- ADR-082 / magic-pencil ticket 06 (AC-08, AC-22, OD-04). A flagged pencil text is held for the
-- teacher as its own kind; every pencil use is logged in the job-owned record and follows the story.
-- Only redacted text is stored (SH-03). A use with no picture (held, stopped, refused) has no
-- image_path and says why in `reason`.
begin;
alter table public.job_moderation_reviews drop constraint job_moderation_reviews_kind_check;
alter table public.job_moderation_reviews add constraint job_moderation_reviews_kind_check check
  (kind in ('title','story_text','character_reference','scene_image','optional_themes','character_pencil_text'));
alter table public.job_picture_records drop constraint job_picture_records_kind_check;
alter table public.job_picture_records add constraint job_picture_records_kind_check check (kind in ('version','pencil'));
alter table public.job_picture_records
  alter column image_path drop not null,
  add column before_path text,
  add column pencil_text text,
  add column text_moderation text check (text_moderation in ('cleared','held','teacher_allowed','teacher_stopped')),
  add column picture_moderation text check (picture_moderation in ('passed','flagged','teacher_allowed')),
  add column reason text check (reason in ('refused','stale','text_stopped')),
  add column choice text check (choice in ('kept','old')),
  add constraint job_picture_records_version_has_image check (kind <> 'version' or image_path is not null);
commit;
