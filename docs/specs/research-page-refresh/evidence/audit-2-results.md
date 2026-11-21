# Audit 2: /research/results and /research/limitations (2026-11-21)

Read-only. No repo file edited. Paths are relative to `C:\Users\Asus\Desktop\story-buddy`.
R = `frontend/app/(research)/research/(reference)`.

## Bottom line

- **Every number on both pages matches its cited doc, and every judge number matches the local result JSON.** `npx vitest run` on both folders: 4 files, 36 tests passed. I compared the confusion counts, F1, CIs, ΔF1, McNemar, seed mean/SD and validation F1 field by field against `data/judge/evaluations/obj4-v1/heldout-1/qwen_comparison.partial.json` and `sensitivity_and_agreement.json`. No mismatch. Nothing on either page is **wrong** as a number.
- **The problems are framing, missing context and staleness:**
  1. **"Seed 1 is more careful" is not a finding.** It misleads the way the owner feared. What was measured: seed 1 says Different on only 11 of 329 pairs (untrained: 76). So its few flags are mostly right (9 of 11), but it catches only 9 of 47 real mismatches. It also gives unreadable output on 40 of 329 (12%).
  2. **New measured evidence the page does not have.** Per-checkpoint validation scores show why seeds 0 and 1 got checkpoint 40. Each tied on validation F1 with a later checkpoint that had **zero** unreadable answers (seed 1: ckpt 40 vs ckpt 110; seed 0: ckpt 40 vs ckpt 80). The registered tie-break ("earlier step wins") picked the checkpoint with 8 and 13 unreadable answers out of 86. The page and changelog still say "three runs are too few to call this a pattern".
  3. **Unsupported causal sentence.** "Unreadable answers … part of why their recall is low" has never been checked. It is unknown how many of the 40 unreadable answers fell on the 47 Different pairs.
  4. **Limitations page is stale since 2026-11-01.** The tap-wording-as-edit probe failed (2 of 9). ADR-082's magic pencil shipped and is on by default since 2026-11-21. Neither appears on the page.
  5. **The reference check is described as finding "most bad references".** It fails 15 of 17 defective references and also 15 of 38 acceptable ones. ADR-082 itself says it "wrongly fails about 4 in 10 clean references".
- **The paper draft has the numbers right** (accuracy 80.2/87.8, specificity 83.3/99.3: I recomputed both). It needs four fixes:
  - It leans on accuracy, which the preregistration bans as a headline ("Never accuracy", `PREREGISTRATION_OBJ4.md:222`). Always answering Same already scores 85.7%.
  - It reads McNemar as "statistically significant difference", which the changelog says not to do without the direction.
  - It never says the comparison is partial (no Gemma baseline).
  - It says the fine-tune "was not deployed as a replacement for Gemma", but Gemma was never scored on this test set.

### One rule for both pages: what a "positive" is

In this project the **positive class is "Different character"** (`evaluate.py`; runbook line ~333: "Agreement treats 'different character' as the positive class"). Positive means "the judge raises a problem".

- **False alarm (false positive):** the human raters said Same, but the judge said Different. In the product, this causes an unnecessary redraw: paid images and slower books.
- **Miss (false negative):** the raters said Different, but the judge said Same or gave unreadable output. In the product, a page with the wrong-looking character reaches the child.
- **Precision:** of the pairs the judge flagged, the share that really were Different.
- **Recall:** of the 47 really-Different pairs, the share the judge flagged.
- **F1:** one number that is high only when both precision and recall are high.

The limitations page's page check and reference check use the same idea ("failed" = flagged), so both pages should use the same two words.

---

## (a) Findings table

Labels: **measured** = read from data or a command; **inferred** = my reasoning on measured values; **inconclusive** = could not be checked.

