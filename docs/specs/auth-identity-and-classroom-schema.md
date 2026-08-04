# Feature Spec — auth: identity, roles & classroom schema

**Status:** draft · **Phase:** 2 · **Owner:** `supabase/migrations/0007_identity_and_classrooms.sql`,
`backend/app/config.py`, `backend/worker/run_job.py`
**Derived from:** `docs/specs/auth-and-classroom-docket.md` S1 · **Rationale:** ADR-006, ADR-017,
ADR-021, ADR-026, MASTER_SPEC §6 (CC-4)

> Not a pipeline node. This spec defines what rows exist, how a role is represented, and where a
> student's password lives. It defines **no** authentication mechanism (S2), **no** policy text (S3),
> and **no** URL or screen (S4).

## 1. Purpose

ADR-017 describes teacher-issued classrooms and child-held student accounts. The database has
neither: there is no user table, no classroom table, and no column on `jobs` naming an owner.
`config.py:19-20`'s `dev-classroom` / `dev-profile` sentinels stand in for the whole identity layer.

This spec gives every actor a row, gives the role a single representation that S3 writes policies
against, and gives `jobs` an owner — far enough that S2 can name a subject and S3 can scope a policy.

## 2. Contract slice

`backend/contracts/` is **unchanged**. `StoryMemory` already declares `classroom_id: str` and
`profile_id: str` (`story_memory.py:171-172`) as required with no default. Those fields stop being
fed sentinels and start being fed real UUID strings. No field is added, no `schema_version` bump.

That the contract requires both fields, non-null, is the reason `jobs.profile_id` and
`jobs.classroom_id` are `NOT NULL` in §4.2 — a nullable column would need a sentinel to survive
Pydantic validation, and the sentinel is precisely what retires.

## 3. Decisions

Five decisions, confirmed with the user 2026-08-04. Each names what it costs.

### 3.1 A student is a real `auth.users` row, reached by a synthetic email

Supabase Auth owns all password material. The project stores none, so AGENTS.md §5 (Security) is
satisfied by construction rather than by care, and no ADR is forced.

The classroom-code + nickname pair maps to a non-deliverable address:

```
juan-dela-cruz@k4m7pq.students.storybuddy.invalid
└── nickname ──┘ └ code ┘
```

The code sits in the **domain**, not the localpart, so `auth.users.email`'s global uniqueness
enforces nickname uniqueness **per classroom** — exactly ADR-017's semantics, at no cost.

`.invalid` is RFC-2606 reserved and can never resolve. Combined with `email_confirm: true` at
creation, no mail is ever addressed or dispatched. **No child email is collected, required, or
deliverable**, and ADR-017's "password reset is teacher-initiated only" stops being a rule that must
be enforced and becomes a fact that cannot be violated: there is no inbox to recover to.

*Rejected:* a project-owned `students` table with a project-owned password hash. It puts credential
material in the project (AGENTS.md §5), removes `auth.uid()` for students so S3 cannot write a
student policy in the ordinary way, and forces S2 to mint a token Supabase Realtime will accept —
which in practice means signing with the Supabase JWT secret anyway. *Also rejected:* teachers in
`auth.users` with students custom — two substrates means S3 writes every `jobs` policy twice, which
is the parallel structure AGENTS.md bans.

**Accepted cost:** the child's nickname is stored in `auth.users.email` in cleartext. This is not a
new disclosure — the nickname is already peer-visible by design in the ADR-021 gallery — but it is a
new location for it. The alternative (an opaque localpart plus an unauthenticated
`(code, nickname) → address` lookup) puts a queryable classroom roster behind a public endpoint,
which is a worse privacy outcome than the one it avoids.

### 3.2 The role is a column on `profiles`, read through a `security definer` helper

`profiles.role` is the single source of truth for all three of `teacher`, `student` and `researcher`.
Policies read it through `public.auth_role()`. A revoked role takes effect on the next query, not
the next token refresh.

*Rejected:* `app_metadata` as a JWT claim. Faster, and the pattern Supabase documents for scale, but
it creates a second source of truth, needs an access-token hook, and leaves a role change stale until
the token refreshes — so revoking a researcher's access would not be immediate, which is the one case
where immediacy matters. At N ≈ 8–15 the performance argument is noise. *Also rejected:* column plus
mirrored claim — buys unneeded performance and adds silent drift, where a policy reading a stale claim
grants access the table says was revoked.

`app_metadata` **is** used at creation time, as transport into the trigger in §4.3. It is never read
by a policy.

