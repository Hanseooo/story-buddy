# Adjudication notes — C3, September 2026

**Owner:** study owner (`383b2bd4…`, `is_adjudicator = true`) · **Started:** 2026-09-23
**Registered by:** `PREREGISTRATION_OBJ4.md`, amendment 2026-09-23, item 4
**Rules:** `docs/specs/labelling-rulebook.md` — frozen. Nothing here is a new rule.

The rulebook says an uncovered case gets the closest existing rule plus a dated private note, and the
same choice every time after. This file is that note, kept in the repo so the dates are git's and not a
memory's. The count of notes is reported in the write-up.

At the time this file was created: 795 non-pilot pairs, 623 agreed, **172 conflicted and awaiting
adjudication**, 0 adjudicated.

---

## Standing decisions

One row per kind of case. Write the decision the **first** time the case appears, then apply it to every
later instance without re-deciding. If a later case makes an earlier decision look wrong, the earlier
decision still stands for this campaign — add a line under Limitations instead.

| # | Case the rules do not cover | Closest rule applied | Decision | Decided | Times applied |
|---|---|---|---|---|---|
| 1 | Hair **length or style** differs; hair colour matches | Step 2 lists hair **colour** only, and Step 3 makes presentation alone Same | *(draft — confirm or change before the first such pair)* Same, unless the face itself is drawn as a different individual, which is `different_face` on its own terms | 2026-09-__ | |
| 2 | The **reference** omits a structural part the pages all draw — seen: a canonical with no eyes, every page with eyes | Step 2 lists eyes under Wrong Body Feature; the exclusion column exempts "a part hidden by the pose" | *(draft — confirm before the first such pair)* Decide which of the two it is, **from the reference**: eyes **absent** on an otherwise visible face → Wrong Body Feature → **Different**. Eyes **not visible** — closed, covered by hair or a hat, face turned — → hidden by the pose → **Same** | 2026-09-__ | |
| 3 | The page adds or changes an **outfit** the story called for, everything else matching | Step 3 as written: "clothing or style alone is Same". Labels are image-only, so whether the story required the outfit is not an input | **Same.** Before recording it, check the two axes clothing is easily confused with: body colour (Wrong Color covers skin, fur, hair, eye and body colour — never garment colour) and countable parts (wings, horns, limbs). If either of those holds it is Different *for that reason*, and the outfit is still not one of them | 2026-09-23 | |
| 4 | A body **part is missing or mangled in the drawing** — seen: a rooster drawn with body, legs and tail but no neck or head | Step 4's "judge what is visible... never mark Different only because the face cannot be seen", and Step 5, which exists for "merged, missing or duplicated body parts" | **Same Character**, and tick **Broken Anatomy**. A rendering defect is not an identity difference: the question Step 2 asks is *which individual is this*, and a broken drawing of the right character is still the right character. **Not** Character Absent — that means you cannot find them on the page at all, not that part of them is missing. Wrong Body Feature is reserved for a part that is *different* (three eyes where there were two, no tail on an intact animal), not for a part the generator failed to render | 2026-09-24 | |
| 5 | An **object or invented-creature** character whose reference is minimal (a face and stick legs) is drawn on the page with **limbs it never had**, and sometimes a **second face** — seen: a tin can given two arms and a second set of eyes and mouth above its original label face | Step 2 lists limbs under Wrong Body Feature and exempts only "a part hidden by the pose"; Step 5's list is "merged, missing or duplicated" and does not reach a part invented from nothing | Split it by which verb applies. **Invented** part (arms where there were none) → **Wrong Body Feature → Different**. **Duplicated** part (a second face, a third eye beside two correct ones) → **Broken Anatomy**, identity untouched. **Missing** part → Broken Anatomy (row 4). A page may trigger more than one of these; tick each in its own field. That the story needed the character to act is not an input — Step 4's Transformation row already says there is no special case | 2026-09-24 | |

Row 1 is pre-filled as a draft because it is the case most likely to come up first and the one the
raters are most likely to have split on. Confirm it, or replace it, **before** adjudicating the first
pair it touches — not after seeing how the pairs fall.

Row 4 separates the two artifact questions the screen asks side by side. The test: *could you name the character from what is drawn?* Yes, with a part missing or mangled → Same + Broken Anatomy. No, they are not on the page → Different + Character Absent. Both raters called the rooster Absent when its body, tail and legs were plainly there, so this row is written the first time the case appeared rather than after seeing how the rest fall.

Row 5 has a **known cost, accepted deliberately**: the object and invented-creature characters are the ones `analyze` describes in their inanimate form, so their references carry a minimal face and stick legs while their pages show them acting. Applying the frozen rule to them will skew that whole group toward Different on Wrong Body Feature. That is a real generator behaviour and the judge should learn it, but the write-up must say the group is affected as a group. The characters concerned are listed in `reference-fidelity-2026-09.md`, and the underlying cause is issue #97.

Row 2 is not a gap in the rules, only in which branch applies; the decision is which one, once, for
every pair of that character. Note what it is **not**: "the pages all agree with each other, so the
reference is the odd one out" is not an axis this rulebook has. Every label compares one page to the
canonical reference, and agreement among pages is not evidence for either answer. If the reference is
the defective artefact, the place that records it is
`ambiguous-references-2026-09.md`, not a label.

## Cases that are already covered — no note needed

Recorded here so they are not mistaken for gaps:

- **The character is drawn twice.** Step 1: compare the better match. A duplicate is not an identity
  failure, and Step 5's Broken Anatomy is for merged, missing or duplicated parts of *one* figure — not
  a second copy of the character.
- **A transformation the story required.** Step 4: no special case, apply Step 2. Labels are image-only;
  the judge never sees the story, so neither does the label.
- **Clothing, style or lighting alone.** Step 3: Same.
- **Back view or hidden face.** Step 4 as written.

## Limitations to carry into the write-up

- Pairs where **both raters agreed on a wrong answer** never reach adjudication. The adjudicator sees
  only the 172 conflicts, so this file cannot record — and adjudication cannot fix — an error the two
  raters shared.
- The adjudicator is **not blind** to which rater produced which label.

## Log

Append a line whenever a decision above is applied to a pair for the first time, or whenever something
happens that a reader of the results would want to know. Do not record pair-level labels here; the
database is the record of those.

- 2026-09-23 — file created; adjudication not yet started.
- 2026-09-24 — row 5 added on its first live case (Sardo the tin can, syn-006): arms invented, face duplicated, original face intact.
- 2026-09-24 — row 4 added on its first live case (headless rooster, syn-001). Rows 3 and 4 were both written from conflicts seen during adjudication, which is the procedure: decide the kind once, at first sight, then apply it.
