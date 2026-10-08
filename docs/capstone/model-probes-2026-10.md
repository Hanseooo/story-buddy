# Model probes — 2026-10

Small paid screens that follow the [stage audit](pipeline-stage-audit-2026-10.md). The owner capped
total spend at USD 2. Synthetic stories only. Images are under the gitignored
`data/judge/evaluations/`. These are screens, not evaluations: one rater (the assistant, looking at
each image), tiny n. The edit probe was not blinded between arms; the count screen was. No
production setting changed.

## Findings and changes

One row per entry below, newest last. Each entry adds its row here when it lands.

| Entry | Finding | Change | Status |
|---|---|---|---|
| Edit-model probe | klein drew a duplicate on 3 of 12 draws where every shipped Qwen page had one | none; a swap needs an ADR and a judge recheck | superseded by the blinded klein screen |
| Reference count screen | no text-to-image model draws stated body counts | none; ADR-056 stands | closed |
| Text-model trial | no open-weight model beats Mistral on the strict-schema path | none; Mistral stays | closed |
| Cast-rule replay | only "species noun in the direction" adds characters without wrong ones | species reconciliation in `segment` | PR #101, awaiting merge |
| Segment prompt trial | no prompt change separates from run-to-run noise | none; `SEGMENT_PROMPT_VERSION` stays 3 | closed |
| Best-of ranking review | ranking `subjects_unique` higher helps one scene and hurts another | none; `_rank` unchanged | closed |
| Defect tally | duplicates are the largest major defect a change could still fix | none; picked duplicates as the next target | closed |
| Duplicate causes | 8 of 13 duplicate pages are the edit model's own behaviour; no prompt or data fix covers more than 2 | none | closed |
| Edit-model probe, extension | klein drew 9 of 12 draws clean on 6 more duplicate scenes; 18 of 24 across both rounds | [ADR-062](../product/adr/ADR-062-klein-4b-base-is-the-candidate-scene-editor-not-yet-the-production-one.md): klein base edit is the candidate scene editor; the swap waits for a blinded rate screen, a judge recheck and a contract check | accepted 2026-10-08; the exploratory blinded screen failed |
| Single-moment line on Qwen | a prompt line asking for one moment left 9 of 10 Qwen draws with a duplicate; klein drew 9 of 10 clean on the same scenes without it | none; the line is not adopted | closed |
| Blinded klein screen | on 30 random scenes, klein drew as many duplicates as Qwen (4 each) and lost identity on 10 pages to Qwen's 3 | none; klein fails the preregistered rule, Qwen stays | closed; a follow-up ADR to ADR-062 is due |
| One-moment directions on Qwen | rewriting the direction as one instant left 7 of 10 duplicate-scene draws with a copy or an extra; 2 of 4 missing actions appeared | none; duplicates stay an open defect | closed |

## Edit-model probe: FLUX.2 klein 4B base — 2026-10-08

**Question.** The duplicate replay showed duplicates persisting across redraws although every prompt
already asks for each character once. Does a different edit model avoid them?

**Setup.** `fal-ai/flux-2/klein/4b/base/edit` (Apache-2.0; `image_urls`, up to 4; has
`negative_prompt`; fal defaults 28 steps, guidance 5). It was given each scene's stored
**first-attempt** prompt, the same canonical references in the same order, `NEGATIVE_PROMPT` and
1024×768. 2 draws per scene, 20 calls. The comparison is the stored `qwen-image-edit-2511` draws.
Qwen had 3 attempts with corrected prompts; klein had 2 with the uncorrected one.

- Duplicate scenes (6): every one shipped a review-confirmed duplicate, and on 3 of them the judge
  flagged all 3 Qwen draws. syn-001 s2, syn-008 s3, syn-016 s1, syn-019 s1, syn-021 s2, syn-021 s6.
- Controls (4): shipped on attempt 1, passed, review `acceptable`. Lowest SHA-256 of
  `klein-probe|<story>|<scene>`, 2 with one reference and 2 with two: syn-022 s3, syn-018 s0,
  syn-025 s1, syn-002 s2.

