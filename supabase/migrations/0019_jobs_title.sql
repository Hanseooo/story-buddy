-- supabase/migrations/0019_jobs_title.sql
-- docs/specs/story-titles.md; ADR-059 Decision 1/5.
-- Nullable: existing rows stay NULL, no backfill. Only `create_storybook` (backend/app/main.py)
-- ever writes this column — there is no PATCH/update endpoint for it, which is how ADR-059
-- Decision 5 enforces immutability. 1-80 char / no-newline validation lives in
-- CreateStorybookRequest, not a DB constraint: the checked/redacted value is computed in Python
-- before the insert, so a DB-level CHECK would duplicate that logic against a value the API has
-- already guaranteed.
alter table jobs
  add column if not exists title text;