| id | Page / location | Issue | Evidence | Label | Severity |
|---|---|---|---|---|---|
| R1 | results/data.ts, all `JUDGES`, `COMPARISON`, `SEEDS`, `SENSITIVITY`, `AGREEMENT` | All values match the local JSON (e.g. seed_1 tp 9, fp 2, fn 38, tn 280, parse_failures 40; delta_f1 −0.16120, CI [−0.35816, 0.00344], McNemar 0.003545; seeds mean 0.36280, SD 0.05356; sensitivity untuned 0.476/0.391/0.610 with tp 25, fp 39). No action. | `heldout-1/qwen_comparison.partial.json`; `heldout-1/sensitivity_and_agreement.json`; vitest 36/36 pass | measured | none |
| R2 | results "What the scores show", bullet 2 (`page.tsx:193`), from group-guide §5.2 "more careful" | "Seed 1 is more careful" reads as "better / safer". The measured behaviour is that it almost never says Different: 11 flags vs 76 (prediction_rate 0.033 vs 0.231). High precision comes from flagging little, on n=11 flags (rough Wilson 95% 0.52–0.95, not the registered method). | JSON `prediction_rate`; arithmetic tp+fp | measured (rate) / inferred (CI) | confusing |
| R3 | results "Unreadable answers", `page.tsx:337` and group-guide §5.2 | "…which is part of why their recall is low" is stated as fact. How many unreadable answers fell on Different pairs was never counted. The local prediction files hold no raw output text. Counting it needs test labels, and the runbook treats reading those as a test access (ledger event). | runbook "Held-out resume context" (checksum-only audit "does not read test labels"); changelog 2026-10-11 Limitation "Whether the unreadable answers were cut off was not checked"; validation jsonl fields: no output text, `latency_ms` null on malformed rows | inconclusive | confusing (unsupported claim) |
| R4 | results "Possible explanations", checkpoint bullet (`page.tsx:447`) | **Stale / missing.** Validation ties existed, and the tie-break picked the checkpoint with more unreadable output. Seed 1: ckpt 40 and ckpt 110 both TP 2, FP 3, FN 2, F1 0.444; malformed **8** vs **0**. Seed 0: ckpt 40 and ckpt 80 both F1 0.333; malformed **13** vs **0**. Seed 2 ckpt 140: malformed 2. Rule: "Highest validation F1 per seed; ties choose earlier optimizer step". Test unreadable rates follow the validation ones: 13.4%, 12.2%, 2.4% on test vs 15.1%, 9.3%, 2.3% on validation. This is training/validation-only evidence, so prereg §7 allows it for debugging. It does **not** permit reselecting a checkpoint on test. | `data/judge/evaluations/obj4-v1/validation_checkpoint_scores.csv`; `validation_scores.json` `selection_rule`; `validation/seed1_checkpoint40.jsonl` (78 parsed / 8 malformed) vs `seed1_checkpoint110.jsonl` (86 parsed) | measured | stale / missing |
| R5 | results, training section | Later checkpoints of seeds 0 and 1 collapse toward always-Same on validation: TP 0, FP 2, FN 4 at every checkpoint from 130 to 183 (seed 0 also at 120). Seed 2 keeps recall 0.5 with many false alarms. So "train longer" would not have fixed seeds 0 and 1 on this evidence. Not on page or in paper. | `validation_checkpoint_scores.csv` | measured | missing |
| R6 | results "The registered comparison" bullets (`page.tsx:361-363`) | "The interval of the gap includes zero. It just touches it." is correct but gives no reading. Plain reading: F1 fell by 0.16. The interval (−0.358 to +0.003) is almost entirely below zero, so there is no sign of improvement. Strictly, a decline is not established either. | JSON `primary_comparison` | measured | confusing |
| R7 | results, no accuracy / false-alarm rate / miss rate | The paper reports accuracy and specificity. The page has neither. It also lacks the always-Same baseline that makes accuracy readable: 282/329 = **85.7%**. Seed 1's 87.8% is 2.1 points above saying Same every time. Rates: false-alarm rate 16.7% untrained vs 0.7% seed 1. Miss rate 38.3% vs 80.9%. | arithmetic on JSON counts; prereg `PREREGISTRATION_OBJ4.md:222` "Never accuracy" | measured | missing |
| R8 | results, judge-vs-human agreement | JSON stores Cohen's κ of each judge against the adjudicated labels: untrained 0.358, seed 0 0.316, seed 1 0.271, seed 2 0.299. This is another chance-corrected view that also favours the untrained model. Not on page or in paper. | `qwen_comparison.partial.json` `judges.*.cohen_kappa` | measured | missing (optional) |
| R9 | results, no ROC/PR or threshold curve | **Not possible for the Qwen judges.** They give a binary verdict with no score: `auroc` null, reason "scores contain None"; calibration "confidences missing". Only CLIP/DINO controls have thresholds (validation F1 0.130 / 0.100). Their held-out captures exist (329 rows each) but no tracked doc scores them. | JSON `auroc`, `calibration`; `validation_scores.json` `controls`; runbook "Held-out resume context" | measured | missing (explain why absent) |
| R10 | results, false alarms concentrated on one character | Dropping the one ambiguous test character (20 pairs: 6 Different, 14 Same) removes 8 of the untrained model's 47 false alarms (47→39), 10 of seed 2's 44, and none of seed 1's. Every judge's unreadable count is unchanged by the drop. | `sensitivity_and_agreement.json` vs primary JSON | measured | missing (useful for error analysis) |
| R11 | results "What the result does not show", rater bullet | κ 0.634 / 89.7% correct. Page omits the sensitivity-slice κ 0.709 and the all-pairs κ 0.659. Fine as is. Paper calls κ 0.634 "considerable". The usual Landis–Koch band for 0.61–0.80 is "substantial". | runbook table; JSON | measured / inferred (scale name) | minor |
| R12 | results "Possible explanations", "The LoRA did nothing" bullet | Correct and well sourced. Add the always-Same drift (R5) as the measured shape of "changed the output". | changelog 2026-10-11 Finding | measured | minor |
| R13 | results, cost/latency | JSON holds per-call latency (mean 5.6 s untrained vs 4.1 s seed 1, 3.3 s seed 2) and cost is null ("not recorded in immutable prediction evidence"). The page states no cost, correctly. | JSON `latency_ms`, `cost_per_call_usd` | measured | missing (optional, ISO 25010 performance) |
| R14 | results lead (`page.tsx:93`) "on this run" | There were three runs. Say "in this training setup". | page text | measured | minor |
| L1 | limitations, all numbers | Every number matches group-guide §5.3–§6, stage audit, model-probes. Tests pass. The klein totals check out against the raw blinded scores (dup 3+5 = 4+4, identity 7+6 = 3+10). Per-arm counts need the unblinding key, which is not in that folder. | vitest; `data/judge/evaluations/klein-screen-2026-10/scores-blind.json` | measured (totals) / inconclusive (per arm) | none |
| L2 | limitations "Automatic checks", reference card text "The check finds most bad references" | Half-true. The reference check fails 15/17 defective **and** 15/38 acceptable (39%). Overall it fails 30 of 55 references. ADR-082 states it as "wrongly fails about 4 in 10 clean references". The page only says it next to the bar. | stage audit "References"; `docs/product/adr/ADR-082-…md:23` | measured | confusing |
| L3 | limitations "Automatic checks", page card | Same issue with no summary sentence. The page check lets 29 of 77 defective pages through (miss 38%) and fails 28 of 71 acceptable pages (false alarm 39%). Also, 23 of the 71 rejected first draws were acceptable, which is a measured cost of false alarms that the page omits. | stage audit "Page gate" | measured | confusing / missing |
| L4 | limitations "What was tried in October" + limitation "Stated body counts" | **Stale.** The 2026-11-01 probe "tap wording as an edit" failed: 2 of 9 vs the 6-of-9 rule (hand-written instructions had 5 of 9). ADR-082 then shipped the magic pencil, an edit from the child's own words, with "children's wording … untested". The page still ends at "Not adopted yet: it needs a test with automatic instructions and an ADR." | `docs/capstone/model-probes-2026-10.md` "Tap wording as an edit: result"; ADR-082 lines 22-24, 52, 59; changelog 2026-11-02 and 2026-11-21 rows | measured | stale |
| L5 | limitations "Duplicate characters": "About 13% of page images" | Source is 28 of 221 page images, including 71 rejected first draws, `duplicate_character` only. Shipped pages: 15/150 = 10%; duplicate or extra on shipped pages: 17/150 = 11.3%. "Page images" without "including rejected draws" will be read as "pages in a book". Also, the stage audit says "216 page images" but `key.json` has 221 (150 final + 71 rejected_first) plus 55 refs = 276. | `model-probes-2026-10.md:948`; `pipeline-stage-audit-2026-10.md` "Duplicates"; `stage-audit-2026-10/key.json` count | measured | confusing (and a doc inconsistency: 216 vs 221) |
| L6 | limitations "Scene editors", klein bars titled "Pages with a duplicate character" | The scored field is "duplicate **or extra** (major)". Label understates it. The klein screen's action count (Qwen 2, klein 8) and "no defect" (20 vs 13) are omitted. | `model-probes-2026-10.md` klein result table | measured | confusing (minor) |
| L7 | limitations "Scene editors" klein text "scored with the editor's name hidden" | Does not say the one rater was the AI assistant ("one rater (Claude), blind to arm"). The page's provisional banner covers the audit only, not the klein screen. | `scores-blind.json` `rater` field | measured | missing |
| L8 | limitations top banner "The owner has not confirmed the scores" | True, but there is more: the owner skipped the confirmation sheet. The assistant spot-checked 7 flagged items (all agreed), which tests precision only. | stage audit "Deviation — owner confirmation" | measured | minor |
| L9 | limitations totals | 77 defective + 71 acceptable = 148. The 2 uncertain pages are not mentioned. | stage audit "Shipped pages" | measured | minor |
| L10 | limitations "Characters with no reference" | Says "once drew them as human boys". The page's own example (syn-016 s2 attempt 4) shows green-skinned helmeted humanoid soldiers. I viewed the image. Both are true of different draws, but readers will compare them. Also missing the measured rate: scenes that direct unrostered beings ship a duplicate or extra on 24% of pages vs 10% elsewhere (17 of 150 scenes). Generation version 7 (2026-10-13) changed the background-group rule, untested. | `model-probes-2026-10.md:948` table row; changelog 2026-10-13; `frontend/public/research/dataset/1843d7d4835a8397-page.webp` | measured | confusing / missing |
| L11 | limitations, missing limitation: reference judge cannot check stated attributes | Measured 2026-09-02/03: no off-the-shelf VLM named "red comb vs metal comb". On syn-002 the reference judge listed "six legs" as present on a four-legged drawing. ADR-056: the ADR-018 fine-tune does not cover this, because consistency pairs compare page to reference, not reference to text. The page shows the effect (reference_inherited, 34 pages) but not this cause. | `docs/capstone/reference_judge_investigation_2026-09-02.md`; ADR-056 | measured | missing |
| L12 | limitations, missing limitation: moderation backstop over-refusal | 4 of 30 synthetic stories were quarantined when the backstop flagged scenes the primary cleared (`backstop (primary said safe) after retry`). Refusal was stochastic: syn-017 s0 passed on the 4th round with no change. fal's checker separately refused 3 more (including *The Red Shoes*). The doc says "human review upheld the primary in all four". My memory notes say the owner inspected 2 of the 4 (syn-022, syn-027): check before quoting "all four". | `docs/specs/obj4-readiness-audit.md:1280-1290` | measured (counts) / inconclusive ("all four reviewed") | missing |
| L13 | limitations, missing scope limits after 2026-10-11 | Unmeasured since the audit: 500-word inputs (ADR-068, "quality at the larger input ceiling is unmeasured"), generation versions 6/7 (retry identity signals, cast count), the magic pencil. The audit describes generation v4. | changelog 2026-10-11, 2026-10-13, 2026-11-02 rows | measured | stale |
| L14 | limitations "The judge result" item | One line, with no numbers and no link to the tradeoff. See copy B-4. | `limitations/data.ts` LIMITATIONS[5] | measured | confusing |
| X1 | both pages: update path | Both pages copy their source docs word for word and tests enforce it (ADR-066/067; `data.test.ts`). Any copy change below must land in `group-guide.md` §5.2/§5.4/§6, the runbook, or `model-probes` first, then on the page. `AGENTS.md:225` also says not to restate numbers elsewhere. | `R/results/data.test.ts`, `R/limitations/data.test.ts` | measured | process note |

