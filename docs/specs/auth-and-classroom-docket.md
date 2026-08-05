# auth-and-classroom — session docket

> **Agent: read this before anything else.**
> This docket governs a multi-session design. You are working ONE session.
> - Do not widen scope past the current session's cluster, and do not
>   re-decompose it. If it should split, append an amendment — don't split it
>   in-session.
> - "Binding constraints" are decided. To challenge one, append a NEW session.
>   Never edit a DONE session.
> - Something real but outside this session's cluster: if it belongs to a later
>   session, add it to that session's open questions; otherwise one line under
>   `## Found & parked`. Never fix it. Never open a file or a tracker for it.
> - Stop at an approved spec. Do NOT continue to writing-plans or implementation.
> - To end the session, in this order: record the spec path, propose the
>   constraints it establishes, wait for the user to confirm them, write them in.
>   Only then set the session to DONE, and flip every session blocked on it to
>   READY. A session is not DONE until its constraints are confirmed.

**Goal:** the identity layer ADR-017 describes and the app does not have — teacher-issued
classrooms, child-held student accounts, the `researcher` role ADR-026 rides on, and the RLS that
turns "classroom isolation" from a sentence in an ADR into a database policy. This is the last
**child-facing** gap in MASTER_SPEC §6, not a paperwork one.

**Cut rationale:** clustered by which open questions constrain each other. What rows exist has to
settle before "how do you become one of them" can, and both have to settle before a policy can name
a subject — so identity → session → authorization is forced, not chosen. Routes go last because
`middleware.ts` guards whatever S2 decides a session is, and the bookshelf query reads whatever S3
decides a child may see. The two questions that *look* like they belong together and do not:
**credential storage** (S1 — it is a row) and **session mechanism** (S2 — it is a claim); putting
them in one session lets the ADR-sized second question eat the first.

**Scope confirmed with the user before decomposition (2026-08-04):**
1. The docket reaches **through** the frontend route move and login/join UX — not backend + RLS only.
   S1 constraint 5 and `kid-flow-reader-and-wait-states.md:61,623` both name this row as their
   successor; stopping at the migration would leave them pointing at nothing.
2. ADR-026's **`researcher` role is IN**, named in S1 and policed in S3. `annotation-surface.md:81`
   is blocked on the role existing; retrofitting a role into a frozen policy migration is worse than
   naming it now. The `annotations` table and the `(research)/` routes stay Phase 2.5 and are **out**.
3. The **student session mechanism is decided inside S2**, escalating to an ADR in-session if the
   choice lands hard-to-reverse — the same pattern kid-flow S1 used for the storage-shape decision.

**Spec path convention:** `docs/specs/auth-<topic>.md` — flat, beside the specs it sequences, per
AGENTS.md ("one canonical location per artifact type", no new folders). This docket lives at
`docs/specs/auth-and-classroom-docket.md` for the same reason, matching `kid-flow-ui-docket.md`.
The skill's default `docs/dockets/` would have been a new top-level folder for one file.

**Roster note:** `MASTER_SPEC.md` §7 and `DECISION_BACKLOG.md` carry `auth-and-classroom` as a
single row. It becomes four specs. Update both rosters when the docket reaches `DONE` throughout —
not before, or the index will point at files that don't exist.

**Engine (writes the spec, exactly one per session):** `superpowers:brainstorming` — installed.
**Hardener (optional, after the engine, writes nothing):** `grilling` — installed. Run it on a
draft spec before the constraint extract, so constraints come off the final text.
`grill-with-docs` is not installed; skip it.

---

## Binding constraints

Decided in earlier sessions. Later sessions treat these as given, not open.

### From S1 · Identity, roles & classroom schema (`docs/specs/auth-identity-and-classroom-schema.md`)

Confirmed 2026-08-05.

