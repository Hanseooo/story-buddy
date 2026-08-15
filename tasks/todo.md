# Current Task: Pipeline Consistency Docket — S2 Design

- [x] Read project guidance, lessons, the docket, S1 carry-forward constraints, current code/specs, and recent commits.
- [x] Reconcile S2 status and spot-check binding constraints against the current implementation.
- [x] Clarify S2 purpose, scope, constraints, and success criteria one question at a time.
- [x] Propose 2–3 approaches with trade-offs and a recommendation.
- [x] Present the S2 design in reviewable sections and obtain approval.
- [x] Record the approved closure in the canonical docket; do not create a duplicate S2 spec.
- [x] Self-review the written closure for placeholders, contradictions, ambiguity, and scope.
- [x] Extract and confirm S2 binding constraints, then update the docket status.

## Outcome

S2 was waived as a separate deliverable because `docs/specs/visual-continuity.md` already owns and
implements the approved behavior. The docket now records BC-7…BC-12, marks S2 `WAIVED`, and makes
S3/S4 `READY`. No implementation changed and no visual-quality claim was made.

---

# Current Task: Pipeline Consistency Docket — S3 Design

- [x] Explore S3 context: project guidance, docket, relevant specs/code, recent commits.
- [x] Offer the visual companion only if a genuinely visual question arises. Not needed for the
      conceptual composition-vs-identity decision.
- [x] Clarify S3 purpose, constraints, and success criteria one question at a time.
- [x] Propose 2–3 mechanisms with trade-offs and a recommendation.
- [x] Present the S3 design in reviewable sections and obtain approval.
- [x] Write the approved S3 spec in `docs/specs/` and commit it (`ea20d92`).
- [x] Self-review the written spec for placeholders, contradictions, ambiguity, and scope.
- [ ] Ask the user to review the written spec. Awaiting response.
- [ ] Record and confirm S3 constraints in the docket; stop before implementation planning.

---

# Current Task: Reference Pipeline Hardening

- [x] Diagnose character prompt contamination and the Supabase reference timeout.
- [x] Confirm PII pseudonymization remains unchanged.
- [x] Obtain approval to implement both independent fixes with delegated agents.
- [x] Create the implementation plan in `docs/specs/plans/2026-08-15-reference-pipeline-hardening.md`.
- [ ] Implement and review Task 1: character-reference prompt fidelity.
- [ ] Implement and review Task 2: signed reference URL delivery.
- [ ] Review the combined blast radius and run backend pre-merge verification.
- [ ] Record commands, results, unverified external behavior, and residual risks below.

## Outcome

In progress.

---

# Current Task: Pipeline Consistency Docket — S4 Design

- [x] Explore S4 context: project guidance, docket, relevant specs/code, and recent commits.
- [x] Reconcile S4's stale null-location question against the already-built carry-forward behavior.
- [x] Clarify S4's artifact, persistence, transient-change, gating, and failure decisions one at a time.
- [x] Propose alternatives with trade-offs and a recommendation.
- [x] Present the S4 design in reviewable sections and obtain approval.
- [x] Write the approved S4 spec at `docs/specs/setting-consistency.md`.
- [x] Self-review the written spec for placeholders, contradictions, ambiguity, and scope.
- [x] User approved the written spec.
- [x] Record and confirm S4 constraints in the docket; stop before implementation planning.

## Outcome

S4 chose a frozen text-only location canon in the existing `Location.description`, retained the
existing carry-forward and prompt order, and routes permanent setting mismatches through the
existing scene-constraint retry path. The approved spec is `docs/specs/setting-consistency.md`;
BC-13…BC-18 are confirmed, S4 is `DONE`, and S5 is `READY`. No implementation or paid model run
occurred, and no visual-quality claim was made.
