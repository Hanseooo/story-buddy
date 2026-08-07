# teacher-dashboard — session docket

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

**Goal:** the teacher's half of the product — how a teacher account and a classroom
come to exist, how student accounts are issued and maintained, and the manual review
gate every book passes through before it is peer-visible or exportable (ADR-017,
PRD §11.1, `ethics_and_safety.md` §4).

**Cut rationale:** the authorization model for a service_role write surface constrains
every write in the feature and neither later session should re-decide it, so it goes
first and stays small. Provisioning's remaining questions — password, nickname
collision, removal — each straddle API and screen, so splitting them by layer would
cut through a real coupling; provisioning stays whole and establishes the teacher
shell the way S4 of the auth docket established `StudentShell`. Review & approval
turned out independent of provisioning (it works on today's hand-provisioned
classrooms) and is the ethics-critical cluster, so it goes last and alone.

**Spec path convention:** `docs/specs/<topic>.md` (project convention — no date prefix;
see `AGENTS.md` → *Artifact hygiene*)

**Created:** 2026-08-07

---

## Binding constraints

Decided in earlier sessions of **this** docket. Later sessions treat these as given,
not open.

**From S1** (`docs/specs/teacher-privileged-writes-and-identity.md`, DONE 2026-08-07):

- **S1-1 — Role is a constant on the self-serve path, never a request value.** `handle_new_user`
  coalesces absent `app_metadata.role` to `'teacher'`. `raw_user_meta_data` is client-controlled and
  is read only for `display_name`. No session adds a metadata-driven role.
- **S1-2 — `app_metadata` remains the admin-only identity channel.** S2's student creation and
  hand-provisioned researchers pass role, classroom and nicknames through it, unchanged from
  `auth-identity-and-classroom-schema.md` §6.1.
- **S1-3 — `display_name` is role-conditional in the trigger.** NULL for students
  (`profiles_role_shape`), three-step fallback otherwise. S2 must not add an unconditional default.
- **S1-4 — Every service_role write passes `require_teacher`, carried on `teacher_router`,** not on
  the handler. **There is no second teacher router.** S2 and S3 hang routes on it and choose their
  own paths — the router has no prefix.
- **S1-5 — Ownership checks are dependencies, not handler bodies, and fail 404.** S1 ships
  `owned_classroom`; a session needing ownership of a different resource adds one on the same
  pattern rather than checking inline.
- **S1-6 — Reads via RLS in the browser, writes via FastAPI, `approved_at` the one exception.** No
  session routes a teacher read through FastAPI without amending this.
- **S1-7 — `authenticated` holds UPDATE on exactly one column of `jobs`: `approved_at`.** Column
  grant, below RLS. S3 consumes this; widening it is an amendment.
- **S1-8 — `0009` is ADR-flagged and not implementable until the ADR is accepted.** It alters a
  `security definer` trigger on `auth.users` and a table grant.
- **S1-9 — `/signup`'s repair (name field + honest error handling) belongs to S1,** not to S2's
  shell. S2 inherits a working teacher-creation path and does not revisit the page.

**From S2** (`docs/specs/teacher-provisioning-and-shell.md`, DONE 2026-08-07):

- **S2-1 — Removing a student is `removed_at` + an auth ban, never a delete.** Both halves are
  required: the column is what the browser reads under RLS, the ban is what makes login fail. A
  student's books survive their removal. Permanent student deletion is not shipped and belongs to
  `data-deletion`.
- **S2-2 — Every list of students filters `removed_at is null` in the query.** `0008:93` and
  `0008:101` both return removed rows. This is S4-4 again: RLS does not scope a list.
- **S2-3 — A child's full name is never stored.** The nickname is reduced (first name only by
  default) in the browser, and the server re-derives `nickname` from the submitted `display_nickname`
  using `app/nickname.py`. No session adds a full-name column.
- **S2-4 — Passwords are generated, returned exactly once, and never persisted.** Reset is the only
  recovery path. No session adds password storage, a rotation flag, or a retrieval endpoint.
- **S2-5 — The teacher route tree is frozen** as `/classroom`,
  `/classroom/[classroomId]{, /add, /settings, /books}`, `/settings`. `/dashboard` is deleted and
  `middleware.ts` redirects there no longer. **`/classroom/[classroomId]/books` is S3's** and is the
  only route S3 adds.
