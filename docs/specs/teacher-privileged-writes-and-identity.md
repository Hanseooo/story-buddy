# Feature Spec — teacher: privileged writes & identity

**Status:** draft · **Phase:** 2 · **Owner:** `supabase/migrations/0009_teacher_identity.sql`,
`backend/app/auth.py`
**Derived from:** `docs/specs/teacher-dashboard-docket.md` S1 · **Rationale:** ADR-006, ADR-017,
ADR-026, MASTER_SPEC §6 (CC-4)

> An authorization session. It answers three questions and no others: how a teacher identity comes
> to exist, what authorizes a write that bypasses RLS, and whether teacher reads go through RLS or
> FastAPI. It defines **no** endpoint body (S2, S3), **no** screen beyond repairing the one it
> breaks, and **no** meaning for "approved" or "rejected" (S3).

## 1. Purpose

The auth docket gave every actor a row, a role, and a policy set. It did not give the system a way
to create the *first* actor. `handle_new_user` sources every profile column from
`raw_app_meta_data`, which no browser client can write — so the shipped `/signup` page cannot
produce a teacher, and `docs/specs/auth-identity-and-classroom-schema.md` §7's operations table has
a row for creating a student and none for creating a teacher.

At the same time, S3-7 froze every write in this feature as a service_role write behind FastAPI.
service_role bypasses RLS by construction, so the four policies `0008` grants teachers protect
exactly nothing on the write path. Today `get_current_user` (`app/main.py:21`) proves a token is
valid and checks nothing else — there is no code anywhere that has ever read `profiles.role` for an
authorization decision.

This spec closes both: the identity-creation path end-to-end from an empty database, and the named
principal + named check + named home for every privileged write S2 and S3 will add.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

None. `backend/contracts/` is untouched. Nothing here enters the pipeline.

## 3. Position in the system map

```
/signup  ──signUp({email, password, options.data.display_name})──▶  auth.users insert
                                                                          │
                                                            handle_new_user (0009)
                                                                          │
                                                          profiles{role:'teacher', display_name}
                                                                          │
/login   ──signInWithPassword──▶ cookie ──▶ auth_role() = 'teacher' ──▶ 0008's SELECT policies
                                                                          │
                        ┌─────────────────────────────────────────────────┴──────────────┐
                        │                                                                │
                READS: browser client, RLS                              WRITES: FastAPI, service_role
                (0008 policies, unchanged)                              get_current_user
                                                                             → require_teacher
                                                                             → owned_classroom
                        │
              EXCEPTION: approved_at UPDATE — browser, RLS (S3-8),
              narrowed to one column by 0009's grant
```

## 4. Behavior & edge cases

### 4.1 The trigger — role is a constant, never a request value

`raw_user_meta_data` is client-controlled: `signUp({options: {data: {...}}})` writes it verbatim.
`raw_app_meta_data` is not — only the admin API can set it. **Therefore the role of a self-serve
signup cannot be read from the request at all.** It is a constant.

```sql
create or replace function public.handle_new_user() returns trigger
  language plpgsql security definer set search_path = '' as $$
declare
  v_role text := coalesce(new.raw_app_meta_data ->> 'role', 'teacher');
begin
  insert into public.profiles (id, role, classroom_id, nickname, display_nickname, display_name)
  values (new.id,
          v_role,
          (new.raw_app_meta_data ->> 'classroom_id')::uuid,
          new.raw_app_meta_data ->> 'nickname',
          new.raw_app_meta_data ->> 'display_nickname',
          case when v_role = 'student' then null
               else coalesce(new.raw_app_meta_data  ->> 'display_name',
                             new.raw_user_meta_data ->> 'display_name',
                             split_part(new.email, '@', 1))
          end);
  return new;
end $$;
```

Two changes from `0007`, and both are load-bearing:

- **`coalesce(… ->> 'role', 'teacher')`.** Absent `app_metadata` ⇒ teacher. The admin channel is
  untouched, so S2's `auth.admin.createUser` and hand-provisioned researchers keep working exactly
  as `auth-identity-and-classroom-schema.md` §6.1 specifies.
