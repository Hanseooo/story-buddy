-- ADR-080 / moderation-stack §9.9, ticket 05. Apply before enabling intake.
begin;
alter table public.jobs
  add column moderation_mode text not null default 'baseline'
    check (moderation_mode in ('baseline', 'teacher_review_v1')),
  add column moderation_settings_snapshot jsonb not null default '{}'::jsonb,
  add column generation_epoch bigint not null default 0 check (generation_epoch >= 0),
  add column worker_finished_at timestamptz;
alter table public.jobs drop constraint jobs_status_check;
alter table public.jobs add constraint jobs_status_check check
  (status in ('queued', 'running', 'awaiting_confirm', 'awaiting_teacher', 'complete', 'failed', 'stopped', 'deleting'));
-- No historical marker backfill: elapsed time does not prove quiescence (ADR-044).

create table public.job_moderation_reviews (
  id uuid primary key,
  job_id uuid not null references public.jobs(id) on delete cascade,
  kind text not null check (kind in ('title','story_text','character_reference','scene_image','optional_themes')),
  subject_id text not null,
  subject_version text not null,
  subject jsonb not null,
  criteria text[] not null default '{}',
  policy_version text not null,
  settings_snapshot jsonb not null,
  classifier_evidence jsonb not null,
  checkpoint_id text,
  return_node text not null,
  created_at timestamptz not null default now(),
  withdraws_review_id uuid references public.job_moderation_reviews(id),
  decision text check (decision in ('allow','replace','stop')),
  actor_id uuid references public.profiles(id),
  decided_at timestamptz,
  decision_policy_version text,
  confirmed_criteria text[],
  request_id uuid,
  decision_epoch bigint,
  dispatch_state text check (dispatch_state in ('pending','queued','consumed','failed')),
  dispatch_kind text check (dispatch_kind in ('resume','anchor_withdrawal')),
  dispatch_error_code text,
  unique (job_id, request_id)
);
create unique index job_moderation_one_open on public.job_moderation_reviews(job_id) where decision is null;
alter table public.job_moderation_reviews enable row level security;
revoke all on public.job_moderation_reviews from public, anon, authenticated;
grant all on public.job_moderation_reviews to service_role;

create function public.protect_moderation_review() returns trigger
language plpgsql set search_path = '' as $$
declare mutable_fields text[] := array['decision','actor_id','decided_at','decision_policy_version',
  'confirmed_criteria','request_id','decision_epoch','dispatch_state','dispatch_kind','dispatch_error_code'];
begin
  if (to_jsonb(new) - mutable_fields) is distinct from (to_jsonb(old) - mutable_fields)
     or (old.decision is not null and
       (to_jsonb(new) - array['dispatch_state','dispatch_error_code']) is distinct from
       (to_jsonb(old) - array['dispatch_state','dispatch_error_code'])) then
    raise exception 'moderation review is immutable';
  end if;
  return new;
end $$;
revoke all on function public.protect_moderation_review() from public, anon, authenticated;
create trigger protect_moderation_review before update on public.job_moderation_reviews
  for each row execute function public.protect_moderation_review();

-- Restrictive AND applies alongside every permissive policy, including researcher ones.
-- Text comparison avoids a UUID cast on untrusted object names. Invisible jobs deny too.
create policy "feature images require guarded delivery" on storage.objects
  as restrictive for select to anon, authenticated using (
    bucket_id <> 'storybook-images' or exists (
      select 1 from public.jobs j where j.id::text = split_part(objects.name, '/', 1)
        and j.moderation_mode = 'baseline'
    )
  );
alter policy "students read own images" on storage.objects using (
  bucket_id = 'storybook-images' and public.auth_role() = 'student' and exists (
    select 1 from public.jobs j where j.id::text = split_part(objects.name, '/', 1) and j.profile_id = auth.uid()
  )
);
alter policy "students read approved peer images" on storage.objects using (
  bucket_id = 'storybook-images' and public.auth_role() = 'student' and exists (
    select 1 from public.jobs j where j.id::text = split_part(objects.name, '/', 1)
      and j.classroom_id = public.auth_classroom_id() and j.approved_at is not null
  )
);
alter policy "teachers read classroom images" on storage.objects using (
  bucket_id = 'storybook-images' and public.auth_role() = 'teacher' and exists (
    select 1 from public.jobs j join public.classrooms c on c.id = j.classroom_id
    where j.id::text = split_part(objects.name, '/', 1) and c.owner_id = auth.uid()
  )
);
alter policy "researchers read approved images" on storage.objects using (
  bucket_id = 'storybook-images' and public.auth_role() = 'researcher' and exists (
    select 1 from public.jobs j where j.id::text = split_part(objects.name, '/', 1) and j.approved_at is not null
  )
);
commit;
