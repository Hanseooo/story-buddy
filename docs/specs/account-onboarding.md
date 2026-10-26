# Feature Spec — Account onboarding and password changes

**Status:** implementation in progress | **Phase:** post technical defense | **Release:** real Auth/socket/device evidence outstanding
**Owners:** frontend auth/student surfaces, FastAPI account operations, Supabase authorization
**Derived from:** [ticket 02](../../.scratch/ptd-account-onboarding/issues/02-grill-onboarding-spec.md),
the owner-confirmed interview and image-link exception (2026-10-26), and ADR-073–078 (linked in §8).
**Verification boundaries:** confirmed by the owner during synthesis (2026-10-26).

**Execution approval (2026-10-26):** After approving and publishing the ticket breakdown, the owner
approved proceeding through tickets 03–07 and the proposed product recommendations below.
Technical proof, final lifecycle/API contracts and hosted evidence remain prerequisites, not facts
established by that approval. See [ticket 03](../../.scratch/ptd-account-onboarding/issues/03-approve-onboarding-contracts.md).

## 1. Purpose and scope

Give Grade 5–6 students a short path from a teacher-issued secret word to a password they choose,
followed by a brief explanation of navigation. Require the current password for student and teacher
password changes. Prioritize usability with an eight-character minimum and recovery that does not
turn partial completion into another teacher reset.

Included: new student accounts, teacher resets/restorations, existing-account exemption, protected
access restriction, settings changes, completion recovery, and a dismissible navigation introduction
remembered across devices. Student recovery remains teacher-only, with classroom isolation (ADR-017).

Excluded: new dependencies/services, student signup or
self-service/email recovery, teacher first-login rotation, a guided tour/navigation redesign,
password storage outside Auth, and pipeline/Story Memory/model/research changes.

### Existing behavior and amendment scope

Baseline before the settings implementation below, verified by source inspection, not a hosted test:

- `/join/[code]` signs in with code + nickname + secret word, then routes to `/s/<user.id>`.
  `/welcome` is a public role chooser, not an authenticated tutorial.
- `frontend/middleware.ts` calls `getUser()` and guards paths/identity without onboarding state.
  FastAPI bearer requests and direct Supabase queries have separate authorization boundaries.
- Student settings calls `updateUser({ password })` without a current password or minimum length.
  Teacher settings enforces eight characters but also lacks current-password verification.
- `backend/app/classrooms.py` owns create/reset/restore; reset and restore issue fresh words.
  `backend/app/wordlist.py` uses Python `random` for two words and two digits.
- `StudentTabBar.tsx` has Bookshelf, Gallery, Profile. Profile opens student settings, which contains
  password change and Log out. `/auth/signout` clears cookies and currently returns to `/login`.
- The proposed required-change and introduction-dismissal state is not implemented in the inspected
  code. Deployed schema and hosted Auth settings were not inspected during synthesis.

### Implemented subset and evidence - 2026-10-26

The owner's repeated proceed instruction authorized implementation. Required password replacement,
settings proof, student lifecycle, enforcement and navigation introduction now exist in the working
tree. The concrete contract is in section 7. No hosted deployment or release acceptance is claimed.

Frontend: `pnpm lint`, `pnpm build`, `pnpm test` passed (723 tests).
Backend: `uv run ruff check .` passed. API/lifecycle targeted tests passed (65).
Real local SQL tests passed (2), covering legacy/reset/restore, password/completion transaction,
stale/direct-write rejection, private-RPC denial, own identity and product/Storage reads.
Full `uv run pytest`: 1,517 passed, 89 skipped, 6 deselected, 6 existing PDF failures due to
unavailable Windows WeasyPrint native libraries. Skipped real-boundary/provider suites are not passes.
The separate existing RLS/annotation baseline had 55 passes and 9 failures from older approval-grant
and fixture assumptions. Production policies were preserved.

