# 04 — Reword the child's download line

**Status:** ready-for-agent
**Type:** task
**Progress:** open
**Blocked by:** None

**Parent:** `docs/specs/teacher-review-and-approval.md` §14
**What to build:** When a child's book isn't approved yet, the book page reads "Ask your teacher about
downloading this book" and no longer says "Your teacher needs to approve this book before you can
download it". The button stays disabled exactly as today.
**Source criteria:** US-04 / AC-17, SH-01 (book page), §14.5 "reworded, not removed"
**Scope:** the hint paragraph on the child book page, its tests, and closing D-V in `DECISION_BACKLOG.md`
**Out of scope:** the note panel on the same page (08); teacher labels (09)
**Complexity:** Low — a copy change with pinned tests
**Blast radius:** Local — one kid page
**Unblocks:** None

## Context
The current line names the decision to the child, which contradicts §4.10 (DECISION_BACKLOG D-V,
found in audit 01). SH-01 allows only this reworded line and the note badge.

## Read first
- `frontend/app/s/[profileId]/book/[jobId]/page.tsx` — the `pdf-approval-hint` paragraph and `canDownload`
- `frontend/app/s/[profileId]/book/[jobId]/page.test.tsx` — the two assertions on the old string
- `docs/product/DECISION_BACKLOG.md` — entry D-V

## Behavior this changes
- The old string is pinned by `book/[jobId]/page.test.tsx` (around `:113` and `:186`). AC-17 replaces it.

## Acceptance criteria
- [ ] An unapproved book shows "Ask your teacher about downloading this book". The button is
      disabled, and its `aria-describedby` still points at the hint.
- [ ] An approved book shows no hint and an enabled button, as today.
- [ ] For pending, approved and rejected rows, the page text contains none of "approve", "approved",
      "rejected", "pending" (SH-01).
- [ ] D-V is marked closed in `DECISION_BACKLOG.md`, citing §14 and AC-17.

## Guidance
`canDownload` already derives from `approved_at`. Don't touch it. Only the copy changes.

## Verification
Extend the existing page test. Run it red by restoring the old string.
**Targeted:** `cd frontend && pnpm exec vitest run "app/s/[profileId]/book/[jobId]/page.test.tsx"`
**Full suite:** at the batch gate (`pnpm lint && pnpm build && pnpm test`)

## Blocked by
None.

## Comments
