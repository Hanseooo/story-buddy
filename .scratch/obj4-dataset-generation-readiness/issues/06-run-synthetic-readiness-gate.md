# 06 — Run the synthetic-generation readiness gate

**What to build:** A reproducible zero-cost gate gives an evidence-backed go/no-go decision for the paid three-story synthetic smoke. It verifies the integrated budget, training, and evaluation closures without using credentials, donated stories, GPU training, or held-out data.

**Blocked by:** 01 — Enforce a megapixel-bound generation budget; 03 — Bind training to the selected immutable freeze; 05 — Complete preregistered reporting and claim assignment.

**Status:** completed
**Labels:** `criticality:high`, `complexity:medium`

- [x] The full deterministic backend test suite and Ruff pass from the documented backend environment.
- [x] The zero-cost corpus fixture completes and reports one story, expected fixture structure, zero provider image calls, and zero spend.
- [x] Training dry-run, evaluation fixture, artifact-integrity checks, and operator-command checks all pass against synthetic data.
- [x] Documentation and committed implementation expose one end-to-end command sequence with no stale or forbidden package-manager commands.
- [x] The verification record distinguishes passed checks, intentional skips, unavailable external infrastructure, and residual risks.
- [x] No provider, GPU, donated-story, annotation, real freeze, or held-out artifact is accessed.
- [x] The resulting verdict explicitly authorizes only the three-story synthetic smoke, not full generation, donation intake, training, or held-out evaluation.

