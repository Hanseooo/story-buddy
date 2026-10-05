# C3 gate audit — 2026-09-26

## Scope and method

The synthetic portion of this read-only audit used the 30 `syn-*` train/validation bundles under
`data/judge/corpus/runs/`. It read `memory.json` and `run.json`; it did not read donated
held-out bundles, their images, or their labels. All 30 runs record reference-judge prompt
version 7 and scene identity-judge prompt version 4, but span five `code_commit` values.
These are stored campaign outcomes, not a live Langfuse or current-production rate.

For each character with `canonical_ref_image`, the actual final reference gate is
`ref_verdict.contradictions == [] and ref_verdict.text_free`. The
`matches_description` field is logged, not used by `char_bible` to accept a draw.
For each scene, an attempt's `passed` field is the stored gate result. The selected
final attempt is the one whose `image_ref` equals `scene.final_image_ref`; it can be
earlier than the last attempt because the node ranks failed draws.

| Stored outcome | Count |
|---|---:|
| Synthetic stories | 30: 24 train, 6 validation |
| Characters | 64: 55 with references, 9 without references |
| Final references with a passing verdict | 25 / 55 |
| Final references with a failing verdict | 30 / 55 |
| References with no verdict | 0 / 55 |
| `matches_description: true` among referenced characters | 49 / 55 |
| `matches_description: true` but actual gate failing | 24 / 55 |
| Scenes / stored draw attempts | 150 / 335 |
| Failed scene draw attempts | 261 / 335 |
| Selected final images whose attempt failed | 76 / 150 |
| Failed draw attempts with a nonempty scene-constraint contradiction list | 202 / 261 |

All 150 scenes have a selected `final_image_ref`. Attempts are repeated draws of the same
scenes and are not independent examples. A failing verdict can still produce a book:
`char_bible` ships the best failed reference after its capped draws, and
`consistency_check` selects a best page when its retry ceiling is reached. These
counts measure the pipeline's recorded gate outcomes. They do **not** measure human
confirmed defects or false-rejection rates. The 202 scene-constraint cases overlap
identity failures, so they cannot be summed as separate causes.

The ten synthetic characters in the face-slot table of
`reference-fidelity-2026-09.md` all have **failing final reference-gate verdicts**
under the actual condition above. The eleventh case is donated and was not read here.
Their `matches_description` booleans therefore cannot be used as gate outcomes.

## Visual spot-checks, not rates

- The selected `syn-001:c0` Quill reference appears to show three orange eyes. Its
  stored verdict says the image has two eyes, records that as a contradiction, and
  simultaneously sets `matches_description: true`. This is one apparent false
  reference-gate rejection; it has not been independently adjudicated.
- The selected `syn-001:s3-3` page shows no visible lettering on inspection, while
  the scene verdict records `text_free: false` and `passed: true`. Text is no longer
  a scene-gating field. This spot-check cannot estimate a false-positive rate.

## One live Langfuse trace cross-check

A local JSON export of one 2026-09-26 Langfuse trace contains 67 observations,
including the initial graph run and its resume under one trace ID. The story reached
`compose`. It has two moderated, reference-gate-passing character references, eight
scenes, 12 scene draw attempts, and four redraws. The final image selected for each of
two scenes (`s3` and `s6`) was attempt 2 of 3 and still had `passed: false`. The other
six selected pages had `passed: true`; all eight recorded output moderation as passed.
These are gate outcomes, not human assessments of the images.

The strongest candidates for a false rejection are `s3` attempts 1 and 2 and `s6`
attempt 2: each has `same_character: true`, `anatomy_intact: true`, no scene-constraint
contradictions, and fails on `wrong_body_feature`. `s6` attempt 1 instead records
`same_character: false`; the third attempts add scene-constraint contradictions.
The Fal thumbnails show repeated compositions but are too small, and lack the
canonical references, to adjudicate any of these verdicts. Inspect the full-size
attempts beside both references before counting a false rejection.

Eight larger Fal screenshots subsequently matched the trace by local request time:
the 15:12, 15:13, and 15:14 café images are `s3` attempts 1–3; 15:16 and 15:18
are separate scenes `s4` and `s5`; 15:19 and 15:20 are `s6` attempts 1–2; 15:23
is `s7`. `s6` attempt 3 was not supplied. On the two rejected `s3` attempts, no
missing or malformed body feature is obvious at screenshot resolution. That is a
candidate false rejection, not an adjudicated one without the canonical references.
The desk images visibly contain invented wall lettering, a separate generation
artifact; `text_free: false` recorded it but did not trigger these redraws. The
three café screenshots show no obvious lettering at this resolution despite the
same `text_free: false` verdict, another item for full-size review.

