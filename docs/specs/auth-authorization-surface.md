# Feature Spec — auth: authorization surface

**Status:** draft · **Phase:** 2 · **Owner:** `supabase/migrations/0008_authorization_surface.sql`
**Derived from:** `docs/specs/auth-and-classroom-docket.md` S3 · **Rationale:** ADR-006, ADR-017,
ADR-021, ADR-026, MASTER_SPEC §6 (CC-4)

> Not a schema session and not a session-model session. This spec defines the single migration that
> replaces both existing anon policy surfaces with classroom-scoped RLS, adds the `jobs` ownership
> columns, seals the LangGraph checkpoint tables, and names every Tier-A isolation test. It defines
> **no** schema (S1), **no** session mechanism (S2), and **no** URL or screen (S4).

## 1. Purpose

S1 gave every actor a row and a role. S2 gave every request a named subject. What remains: a policy
for every (role × table × verb) pair, a Storage policy that works despite the frozen path shape, and
the Tier-A tests that turn ADR-017's "classroom isolation is a real, testable boundary" from a
sentence into evidence.

This spec is also the point at which the `jobs` ownership columns land — specified in S1 §4.2 and
deferred here because `NOT NULL` columns on a populated table require deciding what happens to the
pre-auth rows, and that decision belongs to S3.

## 2. Migration `0008_authorization_surface.sql`

S1 claimed `0007`. This migration is `0008`. The two ship together — `0007` enables RLS on
`classrooms` and `profiles` with zero policies (default-deny), and `0008` writes the policies.
Neither is independently deployable.

### 2.1 Execution order inside `0008`

1. **Delete pre-auth rows** — `DELETE FROM jobs`. Rows created under the `dev-classroom` /
   `dev-profile` sentinels have no owner. The `NOT NULL` constraint on the new ownership columns
   cannot be satisfied for them. `0004` established the precedent: "no real child data has entered
   the system yet" (ADR-017), so destruction is correct.
2. **Add ownership columns to `jobs`** — column definitions are frozen in S1 §4.2; `0008`
   transcribes them without re-deriving them.
3. **Drop the two anon policies** — both carry `ponytail:` comments naming this migration:
   ```sql
   drop policy "anon can read jobs by id"    on jobs;
   drop policy "anon can sign storybook images" on storage.objects;
   ```
4. **Write new RLS policies** on `jobs`, `classrooms`, `profiles`, and `storage.objects`.
5. **Enable RLS on checkpoint tables** — no permissive policies. Default-deny for all browser
   clients.

### 2.2 Checkpoint table sequencing invariant

`PostgresSaver.setup()` creates `checkpoints`, `checkpoint_blobs`, and `checkpoint_writes` on first
run. If the worker has never run when `0008` is applied, those tables do not exist and `ALTER TABLE …
ENABLE ROW LEVEL SECURITY` will fail. `0008` must guard:

```sql
do $$ begin
  if exists (select 1 from information_schema.tables where table_name = 'checkpoints') then
    alter table checkpoints       enable row level security;
    alter table checkpoint_blobs  enable row level security;
    alter table checkpoint_writes enable row level security;
  end if;
end $$;
```

In practice the worker runs before any migration after `0007`, but the guard makes this robust.

## 3. `jobs` ownership columns

Transcribed from S1 §4.2 — S3 adds these, not S1:

```sql
alter table jobs
  add column profile_id   uuid not null references profiles(id)   on delete cascade,
  add column classroom_id uuid not null references classrooms(id) on delete cascade,
  add column approved_at  timestamptz;
```

`NOT NULL` is safe after step 1 removes all existing rows.

## 4. Policy matrix

All policies are `to authenticated` unless noted. Anon is denied everything by the absence of any
anon-targeted permissive policy — no explicit `deny` is needed.

### 4.1 `jobs`

**SELECT — students (two policies, both required):**

```sql
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
```

**SELECT — teachers:**

