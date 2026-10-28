-- ADR-080 / moderation-stack §9.9.7, ticket 14. Synthetic-only, feature off.
begin;
alter table public.classrooms
  add column moderation_theme_ids text[] not null default '{}'
    check (moderation_theme_ids <@ array['spooky_suspense','story_conflict','loss_separation']::text[]
      and array_position(moderation_theme_ids, null) is null),
  add column moderation_settings_version bigint not null default 0
    check (moderation_settings_version >= 0);

-- 0008's classroom RLS already permits browser SELECT only. All classroom writes
-- remain server-only. No new browser grant or policy is needed for these fields.
commit;