The six passing page attempts also recorded `text_free: false` and a
`different_face` failure reason. Current `consistency_check.py` records and ranks
`text_free` but does not gate on it; `different_face` does not gate independently of
`same_character`. Thus these combinations are consistent with the implemented gate,
not evidence on their own that routing malfunctioned. The export has no populated
model ID, prompt name/version, or release columns for the graph observations; the
reference verdicts carry prompt version 7. A model comparison or false-rejection
rate cannot be inferred from this one unlabelled trace.

The export also contains `input.raw_text` in LangGraph state. The worker attaches the
Langfuse callback to that state and calls `set_trace_as_public()` after the graph
(`backend/worker/run_job.py`). Two `public-link` observations are present in the
export. This verifies that raw story text enters a trace the worker intentionally shares
by URL. It does not establish that this particular story contains PII or independently
test access to the public page. Verify redaction of the intended public trace view
before using it with child stories; do not publish this export or trace ID.

## What remains to verify

- Extend the one-trace recount to a bounded, permitted sample while public trace
  redaction is reviewed in parallel. Separate reference draw attempts from final
  references, and scene draw attempts from selected final pages. Record date, model,
  provider, prompt version, style, and code commit where instrumentation supplies them.
- Blindly review a preselected synthetic sample of failing and passing images against
  the source story, description, reference, and scene direction. Count true defects,
  false rejections, false accepts, and unchecked cases separately.
- Diagnose scene-constraint contradictions before changing the judge or regeneration
  policy. A failed attempt is not proof that its image is bad, and a passing attempt
  is not proof that it matches the story.

No Objective-4 label, held-out exclusion, model selection, or pipeline behavior changes
follow from this audit alone.

## C3-04 synthetic visual sample — selection locked 2026-09-30

This follow-up uses only the 30 `syn-*` bundles. No donated bundle or held-out
image is part of the sample. It is a purposive diagnostic sample, not an estimate
of a population error rate. Reviewers must record their image-based assessment
before seeing the stored gate status, reasons, or verdict text. AI-assisted image
review is provisional until a human independently checks the cases; it is not a
new Objective-4 annotation or adjudication round.

The reference frame is all 55 final canonical references. The scene frame is the
185 draw attempts from scenes with exactly one character that has a canonical
reference. Earlier reference draws are not retained in the corpus bundle;
multi-character and unreferenced scene attempts are outside this sample. Strata
are style (`cel`, `cut_paper`, `gouache`), human (`description.species == "human"`)
versus non-human, and stored gate outcome. A reference passes when its final
verdict has no contradictions and `text_free` is true. Scene outcomes are
`pass_selected`, `fail_selected`, and `fail_unselected`, where selection means
`attempt.image_ref == scene.final_image_ref`. There are no pass-unselected scene
attempts in this eligible frame. The cel/human/failing-reference and
cel/human/fail-selected-scene strata are empty.

Select one image per nonempty stratum by ascending SHA-256 of
`C3-04|ref|<canonical_ref_image>` or `C3-04|scene|<attempt.image_ref>`, with
storage paths taken verbatim from `memory.json`. The following IDs were fixed
before opening any selected image. The stored outcomes are intentionally omitted
from this review list.

| Kind | Story | Character | Image |
|---|---|---|---|
| ref | syn-004 | c0 | ref-c0-1.png |
| ref | syn-010 | c1 | ref-c1-1.png |
| ref | syn-004 | c1 | ref-c1-1.png |
| ref | syn-009 | c1 | ref-c1-1.png |
| ref | syn-015 | c1 | ref-c1-1.png |
| ref | syn-006 | c1 | ref-c1-1.png |
| ref | syn-027 | c0 | ref-c0-1.png |
| ref | syn-023 | c0 | ref-c0-1.png |
| ref | syn-020 | c0 | ref-c0-1.png |
| ref | syn-026 | c0 | ref-c0-1.png |
| ref | syn-005 | c1 | ref-c1-1.png |
| scene | syn-013 | c0 | s2-1.png |
| scene | syn-004 | c0 | s1-3.png |
| scene | syn-019 | c0 | s0-2.png |
| scene | syn-004 | c1 | s4-1.png |
| scene | syn-019 | c1 | s2-1.png |
| scene | syn-015 | c0 | s0-3.png |
| scene | syn-024 | c0 | s3-3.png |
| scene | syn-009 | c0 | s1-1.png |
| scene | syn-006 | c1 | s2-2.png |
| scene | syn-021 | c0 | s1-3.png |
| scene | syn-027 | c0 | s1-1.png |
| scene | syn-023 | c0 | s0-1.png |
| scene | syn-014 | c0 | s1-1.png |
| scene | syn-020 | c0 | s2-1.png |
| scene | syn-002 | c0 | s3-1.png |
| scene | syn-026 | c0 | s3-2.png |
| scene | syn-029 | c0 | s0-1.png |