- **S1-1 — Students are real `auth.users` rows.** Login address is `{nickname}@{code}.students.storybuddy.invalid`. Supabase owns all password material. `auth.uid()` exists for students; S3 writes student policies in the ordinary way.
- **S1-2 — The role is `profiles.role`** (values: `teacher`, `student`, `researcher`), read through `public.auth_role()` security definer. A revoked role takes effect on the next query, not the next token refresh.
- **S1-3 — The classroom code is a 6-character immutable string** from a 31-symbol alphabet (a–z + digits, minus 0, O, 1, I, l). Regeneration is permanently off — it would invalidate every student's login address with no atomic remedy.
- **S1-4 — `jobs.profile_id` and `jobs.classroom_id` are both `NOT NULL` with `ON DELETE CASCADE`.** Deleting a student deletes their books; deleting a classroom deletes everything in it.
- **S1-5 — A student belongs to one classroom for life.** No transfer mechanism exists or may be added; transfer would change the login address (the same N-rewrite problem as the code).
- **S1-6 — The approval bit is `jobs.approved_at timestamptz`, nullable.** `null` = not peer-visible. S3 scopes the gallery with `approved_at is not null`.
- **S1-7 — Migration `0007_identity_and_classrooms.sql` creates `classrooms`, `profiles`, triggers, and helper functions, and enables RLS with zero policies (default-deny).** `0007` and S3's policy migration ship together or not at all.
- **S1-8 — The `jobs` ALTER (adding `profile_id`, `classroom_id`, `approved_at`) is executed by S3's migration.** Column definitions are frozen in S1; S3 transcribes them rather than re-deriving them.
- **S1-9 — `backend/contracts/` is unchanged.** `StoryMemory.classroom_id` and `.profile_id` stop receiving sentinels and start receiving real UUIDs.

### From S2 · Session model & trust boundary (`docs/specs/auth-session-model.md`)

Confirmed 2026-08-05.

- **S2-1 — One session mechanism for all three roles.** Supabase `signInWithPassword` → access token stored in a cookie via `@supabase/ssr`'s `createBrowserClient`. No second substrate, no custom session.
- **S2-2 — The frontend composes the synthetic email at login.** Nickname is normalized per S1 §5, then assembled as `{nickname}@{code}.students.storybuddy.invalid` in the browser before calling `signInWithPassword`. The S1 §5.1 test vectors bind both the creation-time and login-time implementations.
- **S2-3 — `POST /storybooks` and `POST /jobs/{id}/confirm` require a valid Bearer JWT.** FastAPI verifies via `supabase.auth.get_user(jwt)`. No token → 401. Teacher or researcher token on `/storybooks` → 403 (null `classroom_id` blocks insert). Valid token for the wrong profile on `/confirm` → 403.
- **S2-4 — Ownership in `POST /storybooks` is always server-derived.** Profile ID and classroom ID are read from the authenticated user's `profiles` row, never from the request body.
- **S2-5 — The worker retains `service_role` deliberately.** Any future worker entrypoint must state this explicitly, not inherit it silently.
- **S2-6 — `middleware.ts` (S4) uses `createServerClient` from `@supabase/ssr`.** Student session expiry → `/join`. Teacher/researcher expiry → `/login`. Mid-process expiry: the job continues server-side; the child re-logs in and returns.
- **S2-7 — Session lifetime is Supabase defaults.** 1-hour access token, auto-refreshed. 60-day refresh token. No custom lifetime.

### Pre-existing constraints, not from this docket

Already frozen. Listed so no session re-decides them.

**From the ADRs:**

- **ADR-017 is the whole shape and is not reopened.** Teacher or BEED student signs up and creates a
  classroom with a code; the teacher creates each student account (nickname + an initial password the
  teacher sets); the child logs in with classroom code + nickname + password and **may change their
  password**; password reset is **teacher-initiated only**, because student accounts carry no email.
  **No self-serve signup for students, no public mode, ever.** A classroom is just a container with an
  adult owner — a tutoring centre owns one, a parent owns one with a single member. **Same table, same
  policy, no second mode.**
- **ADR-017: the teacher manually approves every book before it is peer-visible.** Auto-approve is
  deferred to Future Work — no toggle, and adding one needs an ethics re-review.
