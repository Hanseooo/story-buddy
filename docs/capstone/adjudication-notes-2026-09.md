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
| 1 | Hair **length or style** differs; hair colour matches | Step 2 lists hair **colour** only, and Step 3 makes presentation alone Same | ~~*(draft — confirm or change before the first such pair)*~~ Same, unless the face itself is drawn as a different individual, which is `different_face` on its own terms. Never confirmed in writing; the labels show it was applied (see Log, 2026-10-09) | Not recorded; first such adjudication 2026-09-26 | 15 of 17 adjudicated pairs of the three listed characters ruled Same |
| 2 | The **reference** omits a structural part the pages all draw — seen: a canonical with no eyes, every page with eyes | Step 2 lists eyes under Wrong Body Feature; the exclusion column exempts "a part hidden by the pose" | ~~*(draft — confirm before the first such pair)*~~ Never confirmed in writing (see Log, 2026-10-09). Decide which of the two it is, **from the reference**: eyes **absent** on an otherwise visible face → Wrong Body Feature → **Different**. Eyes **not visible** — closed, covered by hair or a hat, face turned — → hidden by the pose → **Same** | Not recorded | Owner recalls ruling Same; not checked, the character is not named here |
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

- Pairs where **both raters agreed on a wrong answer** do not reach the ordinary adjudication queue.
  The ten agreed pairs selected by the separate, pre-count label audit below are the recorded exception.
  Other shared errors remain a limitation.
- The adjudicator is **not blind** to which rater produced which label.

## Label audit of agreed pairs

**Rule, set before counting (2026-09-24):** count the agreed-Different pairs whose only reasons are
Wrong Clothing or Wrong Style, which Step 3 calls "always a mistake under these rules". Single digits → a
limitations line. Ten or more → the adjudicator re-labels exactly the pairs the query returns, no more and
no fewer, and nothing is excluded.

**Count (Q1 and Q4, `label-audit-queries.sql`):** 12 of 112 agreed-Different pairs (9 Wrong Style, 3 Wrong
Clothing). Two are test pairs that were already conflicted for another reason and go through the
ordinary queue. The other ten (9 train, 1 val) had consensus, so the queue never shows them. They are
listed in `AUDIT_PAIRS` (`backend/finetune/annotation_truth.py`), and the freeze refuses to run until
each has one round-3 row. The adjudicator labels them from the two images alone, with the raters' labels
hidden, via `label-audit-relabel.sql`. Rounds 1 and 2 stay untouched.

**Counted, not acted on:** 26 agreed-Different pairs include Character Absent. No rule separates correct
uses from misuses like the rooster (row 4) without looking at the images, and looking at only some of them
would be choosing pairs by hand. They are reported as a count in the write-up.

## Log

Append a line whenever a decision above is applied to a pair for the first time, or whenever something
happens that a reader of the results would want to know. Do not record pair-level labels here; the
database is the record of those.

- 2026-09-23 — file created; adjudication not yet started.
- 2026-09-30 — the owner accepted an AI-assisted, image-only review of all ten preselected label-audit
  pairs (nine train, one validation) without independently assigning ten item-by-item labels in this
  session. The assistant proposed Same, intact anatomy, and text-free for each; the owner approved
  those exact values, and ten round-3 rows were inserted under the owner's adjudicator profile.
  A read-back verified ten such rows and the original twenty ordinary rows. This is an explicit
  deviation from independently human-adjudicated reference labels, not evidence of ten independent
  human judgments. No held-out test pair was changed. The separate sixteen-pair exploratory training
  exclusion remains a different decision.
