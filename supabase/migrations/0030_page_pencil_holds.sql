-- ADR-082 / magic-pencil ticket 10 (AC-17, AC-18, OD-07). A page pencil on a finished book holds in
-- job_moderation_reviews as its own kinds while the job stays `complete`. A teacher stop of a held
-- page result ends only that request, recorded in the job-owned log. Apply after 0029.
begin;
alter table public.job_moderation_reviews drop constraint job_moderation_reviews_kind_check;
alter table public.job_moderation_reviews add constraint job_moderation_reviews_kind_check check
  (kind in ('title','story_text','character_reference','scene_image','optional_themes','character_pencil_text',
            'page_pencil_text','page_pencil_result'));
alter table public.job_picture_records drop constraint job_picture_records_reason_check;
alter table public.job_picture_records add constraint job_picture_records_reason_check check
  (reason in ('refused','stale','text_stopped','result_stopped'));
commit;
