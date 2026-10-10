# StoryBuddy: Research Changelog

**Last updated:** 2026-10-11 · **Covers:** everything since the Objective 4 pre-registration was frozen
on 2026-08-14. **Use it to:** update the manuscript. Each entry says what changed, why, and which
part of the paper it touches.

Every statement stands on its own. The bracketed paths are where the evidence lives in the
repository. Where this file and a cited source disagree, the source wins and this file needs fixing.
For the current state in plain words, read [`group-guide.md`](group-guide.md) first.

**Entry types:**

- **Decision**: the project chose something.
- **Deviation**: a change to the registered plan, disclosed as such.
- **Finding**: a measured result.
- **Limitation**: something the paper must state as a weakness.
- **Scope**: something added to or removed from what is evaluated.

---

## 1. What the manuscript must now say

1. **The fine-tuned judge is Qwen3.5-9B, not Qwen2.5-VL-7B.** The base model changed on 2026-09-30,
   after labels and the dataset freeze existed. It is a disclosed post-registration deviation
   (ADR-061). [`docs/product/PREREGISTRATION_OBJ4.md` §12, 2026-09-30]
2. **Labels came from two raters with owner adjudication.** This replaced the one-rater plan of
   2026-08-29, so agreement is reported between raters, not as test-retest. Ten audit labels were
   adjudicated with AI assistance, and that is disclosed. [`PREREGISTRATION_OBJ4.md` §12, 2026-09-23
   and 2026-09-30]
   Inter-rater κ on `same_character`, test slice: 0.634 (89.7% agreement, n = 329). The amendment's
   78.4% is a different measure: it counts a pair as conflicted when the raters differ on any
   labelled field. [runbook, "Registered agreement and sensitivity analyses (2026-10-09)"]
3. **The Objective 4 result is partial.**
   - Only untuned Qwen and the three fine-tuned seeds were compared on the held-out set.
   - The prompted Gemma baseline failed authentication, and paid evaluation stopped for budget. The
     registered seven-comparator report is therefore incomplete.
   - No claim-ladder or product-gate decision was made.

   [`docs/capstone/research_runbook.md`, "Held-out resume context"]
