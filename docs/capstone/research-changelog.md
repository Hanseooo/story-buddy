# StoryBuddy: Research Changelog

**Last updated:** 2026-10-09 · **Covers:** everything since the Objective 4 pre-registration was frozen
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
8. **The product did not change its models.** The scene editor stays Qwen-Image-Edit (ADR-063). The
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
