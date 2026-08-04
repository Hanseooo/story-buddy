-- supabase/migrations/0004_jobs_pages.sql
-- kid-flow-book-persistence spec: a finished book is a `pages` array, not one scene.
alter table jobs
  add column if not exists pages jsonb not null default '[]';

alter table jobs
  drop column if exists caption,
  drop column if exists image_path;
-- No backfill: dropping caption/image_path destroys the only page data on old `complete` rows,
-- which is acceptable — ADR-017 means no real child data has entered the system yet (spec §4.7).

-- ponytail: no CHECK enforcing pages non-empty when status='complete'. Atomicity of the single
-- terminal UPDATE in run_job.py is the actual guarantee (spec §5) — a CHECK would guard a second
-- writer that does not exist. Add it as the upgrade path if a second writer ever appears.

-- The bucket is private and no storage.objects policy exists anywhere in this migrations
-- directory. The backend signs with the service-role key, but the frontend reader signs from the
-- browser with the anon key — that call cannot succeed without this policy.
create policy "anon can sign storybook images"
  on storage.objects for select
  to anon
  using (bucket_id = 'storybook-images');
-- ponytail: Phase 2 `auth-and-classroom` migration must DROP this policy and replace it with
-- classroom-scoped RLS on an auth'd role — same rule as 0001:22-23.
