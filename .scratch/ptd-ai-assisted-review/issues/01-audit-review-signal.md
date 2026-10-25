# 01 — Audit: is there a signal the AI can be trusted on?

**Status:** ready-for-agent
**Type:** research
**Progress:** open
**Blocked by:** None
**Conflict gate:** ADR-017, `teacher-review-and-approval.md` §12–13. Reading and $0 analysis are
allowed. Proposing an auto-decision needs the owner's verdict first.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

## Question

Does the pipeline produce any signal that separates books a teacher would approve from books they
would reject, well enough to let a teacher skip the confident ones?

## Starting evidence (2026-10-25)

- No approval-confidence signal exists today. The review stores only `approved_at` and `rejected_at`.
- *Measured*: the stored reference check failed 15 of 38 clean references and 15 of the 17 defective
  ones (`docs/capstone/model-probes-2026-10.md`), so its verdict is not a clean signal on its own.
- *Measured*: three moderation layers gave three different answers on the B6 corpus (see the
  `ptd-moderation-calibration` audit).
- ADR-017 defers auto-approve to Future Work pending an ethics re-review.

## Investigate

- Candidate signals already recorded per book: moderation agreement, consistency-gate results,
  retries used, a failed page shipped as best-of.
- On stored books with teacher decisions, if any exist, how well each signal predicts the decision.
  Report denominators. If too few decisions exist, say so.
- What "unsure" would mean and what share of books it would leave for the teacher.
- What ADR-017 and an ethics re-review would need for the toggle.

## Edge cases the answer must cover

- An unsafe or upsetting book the signal calls confident.
- How a teacher spot-checks auto-approved books, and how they undo one.
- The record of who or what approved each book.
- The toggle is per classroom and sits under an off-by-default setting.

## Done when

- Signal quality on stored data, labelled *measured*, or *inconclusive* with the reason.
- Options (sort-and-flag only, auto-approve the confident ones, none), each with tradeoffs and the ADR
  and ethics work it needs.
- Cost estimate and a go/no-go.

## Comments
