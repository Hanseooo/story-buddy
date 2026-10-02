# Canonical reference fidelity — measured on the C3 corpus, September 2026

**Measured:** 2026-09-23 · **Corpus:** the 79 canonical reference images in `data/judge/corpus/ref/`,
the campaign the C3 labelling ran on · **Method:** every reference read against the `characters` block
of its bundle's `memory.json`, with no generated page, no label and no `ref_verdict` used as an input.

This is a finding about **reference generation**, not about labelling. Nothing here changes a label,
excludes a pair, or feeds the Objective 4 sensitivity analysis — the reasoning for that separation is in
`ambiguous-references-2026-09.md` under "Changes to this criterion": a rater never sees the description,
so a reference that contradicts its description is still a usable anchor.

**Gate correction, 2026-09-26:** The original screen below used
`ref_verdict.matches_description` as if it were the acceptance condition. It is not.
`char_bible` accepts only an empty `contradictions` list with `text_free: true`, and
can still ship the best failed draw. The synthetic-only recount and its limits are in
`pipeline-gate-audit-2026-09.md`. The 79-image visual screen is retained as a manual
finding; its gate and causal interpretations below have been corrected.

---

## The numbers

| | |
|---|---|
| References checked | 79 |
| Differ structurally from their own `CharacterDescription` | **21** |
| Characters whose description says "no face" or "smooth unbroken front surface" *and* have a reference | 11 |
| …of those, references that drew a face anyway | **11 of 11** |
| `ref_verdict.matches_description` across all 98 characters | 73 true · 6 false · 19 absent |
| …of the 11 face-slot contradictions, recorded as `matches_description: true` | **7** |

The six `matches_description: false` values are **not** a gate-rejection count.
The screen found 21 structural mismatches; that manual classification has not been
independently repeated.

## Face-slot contradictions observed

In every `body_features` list, index 1 is the face descriptor. The 11 selected
references below add facial features contrary to that descriptor. The descriptors
are not identical: some specify a blank surface, while others specify eyes or a
beak but exclude another facial part. One stored draw per character cannot establish
that a model always behaves this way or that all 11 share one cause.

| Story | Character | Description says | Reference draws | `matches_description` (not the gate) |
|---|---|---|---|---|
| syn-008 | Mister Kettle | smooth unbroken front surface | two eyes and a smile | true |
| syn-006 | Sardo | smooth front surface with faded label | two eyes, a smile, two legs | true |
| syn-016 | the vacuum | smooth front surface with nozzle | two eyes, two legs with feet | true |
| syn-017 | Bakal | smooth unbroken front surface | an eye and a smiling muzzle | true |
| syn-001 | Bok-Bok | metal beak and comb, no face | an eye and a smile; comb soft red, not metal | true |
| don-005 | the mango tree | smooth unbroken front surface | a two-eyed smiling face on the trunk | true |
| syn-011 | Tarsi | large round eyes, no nose or mouth | a clear nose and smiling mouth | true |
| syn-007 | Halo | smooth front surface, one spoon-shaped appendage | two eyes, two feet, a second nub | false |
| syn-010 | Bramblefoot | no face, five leaf ears | full badger face, two ears, three leaves | false |
| syn-012 | Cog | eight legs, key on back, smooth front | six legs, no key, two-eyed face | false |
| syn-014 | Nimbus Nine | nine raindrop feet, no face | four legs, two-eyed smiling face | false |

Four have `matches_description: false`. In the synthetic-only recount, all ten
listed synthetic characters have a **failing final gate verdict** and still have a
selected reference. The donated case was not read in that recount. `best_draw`
returns the best draw after capped failures, so a failed verdict need not stop pages.

## Stated counts not rendered

| Story | Character | Description says | Reference draws |
|---|---|---|---|
| syn-018 | Mango | four ears (two big, two small) | two large ears, full frontal view |
| syn-002 | Mopsi | six legs | four, side-on, open ground where the others would be |
| syn-009 | Ngiwi | a bird with legs | no legs or feet at all, body unoccluded |
| syn-024 | Wobblejaw | four jaws arranged like flower petals | one central mouth, plus two legs never mentioned |
| syn-030 | Mudlark | five long neck feathers | four, on the nape rather than the neck |
| syn-012 | Cog | eight legs | six |
| syn-014 | Nimbus Nine | nine raindrop feet | four legs |
| syn-010 | Bramblefoot | five leaf ears | two ears, three leaves |

Counter-example worth keeping: syn-001 Quill's description states "three amber eyes" and the reference
draws exactly three. The generator does render stated counts sometimes.
Its stored reference verdict nevertheless lists "two orange eyes" as a contradiction;
the visual spot-check and verdict fields are recorded in `pipeline-gate-audit-2026-09.md`.

## Parts invented or misplaced

