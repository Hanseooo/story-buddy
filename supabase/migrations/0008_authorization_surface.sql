-- 0008_authorization_surface.sql
-- spec: docs/specs/auth-authorization-surface.md
-- Ships with 0007. Neither is independently deployable (spec §7 invariant 5).

-- ── 1. Remove pre-auth rows ──────────────────────────────────────────────────
-- All existing jobs rows pre-date ownership columns. The NOT NULL constraint
-- below cannot be satisfied for them. ADR-017: no real child data exists yet.
delete from jobs;

-- ── 2. Add ownership columns to jobs ────────────────────────────────────────
-- Column definitions frozen in S1 §4.2; transcribed here per S3 spec §3.
alter table jobs
  add column profile_id   uuid not null references profiles(id)   on delete cascade,
  add column classroom_id uuid not null references classrooms(id) on delete cascade,
  add column approved_at  timestamptz;

-- ── 3. Drop anon policies ────────────────────────────────────────────────────
-- ponytail: comments in 0001 and 0004 named this migration as the drop site.
drop policy "anon can read jobs by id"       on jobs;
drop policy "anon can sign storybook images" on storage.objects;

-- ── 4. RLS policies — jobs ───────────────────────────────────────────────────

create policy "students read own jobs"
  on jobs for select to authenticated
  using (auth_role() = 'student' and profile_id = auth.uid());

create policy "students read approved peer jobs"
  on jobs for select to authenticated
  using (
    auth_role() = 'student'
    and classroom_id = auth_classroom_id()
    and approved_at is not null
  );

create policy "teachers read classroom jobs"
  on jobs for select to authenticated
  using (
    auth_role() = 'teacher'
    and exists (
      select 1 from classrooms c
      where c.id = jobs.classroom_id and c.owner_id = auth.uid()
    )
  );

create policy "researchers read approved jobs"
  on jobs for select to authenticated
  using (auth_role() = 'researcher' and approved_at is not null);

-- RLS cannot restrict which columns a teacher updates; policy gates on ownership only.
-- The only legitimate caller (teacher-dashboard) will only set approved_at.
create policy "teachers approve jobs"
  on jobs for update to authenticated
  using (
    auth_role() = 'teacher'
    and exists (
      select 1 from classrooms c
      where c.id = jobs.classroom_id and c.owner_id = auth.uid()
    )
  )
  with check (
    auth_role() = 'teacher'
    and exists (
      select 1 from classrooms c
      where c.id = jobs.classroom_id and c.owner_id = auth.uid()
    )
  );

-- ── 5. RLS policies — classrooms ─────────────────────────────────────────────
-- No INSERT/UPDATE/DELETE: classroom management goes through FastAPI (service_role).

create policy "students read own classroom"
  on classrooms for select to authenticated
  using (auth_role() = 'student' and id = auth_classroom_id());

create policy "teachers read own classrooms"
  on classrooms for select to authenticated
  using (auth_role() = 'teacher' and owner_id = auth.uid());

create policy "researchers read all classrooms"
  on classrooms for select to authenticated
  using (auth_role() = 'researcher');

-- ── 6. RLS policies — profiles ───────────────────────────────────────────────
-- No INSERT/UPDATE/DELETE: profile creation is trigger-only; updates go through FastAPI.
-- Teacher's classroom_id IS NULL → 'students read classroom profiles' evaluates to
-- NULL = <uuid> → false, so teachers are invisible to students (spec §4.3).

create policy "students read own profile"
  on profiles for select to authenticated
  using (auth_role() = 'student' and id = auth.uid());

create policy "students read classroom profiles"
  on profiles for select to authenticated
  using (auth_role() = 'student' and classroom_id = auth_classroom_id());

create policy "teachers read own profile"
  on profiles for select to authenticated
  using (auth_role() = 'teacher' and id = auth.uid());

create policy "teachers read classroom profiles"
  on profiles for select to authenticated
  using (
    auth_role() = 'teacher'
    and exists (
      select 1 from classrooms c
      where c.id = profiles.classroom_id and c.owner_id = auth.uid()
    )
  );

create policy "researchers read all profiles"
  on profiles for select to authenticated
  using (auth_role() = 'researcher');

-- ── 7. RLS policies — storage.objects (bucket: storybook-images) ─────────────
-- Path shape: {job_id}/{scene_id}.png — the first segment is always a job UUID.
-- Safe cast: skip the subquery when name has no '/' to avoid a cast error on
-- root-level objects (spec §9 open question). Anon is denied by absence of policy.

create policy "students read own images"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'storybook-images'
    and auth_role() = 'student'
    and case when name like '%/%' then exists (
      select 1 from jobs j
      where j.id = split_part(name, '/', 1)::uuid
        and j.profile_id = auth.uid()
    ) else false end
  );

create policy "students read approved peer images"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'storybook-images'
    and auth_role() = 'student'
    and case when name like '%/%' then exists (
      select 1 from jobs j
      where j.id = split_part(name, '/', 1)::uuid
        and j.classroom_id = auth_classroom_id()
        and j.approved_at is not null
    ) else false end
  );

create policy "teachers read classroom images"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'storybook-images'
    and auth_role() = 'teacher'
    and case when name like '%/%' then exists (
      select 1 from jobs j
      join classrooms c on c.id = j.classroom_id
      where j.id = split_part(objects.name, '/', 1)::uuid
        and c.owner_id = auth.uid()
    ) else false end
  );

create policy "researchers read approved images"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'storybook-images'
    and auth_role() = 'researcher'
    and case when name like '%/%' then exists (
      select 1 from jobs j
      where j.id = split_part(name, '/', 1)::uuid
        and j.approved_at is not null
    ) else false end
  );

-- ── 8. Checkpoint tables — default-deny ──────────────────────────────────────
-- PostgresSaver.setup() creates these on first worker run. Guard against them
-- not existing when this migration runs (spec §2.2).
-- No permissive policies. Worker retains service_role and bypasses RLS (S2 §5.4).
do $$ begin
  if exists (select 1 from information_schema.tables where table_name = 'checkpoints') then
    alter table checkpoints       enable row level security;
    alter table checkpoint_blobs  enable row level security;
    alter table checkpoint_writes enable row level security;
  end if;
end $$;
