# ADR-074 — Onboarding rollout exempts existing students until reset

**Status:** Accepted (2026-10-26), interview decisions Q4–Q5.

**Context:** [ADR-073](./ADR-073-students-replace-teacher-issued-passwords-before-product-access.md)
requires password replacement before product access. The audit found no existing state that
distinguishes teacher-issued passwords from passwords already chosen by children.

**Decision:** Apply the requirement to accounts created after rollout and to future teacher resets.
Existing student accounts are exempt until a future teacher reset. This narrows ADR-073's rollout
scope; it does not weaken enforcement for students whose password change is required.

**Rationale and tradeoff:** The owner chose to avoid interrupting existing students, accepting that
an existing teacher-issued password may remain in use until a teacher reset.

**Related navigation decision:** Show one short, dismissible introduction after the student's first
required password change. Explain Bookshelf, Gallery, and Profile, including password change and
Log out in Profile. Provide a "Go to my bookshelf" button. Do not repeat the introduction after
later teacher resets. This replaces a guided tab-by-tab tour with one brief explanation; children
may dismiss it without remembering all destinations. How completion is remembered remains open.

These decisions settle ADR-073's open rollout and navigation-format questions. State ownership,
password rules, and reset/completion recovery remain open. No spec, schema, API, or application
behavior is changed by this record.