syn-020 Pebble (shell *is* a chipped teacup; drawn as an ordinary shell with the teacup on top) ·
syn-025 Sunny-Side (two jointed clawed arms never described) · syn-019 Snorkel (eyes stated as two
mismatched buttons; drawn as plain dots with one button beside the head) · syn-015 Sablefin (third
lantern on the flank, plus an unexplained ventral structure) · syn-016 General Lint (two eye objects
where "one lost button eye" probably means one remains) · syn-022 Bantay (both stated eyes on the near
side of a near-profile head).

## Where the pattern sits

Concentrated in the synthetic bundles and in non-human, object and invented-creature characters. Human
characters are near-clean on structural parts — their failures are the presentation ones on the
ambiguous-reference list, not missing limbs.

## What was deliberately not counted

- **Parts hidden by the pose.** Eyes closed in a smile (don-014 Mrs. Maple, syn-008 the grandmother,
  syn-026 Aling Cora), profile animals showing one eye, a three-quarter toad with one foreleg behind the
  body. The rulebook exempts these and so does this measurement.
- **Markings.** syn-004 Tuko (seven stated stripes, five drawn) and syn-013 Puddleback (nine stated
  spots, fewer drawn). Stripes and spots are not on the rulebook's countable-part list.
- **Counts that cannot be resolved from the drawing.** syn-005 Pipit's four wings and syn-023
  Marmalade's ten arms both come out differently depending on how overlaps are split. No defect can be
  asserted either way, and none is.
- **A gendered name against a differently-read drawing** (don-003 Snow, don-009, syn-005, syn-021 Lala,
  syn-026 Perla), where only the name or the `notes` field disagrees and the drawing is internally
  consistent. `analyze.py:250` forbids inferring anything from a name, and this measurement holds to it.
- **Plural characters drawn as one figure** (syn-006 "the family", syn-020 "the other tortoises"). Real,
  and not a body-part defect. Open question rather than a finding.

## A prediction, stated before it was counted

**Recorded 2026-09-24, during adjudication, from three observed pages. No count exists yet, and this
paragraph is committed before one is run so that the order is git's and not a memory's.**

**The hypothesis (the study owner's).** `fal-ai/qwen-image-edit-2511` does not read a *glyph* face — two
dots and a drawn curve, of the kind `fal-ai/qwen-image` puts on an object character — as a face. When a
page asks that character to show an emotion, the edit model has nowhere to put the expression, so it draws
an anatomical face on the nearest face-shaped surface and leaves the glyph untouched. The observed case:
syn-006 Sardo, a tin can, whose page carries its original dot-and-smile label face **and** a second larger
face with brows and a worried mouth on the metal body above it.

**What it predicts, in the owner's words: strongest on non-human characters, and strongest again on strong
emotions — angry, surprised — but not confined to non-humans; a human page demanding a strong expression
may show it too.** Concretely:

1. Duplicated or relocated faces cluster on characters whose reference face is a **glyph**, and are rare on
   characters whose reference face is **rendered** (pupils, a modelled mouth), regardless of species.
2. Within the glyph group, the defect is more frequent on pages whose scene calls for a **high-arousal**
   emotion than on calm ones.
3. Invented limbs travel with it, since the same prompt asks an object to act.

**What would falsify it.** Duplicated faces spread evenly across glyph-faced and rendered-face references;
or concentrated on non-humans irrespective of how their reference face was drawn, which would make it a
species effect rather than a glyph-legibility one.

**What it does not touch.** Any label. Labels are image-only and the generator's reason for a defect is
never an input — the adjudication rule for these pages is row 5 of `adjudication-notes-2026-09.md` and it
is unchanged by whether this hypothesis holds. What it changes is **issue #99**, whose cause 1 points at
#97: if the mechanism is glyph illegibility rather than inanimate description, improving reference
generation is one candidate. A page-prompt or editor effect must be tested separately.

---

## What this supports

- **ADR-056 and `reference_judge_investigation_2026-09-02.md`**, which established on a single sheep
  that the reference judge can misground stated attributes. Here the 7 of 11
  `matches_description: true` values show that boolean is insufficient; the later
  synthetic recount shows the actual gate can fail and still ship a reference.
- **Issue #96** — 21 of 79 references were classified as structurally mismatched in
  this manual screen. A prospective human review rule, detection rate, and cost remain unmeasured.
- **Issue #97** — inspect each story for an actual visual transformation before
  treating a face-slot contradiction as a scene-state problem. Speech or emotion
  alone does not establish a change of form.
- **Issue #95** — the presentation failures (hair unstated, clothing stated) are the human-character
  half of the same gap.
- **The write-up's limitations** — the original manual screen found 21 of 79
  anchors structurally unfaithful to their descriptions. The gate can flag a
  reference and still ship it; its detection accuracy needs a separate visual audit.

## What it does not support

Any change to a label, any exclusion from the held-out set (§9.7), or any claim that the judge's
Objective 4 numbers are wrong. The judge is scored on page-versus-reference agreement with a human
looking at the same two images. An unfaithful reference changes what the characters look like; it does
not change whether the human and the judge agree about them.
