# ADR-066 — The dataset page shows frozen records, and a static page shows the partial judge result

**Status:** Accepted (2026-10-11) · extends ADR-065, which is not edited · adds one public frontend
route · no backend route, no migration, no `StoryMemory` or `contracts/` change · no Supabase read ·
no new dependency

**Context:**

The owner reviewed `/research/dataset` and asked for three things. The constructed example was
hard to read. The cards showed a label and a sentence but none of the stored data. And nothing on
the site shows what the fine-tune did; a panelist has to open `group-guide.md` §5.2.

Epic #102's "Research surfaces" area asks that the panel find the datasets, the criteria, the
results and the decisions without reading code. ADR-065 decision 6 allows an example's label,
reasons and pair id, not its whole record.

What the code and data say, checked on 2026-10-11:

- **Every constructed pair carries the same text.** All 104 have the one reason `different_face`
  and the one sentence in `CONSTRUCTED_RATIONALE` (`backend/finetune/build_dataset.py`). No rater
  wrote either.
- **`differences_observed` is not a rater's sentence on any pair.** `render_rationale` builds it
  from the ticked reasons and the character's stored attributes.
- **Three target fields are constants.** In all 484 records of `train.json`, `attributes_present`
  is empty, `style_match` is false and `subjects_unique` is true. They were not labelled and take
  the schema defaults (`backend/finetune/manifest.py`, the comment under `ManifestRecord`).
- **One prompt is used for every training record.**
- **Two constructed pairs contradict a rated pair.** Recorded in `research_runbook.md`, "What the
  registered freeze contains".
- **The result's exact values had no tracked source.** `group-guide.md` §5.2 gives two decimals.
  The confusion counts, the per-judge intervals, the exact McNemar p and the validation F1 of each
  selected checkpoint were only in the git-ignored `qwen_comparison.partial.json`.
- **The docs give McNemar's p without its direction.** The counts settle it: the untuned model is
  wrong on 65 of 329 pairs and seed 1 on 40. The small p goes with seed 1 making fewer errors, while
  F1, the registered primary metric, is lower for seed 1.
- **Seed and checkpoint were chosen on four Different pairs.** The validation split has 4 Different
  pairs in 86.
- **No chart library is installed** (`frontend/package.json`).
- **The freeze is git-ignored**, so CI cannot compare the page's records with it.

**Decision:**

1. **Each example card shows its frozen record.** The fields of the pair's `manifest.jsonl` row,
   copied as stored, in a block the reader opens. `images` is left out: it holds two local file
   paths, and the pictures are on the card. For a pipeline pair the card also says what each of the
   two raters first answered, from `annotation_agreement.jsonl`, without naming a rater.

2. **The page explains each field once**, in the code's own terms: which fields a person labelled,
   which a script wrote, and which never reach the training text.

3. **One training record is shown whole.** The prompt and the target answer for the constructed
   example, copied from `train.json` without `images`, with a line saying which three fields are
   the same fixed value in every record.

4. **The constructed example becomes `848c636f47f8e342`.** A brown-shelled tortoise's reference against the
   page that the Same example `14126f2a535e8682` uses. The two cards show one page labelled both
   ways, by the reference it is checked against. It replaces `0be3826c05ba35ba`. The owner confirms
   the picture before it is committed, as in ADR-065 decision 6.

5. **`/research/results` is a public static route** in the same route group as the other two. It
   shows the partial comparison of 2026-10-08: the four judges' F1, precision and recall, what each
   did with the 47 Different and the 282 Same test pairs, the unreadable answers, the registered
   seed 1 versus untuned comparison, the ambiguous-reference check, and the limits.

6. **Every number on it comes from `research_runbook.md` or `group-guide.md`.** The exact values
   are first copied into the runbook ("Exact values of the partial comparison"). A unit test fails
   when a value on the page is not in the file it cites.

7. **The charts are plain HTML and CSS bars.** No chart library. Each bar has its number printed
   beside it, and a table on the same page carries every charted value.

