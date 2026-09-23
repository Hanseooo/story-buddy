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
   cannot be made out well enough for a rater to apply Step 2.

It does **not** go on the list for being unusual, ugly, off-style, badly composed, drawn twice, or for
disagreeing with the story. Those are generator faults the labels already handle.

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

**Characters reviewed:** ___ of ___ · **Listed:** ___ · **Written on:** 2026-09-__
