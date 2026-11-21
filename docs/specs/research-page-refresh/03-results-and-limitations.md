# 03 — Results and limitations pages

Index: [../research-page-refresh.md](../research-page-refresh.md). Current code:
`(reference)/results/*` and `(reference)/limitations/*`. Data:
`data/judge/evaluations/obj4-v1/heldout-1/qwen_comparison.partial.json`,
`sensitivity_and_agreement.json`, `data/judge/evaluations/obj4-v1/validation_checkpoint_scores.csv`.
Source docs the page tests pin to: `docs/capstone/research_runbook.md`, `group-guide.md` §5.2,
§5.4, §6, `model-probes-2026-10.md`. Starting draft copy: `evidence/audit-2-results.md` §(b).

**Never run** `score_*` or any script that appends to `test_access.jsonl`. Derived figures come
from the stored counts.

**Measured on 2026-11-21** (329 held-out pairs: 47 Different, 282 Same; a "positive" means the judge
says Different):

| Judge | Said Different | Caught | False alarms | Missed | Unreadable | F1 |
|---|---|---|---|---|---|---|
| Untrained base | 76 | 29 | 47 | 18 | 3 | 0.472 |
| Seed 1 (picked in advance) | 11 | 9 | 2 | 38 | 40 | 0.310 |
| Seed 0 | 14 | 11 | 3 | 36 | 44 | 0.361 |
| Seed 2 | 68 | 24 | 44 | 23 | 8 | 0.417 |

The false positive, false negative and F1 values were read from `qwen_comparison.partial.json`.
The other columns come from `evidence:audit-2-results.md`.

## US-10 Read the result without an ML background

As a non-ML groupmate, I want the judge result in plain words with its numbers, so that I can
repeat it in the paper without overstating it.

Applies: SH-02, SH-03, SH-09

- **AC-01** The page opens with a "How to read this page" box defining these terms in this
  project's sense:
  - a catch
  - a miss: in the app, a page with the wrong-looking character reaches the child
  - a false alarm: in the app, an unneeded redraw, which costs more and makes the book slower
  - precision, recall, F1 (the main measure, fixed before results)

  Draft: B-1.
- **AC-02** "What the scores show" is replaced with B-2, including this sentence verbatim:
  > "The fine-tuned judge raises far fewer false alarms (2 vs 47) because it rarely says
  > 'different' at all. As a result it misses most real character changes (38 of 47 vs 18 of 47),
  > and 12% of its answers could not be read. On the main score, F1, it is worse (0.31 vs 0.47)."
- **AC-03** An accuracy table includes the "answer Same every time" baseline (85.7%) and says why
  accuracy is not the headline measure. Draft: B-3. Its derived values go into the runbook's
  "Derived from the table" paragraph first.
- **AC-04** McNemar is explained in words (B-4): p = 0.0035 shows which judge was right on more
  pairs. Seed 1 was wrong on fewer pairs (40 vs 65), mostly by answering Same. The F1-gap interval
  (−0.36 to +0.003) just reaches zero.
- **AC-05** The page says the comparison is **partial**: the prompted Gemma baseline was not scored
  (authentication failure), paid evaluation stopped, and no gate decision was made.
- **AC-06** The sentence that unreadable answers are "part of why their recall is low"
  (`page.tsx:337`) becomes "may lower their recall". It also says nobody counted how many unreadable
  answers fell on Different pairs (B-6).
- **AC-07** The page promises no ROC, precision-recall or threshold curve. The trained judges output
  a verdict with no score (AUROC is null in the result file).

## US-11 Why seeds 0 and 1 behave this way (validation only)

As a groupmate, I want the measured checkpoint finding, so that the paper's discussion uses it
instead of a guess.

Applies: SH-02

- **AC-08** The "possible explanation" bullet (`page.tsx:447`) is replaced with B-5:
  - Seeds 0 and 1 got checkpoint 40 through the tie rule.
  - The tied alternatives (checkpoints 80 and 110) had 0 unreadable validation answers, against 13
    and 8.
  - Unreadable rates on the test set follow the validation ones.
  - From checkpoint 130 on, seeds 0 and 1 answered Same on almost every validation pair.

  It is labelled as a lead, not a tested cause. The source is `validation_checkpoint_scores.csv`.
  This needs a runbook entry and a changelog row replacing "too few to call it a pattern".

## US-12 What we recommend

As a groupmate writing Conclusion and Recommendations, I want the recommendations the data
supports, so that the paper's last chapter rests on the results.

Applies: SH-02, SH-03

- **AC-09** A new "What we recommend" section holds B-7's five items:
  1. Keep prompted Gemma, a no-change decision: Gemma was not scored on this test set.
  2. Reject checkpoints with many unreadable answers, and enlarge validation's Different class.
  3. Record the judge's full answer text.
  4. Fix the constructed-pair sentence shared by 104 training pairs.
  5. Report the result in the bounded wording of `research-changelog.md` §1 item 4.

  Items 2–4 are marked as drawn from measured facts but untested as fixes.

## US-13 Downloadable result charts

As a groupmate, I want the result charts as images, so that I can put them in the paper.

Applies: SH-06

- **AC-10** Charts produced as PNGs (by the US-22 export):
  - confusion matrices for the base and seed 1
  - F1, precision and recall bars with the F1 interval
  - validation F1 and unreadable count by checkpoint per seed, with ties marked
  - catches vs false alarms per judge
- **AC-11** Each chart's values come from the page's own data module, so the chart and the table
  cannot disagree.

## US-14 Limitations page up to date

As a groupmate writing Results 3.2 and the limitations, I want the limitations as of November, so
that the paper doesn't describe fixed or overstated problems.

Applies: SH-02, SH-03, SH-06

- **AC-12** "Finds most bad references" is replaced with the counts: the reference check fails 15 of
  17 bad references but also 15 of 38 good ones (ADR-082: about 4 in 10 clean references wrongly
  fail). Draft: B-8.
- **AC-13** It adds the November state (B-9):
  - The chip-words-only reference edit probe failed: 2 of 9 fixed, against 5 of 9 with hand-written
    instructions.
  - The magic pencil (ADR-082) shipped and is on by default. Whether children's own wording fixes
    references is unmeasured.
  - Generation versions 6 and 7 and 500-word stories are unmeasured.
- **AC-14** It adds two missing limitations:
  - The reference check cannot verify stated details, such as a red comb against a "metal comb"
    spec (ADR-056).
  - The stricter moderation backstop stopped 4 of 30 synthetic stories that the primary check
    cleared. There is no sentence about human review (D-23).
- **AC-15** Smaller fixes (B-10):
  - "About 13% of page images" says it counts redrawn drafts; on finished pages it is 15 of 150.
  - The klein bars say "duplicate or extra".
  - The klein screen's single rater is named as the AI assistant.
- **AC-16** The page-check counts explain the 2 uncertain pages, so 77 + 71 + 2 = 150
  (`evidence:audit-5-render.md#F7`).
- **AC-17** Reference-check and page-check outcome charts are exported as PNGs (US-22).