- 2026-09-29 — post-adjudication quality check of synthetic training characters
  `syn-006:c0` (Sardo), `syn-016:c0` (General Lint), and `syn-024:c0` (Wobblejaw). This is an
  unresolved audit flag, not a new rule or a change to any annotation, split, or exclusion list.
  Read-only resolved-label snapshots were 4 Same / 1 Different, 2 Same / 10 Different, and
  12 Same / 3 Different, respectively. The `syn-016:c0` snapshot corrects the mistaken claim
  that it had zero Same pairs.

  The Sardo reference has a small face on its label and two feet. Reviewed pages add arms and
  a separate, larger face, including pages currently resolved as Same; some pages visibly contain
  writing despite `text_free = true`. The Wobblejaw reference has no visible eyes, while reviewed
  pages add eye-like features; row 2 above remains unconfirmed. These are reasons to recheck the
  affected labels against the frozen, image-only rulebook, not grounds to infer that a label must
  change from page-to-page agreement or from how the generator works. General Lint has both
  matching and drifting pages, so a story-wide exclusion is not supported by this review.

  The canonical references are generated with `fal-ai/qwen-image` and scenes with
  `fal-ai/qwen-image-edit-2511`. Different endpoints are verified; inability of the edit model
  to preserve a small or absent face is not. Sardo's original `s3` prompt also requests
  "eyes wide". Its third retry says to match "human, human faces, hands" even though Sardo's
  description has none of those features: `regenerate.py` passes all story characters to
  `correction_clauses`, which joins their body features. This explains the retry text but cannot
  explain drift already present on earlier attempts. Issue #99 separately records the measured
  reference-versus-description face problem; it does not establish this scene-edit cause.

  **Next check:** the study owner reviews the flagged synthetic pairs at full size against the
  existing Step 2 and Step 5 rules, and records each suspected labelling error with its reason.
  Submitted annotation rows are final under `annotation-surface.md` §4; the ordinary adjudication
  path covers disagreements, not pairs on which raters agreed. This review therefore makes no
  automatic label correction. Inspect the per-character Same/Different mix before considering a
  separately documented training-data decision. `freeze_dataset.py` applies
  `RunBundle.exclusions` during dataset construction, but completed `run.json` bundles are
  immutable; adding IDs to them after generation would alter the recorded corpus.
  Keep validation membership fixed for comparisons and preserve the registered held-out primary
  set (§9.7). No change to the registered dataset or generator-cause conclusion is recorded here.

  A separate dated input at `data/judge/intake/omit.json` lists 16
  disputed Same-labelled synthetic training pairs from the image review: 14 with visible
  structural differences and two Wobblejaw pages with ambiguous closed eye-like marks. The
  study owner chose to omit all 16 from a separate exploratory training run, without deciding
  that the two ambiguous labels are wrong. It does not edit annotations or corpus bundles.
  The input affects a new exploratory freeze only when explicitly
  passed to `build_dataset --freeze --train-exclusions`; the registered freeze command omits it.
- 2026-09-24 — row 5 added on its first live case (Sardo the tin can, syn-006): arms invented, face duplicated, original face intact.
- 2026-09-24 — row 4 added on its first live case (headless rooster, syn-001). Rows 3 and 4 were both written from conflicts seen during adjudication, which is the procedure: decide the kind once, at first sight, then apply it.
- 2026-09-24 — label audit run: 12 agreed-Different pairs rest on clothing or style alone; 10 go to a round-3 re-label (see *Label audit of agreed pairs*).
- 2026-10-09 — rows 1 and 2 were never confirmed in writing, so what was applied was reconstructed
  (#94). **Row 1**, from a read-only query of round-3 labels for the three characters on
  `ambiguous-references-2026-09.md` (`don-005:c1`, `syn-028:c0`, `syn-030:c0`): 17 of their 36 pairs
  were adjudicated between 2026-09-26 and 2026-09-29, 15 ruled Same (12, 2 and 1) and 2 ruled
  Different (both `syn-028:c0`; reasons across the two: one `wrong_clothing`, one
  `wrong_body_feature`). The owner remembered ruling these pairs not Same; the labels say otherwise,
  and the labels are the record. Whether the two Different pairs were hair-length cases cannot be
  told from the labels. **Row 2**: the owner recalls ruling Same. Not checked, because this file
  does not name the character, so it rests on recollection.