Each image name is resolved through that story's `memory.json` to its exact
storage path and then through `finetune.manifest.local_image_path` to a local
file. All 28 selected files and their scene references were present before
review. Inspect references against their descriptions and scene attempts against
their canonical references, story excerpt, and visual direction. Record visible
defects, uncertain cases, and the underlying component separately before
comparing with stored verdicts. Run metadata supplies model IDs, prompt versions,
style, and code commit; it does not prove the historical provider endpoint or
per-call model revision.

### Provisional image review and stored-gate comparison

An AI reviewer recorded the visible assessment before reading each stored verdict.
The study owner has not independently checked these 28 assessments. `Defect` below
means a visible mismatch with the description or scene direction, not necessarily
a different character from the canonical reference. `Uncertain` is not resolved
by the stored verdict. None of these observations changes an Objective-4 label.

| Reference | Visual assessment | Stored reference gate | Provisional reading |
|---|---|---|---|
| syn-004:c0 | Defect: about five blue stripes, not seven | Fail | Agrees |
| syn-010:c1 | Acceptable deer | Pass | Agrees |
| syn-004:c1 | Acceptable child | Pass | Agrees |
| syn-009:c1 | Plump grey cat with apparently short legs; white markings | Fail | Possible false rejection: neither disputed detail clearly contradicts the description |
| syn-015:c1 | Uncertain: one visible simple eye; reference isolates one shrimp | Pass | Eye and grouping requirements need human interpretation |
| syn-006:c1 | Defect: one person represents a family | Fail | Agrees on count problem |
| syn-027:c0 | Acceptable child | Pass | Agrees |
| syn-023:c0 | Defect: fewer than ten clear squid arms; no evident longer pair | Fail | Agrees; overlaps make exact count difficult |
| syn-020:c0 | Defect: cracked cup sits atop an ordinary shell instead of serving as the shell | Pass | Strong false-acceptance candidate; full-size image independently checked by the audit author |
| syn-026:c0 | Uncertain: hair and skin hues under warm gouache lighting | Fail | Possible false rejection; stored colour objections are subjective |
| syn-005:c1 | Uncertain age/gender in sparsely specified human reference | Pass | No clear contradiction established |

| Scene attempt | Visual assessment before gate reveal | Stored outcome | Provisional reading |
|---|---|---|---|
| syn-013:c0 s2-1 | More than nine back spots; body still resembles reference | Fail, selected | Body-detail defect; stored `same_character=false` conflicts with frozen Same label and needs human review |
| syn-004:c0 s1-3 | Extra child; too few stripes inherited from reference | Fail, unselected | Composition failure supported; stored face explanation weak |
| syn-019:c0 s0-2 | One button visible on sock dragon and reference | Pass, selected | Uncertain inherited reference-detail miss |
| syn-004:c1 s4-1 | Extra child; switch action absent | Fail, unselected | Composition failure supported; stored character-absence explanation doubtful |
| syn-019:c1 s2-1 | Crying baby matches reference | Pass, selected | Pass supported; `different_face` reason is discordant |
| syn-015:c0 s0-3 | Head lights too bright; extra lamp and style drift | Fail, selected | Failure supported; lamp also appears in reference |
| syn-024:c0 s3-3 | Added eyes/brows and one mouth; reference already lacks four jaws | Fail, unselected | Scene and inherited-reference defects; four arms appear visible despite stored two-arm claim |
| syn-009:c0 s1-1 | Side view beside fern, not overhead beneath it | Pass, selected | Composition false-acceptance candidate; frozen Same identity label is compatible with this finding |
| syn-006:c1 s2-2 | One person for family; garbled package lettering | Fail, selected | Failure supported; count defect inherited from reference and lettering unreported |
| syn-021:c0 s1-3 | Moth lacks stated grey wings and six eyespots | Fail, unselected | Failure supported; these missing details are not in stored reasons |
| syn-027:c0 s1-1 | Running child matches reference and direction | Pass, selected | Pass supported |
| syn-023:c0 s0-1 | Squid looks octopus-like with too few arms | Fail, selected | Defect inherited from reference; stored style reason misses it |
| syn-014:c0 s1-1 | Face and limbs instead of faceless cloud with raindrop feet | Fail, unselected | Defect inherited from reference; goat appears requested in setting |
| syn-020:c0 s2-1 | Cup remains atop shell; dried holes still have water | Pass, selected | Reference defect plus composition false-acceptance candidate; frozen Same identity label does not settle either |
| syn-002:c0 s3-1 | Book exchange with librarian matches direction | Fail, selected | Possible false rejection: prompt's one-character rule conflicts with named librarian; style remains debatable |
| syn-026:c0 s3-2 | Lighter hair/skin than reference; rear three-quarter view | Fail, unselected | Failure supported, subject to colour interpretation |
| syn-029:c0 s0-1 | Child and rice-sack action match reference/direction | Pass, selected | Pass supported; stored clothing/face reasons are discordant |

