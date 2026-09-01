# 02 — Reconcile the Batch 3 implementation baseline

**What to build:** Operators and future agents see one authoritative Batch 3 interface. The intended evaluator refinements in the current working state are reconciled with their tests, obsolete standalone instructions are removed in favor of the canonical research runbook, and repository status documentation reflects what is actually implemented.

**Blocked by:** None — can start immediately.

**Status:** completed
**Labels:** `criticality:high`, `complexity:medium`

- [x] Inventory the existing Batch 3 working changes before editing and preserve unrelated user work.
- [x] Evaluator implementation and deterministic tests expose one consistent interface in the committed baseline.
- [x] The canonical runbook contains the supported Objective 4 commands and no bare `pip`, removed CLI form, or conflicting freeze path.
- [x] The obsolete duplicate operator runbook is removed rather than maintained in parallel.
- [x] Repository status guidance no longer claims that the exact model revision or McNemar test is missing when the implementation contains them.
- [x] A repository-wide search finds no remaining copy of the superseded commands or stale Batch 3 status claims.
- [x] Relevant evaluator and integrity tests, Ruff, and whitespace checks pass, with results recorded in the ticket handoff.