- **ADR-021: the gallery is teacher-curated and display-only.** The approved storybook is the only
  peer-visible artifact. No reflection surface, no comments, no cross-classroom, no link-based sharing.
- **ADR-006: Supabase for Auth + Postgres + Storage + Realtime, RLS everywhere.** The platform choice
  stands; only ADR-006's parent→kid *role model* is superseded (by ADR-017).
- **ADR-026: a third role, `researcher`, is added here.** The `annotations` table, its RLS, and the
  `(research)/` route group are Phase 2.5 and belong to `annotation-surface`, not to this docket.
- **ADR-013: publishing outside the container is the PDF export.** The child shares the artifact, not
  the platform. `export-pdf` owns it.
- **`contracts/` is frozen.** `StoryMemory` already carries `classroom_id` and `profile_id`. A session
  that believes it needs a Story Memory change stops and says so (AGENTS.md "Architecture is locked");
  it does not write one.

**From `kid-flow-ui-docket.md` (DONE 2026-08-04) — this docket inherits its output:**

- **Exactly two policy surfaces exist today, and this row replaces both in one migration** —
  `0001_jobs_table.sql:18-21` (`jobs for select to anon using (true)`) and `0004_jobs_pages.sql`'s
  `storage.objects` policy (`using (bucket_id = 'storybook-images')`). Both carry a `ponytail:` comment
  naming this row. kid-flow constraints 4, 16, 23 each re-assert that no third surface was added.
- **A book is `jobs.pages`** — an ordered JSONB array of `{scene_id, caption, image_path}`, **durable
  Storage paths only, never signed URLs**. Signing happens at read time.
- **`run_job.py`'s `_finish` is the only writer of `pages` or `reveal`.** No session here adds a second.
- **A redraw never reuses a Storage path** (kid-flow constraint 13); superseded objects are left for
  `data-deletion`.
- **Three verbs, and only three** — `redraw` / `revise` / `retry`. A terminal job is immutable; recovery
  is always a new job. This docket adds no fourth verb.
- **The child is never shown a moderation category, a flagged span, or `jobs.error`.** The teacher-facing
  reading of a failure is `teacher-dashboard`'s, not this docket's.
- **Kid routes are flat today** (`/write`, `/process/[jobId]`, `/book/[jobId]`) **by intent, waiting on
  this row** (kid-flow constraint 5). The move is documented as "a directory rename plus a middleware
  entry" — S4 tests that claim rather than inheriting it.
- **Next free migration is `0007`.**

---

## Sessions

Statuses: DONE (spec linked **and** constraints confirmed) · PARTIAL (stopped early,
resumable) · READY · BLOCKED (needs Sn)

### S1 · Identity, roles & classroom schema — DONE (`docs/specs/auth-identity-and-classroom-schema.md`)

**Cluster:** what rows exist and who owns what. Whether teachers live in `auth.users` plus a profile
table or somewhere else; what a classroom row is and what a student row is; **how a role is
represented** across all three of teacher, student and `researcher` (a column, a JWT claim,
`app_metadata`, a Postgres role) — one representation, chosen once, because S3 writes policies against
it; the classroom code's format, uniqueness and regeneration, given it is typed into a **public,
unauthenticated** login surface and is therefore guessable-in-principle; **where a student's password
lives** and in what form, which is a security decision and not a session decision; what `jobs` gains to
carry ownership (`profile_id`, `classroom_id`, or both) and whether it is nullable; who supplies those
values now that `config.py:19-20`'s `dev-classroom` / `dev-profile` sentinels retire, given
`StoryMemory` already declares both fields; and what happens to a student row when they leave a
classroom or the classroom is deleted, at least far enough to know whether ownership is a foreign key
or a snapshot.

