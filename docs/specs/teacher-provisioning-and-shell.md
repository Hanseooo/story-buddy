# Feature Spec — teacher: provisioning & the teacher shell

**Status:** draft · **Phase:** 2 · **Owner:** `supabase/migrations/0010_profiles_removed_at.sql`,
`backend/app/classrooms.py`, `backend/app/wordlist.py`, `frontend/app/classroom/**`,
`frontend/app/settings/**`
**Derived from:** `docs/specs/teacher-dashboard-docket.md` S2 · **Rationale:** ADR-017, ADR-021,
ADR-026, MASTER_SPEC §5 (CC-2, CC-4)

> A provisioning session. It answers how a classroom and its student accounts come to exist on a
> real device, and what shell every teacher screen lives in. It defines **no** book state, **no**
> review screen, and **no** meaning for `approved_at` (S3). It does not re-decide S1's authorization
> model — it is the first consumer of it.

## 1. Purpose

S1 shipped `teacher_router` with zero routes. `auth-and-classroom` S4-6 states plainly that
**classrooms and student accounts are hand-provisioned by SQL or the Supabase dashboard until this
row lands**. `auth-identity-and-classroom-schema.md` §6.1 names four credential operations and says
of all of them: *"Nothing here is built."*

This spec builds them, and the screens that carry them. The deployment moment it is designed for is
one sitting: a teacher with a fresh account, a class list, and ~35 children who must all be able to
log in before the lesson starts.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

None. `backend/contracts/` is untouched. Nothing here enters the pipeline.

## 3. Position in the system map

```
/signup (S1) ──▶ teacher, no classroom
      │
      ▼
/classroom ──── 0 classrooms ──▶ "Create your first classroom"
      │         1 classroom  ──▶ redirect into it
      │         2+           ──▶ picker
      │
      ▼  POST /classrooms                      (teacher_router)
/classroom/[id]  ── roster, read via RLS in the browser (S1-6)
      │
      ├─▶ /classroom/[id]/add
      │      textarea → live preview (browser, lib/nickname.ts)
      │      → POST /classrooms/{id}/students  (teacher_router + owned_classroom)
      │      → swap in place → SLIPS  ⚠ passwords exist only in this response
      │
      ├─▶ ⋮ Reset word  → POST …/students/{pid}/reset    → one slip
      ├─▶ ⋮ Remove      → POST …/students/{pid}/remove   → removed_at + ban
      ├─▶   Add back    → POST …/students/{pid}/restore  → one slip
      │
      └─▶ /classroom/[id]/settings   PATCH rename · DELETE cascade

/settings   display_name · password · account deletion NAMED, NOT SHIPPED
```

## 4. Decisions

Eleven open questions from the docket, resolved with the user 2026-08-07.

### 4.1 Roster entry is a bulk paste with a live preview (Q5)

One screen. The teacher pastes a class list, one name per line, and sees a preview table before
anything is created. The class list already exists in a spreadsheet; the deployment moment is a
single sitting; 35 sequential single-student forms is the hostile version of the same act.

**CSV upload was rejected** — file parsing, encoding guesses and column mapping for data that is one
column wide.

### 4.2 The nickname is reduced before it is stored (Q7, CC-2)

ADR-021 makes `nickname` peer-visible, and `auth-identity-and-classroom-schema.md` §3.1 puts it in
`auth.users.email` in cleartext. A pasted `Juan Dela Cruz` therefore publishes a child's full legal
name to 34 classmates and bakes it into an address that S1-5 makes permanent — no transfer, no
rename. So the paste is **reduced** before it becomes an identity.

A **"Shown to classmates"** control sits above the preview and applies to the whole paste:

| Preset | `display_nickname` | `nickname` |
|---|---|---|
| **First name only** *(default)* | `Juan` | `juan` |
| First name + last initial | `Juan D.` | `juan-d` |
| Full name | `Juan Dela Cruz` | `juan-dela-cruz` |

Reduction happens **before** normalization: split on whitespace, take the first token (and, for the
second preset, the first character of the last token). `lib/nickname.ts` then normalizes the result,
so §5.1's fourteen frozen vectors keep governing the output and are neither extended nor amended.

