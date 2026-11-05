# 02 — Grill: appearance and page input → spec

**Status:** ready-for-human
**Type:** grilling
**Progress:** resolved
**Blocked by:** `.scratch/ptd-child-creative-control/issues/01-audit-child-creative-control.md`
**Ships after:** `.scratch/ptd-moderation-calibration/issues/01-audit-moderation-false-alarms.md`,
for any child free text only. It does not block this grill (owner, 2026-11-01).
**Conflict gate:** ADR-029 §2, ADR-069. Open the session by naming the conflict and wait for the
owner's verdict.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

## Decide

- How a child adjusts a character: the input type and the draw type (fresh or edit).
- Whether a child has any say on pages, and its budget.
- Custom prompts: yes or no, and why.
- The off-by-default setting, if the change is ADR-gated.

## Output

- Amendments to `docs/specs/character-review-ux.md` and `docs/specs/reference-moderation-retry.md`
  as needed, with a new ADR drafted for ADR-029 §2 or ADR-069.
- Build tickets `03` onward, each `Blocked by` this ticket.

## Comments

### Interview decisions (2026-11-01)

- **Conflict verdict: opened.** The owner opened ADR-029 §2 and ADR-069 for this epic, free text
  included. Synthetic-only, off by default, ethics re-review before real children. Free text ships
  only after rank 2's audit 01.
- **Goal:** better UX for the child and freedom to choose. Image generation is a dice roll; the
  answer is a general tool where the child judges, not more per-defect prompt fixes. No more paid
  tests for this epic; the owner accepts that the pencil ships unmeasured on children's wording.
- **A2 (tap as an edit with the chip's wording) is dropped:** failed its screen, 2 of 9.
- **Magic pencil, two tools, at "Meet your characters" and on the finished book:**
  1. *Other versions:* where more than one draw exists, the child picks among them. Each must pass
     moderation before a child sees it (unchosen scene draws are `safety_eligibility="unreviewed"`,
     `output_mod.py:118`). No new image cost.
  2. *Pencil:* the child writes what to change; one edit of the current picture; the child keeps
     the new or the old one. Text is PII-redacted and moderated; a flag goes to the ADR-080 teacher
     hold. Each use is logged (before, after, words, choice).
- **Rejected:** a blank custom prompt that draws a new page; pausing the run on each page that
  reached max retries.
- **A character change that contradicts the story:** the child's words become this book's note on
  the character and later pages are drawn with it (amends ADR-069).
- **Reveal:** today's chip button stays as "draw again"; the pencil sits beside it; both share the
  3 goes.
- **Budget:** 3 character goes plus 5 page pencils per book, checked against `IMAGE_BUDGET` (55),
  with a disabled "no pencils left" state. Other versions cost no images.
- **Character other versions:** keep the unchosen reference draws (today `mint_reference` uploads
  only the winner, `char_bible.py:347-371`) and moderate one only when the child opens it. A
  character accepted on its first draw has one version.
- **Approved book edited:** any page change returns the book to the teacher's review queue
  (whole-book review stays).
- **Pencil results skip the consistency checker:** moderation only; the child judges by keeping old
  or new.
- **Pencil text defaults:** about 200 characters, any language the moderation stack takes, neutral
  "waiting for your teacher" copy on a flag.

### Spec drafted (2026-11-01)

[`docs/specs/magic-pencil.md`](../../../docs/specs/magic-pencil.md), status draft. Blockers: seam
confirmation (R-1), OD-01 to OD-06 (three are pivots found in the edge-case sweep: earlier pictures
as versions, teacher-review mode required, Filipino/Taglish text), and the ADR amending ADR-029 §2
and ADR-069 (R-3).

## Answer (2026-11-01)

Spec approved: [`docs/specs/magic-pencil.md`](../../../docs/specs/magic-pencil.md). ADR-082 accepted,
amending ADR-029 §2 and ADR-069. Owner took every recommendation (OD-01 to OD-06, seams) and added
audit option A1 as US-07. Build tickets `03` onward are not written yet.