**Explicitly out:** how anyone authenticates (S2), any policy text (S3), any URL or screen (S4).
`annotations` and the `(research)/` routes (ADR-026, Phase 2.5 — this session names the role and stops).
The **teacher-approval workflow** — S1 may decide only whether the approval *bit* is a column this
migration adds, since S3 needs something to scope the gallery by; the review UI, the notification, and
the approve/reject flow are `teacher-dashboard`'s. `data-deletion`'s retention policy and sweeps.

**Stance:** persistence session — done means a schema, a chosen representation for role and for
credentials, and the invariants that shape must never violate. Not "here are the tables"; "here is what
must always be true of a student row, and what it means that a job points at one".

**Open questions:** ⚠️ this is a schema decision under AGENTS.md §2 **and** a credential-storage
decision under §7 (Security). If the session lands on something hard to reverse — notably storing
password material the project owns rather than delegating it — it writes an ADR and flags it rather
than settling it inline. ⚠️ Whatever this session decides about credential storage **constrains S2's
mechanism choice and may pre-decide it**; name that coupling explicitly at handoff instead of letting
S2 discover it.

---

### S2 · Session model & trust boundary — DONE (`docs/specs/auth-session-model.md`)

**Cluster:** how each of the three roles proves who it is, and what the server trusts. **The load-bearing
question: is a student a real Supabase Auth user (e.g. a synthetic email) or a custom session?** — because
if students are not `auth.users` rows, `auth.uid()` is unavailable for them and S3 cannot write a student
policy in the ordinary way. Then: who mints and signs a student's token, with what claims and what
lifetime; whether the browser holds it in a cookie or `sessionStorage`, which `ROUTE_MAP.md:376` records
as *"decision needed before `auth-and-classroom` spec"*; what a 10-year-old sees when it expires
mid-story, given a draft is already lost on navigation (`ROUTE_MAP.md:246`); whether the frontend keeps
talking to Supabase directly with the anon key (`frontend/lib/supabaseClient.ts`) or reads move behind
FastAPI, which decides whether RLS or an API handler is the enforcement point; what identity
`POST /storybooks` and `POST /jobs/{id}/confirm` start requiring, given **`main.py:94` today lets anyone
holding a job UUID resume any paused job** and `db.py:10` runs every request on the service-role key; and
whether the worker keeps service_role — a deliberate RLS bypass that should be *stated*, not inherited.

**Explicitly out:** the policy text those claims are consumed by (S3), and every screen — the login form,
`/join`, the redirect (S4). The teacher's own signup gate (S4). Password *storage* (S1); this session
decides how a password is *presented and verified*, not where it lives.

**Stance:** trust-boundary session — done means, for every request that can reach data, a named subject,
a named place the claim is verified, and a stated answer to "what does an attacker holding only a job
UUID get". Done is not "we chose JWTs".

**Open questions:**
- **From the cut:** the student-mechanism choice is the likely ADR in this docket. Escalate in-session
  if it is hard to reverse (user-confirmed at decomposition).
- Whatever is chosen must still let **Supabase Realtime** authorize a subscription — `jobs` is in the
  `supabase_realtime` publication and `frontend/lib/useJob.ts` subscribes from the browser today. A
  session model that cannot authorize Realtime silently breaks the wait stepper S4 renders.

---

### S3 · Authorization surface — READY

**Cluster:** the single migration that replaces both existing policy surfaces, and everything that must
be true for it to be safe. The `jobs` policies per role and per verb; **four distinct read paths on one
table** — a child's own books, a classmate's *approved* book in the same classroom, a teacher's read
across classrooms they own, and a researcher's blinded read — which either resolve to one policy set or
prove they cannot; and the Storage half.

⚠️ **A concrete finding this session owns:** Storage paths are `{story_id}/{scene_id}.png` with
`story_id = job_id` — **there is no classroom segment in the path**. A classroom-scoped
`storage.objects` policy must therefore either join back to `jobs` or change the path shape, and the
path shape is frozen by kid-flow constraints 1 and 13 (durable paths, never reused, already written to
rows). This session picks one and says why; it does not discover it late.