- **S2-6 — `TeacherShell` is a shared server component**, imported by `app/classroom/layout.tsx` and
  `app/settings/layout.tsx` — not a route group (S4-2). It owns the single `profiles` read, the role
  check, the classroom switcher and log out. **`middleware.ts` still never reads a role.** S3
  consumes the shell and adds nothing to it but a tab.
- **S2-7 — S1-6 held: no S2 endpoint is a read.** Every teacher read below the shell is a
  client-side RLS fetch. S3's library list is a browser read, not a FastAPI route.
- **S2-8 — Components are native platform elements** (`<dialog>`, `<details>`, popover). No component
  library was added; adding one is an `AGENTS.md` §2 decision, not a session's call.
- **S2-9 — Classroom delete ships; teacher-account delete is named and not shipped.**
- **S2-10 — Bulk create is per-row, capped at 60, and idempotent by name.** A partial failure never
  rolls back the rows that succeeded.
- **S2-11 — `0010` is claimed and ADR-flagged** (adds `profiles.removed_at`).

**From S3** (`docs/specs/teacher-review-and-approval.md`, DONE 2026-08-07):

> **Lettered, not numbered, on purpose.** This file already lists auth-docket constraints **S3-4,
> S3-7, S3-8** under *Pre-existing*, and S3's spec cites them. Numbering this session `S3-1…` would
> collide head-on. (The collision already exists quietly: **`S1-5` means two different things** in
> this file — "ownership checks are dependencies" from S1, and "one classroom for life" from the auth
> docket. Read `S1-5` with its source block, never alone.)

- **S3-A — Three review states, derived from two timestamps, closed by a CHECK.** `0011` adds
  `jobs.rejected_at`; `approved_at`'s meaning is unchanged, so `0008`'s four consuming policies read
  correctly without modification. No `review_status` enum. `jobs_review_exclusive` makes both-set
  **unrepresentable**, not merely unwritten.
- **S3-B — All six transitions exist; the decision is a value, not two buttons.** Un-approve and
  back-to-pending are permitted. No teacher-reachable state is a dead end. This is what makes Undo
  free, and Undo is why the screen has no confirmation dialog.
- **S3-C — The review write is `POST /jobs/{id}/review` on `teacher_router`, behind `require_teacher`
  + `owned_job`.** `owned_job` is new in `app/auth.py` on `owned_classroom`'s pattern (S1-5). The
  server sets every timestamp — no client supplies one. Unauthorized and nonexistent are the same
  `404`.
- **S3-D — After `0011`, `authenticated` holds no UPDATE on `jobs`.** Writes never go through RLS
  anywhere in the system. **Amends S1-7 and auth-docket S3-8**; makes auth-docket S3-7 exceptionless.
  See *Amendments* 1.
- **S3-E — Only `failure_reason = 'child_text'` names the child's writing — for the teacher as for
  the child.** Every other value, every unknown value, and `null` render as *machine*. Kid-flow
  §4.2's fail-safe default survives the audience change; no session widens it.
- **S3-F — No moderation category, flagged span, or `jobs.error` reaches any screen,** teacher-facing
  or child-facing.
- **S3-G — The child is never shown a review state.** Pending, approved and rejected are
  indistinguishable from inside the kid flow. **Binds `classroom-sharing`:** no rejection signal, no
  absence badge, no "why isn't mine here" affordance without amending S3's spec.
- **S3-H — No bulk decision and no auto-approve.** Per-book only. Widening it is ADR-017's Future
  Work path behind an ethics re-review, not a session's call.
- **S3-I — The books list filters `classroom_id` explicitly and deliberately does *not* filter
  `removed_at`.** S2-2 governs lists of *students*; a removed child's book stays reviewable and
  attributed (S2-1).
- **S3-J — No Realtime on the list;** refetch on mount and `visibilitychange`. S4-8's single per-job
  status model stands — no second job-status state model exists anywhere.
- **S3-K — `/classroom/[classroomId]/books` is the only route S3 added** (S2-5 held). The reader is a
  `<dialog>`, not a route. S2-8 held — native elements, no component library.
- **S3-L — `0011` is claimed and ADR-flagged** (adds `rejected_at` + CHECK, revokes a grant, drops a
  policy).

⚠️ **The next free migration is now `0012`** — S1 claims `0009`, S2 `0010`, S3 `0011`.

### Pre-existing constraints, not from this docket

Already frozen elsewhere. Listed so no session re-decides them, and so a session
does not have to re-read four specs to find them.