Migration 0021 was applied only to an isolated local stack after all preceding repository migrations.
Local versions: Auth v2.188.1, Postgres 17.6.1.106, REST 14.10, Storage 1.54.1.
Postgres crashed on a permission denial, also reproduced with an unrelated SELECT-1 function,
matching [upstream #2112](https://github.com/supabase/postgres/issues/2112).
The SQL test connection disables only permission-error hints at startup through
`supautils.hint_roles`. ACLs, RLS and actual EXECUTE-denial assertions are unchanged.
No production configuration changed.

Actual Auth HTTP transactions, sockets, concurrent connections and rendered device/shared-browser
journeys remain unverified. SQL follows the pinned Auth source's hash/metadata statement order.
No hosted project, credentials or existing secret files were inspected.

This contract amends auth-routes middleware/profile reads and password updates, and
teacher-provisioning create/reset/restore. ADR-073 through ADR-078 remain the product decisions.

### Acceptance journeys

1. New student: receive slip → log in → enter current secret word and matching new password → trusted
   completion → one dismissible navigation explanation → own bookshelf.
2. Reset/restored student: replacement-word login → required change → product; a previously dismissed
   introduction stays dismissed.
3. Existing student at rollout: continue without a forced change until a later reset/restoration.
   Ordinary voluntary changes still require the current password.
4. Partial failure: password and completion roll back together or commit together. If the response
   is lost, read trusted state without another change. A newer reset invalidates older operations.
5. Shared device: identify the signed-in student, use visible Log out, and hand off the device;
   another student cannot inherit protected access or that student's introduction dismissal.

## 2. User stories and acceptance criteria

### US-01 — Replace a teacher-issued secret word

As a student, I want to choose my own password after receiving a teacher-issued secret word,
so that I can return with a password I remember.

Applies: SH-01, SH-02, SH-03, SH-04, SH-05, SH-06, SH-07, SH-08.

- **AC-01:** When an account is created after rollout, protected profile state requires password
  change before product access. Successful login enters that flow, including bookmarked entry.
- **AC-02:** When a teacher resets or restores an account, require another change, including for
  previously exempt accounts. Preserve any existing introduction dismissal.
- **AC-03:** Existing accounts at rollout remain exempt until reset/restoration. Do not infer that
  their passwords were child-chosen. Define the concrete migration/backfill in OD-01.
- **AC-04:** When correct current-word proof and matching acceptable replacement are submitted,
  update the password and complete the protected requirement before granting access. The replacement
  must differ from the current secret word. Invalid input never clears the requirement.
- **AC-05:** The required screen identifies the signed-in student and offers visible Log out. Explain
  that the chosen password replaces the secret word and that forgotten passwords require the teacher.
  Product navigation cannot bypass the screen.

### US-02 — Enforce the requirement beyond navigation

As a student, I want required-change state to apply consistently,
so that a bookmark, stale tab, or direct request cannot bypass it.

Applies: SH-01, SH-03, SH-04, SH-07, SH-08.

- **AC-06:** While change is required, protected page entry/deep links lead to the required flow.
  FastAPI product operations and direct Supabase product reads/writes deny access too. Existing
  ownership and classroom checks still apply after completion.
- **AC-07:** A student cannot clear the requirement through direct profile writes, editable Auth
  metadata, submitted target IDs, or browser storage. Trusted completion derives identity from the
  verified caller. Mirrored JWT claims are not the authority.
- **AC-08:** Reset applies to subsequent authorized operations from already-open sessions/tabs.
  Deny new protected data/API access, new image signatures and newly authorized Realtime product
  events. Under ADR-078, previously issued image links retain only their original expiry, at most
  one hour after issuance; reset cannot renew them. Already delivered/cached bytes cannot be recalled.
  This exception grants no product navigation or new signatures. Remaining enforcement details are
  OD-02. A redirect alone cannot satisfy the restriction.

### US-03 — Change a password from settings

As a student or teacher, I want changes to verify my current password,
so that an unattended session alone cannot change my credentials.

Applies: SH-02, SH-03, SH-04, SH-05, SH-06, SH-07.

- **AC-09:** Both roles supply current password, new password and confirmation. Missing/incorrect
  current password prevents the update. Required student changes also require the current secret
  word despite the immediately preceding login.
- **AC-10:** Reject fewer than eight characters and mismatched confirmation with actionable feedback.
  Allow spaces without mandatory capitals, numbers or symbols. Align both forms and server policy;
  client validation alone is insufficient. Maximum length and precise counting are OD-04.
- **AC-11:** Ordinary settings success confirms inline and stays on the page. Retain student guidance,
  "If you forget it, ask your teacher." Teachers cannot see a child's chosen password.

### US-04 — Recover partial completion

As a student, I want to recover when my password was saved but unlocking failed,
so that temporary failure alone does not require another password change or teacher reset.

Applies: SH-01, SH-02, SH-03, SH-04, SH-06, SH-07, SH-08.

- **AC-12:** If password update succeeds but clearing the requirement fails, remain blocked and offer
  secure completion retry using the now-current password. Distinguish incomplete completion from an
  incorrect password. Do not claim full success or require another password change solely for this.
- **AC-13:** Same-change retries are safe to repeat and grant access only after trusted completion.
  A newer teacher reset prevents any older completion from clearing its requirement. Correlation,
  transaction/order protection and retry mechanics are OD-01/OD-03.

### US-05 — Learn navigation once

As a student, I want a short navigation explanation,
so that I can find my books, the class gallery, password settings and Log out.

Applies: SH-03, SH-04, SH-05, SH-06, SH-07.

- **AC-14:** After the first required change, show one short dismissible screen explaining Bookshelf,
  Gallery and Profile, including password change and Log out in Profile. No tab-by-tab guided tour,
  authoring tutorial or navigation redesign is included.
- **AC-15:** Provide "Go to my bookshelf" as the primary exit to the student's own shelf. Dismissal
  is not a password/security prerequisite. Exact alternative dismissal presentation is OD-05.
- **AC-16:** Save dismissal separately on the student's profile. Once dismissed, it stays dismissed
  across devices/browsers and after reset/restoration. Another student using the same browser has
  separate dismissal state. Save-failure and legacy initialization behavior are OD-05.

## 3. Shared behavior

- **SH-01 — Authority and exits:** Profile state is authoritative. Password-change/completion and
  logout remain available without loops. Middleware is the sole page auth gate; API and database
  checks enforce their own boundaries. Define minimal identity reads and other exceptions in OD-02;
  access to all of Profile is not an implicit exception. Failed checks never unlock the product.
- **SH-02 — Credentials and recovery:** Supabase Auth owns password material. Never store/log it in
  profiles, URLs, telemetry, browser persistence, or fixtures captured from children. Student
  recovery is teacher-only. Encourage memorable words. Prefer native current-password verification
  only after hosted support/settings verification (OD-06). Email/phone nonce reauthentication is not
  a substitute. Unavailable support must not silently downgrade verification.
- **SH-03 — Pending/disabled/success:** Every submit visibly becomes pending and prevents duplicate
  submission. Async route segments have `loading.tsx`/`error.tsx` per AGENTS.md. Distinguish password
  save, trusted completion and introduction-dismissal persistence; do not claim any before confirmed.
- **SH-04 — Errors/recovery:** Distinguish validation/current-password, network and partial-completion
  failures with child-readable feedback and retry/logout where applicable, without raw provider errors
  or tokens. Keep existing identical login failures for wrong code/nickname/password. On expiry,
  require login and recheck state, without persisting passwords to resume.
- **SH-05 — Controls/focus:** Label current/new/confirmation fields. Passwords are hidden by default;
  explicit Show/Hide preserves input. Tab follows visual order, Enter submits once, and focus and
  announcements expose step changes/errors. Escape cannot unlock or strand focus. Exact introduction
  dismissal control is OD-05; a modal is not assumed. Preserve visible focus, 44px minimum targets,
  and blur/submit validation from DESIGN.md, MOBILE_GUIDELINES.md and auth-routes §7.5.
- **SH-06 — Presentation/copy:** Reuse Cobalt Playroom tokens, native controls and existing audience
  registers. Required-flow guidance explains current secret word, memorable replacement, its login
  effect and teacher recovery. Introduction content is AC-14. Explanatory copy beyond agreed labels
  is not approved verbatim. Keep logout visible during the required flow.
- **SH-07 — Existing safeguards:** Retain session verification, ownership/classroom isolation, safe
  redirects, generic credential failures and signed/private assets. `?next=` cannot bypass the gate
  or escape allowed routes. Preserve shared-device identity and fallback logout. Replacing the current
  `/login` logout destination with `/join` was not agreed (OD-05).
- **SH-08 — Ordering/trust:** Newer reset requirements prevail. Privileged writes verify identity and
  ownership and preserve unrelated profile facts. Replay, refresh and lost responses cannot cause
  premature access. Auth/profile coordination and exact transitions remain OD-01/OD-03.

## 4. Edge cases

| Case | Expected behavior | Home |
|---|---|---|
| Empty fields, wrong current password, mismatched confirmation or fewer than eight characters | No success/unlock; actionable feedback | AC-04, AC-09, AC-10, SH-04 |
| Acceptable matching eight-character replacement, including spaces/simple character sets | Allowed by the agreed minimum without composition requirements | AC-10 |
| Maximum input, Unicode, leading/trailing or all-space passwords | Counting, maximum, normalization and server policy must be specified | OD-04 |
| Replacement equals current secret word | Reject required replacement without clearing state | AC-04 |
| Server refuses a password | Show safe actionable feedback; exact server-policy compatibility remains open | SH-04, OD-04 |
| Wrong code/nickname/password at login | Keep identical credential-failure response | SH-04 |
| Double tap, Enter or request replay | Pending feedback and no premature/duplicate completion effects | SH-03, SH-05, SH-08 |
| Network failure before password saved | No claimed success; retry/logout available | SH-01, SH-03, SH-04 |
| Password saved, completion fails | Retry using now-current password without another change solely for failure | AC-12, AC-13 |
| Save response lost; refresh/tab close; two tabs change password | Explicit reconciliation and ordering protocol required | OD-03 |
| Reset races completion; provisioning/reset partly fails | No older completion clears newer requirement; atomic operation/version contract in section 7; native concurrency evidence outstanding | AC-13, SH-08, OD-01, OD-03 |
| Reset/restoration after introduction dismissed | Require change but preserve dismissal | AC-02, AC-16 |
| Existing account at rollout | Exempt until reset/restoration; deliberate cutover/backfill | AC-03, OD-01 |
| First required change for exempt student | Define introduction eligibility/dismissal initialization | AC-14, OD-05 |
| Bookmark, hostile `next`, direct data/API request or stale JWT | No bypass; precise allowlist and enforcement matrix required | AC-01, AC-06, AC-07, AC-08, SH-07, OD-02 |
| Image link issued before reset or already delivered/cached image | Original link expires naturally within one hour of issuance; no renewal while blocked; delivered bytes cannot be recalled | AC-08 |
| In-flight export or active Realtime subscription | Enforce current state before releasing downloads and newly authorized product events; verify actual boundaries | AC-08, OD-02 |
| Already-running generation or unsaved draft during reset | Do not silently change persistence/job semantics; settle interruption/resume UX | OD-03 |
| Session expiry, wrong-student bookmark, shared-device handoff | Reauthenticate/recheck, preserve identity and fallback logout safeguards | SH-04, SH-07 |
| Missing/unavailable profile, removed student, deleted classroom | Preserve friendly recovery/logout; specify new state-read failure behavior | SH-01, SH-07, OD-02 |
| Escape, Back, cancellation or navigating away mid-submit | Cannot bypass requirement; route/return and interruption details remain open | SH-05, SH-08, OD-03, OD-05 |
| Dismissal-save failure, concurrent dismissal or switching accounts | Separate per-student state; define error/retry/merge behavior | AC-16, OD-05 |
| Empty shelf/gallery after completion | Keep existing empty states; no extra tutorial/content creation required | AC-14, SH-06 |
| No inbox/phone or unsupported hosted setting | No OTP workaround or verification downgrade; block affected delivery | SH-02, OD-06 |

## 5. Design decisions and rationale

Follow AGENTS.md and MASTER_SPEC §2/§5/§6 with the existing identity/session/authorization specs.
There is no pipeline node or `backend/contracts/` slice to change. Profile state is the single
authority, without a mirrored Auth/JWT flag. Required change and introduction dismissal are distinct
facts. Additional ordering representation is undecided (OD-01).

Existing responsibilities remain: middleware owns page entry, frontend surfaces render feedback,
Supabase Auth verifies/changes passwords, FastAPI owns privileged teacher operations, and database
policies protect direct data and private Storage. Completion/dismissal interfaces do not exist yet:
paths, payloads, errors, authorization and schema remain OD-01/OD-02. Existing server-owned reads
remain server-owned, rather than introducing client refetches.

- ADR-073: teacher credentials are temporary; enforcement beyond navigation costs authorization
  work and a child-facing step after recovery.
- ADR-074: legacy exemption avoids interruption but can leave old teacher words in use. A short
  dismissible explanation reduces taps compared with a tour, but may be skimmed.
- ADR-075: profile authority fits database checks at the cost of a migration and middleware read.
  This narrowly amends the no-profile-fetch rule for onboarding. Current-password proof covers both
  roles and recent student login, at the cost of another field/repeated secret-word entry.
- ADR-076: eight characters favors typing UX over the referenced fifteen-character password-only
  benchmark, without claiming conformance. Recoverable completion reduces teacher support but needs
  verification and reset-ordering protection.
- ADR-077: restoration follows reset because it issues another word. Per-profile dismissal supports
  shared devices and costs a distinct persisted fact and protected update.
- ADR-078: existing image links expire naturally within their original one-hour lifetime. This
  narrows ADR-073's reset boundary without changing ADR-006's image transport; new product operations
  and signatures remain blocked. It accepts temporary residual image access to avoid a new proxy.

Cross-cutting coverage: CC-4 security (AC-06–AC-08), CC-6 accessibility (SH-05), CC-8 audience design
(SH-06), CC-9 failure states (SH-03/SH-04), CC-2 no new stored child PII/password material (SH-02).
Other concerns are not changed by this spec. Active pipeline-job interruption is OD-03, not an
implicit checkpointing or spend-policy amendment.

## 6. Verification

### Confirmed seams and precedents

The owner confirmed these three boundaries during synthesis. They are required checks, not evidence
of implemented or passing behavior.

| Boundary | Observable checks | Existing precedents |
|---|---|---|
| Rendered forms and middleware navigation | Entry/deep links, validation, success/errors, focus, logout, introduction/dismissal | `frontend/middleware.test.ts`, `frontend/app/join/[code]/page.test.tsx`, `frontend/app/s/[profileId]/settings/page.test.tsx`, `frontend/app/auth/signout/route.test.ts` |
| FastAPI request boundary | Caller identity; create/reset/restore requirement; proof for completion; partial retries and reset races | `backend/tests/test_main.py`, `backend/tests/test_avatar.py` use TestClient and external service mocks; these precedents are not existing onboarding coverage |
| Real Supabase authorization | Required/completed own/peer access; no profile tampering; Storage/signing/Realtime; old JWT after reset; role/classroom isolation | `backend/tests/test_rls_isolation.py` exercises SQL policies but skips Realtime cases and does not establish WebSocket behavior |

Use existing test infrastructure. Follow AGENTS.md's failing-test-first and main-path/critical-failure
limits at implementation. Mock outer Auth/database/network boundaries in deterministic tests, not
internal transitions. Real policy evidence needs a reachable disposable database and actual policies;
mocks cannot establish isolation. No real model/image calls or generated-content assertions apply.

Required acceptance evidence: §1 journeys; all lifecycle events and legacy exemption; AC-10 input
boundaries; partial completion/reset races; direct-request bypass attempts; cross-device dismissal;
shared-browser identity/logout, Back, multiple tabs/autofill; 360px and 390px widths with keyboard
visible, readable feedback, keyboard/focus and screen-reader announcements; empty shelf/gallery.
For ADR-078, exercise a link issued before reset through its original expiry while fresh signing
and protected operations are denied. No expiry extension or new signature is allowed during the gate.

Required implementation checks from each project directory:

- Frontend: `pnpm lint`, `pnpm build`, `pnpm test`.
- Backend: `uv run ruff check .`, `uv run pytest`.
- Explicit real RLS/Storage/Realtime and hosted Auth checks in the approved test environment.
  Default-skipped suites are not a pass. Live authenticated execution requires separate approval
  for disposable credentials or user-controlled sign-in under AGENTS.md.

**Actual evidence:** See section 1. Local SQL and deterministic tests do not establish native
Auth HTTP, hosted policy, actual Realtime sockets or rendered-device acceptance.

## 7. Open decisions, readiness and coverage

**Implementation in progress; release not accepted.** The contract below replaces the initial
recommendations. Product choices were approved. Local evidence supports continued implementation,
while native Auth and hosted compatibility remain release prerequisites.

### State and lifecycle (OD-01)

Migration `supabase/migrations/0021_account_onboarding.sql` adds protected nonnegative bigint
`password_reset_version` and `password_completed_version`, with completed <= reset, plus nullable
`introduction_dismissed_at`. Required change is completed < reset, never a separate boolean/JWT claim.
Existing accounts default to 0/0. New students are provisioned banned, upserted at 1/0 with correct
student membership, then unbanned. Profile-write failure cannot expose the temporary teacher profile.
Failed provisioning attempts Auth cleanup.

Reset/restore reserve a private operation and increment reset version before issuing a secret.
Restore clears removal inside the password transaction, never in an earlier profile request.
A failure leaves the requirement active and the teacher can retry. Preserve dismissal and job/draft
state. Workers continue existing jobs; no automatic paid action is replayed.

### Proof, input and recovery (OD-03/OD-04)

Service-role-only `begin_password_operation(uuid, text)` locks the profile and reserves a random
single-use ID with kind and exact reset version in the unexposed, RLS-enabled
`onboarding_private.password_operations` table. Reserve before verifying current proof. A pending
reset/restore cannot be replaced by an ordinary change. Later reservations invalidate older work.

`POST /me/password` derives identity from the verified bearer. Its body contains only
`current_password`, `password`, `confirmation`. Validate at least eight Unicode code points and at
most 72 UTF-8 bytes, exact spaces/confirmation, no trimming/normalization/composition rules.
A replacement must differ from the current word. Never apply new-password rules to current/login
input. Both settings forms use this endpoint and retain inline success. Issued words use stdlib
`secrets` with the existing format/list.

The server explicitly verifies the current password through native Auth sign-in using a transient
proof session, then invokes native UserUpdate with the caller's bearer and operation ID. Finally
sign out the proof session without changing the shared service-role SDK session.
The native current-password flag is an additional defense, not assumed deployed evidence.
No email/phone nonce substitutes for password proof.

A deferred trigger on changed `auth.users.encrypted_password` inspects the final Auth row in the
same transaction and consumes only a matching private operation for the current profile version.
The change receipt travels in user metadata; reset/restore uses app metadata. Metadata itself grants
nothing. The fresh private operation is server-only and is consumed before the receipt is exposed.
Direct hash writes, metadata-only writes, consumed/replayed receipts and stale operations cannot
complete the requirement. Store no password material in the operation table.

Password and trusted completion commit or roll back together. There is no separate unlock HTTP
call that can fail after password persistence. `GET /me/onboarding` returns minimal caller-owned
state with `Cache-Control: no-store`. On an unknown save outcome the required form checks state,
proceeds only on confirmed completion, and otherwise offers **Check again** without another change.
If state confirms the requirement remains, retry the change using the currently valid secret.
A newer reset remains authoritative.

### Enforcement and introduction (OD-02/OD-05)

Middleware preserves refreshed Auth cookies on both pass-through and redirect responses.
It reads current own-profile state and gates product paths, including bookmarks and ordinary
Profile/settings. Unknown/invalid state fails closed. Product API authorization checks active student
state. PDF export rechecks before releasing bytes. Existing student policies consult current
`auth_role()`, denying gated jobs, classroom, classmates and Storage reads. Own identity is the
minimal exception. A JWT is not the profile authority. Actual socket enforcement is a release check.
Previously issued signed image URLs keep only ADR-078's original expiry, at most one hour.
No new product operations/signatures or expiry extension are allowed during the requirement.

`/s/[profileId]/change-password` identifies the student and collects current/new/confirmation,
with visibility control, validation, pending guard, safe focused errors, recovery and logout.
`/s/[profileId]/introduction` explains Bookshelf, Gallery and Profile. Its primary
**Go to my bookshelf** and secondary **Skip for now** call caller-owned
`dismiss_student_introduction()` with no target ID. Preserve the first timestamp. Failure says the
dismissal was not saved and offers an explicit bookshelf link. Only the completed change-password
route leads to the introduction, so an unsaved dismissal does not make it recur on later logins.
Dismissal is not an access prerequisite.
Legacy 0/0 accounts qualify only after a future required completion. Reset/restore preserve dismissal.
Both async routes have loading/error states; server reads share cached `getStudentProfile()`.

### Release prerequisites (OD-06 and remaining D-T evidence)

- Verify target Auth version/settings, native current-password and nonce behavior for older sessions,
  actual transaction permissions and statement order. Verify login/hash re-encryption and account
  deletion compatibility with the Auth-table trigger.
- Exercise native Auth direct-write bypasses, password rollback, lost responses, concurrent changes
  and reset/restore ordering across independent connections. SQL fixture ordering is not this proof.
- Verify old JWTs, actual Realtime subscriptions, fresh signing denial and existing-link expiry.
  Complete in-flight export checks with the native rendering libraries available.
- Render 360px/390px flows with keyboard/autofill, focus/announcements, Back, multiple tabs,
  shared-device logout, missing/removed accounts and cross-device dismissal.
- Deploy migration 0021 and compatible password/reset server and frontend paths as a coordinated
  cutover. Old direct-Auth forms are rejected by the trigger. Do not apply the migration alone.

These are release gates, not requests to create a new hosted project before building. No hosted
credentials or production deployment have been used. D-T remains open for native/hosted integration
evidence; do not mark tickets 03-07 accepted solely from local SQL and mocked HTTP.

### Source-to-acceptance index

| Source requirement | Explicit home |
|---|---|
| Q1 / ADR-073: first login and every reset | AC-01, AC-02, AC-04 |
| Q2 / ADR-073: strict direct/stale-tab restriction, password/logout escape | AC-05–AC-08, SH-01, OD-02 |
| Owner acceptance / ADR-078: existing image links keep original expiry up to one hour after issuance; no new product access/signatures or expiry extension | AC-08, §5, §6; remaining enforcement OD-02 |
| Q3–Q4 / ADR-074: one short dismissible navigation-only explanation, three destinations, Profile password/logout, bookshelf exit | AC-14, AC-15, SH-06 |
| Q4 / ADR-074: no repeat after reset | AC-02, AC-16 |
| Q5 / ADR-074: existing accounts exempt until future reset | AC-03; restore extension AC-02; OD-01 |
| Q6 / ADR-075: protected profile authority, no token mirror, middleware exception | AC-07, SH-01, §5, OD-01/OD-02 |
| Q7 / ADR-075: current proof for both roles/recent login; conditional native setting, no OTP substitute | AC-09, SH-02, OD-06 |
| Q8 / ADR-076: eight characters/spaces/no mixture, memorable words, different replacement, server alignment and deliberate UX tradeoff | AC-04, AC-10, SH-02, §5; input precision OD-04 |
| Q9 / ADR-076: blocked partial completion, now-current retry, no extra change/reset solely for failure, newer reset wins | AC-12, AC-13, SH-08, OD-03 |
| Q10 / ADR-077: restored legacy/new accounts require change | AC-02 |
| Q11 / ADR-077: separate profile dismissal, cross-device, retained after reset/restore | AC-16 |
| Auth-routes §7.3/§7.5, AGENTS.md: inline success, recovery, loading/error/disabled, labels/visibility/focus/keyboard/logout | AC-05, AC-11, SH-03–SH-07 |
| Ticket 01: hosted/mobile gaps, direct bypass/stale JWT, ordering, legacy accounts, shared devices and generator concern | OD-01–OD-06, §6. Support estimates remain scenarios in ticket 01, not new measured findings or a telemetry feature. |
| Owner seam confirmation during synthesis | §6; authenticated execution is not authorized |

Coverage assigns settled clauses and unresolved mechanics explicit homes, without declaring readiness.

## 8. Sources

- [Secret word glossary](../../GLOSSARY.md).
- [Ticket 01: source audit and live gaps](../../.scratch/ptd-account-onboarding/issues/01-audit-accounts-and-first-login.md).
- [Ticket 02: interview scope](../../.scratch/ptd-account-onboarding/issues/02-grill-onboarding-spec.md).
- [ADR-073: requirement/access restriction](../product/adr/ADR-073-students-replace-teacher-issued-passwords-before-product-access.md).
- [ADR-074: rollout/introduction](../product/adr/ADR-074-onboarding-rollout-exempts-existing-students-until-reset.md).
- [ADR-075: profile authority/password proof](../product/adr/ADR-075-profile-state-enforces-password-change-with-current-password-verification.md).
- [ADR-076: password rules/recovery](../product/adr/ADR-076-onboarding-password-rules-and-completion-recovery-prioritize-usability.md).
- [ADR-077: restoration/dismissal](../product/adr/ADR-077-restored-students-change-passwords-and-introduction-dismissal-persists.md).
- [ADR-078: accepted expiry of existing image links after reset](../product/adr/ADR-078-issued-image-links-expire-naturally-after-password-reset.md).
- [Identity](auth-identity-and-classroom-schema.md), [sessions](auth-session-model.md),
  [authorization](auth-authorization-surface.md), [routes](auth-routes-and-account-ux.md),
  [provisioning](teacher-provisioning-and-shell.md), [MASTER_SPEC](../MASTER_SPEC.md).
- [DESIGN.md](../../DESIGN.md), [mobile guidelines](../MOBILE_GUIDELINES.md),
  [local tracker](../agents/issue-tracker.md).
- Blocker-review primary sources checked 2026-10-26:
  [Supabase password security](https://supabase.com/docs/guides/auth/password-security),
  [private asset delivery and signed-URL lifetime](https://supabase.com/docs/guides/storage/serving/downloads),
  [Auth audit-log storage](https://supabase.com/docs/guides/auth/audit-logs),
  [upstream password length checks](https://github.com/supabase/auth/blob/master/internal/api/password.go),
  [upstream user update transaction](https://github.com/supabase/auth/blob/master/internal/api/user.go),
  [upstream admin update](https://github.com/supabase/auth/blob/master/internal/api/admin.go).
  Upstream `master` is inspection evidence, not the deployed Auth version.

The conversation and owner-confirmed ADRs establish the requested change. Repository source
establishes the baseline. This draft is not a statement of deployed schema, Auth settings or results.
