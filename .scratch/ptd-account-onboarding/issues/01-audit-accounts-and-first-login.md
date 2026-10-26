# 01 — Audit: accounts and first login

**Status:** ready-for-human
**Type:** research
**Progress:** investigated; phone walkthrough and hosted settings verification outstanding
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

## Audit findings — 2026-10-25

Evidence labels: **measured** means inspected repository/source or command output, not a live
production test. **Inferred** means a recommendation, estimate, or expected consequence.
No credentials, account passwords, environment files, or live project settings were read.

### Current flow

- **Measured:** The landing page links to `/welcome` and directly to `/join`
  (`frontend/app/page.tsx:41,83,89`). `/welcome` is a public role chooser, not a post-login
  welcome or tutorial. Its student button always opens `/join`; `action=signup` changes the
  teacher destination only (`frontend/app/welcome/page.tsx:12-14,66-72`). It calls the code
  "6-letter", although issued codes also contain digits (`backend/app/classrooms.py:13`).
- **Measured:** `/join` collects six characters, supports paste and keyboard movement, and disables
  submission until complete (`frontend/app/join/page.tsx:20-123,148-200`). `/join/[code]` then
  collects nickname and secret word, with Back and Show/Hide. It derives the synthetic email and
  signs in directly with Supabase (`frontend/app/join/[code]/page.tsx:33-98,135-275`). Invalid
  credentials share one message and return to the nickname step. Network exceptions have a separate
  message. There is no forgot-password/ask-teacher instruction on this login screen.
- **Measured:** Success immediately pushes `/s/<user.id>` (`join/[code]/page.tsx:91`). No first-use
  detection or forced password change appears in this path. Middleware checks session and matching
  profile ID, not password-change state (`frontend/middleware.ts:6-50`). Searches of frontend,
  backend, migrations, and docs found no implementation of the candidate forced-change flag names.
- **Measured:** Student layout reads profile/class identity and shows the greeting. A new empty shelf
  says "Your shelf is empty!" and offers "Write my first book"
  (`frontend/app/s/[profileId]/layout.tsx:26-31,89-102`, `page.tsx:139-160`). Mobile navigation is
  Bookshelf / Gallery / Profile (`frontend/components/StudentTabBar.tsx:6-53`). Profile settings
  contains avatars, then password change, then Log out. The ordinary header has no logout control
  (`frontend/components/StudentHeader.tsx:16-61`, `settings/page.tsx:234-305`). This contradicts
  auth-routes spec §7.1's first-class logout in the header, making shared-device handoff less obvious.
- **Measured:** Child settings checks only equality of new and confirmation values, uses HTML
  `required`, and calls `updateUser({ password })`. There is no local minimum, current-password
  input, or same-password check. It exposes Auth's raw error message. Success already says to ask
  the teacher if the password is forgotten (`settings/page.tsx:77-91,241-278`). Teacher settings
  checks equality and eight characters, but also lacks current-password verification and a pending
  submit state (`frontend/app/settings/page.tsx:62-85,142-174`). Server password policy is unknown.
- **Measured:** Provisioning creates email-confirmed accounts at
  `<nickname>@<code>.students.storybuddy.invalid`; creation/reset/restore return the issued password
  to the teacher (`backend/app/classrooms.py:85-131,175-190,207-225`). Reset requires the owning
  teacher through `owned_classroom`, then replaces the password. Restore also issues a new password
  and must be included in any forced-change design. No flag is set in any of these operations.
  Slips are shown after creation and after reset/restore, not retrieved as existing plaintext
  (`frontend/app/classroom/[classroomId]/add/page.tsx:154-155`,
  `frontend/app/classroom/[classroomId]/page.tsx:275-298`).
- **Measured:** Password minting uses two words plus two digits and Python `random`, not `secrets`
  (`backend/app/wordlist.py:1,26-30`). Replacing it with a cryptographic generator is a related
  credential-hardening consideration for ticket 02, not an edit made by this audit.

### Version and current-password options

**Measured:** Lockfile and installed directory names identify `supabase-js` / `auth-js` **2.110.1**,
`@supabase/ssr` **0.12.4** (`frontend/pnpm-lock.yaml:17-22,1223,1242,4531`). Installed
`auth-js/src/lib/types.ts:483-490` explicitly accepts `current_password`. Backend locks
`supabase-auth` **2.31.0** (`backend/uv.lock:2697-2698`). `supabase/.temp/gotrue-version` contains
**v2.197.0**. That cache is not proof of the currently deployed server or its settings.

