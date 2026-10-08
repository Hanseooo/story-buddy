# Model probes — 2026-10

Small paid screens that follow the [stage audit](pipeline-stage-audit-2026-10.md). The owner capped
total spend at USD 2. Synthetic stories only. Images are under the gitignored
`data/judge/evaluations/`. These are screens, not evaluations: one rater (the assistant, looking at
each image), tiny n. The edit probe was not blinded between arms; the count screen was. No
production setting changed.

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