The 17 selected scene pairs were also matched against the registered **train and
validation manifests only**. All had an existing pipeline-pair label. Those
labels answer *same character relative to the reference*, not whether the scene
follows the story direction or whether the reference follows its description.
For example, `syn-009:c0 s1-1` and `syn-020:c0 s2-1` are frozen Same pairs; that
does not validate the overhead view, fern placement, teacup shell, or dry holes.
Conversely, `syn-013:c0 s2-1` is frozen Same while the stored identity verdict
is Different. These are specific review cases, not an accuracy estimate.

### Label-rule discrepancy found during the synthetic cross-check

The frozen labelling rulebook Step 3 says clothing or style alone means Same.
Seven final **synthetic train/validation** pipeline pairs in the registered
manifests are Different with no recorded reason other than `wrong_clothing` or
`wrong_style`: train `7e28e10547bf8327`, `a64c9c7feaa819fe`,
`917cbfadc3f21010`, `d0dfb122499cd755`, `10438644caae76c6`,
`0d27c8dab8db9c1e`; validation `7aef98a200733f41`. Two occur in this
sample (`syn-014:c0 s1-1`, `syn-015:c0 s0-3`). The recorded reasons cannot
justify Different under Step 3; the image might support another reason that
was not recorded. The earlier ten-pair label audit targeted *agreed* Different
pairs, not all final labels. This discrepancy needs a protocol-aware human
review before these seven are treated as reliable screening examples. No
annotation, registered freeze, exploratory freeze, or exclusion list was
changed by this audit.

All 28 selected cases record `fal-ai/qwen-image` and
`fal-ai/qwen-image-edit-2511`, `google/gemma-3-27b-it`, reference-judge prompt
version 7 and scene-judge prompt version 4 in `run.json`. The sample spans
code commits `1ddf1ceacabcae5b3167ecb54e18396f0492af78`,
`c1f0557bd8c3f22478e8689c9c9e2e71c1ec8474`,
`56d7f4c2b9b63e4a7bde4edae77496e99ad05680`, and
`f2048a463a8fd963d725878da8a861980e72ab58`. Historical per-call
provider and model revisions are not recorded. The sample cannot establish
that a newer VLM or image model would be better. Human confirmation of the
reference and scene-constraint assessments is still needed before using this
as C3-09's human-labelled audit sample.

## C3-09 exploratory provider pilot — 2026-09-30

The owner approved a USD 2 capped **exploratory** two-image identity screen before
training. The OpenRouter key reported a USD 2 total limit and USD 2 remaining before
the first call. The fixed [selection](../../data/judge/intake/vlm_pilot_selection_2026-09-30.json)
contains 24 synthetic **training** pipeline pairs from registered dataset SHA-256
`9faa7b3217466c8b8aec074e6e3f36df4cedb1a0a489f196c2da402cae2a1d0b`
and train-manifest SHA-256
`8cd2f64f82faaf73ec0324aa1d97e8c53e66d1d4b117aa2b43275db4079cd20c`.
It has 12 Same / 12 Different, 12 human / 12 non-human, and 12 stored-gate pass /
12 fail cases. Its stated deterministic strata exclude the 16 exploratory-training
omissions, the ten label-audit pairs, and the seven final Different pairs whose
only recorded reasons conflict with the frozen clothing/style rule. All 24 IDs,
48 assets, and exclusions were checked against the train manifest. No donated,
validation, or held-out test image was used.

Both models received the same two images and production scene-identity prompt
version 4, with `SceneVerdict` strict `json_schema` and `require_parameters: true`.
The one-pair schema probe parsed for both before the full screen. The model IDs were
`google/gemma-3-27b-it` and `qwen/qwen3.5-9b`. OpenRouter metadata receipts identify
Parasail for all 23 parsed Gemma calls; Qwen's 18 parsed calls used Venice 16 times
and Parasail twice. Failed calls have no generation receipt, so their upstream
provider is unknown. The working tree was dirty at Git HEAD
`5ecae9b90e1e4353b70a6a78c476f0d530ebb121`; model weight revisions were not
reported by the provider.