---

## (b) Proposed content changes with draft copy

All copy below uses only measured values. The plain-language sentences are written so a non-ML groupmate can repeat them.

### B-1. Results page: a definitions box at the top (new, before the charts)

> **How to read this page.** The judge looks at a character's reference picture and one book page and answers **Same** or **Different**. Raising a problem means answering Different.
> - A **catch**: the people who labelled the pair said Different, and the judge said Different.
> - A **miss**: the labellers said Different, but the judge said Same, or its answer could not be read. In the app, a page with the wrong-looking character would reach the child.
> - A **false alarm**: the labellers said Same, but the judge said Different. In the app, this means an unnecessary redraw: more cost and a slower book.
> - **Precision**: of the pairs the judge flagged, how many were really Different.
> - **Recall**: of the 47 really-Different pairs, how many the judge flagged.
> - **F1**: one score that is high only when both are high. It is the main number, chosen before the results were seen.

### B-2. Results page: replace the "What the scores show" bullets (and group-guide §5.2 "In plain words")

> - **The untrained model catches more.** It flagged 29 of the 47 Different pairs (62%). Its cost was 47 false alarms out of 282 Same pairs (17%).
> - **The trained judge picked in advance (seed 1) almost never says Different.** It said Different on 11 of 329 pairs, against the untrained model's 76. Most of those 11 were right (9; precision 0.82), so it raised only 2 false alarms (under 1%). But it caught only 9 of the 47 real differences (19%) and missed 38.
> - **Fewer false alarms came with far more misses.** Seed 1 went from 47 false alarms to 2, but from 18 misses to 38. On F1, which counts both, it scores 0.31 against 0.47.
> - **Its answers are also less often usable.** Seed 1 gave unreadable output on 40 of 329 pairs (12%), against 3 for the untrained model. Unreadable output is scored as Same.
> - **Seed 0 behaves like seed 1.** Seed 2 behaves like the untrained model (68 flags, 44 false alarms, 24 catches), with slightly lower scores. No trained run beat the untrained model on F1.

