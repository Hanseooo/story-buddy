# Verify hosted onboarding rollout and shared-device journeys

**Status:** ready-for-human
**Type:** task
**Progress:** open
**Parent:** [Ticket 02](02-grill-onboarding-spec.md)
**What to build:** Recorded release evidence for the completed feature and its hosted enforcement boundaries.
**Source criteria:** [Account onboarding](../../../docs/specs/account-onboarding.md) §1's five journeys, §6, OD-06, all AC/SH as integration checks.
**Scope:** Authorized disposable-environment verification, deployment ordering, hosted settings/schema/policies, real sockets/signing, mobile and shared-device acceptance.
**Out of scope:** Deferred feature behavior or tests. Tickets 04–06 must each close their own acceptance criteria. No production changes are authorized by publishing this ticket.
**Complexity:** Medium — combines established boundaries with asynchronous session/reset and device scenarios.
**Blast radius:** System-wide — validates the complete account-access workflow.
**Unblocks:** None.

## Context

Source inspection and installed SDK types are not hosted evidence. Ticket 01's phone and hosted checks remain outstanding. See spec §6/OD-06 and ADR-078's required verification.

## Read first

- `docs/specs/account-onboarding.md` — §1/§6/OD-06: required evidence.
- `backend/tests/test_rls_isolation.py` — module preamble and fixtures: skipped-test limits.
- `frontend/lib/signedUrls.ts` — `signPaths`: original URL lifetime.
- `backend/app/pdf_export.py` — `download_pdf`: in-flight download boundary.
- `docs/MOBILE_GUIDELINES.md` — forms, feedback and accessibility.
- Tickets 04–06 — implementation evidence and remaining environment requirements.

## Behavior this changes

None unless separately approved deployment/configuration actions are executed.

## Acceptance criteria

- [ ] Verify deployed Auth support/current-password settings, selected proof support, exact password policy and actual schema/policies. No inbox/phone nonce substitute.
- [ ] Confirm compatible forms deploy before any setting rejects old requests.
- [ ] Run all five acceptance journeys, including legacy exemption, reset/restore, partial recovery, reset races and shared-device handoff.
- [ ] Verify direct API/data/profile-tampering attempts, stale JWTs, actual Realtime subscriptions, fresh signing denial and original image-link expiry. Cover in-flight export.
- [ ] Exercise 360px/390px forms with keyboard visible, autofill, Back, multiple tabs, session expiry, focus/announcements and empty shelf/gallery.
- [ ] Verify dismissal across devices and account switching. Retest missing profiles, removed students and deleted classrooms.
- [ ] Record commands/results and unresolved failures in existing ticket/spec evidence surfaces. Skipped checks remain explicit release blockers.
- [ ] No credentials, tokens or password material appear in evidence.

## Guidance

Use user-controlled sign-in or explicitly authorized disposable credentials. A test environment must be approved before authenticated execution.

## Verification

**Targeted:** Real Auth, RLS/Storage/signing and Realtime checks from §6, plus rendered-device journeys.
**Full suite:** From their project directories: frontend `pnpm lint`, `pnpm build`, `pnpm test`; backend `uv run ruff check .`, `uv run pytest`. Record separate real-boundary results.

## Blocked by

[04](04-current-password-settings.md), [05](05-enforce-required-password-replacement.md), [06](06-student-navigation-introduction.md): completed slices.
Compatible deployment available and explicit authorization for live authenticated verification.

## Comments

### Implementation update - 2026-10-26

An isolated local Supabase stack now supplies SQL evidence without a disposable hosted project. This does not establish native Auth HTTP transactions, hosted settings, sockets/signing or rendered-device journeys. No hosted deployment or existing credentials were used. Coordinate migration 0021 with compatible server/frontend paths. Do not deploy the migration alone.

Commands and measured results: account-onboarding spec section 1. Acceptance checkboxes remain open for the stated evidence limits. No commit or hosted deployment was made.