**Result (assistant's reading of each image).**

| Scene | Qwen shipped | klein draw 1 | klein draw 2 |
|---|---|---|---|
| syn-001 s2 | Quill twice | clean | clean |
| syn-008 s3 | grandfather twice | an extra old man (beard and glasses split across two men) | same |
| syn-016 s1 | General Lint twice | one Lint, but drawn as a clothed figure (identity drift) | Lint cloned four times |
| syn-019 s1 | second small Snorkel | one Snorkel; other toys in the box | one Snorkel; two green dinosaurs added |
| syn-021 s2 | Ashwing twice | clean; moth eyespots weak | clean |
| syn-021 s6 | Lala twice | clean | clean; hair drifts brown |
| syn-022 s3 (control) | clean, invented sign lettering | clean, on the counter not behind it | clean |
| syn-018 s0 (control) | clean | clean | clean |
| syn-025 s1 (control) | clean | clean | clean |
| syn-002 s2 (control) | clean | Marisol, not Mopsi, eats (action wrong) | same |

A named character drawn twice or an extra cast-like figure appeared on **3 of 12** klein draws in
the duplicate scenes, against every shipped Qwen page there. Controls kept identity on 8 of 8
draws, with no lettering where Qwen had invented a sign, and one scene had the action wrong on both
draws.

**Reading.** Promising, not decided. n is 10 scenes and 1 rater. syn-016's story really does have an
army of dust bunnies, so some extra figures there are correct. Regression to the mean is possible,
because these scenes were chosen for failing. klein does not fix references: syn-002's sheep keeps
four legs. A production swap still needs what C3-10 lists: judge recheck on the new image
distribution, `REFERENCE_FIELD` row, safety-flag surface (black image vs 422), and an ADR.

**Cost.** 20 calls. fal does not state whether input references are billed. The upper bound at
$0.009/MP for output plus two 1 MP inputs is about $0.03 per call, so at most about $0.55.

## Reference count screen: three text-to-image models — 2026-10-08

**Question.** [ADR-056](../product/adr/ADR-056-numeric-attribute-fidelity-is-a-documented-limitation-not-a-pre-campaign-fix.md) left one lever open for stated counts far off the body
plan: a different text-to-image model. Does any candidate draw the count the story states?

**Setup.** The exact prompt `char_bible` builds (`filtered_description` then `reference_prompt`),
with `NEGATIVE_PROMPT`, `REFERENCE_NEGATIVE` and, for non-humanoids, `NON_HUMAN_NEGATIVE`, at
1024×768. Three arms: `fal-ai/qwen-image` (production) 2 draws, `fal-ai/qwen-image-2512` 2 draws,
`fal-ai/flux-2/klein/4b/base` 3 draws. Eight synthetic characters with a stated count, 56 calls.
Files were named by hash and tiled in hash order, so arm was hidden while counting. Scores were
saved before the key was opened.

| Character | Stated | Hits | Notes |
|---|---|---|---|
| syn-001 c0 | three eyes | 0/7 | all two eyes or fewer |
| syn-002 c1 | six legs | 0/7 | all four legs |
| syn-004 c0 | seven stripes | 0/7 | 4–5 body stripes, or 10+ counting the tail, or spots; one qwen-image-2512 draw is arguable at 6–7 |
| syn-005 c0 | four wings | 0/7 | all two wings |
| syn-012 c1 | eight legs | 1/7 | klein; the rest six legs |
| syn-013 c0 | nine spots | 0/7 | all 10 or more |
| syn-014 c0 | nine raindrop feet | 0/7 | every draw is a cloud with falling rain; two grew stick legs |
| syn-015 c0 | three lanterns | 4/7 | qwen-image 2/2, qwen-image-2512 2/2; klein drew three candles twice and four lanterns once |

Per arm: qwen-image 2/16, qwen-image-2512 2/16, klein 1/24. Every hit except one is the
three-lantern prop, a small count on an object rather than the body.

**Reading.** No candidate fixes body counts. This agrees with ADR-056: counts off the body plan fail
across model families, not only on qwen-image. Swapping the reference model is not worth an ADR on
this evidence, and the documented limitation stands. Caveats: one rater, 7 draws per character,
characters picked for having a stated count (which favours the hard cases), and counts on small
features (stripes, spots) are themselves uncertain within ±1.

**Cost.** qwen-image 16 calls at $0.02 per MP rounded up to 1 MP, $0.32. klein 24 at $0.009/MP,
about $0.22. qwen-image-2512 16 calls; its price was not checked, and at qwen-image's rate it is
$0.32. Screen total about $0.86. Both probes together come to at most about $1.41 of the $2 cap.

## Text-model trial: analyze + segment — 2026-10-08

**Question.** Does a stronger open-weight text model plan better scenes (right cast, faithful
direction) than `mistralai/mistral-small-3.2-24b-instruct`?

**Setup.** `analyze` then `segment`, unchanged, on six synthetic stories: syn-002, 007, 010, 016,
019, 021. Same prompts and strict schema (`structured_text`), temperature 0. Each candidate was
pinned to one provider through `TEXT_PROVIDERS`, as production pins Mistral to deepinfra.

**Which candidates ran at all.**

| Model | Provider | Result |
|---|---|---|
| openai/gpt-oss-120b | default routing | 5/6 broke the schema, 1/6 timed out at 120 s |
| openai/gpt-oss-120b | deepinfra, then groq | broke the schema; groq returned nothing parsable |
| qwen/qwen3-235b-a22b-2507 | deepinfra | broke the schema (1 story tried) |
| deepseek/deepseek-chat-v3.1 | deepinfra | 1/6 broke the schema, 3/6 exceeded the production 120 s call bound; about 185 s per story against Mistral's 42 s |

Every schema break was the same: a character-description object in `locations[].description`, which
the sent schema declares a plain string. The schema was checked (`to_strict_json_schema`). So these
endpoints do not enforce the grammar, and the models copy the character `description` shape into
the same-named location field.

**Scene quality, DeepSeek vs Mistral (assistant's reading, 5 stories).** The three timeouts were
rerun with a 400 s bound for the trial only.

- DeepSeek cut finer: 36 scenes against Mistral's 26 on the same five stories. More pages mean
  more images to pay for.
- Both kept the moth out of the cast in syn-021 before it is named. DeepSeek made it worse: s0
  directs an empty wall although the moth is in the excerpt, and s1 directs "a large moth" with
  an empty cast.
- DeepSeek dropped the baby from syn-019's roster, then directed "facing baby who is laughing".
  That baby has no reference.
- DeepSeek dropped Bramblefoot from syn-010 s5, the scene where he pulls the fence apart.
- DeepSeek put 5 framing values ("close-up", "wide shot") in the viewpoint slot.
- DeepSeek did better in places. Mopsi is the one eating in syn-002 (Mistral's direction had
  this right too, but Qwen-Edit drew Marisol). syn-016's vacuum and dust-bunny beats get their
  own scenes, where Mistral cast no vacuum when it arrives. And no odd directions like Mistral's
  "empty toy box with Snorkel's faint outline".

**Reading.** No gain. The one candidate that fits the strict-schema path is slower, less reliable
and makes the same class of cast error. The cast errors come from what the segment prompt asks
for, not from model capacity: both models leave a character out while the story calls it by
description. Mistral stays.

**Cost.** Text calls only, a few cents.

## Cast-rule replay: does a deterministic rule fix cast errors? — 2026-10-08 ($0 + cents)

**Question.** `segment` already adds a roster character whose *name* appears in the rendered visual
direction. Would a wider rule fix the audit's cast errors without adding wrong characters?

**Rules replayed.** For a roster character missing from a scene's cast:

- **B**: its species head noun appears in the visual direction.
- **A**: its species head noun appears in the excerpt.
- **C**: its name appears in the excerpt.

Head noun means the last word of `species`, with parentheses and anything after "made of"
dropped. A and B skip `human`, which stories never use, and any species two roster entries share.
That rules out Pebble against "the other tortoises" and Mango against "the other bats".
Matching is singular and whole-word, so a plural ("moths") never matches.

**Samples.** The stored corpus runs (30 synthetic stories), plus a fresh Mistral rerun of `analyze`
+ `segment` on the same 30 (154 scenes). Each addition was judged against the excerpt and direction,
and against the stage audit's 29 cast errors (6 major).

| Rule | Additions (stored / fresh) | Correct | Wrong | Arguable |
|---|---|---|---|---|
| B: species in direction | 2 / 2, the same scenes | syn-021 s0, s1 (both audit majors) | none | none |
| A: species in excerpt, not B | 4 / 2 | syn-014 s5 (stored only) | syn-009 s4 (the cat "stopped coming"), in both samples | syn-010 s1, syn-014 s1 |
| C: name in excerpt | 9 / 9 | syn-018 the other bats, syn-019 s2 Snorkel, syn-021 s6, syn-001 s4, syn-014 s5 | syn-003 s2 gardener, syn-004 s2 kid, syn-016 vacuum twice ("a vacuum cannot follow you") | syn-010 s1, syn-014 s1 |

**Reading.**

- B made no wrong additions in either sample, but it fixes only 2 of the 6 audit majors, both in
  one story.
- A and C each have about one wrong addition for every right one. Neither fixes the direction:
  the added character gets a reference and a slot in the subject-count clause, but the direction
  never says what it does.
- syn-019 s2 is a direction that drops a beat (Snorkel on a hand), not a cast slip.
- About 20 of the 29 cast errors are groups or people with no roster entry: the librarian, the
  pigeons, the other cranes, Lint's army, the neighbours. No cast rule can add those. They need
  `analyze` to roster them, or the direction to stop drawing them.

**Untested edge cases for B.** Generic head nouns ("creature" for Bramblefoot, Tarsi and Wobblejaw;
"machine" for the vacuum) could match a different creature or machine in a direction. Neither
sample has a case. A direction naming another individual of a cast species ("a stray dog" while
Bantay is off-page) would add Bantay; neither sample has that either.

## Segment prompt trial: roster kinds and a roster-only rule — 2026-10-08 (about $0.09)

**Question.** Most audit cast errors are groups or people with no roster entry, which the direction
draws without a reference. Separately, `SEGMENTATION_PROMPT` lists only roster *names*, so the
model cannot tell that Ashwing is the moth. Does a prompt change fix either?

**Arms.** `segment` only, on each story's stored `analyze` output, so the roster is fixed. Mistral
on deepinfra, 30 synthetic stories per sample.

- **base**: the current prompt, v3.
- **kinds**: adds "What each character is: Lala is a human; Ashwing is a moth." and a rule that a
  character referred to by its kind is that character.
- **variant**: kinds, plus "visual_direction may depict only the roster characters listed …
  show the roster character's reaction or the result instead".

Each sample was scored on the 9 audit cast errors that involve a roster character, matched by
quote; on empty-cast pages; and on directions that name or species-name a roster character missing
from the cast.

| Sample | Audit errors fixed (of 9) | Empty-cast pages | Direction names an uncast roster character |
|---|---|---|---|
| base, run 1 | 3 | 1 | 3 (all syn-021's moth) |
| base, run 2 | 4 | 1 | 2 (syn-021's moth) |
| kinds, run 1 | 6 | 0 | 2 (syn-021's moth) |
| kinds, run 2 | 4 | 2 | 1 (syn-021's moth) |
| variant, run 1 | 8 | 3 | 0 |
| variant, run 2 | 4 | 1 | not scored |

For variant run 1 only, the assistant read every direction in the 19 stories with audit cast
errors. Off-roster beings drawn fell from 15 to 12 against base run 1. The rule was ignored or made
things worse on syn-003, 011, 013 and 016, and syn-004 s0 became an empty light switch.

**Reading.** No prompt change separates from run-to-run variation. The two baseline runs differ
by one, and the variant's 8 of 9 did not replicate (4 of 9). Mistral at temperature 0 is not
deterministic here, so single-sample prompt comparisons, including the ones earlier in this file,
show direction only. The kinds line did not reliably cast the moth either: s0 stayed uncast in both
kinds runs. The deterministic species reconciliation (PR #101) catches every one of the uncast moth
directions above. No prompt changes; `SEGMENT_PROMPT_VERSION` stays 3. Groups drawn without a
reference remain an open limitation for segment.

**Cost.** 180 `segment` calls at deepinfra's $0.075/M input and $0.20/M output, estimated at about
$0.09. The OpenRouter usage counter did not move during the runs, likely because the provider key
is BYOK, so the in-script cap of $0.25 could not see this spend. The estimate comes from prices.

## Best-of ranking review (2026-10-08, $0)

**Question.** In 5 stored scenes, the shipped attempt had the judge's `subjects_unique` set to
False, and another attempt in the same scene had it True: syn-004 s1, syn-005 s2, syn-013 s2,
syn-016 s1 and syn-024 s3. Should `_rank` move `subjects_unique` up so the unflagged attempt
ships?

**Which term decided.** The shipped attempt never won on a term close to `subjects_unique`. In
three scenes it was the only one whose scene check returned no contradictions (term 2). In
syn-024 it had the fewest contradictions (term 3). In syn-016 it was the only one with
`same_character` True. Moving `subjects_unique` past `text_free` or `GATING_REASONS` changes none
of the five. Only putting it first, ahead of the scene check, would.

**The images.** The assistant compared all three attempts per scene:

| Scene | Shipped attempt | Best unflagged attempt | Better |
|---|---|---|---|
| syn-004 s1 | Tuko drawn twice | a human child added | neither |
| syn-005 s2 | Pipit among the other cranes, as the story says | a child riding Pipit | shipped |
| syn-013 s2 | Puddleback and a crowd of toads | the same crowd; the judge missed it | neither |
| syn-016 s1 | General Lint and a squad of dust bunnies | Lint and three dust bunnies | neither |
| syn-024 s3 | Wobblejaw drawn three times | one Wobblejaw, clean | unflagged |

**Reading.** One scene improves, one gets worse, and three are a wash. The judge's
`subjects_unique` has false positives (the syn-005 cranes, as seen before) and false negatives
(syn-013 a2). Where it and the scene check disagree, neither is reliably right. The `_rank` order
stays as it is.

## Defect tally: where to aim next (2026-10-08, $0)

**Question.** Which defect should the next probe target?

**Tally.** The stage audit's 221 page reviews, by pages carrying each major defect:

| Major defect | Pages | Fixable by a change? |
|---|---|---|
| `reference_inherited` | 52 | mostly no: 9 of the 17 defective references are stated counts (`count_miss`), which the count screen and ADR-056 rule out. Faces drawn on faceless characters (`added_face`, 8 references with major or minor) are the remainder. |
| `duplicate_character` | 28 | open: the edit-model probe suggests the edit model is the lever |
| `identity_drift` | 15 | not probed |
| `action_mismatch` | 13 | not probed |
| `extra_character` | 7 | partly; see below |

**Group directions.** Every page prompt says "This illustration contains exactly N character(s)"
and lists only roster characters. 17 of the 150 scenes on stored runs then direct beings that have
no roster entry ("the other cranes spin in the wind", "his six dust bunny soldiers", "a group of
frogs"), so the prompt contradicts itself. Those 17 shipped a major duplicate or extra character on
4 pages (24%), against 13 of the other 133 (10%). The clash is real but explains only 4 of the 17
duplicate pages; most duplicates happen in scenes with no group at all.

**Reading.** Duplicates are the largest major defect still open to a change, and most of them are
not caused by group directions.

## Duplicate causes: what the 13 non-group duplicates have in common (2026-10-08, $0)

**Question.** The defect tally left 13 pages with a major duplicate or extra character in scenes
that direct no group. Is there one cause a cheap change could remove?

**Method.** Each shipped page was viewed beside the reference images it was given, with its prompt.

| Pattern | Pages | Example |
|---|---|---|
| Two moments in one frame: the direction describes a move, and the character is drawn at both ends | 5 | syn-012 s0, "revealing Cog crawling out": Cog in the clock and on the table. Also syn-001 s2, syn-012 s2, syn-021 s2, syn-021 s5 |
| No visible cause | 3 | syn-021 s6, "Lala looks up at the sky": two Lalas side by side. Also syn-004 s1, syn-004 s5 |
| The setting text names an uncast roster character | 2 | syn-014 s2, s3: the hill is "small, grassy, with a goat on it", the goat is not cast, and two or three goats are drawn |
| A cast member past the two-reference cap (ADR-004) | 2 | syn-008 s2, s3: the grandfather has no reference and is drawn twice |
| A body-part count read as more characters | 1 | syn-024 s3, "all four jaws talking at once": three Wobblejaws |

One copy matched the reference's pose only on syn-001 s2, so pasting the reference is not the
pattern. Every page prompt already says "draw each character exactly once".

**Fixes considered.**

- Setting text: across all 150 scenes, 14 have a setting that names an uncast roster character.
  Only syn-014's goat pages shipped a duplicate from it (2 major, 1 minor elsewhere). Too small
  for a change.
- Two-reference cap: 10 scenes cast a character without a reference. The cap is ADR-004's, so it
  stays.
- Two moments and no visible cause (8 of 13) belong to the edit model. The edit-model probe drew
  three of these scenes with klein (syn-001 s2, syn-021 s2, syn-021 s6), and all 6 draws were
  clean.

**Reading.** No prompt or data change reaches more than 2 of the 13. The edit model is the lever
the evidence points to, and it needs an ADR and a judge recheck before production.

## Edit-model probe, extension: six more duplicate scenes (2026-10-08, about $0.36 at most)

**Question.** The first klein round covered 6 duplicate scenes. Does the drop in duplicates hold on
the 6 duplicate scenes it did not try?

**Setup.** As in the first round: `fal-ai/flux-2/klein/4b/base/edit`, each scene's stored
first-attempt prompt, the same canonical references, `NEGATIVE_PROMPT`, 1024×768, 2 draws per
scene, 12 calls, no controls. Images are in `data/judge/evaluations/klein-probe-2026-10b/`. Not
blinded: the assistant viewed every stored Qwen attempt next to both klein draws.

| Scene | Qwen attempts (stored) | klein draw 1 | klein draw 2 |
|---|---|---|---|
| syn-004 s1 | Tuko twice; then a child added, twice | clean | clean |
| syn-004 s5 | a shadow gecko; then a second kid and second Tuko, twice | clean | clean |
| syn-012 s0 | Cog in the clock and on the table (1 attempt) | one Cog, merged into the clock | a second, smaller beetle |
| syn-012 s2 | Cog in the drawer and on the shelf, 3 of 3 | clean | clean |
| syn-021 s5 | the moth twice, 3 of 3, and Lala twice once | clean | clean |
| syn-024 s3 | three Wobblejaws; then 2 clean (one with invented lettering) | two Wobblejaws | three heads |

**Result.** klein drew 9 of 12 clean against 2 or 3 clean of the 16 stored Qwen attempts. Across
both rounds, klein drew 18 of 24 clean on scenes where Qwen shipped a duplicate. It still fails
where the prompt itself invites copies: the body-count phrase in syn-024 ("all four jaws") and the
cast member without a reference in syn-008.

**Caveats.** The scenes were chosen because Qwen failed on them, so some regression to the mean
is expected. Qwen's later attempts had corrected prompts, while klein got the first prompt. There
is one rater and no blinding. klein loses the style in places: syn-024 lost the cut-paper look,
and syn-004 drifted to orange backgrounds. The first round's 4 controls kept identity on 8 of 8
draws; this round had no controls.

**Reading.** The duplicate drop held on new scenes. The edit model is the strongest lever found
for the largest fixable defect. Before production, it needs an ADR, a judge recheck on klein's
image distribution (C3-10), and a style-fidelity check on a random sample, not on failure-picked
scenes.

**Cost.** 12 calls; at most about $0.36 by the first round's upper bound. Total spend across the
probes in this file is at most about $1.91 of the $2 cap.

## Single-moment line on Qwen (2026-10-08, about $0.30 at most)

**Question.** In 5 of the 13 duplicate pages, the direction describes a move ("revealing Cog
crawling out", "places Cog in the drawer"), and Qwen drew the character at both ends. Does a prompt
line asking for one moment stop that on the production editor?

**Setup.** `fal-ai/qwen-image-edit-2511` through `providers.edit_image`, the production path. Each
scene's stored first-attempt prompt, with one line added under the character-count line: "Show one
single moment: each character appears in one place only, never at both the start and the end of an
action." The same references, 2 draws per scene, 10 calls: syn-001 s2, syn-012 s0, syn-012 s2,
syn-021 s2, syn-021 s5. Images are in `data/judge/evaluations/moment-test-2026-10/`. Not blinded.

| Scene | Stored Qwen attempts | With the line | klein, earlier probes, without the line |
|---|---|---|---|
| syn-001 s2 | Quill twice, 3 of 3 | Quill twice; clean | clean, clean |
| syn-012 s0 | Cog twice (1 attempt) | Cog in the clock and on the table, twice | 1 of 2 clean |
| syn-012 s2 | Cog twice, 3 of 3 | Cog in the drawer and a beetle-costumed figure, twice | clean, clean |
| syn-021 s2 | the moth twice, 3 of 3 | the moth in or on the jar and again outside, twice | clean, clean |
| syn-021 s5 | the moth twice, 3 of 3; Lala twice once | Lala twice and the moth twice, twice | clean, clean |

**Result.** 1 of 10 draws with the line was clean, against 0 of 13 stored Qwen attempts. klein drew
9 of 10 clean on the same five scenes from the same prompt without the line.

**Reading.** The line does not stop Qwen drawing a move at both ends, so it is not adopted. Nothing
in the prompt changed and klein did not duplicate, while Qwen ignored a direct instruction. Of the
explanations tested here, that leaves the editor. This is the strongest evidence in this file that
these duplicates are a Qwen behaviour and not a prompt defect, though n is 5 scenes, one rater, and
the scenes were picked because they had failed.

**Cost.** 10 calls at $0.03 per megapixel of output, about $0.024 each, or $0.03 if rounded up.
Whether input references are billed is unstated, so this is at most about $0.30 plus any input
charge.

## Blinded klein screen: random scenes (2026-10-08) — plan, written before any paid call

**Question.** On random scenes, not ones picked for failing, does klein draw fewer duplicate or
extra characters than Qwen without losing identity or style? Exploratory: ADR-062 runs its gates
after Objective 4, and a pass here counts as its first gate only through a follow-up ADR.

**Sample.** Synthetic scenes from the stored runs, ranked by SHA-256 of `klein-screen|<story>|<scene>`.
The lowest 15 with one referenced cast member and the lowest 15 with two. Excluded are the 21 scenes
already viewed with their alternatives in this file: syn-001 s2, 002 s2, 004 s1, 004 s5, 005 s2,
008 s2, 008 s3, 012 s0, 012 s2, 013 s2, 014 s2, 014 s3, 016 s1, 018 s0, 019 s1, 021 s2, 021 s5,
021 s6, 022 s3, 024 s3, 025 s1.

**Arms.** Qwen: each scene's stored first attempt (`fal-ai/qwen-image-edit-2511`), no new calls.
klein: one new draw from `fal-ai/flux-2/klein/4b/base/edit` with the same first-attempt prompt,
references, `NEGATIVE_PROMPT` and size. Hard cap 30 calls, about $0.62.

**Blinding.** Each scene's two images are shown as A and B, the side set by a hash, beside the
references and the direction. The assistant saves every score before opening the key. klein's style
may be recognisable, so the blinding is partial.

**Scored per image.** Major means a reader would notice it on the page.

- **Duplicate or extra (major):** a cast character drawn more than once, or a figure the direction
  does not ask for that reads as a character. Figures the direction asks for ("the other cranes")
  are not defects.
- **Identity (major):** a cast character not recognisable from its reference: wrong species, main
  colour, or a defining feature.
- **Style (major):** clearly a different art style from the references, such as a cut-paper story
  drawn as a smooth digital render.
- **Lettering:** any invented text.
- **Action:** the direction's main action not shown, or done by the wrong character.

**Pass rule, fixed now.** klein passes if both hold:

1. klein has fewer duplicate-or-extra pages than Qwen.
2. klein's identity-or-style pages exceed Qwen's by at most 3, which is 10% of 30.

Lettering and action are reported but do not decide.

## Blinded klein screen: result (2026-10-08, about $0.62 at most)

**Run.** 30 klein calls as planned, none failed, `has_nsfw_concepts` false on all 30. Images and
`log.json` are in `data/judge/evaluations/klein-screen-2026-10/`. All 60 images were scored and the
scores saved (`scores-blind.json` there) before the key was opened.

| Per 30 pages | Qwen (stored first attempt) | klein (one new draw) |
|---|---|---|
| Duplicate or extra (major) | 4 | 4 |
| Identity (major) | 3 | 10 |
| Style (major) | 0 | 0 |
| Lettering | 2 | 0 |
| Action | 2 | 8 |
| No defect of any kind | 20 | 13 |

Duplicates fell the same way in both arms: 1 of 15 one-reference scenes and 3 of 15 two-reference
scenes. The arms failed on different scenes and shared only one: syn-008 s4, where the grandfather
has no reference. Qwen duplicated in syn-008 s4, syn-015 s3, syn-029 s1 and syn-005 s0. klein
duplicated in syn-008 s4, syn-016 s3, syn-021 s0 and syn-007 s4.

**klein's identity losses:**

- Skin drawn much darker than the reference: syn-027 s3 and s5, the same character.
- Hair changed: syn-028 s5 and syn-005 s0.
- Colours or body shape changed: syn-026 s0 (shirt and hair), and Ngiwi in syn-009 s1 and s2.
- Anatomy invented or a character re-rendered: syn-016 s3 gave a limbless blob limbs and boots;
  syn-007 s4 drew a pixel-art character smooth; syn-003 s2 turned a cute gargoyle into a realistic,
  menacing one.

Qwen's three were syn-012 s3 (a beetle given shoes), syn-016 s3, and syn-005 s1, where an origami
crane was drawn as a real bird.

**Pass rule.** Rule 1 fails: klein's duplicate count is equal to Qwen's, not lower. Rule 2 fails:
klein's identity-or-style count exceeds Qwen's by 7, beyond the margin of 3. klein does not pass.

**Reading.** On random scenes, klein's duplicate advantage disappears. Qwen's rate here is 4 of 30
(13%), the stage audit's rate, and klein's is the same. The earlier probes showed klein clean on
scenes where Qwen fails again and again. This screen shows klein has its own failing scenes. Picking
scenes for Qwen's failures inflated the gap, the regression to the mean the probe caveats warned
of. It also qualifies the single-moment test's reading. Those duplicates are a Qwen behaviour on
those scenes. Duplicates in general are not Qwen-specific: both editors produce them at about the
same rate, in different places. klein also kept identity worse, the defect the reference pipeline
exists to protect. Qwen stays the scene editor on the evidence, not only on ADR-062's timing.

**Caveats.**

- One rater. Blinding was partial: klein's look is sometimes recognisable.
- The Qwen arm is a stored draw, the one production actually made. The klein arm is a single draw.
- Seven of klein's ten identity losses are clear-cut: skin, hair, colour. A stricter or looser
  threshold moves the count by a page or two, not by seven.
- syn-027 s3 and s5 are the same character, so those two losses are correlated.
- Exploratory under ADR-062, which places the gates after Objective 4. This result does not amend
  ADR-062 by itself. A follow-up ADR records it.

**Cost.** 30 calls: 15 with one reference at about $0.016 and 15 with two at about $0.025, about
$0.62 at most. This screen and the single-moment test were authorised separately from the $2 cap.

## One-moment directions on Qwen (2026-10-08) — plan, written before any paid call

**Question.** The single-moment line failed, but it left the move in the direction ("revealing Cog
crawling out"). If the direction itself describes one frozen instant, does Qwen stop drawing the
character at both ends? Does it draw the action the audit found missing? This tests the mechanism
with hand-written rewrites. Whether `segment` can write such directions is a later question.

**Rewrite rules, applied to the "Visual direction:" line only.** Everything else in the stored
first-attempt prompt stays byte-identical: references, count line, setting and style.

1. One instant: the end state of any move.
2. Each character in exactly one stated place.
3. Name only what is visible. Nothing pretended, absent, or about to happen.
4. Keep the characters, expressions, viewpoint and framing.

**Duplicate scenes, 2 draws each.** These are the five move scenes from the duplicate-cause review.
Stored Qwen attempts: 0 of 13 clean. With the single-moment line: 1 of 10 clean.

| Scene | Rewritten direction |
|---|---|
| syn-001 s2 | Quill stands on top of the fence with one paw raised in the air. Quill looks focused; Bok-Bok stands on the ground below, watching. |
| syn-012 s0 | Ate Rina holds the open broken clock; Cog's head and front legs poke out of the clock's open case. Ate Rina looks surprised. |
| syn-012 s2 | Ate Rina bends over the open drawer; Cog sits inside the drawer among tiny screwdrivers. Ate Rina gentle, Cog calm. |
| syn-021 s2 | Lala holds the jar in both hands; Ashwing sits inside the jar. Lala's face curious and gentle. |
| syn-021 s5 | Lala holds the open jar up toward the sky; Ashwing flies alone just above the jar's mouth. Lala's face hopeful. |

**Action scenes, 1 draw each.** These are audit pages whose action was missing or wrong.

| Scene | Audit defect | Rewritten direction |
|---|---|---|
| syn-001 s0 | Bok-Bok upright and clean, no fall | Bok-Bok sits in the mud at the foot of the barn wall, splattered with mud, looking embarrassed. Quill watches with all three eyes. |
| syn-012 s3 | Cog strides instead of stopping to point | Cog stands still in the middle of the floor with one front leg raised, pointing. Cog focused, Ate Rina watching. |
| syn-019 s1 | real fire drawn for "pretending to breathe fire" | Snorkel puffs out his chest, cheeks round and full of air, while the other toys watch politely. Snorkel's eyes are wide with effort, tongue out, and the other toys smile faintly. |
| syn-016 s3 | the vacuum inside the crack with them | General Lint and the last two soldiers squeeze into a crack in the wall; the vacuum stands outside the wall, behind them. Relieved, determined. |

Each keeps its original "Viewpoint: … Framing: …" text. Hard cap: 14 calls through
`providers.edit_image`, the production path, about $0.34 to $0.42.

**Pass rule, fixed now.**

- **Duplicates (decides):** at least 6 of the 10 duplicate-scene draws have no duplicate or extra
  character.
- **Action (reported):** for how many of the 4 action draws the rewritten instant is visible.
- **Guard (reported):** any identity loss or new defect the rewrite introduces.

**Limits.** Not blinded: there is one new arm, scored against stored attempts already seen. One
rater. These scenes were picked because they had failed. A pass justifies a `segment` rule
measured by rate on random scenes (ADR-055), not a production change by itself.

## One-moment directions on Qwen: result (2026-10-08, about $0.34 to $0.42)

**Run.** 14 calls as planned, none failed. Images and `log.json` are in
`data/judge/evaluations/oneshot-test-2026-10/`. Each draw was scored against its references and its
rewritten direction.

| Scene | Draw 1 | Draw 2 |
|---|---|---|
| syn-001 s2 | clean | clean |
| syn-012 s0 | clean | Cog twice (a second small beetle face on the clock); Cog drawn more cartoonish |
| syn-012 s2 | Ate Rina twice, and an extra creature face | an extra round sun-faced creature behind Cog |
| syn-021 s2 | Ashwing twice: in the jar and in the background | same |
| syn-021 s5 | Lala twice | Ashwing twice, and an extra origami-like bird |

| Action scene | Rewritten instant visible? |
|---|---|
| syn-001 s0 | no. Quill sits in the mud at the barn wall; Bok-Bok stands clean beside it. The roles are swapped |
| syn-012 s3 | partly. Cog has one leg raised, but Ate Rina does the pointing |
| syn-019 s1 | yes. Puffed cheeks and a puff of air, tongue out, toys watching; no fire |
| syn-016 s3 | yes. Lint pressed into the crack, the vacuum outside behind them |

**Pass rule.** 3 of 10 duplicate-scene draws are clean, against the 6 required. The rewrite fails.

**Action.** 2 of 4 show the instant, 1 partly, 1 with the roles swapped. Where the old direction
named something absent or pretended (fire, the vacuum's position), naming only the visible state
worked. Where two characters share the scene, the action can still go to the wrong one.

**Guard.**

- Cog lost its beetle shape twice: drawn cartoonish (syn-012 s0 draw 2), and standing upright on two
  long black legs (syn-012 s3).
- syn-016 s3 drew the two soldiers as human boys. They are named in the direction but not cast, so
  the prompt says nothing about what they look like. That is the uncast-character gap, not the
  rewrite.
- Quill was drawn with two eyes despite "all three eyes", as in the count screen.

**Reading.** Directions with one instant and one place per character did not stop the duplicates.
Moves are gone from these directions, yet 7 of 10 draws still copy a character or add one. The
both-ends-of-a-move explanation does not cover these scenes. Qwen copies characters on them however
the direction is phrased. 3 of 10 against the line's 1 of 10 is within the noise of two draws per
scene. Missing actions respond better: stating the visible end state fixed both pages whose old
direction named something absent. Role swaps did not respond.

**Caveats.** One rater, not blinded, failure-picked scenes, two draws per duplicate scene and one per
action scene. The action result is 4 pages and only suggests a `segment` rule; it does not measure
one.
