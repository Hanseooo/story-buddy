# Approve onboarding proof and delivery contracts

**Status:** needs-info
**Type:** research
**Progress:** open
**Parent:** [Ticket 02](02-grill-onboarding-spec.md)
**What to build:** An approved, implementable contract resolving the spec's design prerequisites.
**Source criteria:** [Account onboarding](../../../docs/specs/account-onboarding.md) §7 OD-01–OD-05, D-T, ADR-073–078.
**Scope:** Replacement evidence, reset ordering, lifecycle failures, protected state, interfaces, authorization matrix, exact password policy, routes, copy and dismissal behavior.
**Out of scope:** Application changes, migrations, hosted configuration changes and release verification, owned by 04–07.
**Complexity:** High — replacement evidence must survive lost responses and concurrent Auth/reset operations.
**Blast radius:** System-wide — decisions govern middleware, Auth, FastAPI, database policies and student flows.
**Unblocks:** [04](04-current-password-settings.md), [05](05-enforce-required-password-replacement.md), [06](06-student-navigation-introduction.md).

## Context

The spec explicitly rejects current-password login plus a version counter as sufficient replacement proof. Proposed fields, routes and copy remain recommendations. See spec §7 and `docs/product/DECISION_BACKLOG.md` D-T. ADR-073–078 settle product choices without approving these implementation contracts.

## Read first

- `docs/specs/account-onboarding.md` — §7: recommendations, counterexamples and unresolved prerequisites.
- `docs/product/DECISION_BACKLOG.md` — D-T: architectural decision boundary.
- `backend/app/classrooms.py` — `_create_one`, `reset_student`, `restore_student`: actual lifecycle ordering.
- `frontend/middleware.ts` — `middleware`, `guardRequest`: page enforcement boundary.
- `supabase/migrations/0008_authorization_surface.sql` — student policies: direct-access consumers.
- `backend/tests/test_rls_isolation.py` — module preamble: SQL coverage and omitted socket checks.

## Behavior this changes

None. This ticket settles contracts without changing runtime behavior.

## Acceptance criteria

- [ ] Prove replacement evidence for completion before replacement, lost Auth response, browser closure, replay after reset, and a change verified before reset but committed afterward.
- [ ] Approve state representation, legacy cutover, provisioning/reset/restore failure handling and caller-derived completion/dismissal interfaces. Name actual fields, payloads and errors only after selection.
- [ ] Approve the operation matrix, minimal identity exceptions and enforcement points for API, RLS, Storage, Realtime and in-flight export. Retain ADR-078's original-expiry exception.
- [ ] Resolve server enforcement of exact password counting, maximum bytes, whitespace, normalization and confirmation. Client validation cannot close the direct-Auth bypass.
- [ ] Approve routes, copy, introduction eligibility, exits, save failure and concurrent dismissal behavior.
- [ ] Record prerequisites for native current-password support. Obtain authorized hosted evidence before selecting it for implementation, or leave delivery blocked without a downgrade.
- [ ] Carry accepted decisions into the spec and required decision records. Preserve existing ADRs and obtain acceptance before downstream implementation.

## Guidance

Suggestion: evaluate durable Auth-owned evidence. An audit event is a candidate, not an approved protocol or proof of deployed support.

## Verification

Review each protocol against §7's counterexamples and reconcile every OD with an accepted contract or explicit blocker. Never use child credentials or record password material.

**Targeted:** Documentation and protocol review against `account-onboarding.md` §4/§7 and D-T.
**Full suite:** Not applicable without runtime changes. Record evidence limits explicitly.

## Blocked by

Sufficient evidence for reset-correlated replacement proof and direct-Auth Unicode enforcement, plus final lifecycle/API contracts dependent on that evidence. The owner's product approval is recorded below. Parent linkage is not an implementation blocker. Live authenticated evidence requires separate authorization.

## Comments

### Owner approval and claim — 2026-10-26

The owner said “i approve all” after publication of tickets 03–07. Proceed through the approved work in dependency order. The proposed product recommendations in account-onboarding §7 are approved for this work: input semantics, routes/copy/exits/dismissal behavior, profile-counter direction and operation matrix. This approval does not invent the unfinished replacement-proof protocol or establish hosted support.

Claimed by Codex for public-source and repository research. Remaining technical prerequisites are durable reset-correlated replacement evidence (OD-03/D-T), exact lifecycle/API contracts dependent on it (OD-01), direct-Auth server enforcement of the Unicode minimum (OD-04), and enforcement/hosted evidence (OD-02/OD-06). Do not mark dependent tickets ready on approval alone. No disposable credentials, target test environment or user-controlled sign-in has been supplied for live authenticated execution.

