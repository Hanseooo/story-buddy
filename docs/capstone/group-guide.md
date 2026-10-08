# StoryBuddy: Start Here (Group Guide)

**Last updated:** 2026-10-09 · **For:** group members who need the research context without reading
the code. Every statement below stands on its own. The repository paths in brackets are where the
evidence lives, for anyone who wants to check it.

What changed since registration, and what the manuscript must now say, is in
[`research-changelog.md`](research-changelog.md).

If this guide disagrees with the manuscript or with a file it cites, the other source wins and this
guide needs fixing.

---

## 1. What StoryBuddy is, in three sentences

A Grade 5–6 child writes a story. StoryBuddy turns it into an illustrated digital picture book
automatically, with no person editing any page. The research asks whether the characters stay
recognisable from page to page, especially invented, non-human characters like a sock dragon or a
three-eyed hedgehog, and whether experts find the books acceptable.

[`docs/capstone/research_direction_and_goals.md`]

## 2. The five objectives

| # | Objective | In plain words |
|---|---|---|
| 1 | Implement the AI pipeline | Build the system that makes the books |
| 2 | Produce picture books | Run it on real and synthetic stories |
| 3 | Determine acceptability through expert validation | Validators from the Arts and Education colleges judge the books' presentation and classroom suitability |
| 4 | Evaluate the fine-tuned judge | Measure how well a trained AI model tells "same character" from "different character", using precision, recall and F1 (F1 is the main number) |
| 5 | Evaluate software quality | IT practitioners and teachers rate the system on ISO/IEC 25010 qualities |

The study makes no claim that StoryBuddy is better than other methods and no claim about learning
gains. [`docs/capstone/research_direction_and_goals.md`, Objectives and §5]

## 3. How a book gets made

Each step runs automatically, in this order:

| Step | What it does |
|---|---|
| Input gate | Checks the story is safe and usable |
| Analyze | A text model reads the story and lists the characters, objects and places |
| Segment | Splits the story into scenes (pages) and writes a short drawing direction for each |
| Character bible | Draws one reference picture per main character, at most two characters |
| Reference moderation | Checks those pictures are safe |
| Reveal | Shows the references before the pages are drawn |
| Generate scene | Draws each page, using the reference pictures so characters look the same |
| Consistency check | An AI judge compares each page with the references |
| Regenerate | If the judge finds a mismatch, the page is redrawn with the reasons fed back, up to twice. The best of the (at most three) attempts is kept |
| Output moderation | Checks the pages are safe |
| Compose | Assembles the book |

**The models used today:**

- Text model: `mistral-small-3.2-24b-instruct`.
- Reference pictures: `fal-ai/qwen-image`.
- Pages (the "scene editor"): `fal-ai/qwen-image-edit-2511`.
- Judge in the product: a prompted `gemma-3-27b-it`.
- Judge being trained for Objective 4: `Qwen3.5-9B`.

All of them are open-weight models.

[`backend/app/config.py`, `backend/pipeline/graph.py`, `docs/product/adr/ADR-001-*`]

## 4. Where each objective stands (2026-10-08)

| Objective | Status |
|---|---|
| 1–2 | Built. The research corpus holds 42 generated books: 30 from synthetic stories and 12 from donated stories. |
| 3 | Planned (Tool B, a written open-ended interview form). The repository records no completed session yet. |
| 4 | Training done on three seeds. A **partial** held-out result exists (below). Paid evaluation stopped on 2026-10-07 for budget, and the Gemma baseline failed authentication, so the full registered report is incomplete. Since then the main work has been the page-drawing pipeline. |
| 5 | Planned (Tool C, the ISO/IEC 25010 questionnaire). The repository records no completed session yet. |

[`docs/product/ROADMAP.md` Phase 3 and C3-02, `docs/capstone/research_runbook.md` "Held-out resume context"]

## 5. What we have found so far

### 5.1 Reference pictures help invented characters (Phase 0.5, July 2026)