**The full name is never stored.** There is no column for it and this spec adds none. What the
teacher pasted survives only in their own browser, until they navigate away.

### 4.3 Collisions escalate per row, then ask (Q7)

`profiles_classroom_nickname` is unique on the *normalized* nickname, so `Maria Santos` and
`Maria Reyes` both reduce to `maria` under the default preset and collide. The preview resolves this
without an error:

1. **Level 0** — the chosen preset.
2. **Level 1** — on collision, *the colliding rows only* escalate to first name + last initial:
   `maria-s`, `maria-r`. The badge says why.
3. **Level 2** — still colliding, or no last token to escalate with (a single-token name such as
   `Madonna`), or a normalization rejection: the row is marked and **editable in place**, pre-filled
   with a suggested fix where one is unambiguous.

Collision is checked against **the roster the page already holds** — including removed students,
who keep their nickname reserved (§4.6) — and against the other rows of the same paste.

**Every preview row is editable.** Rejections (illegal character, under 2 or over 32 characters,
emoji, Baybayin — `auth-identity-and-classroom-schema.md` §5.1) are not errors to fix after
submitting; they are rows to fix before.

### 4.4 Passwords are generated word-pairs, shown once (Q6, Q8)

The backend mints `word-word-NN` from a module-level tuple of ~100 concrete nouns in
`backend/app/wordlist.py` — `tiger-lamp-27`. Roughly 10⁶ combinations, aimed at a **classmate
guessing**, which is the real threat model in a shared-device classroom; not at an outside attacker,
who has no address to attack. Typeable and memorable for a 10-year-old, which six random digits is
not.

**A shared class-wide password was rejected**: it makes every child able to log in as every other
child, which is precisely the isolation ADR-017 and `test_rls_isolation.py` exist to guarantee.

The password is returned **once**, in the creation response, and is never retrievable again — the
project stores no password material (`auth-identity-and-classroom-schema.md` invariant 4) and this
spec does not start. "Shown once" is safe because §4.5's reset can always mint another; the warning
on the slips screen says so in those words.

**Reset** (`auth.admin.update_user_by_id(id, {password})`) mints a new word-pair and renders one
slip. No forced rotation at first login and no "has changed password" flag — ADR-017, unchanged.

### 4.5 The slips screen is the only place a password exists (Q10)

After a successful create, the add screen **swaps in place** — it does not navigate — to a grid of
printable cards. Each card carries the three things a child types: the class code, their login
nickname, and their word.

- `@media print` styling; a card-per-child grid.
- **Copy all as text**, which leads on mobile (a teacher on a phone has no printer); **Print** leads
  on desktop.
- A `beforeunload` guard, and an in-page warning that names the recovery: *"Print or save now — these
  words are not shown again. You can reset any student's word later."*

This is also where the classroom code is surfaced at provisioning time. On the roster it lives in the
header, next to a copy-able `/join/[code]` link.

### 4.6 Removal is not deletion (Q9)

Today the cascade is total: delete `profiles` → `handle_profile_deleted` deletes `auth.users` →
`jobs` cascades (`0008:13`) → the child's books are gone, with their images orphaned in Storage
(`auth-identity-and-classroom-schema.md` C4). A child transferring out mid-year must not trigger
that.

**Two distinct acts:**

| Act | Effect | Reversible |
|---|---|---|
| **Remove from class** | `removed_at = now()` **and** ban the auth user | yes — *Add back* |
| **Delete permanently** | not shipped for a student in S2 | — |

**Both halves are required and neither is sufficient alone.** `removed_at` is what the roster reads,
in the browser, under RLS — but RLS cannot stop `signInWithPassword`. The ban
(`auth.admin.update_user_by_id(id, {"ban_duration": "876000h"})`, verified present in
`supabase_auth.types.AdminUserAttributes`) is what makes login fail — but it is invisible to the
browser client, which has no read on `auth.users`. Restore reverses both (`"none"`) and mints a fresh
word-pair, because the old one is unknowable.

**A removed student keeps their nickname reserved.** `profiles_classroom_nickname` is untouched, and
that is correct: their books still exist and are still attributed to that nickname.

### 4.7 Classroom delete ships; account delete is named and parked (Q19, Q20)

