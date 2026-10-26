# ADR-077 — Restored students change passwords and introduction dismissal persists

**Status:** Accepted (2026-10-26), interview decisions Q10–Q11.

**Context:** The restore endpoint issues a new secret word (`backend/app/classrooms.py`).
[ADR-073](./ADR-073-students-replace-teacher-issued-passwords-before-product-access.md)
requires replacing teacher-issued credentials, while
[ADR-074](./ADR-074-onboarding-rollout-exempts-existing-students-until-reset.md)
specifies a single dismissible navigation introduction. The owner accepted both recommendations.

**Decision:** Restoration requires a password change before product access, like a teacher reset.
It applies to restored existing accounts as well as accounts created after rollout. This closes the
restore question left open by ADR-075 without exempting a newly issued restoration secret word.

Store navigation-introduction dismissal on the student's profile so completion follows the student
across devices and browsers. Keep this fact distinct from password-change-required state: a reset
or restoration must not make a previously dismissed introduction reappear. The later spec defines
the field and protected update; no field name is selected here.

**Rationale and tradeoffs:** Restoration issues a replacement credential, so the same rule applies
as for a reset, at the cost of another password change for a returning child. Profile persistence
fulfills the once-per-student introduction across shared classroom devices, at the cost of one
additional stored fact and a protected update. Browser-only memory was rejected because switching
devices or clearing browser data could repeat the introduction.

These decisions settle ADR-075 and ADR-076's open restore and introduction-persistence questions.
Detailed schema/API design, hosted Auth verification, and the rendered phone walkthrough remain
separate work. No application behavior, schema, or API is changed by this record.
