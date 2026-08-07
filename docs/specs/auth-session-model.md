# Feature Spec — auth: session model & trust boundary

**Status:** draft · **Phase:** 2 · **Owner:** `frontend/lib/supabaseClient.ts`,
`backend/app/main.py`
**Derived from:** `docs/specs/auth-and-classroom-docket.md` S2 · **Rationale:** ADR-006, ADR-017,
MASTER_SPEC §6 (CC-4)

> Not a schema session. This spec defines how each role proves who it is, where the session token
> lives, what the FastAPI boundary checks, and what an attacker holding only a job UUID gets. It
> defines **no** policy text (S3) and **no** URL or screen (S4).

## 1. Purpose

S1 established that every actor is a real `auth.users` row reachable via `signInWithPassword`.
`auth.uid()` therefore exists for all three roles, Supabase issues and refreshes sessions, and
Realtime authorizes unchanged. What S1 left open: where the token lives, what the FastAPI endpoints
require, and what happens to today's open resume hole at `main.py:94`.

This spec closes those gaps. When it is done, every request that can reach data has a named subject,
a named place the claim is verified, and a stated answer to "what does an attacker holding only a
job UUID get."

## 2. Session mechanism

All three roles log in via `supabase.auth.signInWithPassword()`. The email format differs by role:

| Role | Email |
|---|---|
| Teacher | Real email address |
| Student | `{nickname}@{code}.students.storybuddy.invalid` |
| Researcher | Real email address |

The student email is composed client-side at login time using the same normalization function
defined in S1 §5 (`frontend/lib/nickname.ts`). If the normalization implementation at login drifts
from the one used at account creation, children cannot log in. The test vectors in S1 §5.1 bind
both implementations.

**No S2 change to the normalizer.** The function already exists and is already tested.

## 3. Token storage: cookie via `@supabase/ssr`

`frontend/lib/supabaseClient.ts` replaces `createClient` from `@supabase/supabase-js` with
`createBrowserClient` from `@supabase/ssr`. All other call sites are unchanged — the client
object exposes the same interface.

`createBrowserClient` stores the session (access token + refresh token) in a cookie rather than
localStorage. This is the only change to the frontend client. Its consequence for S4: `middleware.ts`
can read the session server-side via `createServerClient` from `@supabase/ssr`, which is what
enables the route protection matrix in `ROUTE_MAP.md §4`.

**One new frontend dependency:** `@supabase/ssr`. No other new package.

### 3.1 Session lifetime

Supabase defaults, unchanged:
- Access token: 1 hour, auto-refreshed silently by `createBrowserClient` on every page load
- Refresh token: 60 days

A child in normal use never sees an expiry. If the refresh token expires or the cookie is cleared,
`middleware.ts` (S4 writes this) redirects:
- Student → `/join`
- Teacher → `/login`
- Researcher → `/login`

### 3.2 Session expiry mid-story

| Route | Outcome on expiry |
|---|---|
| `/s/[profileId]/write` | Redirected to `/join`. Draft is already lost on navigation (ROUTE_MAP.md:246) — expiry produces the same loss. S4 owns the confirmation dialog. |
| `/s/[profileId]/process/[jobId]` | The **job continues running** server-side. Child is redirected to `/join`, logs back in, and returns to the process route. Realtime subscription drops and reconnects. |
| `/s/[profileId]/book/[bookId]` | Redirected to `/join`. The book is durable — it is readable again after re-login. |

## 4. Frontend read path

No architecture change. All frontend reads stay as direct Supabase calls. `createBrowserClient`
automatically includes the session JWT in every query; RLS uses `auth.uid()` to enforce access
once S3 ships. Until S3 ships, all new tables are default-deny (S1 §7 C3).

`useJob.ts` is unchanged. Realtime is unchanged. No FastAPI proxy for reads.

## 5. FastAPI trust boundary

### 5.1 JWT verification dependency

```python
from fastapi import Header, HTTPException, Depends
from app.db import get_supabase_client

async def get_current_user(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing token")
    jwt = authorization.removeprefix("Bearer ")
    result = get_supabase_client().auth.get_user(jwt)
    if not result.user:
        raise HTTPException(401, "invalid token")
    return result.user
```

Verification is via `supabase.auth.get_user(jwt)` on the existing service_role client — one HTTP
round-trip to GoTrue per protected request. This catches revoked sessions, not only expired tokens.
**No new Python dependency.** `python-jose` and `PyJWT` are rejected: they cannot catch revocation,
and the performance gain is noise at N ≤ 15.

### 5.2 `POST /storybooks`

Takes `user = Depends(get_current_user)`. After token validation:

1. Look up `profiles WHERE id = user.id` to get `profile_id` and `classroom_id`.
2. Insert the job row with both values.

A client-supplied `profile_id` or `classroom_id` in the request body is ignored. Ownership is
always server-derived (S1 invariant 5).

**Only students have a `classroom_id`.** `profiles_role_shape` constrains this. A teacher or
researcher calling `POST /storybooks` will find their `classroom_id` is null, and the `NOT NULL`
constraint on `jobs.classroom_id` (S1 §4.2) will reject the insert — 500 today, but the correct
long-term answer is a 403 at the FastAPI layer before the insert is attempted. This spec names that
check; the exact HTTP response is an implementation detail for the plan.