| Option | Evidence and tradeoff | Assessment |
|---|---|---|
| Native `updateUser({ current_password, password })` | **Measured:** installed type supports it. Auth v2.197.0 checks the supplied current password only when `UpdatePasswordRequireCurrentPassword` is enabled, outside recovery sessions. No inbox required. Sending the field with the setting disabled does not verify it. | **Inferred:** smallest secure option for both roles, conditional on hosted setting verification. Enable only alongside updated forms, or existing changes will fail. |
| Re-sign-in before update | **Measured:** `signInWithPassword` creates/saves a session and emits `SIGNED_IN`. Synthetic email works without receiving email. | **Inferred:** fallback if native setting unavailable. Shared browser client changes the active session. An isolated nonpersistent client still creates an Auth session and adds rate-limit, cleanup, and failure handling. Verification and update remain separate operations. |
| FastAPI password-change endpoint | **Measured:** backend already verifies callers via `auth.get_user(jwt)` (`backend/app/auth.py:6-17`). Admin password update alone does not prove the old password. | **Inferred:** useful to own forced-change completion. Derive subject/email from verified caller, use a user-scoped native update or isolated re-sign-in, never trust a submitted target ID and never log password bodies. Adds an API contract and credential handling. |
| Secure password change / `reauthenticate()` | **Measured:** separate email/phone OTP nonce flow, required for sessions older than 24 hours when enabled. | **Inferred:** unsuitable for students with unreachable synthetic inboxes and does not check knowledge of the current password. Do not enable it as a substitute. |

