# ADR-073 — Students replace teacher-issued passwords before product access

**Status:** Accepted (2026-10-26), interview decisions Q1–Q2. Implementation design remains open.

**Context:** [ADR-017](./ADR-017-setting-teacher-managed-classroom-child-holds-an-issued.md)
permits child password changes and teacher-only recovery. The owner accepted both recommendations
in the interview for [account-onboarding ticket 02](../../../.scratch/ptd-account-onboarding/issues/02-grill-onboarding-spec.md).

**Decision:** A student must replace the teacher-issued secret word on first login and after every
teacher password reset. Until completion, product access is blocked across page navigation and
direct data/API access, including access attempted from an already-open tab. Password-change and
logout operations must remain available.

**Rationale:** A replacement secret word has the same temporary purpose as the initial one.
Navigation-only enforcement would let a direct request bypass the requirement.

**Tradeoffs:** Teacher recovery now requires the child to choose another password before returning
to their work. Enforcement requires coordination across application and database boundaries rather
than a redirect alone.

**Open:** State ownership, reset/completion ordering and failure recovery, existing-account rollout,
password rules, and the navigation introduction remain undecided. This record does not choose a
schema or API contract, authorize implementation, or amend the existing auth spec. Hosted Auth
settings and the rendered phone walkthrough remain unverified; see [ticket 01's audit](../../../.scratch/ptd-account-onboarding/issues/01-audit-accounts-and-first-login.md).