The sentence the owner asked about, made correct:
> "The fine-tuned judge raises far fewer false alarms (2 vs 47) because it rarely says 'different' at all. As a result it misses most real character changes (38 of 47 vs 18 of 47), and 12% of its answers could not be read. On the main score, F1, it is worse (0.31 vs 0.47)."

Do **not** write "more careful", "more reliable", "more accurate" or "less reliable" without saying in what way. "Less reliable" is only supportable in two concrete senses: it catches fewer real problems, and more of its answers are unreadable.

### B-3. Results page: accuracy, with its baseline (new small table under the main table)

| Judge | Accuracy | Same pairs judged correctly (specificity) | False-alarm rate | Miss rate |
|---|---|---|---|---|
| Answering Same every time | 85.7% | 100% | 0% | 100% |
| Untrained | 80.2% | 83.3% | 16.7% (47/282) | 38.3% (18/47) |
| Seed 1 | 87.8% | 99.3% | 0.7% (2/282) | 80.9% (38/47) |
| Seed 0 | 88.1% | 98.9% | 1.1% (3/282) | 76.6% (36/47) |
| Seed 2 | 79.6% | 84.4% | 15.6% (44/282) | 48.9% (23/47) |

> Accuracy is not the main measure, because 86% of test pairs are Same. A judge that never raises a problem would score 85.7%. Seed 1's higher accuracy comes from answering Same more often, not from finding problems.

