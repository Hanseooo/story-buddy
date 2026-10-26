# ADR-075 — Profile state enforces password change with current-password verification

**Status:** Accepted (2026-10-26), interview decisions Q6–Q7. Schema and API implementation remain separate work.

**Context:** [ADR-073](./ADR-073-students-replace-teacher-issued-passwords-before-product-access.md)
requires enforcement beyond navigation; [ADR-074](./ADR-074-onboarding-rollout-exempts-existing-students-until-reset.md)
defines the rollout exemption. The owner accepted a protected profile field and current-password
verification for both roles during the account-onboarding interview.

**Decision:** The student's profile owns the authoritative password-change-required state. Student
clients cannot clear it directly. Page guards, API authorization, and database policies consult this
current state rather than a mirrored token claim. The later spec must amend auth-routes §2's
prohibition on middleware database reads and define the protected schema and completion operation.
No particular field name or state-transition schema is selected here.

Students and teachers must supply their current password when changing it, including a student's
required change immediately after secret-word login. Prefer Supabase Auth's native current-password
verification, conditional on verifying the hosted setting and deployed support before implementation.
The email/phone nonce reauthentication flow is not a substitute for checking the current password.

**Rationale and tradeoffs:** Profile state fits the existing database authorization model and avoids
stale token claims after a teacher reset. It costs a migration and a middleware database read.
Current-password verification prevents an unattended session alone from authorizing a password
change, at the cost of an additional field and repeating the secret word during a required change.

**Open:** Password rules, reset/completion ordering and recovery, restore behavior, and how the
navigation introduction is remembered. Hosted verification and the phone walkthrough remain open.

**Evidence:** [Ticket 01 source audit](../../../.scratch/ptd-account-onboarding/issues/01-audit-accounts-and-first-login.md),
[identity spec §3.2](../../specs/auth-identity-and-classroom-schema.md), and
[Supabase password security](https://supabase.com/docs/guides/auth/password-security#require-current-password-when-changing-password)
(checked 2026-10-26). No live Auth setting, schema, API, or application behavior was changed.
