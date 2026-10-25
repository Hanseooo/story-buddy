# 01 — Audit: review decisions and what a child sees

**Status:** ready-for-agent
**Type:** research
**Progress:** open
**Blocked by:** None
**Conflict gate:** `teacher-review-and-approval.md` §12–13. Reading is allowed. Proposing a design
that shows a decision to a child needs the owner's verdict first.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

## Question

What does a review decision store and show today, and what would feedback that a child can see
and act on require, including teacher comments and highlights on story text?

## Starting evidence (2026-10-25)

- `jobs` stores only `approved_at` and `rejected_at`, mutually exclusive
  (`supabase/migrations/0011_jobs_rejected_at.sql`). No reason or comment field exists.
- Decisions go through `POST /jobs/{id}/review` (`backend/app/review.py:31`). The teacher screen has
  Pending, Approved and Rejected tabs (`frontend/app/classroom/[classroomId]/books/page.tsx:14`).
- The spec deliberately hides rejection from the child (`docs/specs/teacher-review-and-approval.md:534`,
  `:550`).
- `jobs.input_text` is the raw, pre-redaction story (`AGENTS.md`), so it is not a safe anchor for
  comments a classmate could reach.

## Investigate

- Every child-facing surface that renders a book's review state today.
- What a child can do with feedback. Is there a revise-and-resubmit path? A resubmit is a new paid
  run, so find the cost and the image budget.
- Wording a child reads as encouraging rather than rejected. Check existing kid-facing copy rules.
- A comment data shape: who writes it (the classroom's teacher), who reads it (the owning child, never
  classmates), RLS, retention, and how it interacts with `docs/specs/storybook-deletion.md`.
- Whether teacher comments need PII redaction (a teacher may write a child's name).
- Highlights: which text they anchor to (page text, not `input_text`), what happens if that text
  changes, and tap-to-open notes on mobile with accessible names.
- What an ethics re-review would need to cover.

## Edge cases the answer must cover

- A comment written about a child that the child should not read.
- A book deleted while comments exist.
- A teacher changes a decision after the child has seen feedback (Undo exists today).
- The child is offline or not logged in when feedback arrives. How do they find out?

## Done when

- Findings are labelled *measured* or *inferred*, with file references.
- Options for wording, the child's next step, the comment model and highlights, each with tradeoffs.
- The schema change and the ethics item each option needs.
- Cost estimate and a go/no-go.

## Comments
