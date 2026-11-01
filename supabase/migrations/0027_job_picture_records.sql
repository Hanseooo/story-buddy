-- ADR-082 / magic-pencil OD-04, ticket 04. Job-owned record of kept pictures; later tickets add
-- pencil-use rows. The checkpoint stays the pipeline's source of truth; this record follows the story.
begin;
create table public.job_picture_records (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs(id) on delete cascade,
  kind text not null check (kind in ('version')),
  target_id text not null,
  version_id text not null,
  image_path text not null,
  source text not null,
  created_at timestamptz not null default clock_timestamp(),
  unique (job_id, kind, version_id)
);
alter table public.job_picture_records enable row level security;
revoke all on public.job_picture_records from public, anon, authenticated;
grant all on public.job_picture_records to service_role;
commit;