These are arithmetic on the runbook table. Add them to the runbook "Derived from the table" paragraph first (X1).

### B-4. Results page: the registered comparison, in words (replace the three bullets at `page.tsx:361-363`)

> - Seed 1's F1 is 0.16 lower than the untrained model's.
> - The 95% interval of that gap runs from −0.36 to +0.003. It is almost all below zero, so there is no sign that training helped. Strictly, it also does not prove training made things worse, because the interval just reaches zero.
> - McNemar's test (p = 0.0035) asks which judge was right on more pairs. Seed 1 was wrong on fewer pairs (40 vs 65), mostly by answering Same on a test set where most pairs are Same. It does not mean seed 1 finds problems better.

### B-5. Results page: replace the checkpoint "Possible explanation" bullet (`page.tsx:447`) with the measured tie

> Each seed's checkpoint was the one with the best F1 on the validation pairs, with ties going to the earlier checkpoint (rule fixed in advance). For seeds 0 and 1 there **was** a tie. Seed 1's checkpoint 40 and checkpoint 110 had the same validation counts (2 caught, 3 false alarms, 2 missed). But checkpoint 40 gave 8 unreadable answers out of 86, and checkpoint 110 gave none. Seed 0's checkpoint 40 tied checkpoint 80 (13 unreadable against none). The rule picked the earlier one both times. On the test set these two seeds then gave the most unreadable answers (40 and 44 of 329). Seed 2's checkpoint had 2 unreadable on validation and 8 on test. This is a lead, not a tested cause: the test set may not be used to pick again.
> Later in training, seeds 0 and 1 drifted to answering Same on almost every validation pair: from checkpoint 130 on, they caught none of the 4 Different pairs.

