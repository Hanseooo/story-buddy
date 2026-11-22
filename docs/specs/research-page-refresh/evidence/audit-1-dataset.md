# Audit 1: `/research/dataset` page (staleness, accuracy, clarity, paper sync)

Read-only audit, 2026-11-21. Nothing in the repo was edited.

**Bottom line.** Every count on the page matches the registered freeze. I recounted all of them from
`data/judge/freezes/obj4-v1/` (the freeze is on disk). The page's data test also ran against the
freeze and passed (12/12). Nothing on the page is stale. The problems are elsewhere:

- **Three accuracy gaps.**
  - Nine final labels are Different with only Wrong Clothing or Wrong Style ticked, two of them in
    test. The rulebook calls that combination "always a mistake", and the page says it is Same.
  - The human/non-human table counts 7 animal and machine training characters as human.
  - "No test label changed" is true only of the AI-assisted audit.
- **Clarity.** The page never says what a "page" is. 422 of the 795 rated pairs use a second or
  later drawing attempt, not the final page. It also leaves out how the splits were made and the
  end-to-end process.
- **The paper.** Its annotation-criteria table lists clothing and style as identity criteria. That
  contradicts the rulebook. It also leaves out the AI-assisted relabel deviation.

Target files: `frontend/app/(research)/research/(reference)/dataset/page.tsx`, `data.ts`, `data.test.ts`.
Freeze used for counting: `data/judge/freezes/obj4-v1/` (manifest SHA `9faa7b32…`, matches runbook).

---

## (a) Findings

Labels: **M** = measured (I counted it), **I** = inferred, **X** = inconclusive.
Severity: wrong / stale / missing / confusing.

### Verified correct (no action)

| id | Page location | Claim | Evidence | Label |
|---|---|---|---|---|
| OK1 | Split table | Train 24 stories, 44 chars, 484 pairs, 327 Same / 157 Different, 104 constructed. Val 6/11/86/82/4. Test 12/24/329/282/47. All 42/79/899/691/208 | python over `manifest.jsonl`: `train 484 stories 24 chars 44 same 327 diff 157 … val 86 stories 6 chars 11 same 82 diff 4 … test 329 stories 12 chars 24 same 282 diff 47`. Also matches `dataset_manifest.json` | M |
| OK2 | Bullet "No story or character is in more than one split" | No overlap of `char_id` or story id across splits | Set intersections all empty | M |
| OK3 | Reason table counts | 141/50/18/12/9/4/2, sum 236 over 208 Different | `Counter(failure_reasons)` → exactly these, total 236 | M |
| OK4 | Agreement table | 329 pairs κ 0.634 / 89.7%. Non-human test 25 pairs κ 0.000 / 96.0%. All 795 pairs κ 0.659 / 89.3% | Recomputed Cohen's κ from `annotation_agreement.jsonl`: test (329, .8967, .6342), all (795, .8931, .6587), non-human test (25, .96, 0.0). Non-human: 24 both-Same, 1 split | M |
| OK5 | Bullet "Two of those constructed pairs reuse an image pair the raters had labelled Same" | 2 image pairs appear twice (syn-020 ref c0/c1 × `s1-1`) | duplicate-`images` count = 2 | M |
| OK6 | Six example cards and "Frozen record" | Records and rater answers equal the freeze | `npx vitest run …/dataset/data.test.ts --reporter=verbose` → the freeze-comparison test ran (not skipped) and passed | M |
| OK7 | "One training record, whole" | Single prompt across all records. `attributes_present` = [], `style_match` = false, `subjects_unique` = true in every record | train/val/test.json: 1 distinct prompt each. attrs `[]` 484/86/329, style False 484/86/329, uniq True 484/86/329 | M |
| OK8 | Exploratory bullet | 16 excluded, 468 train pairs | runbook L44-57. `data/judge/freezes/obj4-exploratory-qc-v2` exists | M (doc) |
| OK9 | "Three donated candidate stories were excluded" | don-006, don-013, don-015 replaced by backups don-007/011/010 | `dataset_selection.json` `donated_replacements`, `freeze_report.json` `excluded_donated_stories`. Note: don-013's recorded code is `budget_stopped`, filed as `terminal_pipeline_failure` | M |
| OK10 | Constructed pairs all `different_face` + one sentence | 104/104 | Counter on constructed rows | M |

### Problems

