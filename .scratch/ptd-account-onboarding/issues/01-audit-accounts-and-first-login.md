# 01 — Audit: accounts and first login

**Status:** ready-for-agent
**Type:** research
**Progress:** open
**Blocked by:** None
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

## Question

What does a child's first login and a password change look like today, and what is the smallest
secure way to add a forced change after the secret word and a current-password check?

## Starting evidence (2026-10-25)

Read during the grill, not yet audited:

- The student password form calls `supabase.auth.updateUser({ password })` with no current password
  and no minimum length: `frontend/app/s/[profileId]/settings/page.tsx:83`.
- The teacher form does the same with an 8-character minimum: `frontend/app/settings/page.tsx:70-74`.
- No "must change password" flag was found in `frontend/`, `backend/app/` or `supabase/migrations/`.
- A teacher reset endpoint exists: `backend/app/classrooms.py:176`.
- The child enters the secret word on `frontend/app/join/[code]/page.tsx`. A `/welcome` route
  exists; what it shows is unchecked.

## Investigate

- How the current password can be verified for both roles. Candidates: re-sign-in with it before
  `updateUser`, a FastAPI endpoint, or a Supabase Auth setting. Check the installed supabase-js and
  Auth version, and whether any option needs an email the synthetic student accounts cannot receive.
- Where a forced-change flag can live so the child cannot clear it themselves. `user_metadata` is
  writable by the user. Compare a `profiles` column with `app_metadata`.
- Where the flag is enforced. `middleware.ts` is the only auth gate (`AGENTS.md`).
- What the first-use path shows today, end to end, on a phone. Use `docs/specs/auth-routes-and-account-ux.md`.

## Edge cases the answer must cover

- A teacher reset issues a new secret word and must turn the forced change back on.
- A child who forgets the new password: the teacher reset is the way back, so the copy must say so.
- The teacher cannot see a child-chosen password. Estimate the extra reset load.
- A weak password, or one that equals the secret word.
- The forced-change screen still needs a way out (log out).
- Shared classroom devices.

## Done when

- Findings are labelled *measured* or *inferred*, with file references.
- Options for the current-password check and the flag location, each with tradeoffs.
- Whether a schema change is needed (an approval gate under `AGENTS.md`).
- Cost estimate and a go/no-go.

## Comments