Also here: whether Realtime still authorizes after the policies tighten; and what the **Tier-A isolation
tests** actually assert, since ADR-017 claims classroom isolation is "a real, testable boundary" and that
claim is currently unbacked by a single test.

**Explicitly out:** re-opening the schema (S1) or the session model (S2) — if a policy seems to require
changing one, that is an amendment, not an in-session fix. The `annotations` table's own RLS (ADR-026,
Phase 2.5). The teacher-approval *workflow* (`teacher-dashboard`) — this session consumes the approval
bit S1 placed, and does not design how it gets set. Any screen (S4).

**Stance:** authorization session — done means every (role × table × verb) pair has a chosen answer
including the denials, the migration is writable from the spec alone, and each policy has a named test
that fails if the policy is dropped. A policy nobody can break on purpose is not known to work.

**Open questions:**
- The migration is `0007` unless an earlier session claims it. Claim numbers explicitly.
- Existing rows were created under the dev sentinels and own nothing. What the migration does with them
  is this session's call — `0004` has precedent for destroying pre-auth data on the grounds that ADR-017
  means no real child data has entered the system yet.

---

### S4 · Routes, guards & account UX — BLOCKED (needs S2, S3)

**Cluster:** every URL and every screen the identity layer adds or moves. The flat → `/s/[profileId]`
migration, which kid-flow constraint 5 and `ROUTE_MAP.md:61-65` both describe as "a directory rename
plus a middleware entry" — a claim to **test, not inherit**, since `/book/[jobId]` and `/process/[jobId]`
already carry four-bucket render logic and a Realtime subscription. What `middleware.ts` checks for each
role group and whether it holds to `ROUTE_MAP.md:196`'s "no server-side data fetching in middleware".
`/join` and `/join/[code]` as a flow a 10-year-old completes — code, then nickname, then password, where
**typing a nickname exactly right is a real failure mode** for the age band ADR-017 scopes to. The
teacher's `/signup`, which ADR-017 *does* permit self-serve, and whatever gate it carries. Password
change (child) and password reset (teacher-initiated) as screens. And the **bookshelf list query** S4 of
the kid-flow docket explicitly deferred to this row — `kid-flow-reader-and-wait-states.md:61`: *"needs a
per-child list query, which S1 constraint 4's capability-link model cannot express"*.

**Explicitly out:** the gallery itself (`classroom-sharing`), the teacher dashboard and review screens
(`teacher-dashboard`), the `(research)/` routes (`annotation-surface`). Re-opening a schema (S1), a
session mechanism (S2), or a policy (S3).

**Stance:** interaction session — done means every route in the tree has a stated auth level, a stated
redirect on failure, and a chosen rendering for the states nobody wants: expired session mid-write,
wrong classroom code, a book whose owner no longer has access. Per AGENTS.md, failure screens get the
same design care as success screens.

**Open questions:**
- `ROUTE_MAP.md` §1–§8 already commits a full route tree, protection matrix, back-button matrix and
  loading states for routes that do not exist yet. Read it as **input to reconcile**, not as decisions
  to re-derive — and note it was written before the kid-flow docket, so parts of it may now be stale.
- `DESIGN.md` and `USER_FLOW.md` commit the register (cartoon-pop for kids, Inter/density for teachers).
  Same rule: input, not re-derivation.

---

## Found & parked

Turned up mid-session, belongs to no session here. Recorded so it is not lost, and not this
docket's work.

- 2026-08-04 (from decomposition): `docs/specs/plans/` still holds four plans whose modules are all
  built. AGENTS.md says plans are disposable once built + green + spec updated. Carried over from
  `kid-flow-ui-docket.md`'s parked list, still unactioned. Not this docket's work.
- 2026-08-04 (from decomposition): `ROUTE_MAP.md` is `status: draft` and specifies routes, transitions
  and loading states for screens across `teacher-dashboard`, `classroom-sharing` and this row at once.
  Whether it survives as one spec or is absorbed into the specs it describes is a doc-hygiene question
  no session here owns. S4 reconciles the routes it touches and no more.

## Amendments

*(none yet)*