- On the scene editor StoryBuddy ships (Qwen-Image-Edit, Run 2), the invented hedgehog Quill stayed
  recognisable on 70% of pages with its reference picture, and on 40% without it.
- A second model tried as a backup (OmniGen2, Run 3) reached 80% against 30%.
- A realistic fox cub scored the same with or without its reference.
- Both runs failed the gate set in advance. Qwen-Image-Edit stayed the editor, and the failed gate is
  carried as a limitation.
- These numbers were a build check, scored without blinding. The results file says no Phase 0.5
  number may appear as a finding in the paper without a fresh, blind re-score by three or more raters.

[`docs/product/PHASE_05_RESULTS.md`, Probe 1]

### 5.2 Objective 4: the trained judge did not beat the untrained one (partial, 2026-10-08)

The held-out test set has 329 image pairs, and 47 of them show a different character. The table
ranks each judge by how well it catches those 47.

| Judge | F1 | Precision | Recall | Unreadable answers (of 329) |
|---|---|---|---|---|
| Untrained Qwen3.5-9B | 0.47 | 0.38 | 0.62 | 3 |
| Trained, seed 1 (picked in advance on validation data) | 0.31 | 0.82 | 0.19 | 40 |
| Trained, seed 0 | 0.36 | 0.79 | 0.23 | 44 |
| Trained, seed 2 | 0.42 | 0.35 | 0.51 | 8 |

An unreadable answer is output that did not parse. It is scored as "same character", so on a
different-character pair it counts as a miss. Seeds 0 and 1 gave unreadable answers on about one
pair in eight, which is part of why their recall is low.

**In plain words:**

- The trained judge is more careful. When it says "different", it is usually right (high precision).
- It misses most of the real differences (low recall).
- On F1, the main number, it is lower than the untrained model.
- The gap's 95% interval runs from −0.36 to +0.003, so it just touches zero.
- This is a partial result. It does not say fine-tuning can never work. It says this training run
  did not improve the judge under these data and settings.

[`data/judge/evaluations/obj4-v1/heldout-1/qwen_comparison.partial.json`, the numbers' source. It
is local research evidence, git-ignored, so it is not in the public repository. How it was produced:
`docs/capstone/research_runbook.md` "Partial untuned versus fine-tuned comparison". Scoring of
unreadable answers: `backend/finetune/evaluate.py`, `prediction=False` on `malformed`]

### 5.3 What goes wrong on the pages (October stage audit, provisional)

- Every shipped page of the 30 synthetic books was reviewed: 150 pages and 55 references.
- About half the pages (77 of 150) have at least one major defect.
- Pages with non-human characters fail far more often: 66 of 117, against 11 of 33 for human
  characters.
- The synthetic stories are 83% non-human, while donated stories are mostly about humans. So this
  rate likely overstates what real classroom stories get.

These scores come from AI reviewers, and the owner has not confirmed them. Treat every audit number
as provisional.

| Defect | What it looks like |
|---|---|
| Reference inherited | A mistake in the reference picture (for example six legs drawn as four) repeats on every page |
| Duplicate character | The same character appears twice on one page |
| Missing or wrong action | The character stands there instead of doing what the text says |
| Identity drift | The character's colours, hair or shape change between pages |
| Extra character | Someone who is not in the story appears |

[`docs/capstone/pipeline-stage-audit-2026-10.md`]

### 5.4 What we tried in October to fix the pages