**`/classroom/[id]/settings`** carries rename, the immutable code (S1 §3.3), and a danger zone whose
copy states the counts it is about to destroy and which requires typing the classroom's name to arm.
Without it the only cleanup path for a test classroom is the Supabase dashboard — the
hand-provisioning this spec exists to end.

**`/settings`** carries `display_name`, a read-only email, a password change, and a danger zone that
**names account deletion and does not ship a button**. Deleting a teacher cascades every classroom,
every student and every book they own; that blast radius spans retention and guardian-request
territory, which is `data-deletion`'s row, not this one.

Counts for the classroom danger zone are read in the browser under `0008`'s teacher SELECT policies.
No endpoint exists to supply them.

### 4.8 One teacher, many classrooms (Q17)

The schema already permits it — `classrooms.owner_id`, and a teacher has no `classroom_id` of their
own. The product follows it. `owned_classroom` (S1) takes `classroom_id` from the **path**, which is
the shape this requires.

| Route | Screen |
|---|---|
| `/classroom` | picker · empty state · redirect when there is exactly one |
| `/classroom/[classroomId]` | roster |
| `/classroom/[classroomId]/add` | bulk paste → preview → slips |
| `/classroom/[classroomId]/settings` | rename · danger zone |
| `/classroom/[classroomId]/books` | **S3's**, named here only so the shell's nav is complete |
| `/settings` | teacher account |

`ROUTE_MAP.md` §3's sidebar + breadcrumbs is not adopted — S4-9 already ruled it input, not
authority, and a surface with four destinations does not earn a sidebar. The shell is a top bar: a
classroom switcher, two tabs, and the account menu.

### 4.9 The role check is server-side; every read after it is not (Q18)

`middleware.ts` stays **path-shaped and never reads the role** — S4-3 froze that, `ROUTE_MAP.md:196`
bans DB reads in middleware, and S1 §3.2 keeps the role out of the JWT. So a logged-in *student*
passes a path-only `/classroom` guard, exactly as they pass `/dashboard` today.

The check lands one layer down, in `TeacherShell`, mirroring what `StudentShell` already does at
`s/[profileId]/layout.tsx:50`. It is a **server component** deliberately: a browser-side role check
renders the teacher chrome for a beat before redirecting, and there is no other layer left to catch
it. That is one server read per shell mount — App Router keeps the layout alive across every
navigation *inside* `/classroom/**`, so it does not repeat.

**Everything below the shell is a client-side read through RLS**, per S1-6. The roster, the classroom
list, the danger-zone counts and (in S3) the books list are all browser fetches, so navigation
between teacher screens is client-side. Mutations render optimistically and reconcile against the
response.

**`TeacherShell` is a component, not a layout.** `/settings` is a sibling of `/classroom` and S4-2
froze route groups out, so the same server component is imported by `app/classroom/layout.tsx` and
`app/settings/layout.tsx`. It owns the single `profiles` read, the role check, the classroom
switcher, and log out — S4-7's rule applied to the other role.

### 4.10 Components are native platform elements

The teacher surface needs interactions the kid flow never did. They are built from the platform, not
from a new dependency:

| Need | Element |
|---|---|
| confirm dialog | `<dialog>` — focus trap, Esc, `::backdrop`, inert background, all native |
| Removed (n) section | `<details>` / `<summary>` |
| ⋮ row menu | popover attributes — light-dismiss and top-layer, native |
| toast | hand-rolled, ~20 lines |

**shadcn/ui was rejected**: it would add a `components/ui/` tree that is a second design system
alongside `DESIGN.md`'s neo-pop, while the kid flow stayed hand-rolled — the codebase would carry
both. Hand-rolling the dialog and menu was also rejected: focus trapping, Esc handling and
light-dismiss are exactly what is easy to get subtly wrong and what the browser already does
correctly.

### 4.11 Mobile-first

The teacher is as likely to be on a phone as a laptop.

- The roster is **cards below `sm`**, a table at and above it.
- The add screen offers **"Add one student"** — a single field — beside the paste box, for the
  latecomer case, which is the realistic phone task.
- **Copy all as text** leads on mobile; **Print** leads on desktop.
- The teacher surface uses `font-sans`, not the kid flow's `font-kid`.

