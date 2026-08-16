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
- [x] Implement and review Task 1: character-reference prompt fidelity.
- [x] Implement and review Task 2: signed reference URL delivery.
- [x] Draft ADR-039 and add its index row in a dedicated ADR session.
- [x] Obtain explicit human acceptance of ADR-039 before retaining the conflicting prompt behavior.
- [x] Review the combined blast radius and run backend pre-merge verification.
- [x] Record commands, results, unverified external behavior, and residual risks below.

## Outcome

ADR-039 was accepted on 2026-08-15. Normal canonical-reference prompts now omit narrative `notes`;
targeted redraws read `ReferenceRetry.attribute` directly and emphasize it unconditionally. Analyzer
guidance requires concrete drawable values instead of placeholders. Scene prompts intentionally keep
`notes`, PII pseudonymization is unchanged, and no contract, graph, model, provider, or moderation
ordering changed.

Scene generation now gives fal a fresh 300-second Supabase signed URL for each canonical reference
instead of downloading the full asset through the worker and re-uploading it to fal. URL ordering,
private Storage paths, checkpoint compatibility, and idempotent resume behavior are preserved.

Verification from `backend/` on 2026-08-15:

- `uv run ruff check .` — passed.
- `uv run pytest` — 853 passed, 71 intentionally skipped, 6 deselected; one existing Starlette
  deprecation warning.
- Focused changed surface — 267 passed.
- `git diff --check` — clean.

Repository pre-merge verification also passed: `pnpm lint` and `pnpm test` from `frontend/`, with
34 test files and 269 tests passing. The first frontend test attempt hit the 120-second command
timeout without a result; the isolated retry completed successfully in 31.5 seconds.

Not verified locally: a paid live fal request fetching a private Supabase signed URL. The deterministic
tests prove URL creation, freshness, and ordering but cannot prove fal's external fetch. Remaining
product risk: prompt adherence is probabilistic, and scene prompts still receive narrative `notes` by
ADR-039's deliberately narrow scope. No population-level quality claim is made from the single repro.

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

---

# Current Task: Sanitize placeholder character canon before image generation

- [x] Add regression tests for placeholder values at the canonical and scene prompt boundaries.
- [x] Preserve the ADR-039 permissive contract while projecting blank/placeholder values out of prompts.
- [x] Add an age-appropriate torso-clothing instruction for human/humanoid reference renders.
- [x] Run focused and full backend verification.

## Success criteria

No literal `unspecified`, `none`, `unknown`, or `neutral` value reaches a canonical or scene prompt.
The persisted contract remains backward-compatible, valid descriptions remain unchanged, and no
new terminal failure path or model/image call is introduced.

## Outcome

Implemented `CharacterDescription.without_placeholders()` and applied it to canonical-reference,
judge, reveal, scene, and correction prompt projections. Canonical references now explicitly ask
human/humanoid subjects to wear age-appropriate torso-covering clothing. The initially proposed
terminal validator was rejected because ADR-039 freezes a permissive contract and forbids turning
imperfect extraction into a new child-facing terminal failure; the final fix stays within that ADR.

Verification: `uv run ruff check .` passed; `uv run pytest` passed 861 tests, 71 skipped, 6
deselected, 1 existing Starlette warning. Focused character/prompt/contract tests passed 258 tests
after the final regression addition. `git diff --check` passed.
