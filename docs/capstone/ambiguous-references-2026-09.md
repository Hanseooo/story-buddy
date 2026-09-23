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

The test both clauses share: **would a rater, holding this reference beside a page, be unable to tell
what they are comparing to?** That is the only way a reference can distort a label.

It does **not** go on the list for being unusual, ugly, off-style, badly composed, drawn twice, or for
disagreeing with the story. Those are generator faults the labels already handle. Nor does it go on the
list because the pages agree with each other and not with it; that comparison needs the pages, which
this list may not use. And it does not go on the list for disagreeing with its own
`CharacterDescription` — see the next paragraph.

**Changes to this criterion.**

*2026-09-23, morning — clause 3 added, then removed the same day.* Clause 3 read: "defective on a
structural part the rulebook counts — the reference omits or invents a countable part that the
description neither states nor excludes." It was added after a reference was described as having no
eyes while its pages all drew eyes, on the reasoning that the anchor itself was the anomaly.

*2026-09-23, evening — clause 3 removed, before any row was confirmed and before any per-character
number existed.* **A rater never sees the description.** Labels are image-only by design
(`labelling-rulebook.md`; the judge's prompt carries no description either). So a reference that
contradicts its description is still a perfectly usable anchor: the page-to-reference comparison is
well-posed, the label is decidable, and nothing about it is ambiguous to the person doing the work.
Clause 3 measured *defective for the product*, which is a different property from *ambiguous for the
rater*, and only the second one can distort a label. Adding it was a reasoning error, made before the
pre-screen showed how wide it reached.

The removal is recorded rather than done quietly because it is also convenient: it takes the candidate
count from 27 to 5, and a secondary analysis that drops five characters is reportable where one that
drops twenty-seven is a different dataset. The justification above stands without that convenience, and
it is the justification, but a reader is entitled to see both.

**What clause 3 found is kept, not discarded** — it moves to
`docs/capstone/reference-fidelity-2026-09.md` as a reported finding about reference generation, which
is what it always was. No clause is loosened or removed after the first row is written.

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
reached the session that writes the judge's prompts and evaluation code.

**That restriction was then lifted by the owner, the same day, and this line records it rather than
leaving a false claim in place.** The owner asked for the candidate table in the session so the rows
could be looked up in the database, and the assistant read the file at that point. What it now holds:
the 27 candidate rows with story, character, clause and a sentence each, plus the rejected set. It
still has not seen any generated page, any label, any pair status or any agreement figure. The
consequence to state in the write-up if it matters: any later change the assistant makes to `analyze`,
to `char_bible` or to a judge prompt is made by a party that has seen which held-out references are
defective. Those changes are all scheduled after Objective 4 (issues #95, #97), and the fine-tune's
inputs are pinned by `code_commit`, so nothing in the reported result was produced after the exposure —
but the ordering is the reason it is safe, not the exposure being harmless.

**The authoring act is the owner's confirmation.** A candidate becomes a row only when the owner has
looked at that reference and agreed it meets the criterion; unconfirmed candidates are dropped and the
count of dropped ones is recorded below. The pre-screen chose nothing — it ordered 79 images so the
owner did not have to re-scan them from memory. Any sentence describing this procedure in the write-up
says exactly that.

**What the pre-screen returned** (aggregate, recorded before any row was confirmed): 79 screened, 27
flagged — 4 under clause 1, 1 under clause 2, 22 under the since-removed clause 3. Under the criterion
as it now stands, **5 candidates**, and the other 22 move to `reference-fidelity-2026-09.md`. Every case
the screen judged to be a part merely hidden by the pose it rejected rather than listing, including
three references whose eyes are simply closed in a smile.

## When it must exist

**Before any per-character, per-slice, or before/after-guide number is computed**, and before the
dataset is frozen. Git history is the evidence of that order; a list committed afterwards is selection
on the outcome and the amendment does not authorise one. Adjudication may happen first — it reveals
which pairs conflicted, not how any character scores — but writing this list first is cleaner, and it
is cheap.

## The list

Fill one row per character. Leave the table empty and say so if no reference qualifies; an empty list is
a valid, reportable result.

The five candidates the pre-screen returned under clauses 1 and 2 are below, **unconfirmed**. Strike any
the owner rejects on inspection, add any the screen missed, and fill `char_id` from the database.

| `char_id` | Story | Character | Clause | What the reference shows | Confirmed |
|---|---|---|---|---|---|
| `don-005:c1` | don-005 | the narrator | 1 | Cropped dark boy's head and boyish face above a girls' sailor blouse, navy pleated skirt and knee socks. | |
| `syn-028:c0` | syn-028 | Aya | 1 | Short cropped dark boy's haircut and flat brow above a sailor blouse and navy pleated skirt. | |
| `syn-030:c0` | syn-030 | Basti | 1 | Short dark boy's crop and boyish face above a navy pleated skirt with knee socks. | |
| `don-012:c0` | don-012 | Mia | 1 | Bowl cut and neutral face above a school skirt. Weakest of the four — a bowl cut is not a male cue the way the three above are. | |
| `syn-022:c1` | syn-022 | the man | 2 | Skin, hair fringe and shirt all one teal, close to the background's own colour, leaving no usable colour for the Wrong Color rule. Arguable: legible, just monochrome. | |

**Candidates under the current criterion:** 5 of 79 · **Confirmed by the owner:** ___ · **Dropped on
inspection:** ___ · **Added by the owner that the screen missed:** ___ · **Written on:** 2026-09-__