## 5. The write surface

Every route hangs on S1's `teacher_router` and therefore passes `require_teacher` structurally
(S1-4). Every route with a classroom in its path takes `owned_classroom` and therefore fails **404**,
never 403 (S1-5). **There is no second teacher router**, and no route here is a read — S1-6 stands.

| Route | Body | Returns |
|---|---|---|
| `POST /classrooms` | `{name}` | the classroom row |
| `PATCH /classrooms/{classroom_id}` | `{name}` | the classroom row |
| `DELETE /classrooms/{classroom_id}` | — | 204 |
| `POST /classrooms/{classroom_id}/students` | `{students: [{display_nickname, nickname}]}` | `{created: [...], rejected: [...]}` |
| `POST /classrooms/{classroom_id}/students/{profile_id}/reset` | — | one credential |
| `POST /classrooms/{classroom_id}/students/{profile_id}/remove` | — | 204 |
| `POST /classrooms/{classroom_id}/students/{profile_id}/restore` | — | one credential |

A **credential** is `{profile_id, display_nickname, nickname, password}`. It is the only shape a
password ever travels in, and it is never persisted.

**The client sends both names, and the server does not trust the second.** The server derives
`nickname` by running `app/nickname.py`'s normalization over the submitted `display_nickname`, and
**discards the submitted `nickname` entirely** — the browser's reduction and preview are a UX
affordance, not an authority. A submitted `display_nickname` that normalizes to a rejection is a
`rejected` row, not a 500. `classroom_id` and the classroom code come from the path and the row,
never from the body (`auth-identity-and-classroom-schema.md` §6.3).

**Code minting** is unchanged from `auth-identity-and-classroom-schema.md` §6.2: six characters from
the 31-symbol alphabet, retried on unique violation. The collision is invisible to the teacher.

### 5.1 Bulk create is per-row, never per-batch

Row 17 colliding must not roll back rows 1–16. A teacher forced to redo 16 accounts will paste twice
and create duplicates. So each name is its own `auth.admin.create_user`; a failure lands in
`rejected` with a reason and the rest proceed.

The browser pre-validates, so `rejected` is normally empty — but the server is the authority, because
two teachers pasting the same list at once is a race the browser cannot see.

**Cap: 60 names per request**, 422 above it. A class is 35–40.

**Concurrency: a `ThreadPoolExecutor` of 5, results in submission order.** 40 sequential GoTrue
round-trips is ~15s of a spinner; five at a time is ~3s, which needs no progress UI.

```python
# ponytail: 5 concurrent creates keeps a 40-name class under ~3s. If a class list
# ever exceeds the 60 cap, the upgrade is a streamed response, not a bigger pool.
```

## 6. Behavior & edge cases

Per the docket's stance: the failures here are adult-facing and mostly irreversible, so they get the
same design care as the successes.

| Situation | Behavior |
|---|---|
| **Partial bulk create** | Slips render for `created`. `rejected` renders as a list with a reason each, **plus a textarea pre-filled with only the rejected names** — the retry is a fix-and-resubmit, not a re-derivation |
| **Network failure mid-create** | The teacher cannot know what landed. The roster is the truth, and **re-pasting the whole list is safe**: `profiles_classroom_nickname` rejects the ones that already exist as "already taken", so the second paste produces slips for exactly the ones that did not land. Idempotent by name |
| **Slips lost anyway** | *Reset word* on the roster row. The add screen's warning says this before it can happen, so the dialog is a caution, not a threat |
| **Unowned or nonexistent classroom** | `owned_classroom` 404 → "Classroom not found". Never "not yours" — the endpoint is not a classroom-existence oracle (S1-5) |
| **Deleting the classroom being viewed** | redirect to `/classroom` |
| **Student on `/classroom/**` or `/settings`** | `TeacherShell` redirects to `/s/{their id}`, mirroring `StudentShell`'s inverse |
| **Teacher with zero classrooms** | `/classroom` renders the create card. Not an error state — it is the first screen of the product for a new teacher |
| **Peer reads of the roster** | `0008:93` lets a *student* read classroom profiles, removed ones included. **Every peer-facing and teacher-facing list filters `removed_at is null` in the query** — S4-4's rule again: RLS does not scope a list, the query must |