Also update changelog row 2026-10-11 ("Three seeds are too few to call it a pattern") with a new 2026-11 Finding row citing `validation_checkpoint_scores.csv`.

### B-6. Results page: fix the unreadable sentence (`page.tsx:337`, group-guide §5.2)

> Seeds 0 and 1 gave unreadable answers on about one pair in eight. An unreadable answer on a Different pair counts as a miss, so this **may** lower their recall. How many of them fell on Different pairs was not counted.

### B-7. Results page: a "What we recommend" section (new; the page has none)

> 1. **Keep the production judge (prompted Gemma).** The trained judge did not beat its own untrained base. Gemma itself was not scored on this test set (its run failed authentication), so this is a decision to make no change, not a measured win for Gemma.
> 2. **Before any further training run, change how checkpoints are chosen.** Reject checkpoints whose answers often cannot be read (seeds 0 and 1 had 8–13 of 86 on validation). The validation set also needs far more than 4 Different pairs.
> 3. **Record the judge's full answer text**, so unreadable answers can be diagnosed (cut off at 256 tokens or badly formatted). The saved files keep only the parsed verdict.
> 4. **Fix the training data first.** 104 of the 157 Different training pairs carry the same script-written sentence. Training is synthetic, testing is donated, mostly human.
> 5. **Report the result as bounded.** "Under the evaluated dataset, training settings and inference constraints, fine-tuning did not demonstrate a reliable improvement over the untuned baseline" (changelog §1 item 4).

Items 2–4 are recommendations drawn from measured facts. Whether they would fix the result is untested (inferred).

### B-8. Limitations page: "Automatic checks" card text (L2/L3)

Reference card:
> The check fails most bad references (15 of 17), but it also fails about 4 in 10 good ones (15 of 38). The pipeline then ships the best of the failing draws, so every defect it found still reached the pages.

Page card:
> The page check let 29 of the 77 defective pages through (missed) and failed 28 of the 71 acceptable ones (false alarms). 23 of the 71 redrawn first drafts were already acceptable. A mistake copied from the reference matches the reference, so it passes.

### B-9. Limitations page: update the "Stated body counts" limitation and the "What was tried" table (L4)