### Public-source proof review — 2026-10-26

**Upstream evidence, not hosted verification.** Rechecked current primary sources for OD-03/OD-04. No credentials, secret files, hosted project, or authenticated requests were used. No proof protocol is selected by this review.

- **Native current-password support:** Supabase documents a separate current-password setting. Upstream `UserUpdate` verifies it when enabled, except in recovery sessions. The independent recent-login/nonce setting can still require a nonce for older sessions, so enabling the current-password setting alone does not establish the no-inbox journey. [Password security](https://supabase.com/docs/guides/auth/password-security), [UserUpdate](https://github.com/supabase/auth/blob/master/internal/api/user.go).
- **Durable event candidate:** The user password update and `user_updated_password` audit insertion share a database transaction. The admin update instead emits `user_modified` with target-user traits. This can distinguish a committed user-password operation from the inspected admin path, but does not correlate it to an application reset version. [UserUpdate](https://github.com/supabase/auth/blob/master/internal/api/user.go), [adminUserUpdate](https://github.com/supabase/auth/blob/master/internal/api/admin.go).
- **Persistence matters:** Audit database storage is optional. The model returns without inserting when disabled; its external log is emitted before the transaction has committed. The inspected database event payload carries actor/action but no application reset version; a request ID is added to the external log, not the persisted payload shown here. An external log alone is therefore not evidence of a committed replacement. [Audit model](https://github.com/supabase/auth/blob/master/internal/models/audit_log_entry.go), [audit storage docs](https://supabase.com/docs/guides/auth/audit-logs).
- **Ordering counterexample remains:** Current-password verification and hashing occur before `UserUpdate` opens its write transaction. `UpdatePassword` then writes the prepared hash without a reset-version predicate or old-hash compare-and-set in the inspected function. Inference: an event observed after reset cannot alone establish that verification belonged to that reset. A trigger that merely reads the current application counter at event insertion would not establish this correlation either. The lost-response/browser-close cases have a potential durable seam, but the verification-before-reset/commit-after-reset case still needs a separately proved protocol. [UserUpdate](https://github.com/supabase/auth/blob/master/internal/api/user.go), [UpdatePassword](https://github.com/supabase/auth/blob/master/internal/models/user.go).
- **Unicode gap confirmed upstream:** Password strength uses Go `len(string)` for both minimum and a maximum of 72, which counts bytes. At minimum 8, two four-byte Unicode characters pass the length check despite being fewer than eight code points. This is a source-derived example, not a hosted test. The inspected strength function does not trim or normalize. Client or FastAPI validation alone does not demonstrate equivalent enforcement on direct Auth requests. [Password checks](https://github.com/supabase/auth/blob/master/internal/api/password.go), [Go string/length specification](https://go.dev/ref/spec#Length_and_capacity).

**Conclusion:** OD-03 and OD-04 remain technical blockers. Approval does not supply reset correlation or direct-Auth Unicode enforcement. Hosted version, settings, database audit persistence, permissions, concurrency behavior and policy remain unverified. The changelog Markdown fetch failed with an unsupported-content-type error; the root agent successfully read the [HTML changelog](https://supabase.com/changelog) instead. No deployment compatibility claim is made. Application tests were not run for this source-only review.

### Handoff after source review — 2026-10-26

Claim released. Status is `needs-info`, Progress remains `open`, and acceptance criteria remain unchecked. The next step is the focused D-T architecture session required by AGENTS.md: prove a reset-correlated completion mechanism and direct-Auth Unicode enforcement before finalizing contracts. No supported implementation has been selected. Hosted testing also needs an identified disposable environment and authorized user-controlled sign-in. Product approval need not be requested again.

Verification: root inspected the appended research and upstream password/UserUpdate/UpdatePassword sources. `git diff --check` passed for the tracked spec/map changes, and local-link checks passed for this ticket, the map and the spec. No application, migration or hosted-setting changes were made.

### Implementation update - 2026-10-26

A private single-use operation ID and deferred Auth password trigger now implement reset-correlated atomic completion. See spec section 7 for exact RPC, schema, HTTP, validation and recovery contracts. Source-only conclusions above are superseded by this local implementation, not by a claim of hosted proof. Native transaction/concurrency, login/hash-encryption and deletion compatibility remain open.

Commands and measured results: account-onboarding spec section 1. Acceptance checkboxes remain open for the stated evidence limits. No commit or hosted deployment was made.