### 3.3 The classroom code is immutable

Six characters from a 31-symbol alphabet — lowercase `a–z` and digits, minus the ambiguous
`0 O 1 I l` — giving `31^6 ≈ 8.9 × 10^8`. DNS-label-safe because it is part of a domain, and free of
character pairs a 10-year-old confuses.

It is minted once at classroom creation and never regenerated. **Regenerating it would invalidate the
login address of every student in the classroom**, requiring N admin-API email rewrites with no
transaction spanning them — a partial failure leaves some children unable to log in at all, with no
signal to the teacher.

This is safe because **the code is not a credential**. Login is a single `signInWithPassword` with no
prior lookup, so a guessed code yields nothing without also guessing a nickname and a password,
against Supabase's sign-in rate limiter. The code selects a namespace; it does not grant access.

*Rejected:* an immutable internal slug plus a rotatable teacher-visible join code. It works, but
reintroduces the unauthenticated lookup §3.1 eliminated and creates two identifiers per classroom that
can be confused in every screen and support conversation.

**Accepted cost:** a teacher whose code leaked to another class has no remedy but a new classroom and
re-issued accounts.

### 3.4 `jobs` ownership is a cascading foreign key

`jobs.profile_id` and `jobs.classroom_id` are both `NOT NULL` and both `references … on delete
cascade`. Deleting a student deletes their books; deleting a classroom deletes everything in it.
Deletion actually deletes, which is the correct default for a product holding minors' data under the
PH Data Privacy Act, and no job can reference an owner that does not exist.
`0004_jobs_pages.sql` set the precedent for destroying data on this reasoning.

`classroom_id` is carried on `jobs` directly rather than reached through `profiles`. This is
deliberate and is a gift to S3: the Storage-path finding means a `storage.objects` policy must join
back to `jobs`, and with `classroom_id` present that is one hop instead of two.

*Rejected:* `ON DELETE RESTRICT` — makes "delete this child's data", a right the consent regime must
honour, into a multi-step flow that has to be built before it can be exercised. *Also rejected:*
snapshot values with no FK — leaves a deleted child's books readable by classroom-scoped policies.

**Accepted cost:** an accidental student deletion is unrecoverable, so S4 owes a real confirmation
step. Storage objects do **not** cascade (§7).

### 3.5 The approval bit is `jobs.approved_at timestamptz`

Nullable. `null` means not peer-visible. S3 scopes the gallery with `approved_at is not null`. It
carries *when* approval happened at no extra cost, which the ethics record wants given ADR-017 makes
manual review a safety layer rather than a preference.

It deliberately cannot distinguish "rejected" from "not yet reviewed". The review workflow is
`teacher-dashboard`'s to design, and a state set frozen into a migration before those screens exist is
the retrofit this docket was cut to avoid.

## 4. The schema

### 4.1 Migration `0007_identity_and_classrooms.sql` — claimed by this spec

```sql
create table classrooms (
  id         uuid primary key default gen_random_uuid(),
  code       text not null unique,
  name       text not null,
  owner_id   uuid not null,              -- FK added below, after profiles exists
  created_at timestamptz not null default now()
);

create table profiles (
  id               uuid primary key references auth.users(id) on delete cascade,
  role             text not null check (role in ('teacher','student','researcher')),
  classroom_id     uuid references classrooms(id) on delete cascade,
  nickname         text,   -- students only; normalized; IS the email localpart
  display_nickname text,   -- students only; what the teacher typed, what peers see
  display_name     text,   -- teachers and researchers
  created_at       timestamptz not null default now(),
  constraint profiles_role_shape check (
    (role = 'student'
       and classroom_id is not null and nickname is not null
       and display_nickname is not null and display_name is null)
    or
    (role in ('teacher','researcher')
       and classroom_id is null and nickname is null
       and display_nickname is null and display_name is not null)
  )
);

alter table classrooms
  add constraint classrooms_owner_fk
  foreign key (owner_id) references profiles(id) on delete cascade;

create unique index profiles_classroom_nickname
  on profiles (classroom_id, nickname) where role = 'student';

alter table classrooms enable row level security;
alter table profiles   enable row level security;
-- ponytail: no policies here. Default-deny is correct until S3 writes them; the policy migration
-- and this one ship together (§7 ⑤). Adding a permissive stopgap would create a third policy
-- surface, which the kid-flow docket's constraints exist to prevent.
```

Two columns hold the nickname because they answer different questions. `nickname` is the normalized
form and **is** the email localpart, so it must be reproducible from what a child types at login.
`display_nickname` is `Juan`, which is what a classmate sees. Storing only the normalized form would
put `juan-dela-cruz` on screen.

