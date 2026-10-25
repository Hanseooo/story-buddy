# 01 — Audit: what a child can change today

**Status:** ready-for-agent
**Type:** research
**Progress:** open
**Blocked by:** None
**Conflict gate:** ADR-029 §2, ADR-069. Reading and $0 analysis are allowed. Proposing a change to
the reveal or to page generation needs the owner's verdict first.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

## Question

What control does a child have over characters and pages today, and what would appearance prompts,
child input on a rejected page, and custom prompts cost in safety, spend and quality?

## Starting evidence (2026-10-25)

- The reveal gives 3 "try again" taps (`MAX_RETRY_TAPS`), each picking an attribute from a list.
  Free text (`notes`) is deliberately never offered (`backend/pipeline/reveal.py:15`, `:30`).
- Known gap: a moderation flag on a tapped redraw falls back to an untargeted draw and loses the
  child's attribute (`AGENTS.md`, `reference-moderation-retry` spec §4.6).
- No page-level redo for the child was found on the process page
  (`frontend/app/s/[profileId]/process/[jobId]/page.tsx`). *Inferred*, confirm it.
- Lead from 2026-10-11: editing the current reference fixed 5 of 9 count misses and carried onto
  pages. It is not adopted. Tradeoffs are in `docs/capstone/model-probes-2026-10.md`, "Edit repair of
  references: tradeoffs of adopting it".
- Spend bounds are named constants in `backend/app/config.py` (image budget, prelude). Every paid draw
  calls `check_image_budget()` first.

## Investigate

- Appearance prompts: chips only, chips plus free text, or free text. What free text needs: input
  moderation, PII redaction, prompt-injection limits, the style-forbidden trait filter (ADR-035).
- Whether an edit of the current reference serves the child better than a fresh draw.
- Child input on a rejected page: which rejections the child would ever see (gates run before the
  child does), what the child could say, and the budget per book.
- A custom-prompt verdict, with reasons.
- How each option interacts with the research record (prompt versions, changelog rows).

## Edge cases the answer must cover

- A child types something unsafe or personal into a free-text field.
- A child asks for a trait the story contradicts, or the style forbids.
- The budget runs out mid-book.
- The redraw is flagged by moderation, and the child's wording is lost (the known gap above).

## Done when

- Findings are labelled *measured* or *inferred*, with file references.
- Options with tradeoffs, the ADR each needs, and the custom-prompt verdict.
- Any paid probe proposed with a cost.
- Cost estimate and a go/no-go.

## Comments
