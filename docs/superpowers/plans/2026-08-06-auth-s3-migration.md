# Auth Authorization Surface — Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write and apply `0008_authorization_surface.sql` — delete pre-auth rows, add ownership columns to `jobs`, drop both anon policies, write classroom-scoped RLS on `jobs` / `classrooms` / `profiles` / `storage.objects`, and enable default-deny RLS on checkpoint tables.

**Architecture:** Single SQL migration. `0007` already enables RLS on `classrooms` and `profiles` with zero policies (default-deny). `0008` writes all policies. Both ship together — neither is independently deployable. Execution order is fixed by the spec (§2.1): delete rows → add columns → drop anon policies → write new policies → seal checkpoints.

**Tech Stack:** PostgreSQL (Supabase), SQL, Supabase CLI.

## Global Constraints

- Migration number is `0008` — never `0007` (already taken)
- Must ship with `0007` in the same deploy (spec §7 invariant 5)
- Execution order in `0008` is spec §2.1 — do not reorder
- Storage policies use the safe cast form: `case when name like '%/%' then … else false end` to prevent `split_part(…)::uuid` throwing on root-level objects (spec §9)
- `jobs.classroom_id` is denormalized (S1 §3.4) — storage policies join `storage.objects → jobs` directly, never through `profiles`
- No new SQL functions — `auth_role()`, `auth_classroom_id()`, `auth.uid()` are already defined in `0007`
- Policy names are exact strings — the Tier-A test suite references them by name (Plan 2)
- `DELETE FROM jobs` runs before the `NOT NULL` column additions — existing rows have no owner, destruction is correct (ADR-017)

---

## File Map

| File | Change |
|---|---|
| `supabase/migrations/0008_authorization_surface.sql` | **Create** — full policy migration |

---

### Task 1: Migration `0008_authorization_surface.sql`

**Files:**
- Create: `supabase/migrations/0008_authorization_surface.sql`

**Interfaces:**
- Consumes: `auth_role()`, `auth_classroom_id()`, `auth.uid()` (defined in `0007`); tables `jobs`, `classrooms`, `profiles`, `storage.objects` (bucket `storybook-images` from `0001`)
- Produces: columns `jobs.profile_id`, `jobs.classroom_id`, `jobs.approved_at`; 13 RLS policies on public tables; 4 RLS policies on `storage.objects`; default-deny on checkpoint tables when they exist

- [ ] **Step 1: Verify green baseline**

```bash
cd backend && uv run pytest
cd frontend && pnpm test
```

Expected: all pass. Fix any red before continuing.

- [ ] **Step 2: Create the migration file**

Create `supabase/migrations/0008_authorization_surface.sql` with this exact content:

```sql
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
      where j.id = split_part(name, '/', 1)::uuid
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
```

- [ ] **Step 3: Verify no root-level storage objects (spec §9 open question)**

The storage policies use `split_part(name, '/', 1)::uuid`. On a non-UUID first segment this
*throws* rather than returning NULL (spec §9). The safe-cast form in the migration handles this,
but confirm no such objects exist in the production bucket before deploying.

Run against the local DB (to verify the local bucket) and against production Supabase SQL editor:

```sql
select name from storage.objects
where bucket_id = 'storybook-images'
  and name not like '%/%';
```

Expected: 0 rows. If any rows appear, do not apply the migration until the storage team removes or
renames them — the safe-cast form will silently deny them rather than error, but it's worth knowing.

- [ ] **Step 4: Apply the migration locally**

```bash
supabase db push
```

Expected: migration exits 0 with no errors.

**If** `policy "anon can read jobs by id" does not exist` → the local DB is missing `0001`; run `supabase db reset` to replay all migrations from scratch.

**If** `column "profile_id" of relation "jobs" already exists` → `0008` was partially applied previously; run `supabase db reset`.

- [ ] **Step 5: Verify policies exist**

Connect to the local DB and run:

```sql
select policyname, tablename
from pg_policies
where schemaname in ('public', 'storage')
order by tablename, policyname;
```

Expected — 17 policy rows total:

| tablename | policyname |
|---|---|
| classrooms | researchers read all classrooms |
| classrooms | students read own classroom |
| classrooms | teachers read own classrooms |
| jobs | researchers read approved jobs |
| jobs | students read approved peer jobs |
| jobs | students read own jobs |
| jobs | teachers approve jobs |
| jobs | teachers read classroom jobs |
| objects | researchers read approved images |
| objects | students read approved peer images |
| objects | students read own images |
| objects | teachers read classroom images |
| profiles | researchers read all profiles |
| profiles | students read classroom profiles |
| profiles | students read own profile |
| profiles | teachers read classroom profiles |
| profiles | teachers read own profile |

- [ ] **Step 6: Verify jobs ownership columns**

```sql
select column_name, data_type, is_nullable
from information_schema.columns
where table_name = 'jobs'
  and column_name in ('profile_id', 'classroom_id', 'approved_at')
order by column_name;
```

Expected: 3 rows. `classroom_id` and `profile_id` are `uuid` / `NO`. `approved_at` is `timestamp with time zone` / `YES`.

- [ ] **Step 7: Commit**

```bash
git add supabase/migrations/0008_authorization_surface.sql
git commit -m "feat(auth-s3): migration 0008 — ownership columns, drop anon, classroom-scoped RLS"
```