The unique index is redundant with `auth.users.email`'s uniqueness. It is kept because it makes the
invariant local and checkable rather than an emergent side effect of string construction — one line,
on a child-safety path.

`classrooms.owner_id` and `profiles.classroom_id` reference each other, hence the deferred FK.
Cascades still terminate: deleting a teacher deletes their classrooms, which deletes the students in
them.

### 4.2 The `jobs` change — specified here, executed by S3

S1 claims `0007`. The `jobs` ALTER belongs to S3's policy migration because it **cannot land without
deciding what happens to pre-auth rows**, and the docket assigns that decision to S3. The column
definitions are frozen here; S3 transcribes them rather than re-deriving them.

```sql
alter table jobs
  add column profile_id   uuid not null references profiles(id)   on delete cascade,
  add column classroom_id uuid not null references classrooms(id) on delete cascade,
  add column approved_at  timestamptz;
```

`NOT NULL` on a populated table requires S3 to first dispose of the rows created under the sentinels,
which own nothing.

### 4.3 Triggers

**Creation is atomic.** The profile lands in the same transaction as the `auth.users` row, so no
window exists in which an auth user has no profile.

```sql
create function public.handle_new_user() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, role, classroom_id, nickname, display_nickname, display_name)
  values (new.id,
          new.raw_app_meta_data ->> 'role',
          (new.raw_app_meta_data ->> 'classroom_id')::uuid,
          new.raw_app_meta_data ->> 'nickname',
          new.raw_app_meta_data ->> 'display_nickname',
          new.raw_app_meta_data ->> 'display_name');
  return new;
end $$;

create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();
```

`app_metadata` is used, not `user_metadata`: it is not user-writable, so a student cannot later call
`updateUser` and alter the values their profile was built from. It is transport only — §3.2 stands.

**Deletion closes both directions.** Without this, deleting a classroom deletes `profiles` rows and
leaves the `auth.users` rows behind — live credentials that still authenticate into a session where
`current_role()` is null and every policy denies, so the child sees an empty screen instead of a
login error.

```sql
create function public.handle_profile_deleted() returns trigger
  language plpgsql security definer set search_path = '' as $$
begin
  delete from auth.users where id = old.id;
  return old;
end $$;

create trigger on_profile_deleted after delete on public.profiles
  for each row execute function public.handle_profile_deleted();
```

Not infinitely recursive: when the delete originates at `auth.users`, that row is already gone within
the same command, so the nested delete affects zero rows.

### 4.4 Helper functions — the subject S3 writes policies against

```sql
create function public.auth_role() returns text
  language sql stable security definer set search_path = ''
  as $$ select role from public.profiles where id = auth.uid() $$;

create function public.auth_classroom_id() returns uuid
  language sql stable security definer set search_path = ''
  as $$ select classroom_id from public.profiles where id = auth.uid() $$;
```

`security definer` is required, not preferred: a policy on `profiles` that reads `profiles` recurses
infinitely, and the definer function is the standard break in that loop.

**Not named `current_role`.** `CURRENT_ROLE` is a reserved SQL keyword that Postgres parses specially
and that already returns the session role; a `public.current_role()` would shadow it ambiguously at
every call site. `auth_` is also the prefix S3's policies will read, matching `auth.uid()`.

## 5. Nickname normalization

The function that turns what a teacher types into the email localpart. It runs at account creation
and again at login, and **if the two implementations drift, children stop being able to log in.**

1. Unicode NFKD; strip combining marks (`Niño` → `Nino`, `José` → `Jose`)
2. Lowercase; trim; collapse internal whitespace runs to a single hyphen
3. Collapse repeated hyphens; strip leading and trailing hyphens
4. **Reject** if any character outside `[a-z0-9-]` survives, or the result is under 2 or over 32
   characters

Rejection happens when the **teacher** creates the account, never when the **child** logs in. A
nickname containing an emoji fails on the teacher's screen with a fixable message, rather than
becoming a child who cannot log in and does not know why.

### 5.1 Frozen test vectors

The function exists twice — Python composes the address at creation, TypeScript composes it at login.
**Both test suites assert against this table**, transcribed into each. It is duplicated deliberately
and visibly; a shared fixture loader would be more machinery than fourteen rows are worth.