| Model | Parsed / 24 | Timeout | TP / FN on Different | TN / FP on Same | Median parsed latency |
|---|---:|---:|---:|---:|---:|
| Prompted Gemma-3-27B | 23 | 1 | 2 / 10 | 11 / 0 | 7.5 s |
| Qwen3.5-9B | 18 | 6 | 2 / 8 | 8 / 0 | 20.1 s |

On the **17 pairs both parsed**, each matched the stored identity label on 9.
They disagreed on two pairs, winning one each. The different denominators in the
table must not be used as a direct accuracy ranking; timeouts are availability
failures, not wrong identity verdicts. In the planned slices, parsed/correct were
Gemma human 11/7, non-human 12/6, stored-gate pass 12/7, fail 11/6; Qwen human
10/7, non-human 8/3, pass 7/4, fail 11/6. Both produced zero false Different
verdicts on the Same-labelled pairs they answered, but missed most answered
Different-labelled pairs.

The 41 successful-call [receipts](../../data/judge/evaluations/vlm-pilot-2026-09-30/receipts.jsonl)
sum to USD 0.014013. The dedicated key's usage after the run was USD 0.03951479,
with USD 1.96048521 remaining; the difference cannot be assigned to individual
timed-out requests from the available receipts. The [prediction rows](../../data/judge/evaluations/vlm-pilot-2026-09-30/predictions.jsonl)
are SHA-256 `3ffeefce51da4925dbdd750036704a49e52f1d6cee6d6b6df7d1e2e57a521199`;
the receipt file is SHA-256
`93ddecf19f9260e3fdac5effa2112c19bb64cf54d4e8288109aac1a91135b163`.

This purposively balanced screen is not a population estimate or the full C3-09
human-checked audit. The stored identity labels were not newly checked by the
owner; the screen does not measure reference-to-description or scene-to-story
judging. Qwen's mixed provider routing also prevents a clean architecture-only
comparison. These results give no evidence to replace the prompted Gemma gate or
change the registered Qwen2.5-VL-7B fine-tune. The registered freeze and labels
remain untouched.

Subsequently on 2026-09-30, the owner accepted [ADR-061](../product/adr/ADR-061-qwen3-5-9b-as-the-objective-4-judge-base.md)
and a dated Objective 4 amendment choosing Qwen3.5-9B as the fine-tune base. That later
decision is postregistration and does not turn this pilot into evidence of superiority.

## Selected-page lettering screen — 2026-10-06

Read-only, synthetic only. The frame is the 150 selected final pages of the 30
`syn-*` bundles (`attempt.image_ref == scene.final_image_ref`). Their stored scene
verdicts record `text_free=False` on 108, `True` on 37 and no verdict on 5. Since
2026-09-02 `text_free` records and ranks but does not gate scene pages
(`consistency_check.py`); it still gates references (`char_bible.py`). The comment at
`config.py:136` still describes it as gating and is stale.

Sample: the 8 flagged and 8 unflagged pages with the lowest SHA-256 of
`lettering|<final_image_ref>`, viewed in key order with the stored flag hidden. An AI
reviewer recorded each image first; the owner has not checked these.

| Stored flag | No lettering | Text-like marks, illegible | Glyphs that belong (clock numerals) | Garbled caption text |
|---|---:|---:|---:|---:|
| `text_free=False` (8) | 4 (syn-028 s1, syn-009 s3, syn-007 s4, syn-029 s0) | 2 (syn-027 s4 newspaper; syn-027 s2 radio and wall papers) | 1 (syn-012 s0) | 1 (syn-024 s0, corner caption) |
| `text_free=True` (8) | 8 | 0 | 0 | 0 |

In this sample the flag missed no lettering, and half its positives had none. The one
clear defect is invented caption text on syn-024 s0; illegible marks on drawn
newspapers and papers are a softer case. Eight pages per arm cannot estimate a rate:
it does not establish how many of the 108 flagged pages carry real lettering, and the
earlier syn-006 package lettering shows the flag can also miss. A count rule (caption
vs. object marks vs. legitimate glyphs) has to be fixed before any larger screen.

Incidental: syn-007 s4-3 is pixel art under the `cel` preset, a style escape relevant
to #98.

No label, freeze, prompt, gate or model changed.
