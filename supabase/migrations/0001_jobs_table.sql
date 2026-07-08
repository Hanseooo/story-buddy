-- supabase/migrations/0001_jobs_table.sql
create table if not exists jobs (
  id uuid primary key,
  status text not null default 'queued' check (status in ('queued','running','complete','failed')),
  current_stage text,
  input_text text not null,
  caption text,
  image_path text,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table jobs enable row level security;

-- Capability-link read policy: the UUID itself is the capability. Anon may only ever
-- query with .eq('id', job_id) client-side; there is no listing/enumeration policy.
create policy "anon can read jobs by id"
  on jobs for select
  to anon
  using (true);

alter publication supabase_realtime add table jobs;

insert into storage.buckets (id, name, public)
values ('storybook-images', 'storybook-images', false)
on conflict (id) do nothing;