8. **The page says what the result is.** Partial, with no prompted Gemma and no final report. F1 is
   the registered primary metric and the untuned model has the higher F1. The interval of the gap
   touches zero. It says what the McNemar p does and does not show, and that checkpoint and seed
   were chosen on four Different validation pairs. Wording follows `group-guide.md` §5.2 and the
   runbook; a sentence the docs do not state is arithmetic on the table and is marked as such.

9. **Test material stays aggregate.** Whole-test-slice counts only: no test image, no per-pair
   prediction, no donated story or character id, no rater id. The ambiguous-reference check is
   described as one test character and 20 pairs. The `don-` test of ADR-065 covers the new data.

10. **The two contradictory constructed pairs are stated** on the dataset page and among the
    results page's limits, with the runbook as the source.

**Consequences:**

- The records make public the synthetic story and character ids of six pairs (for example
  `syn-020:c1`). Synthetic ids already appear in the public documents.
- The record check runs only where the freeze is on disk. In CI it is skipped, so a wrong record
  typed into the page is caught on the owner's machine or not at all.
- A second copy of the result now lives in the runbook. If the local result is ever regenerated
  with different numbers, the runbook table and the page are stale until someone recopies them.
- The page puts a negative result one click from the public site. That is the study's result and
  the preregistration requires it reported.
- A full report with the remaining comparators would need this page rewritten, not appended to.
- The header gains a Results tab. Its row already wraps on a phone.

**Alternatives considered:**

- **Add a chart library (Recharts or similar).** Rejected: about a dozen bars do not need one, and
  it adds client JavaScript to a page that is otherwise static.
- **Render the runbook's markdown tables or ship a CSV.** Rejected for the same reasons as ADR-065:
  no markdown renderer, and the docs hub already links the file. A CSV would be a third copy.
- **Show accuracy beside F1.** Rejected: it is not a registered metric, and adding it after seeing
  the result would read as choosing the number that flatters the trained judge. The error counts
  are shown because they are what McNemar's test compares.
- **Show the raw record with its `images` paths.** Rejected: the paths name local files and a
  campaign folder, and add nothing the pictures do not.
- **Put the results on the dataset page.** Rejected: that page answers what the data is; the result
  is a different question and needs its own limits stated beside it.
- **Keep `0be3826c05ba35ba`.** Rejected: the page shows two people and neither is plainly the one
  to compare, which is what made the card hard to read.
- **Drop or relabel the two contradictory pairs.** Out of scope: the freeze is registered. They are
  documented.

### Amendment (a) — 2026-10-11 — the results page also says how the judge was trained and what the project takes from the result

**Context for the amendment.** After accepting this ADR the owner asked where the training is
documented and whether the result can be read as more than a table. The settings were in
`backend/finetune/train_qlora.yaml` and `docs/specs/judge-finetune.md` §6, and neither was linked
from the site. The registered rule for this outcome is in `PREREGISTRATION_OBJ4.md` §6 and §7, and
the move to the pipeline is in `research-changelog.md` §2.

**Decision.** This adds to decision 5. Decisions 6, 8 and 9 apply unchanged.

1. **`/research/results` gains "How the judge was trained".** The settings are first copied into
   the runbook ("Registered training settings"). A unit test checks each one against the runbook
   and against `train_qlora.yaml`. The reason for three seeds follows `PREREGISTRATION_OBJ4.md` §9.5.

2. **It gains "What we take from this".** Four readings, each with its source: what Objective 4
   reports, that the trained judge is not used in the product, when and why the main work moved to
   the pipeline, and that training changed the judge's answers without improving F1.

3. **No cause is given.** The four candidate explanations are listed under a heading that says they
   were not tested, with what the preregistration allows next. They are recorded in
   `research-changelog.md` first.

4. **The docs hub lists `docs/specs/judge-finetune.md` and `backend/finetune/train_qlora.yaml`.**
   ADR-065's list came from issue #105; these two are added here.

**Consequence.** The page now carries interpretation the adviser has not reviewed. Each reading
cites the document it rests on, so a correction is made there first.