| id | Page location | Issue | Evidence | Label | Severity |
|---|---|---|---|---|---|
| F1 | "How a pair was labelled", bullet "Clothing, art style and lighting are not identity. Each of them alone is Same." Also the deviation box. | **The freeze breaks this rule 9 times.** 9 final labels are Different with only `wrong_clothing` (6) or `wrong_style` (3) ticked: train 6, val 1, **test 2**. The rulebook calls this "always a mistake under these rules". The box implies the 10-pair audit fixed this class. It did not catch pairs that reached this label through ordinary adjudication. 5 of the 9 had both raters' first answer = Different, 4 were split. | python: pairs where `failure_reasons ⊆ {wrong_clothing, wrong_style}` → 9 rows (listed by split above). `docs/specs/labelling-rulebook.md` Step 3. `adjudication-notes-2026-09.md` "Label audit" (12 of 112 agreed-Different; 2 test pairs "go through the ordinary queue") and Log 2026-10-09 (one `syn-028:c0` adjudication = `wrong_clothing`) | M (count). I (that adjudication produced them) | missing / wrong-by-omission |
| F2 | Deviation box: "No test label changed." | True only of the 10 AI-assisted labels. Across all pairs, **23 final labels differ from both raters' agreed first answer** (both said Different, final Same): train 19, val 3, **test 1**. 10 of them are the audit. The other 13 come from conflicts that the owner adjudicated: the raters agreed on Same/Different but differed on another field. | python joining `annotation_agreement.jsonl` with the manifest: `test raters False final True` ×1, `train` ×19, `val` ×3. Runbook L338-344: the app flags a conflict when the raters differ on **any** field (172 pairs), and only 85 of those differ on Same/Different | M (counts). I (cause of the 13) | confusing |
| F3 | Bullet "Where their labels disagreed, the study owner settled the pair." | Understates adjudication. The owner settled **172** pairs that conflicted on any field: Same/Different, the reasons, Broken Anatomy or Text Visible. Only **85** disagreed on Same/Different. The owner also wrote **182** adjudication rows in total: the 172 plus the 10 audit pairs, so 22.9% of the 795 rated pairs. The adjudicator was not blind to which rater gave which label. | `dataset_manifest.json` `adjudication_rate: 0.2289` (= 182/795). Runbook L338-344. PREREG §12 2026-09-23 item 2 ("not blind") | M | missing |
| F4 | "Human and non-human pairs" table (Train 19/25, 220/264) | The rule matches character *names* against the intake roster. It counts 7 non-human training characters as **human**: syn-009:c1 cat, syn-010:c1 deer, syn-013:c1 heron, syn-014:c1 goat, syn-015:c1 shrimp, syn-016:c1 vacuum (machine), syn-020:c1 tortoise. Counted by the Character Bible `species` field instead, train is **12 human / 32 non-human characters, 178 / 306 pairs**. Validation is unchanged (9/2, 75/11). The page's own constructed example uses syn-020:c1, a tortoise that this table counts as human. The page states the rule, but a reader will take "human" literally. | `character_slices.json` vs `data/judge/corpus/runs/syn-*/memory.json` `description.species` (script `scratchpad/kinds.py`). Rule: PREREG §12 2026-09-12 item 3 | M (assumes the corpus run memories are the ones frozen. Asset filenames carry the same campaign ids) | wrong (as read) / confusing |
| F5 | Whole page, "A pair is one reference picture of a character and one book page" | A "book page" is any **drawing attempt** of a scene, including attempts the pipeline rejected (ADR-060). **422 of the 795 rated pairs** use attempt 2 or later. Example card 033b8372 uses `s0-3`, the third attempt. Each attempt is paired with every character listed as present in the scene. | `build_dataset.pairs_from_memory` (L95-119). `manifest.scene_images` docstring (L53-74). Filename count `_s<scene>-<attempt>`: pipeline attempt-1 = 166+47+160 = 373, later = 214+39+169 = 422. 544 distinct scene images, 79 references | M (I: the suffix is the attempt number, from the docstring) | missing |
| F6 | First bullet list: "Of the train split's Different pairs, 104 are constructed… The other 795 pairs came out of the pipeline." | Mixes two bases. "The other 795" is the whole dataset minus the constructed pairs, not the rest of train's Different pairs (that is 53). A reader cannot get train Different = 53 natural + 104 constructed. | Counter: train `('pipeline', False): 53`, `('constructed', False): 104` | M | confusing |
| F7 | Missing everywhere | **How the splits were made is not stated.** Splits are by **story**, assigned at intake in `corpus_synthetic.json`: 24 train + 6 val, stratified by art style at 8 train + 2 val per preset. All donated stories are test. So no character, and no story, crosses splits. Which six stories went to validation (syn-025…syn-030, the last six ids): **rationale not found**. | `corpus_synthetic.json`: `('train', cel/gouache/cut_paper): 8 each, ('val', …): 2 each`, val ids syn-025..030. PREREG §2, §3, §12 2026-08-22 and 2026-08-24 | M (the six-story choice: rationale not found) | missing |
| F8 | Missing | **Validation is lopsided and the page does not say so.** 4 Different of 86 (4.7%), against 13.9% natural Different in train (53/380) and 14.3% in test (47/329). 87% of validation pairs are human (75/86), against 37% in train by species. Every checkpoint choice rests on those 4 Different pairs. The paper's results tab already says this. | Counts above. Runbook L240-242 | M | missing |
| F9 | Missing | **How constructed pairs were chosen.** 14 frozen matches (`dataset_selection.json`). Each pairs a reference with **every** natural train page of a target character. Each match has the same species and same art style (rule: PREREG §12 2026-08-24, 2026-09-03 / ADR-057). They were frozen before annotation, at 2026-09-16T20:24:55Z. 12 of 14 are human↔human. 2 are the syn-020 tortoises inside one story. Coverage is best-effort. | `dataset_selection.json`. `build_dataset.constructed_records` L196-247. Species/style check: all 14 same species and same preset (python) | M | missing |
| F10 | Record field table: `anatomy_intact` / `text_free` "false when a rater ticked…" | It is the **final** value. A single rater's tick that the other rater did not make creates a conflict, and the owner decides. Counts are not shown: Broken Anatomy 32/899, Text Visible 3/899. The runbook has them. | Runbook L139. `isConsensus` per runbook L340. Manifest counts: anatomy False 32, text False 3 | M / I (wording) | confusing |
| F11 | Record field `ref_verdict_status` | Missing context: **351 of 899** pairs have a reference that failed the automatic check. Per the owner's earlier measurement, that check cannot ground attributes. A reader may take "passed" as a quality guarantee. | Manifest: passed 548, failed 351. `docs/capstone/reference_judge_investigation_2026-09-02.md` (title only, not reread) | M (count) / I (reliability) | missing |
| F12 | Terminology | The page says "pipeline pair". The paper says "natural pair". `dataset_manifest.json` says `natural_pairs`. "Registered", "freeze" and "frozen record" are never defined. The owner is "study owner" on the page, "developer" in the paper's Methods and "dataset owner" in the paper's Results. | page.tsx L82, L214. paper.md Dataset/Annotation/Results sections | M | confusing |
| F13 | `data.test.ts` "matches the totals in the runbook's freeze table" | The test name overstates it. Only `CHARACTER_KINDS` is checked against the runbook. `SPLITS`, `REASON_PAIRS`, `AGREEMENT` and `EXPLORATORY` are compared to literals typed in the test, so a runbook change would not fail it. | data.test.ts L18-33 | M | confusing (test) |
| F14 | Agreement row "Held-out test, non-human characters, 25 pairs" | ADR-065 decision 5 allows donated material "only as whole-split counts". This row is a sub-split count that covers **2** donated characters. It is probably acceptable (it is a registered slice), but it sits at the edge of the decision. | ADR-065 decision 5. python: test non-human chars = 2 | I | confusing (policy) |
| F15 | Missing | Other facts the paper may need that are not on the page: the guide fix mid-labelling (first 642 labels before deploy `757a406`, κ before/after shows no clear effect). The ambiguous-reference sensitivity analysis (20 test pairs dropped, κ 0.709). 26 agreed-Different pairs with Character Absent counted but not reviewed. | PREREG §12 2026-09-23 item 3. Runbook L346-366. adjudication-notes "Counted, not acted on" | M (doc) | missing |

