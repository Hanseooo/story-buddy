# ptd-account-onboarding: map

**Phase:** [Post technical defense](../post-technical-defense/map.md), rank 1 · **Conflict gate:** none

A child's first login and every password change. Panel suggestions: forced password change after the
secret word, current password on change, better first-use onboarding.

## Tickets

| # | Ticket | Type | Progress | Blocked by |
|---|---|---|---|---|
| 01 | [Audit: accounts and first login](issues/01-audit-accounts-and-first-login.md) | research | investigated; live checks outstanding | — |
| 02 | [Grill: onboarding and password change → spec](issues/02-grill-onboarding-spec.md) | grilling | open | 01 |
| 03 | [Approve onboarding proof and delivery contracts](issues/03-approve-onboarding-contracts.md) | research | implemented local contract; native evidence open | D-T proof and contract evidence |
| 04 | [Require current-password proof in settings](issues/04-current-password-settings.md) | task | implemented; release evidence open | 03 |
| 05 | [Enforce required replacement with recovery](issues/05-enforce-required-password-replacement.md) | task | implemented; real-boundary evidence open | 03; authorized real-boundary checks |
| 06 | [Remember the navigation introduction](issues/06-student-navigation-introduction.md) | task | implemented; device evidence open | 03, 05 |
| 07 | [Verify hosted rollout and shared-device journeys](issues/07-verify-hosted-onboarding-rollout.md) | task | open | 04–06; compatible deployment and authorized test access |

## Current implementation - 2026-10-26

The owner approved tickets 03-07 and repeatedly directed implementation. Settings proof, required
replacement/lifecycle, API and SQL gates, recovery, and navigation introduction are now in the working
tree. Exact contract, commands, results and evidence limits live in
[account-onboarding sections 1 and 7](../../docs/specs/account-onboarding.md).

03-06 remain open pending native Auth/concurrency and real-boundary acceptance. Their earlier
source-only comments are historical. Migration 0021 has been applied only to the isolated local
stack, not a hosted project. 07 retains the real Auth/socket/signing/device release checks.
No new hosted project is required to continue implementation. No necessary prefactor was identified.

### Source coverage

| Source criteria | Ticket owner |
|---|---|
| US-01 AC-01–AC-05: lifecycle, legacy exemption, replacement and required screen | 05 |
| US-02 AC-06–AC-08: authorization boundaries and ADR-078 image-link exception | 05 |
| US-03 AC-09–AC-11: settings proof, input and inline success | 04; required-flow proof/input also 05 |
| US-04 AC-12/AC-13: partial completion and reset ordering | 05 |
| US-05 AC-14–AC-16: introduction and persistence | 06; persistence foundation and reset/restore preservation in 05 |
| SH-01/SH-08: authority, exits, ordering and trust | 05 |
| SH-02: credential handling and teacher-only recovery | 04, 05 |
| SH-03–SH-07: applicable states, errors, accessibility, copy and safeguards | Each affected slice, 04–06 |
| OD-01–OD-05 and D-T | 03 |
| §7 generator hardening recommendation | Approval in 03; implementation in 05 |
| §4 edge cases and §6 verification | Relevant slice above; integrated evidence in 07 |
| OD-06 and hosted/mobile gaps | Prerequisite evidence in 03; release evidence in 07 |

## Answers

Ticket 01 records the original audit. The current implementation and remaining evidence are recorded
in the spec and tickets 03-07. Local SQL is not hosted Auth or socket evidence.