4. **Fine-tuning ran; it did not improve the judge.** Three training runs completed, which shows
   training is technically feasible in this setup. On the held-out set, the untuned model scored
   higher F1 than every fine-tuned seed. The bounded wording to use: "Under the evaluated dataset,
   training settings and inference constraints, fine-tuning did not demonstrate a reliable
   improvement over the untuned baseline." Do not write that fine-tuning is infeasible. [runbook,
   "Owner decisions and confirmed scope"]
   Do not cite the McNemar p (0.0035) as evidence that the fine-tuned judge is worse. The test
   compares which pairs each judge got right, and seed 1 was wrong on fewer pairs (40 against 65)
   because it rarely answers Different. Report it beside the counts. [runbook, "Exact values of the
   partial comparison (copied 2026-10-11)"]
   Do not give a cause for the result. None was tested; the four candidate explanations are in the
   2026-10-11 Limitation row below. [`PREREGISTRATION_OBJ4.md` §7]
5. **Narration and PDF export are out of scope** (ADR-058). The Objective 5 questionnaire item that
   named them was corrected. That correction still needs adviser sign-off before the questionnaire is
   given. [`docs/capstone/research_instruments.md`]
6. **The corpus is 42 generated books:** 30 from synthetic stories and 12 from donated stories.
   Rejected page attempts are included as judge data (ADR-060). [`PREREGISTRATION_OBJ4.md` §12,
   2026-09-12]
7. **The page defects are limitations**, not results:
   - duplicate characters;
   - stated body counts;
   - background groups with no reference;
   - missed actions.

   The stage audit behind them was scored by AI reviewers and is provisional.
   [`model-probes-2026-10.md`, "Limitations to carry into the write-up"]
8. **The labels have limitations of their own.**
   - Hair length or style is not a rulebook reason (only hair colour is), so raters could split on it.
   - Pairs both raters got wrong never reached adjudication. The ten audited pairs are the only
     exception.
   - The adjudicator could see which rater gave which label.
   - 26 agreed-Different pairs include Character Absent. They were counted, not re-checked.
   - Object and invented characters lean toward Different as a group: their references have a
     minimal face and stick legs, and their pages add limbs (adjudication notes, row 5).
   - Duplicated characters are a generator defect the judge is not asked to score.
   - The rulebook assumes references and pages share one style. At least one page came out as
     pixel art under a non-pixel preset.

   [`PREREGISTRATION_OBJ4.md` §12, 2026-09-23 item 4; `adjudication-notes-2026-09.md`]
9. **The product did not change its models.** The scene editor stays Qwen-Image-Edit (ADR-063). The
   product judge stays prompted Gemma, since the fine-tuned judge is not deployed.

## 2. Why the focus moved from the judge to the pipeline

- **2026-10-07:** paid evaluation stopped. Training and validation selection were complete. The owner
  had destroyed the rented GPU hosts after backing them up and could not fund another top-up.
- **Owner's decision that day:** report untuned against fine-tuned Qwen, record the finding, and make
  the existing pipeline the next workstream. Leave the production judge unchanged.
- **2026-10-08:** the partial held-out result came in. The fine-tune did not beat the untuned model.

Pipeline diagnosis was not new at that point. The roadmap had scheduled it alongside Objective 4
since late September (`ROADMAP.md` C3-04, and the September gate audit). What changed on 2026-10-07
is that the pipeline became the main work. [runbook, "Held-out resume context" and "Owner decisions
and confirmed scope"]

## 3. Changelog, newest first

| Date | Type | What changed | Why | Paper section | Source |
|---|---|---|---|---|---|
| 2026-10-11 | Limitation | The training split is not class-balanced: 327 Same and 157 Different pairs, 104 of the Different constructed. `methodology.md` §4.3 and `model_finetuning.md` §3 said constructed negatives balance it, and `model_finetuning.md` §2.2 said the dataset is built over the donated corpus. Both documents are corrected: train and validation are synthetic, the donated stories are the test set only, and constructed negatives raise the Different share without balancing it | Neither statement matched the registration or the freeze. `PREREGISTRATION_OBJ4.md` §2 fixes the corpus roles, and ADR-057 makes constructed-negative coverage best-effort. No balance was registered, so this is a wrong description, not a deviation | Methodology (dataset construction, class imbalance) | `PREREGISTRATION_OBJ4.md` §2; ADR-057; runbook, "What the registered freeze contains" |
| 2026-10-11 | Limitation | The cause of the Objective 4 result is not established. Four explanations are recorded as untested: checkpoints chosen early on four Different validation pairs; 104 of the 157 Different training pairs carrying one script-written reason and sentence; training on synthetic stories (83% non-human) and testing on donated ones (mostly human); answers cut off by the 256-token generation cap. Whether the unreadable answers were cut off was not checked | The Discussion must not present any of these as a finding. `PREREGISTRATION_OBJ4.md` §7 allows debugging on train and validation only, and one second held-out read after a defect, not a modelling change, is fixed. No claim-ladder decision and no second read were made | Discussion, Limitations, Future work | `PREREGISTRATION_OBJ4.md` §6 and §7; runbook, "What the registered freeze contains", "Registered training settings (copied 2026-10-11)" and "Held-out resume context"; `group-guide.md` §5.3 |
| 2026-10-11 | Finding | The two seeds whose selected checkpoint is `checkpoint-40` (40 of 183 updates, before the first epoch ends at update 61) are the two with 40 and 44 unreadable answers of 329. Seed 2, selected at `checkpoint-140`, has 8 and the F1 closest to the untuned model | Arithmetic on tracked values. Three seeds are too few to call it a pattern, and no cause was tested | Results (Objective 4), Discussion | runbook, "Exact values of the partial comparison (copied 2026-10-11)" and "Registered training settings (copied 2026-10-11)" |
| 2026-10-11 | Finding | Training changed the judge's answers without improving F1: seed 1 calls 11 of 329 held-out pairs Different against the untuned model's 76, and gives 40 unreadable answers against 3. `PREREGISTRATION_OBJ4.md` §6 describes a judge that does not beat its base as "The LoRA did nothing"; the counts show the adapter changed the output | The owner asked how to read the result. The wording is for the adviser to confirm | Discussion | runbook, "Exact values of the partial comparison (copied 2026-10-11)"; `PREREGISTRATION_OBJ4.md` §6 |
| 2026-10-11 | Finding | The primary comparison's McNemar p (0.0035) goes with fine-tuned seed 1 being wrong on fewer held-out pairs than the untuned model (40 against 65 of 329), not more. Seed 1 answers Different on 11 pairs against 76, so it makes 2 false alarms and misses 38 of the 47 Different pairs. F1, the registered primary metric, still favours the untuned model | Earlier entries gave the p without its direction. The test compares which pairs each judge got right (`mcnemar_exact`), and the confusion counts settle the direction. The counts were only in the local result until now | Results (Objective 4), Discussion | runbook, "Exact values of the partial comparison (copied 2026-10-11)"; `backend/finetune/evaluation_metrics.py` |
| 2026-10-11 | Limitation | Checkpoint and seed were selected on a validation split with 4 Different pairs out of 86. The selected checkpoints' validation F1 values (0.333, 0.444, 0.364) each rest on those four pairs | Not stated in this file before. Whether it explains the preselected seed scoring lowest on the held-out set was not tested | Limitations | runbook, "Exact values of the partial comparison" and "What the registered freeze contains" |
| 2026-10-11 | Limitation | Two of the 104 constructed training pairs reuse an image pair the raters labelled Same, so `train.json` holds two image pairs with both answers (4 of 484 records). Not corrected: the freeze is registered. No validation or test pair is affected | `constructed_records` pairs a reference with every page of its matched character. One of the 14 frozen matches is inside a single story, and one of its pages shows both characters. Found while choosing an example for `/research/dataset` | Methods (dataset), Limitations | runbook, "What the registered freeze contains"; `backend/finetune/build_dataset.py` |
| 2026-10-11 | Limitation | Three fields of the judge's training answer are constants: `attributes_present` empty, `style_match` false, `subjects_unique` true in all 484 training records. They were not labelled and take the schema defaults, so the fine-tuned judge's output on them carries no information | Recorded in a code comment only until now | Methods (dataset) | `backend/finetune/manifest.py`, comment under `ManifestRecord`; ADR-066 |
| 2026-10-10 | Decision | Donated-story detail in public docs stays as written: IDs, plot summaries, reference-image descriptions, one title with a quoted line, and character names. Nothing is redacted, so there is no history rewrite and the repository stays public | The owner wants the detail on hand if the panel asks. The consent draft promises name removal and private images, not private story text. Open for the adviser: some names are as the children wrote them, and the administered consent wording is not recorded (#54) | Ethics (data handling) | #108; `story_donation_consent_and_assent_draft.md` |
| 2026-10-09 | Limitation | Label limitations gathered for the write-up: hair-length gap, agreed-wrong pairs unseen by the adjudicator, adjudicator not blind to rater, 26 Character Absent pairs counted not checked, object characters skewed toward Different, duplicates, style premise | Recorded during C3 but not yet in this file (#94) | Methods (annotation), Limitations | `PREREGISTRATION_OBJ4.md` §12; `adjudication-notes-2026-09.md` |
| 2026-10-09 | Finding | Registered agreement and sensitivity analyses run. Inter-rater κ, test slice 0.634 (all pairs 0.659); non-human slice κ 0 at 96% agreement, a prevalence artifact (24 of 25 pairs Same for both). Guide boundary: no clear effect, groups small and mostly straddling. Without the ambiguous-reference characters (20 pairs, n = 309): untuned F1 0.48, seed 1 0.35, ΔF1 −0.13 (95% CI −0.33 to +0.05), McNemar p = 0.0075; same direction as the primary | Pre-registered items 2, 3 and 5 of the 2026-09-23 amendment; saved predictions only | Methods (annotation), Results (Objective 4) | runbook, "Registered agreement and sensitivity analyses (2026-10-09)"; `heldout-1/sensitivity_and_agreement.json` (local, git-ignored) |
| 2026-10-08 | Decision | FLUX.2 klein rejected as scene editor; Qwen-Image-Edit stays | On 30 random pages, blinded, klein drew as many duplicates (4 against 4) and lost identity more (10 against 3) | Methods (system), Discussion | ADR-063 |
| 2026-10-08 | Limitation | Duplicate characters stay an open defect at about 13% of page images | Two editors produced them at the same rate; a prompt line, rewritten directions and best-of ranking all failed | Limitations | `model-probes-2026-10.md` |
| 2026-10-08 | Finding | Describing only the visible end state fixed 2 of 2 pages whose direction named something absent or pretend; role swaps did not respond | One-moment direction test, 4 action pages, one AI rater | Discussion (future work) | `model-probes-2026-10.md` |
| 2026-10-08 | Finding (provisional) | 77 of 150 shipped pages carry a major defect; non-human pages 66 of 117, human pages 11 of 33 | Stage audit of the 30 synthetic books, AI reviewers, owner unconfirmed | Limitations; Discussion | `pipeline-stage-audit-2026-10.md` |
| 2026-10-08 | Decision | `segment` now adds a cast member the direction names by species ("the moth") | Two pages drew a character with no reference | Methods (system) | PR #101, `docs/specs/scene-segmentation.md` |
| 2026-10-08 | Finding | Held-out F1: untuned 0.47; fine-tuned seed 1 0.31 (precision 0.82, recall 0.19); difference −0.16, 95% CI −0.36 to +0.003; exact McNemar p = 0.0035; unparsed answers, scored as Same: untuned 3, seed 1 40 (of 329) | Partial comparison, 329 pairs, 47 Different | Results (Objective 4) | `data/judge/evaluations/obj4-v1/heldout-1/qwen_comparison.partial.json` (local, git-ignored); method in runbook, "Partial untuned versus fine-tuned comparison" |
| 2026-10-07 | Scope | Reporting narrowed to untuned against fine-tuned Qwen; paid evaluation stopped; prompted Gemma's capture failed (HTTP 401) and is kept as an infrastructure failure, not a quality result | Budget exhausted; authentication failure | Results (Objective 4), Limitations | runbook, "Owner decisions and confirmed scope" |
| 2026-10-07 | Decision | Validation checkpoint selection signed; seed 1 is the deployment seed; held-out access reserved once (run `obj4-heldout-1`) | Selection on validation only, before the test set is read | Methods (Objective 4) | runbook, "Saved progress and safe resume" |
| By 2026-10-06 | Finding | Three-seed QLoRA training of Qwen3.5-9B completed and backed up | Technical feasibility of training | Results (Objective 4) | runbook, "Qwen35 host qualification" |
| 2026-09-30 | Deviation | Fine-tune base changed to Qwen3.5-9B (pinned revision) | Owner preferred the newer open-weight multimodal base | Methods; Limitations | ADR-061; `PREREGISTRATION_OBJ4.md` §12 |
| 2026-09-30 | Deviation | Ten agreed-pair audit labels adjudicated with AI assistance | Agreed-Different pairs resting only on clothing or style were re-checked | Methods (annotation); Limitations | `PREREGISTRATION_OBJ4.md` §12; `adjudication-notes-2026-09.md` |
| 2026-09-30 | Decision | Registered dataset frozen: 484 train, 86 validation, 329 test pairs. A separate exploratory freeze drops 16 disputed synthetic training pairs | Dataset handoff | Methods (datasets) | runbook, "Dataset handoff" |
| 2026-09-23 | Deviation | Two raters plus owner adjudication; agreement is inter-rater; a sensitivity analysis declared before any number existed | Two raters had each labelled all 795 pairs on 2026-09-21 | Methods (annotation) | `PREREGISTRATION_OBJ4.md` §12 |
| 2026-09-16 to 17 | Decision | Corpus generated: 42 books (30 synthetic, 12 donated), about USD 30; three donated stories left out on purpose once the style floors were met | Corpus campaign | Methods (corpus) | `docs/specs/obj4-readiness-audit.md` §7 |
| 2026-09-14 | Deviation | Labelling rulebook written down; checkpoint schedule set | No document defined Same and Different | Methods (annotation) | `PREREGISTRATION_OBJ4.md` §12; `docs/specs/labelling-rulebook.md` |
| 2026-09-12 | Deviation | Rejected page attempts enter the corpus; held-out size, non-human endpoint, slice source and a split contradiction settled | The judge is used on candidate pages, not only on final ones | Methods (corpus, splits) | ADR-060; `PREREGISTRATION_OBJ4.md` §12 |
| 2026-09-04 | Scope | Narration and PDF export cut; the Objective 5 item naming them corrected, pending adviser sign-off | Neither was built | Methods (system), Instruments | ADR-058; `research_instruments.md` |
| 2026-09-03 | Limitation | Stated body counts ("six legs") are a documented limitation | No tested model draws them reliably | Limitations | ADR-056 |
| 2026-09-03 | Decision | A prompt change is judged by its rate over many pages, never by one page | One page can look good by luck | Methods | ADR-055 |
| 2026-09-03 | Deviation | Hard-negative coverage made best-effort; matching rules unchanged | Completeness was a code rule, not a registered one | Methods (datasets) | ADR-057; `PREREGISTRATION_OBJ4.md` §12 |
| 2026-09-01 to 03 | Decision | Pipeline behaviour refined: judge inputs, references only for characters a scene contains, objects described on fixed axes, one retry for the reference judge, judge provider pinned | Each ADR records its own reason | Methods (system) | ADR-045 to ADR-054 |
| 2026-08-29 | Deviation | One rater with test-retest agreement. Superseded on 2026-09-23 | The researcher was the only rater | Methods (annotation) | `PREREGISTRATION_OBJ4.md` §12 |
| 2026-08-22 to 25 | Deviation | Each story fixed to one style preset; splits assigned at intake; execution pins and the reporting schema fixed | Closing open choices before data existed | Methods (corpus, analysis) | `PREREGISTRATION_OBJ4.md` §12 |

## 4. How to keep this current

When a decision, deviation, finding or limitation lands:

- add a row at the top of the changelog table;
- update section 1 if the paper must say something new;
- update [`group-guide.md`](group-guide.md) if the current state changed.

Unpushed git commits do not define this log. It tracks the research since registration.