New row in TRIED (group-guide §5.4 first):
> | Editing the reference with only the tapped chip's words (November 1) | 2 of 9 fixed, against 5 of 9 with hand-written instructions. Failed its 6-of-9 rule. A tap stays a fresh draw. | Rejected |

Replacement "Stated body counts" body:
> "Six legs" or "seven stripes" usually come out wrong, and no tested model draws them from text (ADR-056). The reference check cannot reliably catch them either: it once listed "six legs" as present on a four-legged sheep. Editing the finished reference fixed 5 of 9 with hand-written instructions, but only 2 of 9 with the chip's own words. Since November the magic pencil lets a child request such an edit in their own words. Whether children's wording works is unmeasured; every use is logged.

Retitle the section "What was tried in October and November".

### B-10. Limitations page: smaller fixes

- L5: "About 13% of page images, counting redrawn drafts (28 of 221), show a character twice. On finished pages it is 15 of 150."
- L6: Bar title "Pages with a duplicate or extra character". Add a sentence: "klein also missed the action on 8 of 30 pages, against 2 for Qwen."
- L7: Add "Scored by one rater, the AI assistant, with the editor hidden."
- L9: "77 of 150 have a major defect, 71 are acceptable and 2 are uncertain."
- L10: Add "Scenes that call for such a group ship a duplicate or extra character on 24% of pages, against 10% elsewhere." Make "human boys" consistent with the shown example, or say "in another draw".
- L11/L12: Two new LIMITATIONS items (via group-guide §6 first):
  > **The reference check cannot verify stated details.** Off-the-shelf vision models tested in September could not tell that a "metal comb" was drawn red, and one listed "six legs" as present on a four-legged drawing. The trained judge would not fix this: it compares pages with references, not references with the story text.
  >
  > **Safety checks sometimes refuse harmless stories.** In the corpus run, the stricter of the two image checks stopped 4 of 30 synthetic stories that the main check had cleared. The same scene could pass on a later try with no change. A third checker at the image provider refused 3 other stories, including a classic fairy tale.
- L13: In the provisional banner, add "These pages were drawn with generation version 4. Changes since (versions 6 and 7, 500-word stories, the magic pencil) are not measured here."
- L14: Replace the "The judge result" item body:
  > Objective 4's result is partial: the prompted Gemma baseline was not scored. The trained judge raised fewer false alarms but missed most real differences, and scored lower F1 than the untrained model (0.31 vs 0.47).

### B-11. Graphs that should be downloadable PNGs (for the paper)

Both pages draw charts with CSS bars, which cannot be saved as figures. Add a "Download PNG" for:
1. **Confusion matrices**, 2×2 per judge (untrained and seed 1 at minimum). Paper Table X has the counts but no figure.
2. **F1 / precision / recall grouped bars with the F1 interval whisker**, four judges. The paper's "Fig. Y" placeholder needs this.
3. **Validation F1 and unreadable count by checkpoint, one line per seed**, with selected checkpoints and ties marked. Source: `validation_checkpoint_scores.csv`. It is the only curve the data supports, and it shows B-5.
4. **Flags vs catches**: per judge, "said Different" (76/11/14/68) split into catches and false alarms. It makes the "rarely says Different" point at a glance.
5. Limitations: **check outcomes** (reference and page gate, miss vs false alarm) and **defects by character kind**.

Do not promise an ROC, PR or threshold curve for the Qwen judges: there are no scores to sweep (R9). Say why on the page in one line.

---

## (c) Paper-sync notes (paper.md "Results working draft" and chapters)