Sources: [Supabase password security](https://supabase.com/docs/guides/auth/password-security),
[reauthenticate API](https://supabase.com/docs/reference/javascript/auth-reauthenticate),
[Auth v2.197.0 update handler](https://github.com/supabase/auth/blob/v2.197.0/internal/api/user.go),
[JS client source](https://github.com/supabase/supabase-js/blob/v2.110.1/packages/core/auth-js/src/GoTrueClient.ts).
**Measured:** Auth's [changelog](https://github.com/supabase/auth/blob/master/CHANGELOG.md) records
current-password support in 2.187.0 and the PKCE recovery exemption fix in 2.189.0. The main
[changelog](https://supabase.com/changelog) was also checked. No relevant password breaking change
was found there. The Markdown index could not be fetched, so the HTML index was used.

### Flag location and enforcement

| Location | Trust, freshness, and cost |
|---|---|
| `user_metadata` | **Measured:** users can edit it. Reject for an enforcement flag. |
| `app_metadata.must_change_password` (proposed, does not exist) | **Measured:** privileged writes only, and middleware already calls Auth `getUser()`. **Inferred:** smallest route-level implementation, with no application table-column change or extra middleware database read. Fresh `getUser()` data can supply it. JWT copies remain stale, so JWT-only RLS cannot immediately enforce reset. Privileged completion must preserve other metadata and must not let an older completion clear a newer reset. |
| `profiles.must_change_password` (proposed, does not exist) | **Measured:** existing migrations deny ordinary profile updates (`0017_research_pair_blinding.sql:29-31`), and profiles already underpin RLS. **Inferred:** better fit for fresh database enforcement and conditional state transitions, but requires a schema migration, protected writes, backfill policy, and an additional middleware read. The latter conflicts with auth-routes spec §2's current no-database-fetch rule and needs explicit amendment. |

Trust/freshness sources: [Supabase RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security#authjwt)
and [getUser API](https://supabase.com/docs/reference/javascript/auth-getuser).

**Inferred recommendation:** Carry the protected `profiles` option into ticket 02 if "forced" means
no product access until completion. It gives database policies a current source of truth. Use
`app_metadata` only if its freshness and race handling are explicitly solved across all boundaries.
Do not implement both flags or make a client callback clear either flag.

**Measured:** Middleware only covers Next.js routes. FastAPI accepts bearer requests independently,
and the frontend reads Supabase directly. `POST /storybooks` checks classroom membership but no
onboarding state (`backend/app/main.py:140-155`); migrations likewise lack a forced-change predicate.
**Inferred:** middleware is the sole page auth gate, but is not a substitute for API/RLS enforcement.
Ticket 02 must define which reads, writes, Storage signing, and Realtime access are blocked and apply
the authoritative check there. A route redirect alone is bypassable.

**Inferred proposed lifecycle, not an accepted design:** create/reset/restore set required state;
middleware directs every signed-in student entry/deep link to the forced-change route. Allow that
route and signout without loops. A trusted operation verifies the old password and changes it before
clearing state. Errors leave the gate closed. Missing state needs an explicit legacy-account rollout
rule. Reset and completion need ordering/version protection so delayed completion cannot clear a
new reset. Password update succeeding while flag clearing fails must have an idempotent recovery
path using the now-current password. These transaction/race questions belong in ticket 02 and the
decision backlog, not a speculative implementation here.

**Schema answer:** native current-password verification alone needs no application schema change.
The recommended protected profiles flag does. App metadata avoids a new table column, but strict
database enforcement can still require policy/helper SQL. Either design touches auth and requires
owner approval under AGENTS.md. Ticket 02 must amend auth-routes §7.3 (which explicitly accepts a
session instead of the current password), plus the schema/authorization specs if that option wins.
ADR-017 already permits child password changes and teacher-only recovery. No ADR change was made.

### Edge cases and classroom cost

- **Inferred:** force change after every teacher reset and restore, not just first provisioning.
  The teacher sees only the replacement secret word. Never store or expose the child-chosen password.
  Keep the existing success guidance and add before submission: "Choose a password you can remember.
  If you forget it, ask your teacher for a new secret word." Next login must explain that the child's
  chosen password replaces the slip's secret word, despite the current "Secret word" label.
- **Measured:** Auth v2.197.0 rejects a new password equal to the current password. **Inferred:**
  also show a child-legible local message for equality and weak passwords, with server enforcement
  as the authority. Grade 5–6 password rules remain a ticket 02 decision. An eight-character rule
  would match the current teacher UI but is not established by this audit as sufficient policy.
- **Inferred:** the forced screen needs its own visible Log out, pending/disabled submit, retryable
  network and incorrect-current-password errors, confirmation, Show/Hide, labels, keyboard submission,
  and focus handling. Reuse the existing design language. Do not rely on reaching Profile to escape.
- **Measured:** signout clears `sb-*` cookies and redirects to `/login`, including student signout
  (`frontend/app/auth/signout/route.ts:9-11,34-45`). **Inferred:** ticket 02 should decide a child
  return to `/join` while preserving stale-session recovery. Shared-device acceptance must include
  account identity, logout before handoff, browser Back, multiple tabs, autofill, and expired sessions.
- **Measured from upstream source, not live:** normal password update retains the initiating session
  and revokes others; admin reset revokes all refresh sessions. Existing access JWTs can outlive
  revocation until expiry. See [Auth password storage](https://github.com/supabase/auth/blob/v2.197.0/internal/models/user.go),
  [admin reset handler](https://github.com/supabase/auth/blob/v2.197.0/internal/api/admin.go), and
  [session validity](https://supabase.com/docs/guides/auth/sessions#how-to-ensure-an-access-token-jwt-cannot-be-used-after-a-user-signs-out).
  **Inferred:** test reset against an already-open device and direct requests, not just fresh login.
- **Inferred support estimate:** no reset telemetry was found, so there is no measured forecast.
  For 40 pupils, assumed extra forgetting rates of 5% / 10% / 20% imply **2 / 4 / 8 resets** per
  teaching period. At an assumed 2–3 minutes to identify the child, reset, deliver the word, and
  supervise another change, that is **4–6 / 8–12 / 16–24 teacher minutes**. These are scenarios,
  not observed rates. Pilot and count resets without recording passwords.
- **Inferred delivery estimate:** 0.5–1 developer day for current-password forms, setting verification,
  and focused tests. Another 2–4 days for a securely enforced forced-change lifecycle, policies,
  reset/restore and race recovery, spec amendments, and shared-device/mobile checks. No new service,
  dependency, image generation, or email delivery is needed for the recommended password mechanism.
  Hosting cost was not priced. Profiles adds one middleware database read per matched request;
  Auth already incurs `getUser()`. Password verification adds hashing work, not a second sign-in.

### Verification and decision

**Measured:** source trace and official documentation support the findings above. Hosted settings,
deployed schema, actual reset behavior, and classroom reset rates remain unverified.

Commands and results:

- From `frontend/`: `pnpm.cmd exec vitest run 'app/join/page.test.tsx'
  'app/join/[code]/page.test.tsx' 'app/s/[profileId]/settings/page.test.tsx'
  'app/login/page.test.tsx' 'middleware.test.ts'` (one command) → **5 files passed, 65 tests passed**,
  91.33 seconds. These existing mocked tests verify current UI/guard behavior, not hosted Auth
  settings or a proposed forced-change flow. `pnpm.cmd` is the Windows launcher for pnpm.
- `git diff --check` → exit 0, with line-ending warnings only.
- Initial `pnpm dev --port 3100` → PowerShell script execution disabled. `pnpm.cmd` then hit
  sandbox `EPERM` reading Corepack's `lastKnownGood.json`. An approved retry reached Next.js,
  then exited with `Another next dev server is already running.` No server was stopped.
- Installed Auth source initially returned `Access is denied`; an approved read confirmed
  `current_password?: string` in the installed types. The repository search also encountered
  inaccessible `.pytest_cache` directories, which are not application source.
- Skipped: full frontend lint/build/test and backend suite, because this change edits research
  notes only. No RLS, provider, live password, or authenticated mobile tests were run.

**Phone walkthrough is outstanding.** Source inspection establishes the sequence and responsive
classes, not a rendered phone result. CUA returned no available browsers. A placeholder-configured
`pnpm.cmd dev --port 3100` attempt exited because an existing Next dev server owns this checkout
on port 3000. That server was left untouched. No authenticated walkthrough was attempted. A follow-up
needs a browser and user-controlled sign-in, or an explicitly approved disposable test account.
Check 360px and 390px widths, the on-screen keyboard, code paste, nickname/back, secret-word errors,
empty shelf, Profile password change, and logout. Do not claim mobile visual acceptance yet.

**Go/no-go (inferred):** **GO to ticket 02's decisions and spec amendment. NO-GO to implementation
or release on this audit alone.** Verify the hosted current-password setting/version, finish the
phone walkthrough, and approve flag ownership, enforcement scope, legacy-account treatment, and
reset/completion race handling first. A middleware-only forced-change screen is not secure enforcement.
