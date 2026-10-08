# Pipeline stage audit — 2026-10

Read-only, synthetic only, $0. The question: **for each defect in what the pipeline ships, which
stage caused it, and in which story scenario?** The answer ranks candidate pipeline routes by
frequency × fixability before any route, ADR or model trial is chosen. It follows the
[C3 gate audit](pipeline-gate-audit-2026-09.md) and does not replace C3-04's 28-image sample.

## Frame

All 30 `syn-*` bundles under `data/judge/corpus/runs/`. No donated bundle, image or label is read.

| Item | Count | Why |
|---|---:|---|
| Final canonical references | 55 | Every page inherits them |
| Selected final pages (`scene.final_image_ref`) | 150 | What a reader sees |
| First attempts that were not selected | 71 | The judge bought a redraw; tests false rejections |

This is a census of shipped output plus the first rejected draw per redrawn scene, not a sample.
Stored outcomes come from reference-judge prompt v7, scene-judge prompt v4, `fal-ai/qwen-image`,
`fal-ai/qwen-image-edit-2511` and `google/gemma-3-27b-it`, across the code commits listed in the
gate audit.

## Blinding

Packets and images are built by a throwaway script into the gitignored
`data/judge/evaluations/stage-audit-2026-10/`. Images are copied to `<item_id>.png`, where
`item_id` is the first 12 hex digits of SHA-256 `stage-audit-2026-10|<kind>|<storage path>`.
Within a scene, images are listed in item-id order, so reviewers cannot tell which image shipped
or whether a redraw happened. Packets contain no verdict, reason, contradiction, `passed` flag,
prompt or attempt number. `key.json` maps item ids back and is not given to reviewers. Reviewers
must not open `data/judge/corpus/runs/`.

## Reviewers

Six AI image reviewers, five stories each in story-id order, and two text-only extraction
reviewers, fifteen stories each. All AI output is **provisional** until the owner checks it.
Reviewer assignment is by story order, so a reviewer effect is confounded with stories.

## Image rubric (fixed before review)

Per item: `scenario_tags`, `defects`, `verdict` (`acceptable` = no major defect, `defect`,
`uncertain`) and `notes`.

**Scenario tags** (all that apply): `multi_ref` (2+ characters with references on the page),
`non_human`, `stated_part_count` (description states a count of a body part), `unusual_body`
(faceless, object-bodied, or a body plan unlike the species), `group_character` (one character
stands for several beings), `text_bearing_object` (the story puts a book, sign, clock or similar in
view), `background_character` (the excerpt names a person or creature not in the cast list),
`appearance_change` (the story changes a character's clothing, form or condition), `zero_ref`,
`object_state`.

**Defect types**: `identity_drift` (not recognisably the reference), `reference_inherited` (the page
copies a defect the reference already has), `missing_character`, `extra_character`,
`duplicate_character`, `action_mismatch`, `viewpoint_mismatch`, `object_wrong`, `setting_wrong`,
`invented_lettering`, `anatomy`, `count_miss`, `added_face`, `group_as_one`, `style_escape`,
`description_unfaithful` (reference matches its description but the description misreads the
story), `other`.

**Severity**: `major` = a reader would notice the page contradicts the story, or the character is
not recognisably the same; `minor` = visible on close inspection, the story still reads correctly.
A viewpoint or expression difference is `minor` unless the excerpt depends on it.

**Origin** per defect: `description`, `reference`, `generator`, `unclear`.

**Lettering count rule**: `invented_lettering` counts captions, labels or legible words the story
did not ask for. Illegible marks on drawn papers are `minor`. Glyphs that belong (clock numerals,
a book's title the story names) are not defects.

## Extraction rubric (fixed before review)

Text only. Per story: roster errors (missing, extra, merged or split characters); per character,
description attributes the story does not state or clearly imply (`invented`), stated visual
attributes the description dropped (`missed`), and contradictions; per scene, cast errors and a
visual direction that contradicts its excerpt. Each finding is `major` if it would put a wrong
thing on the page, else `minor`.

## Analysis plan (fixed before review)

Joining with `key.json` and the stored verdicts afterwards:

1. Defect counts by type, origin and severity on the 150 shipped pages and 55 references.
2. Scenario × defect table: the share of pages with a major defect per scenario tag.
3. Stored gate vs. review: false accepts (stored pass, major defect) and false rejections (stored
   fail, `acceptable`), with redraws on the 71 rejected first attempts as wasted or justified.
4. Extraction findings that reach an image as `description_unfaithful` or `origin: description`.

The owner confirms a fixed subset before any count is treated as more than provisional: every
`uncertain` item and the 30 pages and 10 references with the lowest SHA-256 of
`stage-audit-2026-10|confirm|<item_id>`. No label, freeze, prompt, gate or model changes from this
audit alone.

## Provisional results — 2026-10-08

AI review only; the owner confirmation subset (`owner_confirm.json`: 30 pages, 10 references, 2
uncertain) is not yet checked. All 276 items were reviewed; none missing. Reviewer effects are
confounded with stories.

**Shipped pages.** 77 of 150 have at least one major defect, 71 are acceptable, 2 uncertain. Pages
with no `non_human` tag: 11 of 33 defective, against 66 of 117 for non-human pages. The synthetic
corpus is 83% invented non-human characters while donated stories are mostly human, so the overall
rate likely overstates what classroom stories meet.

**Where the 77 come from** (a page can have several origins): a reference-origin major on 38 (26 only
that), a generator-origin major on 43 (34 only that), a description-origin major on 7. Most common
majors: `reference_inherited` 34, `duplicate_character` 15, `action_mismatch` 9, `identity_drift` 8,
`extra_character` 5. Duplicate or extra characters appear on 17 pages.

**References.** 17 of 55 defective, chiefly a missed stated count (8 major: six legs drawn as four,
seven stripes as five, four wings as two). The stored reference gate failed 15 of those 17 and also
15 of the 38 acceptable references. It detects bad references, but `char_bible` ships the best
failing draw, so every detected defect still reached the pages.

**Page gate.** Of the 77 defective shipped pages, 29 passed the stored gate; of the 71 acceptable,
28 failed it. 23 of the 71 rejected first draws were acceptable, so those paid redraws were likely
unnecessary. The identity judge compares against the reference, so a defect inherited from the
reference passes it by construction.

**Duplicates.** Across all 216 page images, the review marked 33 with a major duplicate or extra
character. The stored `subjects_unique` was False on 16 of those and on 9 of the 183 others. It is
recorded but does not gate.

**Extraction** (text review, 30 stories): 20 major and 146 minor findings. Majors are mostly cast
errors (a character in the excerpt but not in `characters_present`) and background groups the visual
direction draws but no roster lists. One story needs a per-scene character state (syn-010's leaf
ears fall off in winter). Four stored objects carry the literal string `colours: [` in `materials`,
an extraction parse defect.

No label, freeze, prompt, gate or model changed.
