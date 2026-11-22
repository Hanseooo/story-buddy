# 17 — SDLC section: development loops page, record and Figure 3

**Status:** ready-for-agent
**Type:** task
**Progress:** resolved
**Parent:** [`docs/specs/research-page-refresh.md`](../../../docs/specs/research-page-refresh.md)
**What to build:** `/research/sdlc`, the six development loops traced to merged PRs, with Figure 3 and Table 1 for the paper (GitHub issue #138).
**Source criteria:** US-29 AC-23–AC-27, AC-06 (moved); SH-02, SH-03
**Scope:** `docs/capstone/sdlc-record.md` (new), `methodology.md` §1.3 and §1.5, `docs/diagrams/drawio/sdlc_spiral.drawio.svg`, the sdlc page, the methodology page (Spiral table and Phase 0.5 card moved out), reading order, docs hub entry, stale Phase rows in `research_direction_and_goals.md` and `design_decisions_and_risks.md`.
**Out of scope:** Running probe 4 (separate ticket). Changing the paper's text (groupmates).
**Complexity:** Medium — the record is hand-classified, the git facts are tested
**Blast radius:** Local — research pages and capstone docs
**Unblocks:** None

## Decisions (grilled 2026-11-22)
- Keep the Spiral label; rebuild the loops from the record, not from the plan.
- One spiral diagram serves as Figure 3.
- Evaluation is the last loop, marked open.
- Probe 4 is reported as not run.
- The record holds literal values; `sdlc/data.test.ts` checks each row against git (skipped in a shallow clone). Dates are the merge commit's committer date (+0800).