---

## (b) Proposed content changes, with draft copy

Every draft below uses only sourced facts. Where a rationale is missing, the copy says so.

### B1. What a pair is (replaces the first paragraph of "What is in it")

> **A pair** is two pictures. The first is a character's **reference**: the one portrait the app drew
> of that character before drawing the book. The second is one **drawing of a book page** in which
> that character is supposed to appear. The app often draws a page several times before it keeps
> one. Every attempt counts as a page here, including the ones it threw away, because the judge has
> to check every attempt in real use. A page with two characters makes two pairs, one for each
> character's reference.
>
> The dataset has 899 pairs from 42 generated books: 30 from stories the researchers wrote
> (*synthetic*) and 12 from stories children donated (*donated*). 795 pairs came out of the app
> (*natural pairs*) and were labelled by people. 104 were made by a script (*constructed pairs*, see
> below).

Sources: `build_dataset.py` L95-119, `manifest.py` L53-74, ADR-060, runbook freeze table.
Optional fact line: "422 of the 795 natural pairs show a second or later attempt" (measured, F5).
It is not in a tracked doc yet. Per ADR-065 decision 4 it must go into the runbook before the page
can cite it.

### B2. What "same character" and "different character" mean, and how labels were assigned

> **Same character**: the page shows the same individual as the reference. Species, face, body
> colours and countable body parts (eyes, ears, tail, horns, wings, limbs) all match. Pose,
> expression, clothing, art style and lighting may change. **Different character**: at least one of
> those identity features is wrong, or the character is missing from the page. A rater may answer
> Different only by ticking a named reason. If no reason applies, the answer is Same.
>
> **Who decided.** Two group members labelled all 795 natural pairs, each on their own, seeing only
> the two pictures and never the story. Each label is one answer (Same or Different) plus the
> reasons, a Broken Anatomy box and a Text Visible box. When the two labels differed in any of these
> (172 pairs, 85 of them on Same or Different itself), the study owner decided the pair. The owner
> could see who gave which label. The owner also relabelled 10 pairs on which both raters had
> wrongly answered Different for clothing or style alone. An AI reviewed those 10, and the owner
> approved them. This is a reported deviation. The 104 constructed pairs were not labelled by
> anyone. They are Different because a script built them from two different characters.
>
> **Known label errors that were kept.** 9 final labels are Different with only Wrong Clothing or
> Wrong Style ticked, which the rules say should be Same: 6 train, 1 validation, 2 test. The dataset
> is registered, so they were not changed.