```sql
create policy "teachers read classroom jobs"
  on jobs for select to authenticated
  using (
    auth_role() = 'teacher'
    and exists (
      select 1 from classrooms c
      where c.id = jobs.classroom_id and c.owner_id = auth.uid()
    )
  );
```

**SELECT — researchers:**

```sql
create policy "researchers read approved jobs"
  on jobs for select to authenticated
  using (auth_role() = 'researcher' and approved_at is not null);
```

Researcher read is full-row, no column hiding. `input_text` is pseudonymous story content, not
directly identifying. The `profile_id` link to the child is present; researcher-facing views that
strip it belong to `annotation-surface` (Phase 2.5).

**UPDATE — teachers (approval only):**

```sql
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
```

RLS cannot restrict which columns the teacher updates; the policy gates on classroom ownership only.
`teacher-dashboard` is the sole caller and will only set `approved_at`.

No INSERT policy — `POST /storybooks` uses service_role. No DELETE policy — cascade handles
student and classroom deletion.

### 4.2 `classrooms`

```sql
create policy "students read own classroom"
  on classrooms for select to authenticated
  using (auth_role() = 'student' and id = auth_classroom_id());

create policy "teachers read own classrooms"
  on classrooms for select to authenticated
  using (auth_role() = 'teacher' and owner_id = auth.uid());

create policy "researchers read all classrooms"
  on classrooms for select to authenticated
  using (auth_role() = 'researcher');
```

No INSERT/UPDATE/DELETE policies — classroom creation and management go through FastAPI (service_role).

### 4.3 `profiles`

```sql
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
```

`students read classroom profiles` does not expose the teacher's profile: the teacher's
`profiles.classroom_id` is `NULL`, so `classroom_id = auth_classroom_id()` evaluates to
`NULL = <uuid>` → false. Students see only peer rows.

No INSERT/UPDATE/DELETE — profile creation is trigger-only (service_role via `handle_new_user`);
updates go through FastAPI.

### 4.4 `storage.objects` (bucket: `storybook-images`)

**The concrete finding:** Storage paths are `{job_id}/{scene_id}.png`. There is no classroom
segment in the path, and the path shape is frozen (kid-flow constraints 1 and 13: durable, never
reused). A classroom-scoped policy must therefore join back to `jobs`. `split_part(name, '/', 1)::uuid`
extracts the `job_id`. The join is one hop because `jobs.classroom_id` is denormalized (S1 §3.4).

```sql
create policy "students read own images"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'storybook-images'
    and auth_role() = 'student'
    and exists (
      select 1 from jobs j
      where j.id = split_part(name, '/', 1)::uuid
        and j.profile_id = auth.uid()
    )
  );

create policy "students read approved peer images"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'storybook-images'
    and auth_role() = 'student'
    and exists (
      select 1 from jobs j
      where j.id = split_part(name, '/', 1)::uuid
        and j.classroom_id = auth_classroom_id()
        and j.approved_at is not null
    )
  );

create policy "teachers read classroom images"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'storybook-images'
    and auth_role() = 'teacher'
    and exists (
      select 1 from jobs j
      join classrooms c on c.id = j.classroom_id
      where j.id = split_part(name, '/', 1)::uuid
        and c.owner_id = auth.uid()
    )
  );

create policy "researchers read approved images"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'storybook-images'
    and auth_role() = 'researcher'
    and exists (
      select 1 from jobs j
      where j.id = split_part(name, '/', 1)::uuid
        and j.approved_at is not null
    )
  );
```

`createSignedUrl` calls go through the SELECT policy. `createBrowserClient` (S2) includes the JWT
cookie automatically — no code change needed in the image-rendering path. Anon `createSignedUrl`
calls are denied by the absence of an anon policy.

### 4.5 Checkpoint tables

```sql
do $$ begin
  if exists (select 1 from information_schema.tables where table_name = 'checkpoints') then
    alter table checkpoints       enable row level security;
    alter table checkpoint_blobs  enable row level security;
    alter table checkpoint_writes enable row level security;
  end if;
end $$;
-- No permissive policies. Default-deny for all browser clients.
-- Worker retains service_role and bypasses RLS (S2 §5.4 — deliberate, not inherited).
```