### 5.3 `POST /jobs/{job_id}/confirm`

Takes `user = Depends(get_current_user)`. After token validation:

1. Query `jobs WHERE id = job_id AND profile_id = user.id`.
2. If zero rows: return 403. The caller holds a valid token but does not own this job.
3. If a row is found: proceed with existing confirm/try_again logic.

This closes `main.py:94`'s open resume hole. An attacker holding only a job UUID and no token gets
401. An attacker with a valid token for a different profile gets 403.

### 5.4 Worker: `service_role` is correct and permanent

The worker (`backend/worker/run_job.py`) is a trusted internal process running outside any request
context. It continues using `service_role` and deliberately bypasses RLS. This is not inherited from
the current state — it is a stated, intentional choice. The worker never accepts input from an
unauthenticated source; it is enqueued only by FastAPI after auth is verified.

## 6. Trust surface — complete answer

| Request | Subject | Verification point | Attacker with job UUID only gets |
|---|---|---|---|
| Supabase query on `jobs` (direct) | `auth.uid()` via JWT cookie | RLS policy (S3) | Default-deny until S3 ships |
| `POST /storybooks` | JWT Bearer | FastAPI `auth.get_user(jwt)` | 401 — no token |
| `POST /jobs/{id}/confirm` | JWT Bearer + ownership check | FastAPI | 401 (no token) or 403 (wrong owner) |
| Realtime subscription on `jobs` | JWT in cookie/header | Supabase Realtime | Unchanged today; S3 adds the policy |
| Worker reads/writes | `service_role` | GoTrue bypass (deliberate) | N/A — internal only |

## 7. Invariants

1. **The frontend never composes a synthetic email for teachers or researchers.** Only students.
2. **Ownership in `POST /storybooks` is always server-derived.** No client-supplied field is trusted.
3. **The confirm endpoint checks ownership before processing.** Holding a job UUID is not
   sufficient to resume a paused job.
4. **The worker bypasses RLS deliberately.** Any future worker entrypoint must also state this
   explicitly rather than inheriting it silently.
5. **There is one session mechanism for all roles.** Supabase `signInWithPassword` → cookie via
   `@supabase/ssr`. No second mechanism, no second substrate.

## 8. Tests (CI — MASTER_SPEC §6 Tier A)

**FastAPI (pytest, all mocked):**

1. `POST /storybooks` with no `Authorization` header → 401.
2. `POST /storybooks` with `Authorization: Bearer bad-token` (GoTrue rejects) → 401.
3. `POST /storybooks` with a valid teacher or researcher token → 403 (null `classroom_id` blocks
   insert). *Confirms S1 C1: neither a teacher nor a researcher can author a book.*
4. `POST /jobs/{id}/confirm` with no `Authorization` header → 401.
5. `POST /jobs/{id}/confirm` with valid token but `jobs.profile_id ≠ user.id` → 403.
6. `POST /jobs/{id}/confirm` with valid token and matching `profile_id`, job in
   `awaiting_confirm` → 200.

**Frontend (Vitest):**

7. After `signInWithPassword` succeeds, a Supabase session cookie is present in `document.cookie`.
8. `supabaseClient.ts` exports a `createBrowserClient` instance, not a `createClient` instance.
   *(Import assertion — fails if someone reverts the client.)*

**Intentionally absent:** Tests that an authenticated student can read their own jobs belong to S3,
not here. S2's tests assert the auth-or-not boundary only.

## 9. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-4 Security (RLS + signed URLs)** — `POST /storybooks` and `/confirm` now have a named
  subject. RLS enforcement point is unchanged (S3). The open-resume hole is closed.
- [x] **CC-2 PII** — no new PII collected or stored by this spec. The synthetic email composition
  happens client-side at login, not stored separately.
- [ ] CC-1, CC-3, CC-5, CC-6, CC-7, CC-8, CC-9, CC-10 — not touched by this spec.

## 10. Linked decisions & open questions

**Depends on:** S1 (students are real `auth.users` rows, role in `profiles`, `auth_role()` helper).

### Handoffs

**→ S3.** `auth.uid()` is the subject. `auth_role()` and `auth_classroom_id()` are the helpers.
RLS on `jobs` and the new tables can now be written. Realtime's authorization also becomes
expressible once S3 writes the policy. The Tier-A isolation tests S3 must add are distinct from
the auth-boundary tests above.

**→ S4.** The session is a cookie set by `createBrowserClient`. `middleware.ts` uses
`createServerClient` to read it. The protection matrix in `ROUTE_MAP.md §4` is now implementable.
Student session expiry redirects to `/join`; teacher/researcher to `/login`. The `/join` form
composing the synthetic email and calling `signInWithPassword` is entirely S4's.

### Finding, handed off

**S3 also owns the Realtime authorization tightening.** Today `useJob.ts` subscribes via the anon
key and the `jobs` table is under a permissive policy. Once S3 replaces that policy, the
subscription will need a valid JWT to satisfy the new `jobs` SELECT policy. `createBrowserClient`
will include the JWT automatically — no code change in `useJob.ts` — but S3 must test that the
Realtime channel still authorizes after the policy tightens.