Sources: rulebook Steps 1-3, PREREG §12 2026-09-23 / 2026-09-30, runbook L338-344, adjudication
notes. The last paragraph (F1) and the "23 overrides" fact (F2) need a runbook entry first
(ADR-065 decision 4). They are also something the owner should confirm before publishing.

Replace "No test label changed" with: "The AI-assisted review changed no test label. Ordinary
adjudication did decide test pairs, as it did every conflicted pair."

### B3. One real record, field by field

A real validation row, verbatim from `manifest.val.jsonl`. It is the first example card. Image paths
are shown because this is synthetic; ADR-066 chose to hide them on the cards.

```json
{
  "pair_id": "033b8372e89e4c06",
  "char_id": "syn-025:c0",
  "split": "val",
  "provenance": "synthetic",
  "pair_type": "pipeline",
  "images": ["assets/ref/syn-025--campaign-…_ref-c0-1.png",
             "assets/scene/syn-025--campaign-…_s0-3.png"],
  "differences_observed": "Present on the page: human, brown hair, tan skin, … blue shirt, pants.",
  "same_character": true,
  "label": false,
  "anatomy_intact": true,
  "text_free": true,
  "failure_reasons": [],
  "ref_verdict_status": "passed"
}
```

| Field | Plain meaning |
|---|---|
| `pair_id` | A random-looking id made from the character and the page image. No meaning. |
| `char_id` | Story `syn-025`, its first character `c0`. Splits are made on the story. The model never sees this. |
| `split` | Which set the pair is in: `train`, `val` or `test`. |
| `provenance` | `synthetic` = a story the researchers wrote. `donated` = a child's story. |
| `pair_type` | `pipeline` = a natural pair, drawn by the app and labelled by people. `constructed` = made by a script. |
| `images` | Reference first, page second. `s0-3` means scene 0, third attempt. |
| `differences_observed` | A sentence a script writes. For Same, it lists the character's stored description. For Different, it names the ticked reasons. No person wrote it, and it is not a description of this picture. |
| `same_character` | The final answer. `true` = Same. |
| `label` | The opposite of `same_character`. `true` = Different, the class the judge is scored on. |
| `anatomy_intact` | `false` if the final label ticked Broken Anatomy (32 of 899). |
| `text_free` | `false` if the final label ticked Text Visible (3 of 899). |
| `failure_reasons` | The ticked reasons, from the fixed list of seven. Empty for Same. |
| `ref_verdict_status` | Whether the app's automatic check passed the reference portrait when the book was made. 351 of 899 failed. Bookkeeping only. |

### B4. How the splits were made and why