The checkpoint blobs hold the full `StoryMemory` — raw story text, character descriptions, captions.
They must not be accessible to any browser client. The worker's service_role bypass is deliberate
and stated in S2; any future worker entrypoint must also state it explicitly.

## 5. Realtime authorization

`useJob.ts` subscribes to `postgres_changes` on `jobs` filtered by `id=eq.{jobId}`. Supabase
Realtime evaluates the subscriber's SELECT policy against each changed row before broadcasting.

After `0008`, the subscribing student's `students read own jobs` policy (`profile_id = auth.uid()`)
covers rows for their own jobs. `createBrowserClient` includes the JWT cookie in the Realtime
websocket handshake automatically (no code change in `useJob.ts`).

**What changes invisibly:** the anon subscription path is dead after `0008`. Any unauthenticated
subscriber gets no broadcasts. A student watching their own job continues to receive updates.

S3 must verify this with a live integration test (§6, tests 26–27).

## 6. Tier-A isolation tests (CI — MASTER_SPEC §6)

ADR-017 states classroom isolation is "a real, testable boundary." These 33 tests back that claim.
Each one is written so that dropping exactly one policy causes it to fail.

**Test fixture (shared across all 33):**

- Classroom A: teacher TA, students S1 and S2
- Classroom B: teacher TB, student S3
- Researcher R
- Book BA1: authored by S1, **approved** (`approved_at` set)
- Book BA2: authored by S2, **unapproved**
- Book BB1: authored by S3, **approved**
- Storage objects: `{BA1.id}/scene_1.png`, `{BA2.id}/scene_1.png`, `{BB1.id}/scene_1.png`

**`jobs` SELECT:**

1. S1 reads BA1 (own, approved) → **allowed**
2. S1 reads BA2 (classmate, unapproved) as peer → **denied** (no approved_at)
3. S1 reads BA2 as own → **denied** (BA2.profile_id ≠ S1)
4. S1 reads BB1 (approved, different classroom) → **denied**
5. S2 reads BA1 (classmate, approved) → **allowed**
6. TA reads BA1, BA2 (all classroom A books) → **allowed**
7. TA reads BB1 (classroom B) → **denied**
8. TB reads BA1 (classroom A) → **denied**
9. R reads BA1 (approved) → **allowed**
10. R reads BA2 (unapproved) → **denied**
11. Anon reads any job → **denied**

**`jobs` UPDATE:**

12. TA sets `approved_at` on BA2 (own classroom) → **allowed**
13. TA sets `approved_at` on BB1 (classroom B) → **denied**
14. S1 attempts to set `approved_at` on BA1 → **denied** (no student UPDATE policy)

**`classrooms` SELECT:**

15. S1 reads classroom A → **allowed**
16. S1 reads classroom B → **denied**
17. TA reads classroom A → **allowed**
18. TA reads classroom B → **denied**
19. R reads both classrooms → **allowed**

**`profiles` SELECT:**

20. S1 reads own profile → **allowed**
21. S1 reads S2's profile (same classroom) → **allowed**
22. S1 reads TB's profile → **denied** (TB has `classroom_id IS NULL`)
23. S1 reads S3's profile (different classroom) → **denied**
24. TA reads S1 and S2's profiles → **allowed**
25. TA reads S3's profile → **denied**

**Realtime:**

26. S1 subscribes to BA1 (`id=eq.{BA1.id}`), worker updates `status` via service_role → broadcast arrives at S1.
27. S1 subscribes to BA2 (`id=eq.{BA2.id}`), worker updates `status` → **no broadcast** (BA2.profile_id ≠ S1 and BA2 is unapproved, so both student SELECT policies deny it).

**Storage isolation:**

