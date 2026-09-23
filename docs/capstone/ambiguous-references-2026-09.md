# Ambiguous canonical references — C3, September 2026

**Status:** criterion written, list **not yet filled** · **Created:** 2026-09-23
**Registered by:** `PREREGISTRATION_OBJ4.md`, amendment 2026-09-23, item 5
**Written by:** the study owner. Not by an agent — see "Who may write it" below.

This list enables one registered secondary analysis. The primary analysis keeps every pair (§9.7: no
item is excluded from the held-out set after labelling). The secondary recomputes the same metrics with
pairs dropped whose character appears below, and both are reported however far apart they land.

---

## The criterion, fixed before the list

A character goes on the list when its **canonical reference image**, judged on its own, is

1. **internally contradictory** — the drawing carries two incompatible identity cues at once, so a page
   can follow one and contradict the other. The case that prompted this: a short-haired boy's head above
   a girls' school uniform, where the pages drew longer hair and the character reads as a girl; or
2. **unreadable on an identity axis the rulebook scores** — species, palette, body features or face
   cannot be made out well enough for a rater to apply Step 2; or
3. **defective on a structural part the rulebook counts** — the reference omits or invents a countable
   part (eyes, ears, limbs, tail, horns, wings) that the character's `CharacterDescription` neither
   states nor excludes, so the anchor every page is scored against is itself the anomaly. A part merely
   *hidden* in the reference — eyes closed, covered by hair or a hat, face turned — is not this: the
   rulebook already exempts a part hidden by the pose, and such a character does not belong on the list.

It does **not** go on the list for being unusual, ugly, off-style, badly composed, drawn twice, or for
disagreeing with the story. Those are generator faults the labels already handle. Nor does it go on the
list because the pages agree with each other and not with it; that comparison needs the pages, which
this list may not use.

**Changes to this criterion.** 2026-09-23, before any row was written and before any per-character
number existed: clause 3 added. It was prompted by a reference seen during labelling — a character whose
canonical drawing has no eyes while its pages all draw eyes — which clauses 1 and 2 did not cover,
since that reference is neither self-contradicting nor unreadable. The input was a reference image, which
is the same information this list is built from, and no label, count or agreement figure informed it.
No clause is loosened or removed after the first row is written.

## What may and may not be looked at while writing it

**May:** the canonical reference image, and the character's `CharacterDescription` from its bundle.

**May not:** the generated pages, any label, any pair status, any agreement figure, any per-character
count. The list must be decidable from the reference alone. If a character's entry needs a page to
justify it, it does not belong on the list.

## Who may write it

The study owner. Not a coding agent: §7 holds that all development happens on train and validation only,
and the assistant that writes pipeline prompts and judge code must not view held-out reference images —
that is the same exposure §7 exists to prevent, and it has been kept off throughout this campaign (see
`obj4-readiness-audit.md`, Phase C, where five flagged test pairs were deleted unopened). The owner has
already seen every reference in the course of adjudication and loses nothing by writing it.

**A pre-screen was run, 2026-09-23, and it is not the list.** At the owner's request a separate agent
read all 79 reference images and the `characters` block of each bundle's `memory.json`, applied the
criterion above, and wrote a candidate table to a scratchpad file outside this repository. Its
restrictions: no generated page, no database, no label, no pair status, no agreement figure, and no
script under `backend/`. It reported back to the assistant **counts only** — no character, story or
filename, and no description of any individual image — so no per-character fact about held-out data
reached the session that writes the judge's prompts and evaluation code. That restriction held.

**The authoring act is the owner's confirmation.** A candidate becomes a row only when the owner has
looked at that reference and agreed it meets the criterion; unconfirmed candidates are dropped and the
count of dropped ones is recorded below. The pre-screen chose nothing — it ordered 79 images so the
owner did not have to re-scan them from memory. Any sentence describing this procedure in the write-up
says exactly that.

**What the pre-screen returned** (aggregate, recorded before any row was confirmed): 79 screened, 27
flagged — 4 under clause 1, 1 under clause 2, 22 under clause 3, of which 9 are missing a part the
description states and 13 show a part it does not state. Every case it judged to be a part merely
hidden by the pose it rejected rather than listing. Counting all 79 rather than only the flagged ones,
**21 references differ structurally from what their own description states.**

**`ref_verdict` disagrees with the screen on several of those characters** and was deliberately not used
as an input: it is not part of the criterion, and `docs/capstone/reference_judge_investigation_2026-09-02.md`
and ADR-056 already establish that the reference judge cannot reliably ground stated attributes. The
disagreement is consistent with that finding rather than new, and it is reported as corroboration, never
as a reason to change a label.

## When it must exist

**Before any per-character, per-slice, or before/after-guide number is computed**, and before the
dataset is frozen. Git history is the evidence of that order; a list committed afterwards is selection
on the outcome and the amendment does not authorise one. Adjudication may happen first — it reveals
which pairs conflicted, not how any character scores — but writing this list first is cleaner, and it
is cheap.

## The list

Fill one row per character. Leave the table empty and say so if no reference qualifies; an empty list is
a valid, reportable result.

| `char_id` | Character | Which criterion (1 or 2) | What the reference shows |
|---|---|---|---|
| | | | |

**Candidates from the pre-screen:** 27 of 79 · **Confirmed by the owner:** ___ · **Dropped on
inspection:** ___ · **Added by the owner that the screen missed:** ___ · **Written on:** 2026-09-__