**From the auth-and-classroom docket** (`docs/specs/auth-and-classroom-docket.md`, DONE):

- **S3-7 — Writes never go through RLS.** No INSERT policy on any table, no DELETE
  policy anywhere. `POST /storybooks`, classroom creation, and profile updates all run
  service_role behind FastAPI; deletion is cascade-only.
- **S3-8 — The only RLS write path is the teacher's UPDATE on `jobs`,** gated on
  classroom ownership. RLS cannot restrict *which* column; **`teacher-dashboard` is the
  sole caller and sets only `approved_at`.**
- **S3-5 — All policies are `to authenticated` and gate on `auth_role()`.** Denial is by
  absence of a permissive policy — no explicit `deny` anywhere.
- **S3-6 — Storage is classroom-scoped by joining back to `jobs`, not by changing the
  path.** The `{job_id}/{scene_id}.png` shape is frozen. Any teacher-side image read
  inherits the join, not a path rewrite.
- **S3-4 — No anon policy exists on `jobs` or `storage.objects`,** and adding one needs
  the `AGENTS.md` §5 security gate.
- **S4-2 — The route tree is frozen** as `/`, `/login`, `/signup`, `/join`, `/join/[code]`,
  `/dashboard`, `/s/[profileId]/{·, settings, write, process/[jobId], book/[jobId]}`.
  **No Next.js route groups** — `(auth)` and `(immersive)` were both rejected.
  **`teacher-dashboard` extends under `/classroom/…`.**
- **S4-3 — `middleware.ts` uses `getUser()` via `createServerClient`, fails closed, and
  validates `?next=` as a relative path** (must start with `/`, not `//`). `getClaims()`
  with asymmetric JWT signing keys is the named upgrade path and is an infra decision
  under `AGENTS.md` §2/§7 — not a refactor.
- **S4-4 — RLS does not scope a per-child list; the query must.** S3 §4.1 grants students
  *two* SELECT policies on `jobs`. Any "this X's own Y" read filters explicitly.
- **S4-5 — `/dashboard` is a stated placeholder owned by this row,** which replaces it
  wholesale. It exists so signup is not a dead end and middleware has a redirect target.
- **S4-6 — Teacher-initiated password reset belongs to this row** (auth docket amendment 1).
  It needs the roster picker on the student-management screen. **Classrooms and student
  accounts are hand-provisioned by SQL or the Supabase dashboard until this row lands.**
- **S4-7 — `StudentShell` owns the single `profiles` read and the log-out control.**
  Log out is first-class because the deployment target is a shared classroom device.
- **S4-9 — `ROUTE_MAP.md` is input, not authority,** and already diverges in four places.
  A session reconciles the routes it touches and no more.
- **S1-5 — One classroom for life.** `auth_classroom_id()` is load-bearing on this and is
  only valid while `jobs.classroom_id` cannot disagree with the author's
  `profiles.classroom_id`.
- **S1 §3.2 — The role is a column on `profiles`, never a JWT claim.** `app_metadata` is
  used at creation time as transport into the `handle_new_user` trigger, and is never read
  by a policy.
- **S1 §3.3 — The classroom code is immutable.** Six characters from a 31-symbol alphabet
  (lowercase `a–z` + digits, minus ambiguous glyphs).

**From the kid-flow-ui docket** (`docs/specs/kid-flow-ui-docket.md`, DONE):

- **A book is `jobs.pages`** — an ordered JSONB array of `{scene_id, caption, image_path}`,
  **durable Storage paths only, never signed URLs**. Signing happens at read time.
- **`run_job.py`'s `_finish` is the only writer of `pages` or `reveal`.** No session here
  adds a second.
- **Three verbs, and only three** — `redraw` / `revise` / `retry`. A terminal job is
  immutable; recovery is always a new job. This docket adds no fourth verb.
- **The child is never shown a moderation category, a flagged span, or `jobs.error`.** The
  **teacher-facing** reading of a failure was explicitly parked for this row (S3 of that
  docket) — it is S3's cluster here.

**From ADRs / PRD:**

- **ADR-017 — teacher approval is always manual.** There is no auto-approve toggle; it is
  deferred to Future Work behind an ethics re-review. No session here may add one.
- **ADR-021 — the gallery is display-only.** No reflection, comment, or scoring surface.
  The gallery itself is `classroom-sharing`, not this docket.
- **`AGENTS.md` §2 — a schema change is an ADR-session decision, not an inline one.** If a
  session concludes a migration is required, it writes the ADR and flags it.