28. S1 calls `createSignedUrl` for `{BA1.id}/scene_1.png` (own book) → **allowed**
29. S2 calls `createSignedUrl` for `{BA1.id}/scene_1.png` (approved peer book) → **allowed**
30. S1 calls `createSignedUrl` for `{BA2.id}/scene_1.png` (unapproved peer) → **denied**
31. S1 calls `createSignedUrl` for `{BB1.id}/scene_1.png` (different classroom) → **denied**
32. TA calls `createSignedUrl` for `{BA1.id}/scene_1.png` → **allowed**
33. TA calls `createSignedUrl` for `{BB1.id}/scene_1.png` → **denied**
34. TA calls `createSignedUrl` for `{BB1.id}/scene_1.png` → **denied**

## 7. Invariants

1. **No anon access exists after `0008`.** The two anon policies are dropped; no new anon policy is
   created. Any future migration adding one must pass the security gate in AGENTS.md §5.
2. **Classroom isolation is transitive.** A student in classroom A cannot reach any data owned by
   classroom B — jobs, profiles, classrooms, or images — through any policy in this spec.
3. **Researcher access is read-only and approved-only on `jobs` and `storage.objects`.** No researcher
   write path exists. Unapproved books are not accessible.
4. **Checkpoint blobs are unreachable from the browser.** Default-deny by construction; no permissive
   policy exists.
5. **The two policy migrations ship together.** `0007` (RLS enabled, zero policies) is non-functional
   alone. `0008` must be applied in the same deploy or `0007` must not be applied at all.
6. **`jobs.classroom_id` cannot disagree with `profiles.classroom_id` for the same author** — because
   students belong to one classroom for life (S1 invariant 3). This is the load-bearing assumption
   behind `auth_classroom_id()` as the classroom selector in student policies.

## 8. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-4 Security (RLS + signed URLs)** — this spec closes CC-4. Both existing permissive
  policies are dropped and replaced by classroom-scoped authenticated policies. Signed URL access
  requires a valid JWT and classroom membership.
- [x] **CC-2 PII** — `input_text` (child's story) is accessible to researchers (full-row, no column
  hiding). Accepted: pseudonymous, no directly identifying fields in `jobs`. Column-level restriction
  (a view omitting `profile_id`) deferred to `annotation-surface` Phase 2.5.
- [ ] CC-1, CC-3, CC-5, CC-6, CC-7, CC-8, CC-9, CC-10 — not touched by this spec.

## 9. Linked decisions & open questions

**Depends on:** S1 (`auth_role()`, `auth_classroom_id()`, schema), S2 (`createBrowserClient`,
JWT-in-cookie, service_role stated as deliberate).

**Blocking:** S4 (`middleware.ts` can now protect routes with the policy surface live).

### Verify before building

**`split_part(name, '/', 1)::uuid` throws, not returns NULL, on a non-UUID value.** If any object
lives at the bucket root (no `/` in `name`) or has a non-UUID first segment, every storage policy
errors rather than evaluates to false. `0008` must either confirm no such objects exist, or guard
the cast:

```sql
-- safe form: skip the subquery entirely when the path has no folder segment
case when name like '%/%'
     then (select 1 from jobs j where j.id = split_part(name, '/', 1)::uuid and …)
     else null end
```

Likely a non-issue (the worker always writes `{job_id}/{scene_id}.png`) but worth one query
against the live bucket before applying the migration.

### Handoff

**→ S4.** The full policy surface is live. `middleware.ts` may now read the session (via
`createServerClient`) and gate routes by role. The student bookshelf query, the `/join` flow, and
the teacher classroom view all build on the SELECT policies here.

**→ `teacher-dashboard`.** The teacher UPDATE policy on `jobs` is in place. The approval workflow
(setting `approved_at`, the review screens, any notification) is entirely that spec's to design.

**→ `data-deletion`.** Storage objects do not cascade on job deletion (S1 C4). Superseded objects
accumulate in the bucket. That spec owns the sweep.

**→ `annotation-surface` (Phase 2.5).** Researcher SELECT on `jobs` and `profiles` is in place.
Column-level restriction (a view omitting `profile_id` for researcher queries) belongs there, not
here.