- **`display_name` is role-conditional.** `profiles_role_shape` requires `display_name IS NULL` for
  students and `NOT NULL` for teachers and researchers. An unconditional fallback would give a
  student `'juan'` from `juan@abc123.students.storybuddy.invalid` and break S2's provisioning
  before S2 is written. The `case` is not defensive styling; without it the constraint fires.

`display_name`'s three-step fallback covers all three creation paths: `app_metadata` for
hand-provisioned researchers, `user_metadata` for self-serve teachers, email localpart so no row
can violate `NOT NULL` regardless of how it was created. `display_name` is client-controlled on the
self-serve path and that is acceptable — it is a display string with no authorization meaning.
`role` is the only column that decides anything, and it is the one column no client can influence.

`split_part` and `coalesce` resolve under `search_path = ''` because `pg_catalog` is always
implicitly searched.

### 4.2 `/signup` — repairing what the trigger fix exposes

`frontend/app/signup/page.tsx` is S4-frozen. This is a repair of the defect in §1, not a redesign:

- **One new field, "Your name"** → `options.data.display_name`. Required, because
  `profiles_role_shape` needs it and the email-localpart fallback is a floor, not a UX.
- **`signUp`'s error is checked.** Today it is discarded and "Check your email" renders
  unconditionally (`page.tsx:16-18`) — which is how a 500 from the aborted trigger has been
  invisible.

**The non-disclosure behavior must survive.** `auth-routes-and-account-ux.md` §6.2 requires signup
with an existing email to render "check your email". Supabase does not return an error in that case
— it returns a user object with an empty `identities` array. So checking `error` surfaces genuine
failures (weak password, malformed email, network) **without** re-introducing an account-existence
oracle. Rendering rule: `error` present → error state; otherwise → "check your email", unchanged.

Nothing else on the page moves. Retheming is not in scope and neither is `/login`.

### 4.3 Authorization — `backend/app/auth.py`

`get_current_user` moves here from `app/main.py:21`, behavior unchanged. It is the base of the
authorization chain and does not belong in the app module; `main.py` imports it. Two dependencies
join it:

```python
def require_teacher(user=Depends(get_current_user)) -> dict:
    rows = (get_supabase_client().table("profiles")
            .select("id, role").eq("id", user.id).execute().data)
    if not rows or rows[0]["role"] != "teacher":
        raise HTTPException(403, "teachers only")
    return rows[0]


def owned_classroom(classroom_id: str = Path(...), teacher=Depends(require_teacher)) -> dict:
    rows = (get_supabase_client().table("classrooms").select("*")
            .eq("id", classroom_id).eq("owner_id", teacher["id"]).execute().data)
    if not rows:
        raise HTTPException(404, "classroom not found")
    return rows[0]


# ponytail: no prefix — S2 and S3 own endpoint paths. This exists so the role
# check is on the router, not on each handler, and cannot be forgotten.
teacher_router = APIRouter(dependencies=[Depends(require_teacher)])
```

**Why two dependencies and not one.** Role and ownership fail differently. Role is a property of
the caller, checkable before any row is read — so it belongs on the router, where a new endpoint
inherits it by existing. Ownership is a property of the *target row*, knowable only per-route — so
it belongs in the handler signature, where it is visible in review. Collapsing them into one
per-endpoint check means an omission is silent and looks like nothing.

**Status codes.**

| Condition | Code | Why |
|---|---|---|
| No / malformed `Authorization` header | 401 | unchanged from `get_current_user` |
| Token does not resolve to a user | 401 | unchanged |
| No `profiles` row for the subject | 403 | fail closed — a valid token with no profile authorizes nothing |
| `role != 'teacher'` | 403 | student or researcher on a teacher route |
| Classroom absent, or owned by someone else | **404** | 403 would confirm the row exists; the endpoint must not be a classroom-existence oracle |

`owned_classroom` depends on `require_teacher`, and FastAPI caches dependencies per request, so a
route carrying both runs the `profiles` read once.

`teacher_router` is mounted in `main.py` with zero routes. S2 and S3 hang routes on it. **There is
no second teacher router.**