### 6.1 Route reconciliation

S4-5 makes `/dashboard` this row's to replace wholesale, and S4-9 limits reconciliation to the routes
this spec touches.

| Change | Where |
|---|---|
| matcher gains `/classroom/:path*` and `/settings` | `middleware.ts:39` |
| `/dashboard` guard becomes `/classroom`, still path-only | `middleware.ts:15` |
| post-login redirect `"/dashboard"` → `"/classroom"` | `middleware.ts:19` |
| wrong-role escape link → `/classroom` | `s/[profileId]/layout.tsx:58` |
| `app/dashboard/` deleted | — |

## 7. Migration `0010`

```sql
alter table profiles add column removed_at timestamptz;
```

That is the whole migration.

- **No new policy.** `0008:101` "teachers read classroom profiles" already grants a teacher SELECT on
  their classroom's rows; the column rides along. `0008:93` does the same for peers, which is why
  §6's filter is mandatory.
- **`profiles_role_shape` untouched.** A removed student is still a student, still has a classroom,
  still has both nicknames, still has a NULL `display_name`.
- **`profiles_classroom_nickname` untouched** (§4.6).

⚠ **Flagged under `AGENTS.md` §2.** This is a schema change and is not implementable until an ADR
accepts it — the same posture S1 took with `0009`. The spec states the design; the ADR accepts it.

## 8. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-2 PII redaction** — §4.2 reduces a pasted full name to a first name before it becomes a
  permanent, peer-visible, cleartext identity. This **narrows** the concession
  `auth-identity-and-classroom-schema.md` §8 made under CC-2; it does not remove it, because a first
  name is still PII and still sits in `auth.users.email`.
- [x] **CC-4 Security (RLS + signed URLs)** — first consumer of S1's `require_teacher` /
  `owned_classroom`. Adds no policy, changes none, and adds no second authorization model.
- [ ] CC-1, CC-3, CC-5, CC-6, CC-7, CC-8, CC-9, CC-10 — not touched.

## 9. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

No new test infrastructure. Three existing homes plus colocated vitest.

| # | Test | File |
|---|---|---|
| 1 | Bulk create with one colliding name: the other rows still exist, collider is in `rejected` | `tests/test_main.py` |
| 2 | Bulk create is idempotent by name — the same paste twice yields the same roster | `tests/test_main.py` |
| 3 | 61 names → 422; 60 → accepted | `tests/test_main.py` |
| 4 | Minted password matches `word-word-NN` and is ≥ 8 characters | `tests/test_main.py` |
| 5 | Server ignores a submitted `nickname` that disagrees with its `display_nickname` and stores its own | `tests/test_main.py` |
| 6 | Remove sets `removed_at` **and** calls the admin API with `ban_duration` — both halves asserted | `tests/test_main.py` |
| 7 | Restore clears `removed_at` **and** sends `ban_duration: "none"`, and returns a new, different password | `tests/test_main.py` |
| 8 | A `display_nickname` that normalizes to a rejection lands in `rejected`, not a 500 | `tests/test_main.py` |
| 9 | Every classroom-scoped route 404s for another teacher's classroom | `tests/test_main.py` |
| 10 | Code mint retries on unique violation and succeeds | `tests/test_main.py` |
| 11 | `removed_at` is nullable and does not disturb `profiles_role_shape` | `tests/test_auth_schema.py` |
| 12 | A removed student's nickname stays reserved — re-adding the same name collides | `tests/test_auth_schema.py` |
| 13 | A teacher still reads a removed student's profile row | `tests/test_rls_isolation.py` |
| 14 | **A peer still reads a removed classmate's profile row** — the reason §6's query filter exists, asserted so it cannot be mistaken for RLS's job | `tests/test_rls_isolation.py` |
| 15 | Preview: `Maria Santos` + `Maria Reyes` under *First name only* escalate to `maria-s` / `maria-r` | vitest |
| 16 | Preview: `Madonna` colliding escalates to level 2, not to a crash | vitest |
| 17 | Preview: each of §5.1's rejection vectors marks its row editable rather than blocking submit | vitest |
| 18 | `beforeunload` is armed while slips are shown and disarmed after | vitest |
| 19 | Danger zone arms only on an exact name match | vitest |
| 20 | `TeacherShell` redirects a student, and a profile-less user | vitest |
| 21 | `guardRequest` on `/classroom/**` and `/settings` when logged out | vitest |

