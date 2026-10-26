# ADR-076 — Onboarding password rules and completion recovery prioritize usability

**Status:** Accepted (2026-10-26), interview decisions Q8–Q9.

**Context:** [ADR-075](./ADR-075-profile-state-enforces-password-change-with-current-password-verification.md)
leaves password rules and completion recovery open. The owner chose an eight-character minimum
and recoverable completion, stating that UX is the priority.

**Decision:** Require at least eight characters, allow spaces, and do not require a mixture of
capitals, numbers, or symbols. Encourage memorable words. A required replacement must differ from
the current teacher-issued secret word. The later spec must align student and teacher forms with
the server policy rather than relying on client validation alone.

If the password update succeeds but clearing the required-change state fails, keep product access
blocked and permit secure completion retry using the now-current password. The child should not
need another password change or teacher reset solely because completion failed. A retry must not
clear a requirement created by a newer teacher reset. The mechanism and API contract remain open.

**Rationale and tradeoffs:** Eight characters reduces typing burden for children. This deliberately
accepts a shorter minimum than NIST's fifteen-character recommendation for password-only
authentication; it is not a claim of conformance to that guidance. Recoverable completion avoids
turning a partial failure into routine teacher support, at the cost of additional verification and
reset-ordering logic.

**Evidence:** [NIST SP 800-63B password guidance](https://pages.nist.gov/800-63-4/sp800-63b.html#passwordver)
(checked 2026-10-26); the existing teacher form already checks eight characters
(`frontend/app/settings/page.tsx`). Hosted policy compatibility remains unverified.

These decisions settle ADR-075's password-rule and user-facing partial-completion recovery
questions. Restore behavior and introduction persistence remain open. No application behavior,
schema, or API is changed by this record.