**State of the world** (as of decomposition; S1 has since claimed `0009` and S2 `0010`, so the next
free migration is **`0011`**)**:** next free migration is **`0009`**. The backend has exactly three
endpoints (`GET /health`, `POST /storybooks`, `POST /jobs/{id}/confirm`) and one auth
dependency (`get_current_user`, `app/main.py:21`) which verifies a token and checks nothing
else.

---

## Sessions

Statuses: DONE (spec linked **and** constraints confirmed) · PARTIAL (stopped early,
resumable) · READY · BLOCKED (needs Sn)

**Engine for every session:** `superpowers:brainstorming` — it writes the spec.
**Optional hardener:** `grilling` — *after* the engine, on the draft spec, to stress-test
it. A hardener never replaces the engine; a session with no spec cannot reach DONE.

---

### S1 · Privileged writes & teacher identity — DONE

**Spec:** `docs/specs/teacher-privileged-writes-and-identity.md`


**Cluster:** how a privileged identity comes to exist, and what authorizes a write that
bypasses RLS. These constrain each other: an authorization check cannot read
`role = 'teacher'` if no path ever sets the role, and the path that sets it is itself the
most privileged write in the system.

Concretely: how a teacher account is created with a `profiles.role` (**⚠️ no such path
exists today — see *Found & parked***); what ADR-017's "self-serve teacher signup" means in
practice and whether it carries a gate; what authorizes each service_role write in FastAPI,
given that RLS is bypassed and `get_current_user` today checks only that a token is valid;
and whether teacher **reads** go through the browser client's RLS policies (which `0008`
grants), through FastAPI, or a stated mix.

**Explicitly out:** any specific endpoint's request/response body beyond the convention all
of them follow (S2, S3). Any screen (S2, S3). What "approved" or "rejected" means (S3).
Re-opening `0007`/`0008` — if a policy seems to require changing, that is an amendment.
The researcher role and the `(research)/` routes (`annotation-surface`).

**Stance:** authorization session — done means every privileged write has a named principal,
a named check, and a stated place that check lives; and the identity-creation path is
end-to-end, from an empty database to a teacher who can log in. Not "FastAPI will validate
ownership" — *which* function, reading *which* row, failing *how*.

**Open questions:**
- Q1 — How does a teacher account get created with a role? ⚠️ **The shipped path is broken**
  (see *Found & parked*), so this is a fix *and* a decision. ADR-017 permits self-serve
  teacher signup; does it carry a gate (invite, allowlist, manual activation), and does the
  fix belong in the client, a new endpoint, or a DB default?
- Q2 — What authorizes a service_role write? RLS is bypassed by construction (S3-7), so
  classroom ownership must be re-checked in application code. Where does that check live so
  that no future endpoint can forget it?
- Q3 — Do teacher reads go through RLS or FastAPI? `0008` already grants teachers four
  read policies, so "reads via RLS, writes via FastAPI" is available — but it means two
  authorization models in one feature. State the rule, either way.
- ⚠️ Q1 and Q2 are both **security decisions under `AGENTS.md` §5/§2**. If the session lands
  on something hard to reverse, it writes an ADR and flags it rather than deciding inline.

---

### S2 · Provisioning & the teacher shell — DONE

**Spec:** `docs/specs/teacher-provisioning-and-shell.md`

**Cluster:** everything that has to be true before a real classroom exists on a real device
— and the shell every teacher screen lives in. Password choice, nickname collision and
student removal each straddle the API and the screen (a generated-and-shown-once password is
simultaneously an endpoint response and a screen that can never be revisited), so they are
not separable by layer.

Concretely: classroom creation and code minting; student account creation via
`auth.admin.createUser` (S1 §7); what password a new student gets and how it reaches the
child; nickname collision inside a classroom against `profiles_classroom_nickname`;
teacher-initiated password reset (auth docket amendment 1); what removing a student *means*;
how the classroom code and `/join/[code]` link are surfaced. Plus the shell: the teacher
layout, the `middleware.ts` extension to `/classroom/**` and `/settings`, classroom settings,
and teacher account settings.

**Explicitly out:** the library, the review screen, `approved_at`, and anything about a book
(S3). The gallery (`classroom-sharing`). Re-deciding S1's authorization model. Retention
periods and guardian-request deletion flows (`data-deletion`) — this session decides what a
*removal* does, not what a retention policy is.