### 4.4 The read/write rule

> **Every teacher read goes through the browser client under RLS. Every teacher write goes through
> FastAPI under service_role. One exception: `approved_at`, an RLS UPDATE from the browser (S3-8).**

Reads via RLS costs nothing — `0008` already grants teachers four SELECT policies (`jobs`,
`classrooms`, `profiles`, `storage.objects`), all gated on `owner_id = auth.uid()`, all covered by
`test_rls_isolation.py`. Routing reads through FastAPI instead would orphan working, tested policies
and leave them to be maintained as dead code. This is the same split the student surfaces already
use, so it is one model applied consistently rather than two models in one feature.

### 4.5 Closing the column hole under S3-8

S3-8 is binding and is not reopened: the teacher's `approved_at` UPDATE is an RLS write from the
browser. But **RLS cannot restrict which column an UPDATE touches**, which `0008:50` notes and does
not close. Supabase grants `authenticated` full DML on `public` by default, so today a teacher's own
JWT against the anon endpoint can run `update jobs set input_text = …, pages = …` on any row in
their classroom. The policy checks ownership and stops. *"The only legitimate caller sets only
`approved_at`"* is a statement about our client, not a constraint on the system.

Postgres closes this below RLS:

```sql
revoke update on public.jobs from authenticated;
grant  update (approved_at) on public.jobs to authenticated;
```

Column privileges are checked before policies, so the UPDATE policy keeps its exact semantics and
the write surface narrows to the one column S3-8 already says is the only one anyone should set.
This does not re-decide S3-8 — it makes S3-8 true in the database rather than by convention.

INSERT and DELETE need no equivalent: S3-7's denial-by-absence-of-policy already covers them.
`service_role` is unaffected — the revoke names `authenticated` only, and service_role bypasses both
layers.

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-4 Security (RLS + signed URLs)** — narrows the one RLS write surface `0008` left open
  (§4.5) and gives every future service_role write a named check (§4.3). Adds no policy and changes
  no existing one.
- [ ] CC-1, CC-2, CC-3, CC-5, CC-6, CC-7, CC-8, CC-9, CC-10 — not touched.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

No new test infrastructure. Each group lands where its machinery already lives:

| Tests | File | Why there |
|---|---|---|
| 1–6 (trigger) | `tests/test_auth_schema.py` | already tests `handle_new_user` (its tests 4–11); `psycopg` + `SUPABASE_DB_URL`, skips in CI |
| 7–9 (grants) | `tests/test_rls_isolation.py` | carries the `authenticated`-role and JWT-claim machinery a grant test needs |
| 10–15 (dependencies) | `tests/test_main.py` | `dependency_overrides`, no DB |

⚠️ Tests 1–6 **must not** use `test_rls_isolation.py`'s `_auth_user` helper — it sets
`session_replication_role = replica` to suppress triggers, which is precisely what these tests
exercise.

| # | Test | Asserts |
|---|---|---|
| 1 | Insert `auth.users` with **no** `app_metadata` | `profiles` row exists, `role = 'teacher'` — **fails today**, this is the defect |
| 2 | Same, with `user_metadata.display_name` | `display_name` is the supplied value |
| 3 | Same, with no metadata at all | `display_name` is the email localpart |
| 4 | `app_metadata.role='student'` + classroom + nicknames | still a student; **`display_name IS NULL`** — §4.1's `case` |
| 5 | **`user_metadata.role = 'researcher'`** | profile is **`teacher`** — the privilege-escalation attempt |
| 6 | `app_metadata.role='researcher'`, `display_name` set | still a researcher — hand provisioning intact |
| 7 | `authenticated` sets `approved_at` on an owned job | succeeds |
| 8 | **`authenticated` sets `input_text` on an owned job** | **denied by grant, before RLS is consulted** |
| 9 | `service_role` sets `input_text` | succeeds — the revoke does not touch the worker |
| 10 | Student token on a `teacher_router` route | 403 |
| 11 | Valid token, no `profiles` row | 403 |
| 12 | No `Authorization` header | 401 |
| 13 | Teacher, own classroom id | dependency returns the row |
| 14 | Teacher, another teacher's classroom id | **404**, not 403 |
| 15 | Teacher, nonexistent classroom id | 404 — indistinguishable from 14 |

