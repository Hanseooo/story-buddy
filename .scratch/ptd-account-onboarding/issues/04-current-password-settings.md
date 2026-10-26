# Require current-password proof in student and teacher settings

**Status:** needs-info
**Type:** task
**Progress:** open
**Parent:** [Ticket 02](02-grill-onboarding-spec.md)
**What to build:** Both roles can change passwords only with valid current-password proof and the approved server-enforced input policy.
**Source criteria:** [Account onboarding](../../../docs/specs/account-onboarding.md) US-03 AC-09–AC-11, applicable SH-02–SH-07, OD-04/OD-06.
**Scope:** Both settings forms, selected verification/update boundary, validation, safe feedback and accessible interaction states.
**Out of scope:** Required-change lifecycle/recovery, owned by 05. Introduction, owned by 06. Hosted activation, owned by 07.
**Complexity:** Medium — two audience forms must agree with server policy and distinguish authentication, validation and network failures.
**Blast radius:** Shared — changes password behavior for both student and teacher accounts.
**Unblocks:** [07](07-verify-hosted-onboarding-rollout.md).

## Context

Both forms currently update without current-password proof. Student validation lacks the teacher form's minimum-length check. See spec US-03 and ADR-075/076. The exact input and verification contracts remain gated by 03.

## Read first

- `frontend/app/settings/page.tsx` — `handleChangePassword`: teacher form.
- `frontend/app/s/[profileId]/settings/page.tsx` — password submission: student form.
- `frontend/app/s/[profileId]/settings/page.test.tsx` — `Settings — password change`: existing expectations.
- `docs/specs/account-onboarding.md` — AC-09–AC-11 and SH-02–SH-07.
- `frontend/AGENTS.md` — installed Next.js documentation requirement.

## Behavior this changes

AC-09 replaces session-only proof. Existing student success tests expect `updateUser({ password })`. Its error test submits `"pass"`, which must become a validation failure under AC-10 rather than reach Auth.

## Acceptance criteria

- [ ] Both roles submit current/new/confirmation values. Missing or incorrect current proof prevents change.
- [ ] Apply the approved eight-character policy, spaces and no composition requirement consistently in forms and server enforcement. Match confirmation exactly.
- [ ] Confirm ordinary success inline without navigation. Retain the student's teacher-recovery reminder.
- [ ] Label all fields. Hide passwords initially and provide input-preserving Show/Hide.
- [ ] Pending state prevents duplicate submission. Blur/submit validation, Enter, Tab, visible focus, announcements and 44px targets follow SH-03–SH-06.
- [ ] Distinguish validation/current-password, network and session-expiry failures safely. Preserve back/logout recovery and existing session/ownership safeguards.
- [ ] Keep password material exclusively within the approved Auth exchange, without logging or browser persistence.
- [ ] Exercise rendered success and critical rejection paths before closing this slice.

## Guidance

The installed client accepting `current_password` does not prove the hosted server verifies it. Use only the mechanism accepted in 03.

## Verification

Extend existing student tests and add teacher coverage using existing infrastructure. Exercise the selected server boundary directly to establish that browser validation is insufficient to bypass it. Use failing-test-first for changed behavior and mock only outer boundaries.

**Targeted:** From `frontend/`, `pnpm exec vitest run 'app/s/[profileId]/settings/page.test.tsx'` and `pnpm exec vitest run app/settings/page.test.tsx`. Run selected server-boundary tests if added.
**Full suite:** Frontend `pnpm lint`, `pnpm build`, `pnpm test`. Backend `uv run ruff check .`, `uv run pytest` if affected.

## Blocked by

[03](03-approve-onboarding-contracts.md): accepted proof/input contracts and hosted-support prerequisite. Do not treat publication approval as auth implementation approval.

## Comments

### Partial implementation at owner request — 2026-10-26

The owner explicitly directed immediate implementation. Both settings forms now send current-password proof to native Auth, apply the approved client input rules, show/hide inputs, prevent duplicate submits, handle provider/network errors without raw details, and confirm inline. Password fields clear on success. No new dependency or endpoint was added.

Red evidence: student suite failed five tests and teacher suite failed two tests because current-password labels/controls did not exist. Green: student 11/11 and teacher 2/2 pass. Tests cover current-password payload, spaces, Unicode/byte rejection, safe failures, retry and duplicate submission using the existing outer Auth mock.

This ticket remains open and `needs-info`: hosted native enforcement has not been verified and client validation cannot establish direct-Auth Unicode enforcement. Sending `current_password` is not evidence that hosted Auth enforces it. No acceptance criterion is closed solely by these mocked results.

Verification: frontend `pnpm lint` passed, `pnpm build` passed including TypeScript with placeholder public Supabase values, and `pnpm test` passed all 715 tests across 74 files. `git diff --check` passed. The build retains the existing middleware-convention deprecation warning. Hosted Auth, direct-Auth policy, rendered phone and live authenticated checks were not run. Initial sandbox execution of pnpm failed to read Corepack's cache, so the same commands ran with approved escalation using `pnpm.cmd`, the Windows pnpm launcher.

### Implementation update - 2026-10-26

Both settings forms now call the shared caller-owned POST /me/password endpoint. Explicit native sign-in verifies current proof even before the additional hosted current-password flag is confirmed. Exact Unicode/byte validation runs on the server. Direct Auth password writes require a fresh private operation. Forms retain inline success and safe errors. Native Auth/settings acceptance remains open.

Commands and measured results: account-onboarding spec section 1. Acceptance checkboxes remain open for the stated evidence limits. No commit or hosted deployment was made.