**Stance:** provisioning session — done means a teacher with an empty account can reach a
classroom full of children who can log in, with every step named, and every way that
sequence can go wrong given a chosen rendering. Per `AGENTS.md`, failure screens get the same
design care as success screens — and here the failures are adult-facing and mostly
irreversible, which is a different design problem from the kid flow's.

**Open questions:**
- Q4 — Classroom creation: what mints the immutable 6-char code (S1 §3.3), and what happens
  on collision?
- Q5 — Student creation: one at a time, or bulk paste a class list? A real Grade 5–6 class is
  ~30–40 children and the deployment moment is a single sitting.
- Q6 — What password does a new student get — teacher-typed or generated-and-shown-once?
  What policy is age-appropriate for a 10-year-old who must retype it on a shared device?
  (S1: no forced rotation at first login.)
- Q7 — Nickname collision: `profiles_classroom_nickname` is unique on the *normalized*
  nickname, so two visually distinct entries can collide. What does the teacher see? Does the
  roster show `nickname` or `display_nickname`?
- Q8 — Teacher-initiated reset: reset to what, displayed how, handed to the child how?
- Q9 — Removing a student cascades `profiles` → `auth.users` → their `jobs` → their images.
  Is "remove from the roster" the same act as "delete this child's work"? If they must
  differ, that is a schema question under `AGENTS.md` §2.
- Q10 — Where is the classroom code surfaced — the `/join/[code]` link, a printable sheet,
  a projected view?
- Q17 — Does a `TeacherShell` layout exist, and what nav does it carry? `ROUTE_MAP.md` §3
  specifies sidebar + breadcrumbs, but S4-9 already ruled it input, not authority.
- Q18 — `middleware.ts` needs `/classroom/:path*` and `/settings`. S4-3 froze the guard as
  path-shaped and **never reading role**. With two role trees live, a logged-in student
  currently passes the `/dashboard` guard. Does path-only guarding still hold, and if not,
  what changes — knowing `ROUTE_MAP.md:196` bans DB reads in middleware?
- Q19 — `/settings`: teacher password change and account deletion. Deleting a teacher
  cascades their classrooms, every student, and every book. Does this session ship that
  button at all, or name it and leave it to `data-deletion`?
- Q20 — Classroom settings: rename, and the delete danger zone. Same cascade question at
  classroom scale.

---

### S3 · Review & approval — DONE

**Spec:** `docs/specs/teacher-review-and-approval.md`

**Cluster:** what states a book can be in from a teacher's side, and what a teacher is
allowed to see. These constrain each other tightly: whether "rejected" is a real state
determines the library's status set, which determines its badges, filters and empty states;
and whether failed books appear at all determines whether the teacher ever sees a moderation
signal, which is the question the kid-flow docket explicitly parked here.

This is the ethics-critical session. `ethics_and_safety.md` §4 and PRD §11.1 both rest on the
gate this designs, and it is the only thing standing between a generated book and a peer.

**Explicitly out:** classroom or account provisioning (S2). The shell, nav and middleware
(S2) — this session consumes them. The gallery that consumes `approved_at`
(`classroom-sharing`). Any auto-approve mechanism (ADR-017 forbids it). Adding a fourth
recovery verb (kid-flow docket: three, and only three).

**Stance:** state-model session — done means the set of states a book can occupy is closed
and named, every transition has an actor and a trigger, and each state has a chosen teacher
rendering *and* a chosen child-facing consequence. A state a teacher can reach but not leave,
or that reads identically to a different state, is not done.

**Open questions:**
- Q11 — ⚠️ **Is "rejected" a state?** `0008:15` adds only `approved_at timestamptz` nullable,
  so today reject ≡ not-yet-reviewed and the two are indistinguishable in the row. PRD §11.1
  says "manually approved **or rejected**". If reject must be distinct, that is a migration
  and a schema decision under `AGENTS.md` §2 — write the ADR, flag it, do not decide inline.
- Q12 — Can a teacher un-approve? The `teachers approve jobs` UPDATE policy permits setting
  `approved_at` back to null, so this is a product decision, not a technical one. What does a
  child see when a book leaves the gallery?
- Q13 — Does a teacher see failed and moderation-blocked jobs, and see *why*? The kid-flow
  docket parked exactly this. If yes: a moderation category, a flagged span, `jobs.error`,
  `jobs.failure_reason`? Note `failure_reason` was deliberately built so that only
  `child_text` ever blames the child's own writing and every unknown value maps to `machine`
  — the teacher-facing reading must not undo that.
