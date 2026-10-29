# 03 — ADR-081: teacher notes the child can read

**Status:** Accepted (2026-10-29)
**Type:** task
**Progress:** resolved
**Blocked by:** None

**Parent:** `docs/specs/teacher-review-and-approval.md` §14
**What to build:** ADR-081 as its own file plus an index row, status *Proposed*. The ticket closes
when the owner changes it to *Accepted*.
**Source criteria:** §14.5 (migration `0026` is ADR-flagged), §14.10 readiness line, §14.8, `AGENTS.md` §2
**Scope:** `docs/product/adr/ADR-081-*.md`, one row in `docs/product/ADRs.md`
**Out of scope:** the migration itself (05); any code
**Complexity:** Low — the decisions are already made in §14; this records them
**Blast radius:** Local — docs only
**Unblocks:** 05

## Context
§14.10 says ADR-081 must be accepted before `0026` lands. Neither the file nor an index row exists
yet. §14.8 counts more than three modules, so the `AGENTS.md` §2 gate applies.

## Read first
- `docs/product/adr/ADR-080-teacher-held-moderation-and-exact-content-clearance.md` — status line,
  amendments list, and how a private service-role table is justified
- `docs/product/ADRs.md` — row format (line for ADR-080)
- `docs/specs/teacher-review-and-approval.md` — §14.1, §14.5, §14.6, §14.9, §14.10, and §4.10,
  invariants 9 and 12, §13.6
- `.scratch/ptd-review-feedback/issues/01-audit-review-feedback.md` — `## Answer` and owner verdict

## Behavior this changes
None (docs).

## Acceptance criteria
- [ ] The ADR records the decision: the `job_review_notes` table (not a `jobs` column, because
      `0008:28,46` expose whole rows), the `classrooms.review_notes_enabled` switch off by default and
      written only by the server, owner-only reads through endpoints, one note per book, no redaction,
      and the badge that clears.
- [ ] It names what it amends: spec §4.10, invariants 9 and 12, and §13.6 (SH-01, SH-05). It also
      lists the rejected alternatives from §14.9.
- [ ] It names OD-9 (ethics re-review before real children) as a release gate, not a build gate.
- [ ] The index row says "Proposed".
- [ ] The owner sets the status to Accepted with a date. Until then, 05 stays blocked.

## Guidance
Keep it short. Link to the spec sections and don't copy them.

## Verification
Read-through against §14.5 and §14.9. No commands.
**Targeted:** None. **Full suite:** No.

## Blocked by
None.

## Comments

**2026-10-29, owner verdict:** “i accept”. ADR-081 and its index row are Accepted.
Ticket 05's ADR prerequisite is satisfied. OD-9 remains a release gate before real children see notes.