Tests 6 and 14 are the security core: 6 asserts the half of removal that RLS cannot do, 14 asserts
that RLS does not do the other half either — the query must.

**What is not tested, deliberately:** that GoTrue actually refuses a banned user's
`signInWithPassword`. That is Supabase's behavior, it needs a live auth server, and re-testing a
vendor's contract in CI buys nothing. Test 6 asserts we ask for it correctly; the rest is ADR-006's
bet on Supabase, already made.

## 10. Eval / quality checks (MASTER_SPEC §6 Tier B)

None. Nothing here is fuzzy.

## 11. Invariants

1. **The project stores no password material and no full name.** Passwords travel once, in a
   response; the pasted full name never leaves the browser.
2. **A nickname is server-normalized.** The browser's reduction is an affordance; `app/nickname.py`
   is the authority.
3. **Removal never destroys work.** `removed_at` + ban. A student's books survive their removal.
4. **Removal requires both halves** — the column for the roster, the ban for login. Either alone is a
   bug.
5. **Every list of students filters `removed_at is null` in the query**, never by relying on RLS.
6. **Every route in §5 is on `teacher_router`**, and every classroom-scoped one fails 404.
7. **`middleware.ts` never reads a role.** The role check is `TeacherShell`'s.
8. `backend/contracts/` is untouched. No `0008` policy is added, dropped or altered.

### Consequences worth stating

- **C1 — A banned student's existing JWT survives to expiry (~1h).** The ban blocks *refresh*, not an
  issued token. Removal is a roster action, not an emergency lockout. If an immediate lockout is ever
  needed, that is a session-revocation feature and a new decision.
- **C2 — A teacher who navigates away from the slips has lost those passwords permanently.** Mitigated
  by reset, warned before the fact, guarded by `beforeunload` — but not preventable, and that is the
  cost of storing no password material.
- **C3 — Two children named Maria are told apart by a last initial their teacher chose.** The default
  preset is a privacy floor, not a naming system; the level-2 editable row is the escape hatch when it
  does not fit.
- **C4 — Storage objects still do not cascade** on classroom delete
  (`auth-identity-and-classroom-schema.md` C4). Unchanged and still `data-deletion`'s.
- **C5 — A teacher can be deleted only from the Supabase dashboard.** Deliberate (§4.7).

## 12. Linked decisions & open questions

**Flagged under `AGENTS.md` §2 — needs an ADR before implementation.** `0010` adds a column to
`profiles`. Same posture as `0009`.

**Consumed as given (docket binding constraints):** S1-1 through S1-9; S3-7 (writes never through
RLS); S3-8; S4-2 (`/classroom/…`, no route groups); S4-3 (path-shaped middleware, never reads role);
S4-4 (the query scopes, not RLS); S4-5 (`/dashboard` is this row's to replace); S4-6; S4-7; S4-9;
S1-5 (one classroom for life); ADR-017; ADR-021; ADR-026.

**Deliberately not decided here:** anything about a book, the library, the review screen or
`approved_at` (S3); the gallery (`classroom-sharing`); retention periods, guardian-request deletion
and teacher-account deletion (`data-deletion`); the researcher role and `(research)/` routes
(`annotation-surface`).

## 13. Sequencing

1. **`0010` + tests 11–14.** The ADR gates this; nothing below depends on it except removal.
2. **`app/wordlist.py`, `app/classrooms.py` + tests 1–10.** Routes hang on `teacher_router`; nothing
   in the frontend consumes them yet.
3. **`TeacherShell`, `middleware.ts`, `/dashboard` deletion + tests 20–21.** The shell can ship
   against an empty `/classroom` before the roster exists.
4. **`/classroom`, the roster, `/classroom/[id]/settings`, `/settings`.**
5. **`/classroom/[id]/add` — preview, then slips + tests 15–19.** Last, because it is the only screen
   that depends on every part above.

Step 3 is the one that must not slip: deleting `app/dashboard/` while `middleware.ts:19` still
redirects there leaves every login at a 404.