- Q14 — The library list: which statuses appear, what ordering, what filters, and does it
  update via Realtime or on refresh? S4-8 froze `useJob` as the *per-job* hook and forbade a
  second state model for job status — a list is not a job.
- Q15 — Per-book approval only, or bulk? A teacher facing 40 books after one lesson is the
  expected case, and bulk approval is in tension with ADR-017's "manual, always".
- Q16 — Is the teacher told a book is waiting? No doc specifies a notification anywhere.

---

## Found & parked

Turned up mid-decomposition, belongs to no session here. Recorded so it is not lost, and not
this docket's work to fix.

- 2026-08-07 (from decomposition): **teacher signup is broken in shipped code.**
  `frontend/app/signup/page.tsx:16` calls `supabase.auth.signUp({ email, password })`
  client-side, which cannot write `app_metadata`; `handle_new_user`
  (`supabase/migrations/0007_identity_and_classrooms.sql:38-44`) builds the profile from
  `raw_app_meta_data ->> 'role'`, so `role` is NULL, the `not null` constraint rejects the
  insert, the trigger aborts the `auth.users` insert, and `signUp` errors. The page does not
  check the error and shows "Check your email" unconditionally. `auth-identity-and-classroom-schema.md`
  §7's operations table has a row for creating a *student* and none for a teacher.
  **Not parked away — this is S1's Q1**, listed here because it is a live defect and not only
  a design gap.
- 2026-08-07 (from S1): **`AGENTS.md:454` is stale.** It asserts S3's Tier-A isolation suite "is not
  built, and S3-13 says it is not optional". It *is* built — `backend/tests/test_rls_isolation.py`
  carries 31 tests covering S3's tests 1–25 and 28–33, with 26–27 documented as needing a WebSocket
  client and out of scope for pytest. A `Definition of Done` finding-propagation miss from the S3
  build. One-line fix, but it belongs to whoever next touches `AGENTS.md`'s status surface — not this
  docket.
- 2026-08-07 (from decomposition): `docs/specs/plans/` still holds plans whose modules are
  all built. `AGENTS.md` says plans are disposable once built + green + spec updated. Carried
  over unactioned from both prior dockets' parked lists. Still not this docket's work.
- 2026-08-07 (from decomposition): `ROUTE_MAP.md` is `status: draft` and specifies routes,
  transitions and loading states across `teacher-dashboard`, `classroom-sharing` and the auth
  row at once. Whether it survives as one spec or is absorbed into the specs it describes is a
  doc-hygiene question no session here owns. Sessions reconcile the routes they touch and no
  more (S4-9).

## Amendments

**1 — 2026-08-07 (from S3): the RLS write path is removed, not narrowed.**
S1-7 froze `authenticated`'s UPDATE on `jobs` at exactly one column (`approved_at`), and auth-docket
S3-8 called that "the only RLS write path" in the system. S3 moved the review write to
`POST /jobs/{id}/review` so the server owns the timestamps and CC-5 has somewhere to log the one gate
`ethics_and_safety.md` §4 rests on. That leaves `0009:38`'s column grant with no caller and
`0008:52`'s `teachers approve jobs` policy unable to fire.

`0011` therefore **revokes the grant and drops the policy**. S1-7's count goes from one column to
none; auth-docket S3-8 no longer describes anything; auth-docket S3-7 ("writes never go through RLS")
becomes true with **no exceptions**. `0009` is not edited — S1 is DONE — `0011` revokes what it
grants, and is harmless if `0009`'s ADR is never accepted.

Recorded rather than left silent because an inert policy on the approval column is exactly what
misleads whoever next audits the auth surface.

---

## Docket status: COMPLETE

All three sessions are DONE. The four `Found & parked` items above stayed parked across all three, as
intended, and are still not this docket's work.

**Build order for the specs this docket produced** — each is gated on its ADR (`AGENTS.md` §2):

1. `0009` (S1) → `0010` (S2) → `0011` (S3). Migration numbers are claimed in that order and `0011`
   revokes a grant `0009` creates, so `0011` must not land first.
2. S1's `require_teacher` / `owned_classroom` / `teacher_router` are already built
   (`backend/app/auth.py`); S2 hangs the first routes on that router, S3 adds `owned_job` beside
   `owned_classroom` and one more route.
3. `TeacherShell` (S2) must exist before S3's tab and pending count have anywhere to live.
