# Canonical reference fidelity — measured on the C3 corpus, September 2026

**Measured:** 2026-09-23 · **Corpus:** the 79 canonical reference images in `data/judge/corpus/ref/`,
the campaign the C3 labelling ran on · **Method:** every reference read against the `characters` block
of its bundle's `memory.json`, with no generated page, no label and no `ref_verdict` used as an input.

This is a finding about **reference generation**, not about labelling. Nothing here changes a label,
excludes a pair, or feeds the Objective 4 sensitivity analysis — the reasoning for that separation is in
`ambiguous-references-2026-09.md` under "Changes to this criterion": a rater never sees the description,
so a reference that contradicts its description is still a usable anchor.

---

## The numbers

| | |
|---|---|
| References checked | 79 |
| Differ structurally from their own `CharacterDescription` | **21** |
| Characters whose description says "no face" or "smooth unbroken front surface" *and* have a reference | 11 |
| …of those, references that drew a face anyway | **11 of 11** |
| `ref_verdict.matches_description` across all 98 characters | 73 true · 6 false · 19 absent |
| …of the 11 no-face violations, passed as `matches_description: true` | **7** |

The gate rejected 6 references in the whole corpus. The screen found structural mismatches in 21.

## The face slot — one behaviour, not eleven accidents

In every `body_features` list, index 1 is the face descriptor. Where `analyze` wrote "no face" or
"smooth unbroken front surface" for an object or invented creature, `fal-ai/qwen-image` drew two eyes
and a mouth regardless. It did this every single time it was asked.

| Story | Character | Description says | Reference draws | `ref_verdict` |
|---|---|---|---|---|
| syn-008 | Mister Kettle | smooth unbroken front surface | two eyes and a smile | passed |
| syn-006 | Sardo | smooth front surface with faded label | two eyes, a smile, two legs | passed |
| syn-016 | the vacuum | smooth front surface with nozzle | two eyes, two legs with feet | passed |
| syn-017 | Bakal | smooth unbroken front surface | an eye and a smiling muzzle | passed |
| syn-001 | Bok-Bok | metal beak and comb, no face | an eye and a smile; comb soft red, not metal | passed |
| don-005 | the mango tree | smooth unbroken front surface | a two-eyed smiling face on the trunk | passed |
| syn-011 | Tarsi | large round eyes, no nose or mouth | a clear nose and smiling mouth | passed |
| syn-007 | Halo | smooth front surface, one spoon-shaped appendage | two eyes, two feet, a second nub | failed |
| syn-010 | Bramblefoot | no face, five leaf ears | full badger face, two ears, three leaves | failed |
| syn-012 | Cog | eight legs, key on back, smooth front | six legs, no key, two-eyed face | failed |
| syn-014 | Nimbus Nine | nine raindrop feet, no face | four legs, two-eyed smiling face | failed |

Four failed the gate and shipped anyway: `best_draw` re-rolls up to three times and returns the best of
them, so a character that fails every draw still gets a reference.

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

## What this supports

- **ADR-056 and `reference_judge_investigation_2026-09-02.md`**, which established on a single sheep
  that the reference judge cannot ground stated attributes. Here it is on a corpus: 7 of 11 explicit
  "no face" violations passed, and the gate rejected 6 references where 21 are wrong.
- **Issue #96** — a person checking references before pages are drawn would catch roughly a quarter of
  them. This is that rate.
- **Issue #97** — the face-slot cases are the ice-cream problem thirteen times over: `analyze` describes
  an object in its inanimate form, and the story then animates it.
- **Issue #95** — the presentation failures (hair unstated, clothing stated) are the human-character
  half of the same gap.
- **The write-up's limitations**, where the honest sentence is that the anchor every page is drawn from
  is unfaithful to its own specification about a quarter of the time, and the automatic gate does not
  detect it.

## What it does not support

Any change to a label, any exclusion from the held-out set (§9.7), or any claim that the judge's
Objective 4 numbers are wrong. The judge is scored on page-versus-reference agreement with a human
looking at the same two images. An unfaithful reference changes what the characters look like; it does
not change whether the human and the judge agree about them.