| # | Paper location | Issue | Fix |
|---|---|---|---|
| P1 | Untrained vs fine-tuned, Table Y and text "despite its higher accuracy" | Numbers are correct (recomputed: 264/329 = 80.2%, 289/329 = 87.8%, 235/282 = 83.3%, 280/282 = 99.3%). But the preregistration says F1 is primary, "Never accuracy" (`PREREGISTRATION_OBJ4.md:222`), and no baseline is given. | Add the always-Same row (85.7%) and the B-3 sentence. Drop "fine-tuning improved overall accuracy" from the Analysis section, or qualify it. |
| P2 | Analysis: "McNemar's exact test … indicating a statistically significant difference in overall classification correctness" | Accurate but undirected. Changelog §1 item 4 says report it beside the counts and never as "worse/better detector". | Use B-4 bullet 3. |
| P3 | Analysis: "Since the confidence interval included zero, the results did not establish a statistically reliable improvement" | The estimate is a decline. Wording implies an improvement was nearly shown. | Use B-4 bullets 1–2. |
| P4 | Whole results draft | Never says the comparison is **partial**: prompted Gemma failed authentication and the seven-comparator report is incomplete. CLIP/DINO captured but unscored. | Add one paragraph (runbook "Held-out resume context"; changelog §1 item 3). |
| P5 | Final paragraph: "not deployed as a replacement for the existing Gemma 3 27B Consistency Judge" | Gemma was not evaluated on this test set, and per the results page "No formal decision under that rule was recorded". | "The fine-tuned model was not adopted. The production judge stays the prompted Gemma model, whose accuracy on this test set was not measured." |
| P6 | Model Validation and Checkpoint Selection | Omits the tie rule ("ties choose the earlier step") and its effect (B-5). Omits that the untrained model was never scored on validation. | Add both. Add the per-checkpoint figure (B-11 item 3). |
| P7 | Errors table note / unreadable paragraph | Good and properly hedged ("do not establish … how much they contributed"). The page is less careful (R3). Keep the paper's wording and fix the page. | none in paper |
| P8 | Limitations paragraph | Missing the constructed-pair sentence (104 of 157 Different training pairs share one script-written reason), the 256-token cap, the 2 contradicting constructed pairs (4 of 484 records), raters briefed by the adjudicator, and the base-model change after registration (ADR-061). | Add from the results page "Possible explanations" and "does not show" lists. |
| P9 | Missing secondary analysis | The registered sensitivity analysis (drop ambiguous character; n = 309; ΔF1 −0.130, CI −0.333 to +0.053, McNemar 0.0075) is absent. | Add a short paragraph or table (runbook "Secondary sensitivity analysis"). |
| P10 | Inter-annotator section | "considerable level" → "substantial (Landis & Koch)". Typo "Cohen's Cappa". Optionally add all-pairs κ 0.659 (n = 795) and the non-human κ 0 prevalence note. | — |
| P11 | Untrained vs fine-tuned text: "F1-score declined from 47.2% to 31%" | Mixes formats; 31% should be 0.310. | "from 0.472 to 0.310". |
| P12 | Error analysis | Could add R10 (8 of the untrained model's 47 false alarms are on one ambiguous character) and judge-vs-human κ (R8). Optional. | — |
| P13 | RESULTS 3.1/3.2 and limitations | Page-defect findings (77 of 150, provisional, AI-assisted, synthetic only) and the checks' miss/false-alarm rates have no slot yet. The changelog §1 item 7 says these are limitations, not results. | Put them in the limitations of 3.2 with the provisional label. |
| P14 | Dataset section | Consistent with the runbook (899 / 795 / 104; 484 = 380 + 104; 86; 329). No issue. | — |
| P15 | Source doc inconsistency (not paper) | Stage audit says "216 page images". `key.json` holds 221, which matches model-probes. | Owner to correct the stage audit. |

### What I could not check

- **Recomputing metrics from raw predictions plus test labels.** `score_qwen_comparison.py` and `score_sensitivity.py` append a resume event to `test_access.jsonl` (repo write, and a test access). I checked the stored JSON and the arithmetic instead.
- **How many unreadable answers were on Different pairs** (R3). This needs test labels, so it is the owner's call whether that counts as a permitted reporting read.
- **Whether unreadable answers were cut off by the 256-token cap.** Prediction files store no output text, and malformed rows have no latency.
- **The 77/150 audit counts.** The per-item AI review scores are not in `data/judge/evaluations/stage-audit-2026-10/`. Only the key and confirmation lists are there.