Tests 1 and 5 are the security core: 1 is the shipped defect, 5 is the vulnerability the naive fix
would have introduced. Both are written before the migration, per `AGENTS.md` §4.

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

None. Nothing here is fuzzy.

## 8. Invariants

1. **A self-serve signup can only ever produce a teacher.** Role is a constant in the trigger, never
   a request value.
2. **`raw_user_meta_data` is never read for an authorization decision** — only for `display_name`.
3. **No `profiles` row ⇒ no authorization.** Every check fails closed.
4. **Every teacher write that bypasses RLS passes `require_teacher`,** because the check is on the
   router, not the handler.
5. **Ownership failures are 404s**, never 403s.
6. **`authenticated` can write exactly one column of `jobs`: `approved_at`.**
7. `backend/contracts/` is untouched. No policy in `0008` is added, dropped, or altered.

### Consequences worth stating

- **C1 — Anyone with the anon key can mint a teacher account.** That is ADR-017's stated posture
  ("self-serve teacher signup", no further gate per `auth-routes-and-account-ux.md` §6.2), not an
  oversight. The blast radius is bounded: a new teacher owns no classroom, and every teacher policy
  in `0008` gates on `owner_id = auth.uid()`, so they can see nothing. On a shared classroom device
  a child could reach `/signup` and create one; they would get an empty account isolated from their
  own classroom. If this is ever unacceptable, the fix is a gate on signup, which is an ADR-017
  amendment and not a change to this spec.
- **C2 — An unconfirmed teacher already has a `profiles` row.** The trigger fires on the
  `auth.users` insert, which precedes email confirmation. Harmless — they cannot log in until
  confirmed — but it means `profiles` is not a roster of usable accounts.
- **C3 — The "self-serve ⇒ teacher" rule lives in SQL,** invisible from application code. This is
  the accepted cost of not owning an account-minting endpoint; §4.1's comment and test 1 are the
  mitigation.

## 9. Linked decisions & open questions

**Flagged under `AGENTS.md` §2/§5 — needs an ADR before implementation.** `0009` alters a
`security definer` trigger on `auth.users` and changes a table grant. Both are auth-surface changes
and neither is decided by this spec; the spec states the design, the ADR accepts it.

**Consumed as given (docket binding constraints):** S3-7 (writes never go through RLS), S3-8
(`approved_at` is the sole RLS write path), S3-5, S4-2 (`teacher-dashboard` extends under
`/classroom/…`), ADR-017 (manual approval always; self-serve teacher signup with no further gate).

**Deliberately not decided here:** any endpoint's path, request body, or response (S2, S3); any
screen other than the `/signup` repair; what "approved" or "rejected" means (S3); the researcher
role and `(research)/` routes (`annotation-surface`).

**Found, not this spec's work:** `AGENTS.md:454` asserts S3's Tier-A isolation suite "is not built".
It is — `backend/tests/test_rls_isolation.py` carries 31 tests covering S3's tests 1–25 and 28–33,
with 26–27 documented as requiring a WebSocket client and out of scope for pytest. This is a
`Definition of Done` finding-propagation miss from the S3 build. Recorded in the docket's
*Found & parked*.

## 10. Sequencing

Three parts, and the order is forced:

1. **Tests 1–6** (trigger) written and failing, then `0009`'s `create or replace`. The signup defect
   is fixed at this point; everything else is additive.
2. **Tests 7–9** (grants) written and failing, then `0009`'s revoke/grant. Independent of part 1 —
   same migration only because both are one-line auth-surface changes needing one ADR.
3. **`app/auth.py` + tests 10–15.** No route consumes `teacher_router` until S2. Shipping it with
   zero routes is the deliverable of an authorization session, not scaffolding: it is what makes
   invariant 4 structural rather than aspirational.

The `/signup` client repair (§4.2) lands with part 1 — the trigger fix without the name field leaves
every teacher named after their email localpart.