> **Split by story, decided before any picture was drawn.** Each story was assigned to one split
> when it was entered. All of its characters and pages go with it. No story or character appears in
> two splits, so the judge is always tested on characters it has never seen. This stops it scoring
> well by remembering a character.
>
> - **Train**: 24 synthetic stories. **Validation**: 6 synthetic stories. Each of the three art
>   styles has 8 train stories and 2 validation stories.
> - **Test**: every donated story that finished: 12 of 15 candidates. Three failed in the app and
>   were replaced by backup stories of the same style, as the plan required.
> - **Why children's stories are test only**: there are too few donated characters to spare any for
>   training. Testing only on them means the reported number is measured on real children's writing,
>   so any gap between synthetic and real stories shows up in the result instead of hiding.
> - **Constructed pairs are in train only**, so validation and test look like real use.
> - **Not balanced**: no class balancing was planned. Train is 327 Same / 157 Different, validation
>   82 / 4, test 282 / 47. Validation's 4 Different pairs are very few, and every checkpoint choice
>   rests on them.
> - **Rationale not found**: why stories syn-025 to syn-030 in particular became validation, and why
>   validation is 6 stories.

Sources: `corpus_synthetic.json`, PREREG §2, §3, §12 (2026-08-22, 2026-08-24, 2026-09-12 item 4),
`dataset_selection.json`, research-changelog 2026-10-11 (no balance registered).

### B5. Constructed pairs (one short paragraph)

> A constructed pair puts one character's reference next to a page drawn for a **different**
> character of the **same species and art style**: a girl against another girl, a tortoise against
> another tortoise. That makes it a hard "Different" example. 14 such character matches were chosen
> by hand and frozen before labelling began. Each reference is paired with every training page of
> its match, giving 104 pairs. 12 of the 14 matches are two human characters. They give the judge
> more Different examples to learn from (104 of train's 157), but they all carry the same reason and
> the same script-written sentence.

Sources: `dataset_selection.json`, `build_dataset.constructed_records`, PREREG §12 2026-08-24 and
2026-09-03. Note: `docs/capstone/model_finetuning.md` L22 says matches maximize similarity over
colour/body/silhouette/clothing/face. No code that maximizes similarity was found.
`dataset_selection.py` L143-205 only filters by species and style for a manual pick (I).

### B6. End-to-end process (a numbered list or diagram near the top)

1. **Stories.** 30 synthetic stories (researchers) and 15 donated candidates (children). Each is
   assigned a split and an art style when entered.
2. **Books.** The app draws each story once (corpus campaign, one budget): a reference portrait
   per main character, then each page, redrawn when its own check fails. 42 books finished.
3. **Pairs.** Every drawing attempt × every character on that page = one natural pair (795).
4. **Labelling.** Two group members label every pair alone, image-only, against the frozen
   rulebook (2026-09-21).
5. **Adjudication.** The owner decides the 172 pairs where the two labels differ in any field, plus
   the 10 audited pairs (AI-assisted, a deviation).
6. **Constructed pairs.** A script adds 104 train-only Different pairs from 14 frozen matches.
7. **Freeze.** `build_dataset --freeze` writes the manifests and the training files, hashed, on
   2026-09-30. This is the "registered" dataset and is never edited.
8. **Training.** Qwen3.5-9B, QLoRA, 3 seeds × 183 updates on the 484 train pairs.
9. **Checkpoint choice.** Per seed, the checkpoint with the best Different-class F1 on validation.
   Seed 1 was chosen as primary before the test was opened.
10. **Test.** One read of the 329 donated pairs.

Sources: runbook "Execution pipeline sequence" L870-975, freeze report, `train_qlora.yaml`,
results page. Training and selection already appear on `/research/results`, so link to it rather
than repeat the numbers.

### B7. Human/non-human table (F4)

Either relabel the columns "Declared non-human (by name)" / "Not declared". Or add the
species-based count with a one-line note: "Counted by the character's species instead, train has 12
human and 32 non-human characters (178 and 306 pairs). The declared roster missed 7 animal or machine
side characters, such as 'the other tortoises' and 'the goat'." That number needs a runbook entry
first (ADR-065 decision 4). The owner decides which count the paper uses.

### B8. Smaller edits

- F6: change the bullet to "Train's 157 Different pairs are 53 natural and 104 constructed."
- F12: say "natural pair" everywhere and note "(`pipeline` in the files)". Define "registered" once:
  "frozen on 2026-09-30 with a checksum, and never edited after".
- F13: have `data.test.ts` read the runbook freeze-table row instead of literals.
- Show the artifact checkbox counts (32 Broken Anatomy, 3 Text Visible). The paper's table lists
  both.

---

## (c) Paper-sync notes

### Where the paper and the data disagree, or the paper is weaker

1. **Annotation Criteria table (paper.md L253-264 / tab L19-29) contradicts the rulebook.** It lists
   "Clothing and Accessories" and "Style" as identity components. Per the rulebook, each **alone is
   Same**; they are ticked only when the pair is already Different. "Character Absent: Present /
   Absent" is shown as its own criterion, but it is a reason for Different. Suggested fix: split the
   table into *Identity reasons* (Species, Face, Body colour, Body features, Character absent →
   Different), *Not identity on their own* (Clothing, Style, Lighting → Same) and *Artifact flags*
   (Broken Anatomy, Text Visible). Typos: "Text Visibile", and "Cohen's Cappa" in the Results tab.
2. **Adjudication description** ("conflicting classifications or requiring further clarification").
   Should say: 172 pairs conflicted on any field, 85 on Same/Different, and the adjudicator was not
   blind. The **10 AI-assisted, owner-approved labels are absent from the paper**, but
   PREREG §12 2026-09-30 says this deviation "must be reported with the results".
3. **Roles are named three ways**: "developer" (Methods), "dataset owner" (Results), "study owner"
   (page, PREREG). Pick one.
4. **"Generated picture-book page"**: the paper should say rejected attempts are included
   (research-changelog §1 item 6, ADR-060).
5. **Fine-Tuning Procedure** says training data "included the associated drift-reason annotations
   where available". Accurate, but it should add: `differences_observed` is script-written, not a
   rater's words. Three target fields are constants in every record (`style_match` false,
   `attributes_present` empty, `subjects_unique` true; research-changelog 2026-10-11).