| Input | Output |
|---|---|
| `Juan` | `juan` |
| `MARIA` | `maria` |
| `Ana Mae` | `ana-mae` |
| `  Juan  Dela   Cruz ` | `juan-dela-cruz` |
| `Niño` | `nino` |
| `José-María` | `jose-maria` |
| `Kim  -  Lee` | `kim-lee` |
| `--Jun--` | `jun` |
| `R2D2` | `r2d2` |
| `Juan!` | **reject** — illegal character survives |
| `J` | **reject** — under 2 characters |
| 33 × `a` | **reject** — over 32 characters |
| `😀` | **reject** — normalizes to empty |
| `ᜃᜌ` (Baybayin) | **reject** — normalizes to empty |

## 6. Behavior

### 6.1 The four credential operations

Every one is a Supabase Auth call. Nothing here is built.

| Operation | Mechanism |
|---|---|
| Teacher creates a student | `auth.admin.createUser({email, password, email_confirm: true, app_metadata})` |
| Child logs in | normalize nickname → compose address → `signInWithPassword` |
| Child changes their password | `auth.updateUser({password})` |
| Teacher resets a student's password | `auth.admin.updateUserById(id, {password})` |

Password change is **optional** per ADR-017 — no forced rotation at first login, and no
"has changed password" flag, because nothing consumes one.

**Wrong code, wrong nickname and wrong password all return the same error.** That is what stops the
login form being a classroom-roster oracle. S4 owns the wording.

### 6.2 Provisioning

- **Teachers** carry real emails and use ordinary Supabase signup, self-serve per ADR-017. The gate
  on that signup is S4's.
- **Students** are created only by a teacher, into a classroom they own. There is no self-serve path,
  by ADR-017 and by the `profiles_role_shape` constraint.
- **Researchers** are provisioned **by hand** — SQL or the Supabase dashboard. ADR-026 builds no
  admin surface and there are three of them; a provisioning UI for an audience of three exists only
  for schema symmetry.
- **Classroom codes** are minted by the backend and retried on unique violation.

### 6.3 Ownership is server-derived

`POST /storybooks` reads `profile_id` and `classroom_id` from the authenticated subject. A
client-supplied value in the request body is forgeable and is **never** trusted. How the subject is
authenticated is S2's.

### 6.4 Retiring the sentinels

| Location | Change |
|---|---|
| `config.py:19-20` | delete both settings |
| `run_job.py:85` | widen the `SELECT` to include `profile_id, classroom_id` |
| `run_job.py:99-100` | read from the row, not `settings` |
| `test_story_memory.py:155-156` | delete — asserts the sentinels' values |
| `test_run_job.py:105-106` | assert the row's values instead |
| ~13 other test files | unchanged — `"dev-classroom"` there is a fixture literal, still a valid `str` |

## 7. Invariants

1. Every identity is exactly one `auth.users` row and exactly one `profiles` row.
2. A student always has a classroom. A teacher or researcher never has one.
3. **A student belongs to one classroom for life.** No transfer mechanism exists. Transfer would
   change the login address, which is the same N-rewrite problem as §3.3; S4 must not design one.
4. The project stores **no** password material. `auth.users.encrypted_password` is the only copy.
5. Ownership is server-derived, never client-supplied (§6.3).
6. `jobs.classroom_id` can never disagree with its author's `profiles.classroom_id` — **and this
   holds only because invariant 3 holds.** If transfer is ever added, this breaks silently.
7. `backend/contracts/` is untouched.

### Consequences worth stating

- **C1 — Neither a teacher nor a researcher can author a book.** They have no `classroom_id`, and
  `jobs.classroom_id` is `NOT NULL`. Consistent with ADR-017, but the study's researcher-as-teacher
  posture still requires creating a student account to produce any book at all, including for testing.
- **C2 — Deleting a teacher destroys every book in every classroom they own.** Correct cascade,
  alarming ergonomics. S4 owes a confirmation step that says so in words.
- **C3 — `0007` enables RLS with zero policies**, so it is default-deny and leaves the app
  non-functional on its own. `0007` and S3's policy migration ship together or not at all.
- **C4 — Storage objects do not cascade.** Deleting a job row leaves its images in the bucket. Known
  and already parked — kid-flow constraint 13 leaves superseded objects for `data-deletion`.

### Sequencing

This spec is implementable in two parts, and the split is not optional. `0007` (§4.1, §4.3, §4.4) and
the normalization function (§5) land on their own. **The sentinel retirement (§6.4) and tests 12–14
cannot land until S3 has added the `jobs` columns** — until then there is nothing on the job row to
read. A build of this spec that stops before S3 is complete and correct; it just leaves `run_job.py`
still reading `settings`.

