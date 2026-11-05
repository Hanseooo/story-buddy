# 01 — Audit: what a child can change today

**Status:** ready-for-agent
**Type:** research
**Progress:** resolved
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

**2026-11-01, A2 screen run (owner approved, ~$0.27): failed, 2 of 9.** A tap that edits the
reference with only the chip's wording does not fix counts; hand-written change instructions fixed
5 of 9. A2 as specified is no-go. See `docs/capstone/model-probes-2026-10.md`, "Tap wording as an
edit: result".

## Answer (2026-11-01, $0, no model calls)

### What a child controls today

- *Measured.* Only the reveal. Up to 3 redraws per book (`backend/pipeline/reveal.py:16`), each a
  chip picked from style-filtered canon (`reveal.py:29`). `notes` is never offered. The confirm
  endpoint rejects any attribute not in the offered chips (`backend/app/main.py:274`,
  `moderation_hold.py:867`), so free text cannot reach a draw.
- *Measured.* A tap makes one fresh text-to-image draw with `Be sure to include: {chip}.` and
  overwrites the reference unconditionally (`char_bible.py:374-406`, ADR-029 §2).
- *Measured.* No page-level redo for a child. The child routes are `book`, `process`, `write`,
  `gallery`, `settings`; only `process` has a redraw control. Teachers decide whole books, not pages
  (`teacher-review-and-approval.md` §3). The only page replacement is the teacher's, for a
  moderation-held picture (ADR-080, rank 2 ticket 09).
- *Measured.* A child never sees a rejected page. Scenes go through up to 3 consistency draws and
  ship best-of (never a failed job, ADR-010/028); output moderation holds or replaces flagged ones
  before display. So "a rejected page" can only mean a page the child dislikes, or one a teacher
  points at in an ADR-081 note.
- *Measured.* Known gap still open: a flag on a tapped redraw falls back to an untargeted 3-draw
  mint and drops the chip (`reference-moderation-retry.md` §4.6).

### What each option costs

**Appearance**

| Option | Safety | Spend | Quality | ADR |
|---|---|---|---|---|
| A1. Chips as today, plus keep the child's chip through a moderation flag | none new | none | fixes the lost-choice gap only | state-contract decision ADR-069 names; ADR-029 §2 stands |
| A2. A tap edits the current reference instead of redrawing it | edited image passes `char_ref_mod` again; fal's checker refused one edit 6 of 6 (needs fallback to the old reference) | same one image per tap | lead only: hand-written edits fixed 5 of 9 counts, identity kept 9 of 9; a miss is a different wrong picture | amends ADR-029 §2 |
| A3. Chips plus a short free-text box | new moderated child text: redaction (`providers.redact_pii`) and both classifiers at confirm; a flag holds under ADR-080 like ticket 10; style filter (ADR-035) applies word-level | same per tap; adds moderation latency at the reveal | *Inferred, important:* scene prompts restate the stored description (`prompt_optimizer.build_prompt`) while the scene judge compares against the reference (`consistency_check.py:308`). "Make her hair blue" against a story that says black changes the reference but not the prompt, so pages disagree and retries are spent. Fixing that means the child's text rewrites canon, which ADR-069 rules out ("not a second author of canonical identity") | amends ADR-029 §2 and ADR-069; ships after rank 2's audit |

**Pages**

| Option | Safety | Spend | Quality | ADR |
|---|---|---|---|---|
| P0. No child page input; teachers use ADR-081 notes | none new | none | none | none |
| P1. Child redraws one finished page, picking a chip from the characters on it | redraw passes output moderation; flag holds under ADR-080; an approved book returns to pending | ~1 image + judge per redo; *inferred* ~$0.03-0.04 from the October probe prices. `IMAGE_BUDGET` = 55 is per book; the audit's 335 draws for 150 pages suggests typical books leave headroom, but the worst case has none, so the button needs a disabled "no redraws left" state | fresh draw of the same scene prompt: same ~duplicate/identity defect rates as any draw | new ADR: post-completion generation, approval reset, a per-book page-redo cap |
| P2. P1 plus free text | as A3 | as P1 | as A3, plus the child can ask for a scene the story does not contain | as P1 plus ADR-069; ships after rank 2's audit |

### Custom prompts: no

- The story is the prompt. Raw prompts let pictures drift from the child's words, which ADR-013's
  "child's words verbatim" posture and the corpus measurements assume.
- Writing image prompts is an adult skill; a 10-12-year-old gets worse pictures, not more control.
- Every free-text field is more load on a moderation stack measured to over-refuse
  (rank 2 audit, `moderation-backstop-over-refuses`), so more false holds for teachers.
- Prompt injection's blast radius here is small (text only reaches an image model, output is
  moderated), so injection is not the reason. Canon drift and false holds are.

If the panel's ask must be met in words, A3's bounded box is the most that is defensible, and it
still has the canon problem above.

### Research record

`build_corpus` auto-confirms the reveal (#96), so A1/A2/P1 do not touch corpus generation, but each
pipeline change after `technical-defense-2026-10` gets a `research-changelog.md` row. A2 changes
what a reveal tap means, so ADR-029's reported tap behaviour must be marked as pre-change.

### Edge cases

- Unsafe or personal free text: A3/P2 only. Redact, classify, hold for the teacher (ADR-080); the
  child sees neutral waiting copy. Chips-only options have no such input.
- A trait the story contradicts or the style forbids: chips cannot (canon, style-filtered).
  Free text can, see A3's quality column.
- Budget out mid-book: taps are inside the 15-image prelude; a P1 redo must check
  `check_image_budget()` and show a disabled state, never fail the book.
- Flag on a redraw loses the child's choice: A1 fixes it; A2/A3 inherit the gap unless A1 ships.

### Paid probe proposed

A2's screen: the tap's own wording (`Be sure to include: {chip}.`) as an edit on the same 9
count-miss references, one draw each, about **$0.27**. Pass rule to set before running (suggest 6
of 9, as before). Not run; needs approval.

### Go / no-go (assistant's recommendation; the owner rules)

- **Go:** A1 now. Small, no conflict with ADR-029 §2, fixes a known child-facing bug.
- **Go if the $0.27 screen passes:** A2, behind the off-by-default setting.
- **Go, narrow:** P1 chips-only, behind the setting. It is the panel's page ask without free text.
- **No-go for this milestone:** A3, P2 and custom prompts. The canon conflict has no design yet,
  and they wait on rank 2's audit anyway.
