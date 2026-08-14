# Current Task: Visual Continuity Implementation Plan

- [x] Read `AGENTS.md`, `CLAUDE.md`, `tasks/lessons.md`, the approved visual-continuity spec, MASTER_SPEC §5-6, and linked ADR constraints.
- [x] Trace the contract/analyze/segment and prompt/judge/retry implementation seams and deterministic tests.
- [x] Decide the plan is too long for one file and split it into three sequential, independently reviewable implementation gates.
- [x] Write TDD tasks with exact files, interfaces, test commands, implementation snippets, commits, and verification.
- [x] Self-review spec coverage, placeholder patterns, type/signature consistency, frozen graph/config invariants, and Tier B prerequisites.

## Outcome

Plan split into three files under `docs/specs/plans/`: contract/canon; scene planning/prompts; judging/retry/verification. The plans preserve the approved graph, model, budget, and retry architecture. Tier B explicitly stops for owner input because the repository lacks the five images' label metadata and the exact trace story text.
