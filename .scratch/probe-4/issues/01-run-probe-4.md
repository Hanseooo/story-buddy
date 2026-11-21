# 01 — Run probe 4 (Filipino/Taglish moderation) against the shipped moderation stack

**Status:** needs-triage
**Type:** task
**Progress:** open
**Parent:** GitHub issue #138 (the SDLC record reports probe 4 as not run)

## Why
Probe 4 is loop 3's entry gate (ROADMAP.md, Phase 0.5: "Gate → Phase 2: probe 4, no MISS in either direction") and the
release gate for real children. It has never run: `PHASE_05_RESULTS.md` §Probe 4 is still ⬜, and
`docs/capstone/sdlc-record.md` §3 lists it as a deviation. The moderation stack shipped without it
(PR #12, 2026-08-02).

## What to do
1. Read `PHASE_05_RESULTS.md` §Probe 4 and ADR-011. The probe was written against the July 2026
   stack; check the command and the ~26-case set still match the moderation layers as configured
   now, before running anything. A mismatch is a finding, not something to patch mid-run.
2. Run it (`uv run python -m spikes.phase_05 moderation`, or its successor) and score both
   directions: harmful caught by at least one layer, benign flagged by none.
3. Record the result in `PHASE_05_RESULTS.md`, then update loop 3's gate result in
   `sdlc-record.md` §2, `methodology.md` §1.3 and `sdlc/data.ts` together (their tests keep them in step).

## Out of scope
Changing moderation thresholds or models. A MISS goes to its own decision.

## Comments