6. **Constructed pairs**: add "same species and art style, 14 hand-picked matches frozen before
   labelling". Add: two of them contradict a rated Same pair (research-changelog 2026-10-11).
7. **Dataset Division**: add story-level, intake-time assignment with style stratification
   (8 train + 2 val per style). Add the 15 → 12 donated selection with same-style replacement. The
   choice of which six stories went to validation: rationale not found.
8. **Inter-annotator agreement**: the Results tab reports only the test slice. Add the all-pairs
   figure (795, κ 0.659, 89.3%) and the registered limitation: both raters are group members briefed
   by the owner. Add the non-human-slice caveat (κ 0 is a prevalence artifact, 24/25 both Same).
9. **Known label errors** (F1, 9 clothing/style-only Different labels, 2 in test) and the mislabelled
   human/non-human slice (F4) belong in Limitations. Neither is in the paper. Neither is in the
   research-changelog yet either, so log them there first (AGENTS.md routes research findings to
   `research-changelog.md`).
10. **Numbers the paper has right** (checked): 899 / 795 / 104, 42 stories, 79 characters, the split
    table, 76.86% / 23.14%, 12 donated stories, 24 test characters, every training-config row
    (vs `train_qlora.yaml`), validation checkpoints 40/40/140 with F1 .333/.444/.364, and every
    held-out metric and confusion count (vs runbook L231-242).

### What the paper needs that the page lacks

The end-to-end process (B6), the split method (B4), percentages, and the artifact-flag counts. The
paper also needs a sample-pair figure: its placeholder reads "sample image sa dataset mismo" and
"Fig. X Sample Annotation Procedure". The page's six synthetic examples can fill it, but test
images must not be used (ADR-065 decision 5).

### What the page has that the paper lacks

The reason counts (141/50/18/12/9/4/2), the human/non-human mix (once F4 is settled), the exploratory
16-pair freeze and the fact that it was not used, the 3 excluded donated stories, the 2 contradictory
constructed pairs, all-pairs κ, the non-human κ explanation, the 10-pair AI-assisted deviation, and a
full training record.

### Evidence scripts (scratchpad)

- `C:\Users\Asus\AppData\Local\Temp\claude\a4560db910e9236d\4623efc1-7653-44c8-bb27-5d2442de1d7f\scratchpad\kinds.py`
  (species-based human/non-human)
- `C:\Users\Asus\AppData\Local\Temp\claude\a4560db910e9236d\4623efc1-7653-44c8-bb27-5d2442de1d7f\scratchpad\chars.py`
  (character names and species per story)
- The other counts are inline `python -I` one-liners over `data/judge/freezes/obj4-v1/*`. Their
  commands and outputs are in the findings table.