## 8. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-2 PII redaction** — a child's nickname is stored in `auth.users.email` in cleartext.
  Accepted with reasoning in §3.1; it is already peer-visible by design (ADR-021).
- [x] **CC-4 Security (RLS + signed URLs)** — this spec creates the subject CC-4 has never had. It
  does **not** close CC-4; S3 does. `0007` enables RLS on both new tables and writes no policy.
- [x] **CC-10 Checkpointing / resumability** — see the finding in §10.
- [ ] CC-1, CC-3, CC-5, CC-6, CC-7, CC-8, CC-9 — not touched by this spec.

## 9. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Models mocked throughout; none of these call a model at all.

**Normalization (both suites, from the §5.1 table):**
1. Each passing vector normalizes to its stated output.
2. Each rejection vector raises, at creation time.
3. Python and TypeScript agree on every row — the same fourteen cases in both suites.

**Schema constraints:**
4. A `student` row with `classroom_id is null` violates `profiles_role_shape`.
5. A `teacher` row with a non-null `classroom_id` violates `profiles_role_shape`.
6. A second student with the same normalized nickname in the same classroom violates
   `profiles_classroom_nickname`.
7. The same normalized nickname in a *different* classroom inserts cleanly.
8. A `role` outside the three named values violates the check constraint.

**Triggers:**
9. Inserting into `auth.users` with `app_metadata` creates the matching `profiles` row.
10. Deleting a `profiles` row deletes its `auth.users` row.
11. Deleting a classroom deletes its students' `profiles` **and** their `auth.users` rows — the
    §4.3 gap, asserted so it cannot regress.
12. Deleting a classroom deletes its jobs (once S3 has added the FK).

**Sentinel retirement:**
13. `run_job` builds a `StoryMemory` whose `classroom_id` and `profile_id` come from the job row.
14. `settings` has no `dev_classroom_id` or `dev_profile_id` attribute.

## 10. Linked decisions & open questions

**Depends on:** ADR-006 (Supabase, RLS everywhere), ADR-017 (the whole shape — teacher-issued
classrooms, no self-serve student signup, teacher-initiated reset), ADR-021 (nickname is peer-visible),
ADR-026 (the `researcher` role).

### Verify before building

**GoTrue accepts a `.invalid` address with `email_confirm: true`.** It validates format, not
deliverability, and performs no MX lookup — but §3.1 rests on it entirely, so it is checked before
anything is built on top of it.

### Finding, handed off — not fixed here

**The LangGraph checkpoint tables are an unowned second copy of every child's story.**
`run_job.py:106` runs `PostgresSaver.setup()`, which creates `checkpoints`, `checkpoint_blobs` and
`checkpoint_writes` in the `public` schema, keyed on `thread_id = job_id`. They have **no foreign key
to `jobs`**, so §3.4's cascade misses them entirely, and — pending verification against the live
database — **no RLS**, while sitting in the schema PostgREST exposes. The blobs hold the full
`StoryMemory`: raw story text, character descriptions, captions.

Outside S1's cluster, so it is recorded, not fixed. The RLS half belongs to **S3**; the orphan half
belongs to **`data-deletion`**. It also qualifies a kid-flow binding constraint: "exactly two policy
surfaces exist today" describes the *policies*, and there are unprotected *tables* it does not count.

### Handoffs

**→ S2.** §3.1 largely pre-decides the load-bearing question the docket flagged. Students are real
`auth.users` rows, so `auth.uid()` exists for them, Supabase issues and refreshes the session, and
Realtime authorizes unchanged. What remains genuinely open: cookie vs `sessionStorage`
(`ROUTE_MAP.md:376`), what a 10-year-old sees when a session expires mid-story, whether reads move
behind FastAPI or stay on the anon key, what identity `POST /storybooks` and `POST /jobs/{id}/confirm`
require in place of `main.py:94`'s open resume, and whether the worker keeps `service_role`.

**→ S3.** `auth_role()` and `auth_classroom_id()` are the subject. `jobs.classroom_id` is
denormalized so the Storage-policy join back to `jobs` is one hop. `jobs.approved_at is not null`
scopes the gallery. S3 also owns: the §4.2 `jobs` ALTER and the pre-auth row disposal it requires, and
the checkpoint-table finding above.

**→ S4.** No classroom transfer (invariant 3). No researcher provisioning UI (§6.2). A teacher-deletion
confirmation that names the blast radius (consequence ④). A login form that does not distinguish wrong
code from wrong nickname from wrong password (§6.1).