| Tried | Result |
|---|---|
| A different scene editor (FLUX.2 klein) | On 30 random pages it drew as many duplicates as Qwen (4 each) and lost character identity more often (10 against 3). Rejected (ADR-063). |
| A prompt line asking for "one moment" | 1 of 10 draws free of duplicates. Not adopted. |
| Rewriting the direction as one frozen instant | 3 of 10 free of duplicates. Not adopted. It did fix both pages where the text described something absent or pretend. |
| Shipping whichever attempt the judge did not flag for duplicates | Helped one scene and hurt another. Not adopted. |
| A different text model | No open-weight model beat Mistral. |
| Adding a character the direction names by species ("the moth") | Fixed the one story it targets. Waiting to merge (PR #101). |
| Other reference-picture models for stated body counts | None drew counts like "six legs" correctly. Already a stated limitation (ADR-056). |

[`docs/capstone/model-probes-2026-10.md`, top table]

## 6. Limitations to say out loud at the defense

1. **Duplicate characters.** About 13% of page images show a character twice. Two different scene
   editors do this at the same rate, and four fixes failed. It is a limitation of this kind of edit
   model, measured on two of them, and it remains open.
2. **Stated body counts.** "Six legs" or "seven stripes" usually come out wrong. No tested model
   fixes it (ADR-056).
3. **Characters with no reference.** Background groups like "his six dust-bunny soldiers" have no
   reference picture. The model guesses what they look like, and once drew them as human boys.
4. **Actions.** Some pages miss the action, or give it to the wrong character. Describing only what
   is visible helped where the text mentioned something absent or pretend. That kind is about 3
   pages in 150, too few to measure a fix before the defense.
5. **Who scored the image findings.** The stage audit used AI reviewers. The October probes were
   scored by one AI rater, the assistant. Only the klein screen was blinded and used random pages.
6. **The judge result.** Objective 4's result is partial, and the trained judge scored lower F1
   than the untrained one.
7. **Scope.** One grade band, one school, one country. The base model changed after registration,
   and AI assistance in labelling is disclosed. Both are reported as limitations.

[`docs/capstone/model-probes-2026-10.md` "Limitations to carry into the write-up",
`docs/product/PREREGISTRATION_OBJ4.md`, `docs/capstone/methodology.md` §9]

## 7. Rules the project follows, and why they matter

| Rule | Why |
|---|---|
| Write the test plan and pass rule down **before** spending money on a test | So the result cannot be bent to fit afterwards. This is called preregistration. |
| Judge a change by its **rate** over many random pages, never by one good-looking page | One page can look good by luck |
| Record failures too | A failed test is evidence the panel can check |
| Only synthetic stories are browsed during development | Donated children's stories are private under the consent form |
| Decisions are written as ADRs and not edited afterwards | A new decision gets a new ADR, so the history stays honest |
| Open-weight models only | So the work can be reproduced (ADR-015) |

## 8. Words you will see

| Word | Meaning |
|---|---|
| Reference (canonical reference) | The one picture of a character drawn first, which every page copies from |
| Scene editor | The image model that draws a page from the references and a text direction |
| Judge | The AI model that checks whether a page shows the same character as the reference |
| Fine-tune | Further training of an existing model on our own labelled examples |
| Held-out set | Examples kept aside and used only once, for the final score |
| Precision | Of the pages the judge called "different", how many really were |
| Recall | Of the pages that really were different, how many the judge caught |
| F1 | One number that balances precision and recall; 1.0 is perfect |
| Blinded | The scorer cannot tell which model made which image |
| Synthetic story | A story written for testing, not by a child |
| Donated story | A real child's story, given with consent; private |
| ADR | Architecture Decision Record: a short dated note of one decision and its reasons |
| Preregistration | Writing the plan and pass rule down before seeing results |

## 9. Where to read more

| If you want… | Read |
|---|---|
| What changed since registration, and what the paper must say | `docs/capstone/research-changelog.md` |
| The research story, for an adviser | `docs/capstone/research_direction_and_goals.md` |
| The full method | `docs/capstone/methodology.md` |
| Every October test, one line each | the table at the top of `docs/capstone/model-probes-2026-10.md` |
| What is wrong with the pages | `docs/capstone/pipeline-stage-audit-2026-10.md` |
| Objective 4's plan and its amendment | `docs/product/PREREGISTRATION_OBJ4.md` |
| Objective 4's run log and results | `docs/capstone/research_runbook.md` |
| Every decision and its reason | `docs/product/ADRs.md` |
| What is planned next | `docs/product/ROADMAP.md`, "C3 findings follow-up" |
| The July model test (Phase 0.5) | `docs/product/PHASE_05_RESULTS.md` |
